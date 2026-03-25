import asyncio
import json
from collections.abc import Sequence
from dataclasses import replace

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.dto.invocation import LLMInvocation
from app.application.dto.research import SearchHit, SearchResponse
from app.application.ports.llm import ClarificationGenerator, RequirementAnalyzer
from app.application.ports.research import WebSearchClient
from app.application.services.llm import TextGeneration
from app.core.config import Settings
from app.infrastructure.db.models import LLMCallTraceRecord
from app.main import create_app
from tests.contract.rest.test_task_events import assert_stream_closed, read_until_event
from tests.contract.rest.test_tasks import build_create_task_payload
from tests.fixtures.app import StreamingASGITransport
from tests.fixtures.runtime import FakeClock


class ScriptedClarificationGenerator(ClarificationGenerator):
    def __init__(
        self,
        *,
        natural_generation: TextGeneration | None = None,
        options_generation: TextGeneration | None = None,
        natural_generations: Sequence[TextGeneration] | None = None,
        options_generations: Sequence[TextGeneration] | None = None,
    ) -> None:
        self.natural_generations = list(
            natural_generations
            or (
                natural_generation
                or TextGeneration(
                    deltas=("为了更好开展研究，请补充你最关心的研究重点。",),
                    full_text="为了更好开展研究，请补充你最关心的研究重点。",
                ),
            )
        )
        self.options_generations = list(
            options_generations
            or (
                options_generation
                or TextGeneration(
                    deltas=("1. 你更想聚焦哪个方向？\nA. 行业现状\nB. 竞争格局",),
                    full_text="1. 你更想聚焦哪个方向？\nA. 行业现状\nB. 竞争格局",
                ),
            )
        )
        self.natural_invocations: list[LLMInvocation] = []
        self.options_invocations: list[LLMInvocation] = []

    async def generate_natural(self, invocation: LLMInvocation) -> TextGeneration:
        self.natural_invocations.append(invocation)
        if not self.natural_generations:
            raise AssertionError("natural clarification called more times than expected")
        return self.natural_generations.pop(0)

    async def generate_options(self, invocation: LLMInvocation) -> TextGeneration:
        self.options_invocations.append(invocation)
        if not self.options_generations:
            raise AssertionError("options clarification called more times than expected")
        return self.options_generations.pop(0)


class ScriptedWebSearchClient(WebSearchClient):
    def __init__(self, *, results_by_query: dict[str, Sequence[SearchHit]]) -> None:
        self.results_by_query = results_by_query
        self.calls: list[dict[str, str]] = []

    async def search(self, query: str, recency_filter: str) -> SearchResponse:
        self.calls.append({"query": query, "recency_filter": recency_filter})
        return SearchResponse(
            query=query,
            recency_filter=recency_filter,
            results=tuple(self.results_by_query.get(query, ())),
        )


class ScriptedRequirementAnalyzer(RequirementAnalyzer):
    def __init__(self, *, generation: TextGeneration | None = None) -> None:
        self.generation = generation or TextGeneration(
            deltas=(
                '{\n  "research_goal": "分析中国 AI 搜索产品竞争格局",',
            ),
            full_text="""
            {
              "research_goal": "分析中国 AI 搜索产品竞争格局",
              "domain": "互联网 / AI 产品",
              "requirement_details": "聚焦中国市场，偏商业分析，覆盖近两年变化。",
              "output_format": "business_report",
              "freshness_requirement": "high",
              "language": "zh-CN"
            }
            """,
        )

    async def analyze(self, invocation: LLMInvocation) -> TextGeneration:
        return self.generation


@pytest_asyncio.fixture
async def stage4_client(
    settings: Settings,
    fake_clock: FakeClock,
) -> AsyncClient:
    app = create_app(
        settings=settings,
        clock=fake_clock.now,
        clarification_generator=ScriptedClarificationGenerator(),
        requirement_analyzer=ScriptedRequirementAnalyzer(),
    )
    await app.router.startup()

    transport = StreamingASGITransport(app=app, client=("203.0.113.10", 51000))
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        yield client

    await app.state.task_lifecycle.shutdown()
    await app.router.shutdown()


