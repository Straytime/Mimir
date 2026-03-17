# scripts

Repository automation and helper scripts.

## dev.sh

Local development entry point. Detects or starts PostgreSQL, runs Alembic
migrations, then launches the API and Web dev servers in parallel.

```bash
./scripts/dev.sh          # start everything (DB + migrate + API + Web)
./scripts/dev.sh stop     # stop Docker Compose services (PostgreSQL)
./scripts/dev.sh migrate  # run Alembic migrations only
```

If PostgreSQL is already listening on port 5432 (e.g. via Homebrew), the
script skips Docker Compose and uses the existing instance. If PostgreSQL is
not running and Docker is available, it starts PostgreSQL via `compose.yaml`.

Prerequisites: `uv`, `pnpm`. Docker is only required if no local PostgreSQL
is available. Ports 5432, 8000, 3000 must be available.
