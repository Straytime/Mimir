import asyncio
from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.dto.invocation import LLMInvocation
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
from app.application.ports.llm import FeedbackAnalyzer
from app.application.ports.research import (
    CollectorAgent,
    PlannerAgent,
    SummaryAgent,
    WebFetchClient,
    WebSearchClient,
)
from app.application.services.llm import TextGeneration
from app.core.config import Settings
from app.domain.enums import CollectSummaryStatus, FreshnessRequirement
from app.domain.schemas import CollectPlan
from app.infrastructure.db.models import AgentRunRecord, CollectedSourceRecord, LLMCallTraceRecord, ResearchTaskRecord, TaskRevisionRecord
from app.infrastructure.delivery.local import LocalArtifactStore
from app.main import create_app
from tests.contract.rest.test_task_events import read_sse_event, read_until_event
from tests.fixtures.app import StreamingASGITransport
from tests.fixtures.runtime import FakeClock
from tests.fixtures.tasks import seed_delivered_task


class ScriptedFeedbackAnalyzer(FeedbackAnalyzer):
    def __init__(self, generation: TextGeneration) -> None:
        self.generation = generation
        self.prompts: list[str] = []

    async def analyze(self, invocation: LLMInvocation) -> TextGeneration:
        self.prompts.append(invocation.prompt_bundle.user_prompt)
        return self.generation


class BlockingPlannerAgent(PlannerAgent):
    def __init__(self) -> None:
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    async def plan(self, invocation: PlannerInvocation) -> PlannerDecision:
        self.started.set()
        await self.release.wait()
        return PlannerDecision(
            reasoning_deltas=("已有资料足够，准备进入 merge。",),
            plans=(),
            stop=True,
        )


class SixRoundPlannerAgent(PlannerAgent):
    async def plan(self, invocation: PlannerInvocation) -> PlannerDecision:
        return PlannerDecision(
            reasoning_deltas=(f"第 {invocation.call_index} 轮继续补资料。",),
            plans=(
                CollectPlan(
                    tool_call_id=f"call_feedback_{invocation.call_index}",
                    revision_id="rev_placeholder",
                    collect_target=f"补充第 {invocation.call_index} 轮 B 端资料",
                    additional_info="优先官方与高可信媒体。",
                    freshness_requirement=FreshnessRequirement.HIGH,
                ),
            ),
            stop=False,
        )


class MinimalCollectorAgent(CollectorAgent):
    async def plan(self, invocation: CollectorInvocation) -> CollectorDecision:
        if invocation.call_index == 1:
            return CollectorDecision(
                reasoning_text="执行最小搜索。",
                content_text="",
                tool_calls=(
                    CollectorToolCall(
                        tool_call_id=f"call_search_{invocation.plan.tool_call_id}",
                        tool_name="web_search",
                        arguments_json={
                            "search_query": f"{invocation.plan.collect_target} 官方",
                            "search_recency_filter": "noLimit",
                        },
                    ),
                ),
                stop=False,
            )
        if invocation.call_index == 2:
            return CollectorDecision(
                reasoning_text="读取最相关来源。",
                content_text="",
                tool_calls=(
                    CollectorToolCall(
                        tool_call_id=f"call_fetch_{invocation.plan.tool_call_id}",
                        tool_name="web_fetch",
                        arguments_json={"url": "https://example.com/b2b"},
                    ),
                ),
                stop=False,
            )
        return CollectorDecision(
            reasoning_text="当前信息已足够。",
            content_text='[{"info":"某产品发布面向政企客户的新能力。","title":"企业版能力发布","link":"https://example.com/b2b"}]',
            tool_calls=(),
            stop=True,
            items=(
                CollectedSourceItem(
                    title="企业版能力发布",
                    link="https://example.com/b2b",
                    info="某产品发布面向政企客户的新能力。",
                ),
            ),
        )


class MinimalSummaryAgent(SummaryAgent):
    async def summarize(self, invocation: SummaryInvocation) -> SummaryDecision:
        return SummaryDecision(
            status=CollectSummaryStatus.COMPLETED,
            key_findings_markdown="- 找到新的 B 端落地公开信息。",
        )


class MinimalWebSearchClient(WebSearchClient):
    async def search(self, query: str, recency_filter: str) -> SearchResponse:
        return SearchResponse(
            query=query,
            recency_filter=recency_filter,
            results=(
                SearchHit(
                    title="企业版能力发布",
                    link="https://example.com/b2b",
                    snippet="某产品发布面向政企客户的新能力。",
                ),
            ),
        )


class MinimalWebFetchClient(WebFetchClient):
    async def fetch(self, url: str) -> FetchResponse:
        return FetchResponse(
            url=url,
            success=True,
            title="企业版能力发布",
            content="某产品发布面向政企客户的新能力。",
        )