@pytest.mark.asyncio
async def test_natural_clarification_flow_emits_ready_then_analysis_events(
    stage4_client: AsyncClient,
) -> None:
    create_response = await stage4_client.post(
        "/api/v1/tasks",
        json=build_create_task_payload(clarification_mode="natural"),
    )
    create_body = create_response.json()

    async with stage4_client.stream(
        "GET",
        f"/api/v1/tasks/{create_body['task_id']}/events",
        headers={"Authorization": f"Bearer {create_body['task_token']}"},
    ) as response:
        lines = response.aiter_lines()
        _, created_name, _ = await read_until_event(lines, {"task.created"})
        _, delta_name, delta_payload = await read_until_event(lines, {"clarification.delta"})
        _, ready_name, ready_payload = await read_until_event(lines, {"clarification.natural.ready"})

        submit_response = await stage4_client.post(
            f"/api/v1/tasks/{create_body['task_id']}/clarification",
            headers={"Authorization": f"Bearer {create_body['task_token']}"},
            json={
                "mode": "natural",
                "answer_text": "重点看中国市场，偏商业分析，覆盖近两年变化。",
            },
        )
        _, phase_name, phase_payload = await read_until_event(lines, {"phase.changed"})
        _, analysis_delta_name, analysis_delta_payload = await read_until_event(lines, {"analysis.delta"})
        _, completed_name, completed_payload = await read_until_event(lines, {"analysis.completed"})

    assert created_name == "task.created"
    assert delta_name == "clarification.delta"
    assert delta_payload["payload"]["delta"]
    assert ready_name == "clarification.natural.ready"
    assert ready_payload["payload"] == {
        "status": "awaiting_user_input",
        "available_actions": ["submit_clarification"],
    }
    assert submit_response.status_code == 202
    assert phase_name == "phase.changed"
    assert phase_payload["payload"] == {
        "from_phase": "clarifying",
        "to_phase": "analyzing_requirement",
        "status": "running",
    }
    assert analysis_delta_name == "analysis.delta"
    assert analysis_delta_payload["payload"]["delta"].startswith("{")
    assert completed_name == "analysis.completed"
    assert completed_payload["payload"]["requirement_detail"] == {
        "research_goal": "分析中国 AI 搜索产品竞争格局",
        "domain": "互联网 / AI 产品",
        "requirement_details": "聚焦中国市场，偏商业分析，覆盖近两年变化。",
        "output_format": "business_report",
        "freshness_requirement": "high",
        "language": "zh-CN",
    }


