---
name: prod-debug
description: >
  Mimir production environment troubleshooting and data extraction via Railway.
  Covers: investigating failed research tasks, exporting LLM call history,
  querying production DB (research_tasks, task_events, agent_runs, artifacts, etc.),
  reading Railway application logs, and cross-confirming data between app and DB containers.
  Use this skill whenever the user mentions production issues, failed tasks, production logs,
  production data export, Railway SSH debugging, or any investigation that requires
  accessing the live Mimir deployment — even if they don't say "production" explicitly
  but reference a specific task_id or describe a user-facing failure.
allowed-tools: Bash(railway:*), Bash(cat:*), Bash(python:*), Bash(which:*), Read, Write, Grep, Glob
---

# Mimir Production Troubleshooting

This skill guides production investigation for the Mimir deep research platform deployed on Railway. All operations are **read-only** — never mutate production data during troubleshooting.

## Core Principles

1. **Data before conclusions** — Collect raw evidence (DB records, logs, events) before forming hypotheses about what went wrong.
2. **30-minute TTL** — Delivered tasks are cleaned up ~30 minutes after delivery. If you need to investigate writer/delivery issues, sample data immediately while the task is still alive.
3. **No secrets in output** — Never paste API keys, tokens, or connection strings in reports, execution logs, PRs, or conversation output. Record only variable names, existence, and sanitized fragments.
4. **Cross-confirm** — A single data source is not authoritative. Always cross-confirm between the app container (ORM queries) and the Postgres container (raw SQL).
5. **Schema-first** — Before querying, verify field names against the current codebase models. Read `references/db_schema.md` for the authoritative field list.

## Investigation Sequence

Follow this order strictly. Do not skip ahead to implementation hypotheses.

### Step 1: Establish Railway Context

```bash
railway status --json
```

Confirm you're pointed at the correct project/environment. If not, use `--project` and `--environment` flags.

### Step 2: Check Environment Configuration

```bash
railway variable list --service mimir-api --environment production --json
```

Review relevant variables exist and are non-empty. **Do not copy variable values into any output** — only note whether they exist and are populated.

### Step 3: Sample Database Records

This is the most critical step. The sampling order is fixed:

1. `research_tasks` — Get the task's current status, phase, active_revision_id
2. `task_revisions` — Get revision status, collect_agent_calls_used, sandbox_id
3. `task_events` — Full event timeline (ordered by seq)
4. `agent_runs` — LLM call history with content_text, reasoning_text, tool_calls_json
5. `task_tool_calls` — Tool execution results (web_search, web_fetch, etc.)
6. `collected_sources` — Gathered research sources
7. `artifacts` — Output files (zip, pdf)
8. `llm_call_traces` — Raw LLM request/response pairs (if deeper analysis needed)

#### How to Query: Two-Stage Export

For anything beyond a simple single-value lookup, use the two-stage export pattern. This avoids shell quoting nightmares and truncated output.

**Stage 1 — Write and execute a script inside the container:**

```bash
# Enter the container interactively
railway ssh --service mimir-api --environment production
```

Once inside:

```bash
cat > /tmp/investigate.py << 'PYEOF'
import json
from sqlalchemy import create_engine, text
from app.core.config import Settings

db_url = Settings.from_env().database_url
engine = create_engine(db_url)

TASK_ID = "<the-task-id>"

with engine.connect() as conn:
    # Example: get task events
    rows = conn.execute(
        text("SELECT seq, event, phase, revision_id, payload_json, created_at FROM task_events WHERE task_id = :tid ORDER BY seq"),
        {"tid": TASK_ID}
    ).fetchall()

    result = [dict(row._mapping) for row in rows]

with open("/tmp/task_events.json", "w") as f:
    json.dump(result, f, indent=2, default=str)

print(f"Exported {len(result)} events to /tmp/task_events.json")
PYEOF

/app/.venv/bin/python /tmp/investigate.py
```

**Stage 2 — Pull the file back to local machine:**

```bash
# From your LOCAL terminal (not inside the container)
railway ssh --service mimir-api --environment production cat /tmp/task_events.json > /tmp/task_events_local.json
```

#### Anti-Patterns to Avoid

- Do NOT stuff complex Python/SQL into a one-shot `railway ssh ... COMMAND` with heredocs and nested quotes
- Do NOT pipe large results directly to your local terminal — always write to a container file first
- Do NOT combine `railway ssh ... COMMAND` with local redirections in complex ways
- If you see Python REPL prompts, empty output, or truncated scripts, immediately switch to the `/tmp` script approach

### Step 4: Collect Railway Application Logs

```bash
# Save as NDJSON (NOT regular JSON)
railway logs --service mimir-api --environment production --json > /tmp/mimir_logs.ndjson
```

Parse NDJSON correctly:

```python
import json

with open("/tmp/mimir_logs.ndjson") as f:
    entries = [json.loads(line) for line in f if line.strip()]
```

Never use `json.load()` on the whole file — it's newline-delimited JSON, not a JSON array.

### Step 5: Cross-Confirm via Postgres Container

After getting data from the app container, verify counts and key records directly in Postgres:

```bash
railway ssh --service Postgres --environment production
```

Then:

```sql
psql -U postgres -d railway -P pager=off

-- Example: confirm event count matches
SELECT count(*) FROM task_events WHERE task_id = '<task-id>';

-- Example: confirm agent_runs
SELECT id, agent_type, prompt_name, status, created_at
FROM agent_runs
WHERE task_id = '<task-id>'
ORDER BY created_at;

-- Example: confirm artifacts
SELECT artifact_id, resource_type, filename, mime_type, byte_size
FROM artifacts
WHERE task_id = '<task-id>';
```

Do not treat app-container export as authoritative until cross-confirmed here.

### Step 6: Form Hypothesis and Report

Only after completing Steps 1-5 should you form conclusions. Your report should include:

- **Timeline**: Reconstructed from task_events (seq-ordered)
- **Failure point**: Which phase/stage failed
- **Root cause evidence**: Specific field values, error codes, or missing data
- **What's NOT yet determined**: Be explicit about gaps

## Delivery Failure Sub-Stage Isolation

When a failure occurs in the delivery phase, you must first identify which sub-stage failed before drawing any conclusions:

| Sub-stage | What to check |
|---|---|
| `writer` | `agent_runs` where `agent_type='writer'` — look at `content_text`, `tool_calls_json`, `finish_reason` |
| `export (zip/pdf)` | `artifacts` table — check if records exist, `byte_size > 0` |
| `artifact_store.put` | Application logs for storage errors |
| `token/download` | Application logs for access_token generation or download path errors |

Do not generalize as "report generation failed" without isolating the sub-stage.

## When the Task Has Been Cleaned Up

If the task's DB records have been deleted by cleanup:

1. **Stop** attempting DB queries for this task — they will return empty results
2. Fall back to **Railway application logs only** for timeline reconstruction
3. Explicitly state: "DB records for this task have been cleaned up. Analysis is limited to application logs and cannot reach content/tool/result-level detail."

## Cleanup After Investigation

When investigation is complete:

1. Delete temporary scripts and export files from the container `/tmp`
2. If local files contain production data, store them with minimal exposure and clean up after the investigation round

## Quick Reference: `railway connect` Caveat

`railway connect` requires a local `psql` binary. If it fails, that does NOT mean the production DB is unreachable — use `railway ssh --service Postgres --environment production` instead.
