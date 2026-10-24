"""体检管理接口

核保员/主管：查看机构与项目字典、创建体检单、查看体检单。
体检机构：查看并录入本机构体检单结果。
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.deps import require_roles
from app.db.session import get_db
from app.models.user import User
from app.services import exam as exam_service

router = APIRouter(prefix="/exams", tags=["体检管理"])


class ExamOrderIn(BaseModel):
    """创建体检单入参"""

    application_id: int = Field(description="申请ID")
    center_id: int = Field(description="体检机构ID")
    item_ids: list[int] = Field(min_length=1, description="体检项目ID清单")


class ItemResultIn(BaseModel):
    """单项体检结果"""

    item_id: int = Field(description="体检项目ID")
    result_value: str = Field(min_length=1, description="结果值")
    is_abnormal: int = Field(default=0, description="1 异常 0 正常")
    remark: str | None = Field(default=None, description="备注")


class ExamResultIn(BaseModel):
    """录入体检结果入参"""

    overall_result: str = Field(min_length=1, description="体检总结论")
    item_results: list[ItemResultIn] = Field(min_length=1, description="逐项结果")


@router.get("/exam-centers")
def list_centers(
    user: User = Depends(require_roles("underwriter", "supervisor")),
    db: Session = Depends(get_db),
):
    """启用体检机构列表（创建体检单选机构用）。"""
    centers = exam_service.list_centers(db, only_active=True)
    data = [{"id": c.id, "name": c.name, "contact_phone": c.contact_phone, "address": c.address}
            for c in centers]
    return {"code": 0, "message": "success", "data": data}


@router.get("/exam-items")
def list_items(
    user: User = Depends(require_roles("underwriter", "supervisor")),
    db: Session = Depends(get_db),
):
    """启用体检项目列表。"""
    items = exam_service.list_items(db, only_active=True)
    data = [{"id": i.id, "name": i.name, "unit": i.unit, "ref_range": i.ref_range} for i in items]
    return {"code": 0, "message": "success", "data": data}


@router.post("")
def create_exam_order(
    body: ExamOrderIn,
    user: User = Depends(require_roles("underwriter", "supervisor")),
    db: Session = Depends(get_db),
):
    """创建体检单，案件锁定为待体检。"""
    try:
        order = exam_service.create_exam_order(
            db, body.application_id, body.center_id, body.item_ids, user.id)
    except exam_service.ExamError as e:
        return {"code": 1006, "message": e.message, "data": None}
    return {"code": 0, "message": "success", "data": {"id": order.id}}


@router.get("")
def list_exam_orders(
    application_id: int | None = None,
    user: User = Depends(require_roles("underwriter", "supervisor", "exam_center")),
    db: Session = Depends(get_db),
):
    """体检单列表：机构账号仅见本机构单据。"""
    return {"code": 0, "message": "success", "data": exam_service.list_exam_orders(db, user, application_id)}


@router.get("/{order_id}")
def get_exam_order(
    order_id: int,
    user: User = Depends(require_roles("underwriter", "supervisor", "exam_center")),
    db: Session = Depends(get_db),
):
    """体检单详情。"""
    try:
        data = exam_service.get_exam_order(db, user, order_id)
    except exam_service.ExamError as e:
        return {"code": 1006, "message": e.message, "data": None}
    return {"code": 0, "message": "success", "data": data}


@router.put("/{order_id}/result")
def enter_exam_result(
    order_id: int,
    body: ExamResultIn,
    user: User = Depends(require_roles("exam_center")),
    db: Session = Depends(get_db),
):
    """机构录入体检结果，结果回流触发案件重新评估。"""
    try:
        exam_service.enter_exam_result(
            db, user, order_id, body.overall_result,
            [r.model_dump() for r in body.item_results])
    except exam_service.ExamError as e:
        return {"code": 1006, "message": e.message, "data": None}
    return {"code": 0, "message": "success", "data": {"id": order_id}}
