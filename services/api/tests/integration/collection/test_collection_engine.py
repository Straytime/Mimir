import asyncio
import json
from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from types import SimpleNamespace

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.dto.research import (
    CollectedSourceItem,
    CollectorDecision,
    CollectorInvocation,
    CollectorToolCall,
    FetchResponse,
    PlannerDecision,
    PlannerInvocation,
    SearchHit,
    SearchResponse,
    SummaryDecision,
    SummaryInvocation,
)
from app.application.dto.delivery import (
    OutlineDecision,
    OutlineInvocation,
    ResearchOutline,
    WriterDecision,
    WriterInvocation,
)
from app.application.ports.delivery import E2BSandboxClient, OutlineAgent, WriterAgent
from app.application.ports.research import (
    CollectorAgent,
    PlannerAgent,
    SummaryAgent,
    WebFetchClient,
    WebSearchClient,
)
from app.application.services.invocation import (
    OperationTraceSnapshot,
    RetryableOperationError,
    RiskControlTriggered,
    TraceableOperationError,
)
from app.core.config import Settings
from app.domain.enums import CollectSummaryStatus, FreshnessRequirement
from app.domain.schemas import CollectPlan
from app.infrastructure.db.models import (
    AgentRunRecord,
    CollectedSourceRecord,
    LLMCallTraceRecord,
    ResearchTaskRecord,
    TaskRevisionRecord,
    TaskToolCallRecord,
)
from app.infrastructure.research.real_http import ZhipuPlannerAgent
from app.main import create_app
from tests.contract.rest.test_task_events import assert_stream_closed, read_sse_event, read_until_event
from tests.contract.rest.test_tasks import build_create_task_payload
from tests.fixtures.app import StreamingASGITransport
from tests.fixtures.runtime import FakeClock


@dataclass(slots=True)
class SearchScenario:
    results_by_query: dict[str, Sequence[SearchHit]]
    concurrent_calls: int = 0
    max_concurrent_calls: int = 0
    fail_once_queries: set[str] = field(default_factory=set)
    risk_queries: set[str] = field(default_factory=set)
    _attempts: dict[str, int] = field(default_factory=dict)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class ScriptedPlannerAgent(PlannerAgent):
    def __init__(self, rounds: Sequence[PlannerDecision]) -> None:
        self._rounds = list(rounds)
        self.invocations: list[PlannerInvocation] = []

    async def plan(self, invocation: PlannerInvocation) -> PlannerDecision:
        self.invocations.append(invocation)
        if not self._rounds:
            raise AssertionError("planner called more times than expected")
        return self._rounds.pop(0)


class QueuedChatCompletionsAPI:
    def __init__(self, responses: Sequence[object]) -> None:
        self._responses = list(responses)
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        if not self._responses:
            raise AssertionError("planner raw client called more times than expected")
        return self._responses.pop(0)


class QueuedZhipuClient:
    def __init__(self, responses: Sequence[object]) -> None:
        self.chat = SimpleNamespace(
            completions=QueuedChatCompletionsAPI(responses)
        )


class ScriptedCollectorAgent(CollectorAgent):
    def __init__(self, rounds_by_tool_call: dict[str, Sequence[CollectorDecision]]) -> None:
        self._rounds_by_tool_call = {
            key: list(rounds)
            for key, rounds in rounds_by_tool_call.items()
        }
        self.invocations: list[CollectorInvocation] = []
        self.invocations_by_tool_call: dict[str, list[CollectorInvocation]] = {}

    async def plan(self, invocation: CollectorInvocation) -> CollectorDecision:
        self.invocations.append(invocation)
        self.invocations_by_tool_call.setdefault(invocation.plan.tool_call_id, []).append(
            invocation
        )
        rounds = self._rounds_by_tool_call.get(invocation.plan.tool_call_id)
        if not rounds:
            raise AssertionError(
                f"collector called more times than expected: {invocation.plan.tool_call_id}"
            )
        return rounds.pop(0)


def _collector_search_round(
    *,
    tool_call_id: str,
    query: str,
    reasoning: str,
    recency_filter: str = "noLimit",
    provider_finish_reason: str | None = None,
    provider_usage: dict[str, object] | None = None,
) -> CollectorDecision:
    return CollectorDecision(
        reasoning_text=reasoning,
        content_text="",
        tool_calls=(
            CollectorToolCall(
                tool_call_id=tool_call_id,
                tool_name="web_search",
                arguments_json={
                    "search_query": query,
                    "search_recency_filter": recency_filter,
                },
            ),
        ),
        stop=False,
        items=(),
        provider_finish_reason=provider_finish_reason,
        provider_usage=provider_usage,
    )


def _collector_fetch_round(
    *,
    tool_call_id: str,
    url: str,
    reasoning: str,
    provider_finish_reason: str | None = None,
    provider_usage: dict[str, object] | None = None,
) -> CollectorDecision:
    return CollectorDecision(
        reasoning_text=reasoning,
        content_text="",
        tool_calls=(
            CollectorToolCall(
                tool_call_id=tool_call_id,
                tool_name="web_fetch",
                arguments_json={"url": url},
            ),
        ),
        stop=False,
        items=(),
        provider_finish_reason=provider_finish_reason,
        provider_usage=provider_usage,
    )


def _collector_stop_round(
    *,
    reasoning: str,
    items: Sequence[CollectedSourceItem],
    provider_finish_reason: str | None = None,
    provider_usage: dict[str, object] | None = None,
) -> CollectorDecision:
    return CollectorDecision(
        reasoning_text=reasoning,
        content_text="".join(
            [
                json.dumps(
                    [
                        {
                            "info": item.info,
                            "title": item.title,
                            "link": item.link,
                        }
                        for item in items
                    ],
                    ensure_ascii=False,
                )
            ]
        ),
        tool_calls=(),
        stop=True,
        items=tuple(items),
        provider_finish_reason=provider_finish_reason,
        provider_usage=provider_usage,
    )


class ScriptedSummaryAgent(SummaryAgent):
    def __init__(
        self,
        *,
        provider_finish_reason: str | None = None,
        provider_usage: dict[str, object] | None = None,
    ) -> None:
        self.invocations: list[SummaryInvocation] = []
        self.provider_finish_reason = provider_finish_reason
        self.provider_usage = provider_usage

    async def summarize(self, invocation: SummaryInvocation) -> SummaryDecision:
        self.invocations.append(invocation)
        return SummaryDecision(
            status=CollectSummaryStatus.COMPLETED,
            key_findings_markdown=f"- {invocation.plan.collect_target} 已完成总结。",
            provider_finish_reason=self.provider_finish_reason,
            provider_usage=self.provider_usage,
        )


class TraceFailingCollectorAgent(CollectorAgent):
    def __init__(self, *, parsed_text: str) -> None:
        self.parsed_text = parsed_text
        self.invocations: list[CollectorInvocation] = []

    async def plan(self, invocation: CollectorInvocation) -> CollectorDecision:
        self.invocations.append(invocation)
        raise TraceableOperationError(
            "zhipu returned invalid JSON",
            trace_snapshot=OperationTraceSnapshot(
                parsed_text=self.parsed_text,
                reasoning_text="collector failed to emit valid JSON",
                provider_finish_reason="stop",
                provider_usage_json={
                    "prompt_tokens": 22,
                    "completion_tokens": 11,
                    "total_tokens": 33,
                },
                request_id="req_collector_invalid",
                request_payload={"model": invocation.profile.model},
                response_payload={
                    "request_id": "req_collector_invalid",
                    "parsed_text": self.parsed_text,
                    "provider_finish_reason": "stop",
                },
            ),
        )


