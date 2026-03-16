import zipfile
from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from io import BytesIO
from pathlib import Path

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.dto.delivery import (
    GeneratedArtifact,
    OutlineDecision,
    OutlineInvocation,
    OutlineSection,
    ResearchOutline,
    SandboxExecutionResult,
    WriterDecision,
    WriterInvocation,
    WriterToolCall,
)
from app.application.ports.delivery import (
    ArtifactStore,
    E2BSandboxClient,
    OutlineAgent,
    ReportExportService,
    WriterAgent,
)
from app.application.services.invocation import RetryableOperationError
from app.core.config import Settings
from app.domain.enums import AccessTokenResourceType
from app.infrastructure.db.models import ArtifactRecord, TaskRevisionRecord, TaskToolCallRecord
from app.infrastructure.delivery.local import LocalArtifactStore, LocalReportExportService
from app.main import create_app
from tests.contract.rest.test_task_events import read_sse_event, read_until_event
from tests.contract.rest.test_tasks import build_create_task_payload
from tests.fixtures.app import StreamingASGITransport
from tests.fixtures.runtime import FakeClock


class ScriptedOutlineAgent(OutlineAgent):
    def __init__(self, decision: OutlineDecision) -> None:
        self.decision = decision
        self.invocations: list[OutlineInvocation] = []

    async def prepare(self, invocation: OutlineInvocation) -> OutlineDecision:
        self.invocations.append(invocation)
        return self.decision


class ScriptedWriterAgent(WriterAgent):
    def __init__(self, decision: WriterDecision) -> None:
        self.decision = decision
        self.invocations: list[WriterInvocation] = []

    async def write(self, invocation: WriterInvocation) -> WriterDecision:
        self.invocations.append(invocation)
        return self.decision


@dataclass(slots=True)
class SandboxScenario:
    create_failures_remaining: int = 0
    execute_failures_remaining: int = 0
    created_ids: list[str] = field(default_factory=list)
    executed_calls: list[tuple[str, str]] = field(default_factory=list)
    destroyed_ids: list[str] = field(default_factory=list)


class ScriptedSandboxClient(E2BSandboxClient):
    def __init__(
        self,
        *,
        scenario: SandboxScenario,
        artifacts_by_code: dict[str, Sequence[GeneratedArtifact]],
    ) -> None:
        self.scenario = scenario
        self.artifacts_by_code = artifacts_by_code

    async def create(self) -> str:
        if self.scenario.create_failures_remaining > 0:
            self.scenario.create_failures_remaining -= 1
            raise RetryableOperationError("temporary sandbox create failure")

        sandbox_id = f"sbox_{len(self.scenario.created_ids) + 1}"
        self.scenario.created_ids.append(sandbox_id)
        return sandbox_id

    async def execute_python(self, sandbox_id: str, code: str) -> SandboxExecutionResult:
        self.scenario.executed_calls.append((sandbox_id, code))
        if self.scenario.execute_failures_remaining > 0:
            self.scenario.execute_failures_remaining -= 1
            raise RetryableOperationError("temporary sandbox execute failure")

        return SandboxExecutionResult(
            stdout="ok",
            artifacts=tuple(self.artifacts_by_code.get(code, ())),
        )

    async def destroy(self, sandbox_id: str) -> None:
        self.scenario.destroyed_ids.append(sandbox_id)


class FlakyArtifactStore(ArtifactStore):
    def __init__(self, *, inner: ArtifactStore, put_failures_remaining: int = 0) -> None:
        self.inner = inner
        self.put_failures_remaining = put_failures_remaining

    async def put(self, storage_key: str, content: bytes, mime_type: str) -> None:
        if self.put_failures_remaining > 0:
            self.put_failures_remaining -= 1
            raise RetryableOperationError("temporary artifact upload failure")
        await self.inner.put(storage_key, content, mime_type)

    async def get(self, storage_key: str) -> bytes:
        return await self.inner.get(storage_key)


