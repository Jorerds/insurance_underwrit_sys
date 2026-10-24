"""M7 测试：统计看板与导出

命名规则：Test<对象>_<场景>_<预期结果>
"""

import io

import pytest

from tests.conftest import auth_header, login
from tests.test_application import _add_question, _create_product, _valid_payload
from tests.test_underwriting import _create_rule


@pytest.fixture()
def admin_token(client):
    return login(client, "admin01")


@pytest.fixture()
def stats_env(client, admin_token):
    """预置：两种险种、出不同结论的案件。
    返回 (token_uw, token_sup, token_customer, app_ids)。
    """
    # 险种 A：无规则 → 默认标体；险种 B：病史关键词拒保
    pid_a = _create_product(client, admin_token, code="SA", name="医疗险A")
    qid_a = _add_question(client, admin_token, pid_a, "是否有高血压？", is_risk=1)
    pid_b = _create_product(client, admin_token, code="SB", name="医疗险B")
    qid_b = _add_question(client, admin_token, pid_b, "是否有糖尿病？", is_risk=1)
    _create_rule(client, admin_token, {"disease_keywords": ["糖尿病"]}, "DECLINE",
                 product_id=pid_b, rule_name="糖尿病拒保")

    token_customer = login(client, "customer01")
    app_ids = []
    # 标体 2 件（医疗险A）
    for _ in range(2):
        payload = _valid_payload(pid_a, qid_a)
        app_ids.append(client.post("/api/v1/applications", json=payload,
                                   headers=auth_header(token_customer)).json()["data"]["id"])
    # 拒保 1 件（医疗险B）
    payload = _valid_payload(pid_b, qid_b)
    payload["medical_histories"] = [{"disease_name": "糖尿病", "diagnosed_at": "2019-01-01",
                                     "treatment": None}]
    app_ids.append(client.post("/api/v1/applications", json=payload,
                               headers=auth_header(token_customer)).json()["data"]["id"])
    return login(client, "underwriter01"), login(client, "supervisor01"), token_customer, app_ids


class TestStats_客户访问统计接口_返回403:
    def test(self, client, stats_env):
        _, _, token_customer, _ = stats_env
        resp = client.get("/api/v1/stats/dashboard", headers=auth_header(token_customer))
        assert resp.status_code == 403


class TestDashboard_汇总口径_通过率计算正确:
    def test(self, client, stats_env):
        token_uw, _, _, _ = stats_env
        data = client.get("/api/v1/stats/dashboard",
                          headers=auth_header(token_uw)).json()["data"]
        s = data["summary"]
        assert s["total"] == 3
        assert s["passed"] == 2  # 标体×2 计入，拒保不计
        assert s["pass_rate"] == 66.67
        assert s["by_result"]["STANDARD"] == 2
        assert s["by_result"]["DECLINE"] == 1


class TestDashboard_按险种维度_统计正确:
    def test(self, client, stats_env):
        token_uw, _, _, _ = stats_env
        data = client.get("/api/v1/stats/dashboard",
                          headers=auth_header(token_uw)).json()["data"]
        by_product = {p["product_name"]: p for p in data["by_product"]}
        assert by_product["医疗险A"]["total"] == 2
        assert by_product["医疗险A"]["pass_rate"] == 100.0
        assert by_product["医疗险B"]["total"] == 1
        assert by_product["医疗险B"]["pass_rate"] == 0.0


class TestDashboard_按结论维度_占比正确:
    def test(self, client, stats_env):
        token_sup, _, _, _ = stats_env
        data = client.get("/api/v1/stats/dashboard",
                          headers=auth_header(token_sup)).json()["data"]
        by_result = {r["result_type"]: r for r in data["by_result"]}
        assert by_result["STANDARD"]["count"] == 2
        assert by_result["STANDARD"]["ratio"] == 66.67
        assert by_result["DECLINE"]["count"] == 1
        assert by_result["DECLINE"]["ratio"] == 33.33


class TestDashboard_按年龄段维度_分布正确:
    def test(self, client, stats_env):
        token_uw, _, _, _ = stats_env
        data = client.get("/api/v1/stats/dashboard",
                          headers=auth_header(token_uw)).json()["data"]
        # _valid_payload 出生日期 1990-01-01，当前 36 岁 → 31-40 档
        bucket = next(b for b in data["by_age"] if b["age_range"] == "31-40")
        assert bucket["total"] == 3


class TestDashboard_时间范围筛选_区间外不统计:
    def test(self, client, stats_env):
        token_uw, _, _, _ = stats_env
        # 未来区间 → 无数据
        data = client.get("/api/v1/stats/dashboard?from=2099-01-01&to=2099-12-31",
                          headers=auth_header(token_uw)).json()["data"]
        assert data["summary"]["total"] == 0
        # 过去区间 → 无数据
        data = client.get("/api/v1/stats/dashboard?from=2000-01-01&to=2000-12-31",
                          headers=auth_header(token_uw)).json()["data"]
        assert data["summary"]["total"] == 0
        # 包含今天的区间 → 全部数据
        data = client.get("/api/v1/stats/dashboard?from=2000-01-01&to=2099-12-31",
                          headers=auth_header(token_uw)).json()["data"]
        assert data["summary"]["total"] == 3


class TestExport_CSV_含表头与明细:
    def test(self, client, stats_env):
        token_uw, _, _, _ = stats_env
        resp = client.get("/api/v1/stats/export?format=csv", headers=auth_header(token_uw))
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        text = resp.content.decode("utf-8-sig")
        lines = [l for l in text.strip().splitlines() if l]
        assert lines[0].startswith("申请单号")
        assert len(lines) == 4  # 表头 + 3 条明细
        assert "拒保" in text


class TestExport_XLSX_内容可读:
    def test(self, client, stats_env):
        from openpyxl import load_workbook

        token_uw, _, _, _ = stats_env
        resp = client.get("/api/v1/stats/export?format=xlsx", headers=auth_header(token_uw))
        assert resp.status_code == 200
        assert "spreadsheetml" in resp.headers["content-type"]
        wb = load_workbook(io.BytesIO(resp.content))
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        assert rows[0][0] == "申请单号"
        assert len(rows) == 4
        result_col = [r[4] for r in rows[1:]]
        assert result_col.count("标体承保") == 2
        assert result_col.count("拒保") == 1


class TestExport_非法格式_返回422:
    def test(self, client, stats_env):
        token_uw, _, _, _ = stats_env
        resp = client.get("/api/v1/stats/export?format=pdf", headers=auth_header(token_uw))
        assert resp.status_code == 422


class TestDashboard_未出结论案件_不计入核保量:
    def test(self, client, admin_token, stats_env):
        token_uw, _, _, _ = stats_env
        # 构造一个转人工未决案件，不应进入统计
        pid = _create_product(client, admin_token, code="SC", name="医疗险C")
        qid = _add_question(client, admin_token, pid, "是否吸烟？", is_risk=1)
        _create_rule(client, admin_token, {"question_ids": [qid]}, "MANUAL", rule_name="吸烟转人工")
        token_customer = login(client, "customer01")
        payload = _valid_payload(pid, qid, answer="yes", detail="每日一包")
        client.post("/api/v1/applications", json=payload, headers=auth_header(token_customer))

        data = client.get("/api/v1/stats/dashboard",
                          headers=auth_header(token_uw)).json()["data"]
        assert data["summary"]["total"] == 3  # 不变