class TraceFailingSummaryAgent(SummaryAgent):
    def __init__(self, *, parsed_text: str) -> None:
        self.parsed_text = parsed_text
        self.invocations: list[SummaryInvocation] = []

    async def summarize(self, invocation: SummaryInvocation) -> SummaryDecision:
        self.invocations.append(invocation)
        raise TraceableOperationError(
            "zhipu returned invalid JSON",
            trace_snapshot=OperationTraceSnapshot(
                parsed_text=self.parsed_text,
                reasoning_text="summary failed to emit valid JSON",
                provider_finish_reason="stop",
                provider_usage_json={
                    "prompt_tokens": 18,
                    "completion_tokens": 7,
                    "total_tokens": 25,
                },
                request_id="req_summary_invalid",
                request_payload={"model": invocation.profile.model},
                response_payload={
                    "request_id": "req_summary_invalid",
                    "parsed_text": self.parsed_text,
                    "provider_finish_reason": "stop",
                },
            ),
        )


class ScriptedWebSearchClient(WebSearchClient):
    def __init__(self, scenario: SearchScenario) -> None:
        self.scenario = scenario

    async def search(self, query: str, recency_filter: str) -> SearchResponse:
        async with self.scenario._lock:
            self.scenario.concurrent_calls += 1
            self.scenario.max_concurrent_calls = max(
                self.scenario.max_concurrent_calls,
                self.scenario.concurrent_calls,
            )
            self.scenario._attempts[query] = self.scenario._attempts.get(query, 0) + 1
            attempt = self.scenario._attempts[query]

        await asyncio.sleep(0.02)

        async with self.scenario._lock:
            self.scenario.concurrent_calls -= 1

        if query in self.scenario.risk_queries:
            raise RiskControlTriggered("risk 1301")
        if query in self.scenario.fail_once_queries and attempt == 1:
            raise RetryableOperationError("temporary search failure")

        return SearchResponse(
            query=query,
            recency_filter=recency_filter,
            results=tuple(self.scenario.results_by_query.get(query, ())),
        )


class ScriptedWebFetchClient(WebFetchClient):
    def __init__(self, content_by_url: dict[str, FetchResponse]) -> None:
        self.content_by_url = content_by_url
        self.requests: list[str] = []

    async def fetch(self, url: str) -> FetchResponse:
        self.requests.append(url)
        await asyncio.sleep(0.01)
        return self.content_by_url[url]


class NoopOutlineAgent(OutlineAgent):
    async def prepare(self, invocation: OutlineInvocation) -> OutlineDecision:
        return OutlineDecision(
            deltas=(),
            outline=ResearchOutline(
                title="noop",
                sections=(),
                entities=(),
            ),
        )


class NoopWriterAgent(WriterAgent):
    async def write(self, invocation: WriterInvocation) -> WriterDecision:
        return WriterDecision(
            text="noop",
            tool_calls=(),
        )


class NoopSandboxClient(E2BSandboxClient):
    async def create(self) -> str:
        return "sandbox_noop"

    async def execute_python(self, sandbox_id: str, code: str):
        raise AssertionError("noop sandbox should not be used in Stage 5 tests")

    async def destroy(self, sandbox_id: str) -> None:
        return None


@pytest_asyncio.fixture
async def make_stage5_client(
    settings: Settings,
    fake_clock: FakeClock,
):
    apps_to_shutdown: list[FastAPI] = []

    async def _factory(
        *,
        planner_agent: PlannerAgent,
        collector_agent: CollectorAgent,
        summary_agent: SummaryAgent,
        web_search_client: WebSearchClient,
        web_fetch_client: WebFetchClient,
    ) -> AsyncClient:
        test_settings = replace(settings, llm_retry_wait_seconds=0)
        app = create_app(
            settings=test_settings,
            clock=fake_clock.now,
            planner_agent=planner_agent,
            collector_agent=collector_agent,
            summary_agent=summary_agent,
            web_search_client=web_search_client,
            web_fetch_client=web_fetch_client,
            outline_agent=NoopOutlineAgent(),
            writer_agent=NoopWriterAgent(),
            sandbox_client=NoopSandboxClient(),
        )
        await app.router.startup()
        apps_to_shutdown.append(app)
        transport = StreamingASGITransport(app=app, client=("203.0.113.10", 51000))
        client = AsyncClient(transport=transport, base_url="http://testserver")
        return client

    yield _factory

    for app in reversed(apps_to_shutdown):
        await app.state.task_lifecycle.shutdown()
        await app.router.shutdown()


async def _start_collection_flow(
    client: AsyncClient,
) -> tuple[dict[str, object], object]:
    create_response = await client.post(
        "/api/v1/tasks",
        json=build_create_task_payload(clarification_mode="natural"),
    )
    create_body = create_response.json()
    stream = client.stream(
        "GET",
        f"/api/v1/tasks/{create_body['task_id']}/events",
        headers={"Authorization": f"Bearer {create_body['task_token']}"},
    )
    response = await stream.__aenter__()
    lines = response.aiter_lines()
    await read_until_event(lines, {"clarification.natural.ready"})
    clarification_response = await client.post(
        f"/api/v1/tasks/{create_body['task_id']}/clarification",
        headers={"Authorization": f"Bearer {create_body['task_token']}"},
        json={
            "mode": "natural",
            "answer_text": "重点看中国市场，偏商业分析，覆盖近两年变化。",
        },
    )
    assert clarification_response.status_code == 202
    return create_body, (stream, response, lines)


async def _close_stream(stream_context, response) -> None:
    await stream_context.__aexit__(None, None, None)
    await response.aclose()


