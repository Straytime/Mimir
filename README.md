# Mimir

AI-powered deep research assistant — 从用户提问到结构化研究报告的全链路产品。

## 项目当前状态

**M0 ~ M4 实施已完成，R1-001 真实 provider adapter 已接线，仓库进入发布前工程化收尾阶段。**

所有里程碑交付物已落地并通过自动化回归与人工 smoke 验证：

| 里程碑 | 内容 | 状态 |
| --- | --- | --- |
| M0 | 契约与基础设施（monorepo 骨架、contracts、测试基础设施） | ✅ 完成 |
| M1 | 任务框架（创建任务、SSE、heartbeat、disconnect、终止态） | ✅ 完成 |
| M2 | 需求阶段（natural / options 澄清、15s 倒计时、需求分析） | ✅ 完成 |
| M3 | 搜集引擎（planner、collector、summary、barrier、source merge） | ✅ 完成 |
| M4 | 输出引擎（outline、writer、artifact、下载、feedback revision、cleanup） | ✅ 完成 |
| R1-001 | 真实 provider adapter（Zhipu LLM SDK、web_search HTTP、web_fetch HTTP） | ✅ 完成 |

当前阶段的工作口径是**发布前工程化收尾**（Release Engineering），聚焦于：
- 仓库级文档收敛与规范化
- 本地开发体验完善（一条命令拉起联调环境）
- 真实 provider 本地联调验证
- 静态检查门禁（ruff、mypy、ESLint flat config）
- 部署配置与 CI pipeline

## 仓库结构

```text
Mimir/
├─ apps/
│  └─ web/                    # Next.js App Router 前端
├─ services/
│  └─ api/                    # FastAPI 后端
├─ packages/
│  └─ contracts/              # 共享 JS/TS 契约类型
├─ docs/                      # source-of-truth 设计与实施文档
└─ scripts/                   # 仓库级自动化脚本
```

### 各目录职责

- **`apps/web`** — Next.js App Router + TailwindCSS + shadcn/ui 前端；负责研究输入、澄清交互、流式事件渲染、报告展示、下载与反馈。不承担业务编排、prompt 拼接或数据持久化。
- **`services/api`** — FastAPI + Pydantic v2 后端；采用分层架构（`api` / `application` / `domain` / `infrastructure` / `core`），驱动 Task / Revision / SubTask / Event 生命周期，管理 LLM、web_search、web_fetch、E2B 等外部 adapter。
- **`packages/contracts`** — 前后端共享的 TypeScript 类型定义（`TaskSnapshot`、`EventEnvelope` 等）。前端通过 workspace 依赖引入，后端通过 Python domain schemas 保持语义一致。
- **`docs`** — 架构、API、TDD 计划、前端 IA、实施总控与执行日志。所有行为变更必须先更新文档。
- **`scripts`** — 仓库级自动化（预留）。

## 技术栈

### 前端
- Next.js (App Router), React 19, TypeScript
- TailwindCSS, shadcn/ui
- react-markdown + rehype-sanitize（安全 markdown 渲染）
- Vitest + Testing Library + Playwright
- MSW（HTTP mock）

### 后端
- Python 3.12+, FastAPI, Pydantic v2
- SQLAlchemy 2.0 + Alembic（PostgreSQL）
- httpx（HTTP 客户端）
- 智谱官方 SDK（LLM）、原生 HTTP（web_search / web_fetch）
- pytest + pytest-asyncio + respx

### 核心约束
- 不使用 LangChain / LangGraph 或其他 Agent 编排框架
- 显式状态机 + 显式编排器
- 全局同一时刻只允许一个活动研究任务
- SSE 单向流式，不使用 WebSocket
- 前端不缓存 `task_token` 到 localStorage，断连即放弃任务
- contract-first + TDD 开发方式

## Provider Mode

后端默认以 `stub` 模式运行，所有外部依赖使用 deterministic local stub / scripted fake，适用于开发与测试。

| 环境变量 | 说明 |
| --- | --- |
| `MIMIR_PROVIDER_MODE=stub` | 全局默认，所有 adapter 使用本地 stub |
| `MIMIR_PROVIDER_MODE=real` | 切换 LLM / web_search / web_fetch / E2B 为真实 provider |
| `MIMIR_LLM_PROVIDER_MODE` | 单独覆盖 LLM adapter 模式 |
| `MIMIR_WEB_SEARCH_PROVIDER_MODE` | 单独覆盖 web_search adapter 模式 |
| `MIMIR_WEB_FETCH_PROVIDER_MODE` | 单独覆盖 web_fetch adapter 模式 |
| `MIMIR_E2B_PROVIDER_MODE` | 单独覆盖 E2B sandbox adapter 模式 |

`real` 模式下，LLM / `web_search` 需要 `ZHIPU_API_KEY`，`web_fetch` 需要 `JINA_API_KEY`，E2B sandbox 需要 `E2B_API_KEY`。详见 [`services/api/.env.example`](services/api/.env.example)。

