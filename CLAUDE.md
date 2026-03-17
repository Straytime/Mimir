# Repository Guidelines

## 当前仓库阶段

Mimir 仓库的 M0 ~ M4 实施阶段已全部完成，R1-001 真实 provider adapter 已接线。当前处于**发布前工程化收尾（Release Engineering）**阶段。

在此阶段内：

- 不引入新的业务功能或新的 API 端点
- 不修改已固化的设计文档结论（Architecture / OpenAPI / IA / TDD Plan）
- 工作口径限定为：文档收敛、开发体验、静态检查、CI、部署配置、真实 provider 联调验证
- 任何超出上述口径的工作需要显式提出并经 leader 放行

## 执行纪律

### 流程顺序

所有行为变更必须遵循：

1. **docs-first** — 先更新相关文档
2. **tests-first** — 再写失败测试
3. **implementation** — 最后实现代码

如果在实现过程中发现文档与代码不一致，必须先停下并修正文档，不得自行发明新契约。

### Execution Log 强制维护

- `docs/Execution_Log.md` 是全局唯一的实施历史文档
- **每个开发 session 完成后，必须先更新 `docs/Execution_Log.md`，再提交 session 回报**
- leader 放行下一任务包的依据是：`docs/Execution_Log.md` 最新记录 + session 完成回报
- 当前默认采用单线程串行开发，同一时刻只推进一个活跃任务包

### 任务包规范

参照 [`docs/Implementation_Playbook.md`](docs/Implementation_Playbook.md)：
- 单次只做一个"足够小且能验收"的任务包
- 每个任务包必须包含：目标、输入文档、范围、非目标、实现约束、交付物、验收标准、回报格式
- 不接受"先把某端做完"或"按文档全部实现这一阶段"这类大而泛的指令

## 项目结构与架构约束

### 仓库布局

- `apps/web/` — Next.js App Router 前端
- `services/api/` — FastAPI 后端（不是 pnpm workspace 成员，后端工具链用 `uv`）
- `packages/contracts/` — 共享 JS/TS 契约类型
- `docs/` — source-of-truth 设计与实施文档
- `scripts/` — 仓库级自动化

### 架构约束（不可违背）

- 不引入 LangChain、LangGraph 或其他 Agent 编排框架
- 使用显式状态机、显式编排器、contract-first API
- 后端采用 port / adapter 架构，外部集成通过明确端口隔离
- 前端只消费后端结构化契约，不解析原始 LLM 输出
- 前端不缓存 `task_token` 到 localStorage / IndexedDB
- SSE 断连即放弃任务，v1 不支持刷新恢复或 SSE 自动重连
- 全局同一时刻只允许一个活动研究任务
- 保留文档定义的契约名称：`TaskSnapshot`、`EventEnvelope`、`task_token`、`access_token`、`available_actions` 等

### Provider Mode

- 默认 `MIMIR_PROVIDER_MODE=stub`，所有外部 adapter 使用 deterministic local stub
- `MIMIR_PROVIDER_MODE=real` 切换到真实 provider（需 `ZHIPU_API_KEY`）
- 可通过 `MIMIR_LLM_PROVIDER_MODE` / `MIMIR_WEB_SEARCH_PROVIDER_MODE` / `MIMIR_WEB_FETCH_PROVIDER_MODE` 单独覆盖
- stub 是 CI 和日常开发的默认路径；切换到 real 前必须确认环境变量与 API key 已就绪
- 详见 [`services/api/.env.example`](services/api/.env.example)

### 前后端已实现边界

**后端（services/api）已完成：**
- `POST /api/v1/tasks` / `GET /api/v1/tasks/{task_id}` / `GET /api/v1/tasks/{task_id}/events`
- `POST /api/v1/tasks/{task_id}/heartbeat` / `POST /api/v1/tasks/{task_id}/disconnect`
- `POST /api/v1/tasks/{task_id}/clarification` / `POST /api/v1/tasks/{task_id}/feedback`
- `GET /api/v1/tasks/{task_id}/downloads/markdown.zip` / `GET /api/v1/tasks/{task_id}/downloads/report.pdf`
- `GET /api/v1/tasks/{task_id}/artifacts/{artifact_id}`
- 完整 Task 生命周期：创建 -> 澄清 -> 需求分析 -> planner -> collector -> summary -> merge -> outline -> writer -> delivery -> feedback revision -> cleanup
- SSE broker、task_events 持久化、connect deadline、heartbeat timeout、补偿一致性 cleanup
- 真实 provider adapter：Zhipu LLM SDK、web_search HTTP、web_fetch HTTP（E2B 仍为 local stub）

**前端（apps/web）已完成：**
- 首页空态 -> 研究输入 -> 创建任务 -> 立即建 SSE
- natural / options 两条澄清路径 + 15s 倒计时
- timeline 透明度（planner / collector / summary / merge / outline）
- report canvas + artifact gallery + 安全 markdown 渲染
- delivery actions（下载按钮、access_token 刷新重试）
- feedback composer + revision 切换 overlay
- heartbeat / disconnect / sendBeacon / 终态 banner
- 移动端分段布局

