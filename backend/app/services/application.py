"""投保申请服务

负责申请单创建（含问卷校验、单号生成）与查询。
状态流转规则：M2 提交后进入 PENDING（待核保），智能核保评估在 M3 接入。
"""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.application import (
    Application,
    ApplicationAnswer,
    FamilyHistory,
    MedicalHistory,
)
from app.models.product import DisclosureQuestion, Product
from app.schemas.application import ApplicationCreate


class ApplicationError(Exception):
    """业务校验失败，message 为面向用户的中文提示。"""

    def __init__(self, message: str):
        self.message = message


def gen_app_no(db: Session) -> str:
    """生成申请单号：UA + yyyyMMdd + 当天 6 位递增序号。"""
    day = datetime.now().strftime("%Y%m%d")
    prefix = f"UA{day}"
    last = db.execute(
        select(func.max(Application.app_no)).where(Application.app_no.like(f"{prefix}%"))
    ).scalar_one_or_none()
    seq = 1 if last is None else int(last[len(prefix):]) + 1
    return f"{prefix}{seq:06d}"


def validate_answers(db: Session, product_id: int, answers: list) -> dict[int, DisclosureQuestion]:
    """校验答卷是否满足该险种启用题目的要求，返回题目映射。

    规则：必答题必须作答；yes_no 题答案仅允许 yes/no；风险题答"是"必须填详细说明。
    """
    questions = db.execute(
        select(DisclosureQuestion).where(
            DisclosureQuestion.product_id == product_id,
            DisclosureQuestion.status == 1,
        )
    ).scalars().all()
    q_map = {q.id: q for q in questions}

    answered = {a.question_id: a for a in answers}
    for q in questions:
        item = answered.get(q.id)
        if item is None:
            if q.is_required == 1:
                raise ApplicationError(f"问卷第 {q.sort} 题为必答题，请作答")
            continue
        if q.answer_type == "yes_no" and item.answer not in ("yes", "no"):
            raise ApplicationError("问卷存在非法答案，请重新作答")
        # 风险题或 yes_no 题选"是"时，必须补充详细说明（何时何地诊断治疗）
        if q.answer_type == "yes_no" and item.answer == "yes" and not (item.detail or "").strip():
            raise ApplicationError(f"问卷第 {q.sort} 题回答为“是”，请填写详细说明")
    # 拒绝不属于本险种的题目答案
    for qid in answered:
        if qid not in q_map:
            raise ApplicationError("问卷答案包含无效题目，请重新作答")
    return q_map


def create_application(db: Session, customer_id: int, body: ApplicationCreate) -> Application:
    """创建投保申请：校验产品、校验答卷，事务内写入申请单/答卷/病史。"""
    product = db.get(Product, body.product_id)
    if product is None or product.status != 1:
        raise ApplicationError("所选险种不存在或已停售")

    validate_answers(db, body.product_id, body.answers)

    app = Application(
        app_no=gen_app_no(db),
        customer_id=customer_id,
        product_id=body.product_id,
        applicant_name=body.applicant_name,
        gender=body.gender,
        birth_date=body.birth_date,
        id_card_no=body.id_card_no,
        phone=body.phone,
        occupation=body.occupation,
        coverage_amount=body.coverage_amount,
        coverage_period=body.coverage_period,
        pay_method=body.pay_method,
        status="AUTO_UNDERWRITING",  # 提交后进入智能核保中，随后触发评估
    )
    db.add(app)
    db.flush()  # 先拿到 app.id 再写关联数据

    db.add(ApplicationAnswer(
        application_id=app.id,
        answers=[a.model_dump() for a in body.answers],
    ))
    for h in body.medical_histories:
        db.add(MedicalHistory(application_id=app.id, **h.model_dump()))
    for h in body.family_histories:
        db.add(FamilyHistory(application_id=app.id, **h.model_dump()))

    db.commit()

    # 触发智能核保评估：默认同步执行（use_celery=False），接入 Redis 后切异步
    _dispatch_underwriting(app.id, db)
    return app


def _dispatch_underwriting(app_id: int, db: Session) -> None:
    """按配置决定同步评估或投递 Celery 异步任务。

    同步路径复用当前会话（测试与依赖覆盖场景一致）；Celery 路径在任务内自建会话。
    """
    from app.core.config import settings

    if settings.use_celery:
        from app.tasks.celery_app import auto_underwrite
        auto_underwrite.delay(app_id)
    else:
        from app.services.underwriting import run_auto_underwriting
        run_auto_underwriting(db, app_id)