@pytest.mark.asyncio
async def test_full_collect_loop_runs_with_three_parallel_subtasks_and_barrier_merge(
    make_stage5_client,
    db_session: Session,
) -> None:
    planner = ScriptedPlannerAgent(
        rounds=[
            PlannerDecision(
                reasoning_deltas=("当前还缺少代表性玩家与市场趋势信息。",),
                plans=(
                    CollectPlan(
                        tool_call_id="call_1",
                        revision_id="rev_placeholder",
                        collect_target="收集主要玩家",
                        additional_info="官方与高可信媒体优先。",
                        freshness_requirement=FreshnessRequirement.HIGH,
                    ),
                    CollectPlan(
                        tool_call_id="call_2",
                        revision_id="rev_placeholder",
                        collect_target="收集市场趋势",
                        additional_info="关注近两年变化。",
                        freshness_requirement=FreshnessRequirement.HIGH,
                    ),
                    CollectPlan(
                        tool_call_id="call_3",
                        revision_id="rev_placeholder",
                        collect_target="收集商业机会",
                        additional_info="关注中国市场。",
                        freshness_requirement=FreshnessRequirement.HIGH,
                    ),
                ),
                stop=False,
            ),
            PlannerDecision(
                reasoning_deltas=("当前信息已足够进入 source merge。",),
                plans=(),
                stop=True,
            ),
        ]
    )
    collector = ScriptedCollectorAgent(
        rounds_by_tool_call={
            "call_1": (
                _collector_search_round(
                    tool_call_id="call_search_players",
                    query="q_players",
                    reasoning="先搜索主要玩家。",
                ),
                _collector_fetch_round(
                    tool_call_id="call_fetch_players_a",
                    url="https://example.com/a",
                    reasoning="需要读取来源 A。",
                ),
                _collector_fetch_round(
                    tool_call_id="call_fetch_players_shared",
                    url="https://example.com/shared",
                    reasoning="再读取共享来源。",
                ),
                _collector_stop_round(
                    reasoning="已有足够信息，结束收集。",
                    items=(
                        CollectedSourceItem(
                            title="来源 A",
                            link="https://example.com/a",
                            info="A 内容",
                        ),
                        CollectedSourceItem(
                            title="来源 Shared",
                            link="https://example.com/shared",
                            info="Shared 内容",
                        ),
                    ),
                ),
            ),
            "call_2": (
                _collector_search_round(
                    tool_call_id="call_search_trends",
                    query="q_trends",
                    reasoning="先搜索市场趋势。",
                ),
                _collector_fetch_round(
                    tool_call_id="call_fetch_trends_shared",
                    url="https://example.com/shared",
                    reasoning="读取共享趋势来源。",
                ),
                _collector_stop_round(
                    reasoning="趋势信息已足够。",
                    items=(
                        CollectedSourceItem(
                            title="来源 Shared",
                            link="https://example.com/shared",
                            info="Shared 内容",
                        ),
                    ),
                ),
            ),
            "call_3": (
                _collector_search_round(
                    tool_call_id="call_search_opportunities",
                    query="q_opportunities",
                    reasoning="搜索商业机会。",
                ),
                _collector_fetch_round(
                    tool_call_id="call_fetch_opportunities_c",
                    url="https://example.com/c",
                    reasoning="读取商业机会来源。",
                ),
                _collector_stop_round(
                    reasoning="商业机会信息已足够。",
                    items=(
                        CollectedSourceItem(
                            title="来源 C",
                            link="https://example.com/c",
                            info="C 内容",
                        ),
                    ),
                ),
            ),
        }
    )
    summarizer = ScriptedSummaryAgent()
    search = ScriptedWebSearchClient(
        SearchScenario(
            results_by_query={
                "q_players": (
                    SearchHit(
                        title="来源 A",
                        link="https://example.com/a",
                        snippet="A snippet",
                        publish_date="2025-06-10",
                    ),
                    SearchHit(
                        title="来源 Shared",
                        link="https://example.com/shared",
                        snippet="Shared snippet",
                    ),
                ),
                "q_trends": (
                    SearchHit(
                        title="来源 Shared 2",
                        link="https://example.com/shared",
                        snippet="Shared snippet 2",
                    ),
                ),
                "q_opportunities": (
                    SearchHit(
                        title="来源 C",
                        link="https://example.com/c",
                        snippet="C snippet",
                    ),
                ),
            }
        )
    )
    fetch = ScriptedWebFetchClient(
        content_by_url={
            "https://example.com/a": FetchResponse(
                url="https://example.com/a",
                success=True,
                title="来源 A",
                content="A 内容",
            ),
            "https://example.com/shared": FetchResponse(
                url="https://example.com/shared",
                success=True,
                title="来源 Shared",
                content="Shared 内容",
            ),
            "https://example.com/c": FetchResponse(
                url="https://example.com/c",
                success=True,
                title="来源 C",
                content="C 内容",
            ),
        }
    )
    client = await make_stage5_client(
        planner_agent=planner,
        collector_agent=collector,
        summary_agent=summarizer,
        web_search_client=search,
        web_fetch_client=fetch,
    )
    async with client:
        create_body, (stream_context, response, lines) = await _start_collection_flow(client)
        _, merged_name, merged_payload = await read_until_event(lines, {"sources.merged"})
        await _close_stream(stream_context, response)

    db_session.expire_all()
    revision = db_session.get(
        TaskRevisionRecord,
        create_body["snapshot"]["active_revision_id"],
    )
    merged_sources = list(
        db_session.scalars(
            select(CollectedSourceRecord)
            .where(CollectedSourceRecord.revision_id == create_body["snapshot"]["active_revision_id"])
            .where(CollectedSourceRecord.is_merged.is_(True))
            .order_by(CollectedSourceRecord.id.asc())
        )
    )
    agent_runs = list(
        db_session.scalars(
            select(AgentRunRecord)
            .where(AgentRunRecord.task_id == create_body["task_id"])
            .order_by(AgentRunRecord.id.asc())
        )
    )

    assert merged_name == "sources.merged"
    assert merged_payload["payload"] == {
        "source_count_before_merge": 4,
        "source_count_after_merge": 3,
        "reference_count": 3,
    }
    assert search.scenario.max_concurrent_calls == 3
    assert len(planner.invocations) == 2
    assert len(planner.invocations[1].summaries) == 3
    replay_transcript = planner.invocations[1].prompt_bundle.transcript
    assert replay_transcript is not None
    assert [message.role for message in replay_transcript] == [
        "assistant",
        "tool",
        "tool",
        "tool",
    ]
    assert replay_transcript[0].reasoning_content == "当前还缺少代表性玩家与市场趋势信息。"
    assert replay_transcript[0].tool_calls is not None
    assert [tc["id"] for tc in replay_transcript[0].tool_calls] == [
        "call_1",
        "call_2",
        "call_3",
    ]
    assert [message.tool_call_id for message in replay_transcript[1:]] == [
        "call_1",
        "call_2",
        "call_3",
    ]
    assert revision is not None
    assert revision.collect_agent_calls_used == 3
    assert [source.refer for source in merged_sources] == ["ref_1", "ref_2", "ref_3"]
    assert merged_sources[1].link == "https://example.com/shared"
    assert merged_sources[1].info == "Shared 内容"
    assert [run.agent_type for run in agent_runs].count("planner") == 2
    assert [run.agent_type for run in agent_runs].count("collector") == 10
    assert [run.agent_type for run in agent_runs].count("summary") == 3
    collector_replay_round_2 = collector.invocations_by_tool_call["call_1"][1].prompt_bundle.transcript
    assert collector_replay_round_2 is not None
    assert [message.role for message in collector_replay_round_2] == ["assistant", "tool"]
    assert collector_replay_round_2[0].reasoning_content == "先搜索主要玩家。"
    assert collector_replay_round_2[0].tool_calls is not None
    assert collector_replay_round_2[0].tool_calls[0]["function"]["name"] == "web_search"
    assert collector_replay_round_2[1].tool_call_id == "call_search_players"
    assert "\"q_players\"" in collector_replay_round_2[1].content
    assert "\"publish_date\": \"2025-06-10\"" in collector_replay_round_2[1].content
    collector_replay_round_3 = collector.invocations_by_tool_call["call_1"][2].prompt_bundle.transcript
    assert collector_replay_round_3 is not None
    assert [message.role for message in collector_replay_round_3] == [
        "assistant",
        "tool",
        "assistant",
        "tool",
    ]
    assert collector_replay_round_3[2].reasoning_content == "需要读取来源 A。"
    assert collector_replay_round_3[3].tool_call_id == "call_fetch_players_a"


