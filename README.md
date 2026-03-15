# Mimir

This repository currently holds the design docs plus the M0 Stage 0 harness for the frontend and backend workspaces.

## Workspace layout

- `apps/web`: Next.js App Router Stage 0 harness with Vitest and Playwright test infrastructure
- `services/api`: FastAPI Stage 0 harness with the initial test infrastructure and health endpoint
- `packages/contracts`: shared JS/TS workspace package boundary for API contracts and generated artifacts
- `scripts`: repository-level automation and helper scripts
- `docs`: source-of-truth design and implementation documents

## Scope guardrails

- The root JS workspace uses `pnpm-workspace.yaml`.
- The default toolchain split is `pnpm` for the JS workspace and `uv` for Python package and virtual environment management.
- `services/api` is intentionally not modeled as a `pnpm` package; backend tooling stays package-local once the Python service is scaffolded.
- Frontend and backend are still limited to Stage 0 harness work; no research workflow business logic is implemented yet.
- Business contract schemas, REST/SSE workflow consumption, and frontend store/reducer logic are still intentionally pending later tasks.
- Future behavior changes must continue to follow docs first, then tests, then implementation.