@pytest.mark.asyncio
async def test_natural_clarification_can_execute_one_web_search_then_emit_final_ready(
    settings: Settings,
    fake_clock: FakeClock,
) -> None:
    clarification_generator = ScriptedClarificationGenerator(
        natural_generations=(
            TextGeneration(
                deltas=(),
                full_text="",
                tool_calls=(
                    {
                        "id": "call_search_concept",
                        "name": "web_search",
                        "arguments": json.dumps(
                            {
                                "search_query": "Deep Research",
                                "search_recency_filter": "oneWeek",
                            },
                            ensure_ascii=False,
                        ),
                    },
                ),
            ),
            TextGeneration(
                deltas=("为了更好开展研究，请明确关注重点。\n1. 你更想聚焦哪些比较维度？",),
                full_text="为了更好开展研究，请明确关注重点。\n1. 你更想聚焦哪些比较维度？",
            ),
        )
    )
    web_search_client = ScriptedWebSearchClient(
        results_by_query={
            "Deep Research": (
                SearchHit(
                    title="Deep Research 背景说明",
                    link="https://example.com/deep-research",
                    snippet="这是一种面向复杂问题的研究工作流。",
                    publish_date="2025-06-10",
                ),
            )
        }
    )
    app = create_app(
        settings=settings,
        clock=fake_clock.now,
        clarification_generator=clarification_generator,
        requirement_analyzer=ScriptedRequirementAnalyzer(),
        web_search_client=web_search_client,
    )
    await app.router.startup()

    transport = StreamingASGITransport(app=app, client=("203.0.113.10", 51000))
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        create_response = await client.post(
            "/api/v1/tasks",
            json=build_create_task_payload(clarification_mode="natural"),
        )
        create_body = create_response.json()

        async with client.stream(
            "GET",
            f"/api/v1/tasks/{create_body['task_id']}/events",
            headers={"Authorization": f"Bearer {create_body['task_token']}"},
        ) as response:
            lines = response.aiter_lines()
            await read_until_event(lines, {"task.created"})
            _, delta_name, delta_payload = await read_until_event(lines, {"clarification.delta"})
            _, ready_name, ready_payload = await read_until_event(
                lines,
                {"clarification.natural.ready"},
            )

    await app.state.task_lifecycle.shutdown()
    await app.router.shutdown()

    assert delta_name == "clarification.delta"
    assert "明确关注重点" in delta_payload["payload"]["delta"]
    assert ready_name == "clarification.natural.ready"
    assert ready_payload["payload"]["status"] == "awaiting_user_input"
    assert web_search_client.calls == [
        {"query": "Deep Research", "recency_filter": "oneWeek"}
    ]
    assert len(clarification_generator.natural_invocations) == 2
    first_round = clarification_generator.natural_invocations[0]
    assert first_round.prompt_bundle.system_prompt is not None
    assert "最多调用一次" in first_round.prompt_bundle.system_prompt
    assert [tool.name for tool in first_round.tool_schemas] == ["web_search"]
    second_round = clarification_generator.natural_invocations[1]
    assert [message.role for message in second_round.prompt_bundle.transcript] == [
        "assistant",
        "tool",
    ]
    assert second_round.prompt_bundle.transcript[0].tool_calls == (
        {
            "id": "call_search_concept",
            "type": "function",
            "function": {
                "name": "web_search",
                "arguments": json.dumps(
                    {
                        "search_query": "Deep Research",
                        "search_recency_filter": "oneWeek",
                    },
                    ensure_ascii=False,
                ),
            },
        },
    )
    tool_payload = json.loads(second_round.prompt_bundle.transcript[1].content)
    assert tool_payload == {
        "success": True,
        "search_query": "Deep Research",
        "search_recency_filter": "oneWeek",
        "results": [
            {
                "title": "Deep Research 背景说明",
                "link": "https://example.com/deep-research",
                "snippet": "这是一种面向复杂问题的研究工作流。",
                "publish_date": "2025-06-10",
            }
        ],
    }


