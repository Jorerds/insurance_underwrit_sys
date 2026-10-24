"""投保申请服务：查询与视图组装"""

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
from app.schemas.application import ApplicationDetail, ApplicationListItem


def _product_name_map(db: Session, product_ids: list[int]) -> dict[int, str]:
    """批量查询险种名，避免 N+1。"""
    if not product_ids:
        return {}
    rows = db.execute(select(Product.id, Product.name).where(Product.id.in_(product_ids))).all()
    return {pid: name for pid, name in rows}


def list_my_applications(db: Session, customer_id: int) -> list[ApplicationListItem]:
    """客户的申请列表，按创建时间倒序。"""
    apps = db.execute(
        select(Application).where(Application.customer_id == customer_id)
        .order_by(Application.created_at.desc())
    ).scalars().all()
    names = _product_name_map(db, [a.product_id for a in apps])
    return [
        ApplicationListItem(
            id=a.id, app_no=a.app_no, product_name=names.get(a.product_id, ""),
            applicant_name=a.applicant_name, gender=a.gender,
            coverage_amount=a.coverage_amount, status=a.status,
            created_at=a.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        )
        for a in apps
    ]


def get_my_application_detail(db: Session, customer_id: int, app_id: int) -> ApplicationDetail | None:
    """客户申请详情（含答卷与病史），非本人申请返回 None。"""
    app = db.get(Application, app_id)
    if app is None or app.customer_id != customer_id:
        return None
    names = _product_name_map(db, [app.product_id])

    answer = db.execute(
        select(ApplicationAnswer).where(ApplicationAnswer.application_id == app.id)
    ).scalar_one_or_none()
    medical = db.execute(
        select(MedicalHistory).where(MedicalHistory.application_id == app.id)
    ).scalars().all()
    family = db.execute(
        select(FamilyHistory).where(FamilyHistory.application_id == app.id)
    ).scalars().all()

    # 答卷补充题目文本，便于前端直接展示（题目可能已停用，故不按 status 过滤）
    answers = answer.answers if answer else []
    if answers:
        qids = [a["question_id"] for a in answers]
        q_rows = db.execute(
            select(DisclosureQuestion.id, DisclosureQuestion.content,
                   DisclosureQuestion.answer_type).where(DisclosureQuestion.id.in_(qids))
        ).all()
        q_map = {qid: {"content": content, "answer_type": atype} for qid, content, atype in q_rows}
        answers = [
            {**a, **q_map.get(a["question_id"], {"content": "（题目已删除）", "answer_type": ""})}
            for a in answers
        ]

    return ApplicationDetail(
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
        result=_final_result(db, app.id),
        reconsideration=_reconsideration(db, app.id),
    )


def _reconsideration(db: Session, app_id: int) -> dict | None:
    """查询申请单关联的复议记录（客户进度展示用）。"""
    from app.models.reconsideration import Reconsideration
    r = db.execute(
        select(Reconsideration).where(Reconsideration.application_id == app_id)
    ).scalar_one_or_none()
    if r is None:
        return None
    new_result = db.get(UnderwritingResult, r.new_result_id) if r.new_result_id else None
    return {
        "status": r.status, "reason": r.reason, "comment": r.comment,
        "handled_at": r.handled_at.strftime("%Y-%m-%d %H:%M:%S") if r.handled_at else None,
        "final_result_type": new_result.result_type if new_result else None,
    }


def _final_result(db: Session, app_id: int) -> dict | None:
    """查询该申请已生效的最终结论（自动结论出具即为最终），无则返回 None。"""
    r = db.execute(
        select(UnderwritingResult).where(
            UnderwritingResult.application_id == app_id,
            UnderwritingResult.is_final == 1,
        ).order_by(UnderwritingResult.decided_at.desc())
    ).scalars().first()
    if r is None:
        return None
    return {
        "result_type": r.result_type, "reason": r.reason,
        "extra_rate": str(r.extra_rate) if r.extra_rate is not None else None,
        "exclusion_desc": r.exclusion_desc, "postpone_months": r.postpone_months,
        "source": r.source, "decided_at": r.decided_at.strftime("%Y-%m-%d %H:%M:%S"),
        "is_final": r.is_final,
    }
