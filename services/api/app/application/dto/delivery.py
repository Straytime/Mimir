from dataclasses import dataclass
from datetime import datetime

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


@dataclass(frozen=True, slots=True)
class SandboxExecutionResult:
    stdout: str
    artifacts: tuple[GeneratedArtifact, ...]


@dataclass(frozen=True, slots=True)
class WriterDecision:
    text: str
    tool_calls: tuple[WriterToolCall, ...]