@pytest.mark.asyncio
async def test_options_clarification_can_execute_one_web_search_then_emit_ready_and_countdown(
    settings: Settings,
    fake_clock: FakeClock,
) -> None:
    clarification_generator = ScriptedClarificationGenerator(
        options_generations=(
            TextGeneration(
                deltas=(),
                full_text="",
                tool_calls=(
                    {
                        "id": "call_search_entity",
                        "name": "web_search",
                        "arguments": json.dumps(
                            {
                                "search_query": "Agentic AI",
                            },
                            ensure_ascii=False,
                        ),
                    },
                ),
            ),
            TextGeneration(
                deltas=("1. 你更想聚焦哪个方向？\n- 行业现状\n- 竞争格局\n- 商业化机会",),
                full_text=(
                    "1. 你更想聚焦哪个方向？\n"
                    "- 行业现状\n"
                    "- 竞争格局\n"
                    "- 商业化机会"
                ),
            ),
        )
    )
    web_search_client = ScriptedWebSearchClient(
        results_by_query={
            "Agentic AI": (
                SearchHit(
                    title="Agentic AI 定义",
                    link="https://example.com/agentic-ai",
                    snippet="Agentic AI 强调多步目标执行与工具使用。",
                    publish_date=None,
                ),
            )
        }
    )
    app = create_app(
        settings=settings,
        clock=fake_clock.now,
        clarification_generator=clarification_generator,
        requirement_analyzer=ScriptedRequirementAnalyzer(),
        web_search_client=web_search_client,
    )
    await app.router.startup()

    transport = StreamingASGITransport(app=app, client=("203.0.113.10", 51000))
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        create_response = await client.post(
            "/api/v1/tasks",
            json=build_create_task_payload(clarification_mode="options"),
        )
        create_body = create_response.json()

        async with client.stream(
            "GET",
            f"/api/v1/tasks/{create_body['task_id']}/events",
            headers={"Authorization": f"Bearer {create_body['task_token']}"},
        ) as response:
            lines = response.aiter_lines()
            await read_until_event(lines, {"task.created"})
            await read_until_event(lines, {"clarification.delta"})
            _, ready_name, ready_payload = await read_until_event(
                lines,
                {"clarification.options.ready"},
            )
            _, countdown_name, countdown_payload = await read_until_event(
                lines,
                {"clarification.countdown.started"},
            )

    await app.state.task_lifecycle.shutdown()
    await app.router.shutdown()

    assert ready_name == "clarification.options.ready"
    assert ready_payload["payload"]["question_set"]["questions"][0]["options"][-1] == {
        "option_id": "o_auto",
        "label": "自动",
    }
    assert countdown_name == "clarification.countdown.started"
    assert countdown_payload["payload"]["duration_seconds"] == 15
    assert web_search_client.calls == [
        {"query": "Agentic AI", "recency_filter": "noLimit"}
    ]
    assert len(clarification_generator.options_invocations) == 2
    second_round = clarification_generator.options_invocations[1]
    assert second_round.prompt_bundle.transcript[0].tool_calls == (
        {
            "id": "call_search_entity",
            "type": "function",
            "function": {
                "name": "web_search",
                "arguments": json.dumps(
                    {"search_query": "Agentic AI"},
                    ensure_ascii=False,
                ),
            },
        },
    )
    tool_payload = json.loads(second_round.prompt_bundle.transcript[1].content)
    assert tool_payload["results"][0]["publish_date"] is None


@pytest.mark.asyncio
async def test_clarification_web_search_limit_exceeded_uses_deterministic_tool_payload(
    settings: Settings,
    fake_clock: FakeClock,
) -> None:
    clarification_generator = ScriptedClarificationGenerator(
        natural_generations=(
            TextGeneration(
                deltas=(),
                full_text="",
                tool_calls=(
                    {
                        "id": "call_search_1",
                        "name": "web_search",
                        "arguments": json.dumps({"search_query": "概念 A"}, ensure_ascii=False),
                    },
                    {
                        "id": "call_search_2",
                        "name": "web_search",
                        "arguments": json.dumps({"search_query": "概念 B"}, ensure_ascii=False),
                    },
                ),
            ),
            TextGeneration(
                deltas=("为了更好开展研究，请补充你最关心的比较对象。",),
                full_text="为了更好开展研究，请补充你最关心的比较对象。",
            ),
        )
    )
    web_search_client = ScriptedWebSearchClient(results_by_query={})
    app = create_app(
        settings=settings,
        clock=fake_clock.now,
        clarification_generator=clarification_generator,
        requirement_analyzer=ScriptedRequirementAnalyzer(),
        web_search_client=web_search_client,
    )
    await app.router.startup()

    transport = StreamingASGITransport(app=app, client=("203.0.113.10", 51000))
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        create_response = await client.post(
            "/api/v1/tasks",
            json=build_create_task_payload(clarification_mode="natural"),
        )
        create_body = create_response.json()

        async with client.stream(
            "GET",
            f"/api/v1/tasks/{create_body['task_id']}/events",
            headers={"Authorization": f"Bearer {create_body['task_token']}"},
        ) as response:
            lines = response.aiter_lines()
            await read_until_event(lines, {"task.created"})
            await read_until_event(lines, {"clarification.delta"})
            await read_until_event(lines, {"clarification.natural.ready"})

    await app.state.task_lifecycle.shutdown()
    await app.router.shutdown()

    assert web_search_client.calls == []
    second_round = clarification_generator.natural_invocations[1]
    tool_payload = json.loads(second_round.prompt_bundle.transcript[1].content)
    assert tool_payload == {
        "success": False,
        "search_query": "概念 A",
        "search_recency_filter": "noLimit",
        "results": [],
        "error_code": "tool_call_limit_exceeded",
    }


