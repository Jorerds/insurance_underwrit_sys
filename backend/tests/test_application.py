"""M2 测试：险种配置、问卷题目、投保申请

命名规则：Test<对象>_<场景>_<预期结果>
"""

import pytest

from tests.conftest import auth_header, login


def _create_product(client, token, code="MED001", name="百万医疗险"):
    """测试辅助：创建险种。"""
    resp = client.post("/api/v1/admin/products",
                       json={"code": code, "name": name, "status": 1},
                       headers=auth_header(token))
    assert resp.json()["code"] == 0
    return resp.json()["data"]["id"]


def _add_question(client, token, product_id, content, answer_type="yes_no", is_risk=0):
    """测试辅助：为险种添加题目。"""
    resp = client.post(f"/api/v1/admin/products/{product_id}/questions",
                       json={"content": content, "answer_type": answer_type, "is_risk": is_risk,
                             "sort": 1, "is_required": 1, "status": 1},
                       headers=auth_header(token))
    assert resp.json()["code"] == 0
    return resp.json()["data"]["id"]


def _valid_payload(product_id, question_id, answer="no", detail=None):
    """测试辅助：构造合法投保请求体。"""
    return {
        "product_id": product_id,
        "applicant_name": "张三",
        "gender": "M",
        "birth_date": "1990-01-01",
        "id_card_no": "110101199001011234",
        "phone": "13800000000",
        "occupation": "职员",
        "coverage_amount": "1000000.00",
        "coverage_period": "1年",
        "pay_method": "年缴",
        "answers": [{"question_id": question_id, "answer": answer, "detail": detail}],
        "medical_histories": [],
        "family_histories": [],
    }


@pytest.fixture()
def admin_token(client):
    return login(client, "admin01")


@pytest.fixture()
def product_with_question(client, admin_token):
    """预置：1 个险种 + 1 道风险题。"""
    pid = _create_product(client, admin_token)
    qid = _add_question(client, admin_token, pid, "是否曾被诊断患有高血压？", is_risk=1)
    return pid, qid


class TestAdmin_非管理员访问配置接口_返回403:
    def test(self, client):
        token = login(client, "customer01")
        resp = client.get("/api/v1/admin/products", headers=auth_header(token))
        assert resp.status_code == 403


class TestProduct_管理员创建险种_成功:
    def test(self, client, admin_token):
        pid = _create_product(client, admin_token)
        resp = client.get("/api/v1/admin/products", headers=auth_header(admin_token))
        assert any(p["id"] == pid and p["code"] == "MED001" for p in resp.json()["data"])


class TestProduct_险种代码重复_返回错误:
    def test(self, client, admin_token):
        _create_product(client, admin_token, code="DUP001")
        resp = client.post("/api/v1/admin/products",
                           json={"code": "DUP001", "name": "重复险种", "status": 1},
                           headers=auth_header(admin_token))
        assert resp.json()["code"] == 1004


class TestProduct_客户获取启用险种_含启用题目:
    def test(self, client, admin_token, product_with_question):
        pid, qid = product_with_question
        token = login(client, "customer01")
        resp = client.get("/api/v1/products", headers=auth_header(token))
        data = resp.json()["data"]
        target = next(p for p in data if p["id"] == pid)
        assert target["name"] == "百万医疗险"
        assert any(q["id"] == qid for q in target["questions"])


class TestApplication_提交申请_成功且单号格式正确:
    def test(self, client, product_with_question):
        pid, qid = product_with_question
        token = login(client, "customer01")
        resp = client.post("/api/v1/applications",
                           json=_valid_payload(pid, qid),
                           headers=auth_header(token))
        body = resp.json()
        assert body["code"] == 0
        assert body["data"]["app_no"].startswith("UA")
        assert len(body["data"]["app_no"]) == 16  # UA(2) + 8位日期 + 6位序号