## 构建、测试与开发命令

### 后端 (`services/api`)

```bash
cd services/api
uv sync --group dev                                             # 安装依赖
uv run --group dev pytest tests/unit                            # 单元测试
uv run --group dev pytest tests/contract                        # 契约测试
uv run --group dev pytest tests/integration                     # 集成测试（需本地 PostgreSQL）
uv run --group dev pytest tests/unit tests/contract tests/integration  # 全量
uv run alembic upgrade head                                     # 数据库迁移
```

静态检查（尚未作为门禁启用）：
- `ruff check` / `ruff format --check`
- `mypy`

### 前端 (`apps/web`)

```bash
cd apps/web
pnpm dev                    # 开发服务器
pnpm typecheck              # TypeScript 类型检查
pnpm lint                   # ESLint
pnpm test:unit              # 单元测试
pnpm test:contract          # 契约测试
pnpm test:component         # 组件测试
pnpm test:integration       # 集成测试
pnpm test:e2e               # Playwright e2e（需 chromium: pnpm exec playwright install chromium）
```

### 根目录

```bash
pnpm install                # 安装所有 JS workspace 依赖
```

从各自的包目录运行命令，不从仓库根目录。前端和后端命令保持独立，不添加隐藏部署拆分的根级 dev server。

## 编码规范

### 命名

- React 组件：`PascalCase`
- Hooks：`useSomething`
- TypeScript 工具与变量：`camelCase`
- Python 模块与函数：`snake_case`

### 目录组织

- 前端采用 feature-based folders（`features/research/...`）
- 后端采用分层模块（`api` / `application` / `domain` / `infrastructure` / `core`）

### 偏好

- 小模块、显式依赖注入、contract-first 变更
- 避免大而全的 god module

## 测试规范

使用 TDD，行为变更时先更新文档再写测试。

测试目录布局：
- `apps/web/tests/{unit,contract,component,integration,e2e}`
- `services/api/tests/{unit,contract,integration}`

CI 必须确定性：避免真实上游服务、真实计时器、隐藏浏览器状态。使用 fakes、fixtures、MSW、respx。

### 前端测试规则

- 使用 scripted SSE fixtures，不依赖浏览器原生重连
- `available_actions`、`status`、`phase` 是 UI action gating 的唯一权威
- `beforeunload`、`pagehide`、`sendBeacon`、倒计时、scroll 行为用可控 mock 和 fake timers

### 后端测试规则

- 使用 fake adapters（LLM / web_search / web_fetch / E2B）
- 覆盖 SSE 事件排序、cleanup、retry policy、Task / Revision 状态流转

## Commit Message 规范

**从本规范生效起，新提交必须使用完整、标准的 commit message。**

历史 commit 不受此规范约束。此规范面向当前及未来提交。

### 格式要求

```
<type>(<scope>): <subject>

<body>

Co-Authored-By: ...（如适用）
```

### 规则

1. **标题行**采用 [Conventional Commits](https://www.conventionalcommits.org/) 风格
   - `type` 常用值：`feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `ci`, `style`
   - `scope` 推荐值：`api`, `web`, `contracts`, `repo`, `docs`, `ci`
   - `subject` 使用英文祈使句，首字母小写，不加句号
2. **标题与正文之间必须有一个空行**
3. **正文**至少说明：
   - 改了什么（what）
   - 为什么改（why）
   - 如何验证的（verification）
4. 单行 fix 或 trivial chore 可以省略正文，但标题必须清晰

### 示例

```
feat(api): add zhipu provider factory

Add provider mode configuration and factory function that builds
stub or real adapters based on MIMIR_PROVIDER_MODE env var.
Real mode requires ZHIPU_API_KEY and fails fast if missing.

Verified: pytest tests/unit/infrastructure/test_provider_factory.py (8 passed)
```

```
docs(repo): refresh README and AGENTS for release engineering phase

Update repository-level docs to reflect M0-M4 completion and
current release engineering scope. Add commit message conventions.

Verified: manual review of all referenced commands and paths
```

## PR 规范

PR 应当：
- 描述行为变更
- 列出更新的文档和契约
- 说明测试覆盖
- UI 和 SSE 变更附截图或 stream trace

## 安全与配置

- 不提交 secrets、tokens 或 `.env` 文件
- `task_token` 只在内存中，不添加浏览器持久化
- 下载和 artifact URL 使用短期 `access_token` 签名
- 所有密钥读取统一收口到 `app/core/config.py`
- `.env` 文件必须在 `.gitignore` 中

## Release Engineering 阶段工作口径

当前阶段可以做：
- 仓库级文档更新与规范化
- 本地开发体验完善（docker-compose / dev script）
- 静态检查门禁启用（ruff / mypy / ESLint flat config）
- CI pipeline 搭建
- 部署配置模板
- 真实 provider 联调验证
- E2B 真实 adapter 接线
- test-only surface 收敛

当前阶段不应做：
- 新增 API 端点或业务功能
- 修改 Architecture / OpenAPI / IA / TDD Plan 的设计结论
- 引入新的 Agent 编排框架或新的外部依赖
- 回退或重写已验收的实现基线