@pytest.mark.asyncio
async def test_clarification_and_requirement_analysis_persist_unified_llm_traces(
    stage4_client: AsyncClient,
    db_session: Session,
) -> None:
    create_response = await stage4_client.post(
        "/api/v1/tasks",
        json=build_create_task_payload(clarification_mode="natural"),
    )
    create_body = create_response.json()

    async with stage4_client.stream(
        "GET",
        f"/api/v1/tasks/{create_body['task_id']}/events",
        headers={"Authorization": f"Bearer {create_body['task_token']}"},
    ) as response:
        lines = response.aiter_lines()
        await read_until_event(lines, {"task.created"})
        await read_until_event(lines, {"clarification.natural.ready"})
        submit_response = await stage4_client.post(
            f"/api/v1/tasks/{create_body['task_id']}/clarification",
            headers={"Authorization": f"Bearer {create_body['task_token']}"},
            json={
                "mode": "natural",
                "answer_text": "重点看中国市场，偏商业分析，覆盖近两年变化。",
            },
        )
        await read_until_event(lines, {"analysis.completed"})

    assert submit_response.status_code == 202

    traces = list(
        db_session.scalars(
            select(LLMCallTraceRecord)
            .where(LLMCallTraceRecord.task_id == create_body["task_id"])
            .where(
                LLMCallTraceRecord.stage.in_(
                    ("clarification_natural", "requirement_analysis")
                )
            )
            .order_by(LLMCallTraceRecord.id.asc())
        )
    )

    assert [trace.stage for trace in traces] == [
        "clarification_natural",
        "requirement_analysis",
    ]
    assert traces[0].request_json["model"] == "glm-5"
    assert "为了更好开展研究" in traces[0].parsed_text
    assert traces[1].parsed_text.strip().startswith("{")
    assert traces[1].provider_finish_reason is None
    assert traces[1].request_id is None


@pytest.mark.asyncio
async def test_options_clarification_persists_unified_llm_trace(
    stage4_client: AsyncClient,
    db_session: Session,
) -> None:
    create_response = await stage4_client.post(
        "/api/v1/tasks",
        json=build_create_task_payload(clarification_mode="options"),
    )
    create_body = create_response.json()

    async with stage4_client.stream(
        "GET",
        f"/api/v1/tasks/{create_body['task_id']}/events",
        headers={"Authorization": f"Bearer {create_body['task_token']}"},
    ) as response:
        lines = response.aiter_lines()
        await read_until_event(lines, {"task.created"})
        await read_until_event(lines, {"clarification.options.ready"})

    trace = db_session.scalar(
        select(LLMCallTraceRecord)
        .where(LLMCallTraceRecord.task_id == create_body["task_id"])
        .where(LLMCallTraceRecord.stage == "clarification_options")
    )

    assert trace is not None
    assert trace.request_json["model"] == "glm-5"
    assert "行业现状" in trace.parsed_text


@pytest.mark.asyncio
async def test_options_clarification_flow_emits_ready_and_countdown(
    stage4_client: AsyncClient,
) -> None:
    create_response = await stage4_client.post(
        "/api/v1/tasks",
        json=build_create_task_payload(clarification_mode="options"),
    )
    create_body = create_response.json()

    async with stage4_client.stream(
        "GET",
        f"/api/v1/tasks/{create_body['task_id']}/events",
        headers={"Authorization": f"Bearer {create_body['task_token']}"},
    ) as response:
        lines = response.aiter_lines()
        await read_until_event(lines, {"task.created"})
        _, delta_name, _ = await read_until_event(lines, {"clarification.delta"})
        _, ready_name, ready_payload = await read_until_event(lines, {"clarification.options.ready"})
        _, countdown_name, countdown_payload = await read_until_event(
            lines,
            {"clarification.countdown.started"},
        )

    assert delta_name == "clarification.delta"
    assert ready_name == "clarification.options.ready"
    assert ready_payload["payload"]["status"] == "awaiting_user_input"
    assert ready_payload["payload"]["available_actions"] == ["submit_clarification"]
    assert ready_payload["payload"]["question_set"]["questions"][0]["options"][-1] == {
        "option_id": "o_auto",
        "label": "自动",
    }
    assert countdown_name == "clarification.countdown.started"
    assert countdown_payload["payload"]["duration_seconds"] == 15
    assert countdown_payload["payload"]["started_at"]


