# Mimir

This repository currently holds the design docs and the M0-001 monorepo skeleton.

## Workspace layout

- `apps/web`: reserved for the Next.js App Router frontend described in `docs/Architecture.md`
- `services/api`: reserved for the FastAPI backend described in `docs/Architecture.md`
- `packages/contracts`: shared JS/TS workspace package for API contracts and generated artifacts
- `scripts`: repository-level automation and helper scripts
- `docs`: source-of-truth design and implementation documents

## Scope guardrails

- The root JS workspace uses `pnpm-workspace.yaml`.
- The default toolchain split is `pnpm` for the JS workspace and `uv` for Python package and virtual environment management.
- `services/api` is intentionally not modeled as a `pnpm` package; backend tooling stays package-local once the Python service is scaffolded.
- No frontend app, backend app, or business contract schema is initialized in this task.
- Future behavior changes must continue to follow docs first, then tests, then implementation.
