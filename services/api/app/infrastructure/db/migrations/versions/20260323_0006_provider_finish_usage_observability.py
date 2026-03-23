"""Add provider finish reason and usage observability to agent runs.

Revision ID: 20260323_0006
Revises: 20260316_0005
Create Date: 2026-03-23 17:40:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260323_0006"
down_revision: str | None = "20260316_0005"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "agent_runs",
        sa.Column("provider_finish_reason", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "agent_runs",
        sa.Column(
            "provider_usage_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("agent_runs", "provider_usage_json")
    op.drop_column("agent_runs", "provider_finish_reason")