class TestApplication_风险题答是未填说明_返回校验错误:
    def test(self, client, product_with_question):
        pid, qid = product_with_question
        token = login(client, "customer01")
        resp = client.post("/api/v1/applications",
                           json=_valid_payload(pid, qid, answer="yes", detail=None),
                           headers=auth_header(token))
        assert resp.json()["code"] == 1002
        assert "详细说明" in resp.json()["message"]


class TestApplication_必答题未作答_返回校验错误:
    def test(self, client, product_with_question):
        pid, qid = product_with_question
        token = login(client, "customer01")
        payload = _valid_payload(pid, qid)
        payload["answers"] = []  # 必答题全部未作答
        resp = client.post("/api/v1/applications", json=payload, headers=auth_header(token))
        assert resp.json()["code"] == 1002
        assert "必答题" in resp.json()["message"]


class TestApplication_答案含无效题目_返回校验错误:
    def test(self, client, product_with_question):
        pid, qid = product_with_question
        token = login(client, "customer01")
        payload = _valid_payload(pid, qid)
        payload["answers"].append({"question_id": 99999, "answer": "yes", "detail": "x"})
        resp = client.post("/api/v1/applications", json=payload, headers=auth_header(token))
        assert resp.json()["code"] == 1002


class TestApplication_客户仅见本人申请:
    def test(self, client, product_with_question, db_session):
        # 预置第二个客户，分别提交申请后校验列表数据范围
        from app.core.security import hash_password
        from app.models.user import User
        db_session.add(User(username="customer02", real_name="客户乙", role="customer",
                            password_hash=hash_password("Test@123456")))
        db_session.commit()

        pid, qid = product_with_question
        token_a = login(client, "customer01")
        token_b = login(client, "customer02")
        app_a = client.post("/api/v1/applications", json=_valid_payload(pid, qid),
                            headers=auth_header(token_a)).json()["data"]["id"]
        app_b = client.post("/api/v1/applications", json=_valid_payload(pid, qid),
                            headers=auth_header(token_b)).json()["data"]["id"]

        data_a = client.get("/api/v1/applications", headers=auth_header(token_a)).json()["data"]
        data_b = client.get("/api/v1/applications", headers=auth_header(token_b)).json()["data"]
        assert [d["id"] for d in data_a] == [app_a]
        assert [d["id"] for d in data_b] == [app_b]


class TestApplication_查看他人申请详情_返回无权限:
    def test(self, client, product_with_question, db_session):
        from app.core.security import hash_password
        from app.models.user import User
        pid, qid = product_with_question
        db_session.add(User(username="customer02", real_name="客户乙", role="customer",
                            password_hash=hash_password("Test@123456")))
        db_session.commit()

        token_a = login(client, "customer01")
        app_id = client.post("/api/v1/applications",
                             json=_valid_payload(pid, qid),
                             headers=auth_header(token_a)).json()["data"]["id"]

        token_b = login(client, "customer02")
        resp = client.get(f"/api/v1/applications/{app_id}", headers=auth_header(token_b))
        assert resp.json()["code"] == 1003


class TestApplication_申请详情_包含答卷与病史:
    def test(self, client, product_with_question):
        pid, qid = product_with_question
        token = login(client, "customer01")
        payload = _valid_payload(pid, qid)
        payload["medical_histories"] = [{"disease_name": "阑尾炎", "diagnosed_at": "2015-05-01",
                                         "treatment": "已手术切除"}]
        app_id = client.post("/api/v1/applications", json=payload,
                             headers=auth_header(token)).json()["data"]["id"]
        resp = client.get(f"/api/v1/applications/{app_id}", headers=auth_header(token))
        data = resp.json()["data"]
        # 无核保规则命中时默认标体承保，申请单直接已出结论
        assert data["status"] == "DECIDED"
        assert data["result"]["result_type"] == "STANDARD"
        assert len(data["answers"]) == 1
        assert data["medical_histories"][0]["disease_name"] == "阑尾炎"
