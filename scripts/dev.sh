#!/usr/bin/env bash
# scripts/dev.sh — Local development entry point for Mimir.
#
# Starts PostgreSQL (via Docker Compose or detects an existing instance),
# runs Alembic migrations, then launches the API and Web dev servers.
#
# Usage:
#   ./scripts/dev.sh          # start everything
#   ./scripts/dev.sh stop     # stop Docker Compose services
#   ./scripts/dev.sh migrate  # run migrations only
#
# Prerequisites:
#   - Docker (for PostgreSQL) — or a local PostgreSQL already listening on 5432
#   - uv (Python package manager)
#   - pnpm (Node package manager)
#   - Port 5432 (PostgreSQL), 8000 (API), 3000 (Web) available

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
API_DIR="$REPO_ROOT/services/api"
WEB_DIR="$REPO_ROOT/apps/web"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[dev]${NC} $*"; }
warn() { echo -e "${YELLOW}[dev]${NC} $*"; }
err()  { echo -e "${RED}[dev]${NC} $*" >&2; }

# ---------- helpers ----------

check_prerequisites() {
  local missing=0
  for cmd in pnpm uv; do
    if ! command -v "$cmd" &>/dev/null; then
      err "Required command not found: $cmd"
      missing=1
    fi
  done
  if [ "$missing" -eq 1 ]; then
    exit 1
  fi
}

pg_is_ready() {
  # Check if PostgreSQL is already accepting connections on 5432.
  if command -v pg_isready &>/dev/null; then
    pg_isready -h 127.0.0.1 -p 5432 -q 2>/dev/null
  else
    # Fallback: try a TCP connect
    (echo >/dev/tcp/127.0.0.1/5432) 2>/dev/null
  fi
}

start_postgres() {
  if pg_is_ready; then
    log "PostgreSQL already running on localhost:5432 — skipping Docker Compose."
    return
  fi

  if ! command -v docker &>/dev/null; then
    err "PostgreSQL is not running on :5432 and Docker is not installed."
    err "Please start PostgreSQL manually or install Docker."
    exit 1
  fi

  log "Starting PostgreSQL via Docker Compose..."
  docker compose -f "$REPO_ROOT/compose.yaml" up -d --wait
  log "PostgreSQL is ready on localhost:5432"
}

run_migrations() {
  log "Running Alembic migrations..."
  cd "$API_DIR"
  uv run alembic upgrade head
  log "Migrations complete."
}

ensure_web_env() {
  if [ ! -f "$WEB_DIR/.env.local" ]; then
    warn ".env.local not found in apps/web — copying from .env.local.example"
    cp "$WEB_DIR/.env.local.example" "$WEB_DIR/.env.local"
  fi
}

start_api() {
  log "Starting API server on http://localhost:8000 ..."
  cd "$API_DIR"
  MIMIR_PROVIDER_MODE=stub \
    uv run --group dev uvicorn app.main:app \
      --host 127.0.0.1 --port 8000 --reload &
  API_PID=$!
}

start_web() {
  log "Starting Web dev server on http://localhost:3000 ..."
  cd "$WEB_DIR"
  pnpm dev &
  WEB_PID=$!
}

stop_services() {
  if command -v docker &>/dev/null; then
    log "Stopping Docker Compose services..."
    docker compose -f "$REPO_ROOT/compose.yaml" down 2>/dev/null || true
  fi
  log "Done. If PostgreSQL was started outside Docker, stop it manually."
}

cleanup() {
  log "Shutting down..."
  [ -n "${API_PID:-}" ] && kill "$API_PID" 2>/dev/null || true
  [ -n "${WEB_PID:-}" ] && kill "$WEB_PID" 2>/dev/null || true
  wait 2>/dev/null || true
  log "All processes stopped."
}

# ---------- main ----------

case "${1:-start}" in
  stop)
    stop_services
    ;;
  migrate)
    check_prerequisites
    run_migrations
    ;;
  start|"")
    check_prerequisites
    start_postgres
    run_migrations
    ensure_web_env
    trap cleanup EXIT INT TERM
    start_api
    start_web
    log "=== Mimir local dev is running ==="
    log "  Web:  http://localhost:3000"
    log "  API:  http://localhost:8000"
    log "  DB:   postgresql://postgres@localhost:5432/postgres"
    log "  Mode: stub (no real provider keys required)"
    log ""
    log "Press Ctrl+C to stop API and Web servers."
    log "Run './scripts/dev.sh stop' to also stop PostgreSQL (Docker only)."
    wait
    ;;
  *)
    echo "Usage: $0 [start|stop|migrate]"
    exit 1
    ;;
esac