@pytest_asyncio.fixture
async def make_stage6_client(
    settings: Settings,
    fake_clock: FakeClock,
    temp_artifact_dir: Path,
):
    apps_to_shutdown: list[FastAPI] = []

    async def _factory(
        *,
        outline_agent: OutlineAgent,
        writer_agent: WriterAgent,
        sandbox_client: E2BSandboxClient,
        artifact_store: ArtifactStore | None = None,
        report_export_service: ReportExportService | None = None,
    ) -> AsyncClient:
        test_settings = replace(settings, llm_retry_wait_seconds=0)
        app = create_app(
            settings=test_settings,
            clock=fake_clock.now,
            outline_agent=outline_agent,
            writer_agent=writer_agent,
            sandbox_client=sandbox_client,
            artifact_store=artifact_store or LocalArtifactStore(root_dir=temp_artifact_dir),
            report_export_service=report_export_service or LocalReportExportService(),
        )
        await app.router.startup()
        apps_to_shutdown.append(app)
        transport = StreamingASGITransport(app=app, client=("203.0.113.10", 51000))
        return AsyncClient(transport=transport, base_url="http://testserver")

    yield _factory

    for app in reversed(apps_to_shutdown):
        await app.state.task_lifecycle.shutdown()
        await app.router.shutdown()


def build_outline_decision() -> OutlineDecision:
    return OutlineDecision(
        deltas=("{\n  \"research_outline\": {",),
        outline=ResearchOutline(
            title="中国 AI 搜索产品竞争格局研究",
            sections=(
                OutlineSection(
                    section_id="section_1",
                    title="研究背景与问题定义",
                    description="界定研究边界与分析框架。",
                    order=1,
                ),
                OutlineSection(
                    section_id="section_2",
                    title="竞争格局与主要玩家",
                    description="比较核心玩家与差异化能力。",
                    order=2,
                ),
            ),
            entities=("AI 搜索产品", "中国市场", "竞争格局"),
        ),
    )


def build_writer_decision(*, tool_call_count: int = 1) -> WriterDecision:
    return WriterDecision(
        reasoning_deltas=("先完成正文，再补图表。",),
        content_deltas=(
            "## 一、研究背景与问题定义\n",
            "## 二、竞争格局与主要玩家\n",
        ),
        tool_calls=tuple(
            WriterToolCall(
                tool_call_id=f"call_writer_{index}",
                tool_name="python_interpreter",
                code=f"plot_{index}",
            )
            for index in range(1, tool_call_count + 1)
        ),
        final_markdown="# 中国 AI 搜索产品竞争格局研究\n\n## 一、研究背景与问题定义\n正文。\n",
    )


