"""FastAPI 应用入口

负责应用装配：中间件、路由、启动时建表。
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.db.session import Base, engine
from app.models import application, exam, product, reconsideration, underwriting, user  # noqa: F401  确保模型注册到 Base.metadata


def create_app() -> FastAPI:
    """应用工厂，便于测试时按需创建实例。"""
    app = FastAPI(title="医疗保险核保系统")

    # 允许前端开发服务跨域访问
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    def init_db():
        # 开发阶段直接建表；后续里程碑引入 Alembic 迁移
        Base.metadata.create_all(bind=engine)

    app.include_router(api_router)
    return app


app = create_app()
