"""Celery 应用与智能核保任务

默认配置下评估同步执行（见 settings.use_celery），接入 Redis 后置 True 即切换异步。
任务内自建数据库会话，与请求会话解耦。
"""

from celery import Celery

from app.core.config import settings

# broker/backend 地址由配置提供；未启用 Celery 时仅定义，不发起连接
celery_app = Celery(
    "underwriting",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)


@celery_app.task(name="auto_underwrite")
def auto_underwrite(app_id: int) -> None:
    """异步智能核保评估任务：加载全新会话执行评估。"""
    from app.db.session import SessionLocal
    from app.services.underwriting import run_auto_underwriting

    db = SessionLocal()
    try:
        run_auto_underwriting(db, app_id)
    finally:
        db.close()