async def _start_delivery_flow(client: AsyncClient) -> tuple[dict[str, object], object]:
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
async def test_writer_creates_sandbox_lazily_reuses_it_and_destroys_it_on_delivery_completion(
    make_stage6_client,
    db_session: Session,
    temp_artifact_dir: Path,
) -> None:
    outline_agent = ScriptedOutlineAgent(build_outline_decision())
    writer_agent = ScriptedWriterAgent(build_writer_decision(tool_call_count=2))
    scenario = SandboxScenario()
    sandbox_client = ScriptedSandboxClient(
        scenario=scenario,
        artifacts_by_code={
            "plot_1": (
                GeneratedArtifact(
                    filename="chart_market_share.png",
                    mime_type="image/png",
                    content=b"png-chart-1",
                ),
            ),
            "plot_2": (
                GeneratedArtifact(
                    filename="chart_growth.png",
                    mime_type="image/png",
                    content=b"png-chart-2",
                ),
            ),
        },
    )
    client = await make_stage6_client(
        outline_agent=outline_agent,
        writer_agent=writer_agent,
        sandbox_client=sandbox_client,
    )

    async with client:
        create_body, (stream_context, response, lines) = await _start_delivery_flow(client)
        await read_until_event(
            lines,
            {"artifact.ready"},
            timeout=2.0,
        )
        _, phase_changed_name, phase_changed_payload = await read_until_event(
            lines,
            {"phase.changed"},
            timeout=2.0,
        )
        _, report_completed_name, report_completed_payload = await read_until_event(
            lines,
            {"report.completed"},
            timeout=2.0,
        )
        _, awaiting_feedback_name, awaiting_feedback_payload = await read_until_event(
            lines,
            {"task.awaiting_feedback"},
            timeout=2.0,
        )
        await _close_stream(stream_context, response)

    db_session.expire_all()
    revision = db_session.get(TaskRevisionRecord, create_body["snapshot"]["active_revision_id"])
    artifacts = list(
        db_session.scalars(
            select(ArtifactRecord)
            .where(ArtifactRecord.task_id == create_body["task_id"])
            .order_by(ArtifactRecord.created_at.asc())
        )
    )

    assert revision is not None
    assert revision.revision_status == "completed"
    assert len(scenario.created_ids) == 1
    assert len(scenario.executed_calls) == 2
    assert len({sandbox_id for sandbox_id, _ in scenario.executed_calls}) == 1
    assert scenario.destroyed_ids == scenario.created_ids

    assert len(artifacts) == 4
    assert {
        artifact.resource_type for artifact in artifacts
    } == {
        AccessTokenResourceType.ARTIFACT.value,
        AccessTokenResourceType.MARKDOWN_DOWNLOAD.value,
        AccessTokenResourceType.PDF_DOWNLOAD.value,
    }
    assert phase_changed_name == "phase.changed"
    assert phase_changed_payload["payload"]["to_phase"] == "delivered"
    assert phase_changed_payload["payload"]["status"] == "awaiting_feedback"
    assert report_completed_name == "report.completed"
    assert report_completed_payload["payload"]["delivery"]["artifact_count"] == 2
    assert awaiting_feedback_name == "task.awaiting_feedback"
    assert awaiting_feedback_payload["payload"]["available_actions"] == [
        "submit_feedback",
        "download_markdown",
        "download_pdf",
    ]
    assert awaiting_feedback_payload["payload"]["expires_at"]
    assert int(phase_changed_payload["seq"]) < int(report_completed_payload["seq"])
    assert int(report_completed_payload["seq"]) < int(awaiting_feedback_payload["seq"])

    zip_artifact = next(
        artifact
        for artifact in artifacts
        if artifact.resource_type == AccessTokenResourceType.MARKDOWN_DOWNLOAD.value
    )
    pdf_artifact = next(
        artifact
        for artifact in artifacts
        if artifact.resource_type == AccessTokenResourceType.PDF_DOWNLOAD.value
    )

    zip_path = temp_artifact_dir / zip_artifact.storage_key
    pdf_path = temp_artifact_dir / pdf_artifact.storage_key
    assert zip_path.exists()
    assert pdf_path.exists()
    assert pdf_path.read_bytes().startswith(b"%PDF-1.4")

    with zipfile.ZipFile(BytesIO(zip_path.read_bytes())) as archive:
        assert sorted(archive.namelist()) == [
            "artifacts/chart_growth.png",
            "artifacts/chart_market_share.png",
            "report.md",
        ]


