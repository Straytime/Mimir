# Mimir Execution Log

`docs/Execution_Log.md` is the single global implementation history for this repository.

## Usage Rules

- Maintain this file as append-only history for completed implementation sessions.
- The repository currently follows single-threaded serial development: only one active task package should be in flight at a time.
- After each development session completes, append a new entry before handing off or requesting the next task package.
- Leader release decisions should use both this log and the per-session completion report.

## Entry Template

Copy the template below for each completed session:

```md
## <Task Package> <Short Title>

- 日期时间: YYYY-MM-DD HH:MM:SS TZ (+offset)
- 任务包编号: <task id>
- session 标识: <session id>
- 目标摘要: <one-paragraph summary>
- 修改文件:
  - <path>
  - <path>
- 测试/验证:
  - 已运行: <commands or checks>
  - 未运行: <tests not run and why>
- 验收结论: <accepted / not accepted + short reason>
- blocker / 风险:
  - <item>
  - <item>
- 下一步建议:
  - <item>
  - <item>
```

## M0-001 Monorepo Skeleton + Contracts Scaffold

- 日期时间: 2026-03-13 19:20:55 CST (+0800) [retrofilled]
- 任务包编号: M0-001
- session 标识: codex-20260313-m0-001-retrofill
- 目标摘要: 建立 monorepo 基础骨架，固定 `apps/web`、`services/api`、`packages/contracts`、`scripts` 目录边界，并为 `packages/contracts` 提供最小入口与职责说明，不进入任何业务实现。
- 修改文件:
  - `.gitignore`
  - `README.md`
  - `package.json`
  - `pnpm-workspace.yaml`
  - `apps/web/README.md`
  - `services/api/README.md`
  - `scripts/README.md`
  - `packages/contracts/README.md`
  - `packages/contracts/package.json`
  - `packages/contracts/src/index.ts`
- 测试/验证:
  - 已运行: `find . -maxdepth 3 -type f | sort`；`find apps services packages scripts -maxdepth 3 \( -type d -o -type f \) | sort`；静态检查 `pnpm-workspace.yaml`、root `package.json`、`packages/contracts/package.json`、`packages/contracts/src/index.ts`、root `README.md`
  - 未运行: `pnpm --version`、`pnpm list -r --depth -1`，因为当时环境中 `pnpm` 尚未安装到 `PATH`
- 验收结论: accepted；目录结构与 `docs/Architecture.md` 一致，`packages/contracts` 的入口与用途明确，且未越界进入 Stage 0 业务脚手架。
- blocker / 风险:
  - 无交付 blocker
  - 当时 `pnpm` 未就绪，后续需要单独做工具链准备
- 下一步建议:
  - 执行 M0-002，补齐实施日志机制与基础工具链状态

## M0-002 Execution Log Bootstrap + Toolchain Readiness

- 日期时间: 2026-03-13 19:20:55 CST (+0800)
- 任务包编号: M0-002
- session 标识: codex-20260313-m0-002-log-bootstrap
- 目标摘要: 建立全局唯一的实施历史文档，回填 M0-001，明确单线程串行开发与 session 日志维护规则，并验证 `pnpm`、`uv` 的当前可用性，在不扩张范围的前提下尽量补齐 `pnpm`。
- 修改文件:
  - `docs/Execution_Log.md`
  - `docs/Implementation_Playbook.md`
  - `AGENTS.md`
- 测试/验证:
  - 已运行: `date '+%Y-%m-%d %H:%M:%S %Z (%z)'`；`command -v pnpm || true`；`command -v uv || true`；`command -v corepack || true`；`corepack --version`；`corepack pnpm --version`；`corepack enable pnpm`；`pnpm --version`；`command -v pnpm`；`uv --version`
  - 未运行: 任何 `uv` 安装动作；按任务约束未尝试安装 `uv`
- 验收结论: accepted；`docs/Execution_Log.md` 已建立且可直接追加，M0-001 已回填为第一条正式记录，串行开发与日志维护规则已写入主控文档，`pnpm` 已可直接调用，`uv` 状态明确为缺失。
- blocker / 风险:
  - `uv` 当前不可用，后续如需要进入 Python 工具链任务，需单独下发工具链准备任务或明确安装决策
- 下一步建议:
  - 在进入 `services/api` Stage 0 前，单独确认是否要安装 `uv`
  - 后续每个实施 session 完成后继续追加本日志

## M0-003 UV Toolchain Readiness

- 日期时间: 2026-03-14 15:42:17 CST (+0800)
- 任务包编号: M0-003
- session 标识: codex-20260314-m0-003-uv-readiness
- 目标摘要: 补齐 backend 开发所需的 `uv` 工具链，优先通过 Homebrew 以最小风险方式完成安装与可调用性验证，不进入 `services/api` 项目初始化或任何 Stage 0 代码工作。
- 修改文件:
  - `README.md`
  - `docs/Execution_Log.md`
- 测试/验证:
  - 已运行: `date '+%Y-%m-%d %H:%M:%S %Z (%z)'`；`command -v uv || true`；`command -v brew || true`；`brew --version`；`brew list --versions uv`；`brew info uv`；`HOMEBREW_NO_AUTO_UPDATE=1 brew install uv`；`command -v uv`；`uv --version`；`uv venv --help`；`uv pip --help`
  - 未运行: 任何 `uv` 虚拟环境创建、`services/api` 初始化、backend Stage 0 测试或脚手架命令
- 验收结论: accepted；`uv` 已安装并可直接调用，要求的三个验收命令全部成功，且本任务未越界进入 backend Stage 0 项目脚手架。
- blocker / 风险:
  - 无当前 blocker
  - `brew list --versions uv` 与 `brew info uv` 在沙箱内会因 Homebrew cache 写权限失败，需要提权后才能完整执行或安装
- 下一步建议:
  - 可在后续独立任务包中进入 `services/api` Stage 0，使用 `uv` 作为默认 Python 工具链

## M0-004 Backend Stage 0 Harness

- 日期时间: 2026-03-14 16:01:22 CST (+0800)
- 任务包编号: M0-004
- session 标识: codex-20260314-m0-004-backend-stage0-harness
- 目标摘要: 按 `docs/Backend_TDD_Plan.md` 的 Stage 0 在 `services/api` 建立最小 FastAPI 项目骨架、`uv` 管理的 Python 依赖声明、共享测试 fixtures、异步 pytest 基础设施，以及可访问的 `GET /api/v1/health` endpoint；本次实现严格停留在 harness 层，没有进入 `/tasks`、SSE、数据库模型或状态机业务实现。
- 修改文件:
  - `.gitignore`
  - `services/api/README.md`
  - `services/api/pyproject.toml`
  - `services/api/uv.lock`
  - `services/api/app/__init__.py`
  - `services/api/app/main.py`
  - `services/api/app/api/__init__.py`
  - `services/api/app/api/v1/__init__.py`
  - `services/api/app/api/v1/router.py`
  - `services/api/app/api/v1/health.py`
  - `services/api/tests/__init__.py`
  - `services/api/tests/conftest.py`
  - `services/api/tests/fixtures/__init__.py`
  - `services/api/tests/fixtures/app.py`
  - `services/api/tests/fixtures/db.py`
  - `services/api/tests/fixtures/runtime.py`
  - `services/api/tests/fixtures/storage.py`
  - `services/api/tests/unit/test_async_harness.py`
  - `services/api/tests/unit/test_fixture_exports.py`
  - `services/api/tests/unit/test_app_factory.py`
  - `services/api/tests/contract/rest/test_health.py`
  - `docs/Execution_Log.md`