使用 `./scripts/dev.sh` 启动本地联调时，provider 模式、数据库地址与密钥都读取当前 shell 环境；脚本不再强制覆盖为 `stub`。因此本地 real smoke 应先在 shell 中导出 `MIMIR_PROVIDER_MODE`、各 provider override、可选的 `MIMIR_DATABASE_URL` 以及 `ZHIPU_API_KEY` / `JINA_API_KEY` / `E2B_API_KEY`，再执行脚本。

## 本地联调（一条命令）

从仓库根目录启动完整本地开发环境：

```bash
# 前置条件：docker, uv, pnpm
pnpm install                        # 首次：安装 JS 依赖
cd services/api && uv sync --group dev && cd ../..  # 首次：安装 Python 依赖

# 启动（PostgreSQL + migrate + API + Web）
./scripts/dev.sh

# 或通过 pnpm
pnpm dev
```

启动后：
- Web: http://localhost:3000
- API: http://localhost:8000
- DB: `postgresql://postgres@localhost:5432/postgres`
- Provider 模式: `stub`（不需要真实密钥）

```bash
# 仅运行迁移
./scripts/dev.sh migrate

# 停止 PostgreSQL
./scripts/dev.sh stop

# 停止 PostgreSQL 并清除数据
docker compose down -v
```

> `services/api` 不是 pnpm workspace 的一部分，后端工具链使用 `uv` 独立管理。

## 常用命令

### 后端 (`services/api`)

```bash
cd services/api

# 依赖安装
uv sync --group dev

# 启动 API 服务器（需本地 PostgreSQL）
uv run --group dev uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# 运行测试
uv run --group dev pytest tests/unit
uv run --group dev pytest tests/contract
uv run --group dev pytest tests/integration
uv run --group dev pytest tests/unit tests/contract tests/integration  # 全量

# 数据库迁移（需本地 PostgreSQL）
uv run alembic upgrade head
```

### 前端 (`apps/web`)

```bash
cd apps/web

# 开发服务器（读取 .env.local 中的 NEXT_PUBLIC_API_BASE_URL）
pnpm dev

# 类型检查与 lint
pnpm typecheck
pnpm lint

# 运行测试
pnpm test:unit
pnpm test:contract
pnpm test:component
pnpm test:integration
pnpm test:e2e          # 需要先安装 Chromium: pnpm exec playwright install chromium
```

### 根目录

```bash
# 安装所有 JS workspace 依赖
pnpm install
```

## 文档索引

| 文档 | 说明 |
| --- | --- |
| [`docs/Architecture.md`](docs/Architecture.md) | 架构设计（技术选型、状态机、Schema、API 契约、数据存储） |
| [`docs/OpenAPI_v1.md`](docs/OpenAPI_v1.md) | v1 API 契约与 SSE 事件规范 |
| [`docs/Backend_TDD_Plan.md`](docs/Backend_TDD_Plan.md) | 后端 TDD 分阶段计划 |
| [`docs/Frontend_IA.md`](docs/Frontend_IA.md) | 前端信息架构与交互规范 |
| [`docs/Frontend_TDD_Plan.md`](docs/Frontend_TDD_Plan.md) | 前端 TDD 分阶段计划 |
| [`docs/Implementation_Playbook.md`](docs/Implementation_Playbook.md) | 实施总控（任务包规范、并行策略、回报验收） |
| [`docs/Execution_Log.md`](docs/Execution_Log.md) | 全局实施历史（append-only） |

> `docs/` 是 source of truth。行为变更必须先更新文档，再写测试，再实现。

## 当前已知非阻塞事项

- `pnpm lint` 使用 ESLint 9 legacy `.eslintrc` 兼容模式，会打印 deprecation warning（lint 本身通过）
- `ruff check` 与 `mypy` 在后端尚未作为门禁启用
- `pnpm test:e2e` 与后端 integration tests 依赖本机 PostgreSQL 与 Chromium
- 本地联调入口 `./scripts/dev.sh` 已提供，依赖 Docker（PostgreSQL）+ uv + pnpm
- E2B sandbox 已具备真实 adapter baseline；完整 writer 实战联调仍待后续独立 smoke
- 浏览器 e2e 通过 test-only `__MIMIR_TEST_RUNTIME__ / __MIMIR_TEST_STORE__` 注入驱动

## 发布前工程化收尾 — 下一步方向

以下工作属于 Release Engineering 阶段，不应混入新功能实现：

1. **仓库文档收敛** — README / AGENTS 更新、commit message 规范落地
2. **本地开发体验** — `docker-compose` 或等价一键联调入口
3. **真实 provider 联调** — 受控样本 smoke、模型稳定性收敛
4. **静态检查门禁** — ruff + mypy 后端门禁、ESLint flat config 迁移
5. **CI pipeline** — GitHub Actions 全量回归
6. **部署配置** — Railway / Vercel 环境变量模板、生产 CORS 白名单
7. **E2B 真实 adapter** — sandbox 真实接线与 artifact store 对接
8. **test-only surface 收敛** — 浏览器注入策略统一到 e2e harness 层
