"""客户投保申请接口

客户提交投保申请、查看我的申请列表与详情。数据范围限定为本人申请。
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import require_roles
from app.db.session import get_db
from app.models.user import User
from app.schemas.application import ApplicationCreate
from app.services import application as app_service
from app.services import application_query

router = APIRouter(prefix="/applications", tags=["投保申请"])


@router.post("")
def create_application(
    body: ApplicationCreate,
    user: User = Depends(require_roles("customer")),
    db: Session = Depends(get_db),
):
    """提交投保申请（基本信息 + 问卷答卷 + 病史），进入待核保状态。"""
    try:
        app = app_service.create_application(db, user.id, body)
    except app_service.ApplicationError as e:
        return {"code": 1002, "message": e.message, "data": None}
    return {"code": 0, "message": "success", "data": {"id": app.id, "app_no": app.app_no}}


@router.get("")
def list_my_applications(
    user: User = Depends(require_roles("customer")),
    db: Session = Depends(get_db),
):
    """我的申请列表。"""
    data = application_query.list_my_applications(db, user.id)
    return {"code": 0, "message": "success", "data": data}


@router.get("/{app_id}")
def get_my_application(
    app_id: int,
    user: User = Depends(require_roles("customer")),
    db: Session = Depends(get_db),
):
    """我的申请详情（含答卷与病史）。"""
    data = application_query.get_my_application_detail(db, user.id, app_id)
    if data is None:
        return {"code": 1003, "message": "申请不存在或无权查看", "data": None}
    return {"code": 0, "message": "success", "data": data}
