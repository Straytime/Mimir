import asyncio
from dataclasses import replace

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import AsyncClient

from app.application.dto.invocation import LLMInvocation
from app.application.ports.llm import ClarificationGenerator, RequirementAnalyzer
from app.application.services.llm import TextGeneration
from app.core.config import Settings
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
    ) -> None:
        self.natural_generation = natural_generation or TextGeneration(
            deltas=("为了更好开展研究，请补充你最关心的研究重点。",),
            full_text="为了更好开展研究，请补充你最关心的研究重点。",
        )
        self.options_generation = options_generation or TextGeneration(
            deltas=("1. 你更想聚焦哪个方向？\nA. 行业现状\nB. 竞争格局",),
            full_text="1. 你更想聚焦哪个方向？\nA. 行业现状\nB. 竞争格局",
        )

    async def generate_natural(self, invocation: LLMInvocation) -> TextGeneration:
        return self.natural_generation

    async def generate_options(self, invocation: LLMInvocation) -> TextGeneration:
        return self.options_generation


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
