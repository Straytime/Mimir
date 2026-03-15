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
    }.issubset(upgraded_tables)

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
