"""Stage 3 task event persistence.

Revision ID: 20260316_0002
Revises: 20260315_0001
Create Date: 2026-03-16 00:05:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260316_0002"
down_revision: str | None = "20260315_0001"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "task_events",
        sa.Column(
            "task_id",
            sa.String(length=64),
            sa.ForeignKey("research_tasks.task_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("seq", sa.Integer(), primary_key=True),
        sa.Column("event", sa.String(length=128), nullable=False),
        sa.Column("revision_id", sa.String(length=64), nullable=True),
        sa.Column("phase", sa.String(length=64), nullable=False),
        sa.Column(
            "payload_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_task_events_task_id_seq", "task_events", ["task_id", "seq"])


def downgrade() -> None:
    op.drop_index("ix_task_events_task_id_seq", table_name="task_events")
    op.drop_table("task_events")
