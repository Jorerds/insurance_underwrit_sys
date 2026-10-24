"""M4 测试：人工核保与复核

命名规则：Test<对象>_<场景>_<预期结果>
"""

import pytest

from tests.conftest import auth_header, login
from tests.test_application import _add_question, _create_product, _valid_payload
from tests.test_underwriting import _create_rule


@pytest.fixture()
def admin_token(client):
    return login(client, "admin01")


@pytest.fixture()
def manual_case(client, admin_token):
    """预置：命中转人工规则的案件。返回 (app_id, token_underwriter, token_supervisor)。"""
    pid = _create_product(client, admin_token)
    qid = _add_question(client, admin_token, pid, "是否曾被诊断患有高血压？", is_risk=1)
    _create_rule(client, admin_token, {"family_keywords": ["癌"]}, "MANUAL", rule_name="家族史转人工")

    token_customer = login(client, "customer01")
    payload = _valid_payload(pid, qid)
    payload["family_histories"] = [{"relation": "MOTHER", "disease_name": "乳腺癌",
                                    "diagnosed_at": "2015-01-01", "treatment": None}]
    app_id = client.post("/api/v1/applications", json=payload,
                         headers=auth_header(token_customer)).json()["data"]["id"]
    return app_id, login(client, "underwriter01"), login(client, "supervisor01")


def _conclusion(result_type="STANDARD", **kw):
    body = {"result_type": result_type, "reason": "综合评估后决定"}
    body.update(kw)
    return body


class TestTask_客户访问核保接口_返回403:
    def test(self, client, manual_case):
        _, _, token_sup = manual_case
        token_customer = login(client, "customer01")
        resp = client.get("/api/v1/underwriting/tasks", headers=auth_header(token_customer))
        assert resp.status_code == 403
        # 主管可以访问
        resp = client.get("/api/v1/underwriting/tasks", headers=auth_header(token_sup))
        assert resp.status_code == 200


class TestTask_待人工列表_包含转人工案件及命中快照:
    def test(self, client, manual_case):
        app_id, token_uw, _ = manual_case
        resp = client.get("/api/v1/underwriting/tasks?status=MANUAL_REQUIRED",
                          headers=auth_header(token_uw))
        data = resp.json()["data"]
        assert any(t["id"] == app_id for t in data)

        detail = client.get(f"/api/v1/underwriting/tasks/{app_id}",
                            headers=auth_header(token_uw)).json()["data"]
        assert detail["detail"]["status"] == "MANUAL_REQUIRED"
        # 评估快照展示命中规则
        assert any(h["rule_name"] == "家族史转人工" for h in detail["auto_advice"]["hits"])


class TestConclusion_加费缺比例_返回校验错误:
    def test(self, client, manual_case):
        app_id, token_uw, _ = manual_case
        resp = client.post(f"/api/v1/underwriting/tasks/{app_id}/conclusion",
                           json=_conclusion("EXTRA"), headers=auth_header(token_uw))
        assert resp.json()["code"] == 1005
        assert "加费比例" in resp.json()["message"]


class TestConclusion_拒保无理由_参数校验失败:
    def test(self, client, manual_case):
        app_id, token_uw, _ = manual_case
        # reason 为空在 Pydantic 层拦截（422）
        resp = client.post(f"/api/v1/underwriting/tasks/{app_id}/conclusion",
                           json={"result_type": "DECLINE", "reason": ""},
                           headers=auth_header(token_uw))
        assert resp.status_code == 422


class TestConclusion_出具结论_案件进入复核中:
    def test(self, client, manual_case):
        app_id, token_uw, token_sup = manual_case
        resp = client.post(f"/api/v1/underwriting/tasks/{app_id}/conclusion",
                           json=_conclusion("EXCLUSION", exclusion_desc="除外乳腺疾病责任"),
                           headers=auth_header(token_uw))
        assert resp.json()["code"] == 0
        result_id = resp.json()["data"]["result_id"]

        detail = client.get(f"/api/v1/underwriting/tasks/{app_id}",
                            headers=auth_header(token_uw)).json()["data"]
        assert detail["detail"]["status"] == "REVIEWING"
        assert detail["latest_manual_result"]["review_status"] == "PENDING"
        assert detail["latest_manual_result"]["id"] == result_id

        # 主管待复核列表包含该结论
        reviews = client.get("/api/v1/underwriting/reviews", headers=auth_header(token_sup)).json()["data"]
        assert any(r["result_id"] == result_id for r in reviews)
        return result_id


class TestConclusion_非待人工状态出结论_被拒绝:
    def test(self, client, manual_case):
        app_id, token_uw, token_sup = manual_case
        client.post(f"/api/v1/underwriting/tasks/{app_id}/conclusion",
                    json=_conclusion(), headers=auth_header(token_uw))
        # 复核中状态再次出结论应被拒绝
        resp = client.post(f"/api/v1/underwriting/tasks/{app_id}/conclusion",
                           json=_conclusion(), headers=auth_header(token_uw))
        assert resp.json()["code"] == 1005


