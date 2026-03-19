import asyncio
from collections.abc import Sequence
from dataclasses import dataclass, field, replace

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
from app.application.services.invocation import RetryableOperationError, RiskControlTriggered
from app.core.config import Settings
from app.domain.enums import CollectSummaryStatus, FreshnessRequirement
from app.domain.schemas import CollectPlan
from app.infrastructure.db.models import (
    AgentRunRecord,
    CollectedSourceRecord,
    ResearchTaskRecord,
    TaskRevisionRecord,
    TaskToolCallRecord,
)
from app.main import create_app
from tests.contract.rest.test_task_events import assert_stream_closed, read_until_event
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


class ScriptedCollectorAgent(CollectorAgent):
    def __init__(self, query_by_tool_call: dict[str, Sequence[str]]) -> None:
        self.query_by_tool_call = query_by_tool_call
        self.invocations: list[CollectorInvocation] = []

    async def plan(self, invocation: CollectorInvocation) -> CollectorDecision:
        self.invocations.append(invocation)
        return CollectorDecision(
            reasoning_deltas=(f"开始处理 {invocation.plan.collect_target}",),
            search_queries=tuple(self.query_by_tool_call[invocation.plan.tool_call_id]),
            search_recency_filter="noLimit",
        )


class ScriptedSummaryAgent(SummaryAgent):
    def __init__(self) -> None:
        self.invocations: list[SummaryInvocation] = []

    async def summarize(self, invocation: SummaryInvocation) -> SummaryDecision:
        self.invocations.append(invocation)
        return SummaryDecision(
            status=CollectSummaryStatus.COMPLETED,
            key_findings_markdown=f"- {invocation.plan.collect_target} 已完成总结。",
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
            reasoning_deltas=(),
            content_deltas=(),
            tool_calls=(),
            final_markdown="noop",
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
        query_by_tool_call={
            "call_1": ("q_players",),
            "call_2": ("q_trends",),
            "call_3": ("q_opportunities",),
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
    assert revision is not None
    assert revision.collect_agent_calls_used == 3
    assert [source.refer for source in merged_sources] == ["ref_1", "ref_2", "ref_3"]
    assert merged_sources[1].link == "https://example.com/shared"
    assert merged_sources[1].info == "Shared 内容"
    assert [run.agent_type for run in agent_runs].count("planner") == 2
    assert [run.agent_type for run in agent_runs].count("collector") == 3
    assert [run.agent_type for run in agent_runs].count("summary") == 3


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
        query_by_tool_call={
            "call_1": ("q_players",),
            "call_2": ("q_risk",),
            "call_3": ("q_opportunities",),
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
        query_by_tool_call={
            "call_1": ("q_risk_1",),
            "call_2": ("q_risk_2",),
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
        query_by_tool_call={
            "call_1": ("q1",),
            "call_2": ("q2",),
            "call_3": ("q3",),
            "call_4": ("q4",),
            "call_5": ("q5",),
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
    # 5 collector invocations from rounds 1+2; round 3 skipped due to limit
    assert len(collector.invocations) == 5

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
    collector = ScriptedCollectorAgent(query_by_tool_call={"call_1": ("q_dense",)})
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
        query_by_tool_call={"call_1": ("q1",)}
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
    assert len(collector.invocations) == 1

    db_session.expire_all()
    task = db_session.get(
        ResearchTaskRecord,
        create_body["task_id"],
    )
    assert task is not None
    assert task.status != "failed"


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
    collector = ScriptedCollectorAgent(query_by_tool_call={})
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
