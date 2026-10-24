"""认证与权限接口测试

命名规则：Test<对象>_<场景>_<预期结果>
"""

import pytest
from fastapi import Depends

from app.core.deps import require_roles
from tests.conftest import auth_header, login


class TestAuth_登录成功_返回令牌与角色:
    def test(self, client):
        resp = client.post("/api/v1/auth/login",
                           json={"username": "customer01", "password": "Test@123456"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        assert body["data"]["token"]
        assert body["data"]["role"] == "customer"


class TestAuth_密码错误_返回业务错误码:
    def test(self, client):
        resp = client.post("/api/v1/auth/login",
                           json={"username": "customer01", "password": "wrong-pass"})
        body = resp.json()
        assert body["code"] == 1001
        assert body["message"] == "用户名或密码错误"
        assert body["data"] is None


class TestAuth_用户不存在_返回统一错误提示:
    def test(self, client):
        resp = client.post("/api/v1/auth/login",
                           json={"username": "nobody", "password": "Test@123456"})
        assert resp.json()["message"] == "用户名或密码错误"


class TestAuth_未携带令牌_返回401:
    def test(self, client):
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 401


class TestAuth_令牌合法_返回当前用户信息:
    def test(self, client):
        token = login(client, "underwriter01")
        resp = client.get("/api/v1/auth/me", headers=auth_header(token))
        assert resp.status_code == 200
        assert resp.json()["data"]["username"] == "underwriter01"
        assert resp.json()["data"]["role"] == "underwriter"


class TestAuth_令牌伪造_返回401:
    def test(self, client):
        resp = client.get("/api/v1/auth/me", headers=auth_header("invalid-token"))
        assert resp.status_code == 401


class Test权限_角色不符_返回403:
    def test(self, client):
        # 挂载一个仅管理员可访问的临时路由，用于验证 require_roles 拦截
        client.app.add_api_route("/tmp/admin-only", lambda: "ok",
                                 methods=["GET"], dependencies=[Depends(require_roles("admin"))])
        token = login(client, "customer01")
        resp = client.get("/tmp/admin-only", headers=auth_header(token))
        assert resp.status_code == 403


class Test权限_角色匹配_允许访问:
    def test(self, client):
        client.app.add_api_route("/tmp/admin-only2", lambda: {"ok": True},
                                 methods=["GET"], dependencies=[Depends(require_roles("admin"))])
        token = login(client, "admin01")
        resp = client.get("/tmp/admin-only2", headers=auth_header(token))
        assert resp.status_code == 200