class TestReview_复核通过_结论生效:
    def test(self, client, manual_case):
        app_id, token_uw, token_sup = manual_case
        result_id = client.post(f"/api/v1/underwriting/tasks/{app_id}/conclusion",
                                json=_conclusion("STANDARD"), headers=auth_header(token_uw)
                                ).json()["data"]["result_id"]
        resp = client.post(f"/api/v1/underwriting/reviews/{result_id}/approve",
                           headers=auth_header(token_sup))
        assert resp.json()["code"] == 0

        detail = client.get(f"/api/v1/underwriting/tasks/{app_id}",
                            headers=auth_header(token_uw)).json()["data"]
        assert detail["detail"]["status"] == "DECIDED"
        assert detail["detail"]["result"]["result_type"] == "STANDARD"
        assert detail["detail"]["result"]["is_final"] == 1

        # 待复核列表不再包含该结论
        reviews = client.get("/api/v1/underwriting/reviews", headers=auth_header(token_sup)).json()["data"]
        assert all(r["result_id"] != result_id for r in reviews)


class TestReview_复核退回_案件回到待人工:
    def test(self, client, manual_case):
        app_id, token_uw, token_sup = manual_case
        result_id = client.post(f"/api/v1/underwriting/tasks/{app_id}/conclusion",
                                json=_conclusion("STANDARD"), headers=auth_header(token_uw)
                                ).json()["data"]["result_id"]
        # 退回必须填写意见（空值在参数校验层拦截）
        resp = client.post(f"/api/v1/underwriting/reviews/{result_id}/return",
                           json={"comment": ""}, headers=auth_header(token_sup))
        assert resp.status_code == 422

        resp = client.post(f"/api/v1/underwriting/reviews/{result_id}/return",
                           json={"comment": "理由不充分，请补充家族史核实情况"},
                           headers=auth_header(token_sup))
        assert resp.json()["code"] == 0

        detail = client.get(f"/api/v1/underwriting/tasks/{app_id}",
                            headers=auth_header(token_uw)).json()["data"]
        assert detail["detail"]["status"] == "MANUAL_REQUIRED"
        assert detail["latest_manual_result"]["review_status"] == "RETURNED"
        assert "补充家族史" in detail["latest_manual_result"]["review_comment"]

    def test_退回后可重新出具结论(self, client, manual_case):
        app_id, token_uw, token_sup = manual_case
        result_id = client.post(f"/api/v1/underwriting/tasks/{app_id}/conclusion",
                                json=_conclusion(), headers=auth_header(token_uw)
                                ).json()["data"]["result_id"]
        client.post(f"/api/v1/underwriting/reviews/{result_id}/return",
                    json={"comment": "请重新核实"}, headers=auth_header(token_sup))
        # 重新提交新结论并复核通过
        new_result_id = client.post(f"/api/v1/underwriting/tasks/{app_id}/conclusion",
                                    json=_conclusion("EXTRA", extra_rate="20.00"),
                                    headers=auth_header(token_uw)).json()["data"]["result_id"]
        assert new_result_id != result_id
        client.post(f"/api/v1/underwriting/reviews/{new_result_id}/approve",
                    headers=auth_header(token_sup))
        detail = client.get(f"/api/v1/underwriting/tasks/{app_id}",
                            headers=auth_header(token_uw)).json()["data"]
        assert detail["detail"]["status"] == "DECIDED"
        assert detail["detail"]["result"]["result_type"] == "EXTRA"


class TestReview_重复复核_被拒绝:
    def test(self, client, manual_case):
        app_id, token_uw, token_sup = manual_case
        result_id = client.post(f"/api/v1/underwriting/tasks/{app_id}/conclusion",
                                json=_conclusion(), headers=auth_header(token_uw)
                                ).json()["data"]["result_id"]
        client.post(f"/api/v1/underwriting/reviews/{result_id}/approve",
                    headers=auth_header(token_sup))
        resp = client.post(f"/api/v1/underwriting/reviews/{result_id}/approve",
                           headers=auth_header(token_sup))
        assert resp.json()["code"] == 1005


class TestReview_核保员访问复核接口_返回403:
    def test(self, client, manual_case):
        _, token_uw, _ = manual_case
        resp = client.get("/api/v1/underwriting/reviews", headers=auth_header(token_uw))
        assert resp.status_code == 403


class TestResult_人工结论对客户可见:
    def test(self, client, manual_case):
        app_id, token_uw, token_sup = manual_case
        client.post(f"/api/v1/underwriting/tasks/{app_id}/conclusion",
                    json=_conclusion("EXCLUSION", exclusion_desc="除外胃部疾病责任"),
                    headers=auth_header(token_uw))
        token_customer = login(client, "customer01")
        data = client.get(f"/api/v1/applications/{app_id}",
                          headers=auth_header(token_customer)).json()["data"]
        # 复核通过前客户不可见最终结论
        assert data["result"] is None
        reviews = client.get("/api/v1/underwriting/reviews?status=PENDING",
                             headers=auth_header(token_sup)).json()["data"]
        result_id = next(r["result_id"] for r in reviews if r["app_id"] == app_id)
        client.post(f"/api/v1/underwriting/reviews/{result_id}/approve",
                    headers=auth_header(token_sup))
        data = client.get(f"/api/v1/applications/{app_id}",
                          headers=auth_header(token_customer)).json()["data"]
        assert data["status"] == "DECIDED"
        assert data["result"]["result_type"] == "EXCLUSION"
        assert data["result"]["exclusion_desc"] == "除外胃部疾病责任"
