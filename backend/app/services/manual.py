"""人工核保服务

核保员待办、案件详情、出具结论；主管复核通过/退回。
复核针对结论记录（underwriting_result），退回后案件回到待人工核保，原结论留痕。
"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.application import (
    Application,
    ApplicationAnswer,
    FamilyHistory,
    MedicalHistory,
)
from app.models.product import DisclosureQuestion, Product
from app.models.underwriting import UnderwritingResult
from app.models.user import User
from app.schemas.application import ApplicationDetail
from app.services import application_query


class ManualError(Exception):
    """人工核保业务错误，message 为中文提示。"""

    def __init__(self, message: str):
        self.message = message


class ConclusionIn(BaseModel):
    """人工核保结论入参"""

    result_type: str = Field(description="STANDARD/EXTRA/EXCLUSION/POSTPONE/DECLINE")
    reason: str = Field(min_length=1, max_length=1024, description="理由说明")
    extra_rate: Decimal | None = Field(default=None, description="加费比例%")
    exclusion_desc: str | None = Field(default=None, description="除外责任描述")
    postpone_months: int | None = Field(default=None, description="延期月数")

    @field_validator("result_type")
    @classmethod
    def check_type(cls, v: str) -> str:
        allowed = ("STANDARD", "EXTRA", "EXCLUSION", "POSTPONE", "DECLINE")
        if v not in allowed:
            raise ValueError("结论类型不合法")
        return v

    def validate_params(self) -> None:
        """按结论类型校验必带参数（与智能核保规则同口径）。"""
        if self.result_type == "EXTRA" and self.extra_rate is None:
            raise ManualError("加费承保必须填写加费比例")
        if self.result_type == "EXCLUSION" and not self.exclusion_desc:
            raise ManualError("除外承保必须填写除外责任描述")
        if self.result_type == "POSTPONE" and self.postpone_months is None:
            raise ManualError("延期必须填写延期月数")


def list_tasks(db: Session, status: str | None = None) -> list[dict]:
    """核保待办/案件列表（核保员与主管视角，全部案件）。可按状态筛选。"""
    stmt = select(Application).order_by(Application.created_at.desc())
    if status:
        stmt = stmt.where(Application.status == status)
    apps = db.execute(stmt).scalars().all()
    names = application_query._product_name_map(db, [a.product_id for a in apps])
    customers = _customer_name_map(db, [a.customer_id for a in apps])
    return [
        {
            "id": a.id, "app_no": a.app_no, "product_name": names.get(a.product_id, ""),
            "customer_name": customers.get(a.customer_id, ""), "applicant_name": a.applicant_name,
            "gender": a.gender, "coverage_amount": str(a.coverage_amount),
            "status": a.status, "created_at": a.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        }
        for a in apps
    ]


def _customer_name_map(db: Session, user_ids: list[int]) -> dict[int, str]:
    """批量查询客户姓名"""
    if not user_ids:
        return {}
    rows = db.execute(select(User.id, User.real_name).where(User.id.in_(user_ids))).all()
    return {uid: name for uid, name in rows}


def get_task_detail(db: Session, app_id: int) -> dict:
    """案件详情：客户视角全量资料 + 评估快照 + 最新人工结论记录。"""
    app = db.get(Application, app_id)
    if app is None:
        raise ManualError("案件不存在")

    # 客户详情复用（客户视角校验由调用方角色控制，此处直接组装）
    names = application_query._product_name_map(db, [app.product_id])
    customers = _customer_name_map(db, [app.customer_id])
    answer = db.execute(
        select(ApplicationAnswer).where(ApplicationAnswer.application_id == app.id)
    ).scalar_one_or_none()
    medical = db.execute(
        select(MedicalHistory).where(MedicalHistory.application_id == app.id)).scalars().all()
    family = db.execute(
        select(FamilyHistory).where(FamilyHistory.application_id == app.id)).scalars().all()

    answers = answer.answers if answer else []
    if answers:
        qids = [a["question_id"] for a in answers]
        q_rows = db.execute(
            select(DisclosureQuestion.id, DisclosureQuestion.content,
                   DisclosureQuestion.answer_type).where(DisclosureQuestion.id.in_(qids))
        ).all()
        q_map = {qid: {"content": c, "answer_type": t} for qid, c, t in q_rows}
        answers = [{**a, **q_map.get(a["question_id"], {"content": "（题目已删除）", "answer_type": ""})}
                   for a in answers]

    # 该申请最新的人工结论记录（含复核状态），供复核与退回场景展示
    latest = db.execute(
        select(UnderwritingResult).where(
            UnderwritingResult.application_id == app.id,
            UnderwritingResult.source == "MANUAL",
        ).order_by(UnderwritingResult.decided_at.desc())
    ).scalars().first()

    detail = ApplicationDetail(
        id=app.id, app_no=app.app_no, product_name=names.get(app.product_id, ""),
        product_id=app.product_id,
        applicant_name=app.applicant_name, gender=app.gender,
        birth_date=app.birth_date, id_card_no=app.id_card_no, phone=app.phone,
        occupation=app.occupation, coverage_amount=app.coverage_amount,
        coverage_period=app.coverage_period, pay_method=app.pay_method,
        status=app.status, created_at=app.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        answers=answers,
        medical_histories=[
            {"disease_name": h.disease_name, "diagnosed_at": str(h.diagnosed_at), "treatment": h.treatment}
            for h in medical
        ],
        family_histories=[
            {"relation": h.relation, "disease_name": h.disease_name,
             "diagnosed_at": str(h.diagnosed_at), "treatment": h.treatment}
            for h in family
        ],
        result=application_query._final_result(db, app.id),
    )
    # 该申请关联的体检单（含结果），供核保员参考
    from app.models.exam import ExamOrder
    orders = db.execute(
        select(ExamOrder).where(ExamOrder.application_id == app.id).order_by(ExamOrder.id)
    ).scalars().all()
    from app.services import exam as exam_service
    exam_orders = [exam_service._order_view(db, o) for o in orders]

    return {
        "detail": detail.model_dump(),
        "customer_name": customers.get(app.customer_id, ""),
        "auto_advice": app.auto_advice,
        "latest_manual_result": _result_view(latest) if latest else None,
        "exam_orders": exam_orders,
    }


def _result_view(r: UnderwritingResult) -> dict:
    return {
        "id": r.id, "result_type": r.result_type, "reason": r.reason,
        "extra_rate": str(r.extra_rate) if r.extra_rate is not None else None,
        "exclusion_desc": r.exclusion_desc, "postpone_months": r.postpone_months,
        "source": r.source, "review_status": r.review_status,
        "review_comment": r.review_comment,
        "decided_at": r.decided_at.strftime("%Y-%m-%d %H:%M:%S"),
        "is_final": r.is_final,
    }


def submit_conclusion(db: Session, app_id: int, underwriter_id: int, body: ConclusionIn) -> int:
    """核保员出具结论：写 MANUAL 结论（待复核），申请单进入复核中。"""
    body.validate_params()
    app = db.get(Application, app_id)
    if app is None:
        raise ManualError("案件不存在")
    if app.status != "MANUAL_REQUIRED":
        raise ManualError("当前案件状态不允许出具结论")

    result = UnderwritingResult(
        application_id=app.id,
        result_type=body.result_type,
        reason=body.reason,
        extra_rate=body.extra_rate,
        exclusion_desc=body.exclusion_desc,
        postpone_months=body.postpone_months,
        source="MANUAL",
        decided_by=underwriter_id,
        review_status="PENDING",
        is_final=0,
    )
    db.add(result)
    app.status = "REVIEWING"
    db.commit()
    return result.id


def list_reviews(db: Session, status: str = "PENDING") -> list[dict]:
    """待复核结论列表（主管）：关联申请概要。"""
    results = db.execute(
        select(UnderwritingResult).where(
            UnderwritingResult.source == "MANUAL",
            UnderwritingResult.review_status == status,
        ).order_by(UnderwritingResult.decided_at.desc())
    ).scalars().all()
    app_ids = [r.application_id for r in results]
    apps = db.execute(select(Application).where(Application.id.in_(app_ids))).scalars().all() if app_ids else []
    app_map = {a.id: a for a in apps}
    names = application_query._product_name_map(db, [a.product_id for a in apps])
    customers = _customer_name_map(db, [a.customer_id for a in apps])
    underwriters = _customer_name_map(db, [r.decided_by for r in results if r.decided_by])

    data = []
    for r in results:
        a = app_map.get(r.application_id)
        if a is None:
            continue
        data.append({
            "result_id": r.id, "app_id": a.id, "app_no": a.app_no,
            "product_name": names.get(a.product_id, ""),
            "customer_name": customers.get(a.customer_id, ""),
            "result_type": r.result_type,
            "reason": r.reason,
            "underwriter_name": underwriters.get(r.decided_by, ""),
            "decided_at": r.decided_at.strftime("%Y-%m-%d %H:%M:%S"),
        })
    return data


def approve_review(db: Session, result_id: int, supervisor_id: int) -> None:
    """复核通过：结论生效为最终结论，申请单已出结论。"""
    r = db.get(UnderwritingResult, result_id)
    if r is None or r.review_status != "PENDING":
        raise ManualError("复核记录不存在或已处理")
    r.review_status = "APPROVED"
    r.review_by = supervisor_id
    r.review_at = datetime.now()
    r.is_final = 1

    app = db.get(Application, r.application_id)
    app.status = "DECIDED"
    db.commit()


def return_review(db: Session, result_id: int, supervisor_id: int, comment: str) -> None:
    """复核退回：结论留痕为 RETURNED，申请单回到待人工核保。"""
    if not comment.strip():
        raise ManualError("退回必须填写复核意见")
    r = db.get(UnderwritingResult, result_id)
    if r is None or r.review_status != "PENDING":
        raise ManualError("复核记录不存在或已处理")
    r.review_status = "RETURNED"
    r.review_by = supervisor_id
    r.review_at = datetime.now()
    r.review_comment = comment.strip()

    app = db.get(Application, r.application_id)
    app.status = "MANUAL_REQUIRED"
    db.commit()