@pytest.mark.asyncio
async def test_collection_persists_provider_finish_reason_and_usage_for_agent_runs(
    make_stage5_client,
    db_session: Session,
) -> None:
    planner = ScriptedPlannerAgent(
        rounds=[
            PlannerDecision(
                reasoning_deltas=("开始搜集。",),
                plans=(
                    CollectPlan(
                        tool_call_id="call_1",
                        revision_id="rev_placeholder",
                        collect_target="收集主要玩家",
                        additional_info="官方与高可信媒体优先。",
                        freshness_requirement=FreshnessRequirement.HIGH,
                    ),
                ),
                stop=False,
                provider_finish_reason="tool_calls",
                provider_usage={"prompt_tokens": 20, "completion_tokens": 10, "total_tokens": 30},
            ),
            PlannerDecision(
                reasoning_deltas=("准备进入 merge。",),
                plans=(),
                stop=True,
                provider_finish_reason="stop",
                provider_usage={"prompt_tokens": 12, "completion_tokens": 6, "total_tokens": 18},
            ),
        ]
    )
    collector = ScriptedCollectorAgent(
        rounds_by_tool_call={
            "call_1": (
                _collector_search_round(
                    tool_call_id="call_search_players",
                    query="q_players",
                    reasoning="先搜索主要玩家。",
                    provider_finish_reason="tool_calls",
                    provider_usage={"prompt_tokens": 21, "completion_tokens": 9, "total_tokens": 30},
                ),
                _collector_stop_round(
                    reasoning="当前信息已足够。",
                    items=(
                        CollectedSourceItem(
                            title="来源 A",
                            link="https://example.com/a",
                            info="A 内容",
                        ),
                    ),
                    provider_finish_reason="stop",
                    provider_usage={"prompt_tokens": 15, "completion_tokens": 5, "total_tokens": 20},
                ),
            ),
        }
    )
    summarizer = ScriptedSummaryAgent(
        provider_finish_reason="stop",
        provider_usage={"prompt_tokens": 18, "completion_tokens": 7, "total_tokens": 25},
    )
    search = ScriptedWebSearchClient(
        SearchScenario(
            results_by_query={
                "q_players": (
                    SearchHit(
                        title="来源 A",
                        link="https://example.com/a",
                        snippet="A snippet",
                    ),
                ),
            }
        )
    )
    fetch = ScriptedWebFetchClient(content_by_url={})
    client = await make_stage5_client(
        planner_agent=planner,
        collector_agent=collector,
        summary_agent=summarizer,
        web_search_client=search,
        web_fetch_client=fetch,
    )

    async with client:
        create_body, (stream_context, response, lines) = await _start_collection_flow(client)
        await read_until_event(lines, {"sources.merged"})
        await _close_stream(stream_context, response)

    agent_runs = list(
        db_session.scalars(
            select(AgentRunRecord)
            .where(AgentRunRecord.task_id == create_body["task_id"])
            .order_by(AgentRunRecord.id.asc())
        )
    )

    planner_run = next(run for run in agent_runs if run.agent_type == "planner")
    collector_run = next(run for run in agent_runs if run.agent_type == "collector")
    summary_run = next(run for run in agent_runs if run.agent_type == "summary")

    assert planner_run.finish_reason == "plans_generated"
    assert planner_run.provider_finish_reason == "tool_calls"
    assert planner_run.provider_usage_json == {
        "prompt_tokens": 20,
        "completion_tokens": 10,
        "total_tokens": 30,
    }
    assert collector_run.finish_reason == "tool_calls_requested"
    assert collector_run.provider_finish_reason == "tool_calls"
    assert collector_run.provider_usage_json == {
        "prompt_tokens": 21,
        "completion_tokens": 9,
        "total_tokens": 30,
    }
    assert summary_run.finish_reason == "completed"
    assert summary_run.provider_finish_reason == "stop"
    assert summary_run.provider_usage_json == {
        "prompt_tokens": 18,
        "completion_tokens": 7,
        "total_tokens": 25,
    }


@pytest.mark.asyncio
async def test_collection_persists_unified_llm_traces_for_planner_collector_and_summary(
    make_stage5_client,
    db_session: Session,
) -> None:
    planner = ScriptedPlannerAgent(
        rounds=[
            PlannerDecision(
                reasoning_deltas=("开始搜集。",),
                plans=(
                    CollectPlan(
                        tool_call_id="call_1",
                        revision_id="rev_placeholder",
                        collect_target="收集主要玩家",
                        additional_info="官方与高可信媒体优先。",
                        freshness_requirement=FreshnessRequirement.HIGH,
                    ),
                ),
                stop=False,
                provider_finish_reason="tool_calls",
                provider_usage={"prompt_tokens": 20, "completion_tokens": 10, "total_tokens": 30},
            ),
            PlannerDecision(
                reasoning_deltas=("准备进入 merge。",),
                plans=(),
                stop=True,
                provider_finish_reason="stop",
                provider_usage={"prompt_tokens": 12, "completion_tokens": 6, "total_tokens": 18},
            ),
        ]
    )
    collector = ScriptedCollectorAgent(
        rounds_by_tool_call={
            "call_1": (
                _collector_search_round(
                    tool_call_id="call_search_players",
                    query="q_players",
                    reasoning="先搜索主要玩家。",
                    provider_finish_reason="tool_calls",
                    provider_usage={"prompt_tokens": 21, "completion_tokens": 9, "total_tokens": 30},
                ),
                _collector_stop_round(
                    reasoning="当前信息已足够。",
                    items=(
                        CollectedSourceItem(
                            title="来源 A",
                            link="https://example.com/a",
                            info="A 内容",
                        ),
                    ),
                    provider_finish_reason="stop",
                    provider_usage={"prompt_tokens": 15, "completion_tokens": 5, "total_tokens": 20},
                ),
            ),
        }
    )
    summarizer = ScriptedSummaryAgent(
        provider_finish_reason="stop",
        provider_usage={"prompt_tokens": 18, "completion_tokens": 7, "total_tokens": 25},
    )
    client = await make_stage5_client(
        planner_agent=planner,
        collector_agent=collector,
        summary_agent=summarizer,
        web_search_client=ScriptedWebSearchClient(
            SearchScenario(
                results_by_query={
                    "q_players": (
                        SearchHit(
                            title="来源 A",
                            link="https://example.com/a",
                            snippet="A snippet",
                        ),
                    ),
                }
            )
        ),
        web_fetch_client=ScriptedWebFetchClient(content_by_url={}),
    )

    async with client:
        create_body, (stream_context, response, lines) = await _start_collection_flow(client)
        await read_until_event(lines, {"sources.merged"})
        await _close_stream(stream_context, response)

    traces = list(
        db_session.scalars(
            select(LLMCallTraceRecord)
            .where(LLMCallTraceRecord.task_id == create_body["task_id"])
            .where(LLMCallTraceRecord.stage.in_(("planner", "collector", "summary")))
            .order_by(LLMCallTraceRecord.id.asc())
        )
    )

    assert [trace.stage for trace in traces] == [
        "planner",
        "collector",
        "collector",
        "summary",
        "planner",
    ]
    assert traces[0].request_json["model"] == "glm-5"
    assert traces[0].provider_finish_reason == "tool_calls"
    assert traces[0].provider_usage_json == {
        "prompt_tokens": 20,
        "completion_tokens": 10,
        "total_tokens": 30,
    }
    assert traces[1].tool_calls_json == [
        {
            "tool_call_id": "call_search_players",
            "tool_name": "web_search",
            "arguments_json": {
                "search_query": "q_players",
                "search_recency_filter": "noLimit",
            },
        }
    ]
    assert traces[3].parsed_text == "- 收集主要玩家 已完成总结。"


@pytest.mark.asyncio
async def test_collection_persists_collector_trace_when_invalid_output_retries_exhaust(
    make_stage5_client,
    db_session: Session,
) -> None:
    planner = ScriptedPlannerAgent(
        rounds=[
            PlannerDecision(
                reasoning_deltas=("开始搜集。",),
                plans=(
                    CollectPlan(
                        tool_call_id="call_1",
                        revision_id="rev_placeholder",
                        collect_target="收集主要玩家",
                        additional_info="优先官方与高可信媒体。",
                        freshness_requirement=FreshnessRequirement.HIGH,
                    ),
                ),
                stop=False,
            ),
        ]
    )
    client = await make_stage5_client(
        planner_agent=planner,
        collector_agent=TraceFailingCollectorAgent(
            parsed_text="说明文字\nnot valid collector json"
        ),
        summary_agent=ScriptedSummaryAgent(),
        web_search_client=ScriptedWebSearchClient(
            scenario=SearchScenario(results_by_query={})
        ),
        web_fetch_client=ScriptedWebFetchClient(content_by_url={}),
    )

    async with client:
        create_body, (stream_context, response, lines) = await _start_collection_flow(client)
        _, failed_name, failed_payload = await read_until_event(
            lines,
            {"task.failed"},
            timeout=2.0,
        )
        await assert_stream_closed(lines)
        await _close_stream(stream_context, response)

    trace = db_session.scalar(
        select(LLMCallTraceRecord)
        .where(LLMCallTraceRecord.task_id == create_body["task_id"])
        .where(LLMCallTraceRecord.stage == "collector")
    )

    assert failed_name == "task.failed"
    assert failed_payload["payload"]["error"]["code"] == "upstream_service_error"
    assert trace is not None
    assert trace.parsed_text == "说明文字\nnot valid collector json"
    assert trace.provider_finish_reason == "stop"
    assert trace.request_id == "req_collector_invalid"


