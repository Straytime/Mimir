from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base


class ResearchTaskRecord(Base):
    __tablename__ = "research_tasks"

    task_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    trace_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    phase: Mapped[str] = mapped_column(String(64), nullable=False)
    clarification_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    initial_query: Mapped[str] = mapped_column(Text, nullable=False)
    client_timezone: Mapped[str] = mapped_column(String(128), nullable=False)
    client_locale: Mapped[str] = mapped_column(String(32), nullable=False)
    ip_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    task_token_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    active_revision_id: Mapped[str] = mapped_column(String(64), nullable=False)
    active_revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cleanup_pending: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    connect_deadline_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )


class TaskRevisionRecord(Base):
    __tablename__ = "task_revisions"
    __table_args__ = (
        UniqueConstraint("task_id", "revision_number", name="uq_task_revision_number"),
    )

    revision_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    task_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("research_tasks.task_id", ondelete="CASCADE"),
        nullable=False,
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    revision_status: Mapped[str] = mapped_column(String(32), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    requirement_detail_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    collect_agent_calls_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sandbox_id: Mapped[str | None] = mapped_column(String(128))


class SystemLockRecord(Base):
    __tablename__ = "system_locks"

    lock_name: Mapped[str] = mapped_column(String(64), primary_key=True)
    task_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    acquired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class IPUsageCounterRecord(Base):
    __tablename__ = "ip_usage_counters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ip_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class TaskEventRecord(Base):
    __tablename__ = "task_events"

    task_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("research_tasks.task_id", ondelete="CASCADE"),
        primary_key=True,
    )
    seq: Mapped[int] = mapped_column(Integer, primary_key=True)
    event: Mapped[str] = mapped_column(String(128), nullable=False)
    revision_id: Mapped[str | None] = mapped_column(String(64))
    phase: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class TaskToolCallRecord(Base):
    __tablename__ = "task_tool_calls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("research_tasks.task_id", ondelete="CASCADE"),
        nullable=False,
    )
    revision_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("task_revisions.revision_id", ondelete="CASCADE"),
        nullable=False,
    )
    subtask_id: Mapped[str | None] = mapped_column(String(64))
    tool_call_id: Mapped[str | None] = mapped_column(String(64))
    tool_name: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(64))
    request_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    response_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CollectedSourceRecord(Base):
    __tablename__ = "collected_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("research_tasks.task_id", ondelete="CASCADE"),
        nullable=False,
    )
    revision_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("task_revisions.revision_id", ondelete="CASCADE"),
        nullable=False,
    )
    subtask_id: Mapped[str] = mapped_column(String(64), nullable=False)
    tool_call_id: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    link: Mapped[str] = mapped_column(Text, nullable=False)
    info: Mapped[str] = mapped_column(Text, nullable=False)
    source_key: Mapped[str] = mapped_column(String(512), nullable=False)
    refer: Mapped[str | None] = mapped_column(String(64))
    is_merged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AgentRunRecord(Base):
    __tablename__ = "agent_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("research_tasks.task_id", ondelete="CASCADE"),
        nullable=False,
    )
    revision_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("task_revisions.revision_id", ondelete="CASCADE"),
        nullable=False,
    )
    subtask_id: Mapped[str | None] = mapped_column(String(64))
    agent_type: Mapped[str] = mapped_column(String(32), nullable=False)
    prompt_name: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str | None] = mapped_column(String(32))
    reasoning_text: Mapped[str | None] = mapped_column(Text)
    content_text: Mapped[str | None] = mapped_column(Text)
    finish_reason: Mapped[str | None] = mapped_column(String(64))
    provider_finish_reason: Mapped[str | None] = mapped_column(String(64))
    provider_usage_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    tool_calls_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    compressed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ArtifactRecord(Base):
    __tablename__ = "artifacts"

    artifact_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    task_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("research_tasks.task_id", ondelete="CASCADE"),
        nullable=False,
    )
    revision_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("task_revisions.revision_id", ondelete="CASCADE"),
        nullable=False,
    )
    resource_type: Mapped[str] = mapped_column(String(32), nullable=False)
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


Index("ix_ip_usage_counters_ip_hash_created_at", IPUsageCounterRecord.ip_hash, IPUsageCounterRecord.created_at)
Index("ix_research_tasks_cleanup_pending_updated_at", ResearchTaskRecord.cleanup_pending, ResearchTaskRecord.updated_at)
Index("ix_task_events_task_id_seq", TaskEventRecord.task_id, TaskEventRecord.seq)
Index("ix_task_tool_calls_revision_id_created_at", TaskToolCallRecord.revision_id, TaskToolCallRecord.created_at)
Index("ix_collected_sources_revision_id_created_at", CollectedSourceRecord.revision_id, CollectedSourceRecord.created_at)
Index("ix_agent_runs_revision_id_created_at", AgentRunRecord.revision_id, AgentRunRecord.created_at)
Index("ix_artifacts_revision_id_created_at", ArtifactRecord.revision_id, ArtifactRecord.created_at)
