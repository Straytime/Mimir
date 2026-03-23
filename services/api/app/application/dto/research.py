from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.application.dto.invocation import (
    InvocationProfile,
    PromptBundle,
    PromptMessage,
    ToolSchema,
)
from app.domain.enums import CollectSummaryStatus
from app.domain.schemas import CollectPlan, CollectSummary, RequirementDetail


@dataclass(frozen=True, slots=True)
class PlannerInvocation:
    prompt_name: str
    requirement_detail: RequirementDetail
    summaries: tuple[CollectSummary, ...]
    call_index: int
    collect_agent_calls_used: int
    now: datetime
    transcript: tuple[PromptMessage, ...] = ()
    profile: InvocationProfile | None = None
    prompt_bundle: PromptBundle | None = None
    tool_schemas: tuple[ToolSchema, ...] = ()


@dataclass(frozen=True, slots=True)
class PlannerDecision:
    reasoning_deltas: tuple[str, ...]
    plans: tuple[CollectPlan, ...]
    stop: bool
    provider_finish_reason: str | None = None
    provider_usage: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class CollectorInvocation:
    prompt_name: str
    subtask_id: str
    plan: CollectPlan
    call_index: int
    tool_call_limit: int
    now: datetime
    transcript: tuple[PromptMessage, ...] = ()
    profile: InvocationProfile | None = None
    prompt_bundle: PromptBundle | None = None
    tool_schemas: tuple[ToolSchema, ...] = ()


@dataclass(frozen=True, slots=True)
class CollectorToolCall:
    tool_call_id: str
    tool_name: str
    arguments_json: dict[str, Any]


@dataclass(frozen=True, slots=True)
class CollectorDecision:
    reasoning_text: str
    content_text: str
    tool_calls: tuple[CollectorToolCall, ...]
    stop: bool
    items: tuple["CollectedSourceItem", ...] = ()
    provider_finish_reason: str | None = None
    provider_usage: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class SearchHit:
    title: str
    link: str
    snippet: str


@dataclass(frozen=True, slots=True)
class SearchResponse:
    query: str
    recency_filter: str
    results: tuple[SearchHit, ...]


@dataclass(frozen=True, slots=True)
class FetchResponse:
    url: str
    success: bool
    title: str | None
    content: str | None


@dataclass(frozen=True, slots=True)
class CollectedSourceItem:
    title: str
    link: str
    info: str


@dataclass(frozen=True, slots=True)
class CollectResult:
    subtask_id: str
    tool_call_id: str
    collect_target: str
    status: CollectSummaryStatus
    search_queries: tuple[str, ...]
    tool_call_count: int
    items: tuple[CollectedSourceItem, ...]


@dataclass(frozen=True, slots=True)
class SummaryInvocation:
    prompt_name: str
    subtask_id: str
    plan: CollectPlan
    result_status: str
    search_queries: tuple[str, ...]
    item_payloads: tuple[dict[str, str], ...]
    now: datetime
    profile: InvocationProfile | None = None
    prompt_bundle: PromptBundle | None = None
    tool_schemas: tuple[ToolSchema, ...] = ()


@dataclass(frozen=True, slots=True)
class SummaryDecision:
    status: CollectSummaryStatus
    key_findings_markdown: str | None = None
    message: str | None = None
    provider_finish_reason: str | None = None
    provider_usage: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class FormattedSource:
    refer: str
    title: str
    link: str
    info: str