@pytest_asyncio.fixture
async def make_stage7_client(
    settings: Settings,
    fake_clock: FakeClock,
    temp_artifact_dir: Path,
):
    apps_to_shutdown: list[FastAPI] = []

    async def _factory(
        *,
        feedback_analyzer: FeedbackAnalyzer,
        planner_agent: PlannerAgent,
        cleanup_scan_interval_seconds: float = 0.02,
    ) -> tuple[FastAPI, AsyncClient]:
        test_settings = replace(
            settings,
            llm_retry_wait_seconds=0,
            lifecycle_poll_interval_seconds=0.02,
            cleanup_scan_interval_seconds=cleanup_scan_interval_seconds,
        )
        app = create_app(
            settings=test_settings,
            clock=fake_clock.now,
            feedback_analyzer=feedback_analyzer,
            planner_agent=planner_agent,
            collector_agent=MinimalCollectorAgent(),
            summary_agent=MinimalSummaryAgent(),
            web_search_client=MinimalWebSearchClient(),
            web_fetch_client=MinimalWebFetchClient(),
            artifact_store=LocalArtifactStore(root_dir=temp_artifact_dir),
        )
        await app.router.startup()
        apps_to_shutdown.append(app)
        transport = StreamingASGITransport(app=app, client=("203.0.113.10", 51000))
        client = AsyncClient(transport=transport, base_url="http://testserver")
        return app, client

    yield _factory

    for app in reversed(apps_to_shutdown):
        await app.state.task_lifecycle.shutdown()
        await app.router.shutdown()


async def _wait_for_condition(predicate, *, timeout: float = 1.0) -> None:
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        if predicate():
            return
        await asyncio.sleep(0.02)
    raise AssertionError("Timed out waiting for condition.")


@pytest.mark.asyncio
async def test_feedback_rollover_reuses_sources_resets_counter_and_advances_to_planning_collection(
    make_stage7_client,
    db_session: Session,
    fake_clock: FakeClock,
) -> None:
    planner = BlockingPlannerAgent()
    app, client = await make_stage7_client(
        feedback_analyzer=ScriptedFeedbackAnalyzer(
            TextGeneration(
                deltas=('{ "research_goal": "补充 B 端落地分析",',),
                full_text="""
                {
                  "research_goal": "补充 B 端落地分析",
                  "domain": "互联网 / AI 产品",
                  "requirement_details": "补充比较各家产品在 B 端场景的落地情况，删掉不确定推测。",
                  "output_format": "business_report",
                  "freshness_requirement": "high",
                  "language": "zh-CN"
                }
                """,
                provider_finish_reason="stop",
                provider_usage={"prompt_tokens": 14, "completion_tokens": 9, "total_tokens": 23},
            )
        ),
        planner_agent=planner,
    )

    async with client:
        seeded = await seed_delivered_task(
            session=db_session,
            task_service=app.state.task_service,
            artifact_store=app.state.artifact_store,
            now=fake_clock.now(),
            suffix="feedback_rollover",
        )
        async with client.stream(
            "GET",
            f"/api/v1/tasks/{seeded.task_id}/events",
            headers={"Authorization": f"Bearer {seeded.task_token}"},
        ) as response:
            lines = response.aiter_lines()
            await read_sse_event(lines)
            feedback_response = await client.post(
                f"/api/v1/tasks/{seeded.task_id}/feedback",
                headers={"Authorization": f"Bearer {seeded.task_token}"},
                json={
                    "feedback_text": "补充比较各家产品在 B 端场景的落地情况，并删掉不够确定的推测。"
                },
            )

            processing_changed = await read_until_event(lines, {"phase.changed"}, timeout=2.0)
            analysis_delta = await read_until_event(lines, {"analysis.delta"}, timeout=2.0)
            analysis_completed = await read_until_event(lines, {"analysis.completed"}, timeout=2.0)
            planning_changed = await read_until_event(lines, {"phase.changed"}, timeout=2.0)
            await _wait_for_condition(planner.started.is_set, timeout=1.0)

            response_body = feedback_response.json()
            new_revision_id = response_body["revision_id"]

            db_session.expire_all()
            task = db_session.get(ResearchTaskRecord, seeded.task_id)
            new_revision = db_session.get(TaskRevisionRecord, new_revision_id)
            old_sources = list(
                db_session.scalars(
                    select(CollectedSourceRecord)
                    .where(CollectedSourceRecord.revision_id == seeded.revision_id)
                    .order_by(CollectedSourceRecord.id.asc())
                )
            )
            new_sources = list(
                db_session.scalars(
                    select(CollectedSourceRecord)
                    .where(CollectedSourceRecord.revision_id == new_revision_id)
                    .order_by(CollectedSourceRecord.id.asc())
                )
            )
            feedback_run = db_session.scalar(
                select(AgentRunRecord)
                .where(AgentRunRecord.task_id == seeded.task_id)
                .where(AgentRunRecord.revision_id == new_revision_id)
                .where(AgentRunRecord.agent_type == "feedback_analyzer")
            )

            assert feedback_response.status_code == 202
            assert response_body["accepted"] is True
            assert response_body["revision_number"] == 2
            assert processing_changed[2]["payload"]["from_phase"] == "delivered"
            assert processing_changed[2]["payload"]["to_phase"] == "processing_feedback"
            assert analysis_delta[1] == "analysis.delta"
            assert analysis_completed[1] == "analysis.completed"
            assert planning_changed[2]["payload"]["from_phase"] == "processing_feedback"
            assert planning_changed[2]["payload"]["to_phase"] == "planning_collection"
            assert int(processing_changed[2]["seq"]) < int(analysis_completed[2]["seq"])
            assert int(analysis_completed[2]["seq"]) < int(planning_changed[2]["seq"])
            assert task is not None
            assert task.status == "running"
            assert task.phase == "planning_collection"
            assert task.active_revision_id == new_revision_id
            assert task.active_revision_number == 2
            assert new_revision is not None
            assert new_revision.collect_agent_calls_used == 0
            assert new_revision.requirement_detail_json is not None
            assert len(new_sources) == len(old_sources)
            assert {(source.title, source.link, source.is_merged) for source in new_sources} == {
                (source.title, source.link, source.is_merged) for source in old_sources
            }
            assert feedback_run is not None
            assert feedback_run.finish_reason == "analysis_completed"
            assert feedback_run.provider_finish_reason == "stop"
            assert feedback_run.provider_usage_json == {
                "prompt_tokens": 14,
                "completion_tokens": 9,
                "total_tokens": 23,
            }
            feedback_trace = db_session.scalar(
                select(LLMCallTraceRecord)
                .where(LLMCallTraceRecord.task_id == seeded.task_id)
                .where(LLMCallTraceRecord.revision_id == new_revision_id)
                .where(LLMCallTraceRecord.stage == "feedback_analysis")
            )
            assert feedback_trace is not None
            assert feedback_trace.provider_finish_reason == "stop"
            assert feedback_trace.provider_usage_json == {
                "prompt_tokens": 14,
                "completion_tokens": 9,
                "total_tokens": 23,
            }
            assert feedback_trace.parsed_text.strip().startswith("{")

        planner.release.set()


