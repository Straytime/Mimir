# Mimir

AI 驱动的深度研究平台，将用户提问转化为结构化、带引用的研究报告——端到端全链路。

**已上线生产环境**，部署于 Railway（API）和 Vercel（Web）。

## 功能概览

1. **澄清** — 通过自由文本或选择题（15 秒自动提交计时器）追问，收窄研究范围。
2. **需求分析** — 从澄清后的提问中提取结构化需求。
3. **规划与搜集** — 显式 planner agent loop 调度并行 collector 子任务，执行网页搜索、页面抓取与摘要总结。
4. **去重合并** — 去重来源并规范化引用。
5. **大纲与撰写** — writer agent loop 按章节撰写报告，可选在 E2B 沙箱中执行 Python 进行数据分析。
6. **交付** — 导出完成的报告为可下载的 Markdown、PDF 和 ZIP 制品。
7. **修订** — 接受用户反馈，重新运行 writer 优化已交付报告。

整个流程通过 SSE 向浏览器实时推送进度。

## 架构

```text
Browser ──SSE/REST──▸ FastAPI (Railway)
                          │
                          ├─▸ PostgreSQL (Railway)
                          ├─▸ 智谱 LLM API
                          ├─▸ 智谱 Web Search API
                          ├─▸ Jina Reader（网页抓取）
                          └─▸ E2B Sandbox（代码执行）
```

核心约束：

- 不使用 LangChain / LangGraph — 显式状态机 + 显式编排器
- 契约优先、TDD 开发
- 全局同一时刻只允许一个活动研究任务
- 仅使用 SSE 流式推送，不使用 WebSocket
- `task_token` 仅存于内存——断连即放弃任务

## 仓库结构

```
apps/web/            Next.js App Router 前端
services/api/        FastAPI 后端（非 pnpm workspace 成员，使用 uv 管理）
packages/contracts/  共享 TypeScript 类型定义（TaskSnapshot、EventEnvelope 等）
docs/                source-of-truth 设计与实施文档
scripts/             仓库级自动化脚本
```

### 后端分层 (`services/api/app/`)

```
api/              FastAPI 路由、请求/响应序列化
application/      编排器、服务、DTO、prompt 构建、端口定义
domain/           领域模型、枚举、状态机
infrastructure/   适配器实现（LLM、搜索、抓取、沙箱、SSE、数据库）
core/             配置、JSON 工具、ID 生成
```

## 技术栈

### 前端

- Next.js (App Router)、React 19、TypeScript
- Tailwind CSS 自定义工业风设计系统（详见 `docs/DESIGN.md`）
- react-markdown + rehype-sanitize
- Vitest、Testing Library、Playwright

### 后端

- Python 3.12+、FastAPI、Pydantic v2
- SQLAlchemy 2.0 + Alembic（PostgreSQL）
- httpx、智谱官方 SDK
- pytest、pytest-asyncio、respx

## 快速开始

### 前置条件

- Docker（用于本地 PostgreSQL）
- [uv](https://docs.astral.sh/uv/)（Python 包管理器）
- [pnpm](https://pnpm.io/)（Node 包管理器）

### 一键启动

```bash
# 安装依赖
pnpm install
cd services/api && uv sync --group dev && cd ../..

# 启动全部服务（PostgreSQL + 迁移 + API + Web）
./scripts/dev.sh
```

启动后：

| 服务 | 地址 |
|------|------|
| Web  | http://localhost:3000 |
| API  | http://localhost:8000 |
| DB   | postgresql://postgres@localhost:5432/postgres |

默认 provider 模式为 `stub`——本地开发无需 API 密钥。

```bash
./scripts/dev.sh migrate   # 仅运行数据库迁移
./scripts/dev.sh stop      # 停止 PostgreSQL
docker compose down -v     # 停止 PostgreSQL 并清除数据
```

## Provider 模式

后端默认对所有外部服务使用确定性本地 stub。通过环境变量切换为真实 provider：

| 变量 | 说明 |
|------|------|
| `MIMIR_PROVIDER_MODE=stub\|real` | 全局默认，控制所有 adapter |
| `MIMIR_LLM_PROVIDER_MODE` | 单独覆盖智谱 LLM |
| `MIMIR_WEB_SEARCH_PROVIDER_MODE` | 单独覆盖智谱 web search |
| `MIMIR_WEB_FETCH_PROVIDER_MODE` | 单独覆盖 Jina web fetch |
| `MIMIR_E2B_PROVIDER_MODE` | 单独覆盖 E2B sandbox |

真实模式需要 `ZHIPU_API_KEY`、`JINA_API_KEY` 和/或 `E2B_API_KEY`。详见 [`services/api/.env.example`](services/api/.env.example)。

## 常用命令

### 后端 (`services/api`)

```bash
cd services/api
uv sync --group dev                          # 安装依赖
uv run --group dev pytest tests/unit         # 单元测试
uv run --group dev pytest tests/contract     # 契约测试
uv run --group dev pytest tests/integration  # 集成测试（需要 PostgreSQL）
uv run alembic upgrade head                  # 运行数据库迁移
```

### 前端 (`apps/web`)

```bash
cd apps/web
pnpm dev              # 开发服务器
pnpm typecheck        # TypeScript 类型检查
pnpm lint             # ESLint
pnpm test:unit        # 单元测试
pnpm test:contract    # 契约测试
pnpm test:component   # 组件测试
pnpm test:e2e         # Playwright e2e（需先安装 chromium: pnpm exec playwright install chromium）
```

## 生产部署

| 组件 | 平台 | 说明 |
|------|------|------|
| `apps/web` | Vercel | Next.js，从 `main` 分支自动部署 |
| `services/api` | Railway | FastAPI + PostgreSQL + Volume（制品存储） |

完整部署合同见 [`docs/Deploy_Contract.md`](docs/Deploy_Contract.md)。

## 文档索引

| 文档 | 说明 |
|------|------|
| [`docs/Architecture.md`](docs/Architecture.md) | 系统架构、状态机、Schema、API 契约 |
| [`docs/DESIGN.md`](docs/DESIGN.md) | 前端设计系统——"The Kinetic Monolith" |
| [`docs/OpenAPI_v1.md`](docs/OpenAPI_v1.md) | v1 API 契约与 SSE 事件规范 |
| [`docs/Deploy_Contract.md`](docs/Deploy_Contract.md) | Vercel / Railway 部署合同 |
| [`docs/Frontend_IA.md`](docs/Frontend_IA.md) | 前端信息架构 |
| [`docs/Mimir_v1.0.0_prd_0.3.md`](docs/Mimir_v1.0.0_prd_0.3.md) | 产品需求文档 |

## 许可证

私有仓库，保留所有权利。
