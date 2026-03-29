# Repository Guidelines

## 当前仓库阶段

Mimir 是一个深度研究平台（已上线，部署在 Railway）。M0 ~ M4 实施阶段、Release Engineering 均已完成。当前处于**生产调优与 Bug Fix** 阶段。

在此阶段内：

- 不引入新的业务功能或新的 API 端点
- 工作口径：prompt 调优、生产 bug 修复、可观测性增强、PDF 导出质量、provider 适配
- 任何架构性变更需要显式提出并经 leader 放行

## 执行纪律

### agent 规则
- 本项目由 `master-agent` 主控、规划、设定任务包，通过创建 subagent 作为 `execute-agent`的方式，执行任务包进行具体实施。
- `master-agent` 应当始终站在高维宏观视角，不陷入细节，仅负责调度、分析、决策和验收，绝不进行任何实施行为，保持自身上下文简洁。
- 当前默认采用单线程串行开发，同一时刻只推进一个活跃任务包。

所有行为变更必须遵循：
1. **docs-first** — 先更新相关文档
2. **tests-first** — 再写失败测试
3. **implementation** — 最后实现代码

如果在实现过程中发现文档与代码不一致，必须先停下并修正文档，不得自行发明新契约。
#### 任务包下发原则
1. 单次只下发一个”足够小且能验收”的任务包，不下发大而泛的”把某件事做完”。
2. 每个任务包都必须自包含。
3. 每个 Architecture 阶段结束后，都要做一次阶段收口任务，而不是无限连续编码。

任务包信息：
1. `目标`
2. `输入文档`
3. `范围`
4. `非目标`
5. `必须先写的测试`
6. `实现约束`
7. `交付物`
8. `验收标准`
9. `回报格式`

一个好任务包应满足：
- 清晰明确的目标
- 实施者能在可控回合数内闭环
- 不需要实施者自行猜测边界
- 验收标准是”可证明的”，不是”差不多”

#### 任务包执行原则
1. 严格按照任务包内容进行实施和执行
2. 执行完成后，按任务包要求的格式进行回报输出
3. **执行完成后，必须追加 `docs/execution_log.md`**

#### 任务包验收
1. 是否严格在任务包范围内。
2. 是否先有测试，再有实现。
3. 是否满足对应阶段的 DoD。
4. 是否引入了文档漂移

如果任务不通过，应重新生成一个更小的返工任务包，明确写：
- 哪些点未达标
- 本次只修什么
- 不允许顺手扩展什么


### Git 工作树纪律

- **默认禁止直接在 `main` 分支修改任何文件**
- 所有变更必须在已有非 `main` 分支上进行，或先创建新分支后再修改
- 只有用户明确要求”直接在 `main` 变更”时，才允许绕过上述限制
- **任何 `git push` 都必须由用户显式指示后才能执行**
- 未得到用户明确指示时，只允许停留在工作树变更状态，不自行提交或推送

## 项目结构与架构

### 仓库布局

- `apps/web/` — Next.js App Router 前端
- `services/api/` — FastAPI 后端（不是 pnpm workspace 成员，后端工具链用 `uv`）
- `packages/contracts/` — 共享 JS/TS 契约类型（单文件 `src/index.ts`）
- `docs/` — source-of-truth 设计与实施文档（含 PRD `Mimir_v1.0.0_prd_0.3.md`）
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

### 后端分层架构（`services/api/app/`）

```
api/            → FastAPI 路由、请求/响应序列化
application/    → 编排器、服务、DTO、prompt 构建、端口定义
  dto/          → 不可变 frozen dataclass（InvocationProfile, PromptBundle, WriterDecision 等）
  ports/        → Protocol 接口（PlannerAgent, WriterAgent, OutlineAgent 等）
  prompts/      → 各阶段 LLM prompt 构建函数
  services/     → 业务编排（CollectionOrchestrator, DeliveryOrchestrator）
domain/         → 领域模型、枚举、状态机
infrastructure/ → 适配器实现
  llm/          → ZhipuChatClient（统一 LLM 调用层）
  research/     → Planner/Collector/Summary 的 Zhipu 适配器
  delivery/     → Outline/Writer 适配器、E2B 沙箱、PDF 导出
  streaming/    → SSE broker
  db/           → SQLAlchemy repository
core/           → Settings、JSON 工具、ID 生成
```

### Agent Loop 模式

Planner 和 Writer 都采用 agent loop 模式（与 PRD func_7 / func_13 定义一致）：

- **Planner loop**：`CollectionOrchestrator` 多轮调用 `PlannerAgent.plan()` → 发出 `collect_agent` tool_calls → 执行 collector 子任务 → summary → 将结果作为 transcript 回传下一轮 → 直到 planner 输出完成通知
- **Writer loop**：`DeliveryOrchestrator._run_writer_loop()` 多轮调用 `WriterAgent.write()` → 如果返回 `python_interpreter` tool_calls → 在 E2B sandbox 执行 → 将 tool result 作为 transcript 回传下一轮 → 直到无 tool_calls（`writer_max_rounds` 上限保护，默认 5）

两者都设置 `thinking=True, clear_thinking=False`（有利于 Zhipu API cache 命中），transcript 通过 `PromptBundle.transcript` 传递完整 agent loop 历史。

### Provider Mode