- 测试/验证:
  - 已运行: `uv run --with fastapi --with httpx --with pytest --with pytest-asyncio pytest tests/unit tests/contract`（红测，确认缺少 `app` 与 `tests.fixtures`）; `uv sync --group dev`; `uv run --no-sync --group dev pytest tests/unit`; `uv run --no-sync --group dev pytest tests/contract`; `uv run --no-sync --group dev pytest tests/unit tests/contract`
  - 未运行: `ruff check`、`mypy`、`pytest tests/integration`；本任务包仅要求 Stage 0 harness，且当前未进入静态检查和集成测试阶段
- 验收结论: accepted；`tests/unit` 与 `tests/contract` 均可独立运行，异步测试可发现执行，`tests/fixtures` 基础入口可导入，最小 FastAPI app factory 与 `/api/v1/health` 已可启动并通过 contract test，且未越界进入 Backend Stage 1。
- blocker / 风险:
  - 无当前 blocker
  - `db_engine` / `db_session` 仍是 Stage 0 占位 fixture，真实 PostgreSQL 集成应在后续阶段按任务包单独引入
- 下一步建议:
  - 进入独立的 Backend Stage 1 任务包，补 `Core Schema` 与状态机的 red-green 测试
  - 在后续基础设施任务中补 `ruff`、`mypy` 与 integration gate 所需依赖

## M0-005 Frontend Stage 0 Harness

- 日期时间: 2026-03-15 10:16:53 CST (+0800)
- 任务包编号: M0-005
- session 标识: codex-20260315-m0-005-frontend-stage0-harness
- 目标摘要: 按 `docs/Frontend_TDD_Plan.md` Stage 0 在 `apps/web` 建立最小 Next.js App Router 项目骨架、Vitest + jsdom + Testing Library 测试基础设施、ScriptedTaskEventSource 基础夹具、Playwright 基线与轻量 mock server，并保持实现停留在 harness 层，不进入 Stage 1 的契约类型、store、research workflow UI 或真实 REST/SSE 消费逻辑。
- 修改文件:
  - `.gitignore`
  - `README.md`
  - `package.json`
  - `pnpm-lock.yaml`
  - `apps/web/README.md`
  - `apps/web/.eslintrc.json`
  - `apps/web/package.json`
  - `apps/web/tsconfig.json`
  - `apps/web/next-env.d.ts`
  - `apps/web/postcss.config.mjs`
  - `apps/web/tailwind.config.ts`
  - `apps/web/vitest.config.ts`
  - `apps/web/playwright.config.ts`
  - `apps/web/app/globals.css`
  - `apps/web/app/layout.tsx`
  - `apps/web/app/page.tsx`
  - `apps/web/features/research/components/research-page-client.tsx`
  - `apps/web/lib/sse/task-event-source.ts`
  - `apps/web/components/ui/.gitkeep`
  - `apps/web/tests/setup.ts`
  - `apps/web/tests/fixtures/browser.ts`
  - `apps/web/tests/fixtures/render.tsx`
  - `apps/web/tests/fixtures/scripted-task-event-source.ts`
  - `apps/web/tests/unit/setup.spec.ts`
  - `apps/web/tests/unit/scripted-task-event-source.spec.ts`
  - `apps/web/tests/contract/contracts-package.spec.ts`
  - `apps/web/tests/component/research-page-client.spec.tsx`
  - `apps/web/tests/integration/.gitkeep`
  - `apps/web/tests/e2e/fixtures/constants.ts`
  - `apps/web/tests/e2e/fixtures/mock-server.mjs`
  - `apps/web/tests/e2e/specs/harness.spec.ts`
  - `docs/Execution_Log.md`
- 测试/验证:
  - 已运行: `pnpm install`（首次在沙箱内因 npm registry `ENOTFOUND` 失败，提权后完成）；`pnpm typecheck`；`pnpm lint`；`pnpm test:unit`；`pnpm test:contract`；`pnpm test:component`；`pnpm test:integration`；`pnpm test:e2e`（首次暴露 `webServer` 命令写法问题与缺少 Playwright browser，修复后通过）；`pnpm exec playwright install chromium`
  - 未运行: `pnpm build`；本任务包的验收聚焦 Stage 0 harness 与测试基线，不要求进入生产构建与业务联调
- 验收结论: accepted；`apps/web` 已具备最小 Next.js App Router、Vitest/jsdom、Testing Library、ScriptedTaskEventSource、Playwright + mock server 基线，`unit / contract / component` 可独立运行，且本次实现未越界进入 Frontend Stage 1。
- blocker / 风险:
  - 无当前 blocker
  - `pnpm lint` 目前通过 `ESLINT_USE_FLAT_CONFIG=false` 兼容 `eslint-config-next`，运行时会打印 ESLint 9 的 legacy config deprecation warning；后续可在独立工具链任务中切回 flat config
  - Playwright 依赖本机已安装 Chromium；新环境首次执行前仍需运行 `pnpm exec playwright install chromium`
- 下一步建议:
  - 进入独立的 Frontend Stage 1 任务包，补 `TaskSnapshot` / `EventEnvelope` 契约类型、fixture 与 reducer/store red-green 测试
  - 在后续前端基础设施任务中补 `MSW`、更多浏览器 API mock 与 integration 场景的 shared fixtures

## M0-008 Frontend Stage 1 Contract Types + Store Skeleton

- 日期时间: 2026-03-15 21:58:23 CST (+0800)
- 任务包编号: M0-008
- session 标识: codex-20260315-m0-008-frontend-stage1-contract-store
- 目标摘要: 按 `docs/Frontend_TDD_Plan.md` Stage 1 固化前端共享契约类型接入方式、Research session store skeleton、`available_actions` selectors、`task-snapshot-merger`、通用 SSE event reducer 以及 Stage 1 所需 builders / fixtures；本次仅实现 `task.created`、`phase.changed`、`heartbeat`、终态事件与 unsupported event no-op，不进入创建任务、真实 REST / SSE hook、页面壳扩展或 revision 切换逻辑。
- 修改文件:
  - `packages/contracts/src/index.ts`
  - `apps/web/package.json`
  - `pnpm-lock.yaml`
  - `apps/web/lib/contracts/index.ts`
  - `apps/web/features/research/mappers/task-snapshot-merger.ts`
  - `apps/web/features/research/reducers/event-reducer.ts`
  - `apps/web/features/research/store/research-session-store.types.ts`
  - `apps/web/features/research/store/research-session-store.ts`
  - `apps/web/features/research/store/selectors.ts`
  - `apps/web/tests/fixtures/builders.ts`
  - `apps/web/tests/contract/contracts-package.spec.ts`
  - `apps/web/tests/contract/task-snapshot-fixture.spec.ts`
  - `apps/web/tests/contract/event-envelope-fixture.spec.ts`
  - `apps/web/tests/unit/mappers/task-snapshot-merger.spec.ts`
  - `apps/web/tests/unit/reducers/event-reducer.spec.ts`
  - `apps/web/tests/unit/selectors/available-actions.spec.ts`
  - `docs/Execution_Log.md`
- 测试/验证:
  - 已运行: `pnpm install`；`pnpm typecheck`；`pnpm lint`；`pnpm test:contract`；`pnpm test:unit`；`pnpm test:component`；`pnpm test:integration`
  - 未运行: `pnpm build`、`pnpm test:e2e`；本任务包仅覆盖 Frontend Stage 1 的 contracts/store/reducer/selectors 基础，不涉及新的页面交互链路或浏览器级行为变更