@pytest.mark.asyncio
async def test_writer_tool_call_requested_precedes_completed_event_for_same_call(
    make_stage6_client,
) -> None:
    client = await make_stage6_client(
        outline_agent=ScriptedOutlineAgent(build_outline_decision()),
        writer_agent=ScriptedWriterAgent(build_writer_decision(tool_call_count=1)),
        sandbox_client=ScriptedSandboxClient(
            scenario=SandboxScenario(),
            artifacts_by_code={
                "plot_1": (
                    GeneratedArtifact(
                        filename="chart_market_share.png",
                        mime_type="image/png",
                        content=b"png-chart-1",
                    ),
                ),
            },
        ),
    )

    async with client:
        _, (stream_context, response, lines) = await _start_delivery_flow(client)
        requested = await read_until_event(lines, {"writer.tool_call.requested"}, timeout=2.0)
        completed = await read_until_event(lines, {"writer.tool_call.completed"}, timeout=2.0)
        await _close_stream(stream_context, response)

    assert requested[1] == "writer.tool_call.requested"
    assert completed[1] == "writer.tool_call.completed"
    assert int(requested[0] or "0") < int(completed[0] or "0")
    assert requested[2]["payload"]["tool_call_id"] == completed[2]["payload"]["tool_call_id"]


@pytest.mark.asyncio
async def test_sandbox_execution_retry_exhaustion_fails_revision_and_destroys_sandbox(
    make_stage6_client,
) -> None:
    scenario = SandboxScenario(execute_failures_remaining=4)
    sandbox_client = ScriptedSandboxClient(
        scenario=scenario,
        artifacts_by_code={},
    )
    client = await make_stage6_client(
        outline_agent=ScriptedOutlineAgent(build_outline_decision()),
        writer_agent=ScriptedWriterAgent(build_writer_decision(tool_call_count=1)),
        sandbox_client=sandbox_client,
    )

    async with client:
        _, (stream_context, response, lines) = await _start_delivery_flow(client)
        requested = await read_until_event(lines, {"writer.tool_call.requested"}, timeout=2.0)
        completed = await read_until_event(lines, {"writer.tool_call.completed"}, timeout=2.0)
        _, failed_name, failed_payload = await read_until_event(
            lines,
            {"task.failed"},
            timeout=2.0,
        )
        await _close_stream(stream_context, response)

    assert requested[1] == "writer.tool_call.requested"
    assert completed[1] == "writer.tool_call.completed"
    assert completed[2]["payload"]["success"] is False
    assert failed_name == "task.failed"
    assert failed_payload["payload"]["error"]["code"] == "upstream_service_error"
    assert len(scenario.created_ids) == 1
    assert len(scenario.destroyed_ids) == 1


@pytest.mark.asyncio
async def test_artifact_upload_retry_exhaustion_fails_revision_without_silent_degradation(
    make_stage6_client,
    temp_artifact_dir: Path,
) -> None:
    scenario = SandboxScenario()
    sandbox_client = ScriptedSandboxClient(
        scenario=scenario,
        artifacts_by_code={
            "plot_1": (
                GeneratedArtifact(
                    filename="chart_market_share.png",
                    mime_type="image/png",
                    content=b"png-chart-1",
                ),
            ),
        },
    )
    client = await make_stage6_client(
        outline_agent=ScriptedOutlineAgent(build_outline_decision()),
        writer_agent=ScriptedWriterAgent(build_writer_decision(tool_call_count=1)),
        sandbox_client=sandbox_client,
        artifact_store=FlakyArtifactStore(
            inner=LocalArtifactStore(root_dir=temp_artifact_dir),
            put_failures_remaining=4,
        ),
    )

    async with client:
        _, (stream_context, response, lines) = await _start_delivery_flow(client)
        await read_until_event(lines, {"writer.tool_call.requested"}, timeout=2.0)
        completed = await read_until_event(lines, {"writer.tool_call.completed"}, timeout=2.0)
        _, failed_name, failed_payload = await read_until_event(
            lines,
            {"task.failed"},
            timeout=2.0,
        )
        await _close_stream(stream_context, response)

    assert completed[1] == "writer.tool_call.completed"
    assert completed[2]["payload"]["success"] is False
    assert failed_name == "task.failed"
    assert failed_payload["payload"]["error"]["code"] == "upstream_service_error"
    assert len(scenario.created_ids) == 1
    assert len(scenario.destroyed_ids) == 1
