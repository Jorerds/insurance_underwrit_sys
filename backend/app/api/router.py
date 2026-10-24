"""API 路由聚合

所有业务模块的路由在此统一挂载，统一前缀 /api/v1。
"""

from fastapi import APIRouter

from app.api import admin, applications, auth, exams, products, reconsider, stats, underwriting

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(products.router)
api_router.include_router(applications.router)
api_router.include_router(underwriting.router)
api_router.include_router(exams.router)
api_router.include_router(reconsider.router)
api_router.include_router(stats.router)
api_router.include_router(admin.router)