@pytest.mark.asyncio
async def test_feedback_revision_still_respects_collect_agent_limit_after_counter_reset(
    make_stage7_client,
    db_session: Session,
    fake_clock: FakeClock,
) -> None:
    app, client = await make_stage7_client(
        feedback_analyzer=ScriptedFeedbackAnalyzer(
            TextGeneration(
                deltas=('{ "research_goal": "补充 B 端落地分析",',),
                full_text="""
                {
                  "research_goal": "补充 B 端落地分析",
                  "domain": "互联网 / AI 产品",
                  "requirement_details": "补充比较各家产品在 B 端场景的落地情况。",
                  "output_format": "business_report",
                  "freshness_requirement": "high",
                  "language": "zh-CN"
                }
                """,
            )
        ),
        planner_agent=SixRoundPlannerAgent(),
        cleanup_scan_interval_seconds=60.0,
    )

    async with client:
        seeded = await seed_delivered_task(
            session=db_session,
            task_service=app.state.task_service,
            artifact_store=app.state.artifact_store,
            now=fake_clock.now(),
            suffix="feedback_limit",
            include_artifacts=False,
        )
        feedback_response = await client.post(
            f"/api/v1/tasks/{seeded.task_id}/feedback",
            headers={"Authorization": f"Bearer {seeded.task_token}"},
            json={"feedback_text": "请继续补充 B 端落地公开信息。"},
        )

        response_body = feedback_response.json()
        new_revision_id = response_body["revision_id"]

        def _task_delivered() -> bool:
            db_session.expire_all()
            task = db_session.get(ResearchTaskRecord, seeded.task_id)
            return task is not None and task.phase == "delivered"

        await _wait_for_condition(_task_delivered, timeout=2.0)

        db_session.expire_all()
        task = db_session.get(ResearchTaskRecord, seeded.task_id)
        new_revision = db_session.get(TaskRevisionRecord, new_revision_id)

        assert feedback_response.status_code == 202
        assert task is not None
        # PRD: 配额耗尽 → merge → delivery，不 fail
        assert task.status != "failed"
        assert new_revision is not None
        assert new_revision.collect_agent_calls_used == 5
