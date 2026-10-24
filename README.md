# 医疗保险核保系统

对投保申请进行健康告知审核与风险评估：智能核保规则引擎自动评估，复杂案件转人工核保，支持体检管理、复核、复议与统计导出。

## 技术栈

| 层 | 技术 |
| --- | --- |
| 前端 | Vue 3 + Vite + TypeScript + Element Plus（zh-cn）+ TailwindCSS + ECharts |
| 后端 | FastAPI + SQLAlchemy 2.x + Alembic + Celery（可选） |
| 数据库 | MySQL 8（开发默认 SQLite，无需本地装库） |
| 认证 | JWT + RBAC（客户 / 核保员 / 体检机构 / 核保主管 / 管理员） |

## 快速开始

### 本地开发

```bash
# 后端（端口 18080；本机 8000/8001 被系统保留故用此端口）
cd backend
python -m venv ../.venv          # 首次
../.venv/Scripts/pip install -r requirements.txt
../.venv/Scripts/alembic upgrade head
../.venv/Scripts/python -m scripts.init_users
../.venv/Scripts/python -m uvicorn app.main:app --port 18080

# 前端（端口 5173，已配置 /api 代理到 18080）
cd frontend
npm install
npm run dev
```

### Docker Compose（MySQL + Redis + 后端 + 前端）

```bash
docker compose up -d --build
# 前端 http://localhost:8080 ，后端 http://localhost:18080/docs
```

### 测试

```bash
cd backend
../.venv/Scripts/python -m pytest tests/
```

## 预置账号（密码均为 `Init@123456`）

| 账号 | 角色 | 说明 |
| --- | --- | --- |
| admin | 管理员 | 险种 / 问卷 / 规则 / 体检字典维护 |
| customer01 | 客户 | 投保、查结论、申请复议 |
| underwriter01 | 核保员 | 人工核保、体检开单 |
| examcenter01 | 体检机构 | 录入本机构体检结果 |
| supervisor01 | 核保主管 | 复核、复议处理 |

## 目录结构

```
backend/            FastAPI 后端（app/ 下分 api/services/models/rules/tasks）
frontend/           Vue3 前端（src/views 按角色分目录）
docs/               PRD、技术方案、开发进度、测试报告
docker-compose.yml  一键编排
```

## 文档索引

| 文档 | 说明 |
| --- | --- |
| [docs/PRD.md](docs/PRD.md) | 产品需求：业务流程、角色权限、功能与非功能需求 |
| [docs/技术方案.md](docs/技术方案.md) | 架构、数据库设计、API 设计 |
| [docs/开发进度.md](docs/开发进度.md) | 里程碑进度与下一步计划 |
| [docs/测试报告.md](docs/测试报告.md) | 每次测试的记录与缺陷修复 |
