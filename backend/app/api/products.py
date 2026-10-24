"""客户产品接口

提供启用险种及启用问卷题目，供客户投保时展示。
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import require_roles
from app.db.session import get_db
from app.services.product import list_products_with_questions

router = APIRouter(prefix="/products", tags=["险种"])


@router.get("")
def list_products(db: Session = Depends(get_db)):
    """可投保险种列表（仅启用险种 + 启用题目）。登录用户均可查看。"""
    data = list_products_with_questions(db, only_active=True)
    return {"code": 0, "message": "success", "data": data}
