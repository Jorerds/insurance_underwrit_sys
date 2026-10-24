"""M3 测试：核保规则配置与智能核保评估

命名规则：Test<对象>_<场景>_<预期结果>
"""

import pytest

from tests.conftest import auth_header, login
from tests.test_application import _add_question, _create_product, _valid_payload


def _create_rule(client, token, condition, action, product_id=None, **extra):
    """测试辅助：创建核保规则。"""
    body = {"product_id": product_id, "rule_name": extra.pop("rule_name", "测试规则"),
            "condition": condition, "action": action, "status": 1, **extra}
    resp = client.post("/api/v1/admin/rules", json=body, headers=auth_header(token))
    assert resp.json()["code"] == 0, resp.json()
    return resp.json()["data"]["id"]


def _submit(client, pid, qid, answer="no", detail=None, medical=None, birth="1990-01-01",
            amount="1000000.00"):
    """测试辅助：以客户身份提交申请并返回详情。"""
    token = login(client, "customer01")
    payload = _valid_payload(pid, qid, answer=answer, detail=detail)
    payload["birth_date"] = birth
    payload["coverage_amount"] = amount
    if medical:
        payload["medical_histories"] = medical
    app_id = client.post("/api/v1/applications", json=payload,
                         headers=auth_header(token)).json()["data"]["id"]
    return client.get(f"/api/v1/applications/{app_id}", headers=auth_header(token)).json()["data"]


@pytest.fixture()
def admin_token(client):
    return login(client, "admin01")


@pytest.fixture()
def insured_setup(client, admin_token):
    """预置：险种 + 风险题。"""
    pid = _create_product(client, admin_token)
    qid = _add_question(client, admin_token, pid, "是否曾被诊断患有高血压？", is_risk=1)
    return pid, qid


class TestRule_加费规则缺比例_校验失败:
    def test(self, client, admin_token, insured_setup):
        pid, _ = insured_setup
        resp = client.post("/api/v1/admin/rules",
                           json={"product_id": pid, "rule_name": "高血压加费",
                                 "condition": {"question_ids": []}, "action": "EXTRA",
                                 "status": 1},
                           headers=auth_header(admin_token))
        assert resp.status_code == 422


class TestRule_非管理员配置规则_返回403:
    def test(self, client):
        token = login(client, "underwriter01")
        resp = client.get("/api/v1/admin/rules", headers=auth_header(token))
        assert resp.status_code == 403


class TestUnderwriting_命中加费规则_出具加费结论:
    def test(self, client, admin_token, insured_setup):
        pid, qid = insured_setup
        _create_rule(client, admin_token, {"question_ids": [qid]}, "EXTRA",
                     product_id=pid, extra_rate="25.00", rule_name="高血压加费")
        data = _submit(client, pid, qid, answer="yes", detail="2020年确诊高血压，服药控制中")
        assert data["status"] == "DECIDED"
        assert data["result"]["result_type"] == "EXTRA"
        assert data["result"]["extra_rate"] == "25.00"
        assert "高血压加费" in data["result"]["reason"]


class TestUnderwriting_病史关键词命中拒保_出具拒保结论:
    def test(self, client, admin_token, insured_setup):
        pid, qid = insured_setup
        _create_rule(client, admin_token, {"disease_keywords": ["糖尿病"]}, "DECLINE",
                     rule_name="糖尿病拒保")
        medical = [{"disease_name": "2型糖尿病", "diagnosed_at": "2018-01-01", "treatment": "胰岛素治疗"}]
        data = _submit(client, pid, qid, medical=medical)
        assert data["status"] == "DECIDED"
        assert data["result"]["result_type"] == "DECLINE"


class TestUnderwriting_多规则命中_取最严重结论:
    def test(self, client, admin_token, insured_setup):
        pid, qid = insured_setup
        _create_rule(client, admin_token, {"disease_keywords": ["糖尿病"]}, "EXTRA",
                     extra_rate="30.00", rule_name="糖尿病加费")
        _create_rule(client, admin_token, {"disease_keywords": ["糖尿病"]}, "DECLINE",
                     rule_name="糖尿病拒保")
        medical = [{"disease_name": "糖尿病", "diagnosed_at": "2018-01-01", "treatment": None}]
        data = _submit(client, pid, qid, medical=medical)
        # 同命中加费与拒保，应取拒保
        assert data["result"]["result_type"] == "DECLINE"


