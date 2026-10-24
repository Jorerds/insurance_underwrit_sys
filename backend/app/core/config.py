"""应用配置模块

集中管理环境相关配置，全部支持通过环境变量覆盖。
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """全局配置项，开发默认值可直接本地运行。"""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # 数据库连接：默认 SQLite 便于开发，生产通过 DATABASE_URL 切换 MySQL
    database_url: str = "sqlite:///./underwriting.db"

    # JWT 配置
    jwt_secret: str = "dev-secret-change-me"  # 生产环境必须替换
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 8

    # 允许跨域的前端来源（开发环境 Vite 默认端口 5173）
    cors_origins: list[str] = ["http://localhost:5173"]

    # Celery 配置：默认同步执行评估（开发/测试免 Redis），接入 Redis 后启用异步
    use_celery: bool = False
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"


settings = Settings()
