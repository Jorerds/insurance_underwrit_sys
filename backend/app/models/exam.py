"""体检管理模型

对应 PRD 4.6：体检机构与项目由管理员维护字典；
核保员创建体检单，体检机构录入结果，结果回流后案件重新评估。
"""

from datetime import datetime

from sqlalchemy import JSON, BigInteger, DateTime, String, SmallInteger
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.user import BigIntPK

# 体检单状态：待体检 → 结果已录入 → 评估完成
EXAM_ORDER_STATUS = ("PENDING", "RESULT_ENTERED", "DONE")


class ExamCenter(Base):
    """体检机构字典"""

    __tablename__ = "exam_center"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, comment="机构名称")
    contact_phone: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="联系电话")
    address: Mapped[str | None] = mapped_column(String(256), nullable=True, comment="地址")
    status: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False, comment="1 启用 0 停用")


class ExamItem(Base):
    """体检项目字典"""

    __tablename__ = "exam_item"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, comment="项目名称")
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="计量单位")
    ref_range: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="参考范围")
    sort: Mapped[int] = mapped_column(default=0, nullable=False, comment="排序")
    status: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False, comment="1 启用 0 停用")


class ExamOrder(Base):
    """体检单：一个案件可先后存在多张体检单（每次评估要求体检各一张）"""

    __tablename__ = "exam_order"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="申请ID")
    center_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="体检机构ID")
    # 选中的体检项目ID快照（项目字典后续可能停用，快照保证历史单完整性）
    item_ids: Mapped[list] = mapped_column(JSON, nullable=False, comment="体检项目ID快照")
    created_by: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="创建人（核保员）")
    status: Mapped[str] = mapped_column(String(16), default="PENDING", nullable=False, comment="体检单状态")
    overall_result: Mapped[str | None] = mapped_column(String(1024), nullable=True, comment="体检总结论")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    result_entered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="结果录入时间")


class ExamItemResult(Base):
    """体检项目结果：机构逐项录入"""

    __tablename__ = "exam_item_result"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="体检单ID")
    item_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="体检项目ID")
    result_value: Mapped[str] = mapped_column(String(256), nullable=False, comment="结果值")
    is_abnormal: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False, comment="1 异常 0 正常")
    remark: Mapped[str | None] = mapped_column(String(512), nullable=True, comment="备注")