@pytest.mark.asyncio
async def test_collection_persists_summary_trace_when_invalid_output_retries_exhaust(
    make_stage5_client,
    db_session: Session,
) -> None:
    planner = ScriptedPlannerAgent(
        rounds=[
            PlannerDecision(
                reasoning_deltas=("开始搜集。",),
                plans=(
                    CollectPlan(
                        tool_call_id="call_1",
                        revision_id="rev_placeholder",
                        collect_target="收集主要玩家",
                        additional_info="优先官方与高可信媒体。",
                        freshness_requirement=FreshnessRequirement.HIGH,
                    ),
                ),
                stop=False,
            ),
        ]
    )
    collector = ScriptedCollectorAgent(
        rounds_by_tool_call={
            "call_1": (
                _collector_stop_round(
                    reasoning="已有信息足够。",
                    items=(
                        CollectedSourceItem(
                            title="来源 A",
                            link="https://example.com/a",
                            info="A 内容",
                        ),
                    ),
                ),
            ),
        }
    )
    client = await make_stage5_client(
        planner_agent=planner,
        collector_agent=collector,
        summary_agent=TraceFailingSummaryAgent(
            parsed_text="总结如下：not valid summary json"
        ),
        web_search_client=ScriptedWebSearchClient(
            scenario=SearchScenario(results_by_query={})
        ),
        web_fetch_client=ScriptedWebFetchClient(content_by_url={}),
    )

    async with client:
        create_body, (stream_context, response, lines) = await _start_collection_flow(client)
        _, failed_name, failed_payload = await read_until_event(
            lines,
            {"task.failed"},
            timeout=2.0,
        )
        await assert_stream_closed(lines)
        await _close_stream(stream_context, response)

    trace = db_session.scalar(
        select(LLMCallTraceRecord)
        .where(LLMCallTraceRecord.task_id == create_body["task_id"])
        .where(LLMCallTraceRecord.stage == "summary")
    )

    assert failed_name == "task.failed"
    assert failed_payload["payload"]["error"]["code"] == "upstream_service_error"
    assert trace is not None
    assert trace.parsed_text == "总结如下：not valid summary json"
    assert trace.provider_finish_reason == "stop"
    assert trace.request_id == "req_summary_invalid"


@pytest.mark.asyncio
async def test_collection_fetch_content_is_truncated_to_five_thousand_chars_across_summary_and_storage(
    make_stage5_client,
    db_session: Session,
) -> None:
    long_content = "A" * 6200
    planner = ScriptedPlannerAgent(
        rounds=[
            PlannerDecision(
                reasoning_deltas=("开始搜集。",),
                plans=(
                    CollectPlan(
                        tool_call_id="call_1",
                        revision_id="rev_placeholder",
                        collect_target="收集主要玩家",
                        additional_info="优先官方与高可信媒体。",
                        freshness_requirement=FreshnessRequirement.HIGH,
                    ),
                ),
                stop=False,
            ),
            PlannerDecision(
                reasoning_deltas=("准备进入 merge。",),
                plans=(),
                stop=True,
            ),
        ]
    )
    collector = ScriptedCollectorAgent(
        rounds_by_tool_call={
            "call_1": (
                _collector_fetch_round(
                    tool_call_id="call_fetch_players",
                    url="https://example.com/a",
                    reasoning="直接读取详情。",
                ),
                _collector_stop_round(
                    reasoning="信息已足够。",
                    items=(),
                ),
            ),
        }
    )
    summarizer = ScriptedSummaryAgent()
    fetch = ScriptedWebFetchClient(
        content_by_url={
            "https://example.com/a": FetchResponse(
                url="https://example.com/a",
                success=True,
                title="来源 A",
                content=long_content,
            ),
        }
    )
    search = ScriptedWebSearchClient(SearchScenario(results_by_query={}))
    client = await make_stage5_client(
        planner_agent=planner,
        collector_agent=collector,
        summary_agent=summarizer,
        web_search_client=search,
        web_fetch_client=fetch,
    )

    async with client:
        create_body, (stream_context, response, lines) = await _start_collection_flow(client)
        await read_until_event(lines, {"sources.merged"})
        await _close_stream(stream_context, response)

    summary_invocation = summarizer.invocations[0]
    assert summary_invocation.item_payloads[0]["info"] == long_content[:5000]
    assert len(summary_invocation.item_payloads[0]["info"]) == 5000

    stored_source = db_session.scalar(
        select(CollectedSourceRecord)
        .where(CollectedSourceRecord.task_id == create_body["task_id"])
        .where(CollectedSourceRecord.link == "https://example.com/a")
        .where(CollectedSourceRecord.is_merged.is_(False))
    )
    assert stored_source is not None
    assert stored_source.info == long_content[:5000]
    assert len(stored_source.info) == 5000


