# Mimir Production Database Schema Reference

Source of truth: `services/api/app/infrastructure/db/models.py`

Always verify field names against this reference before writing queries. Field names listed here reflect the actual SQLAlchemy column definitions.

## Tables

### research_tasks

| Column | Type | Notes |
|---|---|---|
| task_id | String(64) | PK |
| trace_id | String(64) | Unique |
| status | String(32) | Task lifecycle status |
| phase | String(64) | Current phase |
| clarification_mode | String(32) | |
| initial_query | Text | User's original question |
| client_timezone | String(128) | |
| client_locale | String(32) | |
| ip_hash | String(128) | Hashed client IP |
| task_token_hash | String(128) | Hashed task token |
| active_revision_id | String(64) | Currently active revision |
| active_revision_number | Integer | |
| created_at | DateTime(tz) | |
| updated_at | DateTime(tz) | |
| expires_at | DateTime(tz) | Nullable — when delivery expires |
| cleanup_pending | Boolean | True when scheduled for deletion |
| connect_deadline_at | DateTime(tz) | SSE connection deadline |

### task_revisions

| Column | Type | Notes |
|---|---|---|
| revision_id | String(64) | PK |
| task_id | String(64) | FK → research_tasks (CASCADE) |
| revision_number | Integer | Unique per task |
| revision_status | String(32) | |
| started_at | DateTime(tz) | |
| finished_at | DateTime(tz) | Nullable |
| requirement_detail_json | JSONB | Nullable — parsed requirements |
| collect_agent_calls_used | Integer | Counter for collector invocations |
| sandbox_id | String(128) | Nullable — E2B sandbox ID |

### task_events

| Column | Type | Notes |
|---|---|---|
| task_id | String(64) | PK (composite), FK → research_tasks (CASCADE) |
| seq | Integer | PK (composite) — ordering key |
| event | String(128) | Event type identifier |
| revision_id | String(64) | Nullable |
| phase | String(64) | Phase when event occurred |
| payload_json | JSONB | Event payload (NOT "payload") |
| created_at | DateTime(tz) | (NOT "timestamp") |

### agent_runs

| Column | Type | Notes |
|---|---|---|
| id | Integer | PK, autoincrement |
| task_id | String(64) | FK → research_tasks (CASCADE) |
| revision_id | String(64) | FK → task_revisions (CASCADE) |
| subtask_id | String(64) | Nullable |
| agent_type | String(32) | e.g. planner, collector, summary, outline, writer |
| prompt_name | String(128) | Which prompt was used |
| status | String(32) | Nullable |
| reasoning_text | Text | Nullable — LLM thinking output |
| content_text | Text | Nullable — LLM content output |
| finish_reason | String(64) | Nullable |
| provider_finish_reason | String(64) | Nullable |
| provider_usage_json | JSONB | Nullable — token counts etc. |
| tool_calls_json | JSONB | Nullable — tool calls issued by LLM |
| compressed | Boolean | Whether content was compressed |
| created_at | DateTime(tz) | |
| updated_at | DateTime(tz) | |

### task_tool_calls

| Column | Type | Notes |
|---|---|---|
| id | Integer | PK, autoincrement |
| task_id | String(64) | FK → research_tasks (CASCADE) |
| revision_id | String(64) | FK → task_revisions (CASCADE) |
| subtask_id | String(64) | Nullable |
| tool_call_id | String(64) | Nullable |
| tool_name | String(64) | e.g. web_search, web_fetch, python_interpreter |
| status | String(32) | |
| error_code | String(64) | Nullable |
| request_json | JSONB | Tool call arguments |
| response_json | JSONB | Nullable — tool execution result |
| created_at | DateTime(tz) | |

### collected_sources

| Column | Type | Notes |
|---|---|---|
| id | Integer | PK, autoincrement |
| task_id | String(64) | FK → research_tasks (CASCADE) |
| revision_id | String(64) | FK → task_revisions (CASCADE) |
| subtask_id | String(64) | |
| tool_call_id | String(64) | |
| title | Text | |
| link | Text | |
| info | Text | |
| source_key | String(512) | |
| refer | String(64) | Nullable |
| is_merged | Boolean | |
| created_at | DateTime(tz) | |

### artifacts

| Column | Type | Notes |
|---|---|---|
| artifact_id | String(64) | PK |
| task_id | String(64) | FK → research_tasks (CASCADE) |
| revision_id | String(64) | FK → task_revisions (CASCADE) |
| resource_type | String(32) | e.g. zip, pdf |
| filename | Text | |
| mime_type | String(128) | |
| storage_key | Text | Object storage path |
| byte_size | Integer | |
| metadata_json | JSONB | Nullable |
| created_at | DateTime(tz) | |

### llm_call_traces

| Column | Type | Notes |
|---|---|---|
| id | Integer | PK, autoincrement |
| task_id | String(64) | Nullable |
| revision_id | String(64) | Nullable |
| stage | String(64) | e.g. planner, collector, writer |
| model | String(128) | Model identifier used |
| request_json | JSONB | Full LLM request |
| response_json | JSONB | Full LLM response |
| parsed_text | Text | Nullable |
| reasoning_text | Text | Nullable |
| tool_calls_json | JSONB | Nullable |
| provider_finish_reason | String(64) | Nullable |
| provider_usage_json | JSONB | Nullable |
| request_id | String(128) | Nullable |
| created_at | DateTime(tz) | |

## Common Field Name Mistakes

These are real field names that get frequently confused:

| Wrong | Correct | Table |
|---|---|---|
| `payload` | `payload_json` | task_events |
| `timestamp` | `created_at` | task_events |
| `status` (on task_events) | Does not exist | task_events has no status column |
| `content` | `content_text` | agent_runs |
| `tool_calls` | `tool_calls_json` | agent_runs, llm_call_traces |
| `request` / `response` | `request_json` / `response_json` | task_tool_calls, llm_call_traces |

## Useful Indexes

- `ix_task_events_task_id_seq` — Fast event timeline queries
- `ix_agent_runs_revision_id_created_at` — Agent runs by revision
- `ix_task_tool_calls_revision_id_created_at` — Tool calls by revision
- `ix_artifacts_revision_id_created_at` — Artifacts by revision
- `ix_llm_call_traces_task_id_created_at` — LLM traces by task
