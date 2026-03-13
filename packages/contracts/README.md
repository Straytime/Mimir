# @mimir/contracts

Shared contract workspace package for Mimir.

## Current responsibility

- act as the single workspace entrypoint for future shared API contract artifacts
- host source-aligned or generated contract types derived from `docs/OpenAPI_v1.md`
- avoid introducing new schema fields or business logic during M0-001

## Current state

- the package boundary and entrypoint exist
- the exported surface is intentionally empty until a later contract-first task defines concrete types
- downstream code should treat this package as the only future source for shared JS/TS contract imports
