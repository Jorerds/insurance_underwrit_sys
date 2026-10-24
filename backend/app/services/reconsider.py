"""核保复议服务

客户发起复议（DECIDED 30 天内、每单一次）；主管维持或变更结论。
"""

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.application import Application
from app.models.reconsideration import RECONSIDER_WINDOW_DAYS, Reconsideration
from app.models.underwriting import UnderwritingResult
from app.models.user import User
from app.services.manual import ConclusionIn, ManualError


def start_reconsideration(db: Session, application_id: int, reason: str) -> Reconsideration:
    """客户发起复议：校验状态、有效期与次数。"""
    app = db.get(Application, application_id)
    if app is None:
        raise ManualError("申请不存在")

    # 先校验复议次数（先于状态校验，保证“每单一次”语义明确）
    exists = db.execute(
        select(Reconsideration).where(Reconsideration.application_id == application_id)
    ).scalar_one_or_none()
    if exists is not None:
        raise ManualError("该案件已申请过复议")

    if app.status != "DECIDED":
        raise ManualError("仅已出结论的案件可申请复议")

    # 以当前生效的最终结论出具时间为准计算有效期
    original = db.execute(
        select(UnderwritingResult).where(
            UnderwritingResult.application_id == application_id,
            UnderwritingResult.is_final == 1,
        ).order_by(UnderwritingResult.decided_at.desc())
    ).scalars().first()
    if original is None:
        raise ManualError("该案件尚未出具有效结论")
    deadline = original.decided_at + timedelta(days=RECONSIDER_WINDOW_DAYS)
    if datetime.now() > deadline:
        raise ManualError(f"已超出复议申请期限（结论出具后 {RECONSIDER_WINDOW_DAYS} 天内可申请）")

    rec = Reconsideration(
        application_id=application_id, original_result_id=original.id,
        reason=reason.strip(), status="PENDING",
    )
    db.add(rec)
    app.status = "RECONSIDERING"
    db.commit()
    return rec


def list_reconsiderations(db: Session, status: str = "PENDING") -> list[dict]:
    """复议列表（主管处理视角），关联申请与结论概要。"""
    recs = db.execute(
        select(Reconsideration).where(Reconsideration.status == status)
        .order_by(Reconsideration.id.desc())
    ).scalars().all()
    data = []
    for r in recs:
        app = db.get(Application, r.application_id)
        original = db.get(UnderwritingResult, r.original_result_id)
        customer = db.get(User, app.customer_id) if app else None
        data.append({
            "id": r.id, "application_id": r.application_id,
            "app_no": app.app_no if app else "",
            "customer_name": customer.real_name if customer else "",
            "result_type": original.result_type if original else "",
            "result_reason": original.reason if original else "",
            "reason": r.reason,
            "original_result_id": r.original_result_id,
        })
    return data


def handle_reconsideration(db: Session, rec_id: int, supervisor_id: int,
                           decision: str, comment: str,
                           new_result: ConclusionIn | None) -> None:
    """主管处理复议：维持原结论或变更结论，复议结论为最终结论。"""
    if not comment.strip():
        raise ManualError("请填写复议意见")
    rec = db.get(Reconsideration, rec_id)
    if rec is None or rec.status != "PENDING":
        raise ManualError("复议记录不存在或已处理")
    app = db.get(Application, rec.application_id)
    if app.status != "RECONSIDERING":
        raise ManualError("该案件当前不在复议流程中")

    if decision == "MAINTAIN":
        rec.new_result_id = rec.original_result_id
    elif decision == "CHANGE":
        if new_result is None:
            raise ManualError("变更结论时必须填写新结论")
        new_result.validate_params()
        result = UnderwritingResult(
            application_id=app.id,
            result_type=new_result.result_type,
            reason=new_result.reason,
            extra_rate=new_result.extra_rate,
            exclusion_desc=new_result.exclusion_desc,
            postpone_months=new_result.postpone_months,
            source="RECONSIDER",
            decided_by=supervisor_id,
            review_status="NONE",
            is_final=1,
        )
        db.add(result)
        db.flush()
        rec.new_result_id = result.id
    else:
        raise ManualError("复议决定不合法")

    rec.status = "DONE"
    rec.handled_by = supervisor_id
    rec.handled_at = datetime.now()
    rec.comment = comment.strip()
    app.status = "RECONSIDERED"  # 终态：复议完成
    db.commit()


def get_application_reconsideration(db: Session, application_id: int) -> dict | None:
    """申请单关联的复议记录（客户详情展示用）。"""
    r = db.execute(
        select(Reconsideration).where(Reconsideration.application_id == application_id)
    ).scalar_one_or_none()
    if r is None:
        return None
    new_result = db.get(UnderwritingResult, r.new_result_id) if r.new_result_id else None
    return {
        "status": r.status, "reason": r.reason, "comment": r.comment,
        "handled_at": r.handled_at.strftime("%Y-%m-%d %H:%M:%S") if r.handled_at else None,
        "final_result_type": new_result.result_type if new_result else None,
    }