@pytest.mark.asyncio
async def test_collect_loop_handles_one_risk_blocked_and_two_successful_subtasks(
    make_stage5_client,
) -> None:
    planner = ScriptedPlannerAgent(
        rounds=[
            PlannerDecision(
                reasoning_deltas=("开始搜集。",),
                plans=(
                    CollectPlan(
                        tool_call_id="call_1",
                        revision_id="rev_placeholder",
                        collect_target="收集主要玩家",
                        additional_info="官方与高可信媒体优先。",
                        freshness_requirement=FreshnessRequirement.HIGH,
                    ),
                    CollectPlan(
                        tool_call_id="call_2",
                        revision_id="rev_placeholder",
                        collect_target="收集市场趋势",
                        additional_info="关注近两年变化。",
                        freshness_requirement=FreshnessRequirement.HIGH,
                    ),
                    CollectPlan(
                        tool_call_id="call_3",
                        revision_id="rev_placeholder",
                        collect_target="收集商业机会",
                        additional_info="关注中国市场。",
                        freshness_requirement=FreshnessRequirement.HIGH,
                    ),
                ),
                stop=False,
            ),
            PlannerDecision(
                reasoning_deltas=("继续进入 source merge。",),
                plans=(),
                stop=True,
            ),
        ]
    )
    collector = ScriptedCollectorAgent(
        rounds_by_tool_call={
            "call_1": (
                _collector_search_round(
                    tool_call_id="call_search_players",
                    query="q_players",
                    reasoning="搜索主要玩家。",
                ),
                _collector_fetch_round(
                    tool_call_id="call_fetch_players_a",
                    url="https://example.com/a",
                    reasoning="读取主要玩家来源。",
                ),
                _collector_stop_round(
                    reasoning="主要玩家信息已足够。",
                    items=(
                        CollectedSourceItem(
                            title="来源 A",
                            link="https://example.com/a",
                            info="A 内容",
                        ),
                    ),
                ),
            ),
            "call_2": (
                _collector_search_round(
                    tool_call_id="call_search_risk",
                    query="q_risk",
                    reasoning="搜索市场趋势。",
                ),
            ),
            "call_3": (
                _collector_search_round(
                    tool_call_id="call_search_opportunities",
                    query="q_opportunities",
                    reasoning="搜索商业机会。",
                ),
                _collector_fetch_round(
                    tool_call_id="call_fetch_opportunities_c",
                    url="https://example.com/c",
                    reasoning="读取商业机会来源。",
                ),
                _collector_stop_round(
                    reasoning="商业机会信息已足够。",
                    items=(
                        CollectedSourceItem(
                            title="来源 C",
                            link="https://example.com/c",
                            info="C 内容",
                        ),
                    ),
                ),
            ),
        }
    )
    summarizer = ScriptedSummaryAgent()
    search = ScriptedWebSearchClient(
        SearchScenario(
            results_by_query={
                "q_players": (
                    SearchHit(
                        title="来源 A",
                        link="https://example.com/a",
                        snippet="A snippet",
                    ),
                ),
                "q_opportunities": (
                    SearchHit(
                        title="来源 C",
                        link="https://example.com/c",
                        snippet="C snippet",
                    ),
                ),
            },
            risk_queries={"q_risk"},
        )
    )
    fetch = ScriptedWebFetchClient(
        content_by_url={
            "https://example.com/a": FetchResponse(
                url="https://example.com/a",
                success=True,
                title="来源 A",
                content="A 内容",
            ),
            "https://example.com/c": FetchResponse(
                url="https://example.com/c",
                success=True,
                title="来源 C",
                content="C 内容",
            ),
        }
    )
    client = await make_stage5_client(
        planner_agent=planner,
        collector_agent=collector,
        summary_agent=summarizer,
        web_search_client=search,
        web_fetch_client=fetch,
    )
    async with client:
        _, (stream_context, response, lines) = await _start_collection_flow(client)
        _, summary_name, summary_payload = await read_until_event(lines, {"summary.completed"})
        _, merged_name, _ = await read_until_event(lines, {"sources.merged"})
        await _close_stream(stream_context, response)

    assert summary_name == "summary.completed"
    assert summary_payload["payload"]["status"] in {"completed", "risk_blocked"}
    assert len(planner.invocations[1].summaries) == 3
    assert {summary.status.value for summary in planner.invocations[1].summaries} == {
        "completed",
        "risk_blocked",
    }
    assert merged_name == "sources.merged"


@pytest.mark.asyncio
async def test_risk_control_threshold_terminates_task_after_two_risk_blocked_summaries(
    make_stage5_client,
) -> None:
    planner = ScriptedPlannerAgent(
        rounds=[
            PlannerDecision(
                reasoning_deltas=("开始搜集。",),
                plans=(
                    CollectPlan(
                        tool_call_id="call_1",
                        revision_id="rev_placeholder",
                        collect_target="收集主要玩家",
                        additional_info="官方与高可信媒体优先。",
                        freshness_requirement=FreshnessRequirement.HIGH,
                    ),
                    CollectPlan(
                        tool_call_id="call_2",
                        revision_id="rev_placeholder",
                        collect_target="收集市场趋势",
                        additional_info="关注近两年变化。",
                        freshness_requirement=FreshnessRequirement.HIGH,
                    ),
                ),
                stop=False,
            ),
        ]
    )
    collector = ScriptedCollectorAgent(
        rounds_by_tool_call={
            "call_1": (
                _collector_search_round(
                    tool_call_id="call_search_risk_1",
                    query="q_risk_1",
                    reasoning="先搜第一条高风险目标。",
                ),
            ),
            "call_2": (
                _collector_search_round(
                    tool_call_id="call_search_risk_2",
                    query="q_risk_2",
                    reasoning="再搜第二条高风险目标。",
                ),
            ),
        }
    )
    summarizer = ScriptedSummaryAgent()
    search = ScriptedWebSearchClient(
        SearchScenario(
            results_by_query={},
            risk_queries={"q_risk_1", "q_risk_2"},
        )
    )
    fetch = ScriptedWebFetchClient(content_by_url={})
    client = await make_stage5_client(
        planner_agent=planner,
        collector_agent=collector,
        summary_agent=summarizer,
        web_search_client=search,
        web_fetch_client=fetch,
    )
    async with client:
        _, (stream_context, response, lines) = await _start_collection_flow(client)
        _, terminated_name, terminated_payload = await read_until_event(
            lines,
            {"task.terminated"},
        )
        await assert_stream_closed(lines)
        await _close_stream(stream_context, response)

    assert terminated_name == "task.terminated"
    assert terminated_payload["payload"] == {"reason": "risk_control_threshold_exceeded"}


@pytest.mark.asyncio
async def test_collect_agent_limit_exceeded_triggers_merge_not_fail(
    make_stage5_client,
    db_session: Session,
) -> None:
    """PRD func_7: 达到调用次数上限 → 进入搜集结果汇总，不终止任务。"""
    planner = ScriptedPlannerAgent(
        rounds=[
            PlannerDecision(
                reasoning_deltas=("第一轮搜集。",),
                plans=(
                    CollectPlan(
                        tool_call_id="call_1",
                        revision_id="rev_placeholder",
                        collect_target="目标 1",
                        additional_info="说明 1",
                        freshness_requirement=FreshnessRequirement.HIGH,
                    ),
                    CollectPlan(
                        tool_call_id="call_2",
                        revision_id="rev_placeholder",
                        collect_target="目标 2",
                        additional_info="说明 2",
                        freshness_requirement=FreshnessRequirement.HIGH,
                    ),
                    CollectPlan(
                        tool_call_id="call_3",
                        revision_id="rev_placeholder",
                        collect_target="目标 3",
                        additional_info="说明 3",
                        freshness_requirement=FreshnessRequirement.HIGH,
                    ),
                ),
                stop=False,
            ),
            # Round 2: planner asks for 2 more, but limit is 5 → 3+2=5 OK
            PlannerDecision(
                reasoning_deltas=("第二轮补充。",),
                plans=(
                    CollectPlan(
                        tool_call_id="call_4",
                        revision_id="rev_placeholder",
                        collect_target="目标 4",
                        additional_info="说明 4",
                        freshness_requirement=FreshnessRequirement.HIGH,
                    ),
                    CollectPlan(
                        tool_call_id="call_5",
                        revision_id="rev_placeholder",
                        collect_target="目标 5",
                        additional_info="说明 5",
                        freshness_requirement=FreshnessRequirement.HIGH,
                    ),
                ),
                stop=False,
            ),
            # Round 3: planner asks for 1 more, but 5+1=6 > 5 → limit reached → merge
            PlannerDecision(
                reasoning_deltas=("第三轮继续。",),
                plans=(
                    CollectPlan(
                        tool_call_id="call_6",
                        revision_id="rev_placeholder",
                        collect_target="目标 6",
                        additional_info="说明 6",
                        freshness_requirement=FreshnessRequirement.HIGH,
                    ),
                ),
                stop=False,
            ),
        ]
    )
    collector = ScriptedCollectorAgent(
        rounds_by_tool_call={
            f"call_{index}": (
                _collector_search_round(
                    tool_call_id=f"call_search_{index}",
                    query=f"q{index}",
                    reasoning=f"搜索目标 {index}。",
                ),
                _collector_fetch_round(
                    tool_call_id=f"call_fetch_{index}",
                    url=f"https://example.com/{index}",
                    reasoning=f"读取目标 {index}。",
                ),
                _collector_stop_round(
                    reasoning=f"目标 {index} 信息已足够。",
                    items=(
                        CollectedSourceItem(
                            title=str(index),
                            link=f"https://example.com/{index}",
                            info=f"内容 {index}",
                        ),
                    ),
                ),
            )
            for index in range(1, 6)
        }
    )
    summarizer = ScriptedSummaryAgent()
    search = ScriptedWebSearchClient(
        SearchScenario(
            results_by_query={
                "q1": (SearchHit(title="1", link="https://example.com/1", snippet="1"),),
                "q2": (SearchHit(title="2", link="https://example.com/2", snippet="2"),),
                "q3": (SearchHit(title="3", link="https://example.com/3", snippet="3"),),
                "q4": (SearchHit(title="4", link="https://example.com/4", snippet="4"),),
                "q5": (SearchHit(title="5", link="https://example.com/5", snippet="5"),),
            }
        )
    )
    fetch = ScriptedWebFetchClient(
        content_by_url={
            f"https://example.com/{index}": FetchResponse(
                url=f"https://example.com/{index}",
                success=True,
                title=str(index),
                content=f"内容 {index}",
            )
            for index in range(1, 6)
        }
    )
    client = await make_stage5_client(
        planner_agent=planner,
        collector_agent=collector,
        summary_agent=summarizer,
        web_search_client=search,
        web_fetch_client=fetch,
    )
    async with client:
        create_body, (stream_context, response, lines) = await _start_collection_flow(client)
        # Should merge, NOT fail
        _, merged_name, merged_payload = await read_until_event(lines, {"sources.merged"})
        await _close_stream(stream_context, response)

    assert merged_name == "sources.merged"
    # 5 subtasks, each uses search -> fetch -> stop
    assert len(collector.invocations) == 15

    db_session.expire_all()
    revision = db_session.get(
        TaskRevisionRecord,
        create_body["snapshot"]["active_revision_id"],
    )
    assert revision is not None
    assert revision.collect_agent_calls_used == 5


