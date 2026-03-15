from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import ClarificationMode
from app.domain.schemas import RevisionSummary, TaskSnapshot


class ApiDto(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ResearchConfig(ApiDto):
    clarification_mode: ClarificationMode


class TaskClientInfo(ApiDto):
    timezone: str = Field(min_length=1)
    locale: str = Field(default="zh-CN", min_length=1)


class CreateTaskRequest(ApiDto):
    initial_query: str = Field(min_length=1, max_length=500)
    config: ResearchConfig
    client: TaskClientInfo


class TaskUrls(ApiDto):
    events: str
    heartbeat: str
    disconnect: str


class CreateTaskResponse(ApiDto):
    task_id: str
    task_token: str
    trace_id: str
    snapshot: TaskSnapshot
    urls: TaskUrls
    connect_deadline_at: datetime


class ArtifactSummary(ApiDto):
    artifact_id: str
    filename: str
    mime_type: str
    url: str
    access_expires_at: datetime


class DeliverySummary(ApiDto):
    revision_id: str
    revision_number: int = Field(ge=1)
    word_count: int = Field(ge=0)
    artifact_count: int = Field(ge=0)
    markdown_zip_url: str
    pdf_url: str
    artifacts: list[ArtifactSummary]


class TaskDetailResponse(ApiDto):
    task_id: str
    snapshot: TaskSnapshot
    current_revision: RevisionSummary
    delivery: DeliverySummary | None = None


class DisconnectRequestBody(ApiDto):
    reason: str = Field(min_length=1)
    task_token: str | None = None


class AcceptedResponse(ApiDto):
    accepted: bool
