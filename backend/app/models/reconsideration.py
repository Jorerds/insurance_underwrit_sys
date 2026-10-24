"""核保复议模型

对应 PRD 4.8：客户对已出结论有异议可申请复议，复议结论为最终结论。
"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.user import BigIntPK

# 复议申请的有效期：结论出具后 30 天内
RECONSIDER_WINDOW_DAYS = 30


class Reconsideration(Base):
    """复议记录：每个申请单至多一条"""

    __tablename__ = "reconsideration"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, comment="申请ID，每单仅一次复议")
    original_result_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="针对的原结论ID")
    reason: Mapped[str] = mapped_column(String(1024), nullable=False, comment="客户复议理由")
    status: Mapped[str] = mapped_column(String(16), default="PENDING", nullable=False, comment="PENDING/DONE")
    # 复议后结论：维持时指向原结论；变更时指向新出具的 RECONSIDER 结论
    new_result_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="复议结论ID")
    handled_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="处理人（主管）")
    handled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="处理时间")
    comment: Mapped[str | None] = mapped_column(Text, nullable=True, comment="复议意见")
