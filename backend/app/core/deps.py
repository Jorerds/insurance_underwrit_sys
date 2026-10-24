"""通用依赖

提供当前用户解析与基于角色的权限校验依赖。
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import UserInfo

# 自动从 Authorization: Bearer <token> 头解析凭证
bearer = HTTPBearer(auto_error=False)


def get_current_user(
    cred: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    """解析 JWT 并加载用户实体；未登录、令牌失效、账号停用均拒绝。"""
    if cred is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="未登录或登录已过期")
    try:
        payload = decode_token(cred.credentials)
    except Exception:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="未登录或登录已过期")

    user = db.get(User, int(payload["sub"]))
    if user is None or user.status != 1:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="账号不存在或已停用")
    return user


def require_roles(*roles: str):
    """生成角色校验依赖：仅允许指定角色访问，否则 403。"""

    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="无权访问该资源")
        return user

    return checker


def to_user_info(user: User) -> UserInfo:
    """ORM 实体转响应模型。"""
    return UserInfo.model_validate(user)
