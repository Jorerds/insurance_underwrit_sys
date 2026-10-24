"""pytest 公共夹具

使用内存 SQLite + StaticPool，每个测试独立数据库，不依赖执行顺序与外部服务。
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.session import Base, get_db
from app.main import create_app
from app.models import user  # noqa: F401  注册模型
from app.models.user import User

# 各角色测试账号及统一测试密码
TEST_USERS = [
    ("customer01", "客户甲", "customer"),
    ("underwriter01", "核保员甲", "underwriter"),
    ("examcenter01", "体检机构甲", "exam_center"),
    ("supervisor01", "主管甲", "supervisor"),
    ("admin01", "管理员甲", "admin"),
]
TEST_PASSWORD = "Test@123456"


@pytest.fixture()
def db_session():
    """内存数据库会话，预置全部角色测试账号。"""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    db = Session()
    for username, real_name, role in TEST_USERS:
        db.add(User(username=username, real_name=real_name, role=role,
                    password_hash=hash_password(TEST_PASSWORD)))
    db.commit()
    yield db
    db.close()


@pytest.fixture()
def client(db_session):
    """测试客户端，数据库依赖替换为内存会话。"""
    app = create_app()

    def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    return TestClient(app)


def login(client: TestClient, username: str) -> str:
    """测试辅助：登录并返回令牌。"""
    resp = client.post("/api/v1/auth/login",
                       json={"username": username, "password": TEST_PASSWORD})
    assert resp.status_code == 200
    return resp.json()["data"]["token"]


def auth_header(token: str) -> dict:
    """测试辅助：构造 Bearer 请求头。"""
    return {"Authorization": f"Bearer {token}"}
