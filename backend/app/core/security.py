"""安全工具模块

提供密码哈希与 JWT 编解码能力。
"""

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import settings


def hash_password(plain: str) -> str:
    """对明文密码做 bcrypt 加盐哈希，返回可落库的字符串。"""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """校验明文密码与库中哈希是否匹配。"""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_token(user_id: int, role: str) -> str:
    """生成 JWT，payload 携带用户 ID、角色与过期时间。"""
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expire_hours),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    """解析 JWT，签名错误或过期会抛 jwt 异常，由调用方统一处理。"""
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
