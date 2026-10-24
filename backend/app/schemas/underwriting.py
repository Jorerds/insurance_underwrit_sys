"""核保规则与结论 Schema"""

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class RuleCondition(BaseModel):
    """规则触发条件：任一子条件命中即触发；全空表示不触发任何案件"""

    question_ids: list[int] = Field(default_factory=list, description="风险题ID列表，任一职答'是'即命中")
    disease_keywords: list[str] = Field(default_factory=list, description="既往病史关键词")
    family_keywords: list[str] = Field(default_factory=list, description="家族病史关键词")
    min_age: int | None = Field(default=None, description="年龄下限（含）")
    max_age: int | None = Field(default=None, description="年龄上限（含）")
    min_amount: str | None = Field(default=None, description="保额下限（含）")


class RuleIn(BaseModel):
    """规则创建/编辑入参"""

    product_id: int | None = Field(default=None, description="适用险种，空为通用")
    rule_name: str = Field(min_length=1, max_length=128, description="规则名称")
    condition: RuleCondition = Field(description="触发条件")
    action: Literal["STANDARD", "EXTRA", "EXCLUSION", "POSTPONE", "DECLINE", "MANUAL", "EXAM"]
    extra_rate: str | None = Field(default=None, description="加费比例%，加费规则必填")
    exclusion_desc: str | None = Field(default=None, description="除外责任描述，除外规则必填")
    postpone_months: int | None = Field(default=None, description="延期月数，延期规则必填")
    status: int = Field(default=1, description="1 启用 0 停用")

    @model_validator(mode="after")
    def check_action_params(self):
        """动作必填参数校验：加费须带比例、除外须带描述、延期须带月数"""
        if self.action == "EXTRA" and self.extra_rate is None:
            raise ValueError("加费规则必须填写加费比例")
        if self.action == "EXCLUSION" and not self.exclusion_desc:
            raise ValueError("除外规则必须填写除外责任描述")
        if self.action == "POSTPONE" and self.postpone_months is None:
            raise ValueError("延期规则必须填写延期月数")
        return self


class RuleOut(BaseModel):
    """规则视图"""

    id: int
    product_id: int | None
    rule_name: str
    condition: dict
    action: str
    extra_rate: str | None
    exclusion_desc: str | None
    postpone_months: int | None
    status: int


class ResultOut(BaseModel):
    """核保结论视图（客户可见部分）"""

    result_type: str
    reason: str
    extra_rate: str | None
    exclusion_desc: str | None
    postpone_months: int | None
    source: str
    decided_at: str
    is_final: int