- 验收结论: accepted；Stage 1 所需 contracts 类型、store skeleton、snapshot merger、通用事件 reducer、available actions selectors 与 builders / fixtures 已固定，关键分支均有 contract 或 unit tests 保护，且 revision 切换与 Stage 2 页面/API 行为未提前落地。
- blocker / 风险:
  - 无当前 blocker
  - 共享 `EventEnvelope` union 当前只覆盖 Stage 1 已进入测试的关键事件与一个已知 unsupported 事件；后续阶段引入更多事件时需要继续按文档扩展
  - `pnpm lint` 仍沿用 legacy `.eslintrc` 兼容 `eslint-config-next`，会打印 ESLint 9 deprecation warning
- 下一步建议:
  - 进入独立的 Frontend Stage 2 任务包，打通首页 shell、`POST /tasks` 状态写入与“创建后立即建 SSE”的 red-green 流程
  - 在后续阶段按 `Frontend_IA.md` §8 持续扩充 `EventEnvelope` 联合类型、event fixtures 与 reducer 分支

## M0-006 Accepted M0 Integration + Baseline Verification

- 日期时间: 2026-03-15 10:31:02 CST (+0800)
- 任务包编号: M0-006
- session 标识: codex-20260315-m0-006-m0-closure
- 目标摘要: 将已验收的 M0 成果确认整合到同一工作基线，核对 `main` 上的来源分支与关键冲突文件状态，执行 root、backend Stage 0、frontend Stage 0 的基线验证，并在仅出现最小集成问题时做最小修补，为 M1 做收口准备。
- 修改文件:
  - `apps/web/.eslintrc.json`
  - `docs/Execution_Log.md`
- 测试/验证:
  - 已运行: `git status --short`；`git branch --all --verbose --no-abbrev`；`git log --oneline --decorate --graph --all --max-count=40`；`find . -maxdepth 3 \( -type d -o -type f \) | sort`；`pnpm --version`；`cd services/api && UV_CACHE_DIR=/tmp/uv-cache uv run --no-sync --group dev pytest tests/unit tests/contract`；`cd apps/web && pnpm typecheck`；`cd apps/web && pnpm lint`；`cd apps/web && pnpm test:unit`；`cd apps/web && pnpm test:contract`；`cd apps/web && pnpm test:component`；`cd apps/web && pnpm test:e2e`
  - 未运行: `cd apps/web && pnpm test:integration`；当前任务包建议验证命令未要求该项，且本次收口聚焦已验收的 M0 基线共存与建议命令通过
- 验收结论: accepted；`main` 已包含 `M0-001` 至 `M0-005` 的已验收成果并可共存，backend Stage 0 验证通过，frontend Stage 0 的 typecheck / lint / unit / contract / component / e2e 基线已通过，本次未进入 M1。
- blocker / 风险:
  - 无当前 blocker
  - `apps/web` 的 e2e 基线在沙箱内无法监听 `127.0.0.1:3100`，需要提权或非受限环境运行；这属于执行环境限制，不是代码回归
  - `pnpm lint` 仍会打印 ESLint 9 legacy config warning，但 lint 已通过；该 warning 按任务要求未在本次处理
- 下一步建议:
  - M0 可正式收口，下一批任务包可进入 M1 但应继续保持单任务串行推进
  - 如需在受限环境重复跑 e2e，应沿用已批准的提权路径

## M0-007 Backend Stage 1 Core Schema + State Machine

- 日期时间: 2026-03-15 20:56:27 CST (+0800)
- 任务包编号: M0-007
- session 标识: codex-20260315-m0-007-backend-stage1
- 目标摘要: 按 `docs/Backend_TDD_Plan.md` Stage 1 在 `services/api` 固化后端核心 schema、domain enums、任务状态机、基础 token payload model 与纯 `RetryPolicy`，并以 unit tests 覆盖 schema 约束、`status × phase` 组合矩阵、合法/非法流转与重试预算，且实现严格停留在纯领域/纯策略层，不进入 `/tasks`、鉴权签名实现、repository、DB 或 SSE broker。
- 修改文件:
  - `services/api/app/core/__init__.py`
  - `services/api/app/core/retry.py`
  - `services/api/app/domain/__init__.py`
  - `services/api/app/domain/enums.py`
  - `services/api/app/domain/exceptions.py`
  - `services/api/app/domain/state_machine.py`
  - `services/api/app/domain/schemas.py`
  - `services/api/app/domain/tokens.py`
  - `services/api/tests/unit/core/test_retry.py`
  - `services/api/tests/unit/domain/test_schemas.py`
  - `services/api/tests/unit/domain/test_state_machine.py`
  - `docs/Execution_Log.md`
- 测试/验证:
  - 已运行: `cd services/api && UV_CACHE_DIR=/tmp/uv-cache uv run --no-sync --group dev pytest tests/unit/domain tests/unit/core`（红测，初始因缺少 `app.domain` / `app.core` 失败，补实现后通过）；`cd services/api && UV_CACHE_DIR=/tmp/uv-cache uv run --no-sync --group dev pytest tests/unit`; `cd services/api && UV_CACHE_DIR=/tmp/uv-cache uv run --no-sync --group dev pytest tests/unit tests/contract`
  - 未运行: `ruff check`、`mypy`、`pytest tests/integration`；本任务包只要求 Stage 1 纯领域与纯策略，不包含静态门禁补齐和集成层工作
- 验收结论: accepted；`TaskSnapshot`、`RevisionSummary`、`RequirementDetail`、`CollectPlan`、`CollectSummary`、`EventEnvelope`、domain enums、`TaskStateMachine`、token payload model 与 `RetryPolicy` 均已落地并具备 unit tests，非法状态流转会抛明确领域异常，Stage 0 health contract 回归也通过，本次未越界进入 Backend Stage 2。
- blocker / 风险:
  - 无当前 blocker
  - `RequirementDetail.raw_llm_output` 作为内部领域字段实现为可选，以同时兼容 `Architecture.md` 的内部 schema 与 `OpenAPI_v1.md` 的对外返回形态；后续若要外显该字段，需先改文档
- 下一步建议:
  - 进入独立的 Backend Stage 2 任务包，实现 `/tasks`、鉴权骨架与基础策略的 contract-first red-green
  - 在后续基础设施任务中再补真实 signer、repository 和 DB migration

## M0-009 Stage 1 Integration + M0 Final Closure

- 日期时间: 2026-03-15 22:07:52 CST (+0800)
- 任务包编号: M0-009
- session 标识: codex-20260315-m0-009-m0-final-closure
- 目标摘要: 对已验收的 `M0-007` 与 `M0-008` 做统一基线核对，确认当前 `main` 已同时包含 Backend Stage 0+1 与 Frontend Stage 0+1，检查 `packages/contracts`、后端 schema 与前端 contracts 接入没有真实语义冲突，并完成完整的 M0 基线验证，作为 M1 前唯一开发基线。
- 修改文件:
  - `docs/Execution_Log.md`
- 测试/验证:
  - 已运行: `git status --short`；`git branch --all --verbose --no-abbrev`；`git log --oneline --decorate --graph --all --max-count=60`；`sed -n '1,260p' packages/contracts/src/index.ts`；`sed -n '1,260p' apps/web/lib/contracts/index.ts`；`sed -n '1,260p' services/api/app/domain/schemas.py`；`sed -n '1,260p' services/api/app/domain/enums.py`；`pnpm --version`；`uv --version`；`cd services/api && UV_CACHE_DIR=/tmp/uv-cache uv run --no-sync --group dev pytest tests/unit tests/contract`；`cd apps/web && pnpm typecheck`；`cd apps/web && pnpm lint`；`cd apps/web && pnpm test:contract`；`cd apps/web && pnpm test:unit`；`cd apps/web && pnpm test:component`；`cd apps/web && pnpm test:integration`；`cd apps/web && pnpm test:e2e`
  - 未运行: 无
