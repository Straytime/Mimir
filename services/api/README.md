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