class TestUnderwriting_命中体检规则_状态为待体检:
    def test(self, client, admin_token, insured_setup):
        pid, qid = insured_setup
        _create_rule(client, admin_token, {"min_age": 50, "min_amount": "2000000.00"}, "EXAM",
                     rule_name="高龄高保额体检")
        data = _submit(client, pid, qid, birth="1960-01-01", amount="3000000.00")
        assert data["status"] == "EXAM_REQUIRED"
        assert data["result"] is None


class TestUnderwriting_命中转人工规则_状态为待人工核保:
    def test(self, client, admin_token, insured_setup):
        pid, qid = insured_setup
        _create_rule(client, admin_token, {"family_keywords": ["癌"]}, "MANUAL",
                     rule_name="家族癌症史转人工")
        payload_family = [{"relation": "FATHER", "disease_name": "肺癌",
                           "diagnosed_at": "2019-01-01", "treatment": None}]
        token = login(client, "customer01")
        payload = _valid_payload(pid, qid)
        payload["family_histories"] = payload_family
        app_id = client.post("/api/v1/applications", json=payload,
                             headers=auth_header(token)).json()["data"]["id"]
        data = client.get(f"/api/v1/applications/{app_id}", headers=auth_header(token)).json()["data"]
        assert data["status"] == "MANUAL_REQUIRED"
        assert data["result"] is None


class TestUnderwriting_拒保规则优先于体检规则:
    def test(self, client, admin_token, insured_setup):
        pid, qid = insured_setup
        _create_rule(client, admin_token, {"disease_keywords": ["尿毒症"]}, "DECLINE",
                     rule_name="尿毒症拒保")
        _create_rule(client, admin_token, {"min_age": 50}, "EXAM", rule_name="高龄体检")
        medical = [{"disease_name": "尿毒症", "diagnosed_at": "2020-01-01", "treatment": "透析"}]
        data = _submit(client, pid, qid, medical=medical, birth="1960-01-01")
        # 拒保/延期直接生效，不因体检规则进入待体检
        assert data["status"] == "DECIDED"
        assert data["result"]["result_type"] == "DECLINE"


class TestUnderwriting_规则停用_不再参与评估:
    def test(self, client, admin_token, insured_setup):
        pid, qid = insured_setup
        rid = _create_rule(client, admin_token, {"question_ids": [qid]}, "DECLINE",
                           product_id=pid, rule_name="停用测试规则")
        resp = client.put(f"/api/v1/admin/rules/{rid}",
                          json={"product_id": pid, "rule_name": "停用测试规则",
                                "condition": {"question_ids": [qid]}, "action": "DECLINE",
                                "status": 0},
                          headers=auth_header(admin_token))
        assert resp.json()["code"] == 0
        data = _submit(client, pid, qid, answer="yes", detail="有高血压史")
        # 规则已停用，应回落默认标体
        assert data["result"]["result_type"] == "STANDARD"


class TestUnderwriting_通用规则跨险种生效:
    def test(self, client, admin_token, insured_setup):
        pid, qid = insured_setup
        _create_rule(client, admin_token, {"max_age": 17}, "POSTPONE",
                     postpone_months=6, rule_name="未成年延期", product_id=None)
        data = _submit(client, pid, qid, birth="2015-01-01")
        assert data["status"] == "DECIDED"
        assert data["result"]["result_type"] == "POSTPONE"
        assert data["result"]["postpone_months"] == 6


class TestUnderwriting_延期结论_需带月数与理由:
    def test(self, client, admin_token, insured_setup):
        pid, qid = insured_setup
        _create_rule(client, admin_token, {"disease_keywords": ["甲状腺"]}, "POSTPONE",
                     postpone_months=12, rule_name="甲亢延期")
        medical = [{"disease_name": "甲状腺功能亢进", "diagnosed_at": "2021-01-01", "treatment": None}]
        data = _submit(client, pid, qid, medical=medical)
        assert data["result"]["result_type"] == "POSTPONE"
        assert "甲亢延期" in data["result"]["reason"]
