# services/api

Stage 0 FastAPI harness for the Mimir backend.

## Current scope

- minimal `FastAPI` app factory under `app/`
- `GET /api/v1/health` endpoint
- `pytest` + `pytest-asyncio` test harness
- shared Stage 0 fixtures under `tests/fixtures/`

## Local commands

- `uv sync --group dev`
- `uv run --group dev pytest tests/unit`
- `uv run --group dev pytest tests/contract`

## Provider modes

- `MIMIR_PROVIDER_MODE=stub` is the default and keeps the current deterministic test path.
- `MIMIR_PROVIDER_MODE=real` switches LLM and `web_search` to real provider adapters and `web_fetch` to real HTTP fetch.
- `MIMIR_LLM_PROVIDER_MODE`, `MIMIR_WEB_SEARCH_PROVIDER_MODE`, and `MIMIR_WEB_FETCH_PROVIDER_MODE` can override the global mode per adapter.

## Real provider env

See [`.env.example`](/Users/aminer/Library/CloudStorage/OneDrive-个人/projects/Mimir/services/api/.env.example) for the supported variables.

- `ZHIPU_API_KEY` or `MIMIR_ZHIPU_API_KEY` is required when `llm` or `web_search` runs in `real` mode.
- Model IDs are configurable per agent role; the defaults are separated in config even if you keep them on the same model family at first.
