"""Stage 2 tasks API shell tables.

Revision ID: 20260315_0001
Revises:
Create Date: 2026-03-15 20:40:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260315_0001"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "research_tasks",
        sa.Column("task_id", sa.String(length=64), primary_key=True),
        sa.Column("trace_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("phase", sa.String(length=64), nullable=False),
        sa.Column("clarification_mode", sa.String(length=32), nullable=False),
        sa.Column("initial_query", sa.Text(), nullable=False),
        sa.Column("client_timezone", sa.String(length=128), nullable=False),
        sa.Column("client_locale", sa.String(length=32), nullable=False),
        sa.Column("ip_hash", sa.String(length=128), nullable=False),
        sa.Column("task_token_hash", sa.String(length=128), nullable=False),
        sa.Column("active_revision_id", sa.String(length=64), nullable=False),
        sa.Column("active_revision_number", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("connect_deadline_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "task_revisions",
        sa.Column("revision_id", sa.String(length=64), primary_key=True),
        sa.Column(
            "task_id",
            sa.String(length=64),
            sa.ForeignKey("research_tasks.task_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("revision_status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("requirement_detail_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.UniqueConstraint("task_id", "revision_number", name="uq_task_revision_number"),
    )
    op.create_table(
        "system_locks",
        sa.Column("lock_name", sa.String(length=64), primary_key=True),
        sa.Column("task_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("acquired_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "ip_usage_counters",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("ip_hash", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_ip_usage_counters_ip_hash_created_at",
        "ip_usage_counters",
        ["ip_hash", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_ip_usage_counters_ip_hash_created_at", table_name="ip_usage_counters")
    op.drop_table("ip_usage_counters")
    op.drop_table("system_locks")
    op.drop_table("task_revisions")
    op.drop_table("research_tasks")
