from alembic import command
from sqlalchemy import inspect
from sqlalchemy.engine import create_engine


def test_stage_two_migrations_upgrade_and_downgrade(
    alembic_config,
    database_url: str,
) -> None:
    command.upgrade(alembic_config, "head")

    upgraded_engine = create_engine(database_url, future=True)
    try:
        upgraded_tables = set(inspect(upgraded_engine).get_table_names())
    finally:
        upgraded_engine.dispose()

    assert {
        "research_tasks",
        "task_revisions",
        "system_locks",
        "ip_usage_counters",
        "task_events",
        "task_tool_calls",
        "collected_sources",
        "agent_runs",
        "llm_call_traces",
        "artifacts",
    }.issubset(upgraded_tables)

    task_revision_columns = {
        column["name"]
        for column in inspect(upgraded_engine).get_columns("task_revisions")
    }
    assert "collect_agent_calls_used" in task_revision_columns
    assert "sandbox_id" in task_revision_columns

    research_task_columns = {
        column["name"]
        for column in inspect(upgraded_engine).get_columns("research_tasks")
    }
    assert "cleanup_pending" in research_task_columns

    agent_run_columns = {
        column["name"]
        for column in inspect(upgraded_engine).get_columns("agent_runs")
    }
    assert "provider_finish_reason" in agent_run_columns
    assert "provider_usage_json" in agent_run_columns

    llm_trace_columns = {
        column["name"]
        for column in inspect(upgraded_engine).get_columns("llm_call_traces")
    }
    assert "request_json" in llm_trace_columns
    assert "response_json" in llm_trace_columns
    assert "provider_finish_reason" in llm_trace_columns
    assert "provider_usage_json" in llm_trace_columns

    command.downgrade(alembic_config, "base")

    downgraded_engine = create_engine(database_url, future=True)
    try:
        downgraded_tables = set(inspect(downgraded_engine).get_table_names())
    finally:
        downgraded_engine.dispose()

    assert "research_tasks" not in downgraded_tables
    assert "task_revisions" not in downgraded_tables
    assert "system_locks" not in downgraded_tables
    assert "ip_usage_counters" not in downgraded_tables
    assert "task_events" not in downgraded_tables
    assert "task_tool_calls" not in downgraded_tables
    assert "collected_sources" not in downgraded_tables
    assert "agent_runs" not in downgraded_tables
    assert "llm_call_traces" not in downgraded_tables
    assert "artifacts" not in downgraded_tables
