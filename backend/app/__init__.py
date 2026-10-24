"""后端项目说明

医疗保险核保系统后端，基于 FastAPI + SQLAlchemy。
启动方式（需在 .venv 虚拟环境中）：
    uvicorn app.main:app --reload --port 8000
"""

from pathlib import Path

# 项目根目录（backend/ 的父目录）
BASE_DIR = Path(__file__).resolve().parent
