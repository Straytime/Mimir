"""Stage 5 collection engine persistence.

Revision ID: 20260316_0003
Revises: 20260316_0002
Create Date: 2026-03-16 15:40:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260316_0003"
down_revision: str | None = "20260316_0002"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "task_revisions",
        sa.Column(
            "collect_agent_calls_used",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.alter_column("task_revisions", "collect_agent_calls_used", server_default=None)

    op.create_table(
        "task_tool_calls",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "task_id",
            sa.String(length=64),
            sa.ForeignKey("research_tasks.task_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "revision_id",
            sa.String(length=64),
            sa.ForeignKey("task_revisions.revision_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("subtask_id", sa.String(length=64), nullable=True),
        sa.Column("tool_call_id", sa.String(length=64), nullable=True),
        sa.Column("tool_name", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column(
            "request_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "response_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_task_tool_calls_revision_id_created_at",
        "task_tool_calls",
        ["revision_id", "created_at"],
    )

    op.create_table(
        "collected_sources",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "task_id",
            sa.String(length=64),
            sa.ForeignKey("research_tasks.task_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "revision_id",
            sa.String(length=64),
            sa.ForeignKey("task_revisions.revision_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("subtask_id", sa.String(length=64), nullable=False),
        sa.Column("tool_call_id", sa.String(length=64), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("link", sa.Text(), nullable=False),
        sa.Column("info", sa.Text(), nullable=False),
        sa.Column("source_key", sa.String(length=512), nullable=False),
        sa.Column("refer", sa.String(length=64), nullable=True),
        sa.Column("is_merged", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.alter_column("collected_sources", "is_merged", server_default=None)
    op.create_index(
        "ix_collected_sources_revision_id_created_at",
        "collected_sources",
        ["revision_id", "created_at"],
    )

    op.create_table(
        "agent_runs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "task_id",
            sa.String(length=64),
            sa.ForeignKey("research_tasks.task_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "revision_id",
            sa.String(length=64),
            sa.ForeignKey("task_revisions.revision_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("subtask_id", sa.String(length=64), nullable=True),
        sa.Column("agent_type", sa.String(length=32), nullable=False),
        sa.Column("prompt_name", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=True),
        sa.Column("reasoning_text", sa.Text(), nullable=True),
        sa.Column("content_text", sa.Text(), nullable=True),
        sa.Column("finish_reason", sa.String(length=64), nullable=True),
        sa.Column(
            "tool_calls_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("compressed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.alter_column("agent_runs", "compressed", server_default=None)
    op.create_index(
        "ix_agent_runs_revision_id_created_at",
        "agent_runs",
        ["revision_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_agent_runs_revision_id_created_at", table_name="agent_runs")
    op.drop_table("agent_runs")
    op.drop_index("ix_collected_sources_revision_id_created_at", table_name="collected_sources")
    op.drop_table("collected_sources")
    op.drop_index("ix_task_tool_calls_revision_id_created_at", table_name="task_tool_calls")
    op.drop_table("task_tool_calls")
    op.drop_column("task_revisions", "collect_agent_calls_used")