@pytest.mark.asyncio
async def test_options_parse_failure_falls_back_to_natural_clarification(
    settings: Settings,
    fake_clock: FakeClock,
) -> None:
    app = create_app(
        settings=settings,
        clock=fake_clock.now,
        clarification_generator=ScriptedClarificationGenerator(
            options_generation=TextGeneration(
                deltas=("这是一段无法解析的问题草稿。",),
                full_text="这是一段无法解析的问题草稿。",
            )
        ),
        requirement_analyzer=ScriptedRequirementAnalyzer(),
    )
    await app.router.startup()

    transport = StreamingASGITransport(app=app, client=("203.0.113.10", 51000))
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        create_response = await client.post(
            "/api/v1/tasks",
            json=build_create_task_payload(clarification_mode="options"),
        )
        create_body = create_response.json()

        async with client.stream(
            "GET",
            f"/api/v1/tasks/{create_body['task_id']}/events",
            headers={"Authorization": f"Bearer {create_body['task_token']}"},
        ) as response:
            lines = response.aiter_lines()
            await read_until_event(lines, {"task.created"})
            _, fallback_name, fallback_payload = await read_until_event(
                lines,
                {"clarification.fallback_to_natural"},
            )
            _, ready_name, ready_payload = await read_until_event(
                lines,
                {"clarification.natural.ready"},
            )

    await app.state.task_lifecycle.shutdown()
    await app.router.shutdown()

    assert fallback_name == "clarification.fallback_to_natural"
    assert fallback_payload["payload"] == {"reason": "parse_failed"}
    assert ready_name == "clarification.natural.ready"
    assert ready_payload["payload"]["status"] == "awaiting_user_input"


@pytest.mark.asyncio
async def test_options_backend_timeout_auto_submits_after_sixty_seconds(
    stage4_client: AsyncClient,
    fake_clock: FakeClock,
) -> None:
    create_response = await stage4_client.post(
        "/api/v1/tasks",
        json=build_create_task_payload(clarification_mode="options"),
    )
    create_body = create_response.json()

    async with stage4_client.stream(
        "GET",
        f"/api/v1/tasks/{create_body['task_id']}/events",
        headers={"Authorization": f"Bearer {create_body['task_token']}"},
    ) as response:
        lines = response.aiter_lines()
        await read_until_event(lines, {"task.created"})
        await read_until_event(lines, {"clarification.options.ready"})
        await read_until_event(lines, {"clarification.countdown.started"})

        fake_clock.advance(seconds=30)
        await asyncio.sleep(0.1)
        heartbeat_response = await stage4_client.post(
            f"/api/v1/tasks/{create_body['task_id']}/heartbeat",
            headers={"Authorization": f"Bearer {create_body['task_token']}"},
            json={"client_time": fake_clock.now().isoformat()},
        )

        fake_clock.advance(seconds=31)
        await asyncio.sleep(0.1)
        _, phase_name, _ = await read_until_event(lines, {"phase.changed"})
        _, completed_name, completed_payload = await read_until_event(
            lines,
            {"analysis.completed"},
        )

    assert heartbeat_response.status_code == 204
    assert phase_name == "phase.changed"
    assert completed_name == "analysis.completed"
    assert completed_payload["payload"]["requirement_detail"]["research_goal"] == (
        "分析中国 AI 搜索产品竞争格局"
    )
