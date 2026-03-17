# services/api

Stage 0 FastAPI harness for the Mimir backend.

## Current scope

- minimal `FastAPI` app factory under `app/`
- `GET /api/v1/health` endpoint
- `pytest` + `pytest-asyncio` test harness
- shared Stage 0 fixtures under `tests/fixtures/`

## Local commands

```bash
uv sync --group dev                                                # install deps
uv run --group dev uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload  # dev server
uv run alembic upgrade head                                        # run migrations
uv run --group dev pytest tests/unit                               # unit tests
uv run --group dev pytest tests/contract                           # contract tests
uv run --group dev pytest tests/integration                        # integration tests (needs PostgreSQL)
```

The `MIMIR_DATABASE_URL` env var (default: `postgresql+psycopg://postgres@127.0.0.1:5432/postgres`) is shared between the app and Alembic migrations.

## Provider modes

- `MIMIR_PROVIDER_MODE=stub` is the default and keeps the current deterministic test path.
- `MIMIR_PROVIDER_MODE=real` switches LLM and `web_search` to Zhipu real adapters and `web_fetch` to Jina Reader (`r.jina.ai`).
- `MIMIR_LLM_PROVIDER_MODE`, `MIMIR_WEB_SEARCH_PROVIDER_MODE`, and `MIMIR_WEB_FETCH_PROVIDER_MODE` can override the global mode per adapter.

## Real provider env

See [`.env.example`](/Users/aminer/Library/CloudStorage/OneDrive-个人/projects/Mimir/services/api/.env.example) for the supported variables.

- `ZHIPU_API_KEY` or `MIMIR_ZHIPU_API_KEY` is required when `llm` or `web_search` runs in `real` mode.
- `JINA_API_KEY` or `MIMIR_JINA_API_KEY` is required when `web_fetch` runs in `real` mode. Jina Reader base URL defaults to `https://r.jina.ai/` and can be overridden via `MIMIR_JINA_BASE_URL`.
- Model IDs are configurable per agent role; the current default contract is `glm-5` for all roles unless you explicitly override them in local env.
- `MIMIR_WEB_SEARCH_ENGINE` defaults to `search_prime`, which matches the current architecture contract for Zhipu `web_search`.