@pytest.mark.asyncio
async def test_sub_agent_tool_call_limit_caps_at_ten_and_marks_partial_result(
    make_stage5_client,
    db_session: Session,
) -> None:
    planner = ScriptedPlannerAgent(
        rounds=[
            PlannerDecision(
                reasoning_deltas=("开始搜集。",),
                plans=(
                    CollectPlan(
                        tool_call_id="call_1",
                        revision_id="rev_placeholder",
                        collect_target="高密度抓取测试",
                        additional_info="尽量多抓取",
                        freshness_requirement=FreshnessRequirement.HIGH,
                    ),
                ),
                stop=False,
            ),
            PlannerDecision(
                reasoning_deltas=("进入 merge。",),
                plans=(),
                stop=True,
            ),
        ]
    )
    collector = ScriptedCollectorAgent(
        rounds_by_tool_call={
            "call_1": (
                _collector_search_round(
                    tool_call_id="call_search_dense",
                    query="q_dense",
                    reasoning="先做密集搜索。",
                ),
                *tuple(
                    _collector_fetch_round(
                        tool_call_id=f"call_fetch_dense_{index}",
                        url=f"https://example.com/{index}",
                        reasoning=f"读取来源 {index}。",
                    )
                    for index in range(1, 20)
                ),
                _collector_stop_round(
                    reasoning="达到上限后结束。",
                    items=tuple(
                        CollectedSourceItem(
                            title=f"来源 {index}",
                            link=f"https://example.com/{index}",
                            info=f"内容 {index}",
                        )
                        for index in range(1, 20)
                    ),
                ),
            ),
        }
    )
    summarizer = ScriptedSummaryAgent()
    search = ScriptedWebSearchClient(
        SearchScenario(
            results_by_query={
                "q_dense": tuple(
                    SearchHit(
                        title=f"来源 {index}",
                        link=f"https://example.com/{index}",
                        snippet=f"snippet {index}",
                    )
                    for index in range(1, 21)
                ),
            },
            fail_once_queries={"q_dense"},
        )
    )
    fetch = ScriptedWebFetchClient(
        content_by_url={
            f"https://example.com/{index}": FetchResponse(
                url=f"https://example.com/{index}",
                success=True,
                title=f"来源 {index}",
                content=f"内容 {index}",
            )
            for index in range(1, 21)
        }
    )
    client = await make_stage5_client(
        planner_agent=planner,
        collector_agent=collector,
        summary_agent=summarizer,
        web_search_client=search,
        web_fetch_client=fetch,
    )
    async with client:
        create_body, (stream_context, response, lines) = await _start_collection_flow(client)
        _, collector_completed_name, collector_completed_payload = await read_until_event(
            lines,
            {"collector.completed"},
        )
        _, merged_name, _ = await read_until_event(lines, {"sources.merged"})
        await _close_stream(stream_context, response)

    db_session.expire_all()
    tool_calls = list(
        db_session.scalars(
            select(TaskToolCallRecord)
            .where(TaskToolCallRecord.task_id == create_body["task_id"])
            .order_by(TaskToolCallRecord.id.asc())
        )
    )

    assert collector_completed_name == "collector.completed"
    assert collector_completed_payload["payload"]["status"] == "partial"
    assert len(tool_calls) == 10
    assert merged_name == "sources.merged"


@pytest.mark.asyncio
async def test_planner_empty_plans_with_existing_data_triggers_merge(
    make_stage5_client,
    db_session: Session,
) -> None:
    """Non-first round: planner returns empty plans → merge, not fail."""
    planner = ScriptedPlannerAgent(
        rounds=[
            # Round 1: normal plans
            PlannerDecision(
                reasoning_deltas=("第一轮搜集。",),
                plans=(
                    CollectPlan(
                        tool_call_id="call_1",
                        revision_id="rev_placeholder",
                        collect_target="目标 1",
                        additional_info="说明 1",
                        freshness_requirement=FreshnessRequirement.HIGH,
                    ),
                ),
                stop=False,
            ),
            # Round 2: empty plans, but data already collected → merge
            PlannerDecision(
                reasoning_deltas=("没有更多需要搜集的了。",),
                plans=(),
                stop=False,
            ),
        ]
    )
    collector = ScriptedCollectorAgent(
        rounds_by_tool_call={
            "call_1": (
                _collector_search_round(
                    tool_call_id="call_search_1",
                    query="q1",
                    reasoning="搜索目标 1。",
                ),
                _collector_fetch_round(
                    tool_call_id="call_fetch_1",
                    url="https://example.com/1",
                    reasoning="读取目标 1。",
                ),
                _collector_stop_round(
                    reasoning="目标 1 信息已足够。",
                    items=(
                        CollectedSourceItem(
                            title="1",
                            link="https://example.com/1",
                            info="内容 1",
                        ),
                    ),
                ),
            ),
        }
    )
    summarizer = ScriptedSummaryAgent()
    search = ScriptedWebSearchClient(
        SearchScenario(
            results_by_query={
                "q1": (SearchHit(title="1", link="https://example.com/1", snippet="1"),),
            }
        )
    )
    fetch = ScriptedWebFetchClient(
        content_by_url={
            "https://example.com/1": FetchResponse(
                url="https://example.com/1",
                success=True,
                title="1",
                content="内容 1",
            ),
        }
    )
    client = await make_stage5_client(
        planner_agent=planner,
        collector_agent=collector,
        summary_agent=summarizer,
        web_search_client=search,
        web_fetch_client=fetch,
    )
    async with client:
        create_body, (stream_context, response, lines) = await _start_collection_flow(client)
        _, merged_name, _ = await read_until_event(lines, {"sources.merged"})
        await _close_stream(stream_context, response)

    assert merged_name == "sources.merged"
    assert len(collector.invocations) == 3

    db_session.expire_all()
    task = db_session.get(
        ResearchTaskRecord,
        create_body["task_id"],
    )
    assert task is not None
    assert task.status != "failed"


