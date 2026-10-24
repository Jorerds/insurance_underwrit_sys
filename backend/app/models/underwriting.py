"""智能核保模型：核保规则与核保结论

对应 PRD 4.3 / 4.7。规则由业务在管理端配置；结论表同时承载
自动（AUTO）、人工（MANUAL）、复议（RECONSIDER）三种来源。
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, DATETIME, BigInteger, DateTime, Numeric, String, SmallInteger, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.user import BigIntPK

# 规则动作枚举：结论类 + 路由类（转人工 / 要求体检）
RULE_ACTIONS = ("STANDARD", "EXTRA", "EXCLUSION", "POSTPONE", "DECLINE", "MANUAL", "EXAM")

# 结论类动作的严重度排序（高 → 低），多规则命中时取最严重结论
ACTION_SEVERITY = {"DECLINE": 5, "POSTPONE": 4, "EXCLUSION": 3, "EXTRA": 2, "STANDARD": 1}


class UnderwritingRule(Base):
    """核保规则配置表，业务可在管理端维护"""

    __tablename__ = "underwriting_rule"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    # 适用险种；为空表示全部险种通用
    product_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="适用险种，空为通用")
    rule_name: Mapped[str] = mapped_column(String(128), nullable=False, comment="规则名称")
    # 触发条件，任一子条件命中即触发：
    # {question_ids: [...], disease_keywords: [...], family_keywords: [...], min_age, max_age, min_amount}
    condition_json: Mapped[dict] = mapped_column(JSON, nullable=False, comment="触发条件")
    action: Mapped[str] = mapped_column(String(16), nullable=False, comment="动作：结论类或 MANUAL/EXAM")
    extra_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True, comment="加费比例%")
    exclusion_desc: Mapped[str | None] = mapped_column(String(512), nullable=True, comment="除外责任描述")
    postpone_months: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="建议延期月数")
    status: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False, comment="1 启用 0 停用")


class UnderwritingResult(Base):
    """核保结论表：自动/人工/复议三种来源，含复核留痕"""

    __tablename__ = "underwriting_result"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="申请ID")
    # 结论类型：STANDARD 标体 / EXTRA 加费 / EXCLUSION 除外 / POSTPONE 延期 / DECLINE 拒保
    result_type: Mapped[str] = mapped_column(String(16), nullable=False, comment="结论类型")
    reason: Mapped[str] = mapped_column(String(1024), nullable=False, comment="理由说明")
    extra_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True, comment="加费比例%")
    exclusion_desc: Mapped[str | None] = mapped_column(String(512), nullable=True, comment="除外责任描述")
    postpone_months: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="延期月数")
    # 来源：AUTO 智能核保 / MANUAL 人工核保 / RECONSIDER 复议
    source: Mapped[str] = mapped_column(String(16), default="AUTO", nullable=False, comment="结论来源")
    decided_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="出具人，系统自动结论为空")
    decided_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    # 智能核保命中的规则快照：[{rule_id, rule_name, action}]
    hit_rules: Mapped[list | None] = mapped_column(JSON, nullable=True, comment="命中规则快照")
    # 人工结论复核状态；自动结论恒为 NONE
    review_status: Mapped[str] = mapped_column(String(16), default="NONE", nullable=False, comment="NONE/PENDING/APPROVED/RETURNED")
    review_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="复核人")
    review_at: Mapped[datetime | None] = mapped_column(DATETIME, nullable=True, comment="复核时间")
    review_comment: Mapped[str | None] = mapped_column(Text, nullable=True, comment="复核意见")
    is_final: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False, comment="1 最终结论")
