# services/api

FastAPI backend for Mimir.

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
`DATABASE_URL` is also accepted as a production fallback, which aligns with Railway's default Postgres injection.

## Provider modes

- `MIMIR_PROVIDER_MODE=stub` is the default and keeps the current deterministic test path.
- `MIMIR_PROVIDER_MODE=real` switches LLM and `web_search` to Zhipu real adapters, `web_fetch` to Jina Reader (`r.jina.ai`), and `python_interpreter` sandbox calls to real E2B.
- `MIMIR_LLM_PROVIDER_MODE`, `MIMIR_WEB_SEARCH_PROVIDER_MODE`, `MIMIR_WEB_FETCH_PROVIDER_MODE`, and `MIMIR_E2B_PROVIDER_MODE` can override the global mode per adapter.

## Real provider env

See [`.env.example`](/Users/aminer/Library/CloudStorage/OneDrive-个人/projects/Mimir/services/api/.env.example) for the supported variables.

- `ZHIPU_API_KEY` or `MIMIR_ZHIPU_API_KEY` is required when `llm` or `web_search` runs in `real` mode.
- `JINA_API_KEY` or `MIMIR_JINA_API_KEY` is required when `web_fetch` runs in `real` mode. Jina Reader base URL defaults to `https://r.jina.ai/` and can be overridden via `MIMIR_JINA_BASE_URL`.
- `E2B_API_KEY` or `MIMIR_E2B_API_KEY` is required when the E2B sandbox runs in `real` mode. Request / execution / sandbox lifetime defaults can be overridden via `MIMIR_E2B_REQUEST_TIMEOUT_SECONDS`, `MIMIR_E2B_EXECUTION_TIMEOUT_SECONDS`, and `MIMIR_E2B_SANDBOX_TIMEOUT_SECONDS`.
- `MIMIR_E2B_TEMPLATE` is optional. When set, the real E2B adapter creates sandboxes from that published template name/alias; the intended Mimir template preinstalls `Noto Sans CJK SC` for Chinese charts.
- Model IDs are configurable per agent role; the current default contract is `glm-5` for all roles unless you explicitly override them in local env.
- `MIMIR_WEB_SEARCH_ENGINE` defaults to `search_prime`, which matches the current architecture contract for Zhipu `web_search`.
- `MIMIR_WRITER_MAX_ROUNDS` controls the writer tool-call round limit. Default is `5`; if the final allowed round still returns `tool_calls`, the task now fails instead of silently delivering an empty report.

## Deploy contract

- Deployment target: `Railway`
- Root Directory: `/services/api`
- Config file path: `/services/api/railway.json`
- Build command: `uv sync --frozen --no-dev`
- Pre-deploy command: `uv run --no-sync alembic upgrade head`
- Start command: `uv run --no-sync uvicorn app.main:app --host 0.0.0.0 --port ${PORT}`
- Healthcheck path: `/api/v1/health`

Production required env:

- `MIMIR_PROVIDER_MODE=real`
- `MIMIR_DATABASE_URL`
- `MIMIR_CORS_ALLOW_ORIGINS`
- `MIMIR_TASK_TOKEN_SECRET`
- `MIMIR_ACCESS_TOKEN_SECRET`
- `ZHIPU_API_KEY`
- `JINA_API_KEY`
- `E2B_API_KEY`

Artifact / storage contract:

- 当前文件制品实现仍走本地文件系统 artifact store。
- Railway 生产环境应挂载 Volume；若存在 `RAILWAY_VOLUME_MOUNT_PATH`，应用会默认把 artifact root 收敛到 `${RAILWAY_VOLUME_MOUNT_PATH}/mimir-artifacts`。
- 若需要自定义目录，可显式设置 `MIMIR_ARTIFACT_ROOT_DIR`。

完整 env matrix、CORS、download/access-token 约束见 [docs/Deploy_Contract.md](/Users/aminer/Library/CloudStorage/OneDrive-个人/projects/Mimir/docs/Deploy_Contract.md)。

## E2B template

- Template definition lives in [e2b_template/e2b.Dockerfile](/Users/aminer/Library/CloudStorage/OneDrive-个人/projects/Mimir/services/api/e2b_template/e2b.Dockerfile).
- Controlled font asset lives in [assets/fonts/NotoSansCJKsc-Regular.otf](/Users/aminer/Library/CloudStorage/OneDrive-个人/projects/Mimir/services/api/assets/fonts/NotoSansCJKsc-Regular.otf).
- Build/publish the template with the E2B CLI, then set `MIMIR_E2B_TEMPLATE` to the published template name before running the real E2B adapter.
