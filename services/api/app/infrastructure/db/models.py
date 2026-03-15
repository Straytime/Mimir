from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
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
    connect_deadline_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )


class TaskRevisionRecord(Base):
    __tablename__ = "task_revisions"

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


Index("ix_ip_usage_counters_ip_hash_created_at", IPUsageCounterRecord.ip_hash, IPUsageCounterRecord.created_at)