- 验收结论: accepted；`main` 已通过 PR #3 与 PR #4 吸收 `M0-007` 和 `M0-008`，Backend Stage 0+1 与 Frontend Stage 0+1 基线验证全部通过，`packages/contracts` 与前后端 Stage 1 契约接入可共存，M0 可明确宣布完成。
- blocker / 风险:
  - 无当前 blocker
  - `pnpm lint` 仍会打印 ESLint 9 legacy config warning，但 lint 已通过，且按任务约束本次未处理
  - `pnpm test:e2e` 在受限环境下需要最小范围提权以启动本地 web server；代码本身已验证通过
- 下一步建议:
  - 后续任务包可以正式进入 M1，但应继续保持单线程串行开发与 `docs/Execution_Log.md` 追加维护
  - M1 应从任务框架最小闭环开始，不回退扩张 M0 范围

## M1-001 Backend Stage 2 Tasks API Shell

- 日期时间: 2026-03-15 22:40:51 CST (+0800)
- 任务包编号: M1-001
- session 标识: codex-20260315-m1-001-backend-stage2-shell
- 目标摘要: 按 `docs/Backend_TDD_Plan.md` Stage 2 实现后端任务框架第一批最小闭环，在 `services/api` 落地 `POST /api/v1/tasks`、`GET /api/v1/tasks/{task_id}`、最小 `POST /api/v1/tasks/{task_id}/disconnect` 鉴权壳、task/access token signer 接口骨架、单活动任务锁、同 IP 配额策略、CORS、request/trace id middleware，并补齐真实 PostgreSQL 路径下的 SQLAlchemy/Alembic scaffolding 与首个 migration；严格停留在 REST shell，不进入 `GET /events`、heartbeat / connect deadline 生命周期、clarification / feedback / downloads 或任何 Stage 3 内容。
- 修改文件:
  - `services/api/pyproject.toml`
  - `services/api/alembic.ini`
  - `services/api/app/main.py`
  - `services/api/app/api/deps.py`
  - `services/api/app/api/error_handlers.py`
  - `services/api/app/api/errors.py`
  - `services/api/app/api/middleware.py`
  - `services/api/app/api/v1/router.py`
  - `services/api/app/api/v1/tasks.py`
  - `services/api/app/application/dto/tasks.py`
  - `services/api/app/application/policies/activity_lock.py`
  - `services/api/app/application/policies/ip_quota.py`
  - `services/api/app/application/ports/security.py`
  - `services/api/app/application/services/tasks.py`
  - `services/api/app/core/config.py`
  - `services/api/app/core/ids.py`
  - `services/api/app/infrastructure/db/base.py`
  - `services/api/app/infrastructure/db/models.py`
  - `services/api/app/infrastructure/db/repositories.py`
  - `services/api/app/infrastructure/db/session.py`
  - `services/api/app/infrastructure/db/migrations/env.py`
  - `services/api/app/infrastructure/db/migrations/versions/20260315_0001_stage2_api_shell.py`
  - `services/api/app/infrastructure/security/hmac_signers.py`
  - `services/api/tests/conftest.py`
  - `services/api/tests/fixtures/app.py`
  - `services/api/tests/fixtures/db.py`
  - `services/api/tests/unit/application/test_policies.py`
  - `services/api/tests/unit/infrastructure/test_token_signers.py`
  - `services/api/tests/contract/rest/test_tasks.py`
  - `services/api/tests/integration/db/test_migrations.py`
  - `services/api/uv.lock`
  - `docs/Execution_Log.md`
- 测试/验证:
  - 已运行: `cd services/api && UV_CACHE_DIR=/tmp/uv-cache uv sync --group dev`；`cd services/api && UV_CACHE_DIR=/tmp/uv-cache uv run --no-sync --group dev pytest tests/unit/application tests/unit/infrastructure`；`cd services/api && UV_CACHE_DIR=/tmp/uv-cache uv run --no-sync --group dev pytest tests/contract/rest/test_tasks.py tests/integration/db/test_migrations.py`；`cd services/api && UV_CACHE_DIR=/tmp/uv-cache uv run --no-sync --group dev pytest tests/unit tests/contract tests/integration`
  - 调试过程: 初始 red tests 因缺少 Stage 2 模块失败；真实 PostgreSQL 夹具随后暴露两个环境问题并已修复: Unix socket 路径过长导致 `postgres` 无法启动，以及 test database DSN 组装错误导致连接指向错误 socket；修复后所有后端测试通过
  - 未运行: `ruff check`、`mypy`；本任务包验收标准聚焦 contract / integration / 必要 unit tests 与 migration 正反向验证，未要求额外静态门禁
- 验收结论: accepted；`POST /api/v1/tasks`、`GET /api/v1/tasks/{task_id}`、最小 disconnect 鉴权壳、单活动任务锁、IP quota、CORS、`X-Request-ID` / `X-Trace-ID` 响应头、真实 PostgreSQL migration 正反向能力均已落地并被 unit / contract / integration tests 覆盖，且实现边界停留在 Backend Stage 2 API shell，没有进入 SSE broker 或 Stage 3 生命周期。
- blocker / 风险:
  - 无当前 blocker
  - 本次 token signer 为最小 HMAC 实现与接口骨架，满足 Stage 2 契约验证；后续如需切换更强签名机制，应在独立任务包中处理并先核对文档
  - `POST /disconnect` 仅覆盖本阶段所需的 header/body 鉴权与锁释放壳，不包含 heartbeat、connect deadline 或 SSE 连接清理语义
- 下一步建议:
  - 进入独立的 Backend Stage 2 后续任务包，补 `GET /events` 与 SSE 生命周期
  - 在下一阶段继续沿用真实 PostgreSQL 路径，为 repository / orchestrator / broker 增加集成测试

## M1-002 Frontend Stage 2 Workspace Shell + Create Task Flow

- 日期时间: 2026-03-15 23:16:27 CST (+0800)
- 任务包编号: M1-002
- session 标识: codex-20260315-m1-002-frontend-stage2-shell
- 目标摘要: 按 `docs/Frontend_TDD_Plan.md` Stage 2 在 `apps/web` 落地首页空态、研究输入面板、研究配置面板、创建任务 REST client / hook、工作台壳层和创建后立即触发 SSE 建连动作的最小闭环；严格停留在“创建任务并启动建连动作”，不进入 Stage 3 的 SSE 生命周期消费、heartbeat / disconnect 处理、澄清流程、timeline / report / feedback UI 或任何真实后端联调。
- 修改文件:
  - `packages/contracts/src/index.ts`
  - `apps/web/package.json`
  - `apps/web/lib/api/task-api-client.ts`
  - `apps/web/lib/sse/task-event-source.ts`
  - `apps/web/features/research/store/research-session-store.types.ts`
  - `apps/web/features/research/store/research-session-store.ts`
  - `apps/web/features/research/providers/research-workspace-providers.tsx`
  - `apps/web/features/research/hooks/use-create-task.ts`
  - `apps/web/features/research/components/research-page-client.tsx`
  - `apps/web/features/research/components/research-input-panel.tsx`
  - `apps/web/features/research/components/research-config-panel.tsx`
  - `apps/web/features/research/components/research-workspace-shell.tsx`
  - `apps/web/tests/setup.ts`
  - `apps/web/tests/fixtures/msw-server.ts`
  - `apps/web/tests/fixtures/render.tsx`
  - `apps/web/tests/fixtures/builders.ts`
  - `apps/web/tests/component/research-page-client.spec.tsx`
  - `apps/web/tests/component/research-input-panel.spec.tsx`
  - `apps/web/tests/component/research-config-panel.spec.tsx`
  - `apps/web/tests/integration/create-task-flow.spec.tsx`
  - `pnpm-lock.yaml`
  - `docs/Execution_Log.md`
