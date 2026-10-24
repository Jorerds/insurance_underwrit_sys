"""产品（险种）相关服务与视图组装

客户可见启用险种 + 启用题目；管理端可见全部。
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.product import DisclosureQuestion, Product
from app.schemas.application import ProductOut, QuestionOut


def list_products_with_questions(db: Session, only_active: bool) -> list[ProductOut]:
    """返回险种列表（含题目）。only_active=True 时仅返回启用险种与启用题目，供客户投保。"""
    stmt = select(Product)
    if only_active:
        stmt = stmt.where(Product.status == 1)
    products = db.execute(stmt.order_by(Product.id)).scalars().all()
    if not products:
        return []

    # 批量取题目，按险种分组，避免 N+1
    pids = [p.id for p in products]
    q_stmt = select(DisclosureQuestion).where(DisclosureQuestion.product_id.in_(pids))
    if only_active:
        q_stmt = q_stmt.where(DisclosureQuestion.status == 1)
    questions = db.execute(q_stmt.order_by(DisclosureQuestion.sort)).scalars().all()
    by_product: dict[int, list[QuestionOut]] = {}
    for q in questions:
        by_product.setdefault(q.product_id, []).append(QuestionOut.model_validate(q))

    return [
        ProductOut(
            id=p.id, code=p.code, name=p.name, description=p.description,
            questions=by_product.get(p.id, []),
        )
        for p in products
    ]
