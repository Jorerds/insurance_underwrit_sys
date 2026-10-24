"""体检管理服务

核保员创建体检单（案件锁定待体检）；机构录入结果（限本机构）；
结果回流后案件重新进入智能核保评估。
"""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.application import Application
from app.models.exam import ExamCenter, ExamItem, ExamItemResult, ExamOrder
from app.models.user import User


class ExamError(Exception):
    """体检业务错误，message 为中文提示。"""

    def __init__(self, message: str):
        self.message = message


def list_centers(db: Session, only_active: bool = False) -> list[ExamCenter]:
    """机构列表；only_active 时仅启用机构（下拉选择用）。"""
    stmt = select(ExamCenter).order_by(ExamCenter.id)
    if only_active:
        stmt = stmt.where(ExamCenter.status == 1)
    return db.execute(stmt).scalars().all()


def list_items(db: Session, only_active: bool = False) -> list[ExamItem]:
    """体检项目列表。"""
    stmt = select(ExamItem).order_by(ExamItem.sort)
    if only_active:
        stmt = stmt.where(ExamItem.status == 1)
    return db.execute(stmt).scalars().all()


def create_exam_order(db: Session, application_id: int, center_id: int,
                      item_ids: list[int], operator_id: int) -> ExamOrder:
    """创建体检单：案件须处于待体检或待人工核保状态，创建后锁定为待体检。"""
    app = db.get(Application, application_id)
    if app is None:
        raise ExamError("案件不存在")
    if app.status not in ("EXAM_REQUIRED", "MANUAL_REQUIRED"):
        raise ExamError("当前案件状态不允许创建体检单")

    center = db.get(ExamCenter, center_id)
    if center is None or center.status != 1:
        raise ExamError("体检机构不存在或已停用")

    # 同一案件不允许同时存在未完成的体检单（防止重复创建）
    open_order = db.execute(
        select(ExamOrder).where(
            ExamOrder.application_id == application_id,
            ExamOrder.status.in_(("PENDING", "RESULT_ENTERED")),
        )
    ).scalars().first()
    if open_order is not None:
        raise ExamError("该案件已存在进行中的体检单")

    # 校验项目均来自启用字典
    items = db.execute(
        select(ExamItem).where(ExamItem.id.in_(item_ids or []), ExamItem.status == 1)
    ).scalars().all()
    if not items or len(items) != len(set(item_ids)):
        raise ExamError("体检项目无效，请重新选择")

    order = ExamOrder(
        application_id=app.id, center_id=center_id,
        item_ids=sorted(set(item_ids)), created_by=operator_id, status="PENDING",
    )
    db.add(order)
    # 锁定案件：进入待体检，等待结果回流后重新评估
    app.status = "EXAM_REQUIRED"
    db.commit()
    return order


def _order_view(db: Session, o: ExamOrder) -> dict:
    """体检单视图：含机构名、项目明细与结果。"""
    center = db.get(ExamCenter, o.center_id)
    app = db.get(Application, o.application_id)
    items = db.execute(select(ExamItem).where(ExamItem.id.in_(o.item_ids or []))).scalars().all() \
        if o.item_ids else []
    item_names = {i.id: i.name for i in items}
    results = db.execute(
        select(ExamItemResult).where(ExamItemResult.order_id == o.id)).scalars().all()
    result_map = {r.item_id: r for r in results}

    return {
        "id": o.id, "application_id": o.application_id,
        "app_no": app.app_no if app else "",
        "center_id": o.center_id, "center_name": center.name if center else "",
        "status": o.status, "overall_result": o.overall_result,
        "created_at": o.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "result_entered_at": o.result_entered_at.strftime("%Y-%m-%d %H:%M:%S") if o.result_entered_at else None,
        "items": [
            {
                "item_id": iid, "item_name": item_names.get(iid, f"项目#{iid}"),
                "result_value": result_map[iid].result_value if iid in result_map else None,
                "is_abnormal": result_map[iid].is_abnormal if iid in result_map else None,
                "remark": result_map[iid].remark if iid in result_map else None,
            }
            for iid in (o.item_ids or [])
        ],
    }


def list_exam_orders(db: Session, user: User, application_id: int | None = None) -> list[dict]:
    """体检单列表。机构账号仅可见本机构单据。"""
    stmt = select(ExamOrder).order_by(ExamOrder.id.desc())
    if user.role == "exam_center":
        if user.exam_center_id is None:
            return []
        stmt = stmt.where(ExamOrder.center_id == user.exam_center_id)
    if application_id is not None:
        stmt = stmt.where(ExamOrder.application_id == application_id)
    orders = db.execute(stmt).scalars().all()
    return [_order_view(db, o) for o in orders]


def get_exam_order(db: Session, user: User, order_id: int) -> dict:
    """体检单详情（含数据范围校验）。"""
    order = db.get(ExamOrder, order_id)
    if order is None:
        raise ExamError("体检单不存在")
    if user.role == "exam_center" and user.exam_center_id != order.center_id:
        raise ExamError("无权查看该体检单")
    return _order_view(db, order)


def enter_exam_result(db: Session, user: User, order_id: int,
                      overall_result: str, item_results: list[dict]) -> None:
    """机构录入体检结果：校验归属与项目，结果回流触发案件重新评估。"""
    order = db.get(ExamOrder, order_id)
    if order is None:
        raise ExamError("体检单不存在")
    if user.role != "exam_center" or user.exam_center_id != order.center_id:
        raise ExamError("仅本机构可录入该体检单结果")
    if order.status != "PENDING":
        raise ExamError("该体检单结果已录入，请勿重复提交")
    if not overall_result.strip():
        raise ExamError("请填写体检总结论")
    if not item_results:
        raise ExamError("请至少录入一项体检结果")

    # 结果项目必须属于本单选定的项目清单
    item_ids = set(order.item_ids or [])
    for r in item_results:
        if r.get("item_id") not in item_ids:
            raise ExamError("结果包含本单之外的体检项目")
        if not str(r.get("result_value") or "").strip():
            raise ExamError("存在未填写结果值的项目")

    for r in item_results:
        db.add(ExamItemResult(
            order_id=order.id, item_id=r["item_id"],
            result_value=str(r["result_value"]).strip(),
            is_abnormal=1 if r.get("is_abnormal") else 0,
            remark=(r.get("remark") or None),
        ))
    order.status = "RESULT_ENTERED"
    order.overall_result = overall_result.strip()
    order.result_entered_at = datetime.now()

    # 结果回流：案件重新进入智能核保评估（携体检资料，供核保员参考）
    app = db.get(Application, order.application_id)
    app.status = "AUTO_UNDERWRITING"
    db.commit()

    # from_exam=True：跳过体检类规则，避免体检后再次被要求体检
    from app.services.underwriting import run_auto_underwriting
    run_auto_underwriting(db, app.id, from_exam=True)

    # 评估完成后本单职责结束：无论出结论还是再转人工/体检，均置为 DONE
    order = db.get(ExamOrder, order_id)
    order.status = "DONE"
    db.commit()
