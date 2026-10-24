# 后端镜像：FastAPI + Alembic 迁移 + 预置账号初始化
FROM python:3.13-slim

WORKDIR /app

# 先装依赖，充分利用构建缓存
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 启动时执行迁移、初始化预置账号，再启动服务
CMD ["sh", "-c", "alembic upgrade head && python -m scripts.init_users && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
