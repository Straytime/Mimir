from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.application.dto.invocation import InvocationProfile, PromptBundle, ToolSchema
from app.application.dto.research import FormattedSource
from app.domain.schemas import RequirementDetail


@dataclass(frozen=True, slots=True)
class OutlineSection:
    section_id: str
    title: str
    description: str
    order: int


@dataclass(frozen=True, slots=True)
class ResearchOutline:
    title: str
    sections: tuple[OutlineSection, ...]
    entities: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class OutlineInvocation:
    prompt_name: str
    requirement_detail: RequirementDetail
    formatted_sources: tuple[FormattedSource, ...]
    now: datetime
    profile: InvocationProfile | None = None
    prompt_bundle: PromptBundle | None = None
    tool_schemas: tuple[ToolSchema, ...] = ()


@dataclass(frozen=True, slots=True)
class OutlineDecision:
    deltas: tuple[str, ...]
    outline: ResearchOutline
    provider_finish_reason: str | None = None
    provider_usage: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class WriterToolCall:
    tool_call_id: str
    tool_name: str
    code: str


@dataclass(frozen=True, slots=True)
class WriterInvocation:
    prompt_name: str
    requirement_detail: RequirementDetail
    formatted_sources: tuple[FormattedSource, ...]
    outline: ResearchOutline
    now: datetime
    profile: InvocationProfile | None = None
    prompt_bundle: PromptBundle | None = None
    tool_schemas: tuple[ToolSchema, ...] = ()


@dataclass(frozen=True, slots=True)
class GeneratedArtifact:
    filename: str
    mime_type: str
    content: bytes


def build_canonical_artifact_path(artifact_id: str) -> str:
    return f"mimir://artifact/{artifact_id}"


@dataclass(frozen=True, slots=True)
class ToolResultArtifact:
    artifact_id: str
    filename: str
    mime_type: str
    canonical_path: str


@dataclass(frozen=True, slots=True)
class PythonToolResult:
    success: bool
    summary: str
    stdout: str
    stderr: str | None = None
    error_type: str | None = None
    error_message: str | None = None
    traceback_excerpt: str | None = None
    artifacts: tuple[ToolResultArtifact, ...] = ()


@dataclass(frozen=True, slots=True)
class SandboxExecutionResult:
    success: bool
    stdout: str
    stderr: str | None = None
    error_type: str | None = None
    error_message: str | None = None
    traceback_excerpt: str | None = None
    artifacts: tuple[GeneratedArtifact, ...] = ()


@dataclass(frozen=True, slots=True)
class WriterDecision:
    text: str
    tool_calls: tuple[WriterToolCall, ...]
    reasoning_text: str = ""
    provider_finish_reason: str | None = None
    provider_usage: dict[str, Any] | None = None
