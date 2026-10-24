"""M5 测试：体检管理

命名规则：Test<对象>_<场景>_<预期结果>
"""

import pytest

from app.core.security import hash_password
from app.models.exam import ExamCenter, ExamItem
from app.models.user import User
from tests.conftest import auth_header, login
from tests.test_application import _add_question, _create_product, _valid_payload
from tests.test_underwriting import _create_rule


def _create_center_item(client, token):
    """测试辅助：创建体检机构与两个项目，返回 (center_id, item_ids)。"""
    resp = client.post("/api/v1/admin/centers",
                       json={"name": "协和体检中心", "contact_phone": "010-12345678", "status": 1},
                       headers=auth_header(token))
    center_id = resp.json()["data"]["id"]
    item_ids = []
    for name, unit, ref in [("血常规", None, None), ("心电图", None, None)]:
        resp = client.post("/api/v1/admin/exam-items",
                           json={"name": name, "unit": unit, "ref_range": ref, "sort": 1, "status": 1},
                           headers=auth_header(token))
        item_ids.append(resp.json()["data"]["id"])
    return center_id, item_ids


def _make_exam_case(client, admin_token):
    """预置：EXAM_REQUIRED 案件。返回 (app_id, token_uw)。"""
    pid = _create_product(client, admin_token)
    qid = _add_question(client, admin_token, pid, "是否曾被诊断患有高血压？", is_risk=1)
    _create_rule(client, admin_token, {"min_age": 50}, "EXAM", rule_name="高龄体检")
    token_customer = login(client, "customer01")
    payload = _valid_payload(pid, qid)
    payload["birth_date"] = "1960-01-01"
    app_id = client.post("/api/v1/applications", json=payload,
                         headers=auth_header(token_customer)).json()["data"]["id"]
    return app_id, login(client, "underwriter01")


@pytest.fixture()
def admin_token(client):
    return login(client, "admin01")


@pytest.fixture()
def exam_env(client, db_session, admin_token):
    """预置：机构、项目、两个机构账号（甲/乙）、EXAM_REQUIRED 案件。"""
    center_id, item_ids = _create_center_item(client, admin_token)
    db_session.add_all([
        User(username="center01", real_name="机构甲", role="exam_center",
             password_hash=hash_password("Test@123456"), exam_center_id=center_id),
        User(username="center02", real_name="机构乙", role="exam_center",
             password_hash=hash_password("Test@123456"), exam_center_id=center_id + 999),
    ])
    db_session.commit()
    app_id, token_uw = _make_exam_case(client, admin_token)
    return {"app_id": app_id, "token_uw": token_uw,
            "token_c1": login(client, "center01"), "token_c2": login(client, "center02"),
            "center_id": center_id, "item_ids": item_ids}


class TestExam_非授权角色访问体检接口_返回403:
    def test(self, client, exam_env):
        token_customer = login(client, "customer01")
        resp = client.get("/api/v1/exams", headers=auth_header(token_customer))
        assert resp.status_code == 403


class TestExam_创建体检单_案件锁定待体检:
    def test(self, client, exam_env):
        resp = client.post("/api/v1/exams",
                           json={"application_id": exam_env["app_id"],
                                 "center_id": exam_env["center_id"],
                                 "item_ids": exam_env["item_ids"]},
                           headers=auth_header(exam_env["token_uw"]))
        assert resp.json()["code"] == 0
        order_id = resp.json()["data"]["id"]

        detail = client.get(f"/api/v1/underwriting/tasks/{exam_env['app_id']}",
                            headers=auth_header(exam_env["token_uw"])).json()["data"]
        assert detail["detail"]["status"] == "EXAM_REQUIRED"
        assert len(detail["exam_orders"]) == 1
        assert detail["exam_orders"][0]["id"] == order_id
        assert len(detail["exam_orders"][0]["items"]) == 2

    def test_重复创建体检单_被拒绝(self, client, exam_env):
        body = {"application_id": exam_env["app_id"], "center_id": exam_env["center_id"],
                "item_ids": exam_env["item_ids"]}
        client.post("/api/v1/exams", json=body, headers=auth_header(exam_env["token_uw"]))
        # 案件已锁定 EXAM_REQUIRED，再次创建应被拒绝（EXAM_REQUIRED 不在允许状态内）
        resp = client.post("/api/v1/exams", json=body, headers=auth_header(exam_env["token_uw"]))
        assert resp.json()["code"] == 1006


class TestExam_机构数据范围_仅见本机构单据:
    def test(self, client, exam_env):
        body = {"application_id": exam_env["app_id"], "center_id": exam_env["center_id"],
                "item_ids": exam_env["item_ids"]}
        order_id = client.post("/api/v1/exams", json=body,
                               headers=auth_header(exam_env["token_uw"])).json()["data"]["id"]

        data1 = client.get("/api/v1/exams", headers=auth_header(exam_env["token_c1"])).json()["data"]
        assert [o["id"] for o in data1] == [order_id]
        # 机构乙（center_id 不存在于单据中）看不到任何单据
        data2 = client.get("/api/v1/exams", headers=auth_header(exam_env["token_c2"])).json()["data"]
        assert data2 == []

    def test_非本机构录入结果_被拒绝(self, client, exam_env):
        body = {"application_id": exam_env["app_id"], "center_id": exam_env["center_id"],
                "item_ids": exam_env["item_ids"]}
        order_id = client.post("/api/v1/exams", json=body,
                               headers=auth_header(exam_env["token_uw"])).json()["data"]["id"]
        resp = client.put(f"/api/v1/exams/{order_id}/result",
                          json={"overall_result": "全部正常",
                                "item_results": [{"item_id": exam_env["item_ids"][0], "result_value": "正常"}]},
                          headers=auth_header(exam_env["token_c2"]))
        assert resp.json()["code"] == 1006


