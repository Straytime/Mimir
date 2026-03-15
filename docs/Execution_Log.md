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
