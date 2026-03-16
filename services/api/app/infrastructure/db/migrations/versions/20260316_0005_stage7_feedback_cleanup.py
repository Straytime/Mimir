"""Stage 7 feedback cleanup hardening.

Revision ID: 20260316_0005
Revises: 20260316_0004
Create Date: 2026-03-16 18:45:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260316_0005"
down_revision: str | None = "20260316_0004"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "research_tasks",
        sa.Column(
            "cleanup_pending",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.alter_column("research_tasks", "cleanup_pending", server_default=None)
    op.create_index(
        "ix_research_tasks_cleanup_pending_updated_at",
        "research_tasks",
        ["cleanup_pending", "updated_at"],
    )
    op.add_column(
        "task_revisions",
        sa.Column("sandbox_id", sa.String(length=128), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("task_revisions", "sandbox_id")
    op.drop_index(
        "ix_research_tasks_cleanup_pending_updated_at",
        table_name="research_tasks",
    )
    op.drop_column("research_tasks", "cleanup_pending")
