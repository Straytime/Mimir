"""Add unified LLM call trace retention table.

Revision ID: 20260324_0007
Revises: 20260323_0006
Create Date: 2026-03-24 18:20:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260324_0007"
down_revision: str | None = "20260323_0006"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "llm_call_traces",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("task_id", sa.String(length=64), nullable=True),
        sa.Column("revision_id", sa.String(length=64), nullable=True),
        sa.Column("stage", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column(
            "request_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "response_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("parsed_text", sa.Text(), nullable=True),
        sa.Column("reasoning_text", sa.Text(), nullable=True),
        sa.Column(
            "tool_calls_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("provider_finish_reason", sa.String(length=64), nullable=True),
        sa.Column(
            "provider_usage_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("request_id", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_llm_call_traces_created_at",
        "llm_call_traces",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_llm_call_traces_task_id_created_at",
        "llm_call_traces",
        ["task_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_llm_call_traces_task_id_created_at", table_name="llm_call_traces")
    op.drop_index("ix_llm_call_traces_created_at", table_name="llm_call_traces")
    op.drop_table("llm_call_traces")