- 测试/验证:
  - 已运行: `cd apps/web && pnpm typecheck`；`cd apps/web && pnpm lint`；`cd apps/web && pnpm test:contract`；`cd apps/web && pnpm test:unit`；`cd apps/web && pnpm test:component`；`cd apps/web && pnpm test:integration`
  - 调试过程: 初始 integration tests 因测试环境下默认 runtime 的请求地址/`fetch` 组合未与 MSW handler 基址对齐，导致 `POST /tasks` 走入 generic error 分支；已改为在 Stage 2 integration tests 中显式注入真实 `fetch`-based `taskApiClient` 与测试 origin 对齐，继续保持 REST+MSW 验证，不以 stub 替代 HTTP client 行为
  - 未运行: `pnpm test:e2e`；Stage 2 验收标准聚焦 unit / component / integration 闭环，本任务包未扩张到 Playwright 回归
- 验收结论: accepted；`ResearchPageClient`、workspace shell、`ResearchInputPanel`、`ResearchConfigPanel`、create task REST client / hook 已落地，首页可从 `Idle` 空态提交 `POST /api/v1/tasks` 进入活跃工作台，成功写入 `task_id` / `task_token` / `urls` / 初始 snapshot，并立即触发 SSE 建连动作；`creating_task` pendingAction 生命周期、`422 validation_error`、`409 resource_busy`、`429 ip_quota_exceeded`、创建中禁用输入与配置、以及“创建成功后不额外调用 `GET /tasks`”均已被 component / integration tests 覆盖，且实现边界停留在 Frontend Stage 2，没有越界进入 Stage 3。
- blocker / 风险:
  - 无当前 blocker
  - `pnpm lint` 仍会打印 ESLint 9 legacy config warning，但 lint 已通过，且按本任务约束未处理配置迁移
  - 当前默认 runtime 仍采用最小浏览器端 fetch client；真实部署时若需独立 API base 配置，应在后续独立任务包中按文档与部署方案统一处理，不在本次 Stage 2 内扩张
- 下一步建议:
  - 进入独立的 Frontend Stage 3 任务包，实现 SSE 生命周期消费、heartbeat / disconnect 与终态处理
  - 在后续前端任务中再接入 clarification / timeline / report 等业务 UI，继续保持 contract-first 与阶段边界

## M1-003 Backend Stage 3 SSE Broker + Lifecycle

- 日期时间: 2026-03-16 10:32:17 CST (+0800)
- 任务包编号: M1-003
- session 标识: codex-20260316-m1-003-backend-stage3-sse
- 目标摘要: 按 `docs/Backend_TDD_Plan.md` Stage 3 在 `services/api` 打通任务级 SSE 流、`task_events` 持久化、event serialization、首个 SSE 连接门控、connect deadline、heartbeat / disconnect / expiry 生命周期，并以最小框架级 orchestrator 语义保证“先连 SSE 再启动任务流”；严格停留在任务框架级流式编排，不接入 clarification、LLM、collector、writer、feedback 提交或任何 Stage 4 内容。
- 修改文件:
  - `services/api/app/api/deps.py`
  - `services/api/app/api/v1/tasks.py`
  - `services/api/app/application/dto/tasks.py`
  - `services/api/app/application/services/tasks.py`
  - `services/api/app/core/config.py`
  - `services/api/app/infrastructure/db/models.py`
  - `services/api/app/infrastructure/db/repositories.py`
  - `services/api/app/infrastructure/db/migrations/versions/20260316_0002_stage3_sse_lifecycle.py`
  - `services/api/app/infrastructure/security/hmac_signers.py`
  - `services/api/app/infrastructure/streaming/__init__.py`
  - `services/api/app/infrastructure/streaming/broker.py`
  - `services/api/app/main.py`
  - `services/api/tests/conftest.py`
  - `services/api/tests/fixtures/app.py`
  - `services/api/tests/contract/rest/test_task_events.py`
  - `services/api/tests/integration/db/test_migrations.py`
  - `services/api/tests/integration/lifecycle/test_task_stream_lifecycle.py`
  - `services/api/tests/unit/infrastructure/test_streaming.py`
  - `docs/Execution_Log.md`
- 测试/验证:
  - 已运行: `cd services/api && UV_CACHE_DIR=/tmp/uv-cache uv run --no-sync --group dev pytest tests/contract/rest/test_task_events.py tests/integration/lifecycle/test_task_stream_lifecycle.py`；`cd services/api && UV_CACHE_DIR=/tmp/uv-cache uv run --no-sync --group dev pytest tests/unit tests/contract tests/integration`
  - 调试过程:
    - 初始 red tests 暴露缺少 `task_events` 模型、SSE 路由与生命周期实现
    - 引入 fake clock 后，`task_token` 校验仍使用真实系统时间导致 `/events` 返回 `401 task_token_invalid`；已将 HMAC signer 接入同一时钟源
    - `httpx.ASGITransport` 会缓冲响应直至 body 完整结束，无法真实验证长连接 SSE；已在测试夹具中补一个 streaming-capable in-process transport，用于 Stage 3 contract / integration tests 增量消费事件帧
  - 未运行: `ruff check`、`mypy`；本任务包验收标准聚焦 Stage 3 的 unit / contract / integration 与 migration 正反向验证
- 验收结论: accepted；`GET /api/v1/tasks/{task_id}/events`、`POST /api/v1/tasks/{task_id}/heartbeat`、增强后的 `POST /api/v1/tasks/{task_id}/disconnect`、`task_events` 持久化、统一 SSE envelope、`task.created` / `heartbeat` / `phase.changed` / `task.failed` / `task.terminated` / `task.expired`、首连后才启动任务流、10 秒 connect deadline 清理、heartbeat timeout、awaiting_feedback 保持 SSE 打开且仍允许 heartbeat / disconnect、以及终态事件顺序均已落地并被 tests 覆盖；实现边界停留在 Backend Stage 3，没有进入 clarification、feedback、downloads 或 Stage 4。
- blocker / 风险:
  - 无当前 blocker
  - 当前 Stage 3 的“orchestrator 启动”仍是最小任务框架语义: 首连后落 `task.created` 并进入可流式生命周期，真实 clarification / LLM / collector / writer 编排留给后续阶段
  - 生命周期 runtime 依赖进程内 broker 状态管理活动连接与客户端心跳；这符合 v1 单进程 / 不支持刷新恢复的设计，但若后续部署拓扑变化，需要在独立任务包里重新评估跨实例一致性
- 下一步建议:
  - 进入独立的 Backend Stage 4 任务包，实现 clarification 与需求分析链路，并复用当前 Stage 3 的 SSE / 生命周期底座
  - 在后续阶段继续沿用真实 PostgreSQL 路径，为 orchestrator、event producer 和 feedback / artifact 生命周期补更多 integration tests

## M1-004 Frontend Stage 3 SSE Lifecycle + Heartbeat + Disconnect