@pytest.mark.asyncio
async def test_planner_second_round_tool_calls_without_additional_info_are_executed(
    make_stage5_client,
) -> None:
    planner = ZhipuPlannerAgent(
        client=QueuedZhipuClient(
            [
                SimpleNamespace(
                    id="req_r1",
                    choices=[
                        SimpleNamespace(
                            finish_reason="tool_calls",
                            message=SimpleNamespace(
                                content="",
                                reasoning_content="先补玩家信息。",
                                tool_calls=[
                                    SimpleNamespace(
                                        id="call_tc_r1",
                                        function=SimpleNamespace(
                                            name="collect_agent",
                                            arguments=json.dumps(
                                                {
                                                    "collect_target": "目标 1",
                                                    "additional_info": "说明 1",
                                                    "freshness_requirement": "high",
                                                },
                                                ensure_ascii=False,
                                            ),
                                        ),
                                    )
                                ],
                            ),
                        )
                    ],
                ),
                SimpleNamespace(
                    id="req_r2",
                    choices=[
                        SimpleNamespace(
                            finish_reason="tool_calls",
                            message=SimpleNamespace(
                                content="",
                                reasoning_content="继续并行补市场与机会信息。",
                                tool_calls=[
                                    SimpleNamespace(
                                        id="call_tc_r2_a",
                                        function=SimpleNamespace(
                                            name="collect_agent",
                                            arguments=json.dumps(
                                                {
                                                    "collect_target": "目标 2",
                                                },
                                                ensure_ascii=False,
                                            ),
                                        ),
                                    ),
                                    SimpleNamespace(
                                        id="call_tc_r2_b",
                                        function=SimpleNamespace(
                                            name="collect_agent",
                                            arguments=json.dumps(
                                                {
                                                    "collect_target": "目标 3",
                                                    "freshness_requirement": "low",
                                                },
                                                ensure_ascii=False,
                                            ),
                                        ),
                                    ),
                                ],
                            ),
                        )
                    ],
                ),
                SimpleNamespace(
                    id="req_r3",
                    choices=[
                        SimpleNamespace(
                            finish_reason="stop",
                            message=SimpleNamespace(
                                content=json.dumps(
                                    {
                                        "reasoning_deltas": ["进入 merge。"],
                                        "stop": True,
                                        "plans": [],
                                    },
                                    ensure_ascii=False,
                                ),
                            ),
                        )
                    ],
                ),
            ]
        ),
        model="glm-test",
    )
    collector = ScriptedCollectorAgent(
        rounds_by_tool_call={
            "call_tc_r1": (
                _collector_search_round(
                    tool_call_id="call_search_1",
                    query="q1",
                    reasoning="搜索目标 1。",
                ),
                _collector_fetch_round(
                    tool_call_id="call_fetch_1",
                    url="https://example.com/1",
                    reasoning="读取目标 1。",
                ),
                _collector_stop_round(
                    reasoning="目标 1 信息已足够。",
                    items=(
                        CollectedSourceItem(
                            title="来源 1",
                            link="https://example.com/1",
                            info="内容 1",
                        ),
                    ),
                ),
            ),
            "call_tc_r2_a": (
                _collector_search_round(
                    tool_call_id="call_search_2",
                    query="q2",
                    reasoning="搜索目标 2。",
                ),
                _collector_fetch_round(
                    tool_call_id="call_fetch_2",
                    url="https://example.com/2",
                    reasoning="读取目标 2。",
                ),
                _collector_stop_round(
                    reasoning="目标 2 信息已足够。",
                    items=(
                        CollectedSourceItem(
                            title="来源 2",
                            link="https://example.com/2",
                            info="内容 2",
                        ),
                    ),
                ),
            ),
            "call_tc_r2_b": (
                _collector_search_round(
                    tool_call_id="call_search_3",
                    query="q3",
                    reasoning="搜索目标 3。",
                ),
                _collector_fetch_round(
                    tool_call_id="call_fetch_3",
                    url="https://example.com/3",
                    reasoning="读取目标 3。",
                ),
                _collector_stop_round(
                    reasoning="目标 3 信息已足够。",
                    items=(
                        CollectedSourceItem(
                            title="来源 3",
                            link="https://example.com/3",
                            info="内容 3",
                        ),
                    ),
                ),
            ),
        }
    )
    summarizer = ScriptedSummaryAgent()
    search = ScriptedWebSearchClient(
        SearchScenario(
            results_by_query={
                "q1": (SearchHit(title="来源 1", link="https://example.com/1", snippet="1"),),
                "q2": (SearchHit(title="来源 2", link="https://example.com/2", snippet="2"),),
                "q3": (SearchHit(title="来源 3", link="https://example.com/3", snippet="3"),),
            }
        )
    )
    fetch = ScriptedWebFetchClient(
        content_by_url={
            "https://example.com/1": FetchResponse(
                url="https://example.com/1",
                success=True,
                title="来源 1",
                content="内容 1",
            ),
            "https://example.com/2": FetchResponse(
                url="https://example.com/2",
                success=True,
                title="来源 2",
                content="内容 2",
            ),
            "https://example.com/3": FetchResponse(
                url="https://example.com/3",
                success=True,
                title="来源 3",
                content="内容 3",
            ),
        }
    )
    client = await make_stage5_client(
        planner_agent=planner,
        collector_agent=collector,
        summary_agent=summarizer,
        web_search_client=search,
        web_fetch_client=fetch,
    )

    async with client:
        _, (stream_context, response, lines) = await _start_collection_flow(client)
        events: list[tuple[str | None, str | None, dict[str, object]]] = []
        while True:
            event = await read_sse_event(lines, timeout=2.0)
            events.append(event)
            if event[1] == "sources.merged":
                break
        await _close_stream(stream_context, response)

    planner_events = [
        payload
        for _, event_name, payload in events
        if event_name == "planner.tool_call.requested"
    ]

    assert len(planner_events) == 3
    assert planner_events[1]["payload"]["tool_call_id"] == "call_tc_r2_a"
    assert planner_events[1]["payload"]["collect_target"] == "目标 2"
    assert planner_events[1]["payload"]["additional_info"] == ""
    assert planner_events[2]["payload"]["tool_call_id"] == "call_tc_r2_b"
    assert planner_events[2]["payload"]["collect_target"] == "目标 3"
    assert planner_events[2]["payload"]["additional_info"] == ""
    assert len(collector.invocations_by_tool_call["call_tc_r2_a"]) == 3
    assert len(collector.invocations_by_tool_call["call_tc_r2_b"]) == 3


@pytest.mark.asyncio
async def test_planner_empty_plans_first_round_still_fails(
    make_stage5_client,
) -> None:
    """First round: planner returns empty plans → fail (no data to merge)."""
    planner = ScriptedPlannerAgent(
        rounds=[
            PlannerDecision(
                reasoning_deltas=("不知道该搜什么。",),
                plans=(),
                stop=False,
            ),
        ]
    )
    collector = ScriptedCollectorAgent(rounds_by_tool_call={})
    summarizer = ScriptedSummaryAgent()
    search = ScriptedWebSearchClient(SearchScenario(results_by_query={}))
    fetch = ScriptedWebFetchClient(content_by_url={})
    client = await make_stage5_client(
        planner_agent=planner,
        collector_agent=collector,
        summary_agent=summarizer,
        web_search_client=search,
        web_fetch_client=fetch,
    )
    async with client:
        _, (stream_context, response, lines) = await _start_collection_flow(client)
        _, failed_name, failed_payload = await read_until_event(lines, {"task.failed"})
        await assert_stream_closed(lines)
        await _close_stream(stream_context, response)

    assert failed_name == "task.failed"
    assert failed_payload["payload"]["error"]["code"] == "planner_invalid_output"
