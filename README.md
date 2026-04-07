# Mimir

[中文版 README](README.zh-CN.md)

AI-powered deep research platform that transforms a user question into a structured, citation-backed research report — end to end.

**Live in production** on Railway (API) and Vercel (Web).

Built 100% through vibe coding with [Claude Code](https://claude.ai/code) and [Codex](https://openai.com/index/introducing-codex/) — no line of code was written by hand.

## What It Does

1. **Clarify** — Asks follow-up questions (free-form or multiple-choice with a 15 s auto-commit timer) to sharpen the research scope.
2. **Analyze** — Extracts structured requirements from the clarified prompt.
3. **Plan & Collect** — An explicit planner agent loop dispatches parallel collector subtasks that search the web, fetch pages, and summarize findings.
4. **Merge** — Deduplicates sources and normalizes citations.
5. **Outline & Write** — A writer agent loop drafts the report section by section, optionally executing Python in an E2B sandbox for data analysis.
6. **Deliver** — Exports the finished report as downloadable Markdown, PDF, and ZIP artifacts.
7. **Revise** — Accepts user feedback and reruns the writer to refine the delivered report.

The entire pipeline streams progress to the browser via SSE.

## Architecture

```text
Browser ──SSE/REST──▸ FastAPI (Railway)
                          │
                          ├─▸ PostgreSQL (Railway)
                          ├─▸ Zhipu LLM API
                          ├─▸ Zhipu Web Search API
                          ├─▸ Jina Reader (web fetch)
                          └─▸ E2B Sandbox (code execution)
```

Key constraints:

- No LangChain / LangGraph — explicit state machine + explicit orchestrator
- Contract-first, TDD development
- One active research task at a time (global singleton)
- SSE streaming only; no WebSocket
- `task_token` is memory-only — disconnect abandons the task

## Repository Layout

```
apps/web/            Next.js App Router frontend
services/api/        FastAPI backend (not a pnpm workspace member; uses uv)
packages/contracts/  Shared TypeScript type definitions (TaskSnapshot, EventEnvelope, …)
docs/                Source-of-truth design & implementation docs
scripts/             Repo-level automation
```

### Backend Layers (`services/api/app/`)

```
api/              FastAPI routes, request/response serialization
application/      Orchestrators, services, DTOs, prompt builders, port definitions
domain/           Domain models, enums, state machine
infrastructure/   Adapter implementations (LLM, search, fetch, sandbox, SSE, DB)
core/             Settings, JSON utilities, ID generation
```

## Tech Stack

### Frontend

- Next.js (App Router), React 19, TypeScript
- Tailwind CSS with a custom industrial design system (see `docs/DESIGN.md`)
- react-markdown + rehype-sanitize
- Vitest, Testing Library, Playwright

### Backend

- Python 3.12+, FastAPI, Pydantic v2
- SQLAlchemy 2.0 + Alembic (PostgreSQL)
- httpx, Zhipu SDK
- pytest, pytest-asyncio, respx

## Getting Started

### Prerequisites

- Docker (for local PostgreSQL)
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- [pnpm](https://pnpm.io/) (Node package manager)

### Quick Start

```bash
# Install dependencies
pnpm install
cd services/api && uv sync --group dev && cd ../..

# Start everything (PostgreSQL + migrations + API + Web)
./scripts/dev.sh
```

After startup:

| Service | URL |
|---------|-----|
| Web     | http://localhost:3000 |
| API     | http://localhost:8000 |
| DB      | postgresql://postgres@localhost:5432/postgres |

Default provider mode is `stub` — no API keys required for local development.

```bash
./scripts/dev.sh migrate   # Run migrations only
./scripts/dev.sh stop      # Stop PostgreSQL
docker compose down -v     # Stop PostgreSQL and wipe data
```

## Provider Modes

The backend defaults to deterministic local stubs for all external services. Switch to real providers with environment variables:

| Variable | Description |
|----------|-------------|
| `MIMIR_PROVIDER_MODE=stub\|real` | Global default for all adapters |
| `MIMIR_LLM_PROVIDER_MODE` | Override for Zhipu LLM |
| `MIMIR_WEB_SEARCH_PROVIDER_MODE` | Override for Zhipu web search |
| `MIMIR_WEB_FETCH_PROVIDER_MODE` | Override for Jina web fetch |
| `MIMIR_E2B_PROVIDER_MODE` | Override for E2B sandbox |

Real mode requires `ZHIPU_API_KEY`, `JINA_API_KEY`, and/or `E2B_API_KEY`. See [`services/api/.env.example`](services/api/.env.example).

## Commands

### Backend (`services/api`)

```bash
cd services/api
uv sync --group dev                          # Install dependencies
uv run --group dev pytest tests/unit         # Unit tests
uv run --group dev pytest tests/contract     # Contract tests
uv run --group dev pytest tests/integration  # Integration tests (needs PostgreSQL)
uv run alembic upgrade head                  # Run migrations
```

### Frontend (`apps/web`)

```bash
cd apps/web
pnpm dev              # Dev server
pnpm typecheck        # TypeScript check
pnpm lint             # ESLint
pnpm test:unit        # Unit tests
pnpm test:contract    # Contract tests
pnpm test:component   # Component tests
pnpm test:e2e         # Playwright e2e (needs chromium: pnpm exec playwright install chromium)
```

## Production Deployment

| Component | Platform | Details |
|-----------|----------|---------|
| `apps/web` | Vercel | Next.js, auto-deploy from `main` |
| `services/api` | Railway | FastAPI + PostgreSQL + Volume (artifact storage) |

See [`docs/Deploy_Contract.md`](docs/Deploy_Contract.md) for the full deployment contract.

## Documentation

| Document | Description |
|----------|-------------|
| [`docs/Architecture.md`](docs/Architecture.md) | System architecture, state machine, schemas, API contracts |
| [`docs/DESIGN.md`](docs/DESIGN.md) | Frontend design system — "The Kinetic Monolith" |
| [`docs/OpenAPI_v1.md`](docs/OpenAPI_v1.md) | v1 API contract and SSE event specification |
| [`docs/Deploy_Contract.md`](docs/Deploy_Contract.md) | Vercel / Railway deployment contract |
| [`docs/Frontend_IA.md`](docs/Frontend_IA.md) | Frontend information architecture |
| [`docs/Mimir_v1.0.0_prd_0.3.md`](docs/Mimir_v1.0.0_prd_0.3.md) | Product requirements document |

## License

This project is licensed under the [GPL-3.0 License](LICENSE).