- 日期时间: 2026-03-16 11:24:02 CST (+0800)
- 任务包编号: M1-004
- session 标识: codex-20260316-m1-004-frontend-stage3-lifecycle
- 目标摘要: 按 `docs/Frontend_TDD_Plan.md` Stage 3 在 `apps/web` 打通前端最关键的任务生命周期：`use-task-stream`、`use-heartbeat-loop`、`use-disconnect-guard`、顶栏连接状态和 `TerminalBanner`，覆盖 SSE 建连、connect deadline、heartbeat、`beforeunload` / `pagehide` / `sendBeacon`、手动 disconnect 与最小终态 UI；严格维持 v1 “不恢复、不重连”的约束，不进入 clarification、timeline、report、delivery、feedback 或任何 Frontend Stage 4 内容。
- 修改文件:
  - `packages/contracts/src/index.ts`
  - `apps/web/lib/api/task-api-client.ts`
  - `apps/web/features/research/store/research-session-store.types.ts`
  - `apps/web/features/research/store/research-session-store.ts`
  - `apps/web/features/research/store/selectors.ts`
  - `apps/web/features/research/hooks/use-create-task.ts`
  - `apps/web/features/research/hooks/use-task-stream.ts`
  - `apps/web/features/research/hooks/use-heartbeat-loop.ts`
  - `apps/web/features/research/hooks/use-disconnect-guard.ts`
  - `apps/web/features/research/components/research-input-panel.tsx`
  - `apps/web/features/research/components/research-page-client.tsx`
  - `apps/web/features/research/components/research-workspace-shell.tsx`
  - `apps/web/features/research/components/session-status-bar.tsx`
  - `apps/web/features/research/components/terminal-banner.tsx`
  - `apps/web/tests/fixtures/builders.ts`
  - `apps/web/tests/component/research-input-panel.spec.tsx`
  - `apps/web/tests/integration/task-stream-lifecycle.spec.tsx`
  - `docs/Execution_Log.md`
- 测试/验证:
  - 已运行: `cd apps/web && pnpm typecheck`；`cd apps/web && pnpm lint`；`cd apps/web && pnpm test:unit`；`cd apps/web && pnpm test:contract`；`cd apps/web && pnpm test:component`；`cd apps/web && pnpm test:integration`
  - 调试过程:
    - 新增 Stage 3 integration tests 后，初始失败集中在三类：全局 fake timers 让 `waitFor/findBy*` 整体挂起、`use-task-stream` 为规避 open 后 cleanup 暂时移除了依赖导致 lint 失败、以及 `sendBeacon` 在 jsdom 下对 `Blob` 读取不稳定
    - 已将 lifecycle tests 改为“仅时间相关用例启用 fake timers”，并将 `use-task-stream` 重构为 ref 持有订阅与 deadline timer 的方式，在满足 `react-hooks/exhaustive-deps` 的同时避免 open 后被 effect cleanup 误断开
    - `connect_deadline_at` 的测试 builder 由固定远未来时间改为动态 `Date.now() + 60s`，避免 Node `TimeoutOverflowWarning` 与旧 Stage 2 integration tests 被立即 timeout 破坏
    - `pagehide` beacon 改为发送 JSON 字符串 body，继续满足“body 中携带 `task_token`”的 Stage 3 契约要求，同时让测试环境可稳定断言内容
  - 未运行: `pnpm test:e2e`；本任务包验收标准聚焦 unit / contract / component / integration，不扩张到 Playwright 回归
- 验收结论: accepted；前端已具备 `task.created` 覆盖初始化 snapshot、connect deadline 客户端超时、heartbeat loop 启停与 `409/404` 终止、SSE 中断即终态、不自动重连、活跃任务 `beforeunload` 注册与终态移除、`pagehide` 触发 `sendBeacon`、手动 `POST /disconnect`、`disconnecting` pendingAction 生命周期，以及 `task.failed / task.terminated / task.expired` 禁用旧操作的完整 Stage 3 生命周期能力；断连、终止、过期三条路径均有 integration tests，且实现边界停留在 Frontend Stage 3，没有越界进入 Stage 4。
- blocker / 风险:
  - 无当前 blocker
  - `pnpm lint` 仍会打印 ESLint 9 legacy config warning，但 lint 已通过，且按本任务包约束未处理配置迁移
  - `pagehide` beacon 当前使用 JSON 字符串 body；这仍满足 `task_token` 随 body 发送的 Stage 3 契约，但如果后续要严格对齐文档中的 `Blob(application/json)` 推荐写法，应在独立任务包中结合真实浏览器环境再收敛
- 下一步建议:
  - 进入独立的 Frontend Stage 4 任务包，实现 clarification 事件消费、表单提交与倒计时
  - 在后续阶段继续沿用当前 Stage 3 生命周期底座，为 timeline、report、delivery 和 feedback UI 增加渐进式集成测试

## M1-005 Task Framework Integration + Final Closure

- 日期时间: 2026-03-16 11:42:14 CST (+0800)
- 任务包编号: M1-005
- session 标识: codex-20260316-m1-005-final-closure
- 目标摘要: 核对 `M1-001` 至 `M1-004` 是否已进入同一工作基线，确认当前 `main` 同时包含 Backend Stage 2+3 与 Frontend Stage 2+3，检查 shared contracts、后端 API 契约与前端消费代码没有真实字段漂移，并完成完整的 M1 基线验证；仅当验证暴露整合层问题时做最小修补，为 M2 建立唯一开发基线。
- 修改文件:
  - `apps/web/tests/e2e/specs/harness.spec.ts`
  - `docs/Execution_Log.md`
- 测试/验证:
  - 已运行: `git status --short`；`git branch --all --verbose --no-abbrev`；`git log --oneline --decorate --graph --all --max-count=80`；`sed -n '1,260p' packages/contracts/src/index.ts`；`sed -n '1,260p' apps/web/lib/api/task-api-client.ts`；`sed -n '1,260p' apps/web/lib/sse/task-event-source.ts`；`find apps/web/features/research/store -maxdepth 3 -type f | sort`；`sed -n '1,260p' services/api/app/api/v1/tasks.py`；`sed -n '1,320p' services/api/app/application/services/tasks.py`；`sed -n '1,360p' services/api/app/infrastructure/streaming/broker.py`；`sed -n '1,320p' apps/web/features/research/hooks/use-task-stream.ts`；`sed -n '1,320p' apps/web/features/research/hooks/use-heartbeat-loop.ts`；`sed -n '1,320p' apps/web/features/research/hooks/use-disconnect-guard.ts`；`pnpm --version`；`uv --version`；`cd services/api && UV_CACHE_DIR=/tmp/uv-cache uv run --no-sync --group dev pytest tests/unit tests/contract tests/integration`；`cd apps/web && pnpm typecheck`；`cd apps/web && pnpm lint`；`cd apps/web && pnpm test:contract`；`cd apps/web && pnpm test:unit`；`cd apps/web && pnpm test:component`；`cd apps/web && pnpm test:integration`；`cd apps/web && pnpm test:e2e`
  - 调试过程:
    - 后端 `pytest tests/unit tests/contract tests/integration` 首次在沙箱内失败，原因不是代码回归，而是 PostgreSQL 夹具创建 shared memory segment 被受限环境拦截；提权重跑后 `42 passed`
    - 前端 `pnpm test:e2e` 首次在提权环境下失败，定位为遗留 Stage 0 Playwright 断言仍在查找旧标题 `Mimir Frontend Stage 0 Harness`；已最小更新 spec，使其对齐当前 Stage 3 页面壳文案后重跑通过
  - 未运行: 无
