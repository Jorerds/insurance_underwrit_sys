"""认证路由

提供登录与当前用户信息接口。
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, to_user_info
from app.core.security import create_token
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, UserInfo
from app.services.user import authenticate

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/login", response_model=None)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    """账号密码登录，成功返回 JWT 与角色。"""
    user = authenticate(db, body.username, body.password)
    if user is None:
        # PRD 要求中文提示；统一提示避免暴露账号是否存在
        return {"code": 1001, "message": "用户名或密码错误", "data": None}
    return {"code": 0, "message": "success", "data": TokenResponse(token=create_token(user.id, user.role), role=user.role)}


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    """获取当前登录用户信息。"""
    return {"code": 0, "message": "success", "data": to_user_info(user)}
