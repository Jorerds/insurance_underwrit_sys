"""投保申请相关模型

对应 PRD 4.1：投保申请单、问卷答卷（JSON）、既往病史、家族病史。
申请单状态机见 PRD 4.1，状态流转集中在 service 层处理。
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import JSON, BigInteger, Date, DateTime, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.user import BigIntPK

# 申请单状态枚举值，供前后端与测试共用
APP_STATUS = (
    "PENDING",            # 待核保
    "AUTO_UNDERWRITING",  # 智能核保中
    "EXAM_REQUIRED",      # 待体检
    "MANUAL_REQUIRED",    # 待人工核保
    "REVIEWING",          # 复核中
    "DECIDED",            # 已出结论
    "RECONSIDERING",      # 复议中
    "RECONSIDERED",       # 复议完成（最终结论）
)


class Application(Base):
    """投保申请单主表"""

    __tablename__ = "application"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    app_no: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, comment="申请单号 UA+日期+序号")
    customer_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="客户ID")
    product_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="险种ID")
    applicant_name: Mapped[str] = mapped_column(String(64), nullable=False, comment="投保人姓名")
    gender: Mapped[str] = mapped_column(String(8), nullable=False, comment="M 男 / F 女")
    birth_date: Mapped[date] = mapped_column(Date, nullable=False, comment="出生日期，用于年龄统计")
    id_card_no: Mapped[str] = mapped_column(String(32), nullable=False, comment="证件号码")
    phone: Mapped[str] = mapped_column(String(20), nullable=False, comment="联系电话")
    occupation: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="职业")
    coverage_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, comment="保额")
    coverage_period: Mapped[str] = mapped_column(String(32), nullable=False, comment="保障期限")
    pay_method: Mapped[str] = mapped_column(String(32), nullable=False, comment="缴费方式")
    status: Mapped[str] = mapped_column(String(32), default="PENDING", nullable=False, comment="申请单状态")
    # 智能核保评估快照（转人工/体检时写入命中规则，供核保员参考）
    auto_advice: Mapped[dict | None] = mapped_column(JSON, nullable=True,
                                                     comment="评估快照：{next_status, hits:[...]}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)


class ApplicationAnswer(Base):
    """问卷答卷：一份申请一份答卷，答案以 JSON 存储"""

    __tablename__ = "application_answer"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, comment="申请ID")
    # 结构：[{question_id, answer, detail}]，answer 取值 yes/no/文本
    answers: Mapped[list] = mapped_column(JSON, nullable=False, comment="问卷答案")


class MedicalHistory(Base):
    """既往病史"""

    __tablename__ = "medical_history"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="申请ID")
    disease_name: Mapped[str] = mapped_column(String(128), nullable=False, comment="疾病名称")
    diagnosed_at: Mapped[date] = mapped_column(Date, nullable=False, comment="诊断时间")
    treatment: Mapped[str | None] = mapped_column(String(512), nullable=True, comment="治疗情况")


class FamilyHistory(Base):
    """家族病史：直系亲属重大疾病/遗传病史"""

    __tablename__ = "family_history"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="申请ID")
    # 亲属关系：FATHER 父 / MOTHER 母 / SIBLING 兄弟姐妹
    relation: Mapped[str] = mapped_column(String(16), nullable=False, comment="亲属关系")
    disease_name: Mapped[str] = mapped_column(String(128), nullable=False, comment="疾病名称")
    diagnosed_at: Mapped[date] = mapped_column(Date, nullable=False, comment="确诊时间")
    treatment: Mapped[str | None] = mapped_column(String(512), nullable=True, comment="治疗情况")