- 验收结论: accepted；`main` 已通过 PR #6、#7、#8、#9 吸收 `M1-001` 至 `M1-004`，Backend Stage 2+3 与 Frontend Stage 2+3 基线验证通过，且统一基线上已满足“创建任务后立即建连、10 秒 connect deadline、SSE 中断即终止、`sendBeacon` 与普通 disconnect 都能工作”的 M1 闭环，M1 可明确宣布完成。
- blocker / 风险:
  - 无当前 blocker
  - `pnpm lint` 仍会打印 ESLint 9 legacy config warning，但 lint 已通过，且按任务约束本次未处理
  - 后端 integration tests 依赖真实 PostgreSQL 夹具，在受限沙箱里需要提权运行；前端 e2e 同样需要提权以启动本地 web server
- 下一步建议:
  - 后续任务包可以正式进入 M2，但应继续保持单线程串行开发与 `docs/Execution_Log.md` 追加维护
  - M2 应从 clarification / requirement analysis 的最小闭环开始，不回退扩张 M1 范围

## M2-001 Backend Stage 4 Clarification + Requirement Analysis

- 日期时间: 2026-03-16 14:09:16 CST (+0800)
- 任务包编号: M2-001
- session 标识: codex-20260316-m2-001-backend-stage4-clarification
- 目标摘要: 按 `docs/Backend_TDD_Plan.md` Stage 4 在 `services/api` 打通从任务进入 `clarifying`、SSE 输出 natural / options 两条澄清路径、`POST /api/v1/tasks/{task_id}/clarification` 提交、到 `RequirementDetail` 生成与落库的最小后端闭环；严格停在需求阶段，不进入 planner / collector / writer / feedback / downloads 或任何 Stage 5 内容。
- 修改文件:
  - `services/api/app/api/v1/tasks.py`
  - `services/api/app/application/dto/clarification.py`
  - `services/api/app/application/parsers/__init__.py`
  - `services/api/app/application/parsers/clarification.py`
  - `services/api/app/application/parsers/requirement.py`
  - `services/api/app/application/ports/llm.py`
  - `services/api/app/application/prompts/__init__.py`
  - `services/api/app/application/prompts/clarification.py`
  - `services/api/app/application/prompts/requirement.py`
  - `services/api/app/application/services/clarification.py`
  - `services/api/app/application/services/llm.py`
  - `services/api/app/application/services/tasks.py`
  - `services/api/app/core/config.py`
  - `services/api/app/infrastructure/db/repositories.py`
  - `services/api/app/infrastructure/llm/__init__.py`
  - `services/api/app/infrastructure/llm/local_stub.py`
  - `services/api/app/infrastructure/streaming/broker.py`
  - `services/api/app/main.py`
  - `services/api/tests/contract/rest/test_clarification.py`
  - `services/api/tests/contract/rest/test_task_events.py`
  - `services/api/tests/contract/rest/test_tasks.py`
  - `services/api/tests/integration/lifecycle/test_clarification_lifecycle.py`
  - `services/api/tests/integration/lifecycle/test_task_stream_lifecycle.py`
  - `services/api/tests/unit/application/test_clarification_parsers.py`
  - `services/api/tests/unit/application/test_prompts.py`
  - `services/api/tests/unit/application/test_retrying_llm.py`
  - `docs/Execution_Log.md`
- 测试/验证:
  - 已运行: `cd services/api && UV_CACHE_DIR=/tmp/uv-cache uv run --no-sync --group dev pytest tests/unit/application/test_clarification_parsers.py tests/unit/application/test_prompts.py tests/unit/application/test_retrying_llm.py`；`cd services/api && UV_CACHE_DIR=/tmp/uv-cache uv run --no-sync --group dev pytest tests/contract/rest/test_clarification.py tests/integration/lifecycle/test_clarification_lifecycle.py`；`cd services/api && UV_CACHE_DIR=/tmp/uv-cache uv run --no-sync --group dev pytest tests/unit tests/contract tests/integration`
  - 调试过程:
    - red tests 首先暴露缺失的 Stage 4 模块边界：clarification parser、prompt builder、LLM port / retry wrapper、clarification orchestrator 与 `POST /clarification`
    - contract / integration 测试在受限沙箱里无法启动真实 PostgreSQL，报错为 shared memory segment 创建受限；已按真实 PostgreSQL 路径提权重跑，不回退到内存实现
    - Stage 3 的 SSE tests 原先写死了 `task.created` 后的 seq，Stage 4 插入 `clarification.delta` / ready 事件后变得过脆；已改为断言单调递增与目标事件到达，不再把中间 clarification 事件当成回归
    - Stage 4 评估后未新增 migration：现有 `research_tasks`、`task_revisions`、`task_events` 足以承载 v1 clarification runtime 与 `RequirementDetail` 落库，避免超范围发明 schema
  - 未运行: `ruff check`、`mypy`；本任务包验收标准聚焦 Backend Stage 4 的 unit / contract / integration 闭环
- 验收结论: accepted；natural 与 options 两条路径都可在首个 SSE 连接后启动 clarification orchestrator，输出 `clarification.delta`、`clarification.natural.ready` / `clarification.options.ready`、`clarification.countdown.started`，options 解析失败会发送 `clarification.fallback_to_natural` 并回退到 natural；`POST /api/v1/tasks/{task_id}/clarification` 已支持 natural / options 两种 body，并在成功后推进到 `running + analyzing_requirement`；需求分析通过 `RetryPolicy` 包裹的 adapter 调用输出 `analysis.delta` 与 `analysis.completed`，最终 `RequirementDetail` 落库到 revision 且对外响应隐藏 `raw_llm_output`；60 秒后端兜底超时会按默认 `o_auto` 自动推进分析；实现边界停留在 Backend Stage 4，没有进入 planner / collector / summary / writer / feedback / downloads 或 Stage 5。
- blocker / 风险:
  - 无当前 blocker
  - 当前 Stage 4 的 LLM provider 仍是挂在清晰端口后的 deterministic local stub / scripted fake，满足 TDD 与无外网约束；接真实 provider 时必须继续保留相同端口和 RetryPolicy 行为
  - clarification 的待答问题集与 60 秒兜底 deadline 仍保留在单进程 runtime，而非数据库；这符合 v1 “不支持刷新恢复 / 单进程 broker” 约束，但如果后续要支持多实例或恢复语义，需要在独立任务包里重新设计
- 下一步建议:
  - 进入独立的 Backend Stage 5 任务包，实现 planner / collector / collect summary，并复用当前 Stage 4 产出的 `RequirementDetail`
  - 后续引入真实 LLM provider 时，优先增加 adapter contract tests 与 malformed output integration cases，避免破坏现有 clarification / analysis 闭环

## M2-002 Frontend Stage 4 Clarification UI + Requirement Analysis Handoff

