"""认证相关请求/响应模型"""

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """登录请求体"""

    username: str = Field(min_length=1, description="登录名")
    password: str = Field(min_length=1, description="密码")


class TokenResponse(BaseModel):
    """登录成功响应体"""

    token: str = Field(description="JWT 令牌")
    role: str = Field(description="用户角色")


class UserInfo(BaseModel):
    """当前登录用户信息"""

    id: int
    username: str
    real_name: str
    role: str

    model_config = {"from_attributes": True}
