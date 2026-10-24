"""用户模型

对应 PRD 角色定义：customer / underwriter / exam_center / supervisor / admin。
"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, String, SmallInteger
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base

# SQLite 中 BIGINT 主键不支持自增，用 Integer 变体兼容，MySQL 下仍为 BIGINT
BigIntPK = BigInteger().with_variant(Integer, "sqlite")


class User(Base):
    """系统用户表，角色字段驱动 RBAC 权限。"""

    __tablename__ = "user"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, comment="登录名")
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False, comment="bcrypt 密码哈希")
    real_name: Mapped[str] = mapped_column(String(64), nullable=False, comment="姓名")
    # 角色：customer 客户 / underwriter 核保员 / exam_center 体检机构 / supervisor 核保主管 / admin 管理员
    role: Mapped[str] = mapped_column(String(32), nullable=False, comment="角色")
    exam_center_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="体检机构账号关联的机构ID")
    status: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False, comment="1 启用 0 停用")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
