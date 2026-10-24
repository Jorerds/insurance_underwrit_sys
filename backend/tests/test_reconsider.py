"""M6 测试：核保复议

命名规则：Test<对象>_<场景>_<预期结果>
"""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import select

from tests.conftest import auth_header, login
from tests.test_application import _add_question, _create_product, _valid_payload
from tests.test_underwriting import _create_rule


@pytest.fixture()
def admin_token(client):
    return login(client, "admin01")


@pytest.fixture()
def decided_case(client, admin_token, db_session):
    """预置：已出结论（标体）的案件。返回 (app_id, token_customer, token_supervisor)。"""
    pid = _create_product(client, admin_token)
    qid = _add_question(client, admin_token, pid, "是否有吸烟史？", is_risk=1)
    # 无规则命中 → 默认标体直接 DECIDED
    token_customer = login(client, "customer01")
    payload = _valid_payload(pid, qid)
    app_id = client.post("/api/v1/applications", json=payload,
                         headers=auth_header(token_customer)).json()["data"]["id"]
    return app_id, token_customer, login(client, "supervisor01")


def _start(client, app_id, token, reason="对除外责任有异议，申请复议"):
    return client.post(f"/api/v1/reconsiderations/by-application/{app_id}",
                       json={"reason": reason}, headers=auth_header(token))


class TestReconsider_未出结论发起_被拒绝:
    def test(self, client, admin_token, db_session):
        # 构造 MANUAL_REQUIRED 案件
        pid = _create_product(client, admin_token, code="MED003", name="住院险")
        qid = _add_question(client, admin_token, pid, "是否住院过？", is_risk=1)
        _create_rule(client, admin_token, {"question_ids": [qid]}, "MANUAL", rule_name="转人工")
        token_customer = login(client, "customer01")
        payload = _valid_payload(pid, qid, answer="yes", detail="2022年因肺炎住院一周")
        app_id = client.post("/api/v1/applications", json=payload,
                             headers=auth_header(token_customer)).json()["data"]["id"]
        resp = _start(client, app_id, token_customer)
        assert resp.json()["code"] == 1007


class TestReconsider_重复发起_被拒绝:
    def test(self, client, decided_case):
        app_id, token_customer, _ = decided_case
        assert _start(client, app_id, token_customer).json()["code"] == 0
        resp = _start(client, app_id, token_customer)
        assert resp.json()["code"] == 1007
        assert "已申请过复议" in resp.json()["message"]


class TestReconsider_超出30天_被拒绝:
    def test(self, client, decided_case, db_session):
        from app.models.underwriting import UnderwritingResult
        app_id, token_customer, _ = decided_case
        # 把结论出具时间改为 31 天前
        result = db_session.execute(
            select(UnderwritingResult).where(UnderwritingResult.application_id == app_id)
        ).scalars().first()
        result.decided_at = datetime.now() - timedelta(days=31)
        db_session.commit()
        resp = _start(client, app_id, token_customer)
        assert resp.json()["code"] == 1007
        assert "复议申请期限" in resp.json()["message"]


class TestReconsider_发起成功_案件进入复议中:
    def test(self, client, decided_case):
        app_id, token_customer, token_sup = decided_case
        resp = _start(client, app_id, token_customer)
        assert resp.json()["code"] == 0

        data = client.get(f"/api/v1/applications/{app_id}",
                          headers=auth_header(token_customer)).json()["data"]
        assert data["status"] == "RECONSIDERING"
        # 复议期间客户仍可见原结论
        assert data["result"]["result_type"] == "STANDARD"
        assert data["reconsideration"]["status"] == "PENDING"

        # 主管待处理列表包含该复议
        rows = client.get("/api/v1/reconsiderations", headers=auth_header(token_sup)).json()["data"]
        assert any(r["application_id"] == app_id for r in rows)


class TestHandle_维持原结论_复议完成:
    def test(self, client, decided_case):
        app_id, token_customer, token_sup = decided_case
        _start(client, app_id, token_customer)
        rec_id = client.get("/api/v1/reconsiderations",
                            headers=auth_header(token_sup)).json()["data"][0]["id"]
        resp = client.post(f"/api/v1/reconsiderations/{rec_id}/handle",
                           json={"decision": "MAINTAIN", "comment": "经复核维持原结论"},
                           headers=auth_header(token_sup))
        assert resp.json()["code"] == 0

        data = client.get(f"/api/v1/applications/{app_id}",
                          headers=auth_header(token_customer)).json()["data"]
        assert data["status"] == "RECONSIDERED"
        assert data["reconsideration"]["status"] == "DONE"
        assert data["reconsideration"]["final_result_type"] == "STANDARD"
        assert data["result"]["result_type"] == "STANDARD"


class TestHandle_变更结论_客户可见新结论:
    def test(self, client, decided_case):
        app_id, token_customer, token_sup = decided_case
        _start(client, app_id, token_customer)
        rec_id = client.get("/api/v1/reconsiderations",
                            headers=auth_header(token_sup)).json()["data"][0]["id"]

        # 变更缺少新结论 → 拒绝
        resp = client.post(f"/api/v1/reconsiderations/{rec_id}/handle",
                           json={"decision": "CHANGE", "comment": "变更为加费"},
                           headers=auth_header(token_sup))
        assert resp.json()["code"] == 1007

        resp = client.post(f"/api/v1/reconsiderations/{rec_id}/handle",
                           json={"decision": "CHANGE", "comment": "重新评估后加费承保",
                                 "new_result": {"result_type": "EXTRA", "reason": "告知异常，加费承保",
                                                "extra_rate": "30.00"}},
                           headers=auth_header(token_sup))
        assert resp.json()["code"] == 0

        data = client.get(f"/api/v1/applications/{app_id}",
                          headers=auth_header(token_customer)).json()["data"]
        assert data["status"] == "RECONSIDERED"
        assert data["result"]["result_type"] == "EXTRA"
        assert data["result"]["extra_rate"] == "30.00"
        assert data["result"]["source"] == "RECONSIDER"


class TestHandle_非主管处理_返回403:
    def test(self, client, decided_case):
        app_id, token_customer, _ = decided_case
        _start(client, app_id, token_customer)
        token_uw = login(client, "underwriter01")
        resp = client.get("/api/v1/reconsiderations", headers=auth_header(token_uw))
        assert resp.status_code == 403
