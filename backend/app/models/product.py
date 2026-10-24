"""险种与告知问卷模型

对应 PRD 4.2：告知问卷按险种配置，题目支持启停。
"""

from sqlalchemy import BigInteger, Integer, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.user import BigIntPK  # 复用 SQLite 兼容的主键类型


class Product(Base):
    """险种表"""

    __tablename__ = "product"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, comment="险种代码")
    name: Mapped[str] = mapped_column(String(64), nullable=False, comment="险种名称")
    description: Mapped[str | None] = mapped_column(String(512), nullable=True, comment="简介")
    status: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False, comment="1 启用 0 停用")


class DisclosureQuestion(Base):
    """告知问卷题目表，按险种配置"""

    __tablename__ = "disclosure_question"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="所属险种")
    content: Mapped[str] = mapped_column(String(512), nullable=False, comment="题干")
    sort: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="排序，越小越靠前")
    # 是否风险题：答"是"即触发智能核保评估
    is_risk: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False, comment="是否风险题")
    # 题目类型：yes_no 选"是"必须填详细说明；text 为自由文本
    answer_type: Mapped[str] = mapped_column(String(16), default="yes_no", nullable=False, comment="yes_no/text")
    is_required: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False, comment="是否必答")
    status: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False, comment="1 启用 0 停用")
