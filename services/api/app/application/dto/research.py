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
    request_id: str | None = None
    provider_finish_reason: str | None = None
    provider_usage: dict[str, Any] | None = None
    request_payload: dict[str, Any] | None = None
    response_payload: dict[str, Any] | None = None
    tool_calls_json: tuple[dict[str, Any], ...] = ()


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
    request_id: str | None = None
    provider_finish_reason: str | None = None
    provider_usage: dict[str, Any] | None = None
    request_payload: dict[str, Any] | None = None
    response_payload: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class SearchHit:
    title: str
    link: str
    snippet: str
    publish_date: str | None = None


@dataclass(frozen=True, slots=True)
class SearchResponse:
    query: str
    recency_filter: str
    results: tuple[SearchHit, ...]


def build_web_search_tool_payload(
    search_response: SearchResponse | None,
    *,
    search_query: str | None = None,
    search_recency_filter: str | None = None,
    error_code: str | None = None,
) -> dict[str, Any]:
    if search_response is not None:
        payload: dict[str, Any] = {
            "success": True,
            "search_query": search_response.query,
            "search_recency_filter": search_response.recency_filter,
            "results": [
                {
                    "title": result.title,
                    "link": result.link,
                    "snippet": result.snippet,
                    "publish_date": result.publish_date,
                }
                for result in search_response.results
            ],
        }
    else:
        payload = {
            "success": False,
            "search_query": search_query or "",
            "search_recency_filter": search_recency_filter or "noLimit",
            "results": [],
        }
    if error_code is not None:
        payload["error_code"] = error_code
    return payload


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
    request_id: str | None = None
    provider_finish_reason: str | None = None
    provider_usage: dict[str, Any] | None = None
    request_payload: dict[str, Any] | None = None
    response_payload: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class FormattedSource:
    refer: str
    title: str
    link: str
    info: str