- 日期时间: 2026-03-16 14:55:44 CST (+0800)
- 任务包编号: M2-002
- session 标识: codex-20260316-m2-002-frontend-stage4-clarification-ui
- 目标摘要: 按 `docs/Frontend_TDD_Plan.md` Stage 4 在 `apps/web` 打通自然语言澄清与选单澄清两条前端提交路径，接入 `clarification.*` / `analysis.*` 事件消费、15 秒前端倒计时、移动端澄清布局替换，以及最小 requirement analysis handoff 展示；严格停在 Stage 4，不进入 timeline / planner / collector / report / feedback UI。
- 修改文件:
  - `packages/contracts/src/index.ts`
  - `apps/web/lib/api/task-api-client.ts`
  - `apps/web/features/research/store/research-session-store.types.ts`
  - `apps/web/features/research/store/research-session-store.ts`
  - `apps/web/features/research/reducers/event-reducer.ts`
  - `apps/web/features/research/hooks/use-task-stream.ts`
  - `apps/web/features/research/hooks/use-clarification-submit.ts`
  - `apps/web/features/research/hooks/use-clarification-countdown.ts`
  - `apps/web/features/research/components/clarification-panels.tsx`
  - `apps/web/features/research/components/research-workspace-shell.tsx`
  - `apps/web/features/research/components/research-page-client.tsx`
  - `apps/web/features/research/components/research-input-panel.tsx`
  - `apps/web/features/research/components/research-config-panel.tsx`
  - `apps/web/tests/fixtures/builders.ts`
  - `apps/web/tests/contract/event-envelope-fixture.spec.ts`
  - `apps/web/tests/unit/reducers/event-reducer.spec.ts`
  - `apps/web/tests/component/research-input-panel.spec.tsx`
  - `apps/web/tests/component/research-page-client.spec.tsx`
  - `apps/web/tests/integration/clarification-flow.spec.tsx`
  - `docs/Execution_Log.md`
- 测试/验证:
  - 已运行: `cd apps/web && pnpm typecheck`；`cd apps/web && pnpm lint`；`cd apps/web && pnpm test:contract`；`cd apps/web && pnpm test:unit`；`cd apps/web && pnpm test:component`；`cd apps/web && pnpm test:integration`
  - 调试过程:
    - 先补了 Stage 4 red tests：`clarification.delta`、`natural/options.ready`、倒计时、timeout auto submit、manual submit、`422 validation_error`、`fallback_to_natural`、移动端 `澄清详情` 分段替换，以及 `analysis.delta` / `analysis.completed`
    - 实现过程中暴露出 Stage 3 遗留缺陷：`use-task-stream` 在 `onOpen` 后因 effect 重跑把旧闭包标记为 disposed，导致后续 SSE 事件在 UI 上被静默吞掉；本任务内已最小修补为 mount-ref 守卫，确保 Stage 4 事件消费真实可用
    - 假时钟下的 clarification submit integration tests 改为注入 `taskApiClient` 测试替身，以避免 `MSW + fake timers` 干扰倒计时行为本身；`422 validation_error` 仍保留 MSW 覆盖 REST 契约错误路径
  - 未运行: `pnpm test:e2e`；本任务包验收标准不要求 e2e 变更
- 验收结论: accepted；自然语言澄清与选单澄清两条路径都可从 UI 成功提交；`clarification.delta`、`clarification.natural.ready`、`clarification.options.ready`、`clarification.countdown.started`、`clarification.fallback_to_natural`、`analysis.delta`、`analysis.completed` 都已接入前端状态与展示；倒计时的启动、重置、超时自动提交、手动提交取消倒计时，以及 `pendingAction = submitting_clarification` 生命周期都有测试保护；`analysis.completed` 会把 `requirement_detail` 写入 `currentRevision` 并清空 `analysisText`；移动端在 `clarifying` 阶段会把 `报告` 分段替换为 `澄清详情`；实现边界停留在 Frontend Stage 4，没有进入 Stage 5 的 timeline / planner / collector / summary / report / feedback UI。
- blocker / 风险:
  - 无当前 blocker
  - `pnpm lint` 仍会打印 ESLint 9 legacy config warning，但 lint 已通过，且按任务约束本次未处理配置迁移
  - 当前倒计时是纯前端 UI timer，按文档只基于 `duration_seconds` 与本地时间维护，没有发明权威 `auto_submit_at`
- 下一步建议:
  - 进入独立的 Frontend Stage 5 任务包，实现 requirement summary card、timeline 与研究中透明度事件映射
  - 后续 Stage 5+ 应继续复用当前 clarification / analysis handoff 底座，不要回退到组件内临时拼装业务状态

## M2-003 Clarification Phase Integration + Final Closure

- 日期时间: 2026-03-16 15:09:34 CST (+0800)
- 任务包编号: M2-003
- session 标识: codex-20260316-m2-003-final-closure
- 目标摘要: 核对 `M2-001` 与 `M2-002` 是否已进入同一工作基线，确认当前 `main` 同时包含 Backend Stage 4、Frontend Stage 4 以及此前已闭环的 M1 生命周期能力，检查 shared contracts、后端事件契约与前端消费代码没有真实字段漂移，并完成完整的 M2 基线验证，作为 M3 前唯一开发基线。
- 修改文件:
  - `docs/Execution_Log.md`
- 测试/验证:
  - 已运行: `git status --short`；`git branch --all --verbose --no-abbrev`；`git log --oneline --decorate --graph --all --max-count=100`；`sed -n '520,760p' docs/Execution_Log.md`；`sed -n '1,360p' packages/contracts/src/index.ts`；`sed -n '1,320p' apps/web/lib/api/task-api-client.ts`；`sed -n '1,320p' apps/web/features/research/hooks/use-task-stream.ts`；`sed -n '1,320p' apps/web/features/research/hooks/use-clarification-submit.ts`；`sed -n '1,320p' apps/web/features/research/hooks/use-clarification-countdown.ts`；`sed -n '1,360p' apps/web/features/research/store/research-session-store.types.ts`；`sed -n '1,360p' apps/web/features/research/store/research-session-store.ts`；`sed -n '1,360p' apps/web/features/research/reducers/event-reducer.ts`；`sed -n '1,360p' services/api/app/application/services/clarification.py`；`sed -n '1,420p' services/api/app/application/services/tasks.py`；`sed -n '1,420p' services/api/app/infrastructure/streaming/broker.py`；`sed -n '1,360p' services/api/app/api/v1/tasks.py`；`pnpm --version`；`uv --version`；`cd services/api && UV_CACHE_DIR=/tmp/uv-cache uv run --no-sync --group dev pytest tests/unit tests/contract tests/integration`；`cd apps/web && pnpm typecheck`；`cd apps/web && pnpm lint`；`cd apps/web && pnpm test:contract`；`cd apps/web && pnpm test:unit`；`cd apps/web && pnpm test:component`；`cd apps/web && pnpm test:integration`；`cd apps/web && pnpm test:e2e`
  - 调试过程:
    - 后端 Stage 4 baseline 在当前环境无需额外提权，`62 passed`
    - 前端 e2e 仍需最小范围提权以启动本地 web server；提权后通过，代码本身无回归
  - 未运行: 无
- 验收结论: accepted；`main` 已通过 PR #11 与 PR #12 吸收 `M2-001` 和 `M2-002`，Backend Stage 4 与 Frontend Stage 4 基线验证通过，且统一基线上已满足 natural / options 两条澄清路径、15 秒前端倒计时、60 秒后端兜底、`analysis.completed -> RequirementDetail` 与既有 M1 生命周期能力共存，M2 可明确宣布完成。
- blocker / 风险:
  - 无当前 blocker
  - `pnpm lint` 仍会打印 ESLint 9 legacy config warning，但 lint 已通过，且按任务约束本次未处理
  - `pnpm test:e2e` 在受限环境下需要最小范围提权以启动本地 web server；这属于执行环境限制，不是 M2 回归
- 下一步建议:
  - 后续任务包可以正式进入 M3，但应继续保持单线程串行开发与 `docs/Execution_Log.md` 追加维护
  - M3 应从 planner / collector / summary 的最小闭环开始，不回退扩张 M2 范围
