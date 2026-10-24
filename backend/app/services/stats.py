"""统计服务

口径：核保量 = 筛选时间内出具最终结论（is_final=1）的案件数，按结论出具时间过滤；
通过率 =（标体+加费+除外）/ 核保量。年龄段按申请单出生日期计算周岁。
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.application import Application
from app.models.underwriting import UnderwritingResult

# 承保类结论：计入通过
PASS_TYPES = ("STANDARD", "EXTRA", "EXCLUSION")

# 年龄段分档（左闭右开，最后档含 60 及以上）
AGE_BUCKETS = [(0, 17), (18, 30), (31, 40), (41, 50), (51, 60), (61, 200)]
AGE_LABELS = ["0-17", "18-30", "31-40", "41-50", "51-60", "60+"]


def _age(birth_date: date) -> int:
    """按出生日期计算周岁"""
    today = date.today()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))


def _age_bucket(age: int) -> str:
    for (lo, hi), label in zip(AGE_BUCKETS, AGE_LABELS):
        if lo <= age <= hi:
            return label
    return AGE_LABELS[-1]


def _load_decided_rows(db: Session, date_from: date | None, date_to: date | None) -> list[dict]:
    """加载筛选时间内的最终结论及其申请信息。"""
    stmt = select(UnderwritingResult, Application).join(
        Application, UnderwritingResult.application_id == Application.id
    ).where(UnderwritingResult.is_final == 1)
    if date_from is not None:
        stmt = stmt.where(UnderwritingResult.decided_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to is not None:
        stmt = stmt.where(UnderwritingResult.decided_at <= datetime.combine(date_to, datetime.max.time()))
    rows = db.execute(stmt.order_by(UnderwritingResult.decided_at.desc())).all()
    return [
        {
            "app_no": app.app_no, "product_id": app.product_id,
            "applicant_name": app.applicant_name, "age": _age(app.birth_date),
            "result_type": r.result_type, "source": r.source,
            "decided_at": r.decided_at.strftime("%Y-%m-%d"),
        }
        for r, app in rows
    ]


def _product_name_map(db: Session) -> dict[int, str]:
    from app.models.product import Product
    rows = db.execute(select(Product.id, Product.name)).all()
    return {pid: name for pid, name in rows}


def build_dashboard(db: Session, date_from: date | None, date_to: date | None) -> dict:
    """组装看板数据：汇总卡片 + 三维度统计 + 明细行。"""
    rows = _load_decided_rows(db, date_from, date_to)
    names = _product_name_map(db)

    total = len(rows)
    passed = sum(1 for r in rows if r["result_type"] in PASS_TYPES)

    # 按结论分布
    by_result: dict[str, int] = {}
    for r in rows:
        by_result[r["result_type"]] = by_result.get(r["result_type"], 0) + 1

    # 按险种
    by_product_map: dict[int, dict] = {}
    for r in rows:
        d = by_product_map.setdefault(r["product_id"],
                                      {"total": 0, "passed": 0, "results": {}})
        d["total"] += 1
        if r["result_type"] in PASS_TYPES:
            d["passed"] += 1
        d["results"][r["result_type"]] = d["results"].get(r["result_type"], 0) + 1
    by_product = [
        {"product_id": pid, "product_name": names.get(pid, f"险种#{pid}"),
         "total": d["total"], "passed": d["passed"],
         "pass_rate": round(d["passed"] / d["total"] * 100, 2) if d["total"] else 0,
         "results": d["results"]}
        for pid, d in sorted(by_product_map.items(), key=lambda x: -x[1]["total"])
    ]

    # 按年龄段
    by_age_map: dict[str, dict] = {label: {"total": 0, "passed": 0} for label in AGE_LABELS}
    for r in rows:
        label = _age_bucket(r["age"])
        by_age_map[label]["total"] += 1
        if r["result_type"] in PASS_TYPES:
            by_age_map[label]["passed"] += 1
    by_age = [
        {"age_range": label, "total": d["total"], "passed": d["passed"],
         "pass_rate": round(d["passed"] / d["total"] * 100, 2) if d["total"] else 0}
        for label, d in by_age_map.items()
    ]

    return {
        "summary": {
            "total": total, "passed": passed,
            "pass_rate": round(passed / total * 100, 2) if total else 0,
            "by_result": by_result,
        },
        "by_product": by_product,
        "by_age": by_age,
        "by_result": [
            {"result_type": t, "count": by_result.get(t, 0),
             "ratio": round(by_result.get(t, 0) / total * 100, 2) if total else 0}
            for t in ("STANDARD", "EXTRA", "EXCLUSION", "POSTPONE", "DECLINE")
        ],
        "detail": [
            {**r, "product_name": names.get(r["product_id"], "")} for r in rows
        ],
    }


EXPORT_HEADERS = ["申请单号", "险种", "投保人", "年龄段", "核保结论", "结论来源", "出具日期"]


def export_rows(db: Session, date_from: date | None, date_to: date | None,
                fmt: str) -> tuple[bytes, str, str]:
    """导出明细为 xlsx 或 csv，返回 (内容, 媒体类型, 文件名)。"""
    rows = _load_decided_rows(db, date_from, date_to)
    names = _product_name_map(db)

    from app.utils.dict import RESULT_NAMES  # 中文结论名
    table = [
        [r["app_no"], names.get(r["product_id"], ""), r["applicant_name"],
         _age_bucket(r["age"]), RESULT_NAMES.get(r["result_type"], r["result_type"]),
         {"AUTO": "智能核保", "MANUAL": "人工核保", "RECONSIDER": "复议"}.get(r["source"], r["source"]),
         r["decided_at"]]
        for r in rows
    ]

    filename_date = datetime.now().strftime("%Y%m%d")
    if fmt == "csv":
        import csv
        import io

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(EXPORT_HEADERS)
        writer.writerows(table)
        # UTF-8 BOM 保证 Excel 打开中文不乱码
        return ("﻿" + buf.getvalue()).encode("utf-8"), \
            "text/csv; charset=utf-8", f"核保统计_{filename_date}.csv"

    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "核保统计"
    ws.append(EXPORT_HEADERS)
    for row in table:
        ws.append(row)
    import io

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue(), \
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", \
        f"核保统计_{filename_date}.xlsx"