class TestExam_录入结果_案件重评并出结论:
    def test(self, client, exam_env):
        body = {"application_id": exam_env["app_id"], "center_id": exam_env["center_id"],
                "item_ids": exam_env["item_ids"]}
        order_id = client.post("/api/v1/exams", json=body,
                               headers=auth_header(exam_env["token_uw"])).json()["data"]["id"]

        # 机构甲录入逐项结果（含异常项）
        results = [
            {"item_id": exam_env["item_ids"][0], "result_value": "白细胞计数 11.2", "is_abnormal": 1,
             "remark": "略高于参考值"},
            {"item_id": exam_env["item_ids"][1], "result_value": "窦性心律，正常心电图", "is_abnormal": 0},
        ]
        resp = client.put(f"/api/v1/exams/{order_id}/result",
                          json={"overall_result": "血常规异常，建议复查；其余正常", "item_results": results},
                          headers=auth_header(exam_env["token_c1"]))
        assert resp.json()["code"] == 0

        # 体检单完成；案件重评：无规则命中（体检规则不再重复触发条件的其他分支）→ 默认标体
        order = client.get(f"/api/v1/exams/{order_id}", headers=auth_header(exam_env["token_c1"])).json()["data"]
        assert order["status"] == "DONE"
        assert order["overall_result"] == "血常规异常，建议复查；其余正常"
        assert order["items"][0]["is_abnormal"] == 1

        detail = client.get(f"/api/v1/underwriting/tasks/{exam_env['app_id']}",
                            headers=auth_header(exam_env["token_uw"])).json()["data"]
        assert detail["detail"]["status"] == "DECIDED"
        assert detail["detail"]["result"]["result_type"] == "STANDARD"

    def test_重复录入_被拒绝(self, client, exam_env):
        body = {"application_id": exam_env["app_id"], "center_id": exam_env["center_id"],
                "item_ids": exam_env["item_ids"]}
        order_id = client.post("/api/v1/exams", json=body,
                               headers=auth_header(exam_env["token_uw"])).json()["data"]["id"]
        payload = {"overall_result": "正常",
                   "item_results": [{"item_id": exam_env["item_ids"][0], "result_value": "正常"}]}
        client.put(f"/api/v1/exams/{order_id}/result", json=payload,
                   headers=auth_header(exam_env["token_c1"]))
        resp = client.put(f"/api/v1/exams/{order_id}/result", json=payload,
                          headers=auth_header(exam_env["token_c1"]))
        assert resp.json()["code"] == 1006

    def test_结果含单外项目_被拒绝(self, client, exam_env):
        body = {"application_id": exam_env["app_id"], "center_id": exam_env["center_id"],
                "item_ids": exam_env["item_ids"]}
        order_id = client.post("/api/v1/exams", json=body,
                               headers=auth_header(exam_env["token_uw"])).json()["data"]["id"]
        resp = client.put(f"/api/v1/exams/{order_id}/result",
                          json={"overall_result": "正常",
                                "item_results": [{"item_id": 99999, "result_value": "正常"}]},
                          headers=auth_header(exam_env["token_c1"]))
        assert resp.json()["code"] == 1006


class TestExam_人工要求补充体检_从待人工创建:
    def test(self, client, exam_env, admin_token):
        # 再构造一个 MANUAL_REQUIRED 案件：人工要求体检
        pid = _create_product(client, admin_token, code="MED002", name="重疾险")
        qid = _add_question(client, admin_token, pid, "是否吸烟？", is_risk=1)
        _create_rule(client, admin_token, {"question_ids": [qid]}, "MANUAL", rule_name="吸烟转人工")
        token_customer = login(client, "customer01")
        payload = _valid_payload(pid, qid, answer="yes", detail="每日吸烟10支，10年")
        app_id = client.post("/api/v1/applications", json=payload,
                             headers=auth_header(token_customer)).json()["data"]["id"]
        assert client.get(f"/api/v1/underwriting/tasks/{app_id}",
                          headers=auth_header(exam_env["token_uw"])).json()["data"]["detail"]["status"] \
            == "MANUAL_REQUIRED"

        resp = client.post("/api/v1/exams",
                           json={"application_id": app_id, "center_id": exam_env["center_id"],
                                 "item_ids": exam_env["item_ids"]},
                           headers=auth_header(exam_env["token_uw"]))
        assert resp.json()["code"] == 0
        detail = client.get(f"/api/v1/underwriting/tasks/{app_id}",
                            headers=auth_header(exam_env["token_uw"])).json()["data"]
        assert detail["detail"]["status"] == "EXAM_REQUIRED"


class TestExam_admin字典接口_权限与CRUD:
    def test(self, client, exam_env, admin_token):
        # 管理员可见机构列表
        centers = client.get("/api/v1/admin/centers", headers=auth_header(admin_token)).json()["data"]
        assert any(c["name"] == "协和体检中心" for c in centers)
        # 核保员无权访问管理接口
        resp = client.get("/api/v1/admin/centers", headers=auth_header(exam_env["token_uw"]))
        assert resp.status_code == 403
        # 编辑启停
        cid = exam_env["center_id"]
        resp = client.put(f"/api/v1/admin/centers/{cid}",
                          json={"name": "协和体检中心", "contact_phone": "010-12345678",
                                "address": None, "status": 0},
                          headers=auth_header(admin_token))
        assert resp.json()["code"] == 0
