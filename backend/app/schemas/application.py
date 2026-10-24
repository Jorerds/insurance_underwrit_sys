"""投保申请相关 Schema"""

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class AnswerItem(BaseModel):
    """单题答卷"""

    question_id: int = Field(description="题目ID")
    # yes_no 题取值为 yes/no；text 题为自由文本
    answer: str = Field(description="答案")
    detail: str | None = Field(default=None, description="详细说明，风险题答'是'时必填")


class MedicalHistoryItem(BaseModel):
    """既往病史条目"""

    disease_name: str = Field(min_length=1, max_length=128, description="疾病名称")
    diagnosed_at: date = Field(description="诊断时间")
    treatment: str | None = Field(default=None, description="治疗情况")


class FamilyHistoryItem(BaseModel):
    """家族病史条目"""

    relation: Literal["FATHER", "MOTHER", "SIBLING"] = Field(description="亲属关系")
    disease_name: str = Field(min_length=1, max_length=128, description="疾病名称")
    diagnosed_at: date = Field(description="确诊时间")
    treatment: str | None = Field(default=None, description="治疗情况")


class ApplicationCreate(BaseModel):
    """投保申请提交体"""

    product_id: int = Field(description="险种ID")
    applicant_name: str = Field(min_length=1, max_length=64, description="投保人姓名")
    gender: Literal["M", "F"] = Field(description="性别")
    birth_date: date = Field(description="出生日期")
    id_card_no: str = Field(min_length=1, max_length=32, description="证件号码")
    phone: str = Field(min_length=1, max_length=20, description="联系电话")
    occupation: str | None = Field(default=None, description="职业")
    coverage_amount: Decimal = Field(gt=0, description="保额")
    coverage_period: str = Field(min_length=1, description="保障期限")
    pay_method: str = Field(min_length=1, description="缴费方式")
    answers: list[AnswerItem] = Field(description="问卷答卷")
    medical_histories: list[MedicalHistoryItem] = Field(default_factory=list, description="既往病史")
    family_histories: list[FamilyHistoryItem] = Field(default_factory=list, description="家族病史")


class QuestionOut(BaseModel):
    """问卷题目（对客户可见的视图）"""

    id: int
    content: str
    sort: int
    is_risk: int
    answer_type: str
    is_required: int

    model_config = {"from_attributes": True}


class ProductOut(BaseModel):
    """险种视图（含启用中的问卷题目）"""

    id: int
    code: str
    name: str
    description: str | None
    questions: list[QuestionOut] = Field(default_factory=list)


class ApplicationListItem(BaseModel):
    """申请列表项视图"""

    id: int
    app_no: str
    product_name: str
    applicant_name: str
    gender: str
    coverage_amount: Decimal
    status: str
    created_at: str


class ApplicationDetail(ApplicationListItem):
    """申请详情视图：含完整投保资料与答卷"""

    product_id: int
    birth_date: date
    id_card_no: str
    phone: str
    occupation: str | None
    coverage_period: str
    pay_method: str
    answers: list[dict] = Field(default_factory=list)
    medical_histories: list[dict] = Field(default_factory=list)
    family_histories: list[dict] = Field(default_factory=list)
    # 已生效的核保结论（source=AUTO 且 is_final），未出具时为空
    result: dict | None = Field(default=None)
    # 复议记录（每单至多一条），未发起时为空
    reconsideration: dict | None = Field(default=None)
