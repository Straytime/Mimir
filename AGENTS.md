# Repository Guidelines

## Project Structure & Module Organization

`docs/` is the source of truth today. Start with [`docs/Architecture.md`](/Users/aminer/Library/CloudStorage/OneDrive-个人/projects/Mimir/docs/Architecture.md), [`docs/OpenAPI_v1.md`](/Users/aminer/Library/CloudStorage/OneDrive-个人/projects/Mimir/docs/OpenAPI_v1.md), [`docs/Frontend_IA.md`](/Users/aminer/Library/CloudStorage/OneDrive-个人/projects/Mimir/docs/Frontend_IA.md), and the two TDD plans before changing behavior.

Implementation is planned as a monorepo:

- `apps/web/` for the Next.js App Router frontend
- `services/api/` for the FastAPI backend
- `packages/contracts/` for shared API schemas and types
- `scripts/` for automation

Until those directories exist, keep new contributions focused on the docs and preserve cross-document consistency.

Important v1 product constraints from the design docs:

- Single active research task globally at any time
- Frontend talks directly to the backend over REST + SSE
- v1 does not support page refresh recovery, SSE reconnect resume, or browser persistence of `task_token`
- Feedback creates a new `Revision` inside the same `Task`; existing collected information is retained
- Any behavior change must update the relevant docs first, then tests, then implementation

Execution log rule:

- `docs/Execution_Log.md` is the single global implementation history document for this repository.
- After every implementation session that changes docs, code, scaffolding, or toolchain state, update `docs/Execution_Log.md` before sending the final completion report.

## Build, Test, and Development Commands

There is no runnable root application yet. Use the planned package-level commands once scaffolding is added.

- Frontend (`apps/web`): `eslint`, `tsc --noEmit`, `vitest tests/unit`, `vitest tests/contract`, `vitest tests/component`, `vitest tests/integration`, `playwright test`
- Backend (`services/api`): `ruff check`, `ruff format --check`, `mypy`, `pytest tests/unit`, `pytest tests/contract`, `pytest tests/integration`

Run commands from the relevant package directory, not the repository root.

When scaffolding is introduced, keep frontend and backend commands separate. Do not add a root-level dev server that hides the intended deployment split (`Vercel` for `apps/web`, `Railway` for `services/api`) unless the architecture docs are updated first.

## Coding Style & Naming Conventions

Follow the documented stack: Next.js App Router + TypeScript/React on the frontend, and Python 3.12+ + FastAPI on the backend. Use feature-based folders on the frontend (`features/research/...`) and layered modules on the backend (`application`, `domain`, `infrastructure`).

Architecture constraints that should not be bypassed:

- Do not introduce LangChain, LangGraph, or other agent orchestration frameworks
- Use explicit state machines, explicit orchestrators, and contract-first APIs
- Backend integrations are planned around Zhipu official SDK, native HTTP clients, and E2B Sandbox API
- Frontend should consume structured backend contracts only; do not parse raw LLM option markdown on the client
- Preserve documented contract names exactly, for example `TaskSnapshot`, `EventEnvelope`, `task_token`, `access_token`, `available_actions`

- React components: `PascalCase`
- Hooks: `useSomething`
- TypeScript utilities and variables: `camelCase`
- Python modules and functions: `snake_case`

Prefer small modules, explicit dependency injection, and contract-first changes.

## Testing Guidelines

Use TDD and update docs before code when behavior changes. Mirror the planned test layout: `apps/web/tests/{unit,contract,component,integration,e2e}` and `services/api/tests/{unit,contract,integration,smoke}`.

Keep CI deterministic: avoid real upstream services, real timers, and hidden browser state. Use fakes, fixtures, `MSW`, and `respx` where applicable.

Frontend-specific testing rules:

- Use scripted SSE fixtures instead of relying on browser-native reconnect behavior
- Test `beforeunload`, `pagehide`, `sendBeacon`, countdowns, and scroll behavior with controllable mocks and fake timers
- Treat `available_actions`, `status`, and `phase` as the only authority for UI action gating

Backend-specific testing rules:

- Use fake adapters for Zhipu, `web_search`, `web_fetch`, and E2B in CI
- Cover SSE event ordering, cleanup, retry policy, and `Task / Revision` transitions explicitly

## Commit & Pull Request Guidelines

The current history uses short imperative subjects (`Initial commit`). Continue with concise messages such as `Add task event schema fixtures`.

PRs should:

- describe the behavior change
- list updated docs and contracts
- note test coverage
- include screenshots or stream traces for UI and SSE changes

## Security & Configuration Tips

Do not commit secrets, tokens, or environment files. `task_token` is designed to stay in memory only; do not add browser persistence without first updating the architecture and API docs.

Also keep these constraints in mind:

- Treat download and artifact URLs as short-lived `access_token`-bound resources
- Do not add frontend BFF token storage or server-side proxying by default
- Fail closed on contract uncertainty: if docs and implementation disagree, reconcile the docs before proceeding
