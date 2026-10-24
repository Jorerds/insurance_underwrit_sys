"""统计看板与导出接口

仅核保员与核保主管可见。统计口径：筛选时间内出具最终结论的案件。
"""

from datetime import date

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.deps import require_roles
from app.db.session import get_db
from app.services import stats as stats_service

router = APIRouter(prefix="/stats", tags=["统计报表"],
                   dependencies=[Depends(require_roles("underwriter", "supervisor"))])


@router.get("/dashboard")
def dashboard(
    date_from: date | None = Query(default=None, alias="from", description="起始日期（含）"),
    date_to: date | None = Query(default=None, alias="to", description="截止日期（含）"),
    db: Session = Depends(get_db),
):
    """看板数据：汇总 + 按险种/年龄段/结论统计 + 明细行。"""
    return {"code": 0, "message": "success",
            "data": stats_service.build_dashboard(db, date_from, date_to)}


@router.get("/export")
def export_stats(
    format: str = Query(default="xlsx", pattern="^(xlsx|csv)$", description="导出格式"),
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
    db: Session = Depends(get_db),
):
    """导出核保明细（xlsx/csv），文件名带日期。"""
    content, media_type, filename = stats_service.export_rows(db, date_from, date_to, format)
    # 文件名含中文，按 RFC 5987 编码
    from urllib.parse import quote

    return Response(
        content=content, media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )
