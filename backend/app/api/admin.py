"""基础配置管理接口（admin）

险种与告知问卷题目的维护。仅管理员可访问。
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import require_roles
from app.db.session import get_db
from app.models.product import DisclosureQuestion, Product
from app.models.underwriting import UnderwritingRule
from app.schemas.underwriting import RuleIn, RuleOut

router = APIRouter(prefix="/admin", tags=["系统管理"], dependencies=[Depends(require_roles("admin"))])


class ProductIn(BaseModel):
    """险种创建/编辑入参"""

    code: str = Field(min_length=1, max_length=32, description="险种代码")
    name: str = Field(min_length=1, max_length=64, description="险种名称")
    description: str | None = Field(default=None, description="简介")
    status: int = Field(default=1, description="1 启用 0 停用")


class QuestionIn(BaseModel):
    """题目创建/编辑入参"""

    content: str = Field(min_length=1, max_length=512, description="题干")
    sort: int = Field(default=0, description="排序")
    is_risk: int = Field(default=0, description="是否风险题")
    answer_type: str = Field(default="yes_no", description="yes_no/text")
    is_required: int = Field(default=1, description="是否必答")
    status: int = Field(default=1, description="1 启用 0 停用")


def _question_view(q: DisclosureQuestion) -> dict:
    return {"id": q.id, "content": q.content, "sort": q.sort, "is_risk": q.is_risk,
            "answer_type": q.answer_type, "is_required": q.is_required, "status": q.status}


@router.get("/products")
def list_products(db: Session = Depends(get_db)):
    """全部险种列表（管理视角，含停用）。"""
    products = db.execute(select(Product).order_by(Product.id)).scalars().all()
    data = [{"id": p.id, "code": p.code, "name": p.name,
             "description": p.description, "status": p.status} for p in products]
    return {"code": 0, "message": "success", "data": data}


@router.post("/products")
def create_product(body: ProductIn, db: Session = Depends(get_db)):
    """新增险种，代码不可重复。"""
    exists = db.execute(select(Product).where(Product.code == body.code)).scalar_one_or_none()
    if exists:
        return {"code": 1004, "message": "险种代码已存在", "data": None}
    product = Product(**body.model_dump())
    db.add(product)
    db.commit()
    return {"code": 0, "message": "success", "data": {"id": product.id}}


@router.put("/products/{product_id}")
def update_product(product_id: int, body: ProductIn, db: Session = Depends(get_db)):
    """编辑险种（含启停）。"""
    product = db.get(Product, product_id)
    if product is None:
        return {"code": 1004, "message": "险种不存在", "data": None}
    for k, v in body.model_dump().items():
        setattr(product, k, v)
    db.commit()
    return {"code": 0, "message": "success", "data": {"id": product.id}}


@router.get("/products/{product_id}/questions")
def list_questions(product_id: int, db: Session = Depends(get_db)):
    """某险种的全部题目（管理视角）。"""
    questions = db.execute(
        select(DisclosureQuestion).where(DisclosureQuestion.product_id == product_id)
        .order_by(DisclosureQuestion.sort)
    ).scalars().all()
    return {"code": 0, "message": "success", "data": [_question_view(q) for q in questions]}


@router.post("/products/{product_id}/questions")
def create_question(product_id: int, body: QuestionIn, db: Session = Depends(get_db)):
    """为险种新增告知题目。"""
    if db.get(Product, product_id) is None:
        return {"code": 1004, "message": "险种不存在", "data": None}
    q = DisclosureQuestion(product_id=product_id, **body.model_dump())
    db.add(q)
    db.commit()
    return {"code": 0, "message": "success", "data": {"id": q.id}}


@router.put("/questions/{question_id}")
def update_question(question_id: int, body: QuestionIn, db: Session = Depends(get_db)):
    """编辑/启停题目。"""
    q = db.get(DisclosureQuestion, question_id)
    if q is None:
        return {"code": 1004, "message": "题目不存在", "data": None}
    for k, v in body.model_dump().items():
        setattr(q, k, v)
    db.commit()
    return {"code": 0, "message": "success", "data": {"id": q.id}}


# ---------- 核保规则配置 ----------

def _rule_view(r: UnderwritingRule) -> dict:
    return RuleOut(
        id=r.id, product_id=r.product_id, rule_name=r.rule_name,
        condition=r.condition_json, action=r.action, extra_rate=str(r.extra_rate) if r.extra_rate is not None else None,
        exclusion_desc=r.exclusion_desc,
        postpone_months=r.postpone_months, status=r.status,
    ).model_dump()


@router.get("/rules")
def list_rules(product_id: int | None = None, db: Session = Depends(get_db)):
    """规则列表，可按险种过滤（不传则含通用规则）。"""
    stmt = select(UnderwritingRule)
    if product_id is not None:
        stmt = stmt.where((UnderwritingRule.product_id == product_id) | (UnderwritingRule.product_id.is_(None)))
    rules = db.execute(stmt.order_by(UnderwritingRule.id)).scalars().all()
    return {"code": 0, "message": "success", "data": [_rule_view(r) for r in rules]}


@router.post("/rules")
def create_rule(body: RuleIn, db: Session = Depends(get_db)):
    """新增核保规则。"""
    if body.product_id is not None and db.get(Product, body.product_id) is None:
        return {"code": 1004, "message": "险种不存在", "data": None}
    rule = UnderwritingRule(
        product_id=body.product_id, rule_name=body.rule_name,
        condition_json=body.condition.model_dump(), action=body.action,
        extra_rate=body.extra_rate, exclusion_desc=body.exclusion_desc,
        postpone_months=body.postpone_months, status=body.status,
    )
    db.add(rule)
    db.commit()
    return {"code": 0, "message": "success", "data": {"id": rule.id}}


@router.put("/rules/{rule_id}")
def update_rule(rule_id: int, body: RuleIn, db: Session = Depends(get_db)):
    """编辑/启停核保规则。"""
    rule = db.get(UnderwritingRule, rule_id)
    if rule is None:
        return {"code": 1004, "message": "规则不存在", "data": None}
    rule.product_id = body.product_id
    rule.rule_name = body.rule_name
    rule.condition_json = body.condition.model_dump()
    rule.action = body.action
    rule.extra_rate = body.extra_rate
    rule.exclusion_desc = body.exclusion_desc
    rule.postpone_months = body.postpone_months
    rule.status = body.status
    db.commit()
    return {"code": 0, "message": "success", "data": {"id": rule.id}}


# ---------- 体检机构与项目字典 ----------

class CenterIn(BaseModel):
    """体检机构入参"""

    name: str = Field(min_length=1, max_length=128, description="机构名称")
    contact_phone: str | None = Field(default=None, description="联系电话")
    address: str | None = Field(default=None, description="地址")
    status: int = Field(default=1, description="1 启用 0 停用")


class ExamItemIn(BaseModel):
    """体检项目入参"""

    name: str = Field(min_length=1, max_length=128, description="项目名称")
    unit: str | None = Field(default=None, description="计量单位")
    ref_range: str | None = Field(default=None, description="参考范围")
    sort: int = Field(default=0, description="排序")
    status: int = Field(default=1, description="1 启用 0 停用")


@router.get("/centers")
def list_centers(db: Session = Depends(get_db)):
    """体检机构列表（管理视角）。"""
    from app.models.exam import ExamCenter
    centers = db.execute(select(ExamCenter).order_by(ExamCenter.id)).scalars().all()
    data = [{"id": c.id, "name": c.name, "contact_phone": c.contact_phone,
             "address": c.address, "status": c.status} for c in centers]
    return {"code": 0, "message": "success", "data": data}


@router.post("/centers")
def create_center(body: CenterIn, db: Session = Depends(get_db)):
    """新增体检机构。"""
    from app.models.exam import ExamCenter
    center = ExamCenter(**body.model_dump())
    db.add(center)
    db.commit()
    return {"code": 0, "message": "success", "data": {"id": center.id}}


@router.put("/centers/{center_id}")
def update_center(center_id: int, body: CenterIn, db: Session = Depends(get_db)):
    """编辑/启停体检机构。"""
    from app.models.exam import ExamCenter
    center = db.get(ExamCenter, center_id)
    if center is None:
        return {"code": 1004, "message": "机构不存在", "data": None}
    for k, v in body.model_dump().items():
        setattr(center, k, v)
    db.commit()
    return {"code": 0, "message": "success", "data": {"id": center.id}}


@router.get("/exam-items")
def list_exam_items(db: Session = Depends(get_db)):
    """体检项目列表（管理视角）。"""
    from app.models.exam import ExamItem
    items = db.execute(select(ExamItem).order_by(ExamItem.sort)).scalars().all()
    data = [{"id": i.id, "name": i.name, "unit": i.unit, "ref_range": i.ref_range,
             "sort": i.sort, "status": i.status} for i in items]
    return {"code": 0, "message": "success", "data": data}


@router.post("/exam-items")
def create_exam_item(body: ExamItemIn, db: Session = Depends(get_db)):
    """新增体检项目。"""
    from app.models.exam import ExamItem
    item = ExamItem(**body.model_dump())
    db.add(item)
    db.commit()
    return {"code": 0, "message": "success", "data": {"id": item.id}}


@router.put("/exam-items/{item_id}")
def update_exam_item(item_id: int, body: ExamItemIn, db: Session = Depends(get_db)):
    """编辑/启停体检项目。"""
    from app.models.exam import ExamItem
    item = db.get(ExamItem, item_id)
    if item is None:
        return {"code": 1004, "message": "项目不存在", "data": None}
    for k, v in body.model_dump().items():
        setattr(item, k, v)
    db.commit()
    return {"code": 0, "message": "success", "data": {"id": item.id}}