- 默认 `MIMIR_PROVIDER_MODE=stub`，所有外部 adapter 使用 deterministic local stub
- `MIMIR_PROVIDER_MODE=real` 切换到真实 provider
- 可通过 `MIMIR_LLM_PROVIDER_MODE` / `MIMIR_WEB_SEARCH_PROVIDER_MODE` / `MIMIR_WEB_FETCH_PROVIDER_MODE` / `MIMIR_E2B_PROVIDER_MODE` 单独覆盖
- 真实 provider：Zhipu LLM SDK、Zhipu web_search HTTP、Jina Reader web_fetch、E2B sandbox
- stub 是 CI 和日常开发的默认路径；切换到 real 前必须确认环境变量与 API key 已就绪
- 详见 [`services/api/.env.example`](services/api/.env.example)

### Prompt 与 PRD 对齐原则

所有 LLM 调用阶段的 system_prompt 和 user_prompt 必须与 PRD（`docs/Mimir_v1.0.0_prd_0.3.md`）中对应 func 的定义**完全一致**（包括加粗标记、标点、示例文本）。适配器层不得在 user_prompt 末尾追加额外的 JSON 格式指令或改变输出格式要求。

### Task 生命周期

创建 → 澄清 → 需求分析 → planner → collector → summary → merge → outline → writer → delivery → feedback revision → cleanup

每个阶段的 prompt 定义见 PRD（`docs/Mimir_v1.0.0_prd_0.3.md`），对应 func_5 ~ func_14。

## 构建、测试与开发命令

### 后端 (`services/api`)

```bash
cd services/api
uv sync --group dev                                             # 安装依赖
uv run --group dev pytest tests/unit                            # 单元测试
uv run --group dev pytest tests/contract                        # 契约测试
uv run --group dev pytest tests/integration                     # 集成测试（需本地 PostgreSQL）
uv run --group dev pytest tests/unit/infrastructure/test_zhipu_writer_agent.py  # 运行单个测试文件
uv run --group dev pytest tests/unit -k "test_planner_prompt"   # 按名称过滤运行
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
- DTO 使用 frozen dataclass（`@dataclass(frozen=True, slots=True)`）

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

### 提交权限前置条件

- commit 规范只在**用户已明确要求执行 commit**时适用
- 未经用户同步和指示，不得因为“修好了”或“准备发版”而自行提交
- `push` 同样需要单独的用户明确指示，不能默认在 commit 后自动执行

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
- PDF 导出使用 allowlist HTML 安全过滤（阻止 script/iframe/事件处理器，只允许 data:image/png base64 图片）

## Production 排查

### Production 只读排查路径

- 需要查看 production 原始任务数据时，优先使用 Railway 平台内的只读路径，不要先凭本机缓存、浏览器状态或非权威 DB 连接下结论
- 固定顺序：
  - `railway status --json`
  - `railway variable list --service mimir-api --environment production --json`
  - `railway ssh --service mimir-api --environment production`
  - `railway ssh --service Postgres --environment production`
- `mimir-api` 容器内的权威查询方式：
  - 使用 `/app/.venv/bin/python`
  - 通过 `from app.core.config import Settings; Settings.from_env().database_url` 解析运行时真实 DB URL
  - 再用 SQLAlchemy 做只读查询
- `Postgres` 容器内的交叉确认方式：
  - 使用 `psql -U postgres -d railway -P pager=off`
  - 只运行只读 SQL，用于确认 `research_tasks`、`task_events`、`agent_runs`、`task_tool_calls`、`artifacts`
- `railway connect` 只作为可选辅助路径：
  - 它依赖本机 `psql`
  - 若本机缺少 `psql`，不要把 `railway connect` 失败误判为 production DB 不可达
- production 数据是短期存活的：
  - delivered task 默认 `30` 分钟后进入过期/cleanup 路径
  - cleanup 会物理删除 `research_tasks` 及其级联表记录与 artifacts
  - 因此排查 writer / delivery 正文问题时，必须在 task 仍存活时立即采样原始数据
- 在拿到存活 task 的 `agent_runs.content_text`、最终 delivery 存储值，以及尾部 `task_events` 之前，不对 writer 正文语义、正文截断或正文拼装问题下实现结论

### Production 失败任务快速排查约定

- 对 production 活体失败任务做纯排查时，直接执行排查，不先发任务包；只有进入 docs / tests / implementation 变更时才切回任务包模式
- 失败任务的采样顺序固定为：
  - 先抓 `task_events / agent_runs / task_tool_calls / artifacts / research_tasks`
  - 再抓 Railway 应用日志
  - 最后才做实现层推断
- `railway logs --json` 当前返回的是 **NDJSON**，不是 JSON array：
  - 先落盘到 `/tmp/*.ndjson`
  - 再用 Python 按行 `json.loads(line)` 解析
  - 不要直接对整文件 `json.load(...)`
- 对 `mimir-api` 容器执行复杂查询时，优先使用：
  - `railway ssh --service mimir-api --environment production`
  - 连进去后再运行交互式 `python - <<'PY'`
- 对 `Postgres` 容器执行复杂 SQL 时，优先使用：
  - `railway ssh --service Postgres --environment production`
  - 连进去后再运行交互式 `psql -U postgres -d railway -P pager=off`
- 避免把复杂 heredoc、多层引号、包含 SQL/Python 代码的长命令直接塞进：
  - `railway ssh ... COMMAND`
  - 这类形式很容易被 shell quoting 打断，浪费活体任务窗口
- 若任务已被 cleanup 删除：
  - 立即停止继续尝试 DB 回补
  - 改为只基于已落盘的 Railway 日志做失败时序还原
  - 并明确说明“原始 DB 记录已丢失，当前无法进一步定界到 content/tool/result 级别”
- 若问题发生在 `delivery` 末段：
  - 优先先区分是 `writer`、`export(zip/pdf)`、`artifact_store.put` 还是 token/download 路径
  - 不要在尚未区分失败子阶段前笼统归因为”报告生成失败”
