"""人工核保与复核接口

核保员：待办列表、案件详情、出具结论。
核保主管：待复核列表、复核通过/退回。
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.deps import require_roles
from app.db.session import get_db
from app.models.user import User
from app.services import manual as manual_service

router = APIRouter(prefix="/underwriting", tags=["人工核保"])


class ReturnIn(BaseModel):
    """复核退回入参"""

    comment: str = Field(min_length=1, description="复核意见（退回理由）")


@router.get("/tasks")
def list_tasks(
    status: str | None = None,
    user: User = Depends(require_roles("underwriter", "supervisor")),
    db: Session = Depends(get_db),
):
    """核保案件列表，可按状态筛选（MANUAL_REQUIRED/REVIEWING 等）。"""
    return {"code": 0, "message": "success", "data": manual_service.list_tasks(db, status)}


@router.get("/tasks/{app_id}")
def get_task(
    app_id: int,
    user: User = Depends(require_roles("underwriter", "supervisor")),
    db: Session = Depends(get_db),
):
    """案件详情：投保资料 + 评估快照 + 最新人工结论记录。"""
    try:
        data = manual_service.get_task_detail(db, app_id)
    except manual_service.ManualError as e:
        return {"code": 1005, "message": e.message, "data": None}
    return {"code": 0, "message": "success", "data": data}


@router.post("/tasks/{app_id}/conclusion")
def submit_conclusion(
    app_id: int,
    body: manual_service.ConclusionIn,
    user: User = Depends(require_roles("underwriter")),
    db: Session = Depends(get_db),
):
    """核保员出具结论，进入复核中。"""
    try:
        result_id = manual_service.submit_conclusion(db, app_id, user.id, body)
    except manual_service.ManualError as e:
        return {"code": 1005, "message": e.message, "data": None}
    return {"code": 0, "message": "success", "data": {"result_id": result_id}}


@router.get("/reviews")
def list_reviews(
    status: str = "PENDING",
    user: User = Depends(require_roles("supervisor")),
    db: Session = Depends(get_db),
):
    """待复核结论列表（主管）。"""
    return {"code": 0, "message": "success", "data": manual_service.list_reviews(db, status)}


@router.post("/reviews/{result_id}/approve")
def approve_review(
    result_id: int,
    user: User = Depends(require_roles("supervisor")),
    db: Session = Depends(get_db),
):
    """复核通过：结论生效。"""
    try:
        manual_service.approve_review(db, result_id, user.id)
    except manual_service.ManualError as e:
        return {"code": 1005, "message": e.message, "data": None}
    return {"code": 0, "message": "success", "data": {"result_id": result_id}}


@router.post("/reviews/{result_id}/return")
def return_review(
    result_id: int,
    body: ReturnIn,
    user: User = Depends(require_roles("supervisor")),
    db: Session = Depends(get_db),
):
    """复核退回：案件回到待人工核保，需填写复核意见。"""
    try:
        manual_service.return_review(db, result_id, user.id, body.comment)
    except manual_service.ManualError as e:
        return {"code": 1005, "message": e.message, "data": None}
    return {"code": 0, "message": "success", "data": {"result_id": result_id}}
