"""核保复议接口

客户：对已出结论案件发起复议（30 天内、每单一次）。
核保主管：查看并处理复议（维持/变更结论）。
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.deps import require_roles
from app.db.session import get_db
from app.models.user import User
from app.services import reconsider as rec_service
from app.services.manual import ConclusionIn, ManualError

router = APIRouter(prefix="/reconsiderations", tags=["核保复议"])


class ReconsiderIn(BaseModel):
    """发起复议入参"""

    reason: str = Field(min_length=1, max_length=1024, description="复议理由")


class HandleIn(BaseModel):
    """处理复议入参"""

    decision: str = Field(description="MAINTAIN 维持 / CHANGE 变更")
    comment: str = Field(min_length=1, max_length=1024, description="复议意见")
    new_result: ConclusionIn | None = Field(default=None, description="变更时的新结论")


@router.post("/by-application/{app_id}")
def start_reconsideration(
    app_id: int,
    body: ReconsiderIn,
    user: User = Depends(require_roles("customer")),
    db: Session = Depends(get_db),
):
    """客户发起复议。"""
    try:
        rec = rec_service.start_reconsideration(db, app_id, body.reason)
    except ManualError as e:
        return {"code": 1007, "message": e.message, "data": None}
    return {"code": 0, "message": "success", "data": {"id": rec.id}}


@router.get("")
def list_reconsiderations(
    status: str = "PENDING",
    user: User = Depends(require_roles("supervisor")),
    db: Session = Depends(get_db),
):
    """复议列表（主管处理视角）。"""
    return {"code": 0, "message": "success", "data": rec_service.list_reconsiderations(db, status)}


@router.post("/{rec_id}/handle")
def handle_reconsideration(
    rec_id: int,
    body: HandleIn,
    user: User = Depends(require_roles("supervisor")),
    db: Session = Depends(get_db),
):
    """主管处理复议：维持或变更结论。"""
    try:
        rec_service.handle_reconsideration(
            db, rec_id, user.id, body.decision, body.comment, body.new_result)
    except ManualError as e:
        return {"code": 1007, "message": e.message, "data": None}
    return {"code": 0, "message": "success", "data": {"id": rec_id}}
