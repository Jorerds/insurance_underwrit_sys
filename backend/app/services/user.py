"""用户服务

用户相关的业务逻辑：登录认证。
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.models.user import User


def authenticate(db: Session, username: str, password: str) -> User | None:
    """校验用户名密码，成功返回用户实体，失败返回 None。"""
    user = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
    # 统一失败提示，避免暴露账号是否存在
    if user is None or user.status != 1 or not verify_password(password, user.password_hash):
        return None
    return user
