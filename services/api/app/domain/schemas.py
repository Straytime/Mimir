from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.enums import (
    AvailableAction,
    ClarificationMode,
    CollectSummaryStatus,
    FreshnessRequirement,
    OutputFormat,
    RevisionStatus,
    TaskPhase,
    TaskStatus,
)
from app.domain.state_machine import TaskStateMachine


class DomainModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class RequirementDetail(DomainModel):
    research_goal: str = Field(min_length=1)
    domain: str = Field(min_length=1)
    requirement_details: str = Field(min_length=1)
    output_format: OutputFormat
    freshness_requirement: FreshnessRequirement
    language: str = Field(min_length=1)
    raw_llm_output: dict[str, Any] | None = None


class RevisionSummary(DomainModel):
    revision_id: str = Field(min_length=1)
    revision_number: int = Field(ge=1)
    revision_status: RevisionStatus
    started_at: datetime
    finished_at: datetime | None = None
    requirement_detail: RequirementDetail | None = None

    @model_validator(mode="after")
    def validate_timestamps(self) -> "RevisionSummary":
        if self.finished_at is not None and self.finished_at < self.started_at:
            raise ValueError("finished_at must not be earlier than started_at")
        return self


class TaskSnapshot(DomainModel):
    task_id: str = Field(min_length=1)
    status: TaskStatus
    phase: TaskPhase
    active_revision_id: str = Field(min_length=1)
    active_revision_number: int = Field(ge=1)
    clarification_mode: ClarificationMode
    created_at: datetime
    updated_at: datetime
    expires_at: datetime | None = None
    available_actions: list[AvailableAction] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_snapshot(self) -> "TaskSnapshot":
        TaskStateMachine.ensure_public_state(status=self.status, phase=self.phase)
        if self.updated_at < self.created_at:
            raise ValueError("updated_at must not be earlier than created_at")
        if self.expires_at is not None and self.expires_at < self.updated_at:
            raise ValueError("expires_at must not be earlier than updated_at")
        return self


class CollectPlan(DomainModel):
    tool_call_id: str = Field(min_length=1)
    revision_id: str = Field(min_length=1)
    collect_target: str = Field(min_length=1)
    additional_info: str = ""
    freshness_requirement: FreshnessRequirement


class CollectSummary(DomainModel):
    tool_call_id: str = Field(min_length=1)
    subtask_id: str = Field(min_length=1)
    collect_target: str | None = None
    status: CollectSummaryStatus
    search_queries: list[str] = Field(default_factory=list)
    key_findings_markdown: str | None = None
    message: str | None = None
    additional_info: str | None = None
    freshness_requirement: str | None = None

    @model_validator(mode="after")
    def validate_shape(self) -> "CollectSummary":
        if self.status is CollectSummaryStatus.RISK_BLOCKED:
            if not self.message:
                raise ValueError("risk_blocked summary requires a message")
            return self

        if not self.collect_target:
            raise ValueError("collect_target is required unless status is risk_blocked")
        if not self.key_findings_markdown:
            raise ValueError(
                "key_findings_markdown is required unless status is risk_blocked"
            )
        return self


class EventEnvelope(DomainModel):
    seq: int = Field(ge=1)
    event: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    revision_id: str | None = None
    phase: TaskPhase
    timestamp: datetime
    payload: dict[str, Any] = Field(default_factory=dict)
