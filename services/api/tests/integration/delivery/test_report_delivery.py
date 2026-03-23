from base64 import b64decode
import zipfile
from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from io import BytesIO
import json
from pathlib import Path

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import AsyncClient
from pypdf import PdfReader
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
from app.infrastructure.db.models import (
    AgentRunRecord,
    ArtifactRecord,
    TaskRevisionRecord,
    TaskToolCallRecord,
)
from app.infrastructure.delivery.local import LocalArtifactStore, LocalReportExportService
from app.main import create_app
from tests.contract.rest.test_task_events import assert_stream_closed, read_sse_event, read_until_event
from tests.contract.rest.test_tasks import build_create_task_payload
from tests.fixtures.app import StreamingASGITransport
from tests.fixtures.runtime import FakeClock

_ONE_PIXEL_PNG = b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO3Z7xQAAAAASUVORK5CYII="
)


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(pdf_bytes))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def _count_pdf_images(pdf_bytes: bytes) -> int:
    reader = PdfReader(BytesIO(pdf_bytes))
    count = 0

    for page in reader.pages:
        resources = page.get("/Resources")
        if resources is None:
            continue
        xobjects = resources.get("/XObject")
        if xobjects is None:
            continue
        for candidate in xobjects.values():
            obj = candidate.get_object()
            if obj.get("/Subtype") == "/Image":
                count += 1

    return count


class ScriptedOutlineAgent(OutlineAgent):
    def __init__(self, decision: OutlineDecision) -> None:
        self.decision = decision
        self.invocations: list[OutlineInvocation] = []

    async def prepare(self, invocation: OutlineInvocation) -> OutlineDecision:
        self.invocations.append(invocation)
        return self.decision


class ScriptedWriterAgent(WriterAgent):
    """Returns tool_calls on first call, then text-only on subsequent calls."""

    def __init__(self, decision: WriterDecision) -> None:
        self.decision = decision
        self.invocations: list[WriterInvocation] = []

    async def write(self, invocation: WriterInvocation) -> WriterDecision:
        self.invocations.append(invocation)
        has_transcript = (
            invocation.prompt_bundle is not None
            and len(invocation.prompt_bundle.transcript) > 0
        )
        if has_transcript:
            return WriterDecision(text=self.decision.text, tool_calls=())
        return self.decision


class TranscriptAwareWriterAgent(WriterAgent):
    def __init__(self, *, tool_call: WriterToolCall, image_alt: str = "图表") -> None:
        self.tool_call = tool_call
        self.image_alt = image_alt
        self.invocations: list[WriterInvocation] = []

    async def write(self, invocation: WriterInvocation) -> WriterDecision:
        self.invocations.append(invocation)
        has_transcript = (
            invocation.prompt_bundle is not None
            and len(invocation.prompt_bundle.transcript) > 0
        )
        if not has_transcript:
            return WriterDecision(text="", tool_calls=(self.tool_call,))

        tool_payload = json.loads(invocation.prompt_bundle.transcript[-1].content)
        artifacts = tool_payload.get("artifacts", [])
        image_markdown = ""
        if artifacts:
            image_markdown = (
                f"\n![{self.image_alt}]({artifacts[0]['canonical_path']})\n"
            )

        return WriterDecision(
            text=f"# 中国 AI 搜索产品竞争格局研究\n\n正文摘要。{image_markdown}",
            tool_calls=(),
        )


class ExecutionFailureAwareWriterAgent(WriterAgent):
    def __init__(self, *, tool_call: WriterToolCall) -> None:
        self.tool_call = tool_call
        self.invocations: list[WriterInvocation] = []

    async def write(self, invocation: WriterInvocation) -> WriterDecision:
        self.invocations.append(invocation)
        has_transcript = (
            invocation.prompt_bundle is not None
            and len(invocation.prompt_bundle.transcript) > 0
        )
        if not has_transcript:
            return WriterDecision(text="", tool_calls=(self.tool_call,))

        tool_payload = json.loads(invocation.prompt_bundle.transcript[-1].content)
        assert tool_payload["success"] is False
        return WriterDecision(
            text=(
                "# 中国 AI 搜索产品竞争格局研究\n\n"
                "图表脚本执行失败后，正文改为直接输出文字分析结论。\n"
            ),
            tool_calls=(),
        )


class FailingWriterAgent(WriterAgent):
    def __init__(self, *, error: Exception) -> None:
        self.error = error
        self.invocations: list[WriterInvocation] = []

    async def write(self, invocation: WriterInvocation) -> WriterDecision:
        self.invocations.append(invocation)
        raise self.error


class PersistentToolCallWriterAgent(WriterAgent):
    def __init__(self, *, code: str = "plot_forever", text: str = "") -> None:
        self.code = code
        self.text = text
        self.invocations: list[WriterInvocation] = []

    async def write(self, invocation: WriterInvocation) -> WriterDecision:
        self.invocations.append(invocation)
        return WriterDecision(
            text=self.text,
            tool_calls=(
                WriterToolCall(
                    tool_call_id=f"call_writer_round_{len(self.invocations)}",
                    tool_name="python_interpreter",
                    code=self.code,
                ),
            ),
        )


class EmptyTextWriterAgent(WriterAgent):
    def __init__(self, *, text: str = "   \n\t") -> None:
        self.text = text
        self.invocations: list[WriterInvocation] = []

    async def write(self, invocation: WriterInvocation) -> WriterDecision:
        self.invocations.append(invocation)
        return WriterDecision(
            text=self.text,
            tool_calls=(),
        )


class MultiRoundAssemblyWriterAgent(WriterAgent):
    def __init__(self) -> None:
        self.invocations: list[WriterInvocation] = []

    async def write(self, invocation: WriterInvocation) -> WriterDecision:
        self.invocations.append(invocation)
        round_num = len(self.invocations)
        if round_num == 1:
            return WriterDecision(
                text="# 中国 AI 搜索产品竞争格局研究\n\n第一部分正文，并以“让我们绘制市场份额图”收尾。",
                tool_calls=(
                    WriterToolCall(
                        tool_call_id="call_writer_round_1",
                        tool_name="python_interpreter",
                        code="plot_round_1",
                    ),
                ),
                reasoning_text="先写研究背景，再请求第一张图。",
            )
        if round_num == 2:
            return WriterDecision(
                text="第二部分正文，承接第一张图后的分析，并继续请求趋势图。",
                tool_calls=(
                    WriterToolCall(
                        tool_call_id="call_writer_round_2",
                        tool_name="python_interpreter",
                        code="plot_round_2",
                    ),
                ),
                reasoning_text="第一张图返回后补中段分析，再请求第二张图。",
            )
        return WriterDecision(
            text="第三部分正文，承接第二张图并给出最终结论。",
            tool_calls=(),
            reasoning_text="收到第二张图后完成结尾。",
        )


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
        results_by_code: dict[str, SandboxExecutionResult] | None = None,
    ) -> None:
        self.scenario = scenario
        self.artifacts_by_code = artifacts_by_code
        self.results_by_code = results_by_code or {}

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

        if code in self.results_by_code:
            return self.results_by_code[code]

        return SandboxExecutionResult(
            success=True,
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

    async def delete(self, storage_key: str) -> None:
        await self.inner.delete(storage_key)


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
        writer_max_rounds: int | None = None,
    ) -> AsyncClient:
        test_settings = replace(
            settings,
            llm_retry_wait_seconds=0,
            writer_max_rounds=writer_max_rounds or settings.writer_max_rounds,
        )
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


def build_outline_decision(
    *,
    provider_finish_reason: str | None = None,
    provider_usage: dict[str, object] | None = None,
) -> OutlineDecision:
    return OutlineDecision(
        deltas=(),
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
        provider_finish_reason=provider_finish_reason,
        provider_usage=provider_usage,
    )


def build_writer_decision(
    *,
    tool_call_count: int = 1,
    provider_finish_reason: str | None = None,
    provider_usage: dict[str, object] | None = None,
) -> WriterDecision:
    return WriterDecision(
        text="# \u4e2d\u56fd AI \u641c\u7d22\u4ea7\u54c1\u7ade\u4e89\u683c\u5c40\u7814\u7a76\n\n## \u4e00\u3001\u7814\u7a76\u80cc\u666f\u4e0e\u95ee\u9898\u5b9a\u4e49\n\u6b63\u6587\u3002\n",
        tool_calls=tuple(
            WriterToolCall(
                tool_call_id=f"call_writer_{index}",
                tool_name="python_interpreter",
                code=f"plot_{index}",
            )
            for index in range(1, tool_call_count + 1)
        ),
        provider_finish_reason=provider_finish_reason,
        provider_usage=provider_usage,
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


async def _read_events_until(
    lines,
    *,
    stop_names: set[str],
    timeout: float = 2.0,
) -> list[tuple[str | None, str | None, dict[str, object]]]:
    events: list[tuple[str | None, str | None, dict[str, object]]] = []
    while True:
        event = await read_sse_event(lines, timeout=timeout)
        events.append(event)
        if event[1] in stop_names:
            return events


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
                    content=_ONE_PIXEL_PNG,
                ),
            ),
            "plot_2": (
                GeneratedArtifact(
                    filename="chart_growth.png",
                    mime_type="image/png",
                    content=_ONE_PIXEL_PNG,
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
        pdf_bytes = pdf_path.read_bytes()
        PdfReader(BytesIO(pdf_bytes))
        assert "中国 AI 搜索产品竞争格局研究" in _extract_pdf_text(pdf_bytes)

        with zipfile.ZipFile(BytesIO(zip_path.read_bytes())) as archive:
            assert sorted(archive.namelist()) == [
                "artifacts/chart_growth.png",
                "artifacts/chart_market_share.png",
                "report.md",
            ]

        await _close_stream(stream_context, response)


@pytest.mark.asyncio
async def test_writer_persists_reasoning_text_and_assembles_multi_round_markdown_in_order(
    make_stage6_client,
    db_session: Session,
) -> None:
    writer_agent = MultiRoundAssemblyWriterAgent()
    client = await make_stage6_client(
        outline_agent=ScriptedOutlineAgent(build_outline_decision()),
        writer_agent=writer_agent,
        sandbox_client=ScriptedSandboxClient(
            scenario=SandboxScenario(),
            artifacts_by_code={
                "plot_round_1": (
                    GeneratedArtifact(
                        filename="chart_market_share.png",
                        mime_type="image/png",
                        content=_ONE_PIXEL_PNG,
                    ),
                ),
                "plot_round_2": (
                    GeneratedArtifact(
                        filename="chart_growth.png",
                        mime_type="image/png",
                        content=_ONE_PIXEL_PNG,
                    ),
                ),
            },
        ),
    )

    async with client:
        create_body, (stream_context, response, lines) = await _start_delivery_flow(client)
        await read_until_event(lines, {"report.completed"}, timeout=2.0)
        task_detail_response = await client.get(
            f"/api/v1/tasks/{create_body['task_id']}",
            headers={"Authorization": f"Bearer {create_body['task_token']}"},
        )
        assert task_detail_response.status_code == 200
        markdown_zip_response = await client.get(
            task_detail_response.json()["delivery"]["markdown_zip_url"]
        )
        await _close_stream(stream_context, response)

    writer_runs = list(
        db_session.scalars(
            select(AgentRunRecord)
            .where(AgentRunRecord.task_id == create_body["task_id"])
            .where(AgentRunRecord.agent_type == "writer")
            .order_by(AgentRunRecord.created_at.asc(), AgentRunRecord.id.asc())
        )
    )

    assert markdown_zip_response.status_code == 200
    with zipfile.ZipFile(BytesIO(markdown_zip_response.content)) as archive:
        report_markdown = archive.read("report.md").decode("utf-8")

    assert len(writer_runs) == 3
    assert [run.reasoning_text for run in writer_runs] == [
        "先写研究背景，再请求第一张图。",
        "第一张图返回后补中段分析，再请求第二张图。",
        "收到第二张图后完成结尾。",
    ]

    round_two_transcript = writer_agent.invocations[1].prompt_bundle.transcript
    assert round_two_transcript is not None
    assert [message.role for message in round_two_transcript] == ["assistant", "tool"]
    assert round_two_transcript[0].reasoning_content == "先写研究背景，再请求第一张图。"
    assert round_two_transcript[0].tool_calls is not None
    assert round_two_transcript[0].tool_calls[0]["id"] == "call_writer_round_1"
    assert round_two_transcript[1].tool_call_id == "call_writer_round_1"
    assert json.loads(round_two_transcript[1].content)["summary"] == "ok"

    first_idx = report_markdown.index("第一部分正文，并以“让我们绘制市场份额图”收尾。")
    second_idx = report_markdown.index("第二部分正文，承接第一张图后的分析，并继续请求趋势图。")
    third_idx = report_markdown.index("第三部分正文，承接第二张图并给出最终结论。")
    assert first_idx < second_idx < third_idx
    assert report_markdown.count("# 中国 AI 搜索产品竞争格局研究") == 1
    assert "![chart_market_share.png](artifacts/chart_market_share.png)" not in report_markdown


@pytest.mark.asyncio
async def test_delivery_persists_provider_finish_reason_and_usage_for_outline_and_writer_runs(
    make_stage6_client,
    db_session: Session,
) -> None:
    client = await make_stage6_client(
        outline_agent=ScriptedOutlineAgent(
            build_outline_decision(
                provider_finish_reason="stop",
                provider_usage={"prompt_tokens": 30, "completion_tokens": 12, "total_tokens": 42},
            )
        ),
        writer_agent=ScriptedWriterAgent(
            build_writer_decision(
                tool_call_count=0,
                provider_finish_reason="stop",
                provider_usage={"prompt_tokens": 44, "completion_tokens": 18, "total_tokens": 62},
            )
        ),
        sandbox_client=ScriptedSandboxClient(
            scenario=SandboxScenario(),
            artifacts_by_code={},
        ),
    )

    async with client:
        create_body, (stream_context, response, lines) = await _start_delivery_flow(client)
        await read_until_event(lines, {"report.completed"}, timeout=2.0)
        await _close_stream(stream_context, response)

    outline_run = db_session.scalar(
        select(AgentRunRecord)
        .where(AgentRunRecord.task_id == create_body["task_id"])
        .where(AgentRunRecord.agent_type == "outliner")
    )
    writer_run = db_session.scalar(
        select(AgentRunRecord)
        .where(AgentRunRecord.task_id == create_body["task_id"])
        .where(AgentRunRecord.agent_type == "writer")
    )

    assert outline_run is not None
    assert outline_run.finish_reason == "outline_completed"
    assert outline_run.provider_finish_reason == "stop"
    assert outline_run.provider_usage_json == {
        "prompt_tokens": 30,
        "completion_tokens": 12,
        "total_tokens": 42,
    }
    assert writer_run is not None
    assert writer_run.finish_reason == "writer_completed"
    assert writer_run.provider_finish_reason == "stop"
    assert writer_run.provider_usage_json == {
        "prompt_tokens": 44,
        "completion_tokens": 18,
        "total_tokens": 62,
    }


@pytest.mark.asyncio
async def test_writer_tool_transcript_contains_summary_and_real_artifact_metadata(
    make_stage6_client,
) -> None:
    writer_agent = ScriptedWriterAgent(build_writer_decision(tool_call_count=1))
    client = await make_stage6_client(
        outline_agent=ScriptedOutlineAgent(build_outline_decision()),
        writer_agent=writer_agent,
        sandbox_client=ScriptedSandboxClient(
            scenario=SandboxScenario(),
            artifacts_by_code={
                "plot_1": (
                    GeneratedArtifact(
                        filename="chart_market_share.png",
                        mime_type="image/png",
                        content=_ONE_PIXEL_PNG,
                    ),
                ),
            },
        ),
    )

    async with client:
        _, (stream_context, response, lines) = await _start_delivery_flow(client)
        await read_until_event(lines, {"report.completed"}, timeout=2.0)
        await _close_stream(stream_context, response)

    assert len(writer_agent.invocations) == 2
    transcript = writer_agent.invocations[1].prompt_bundle.transcript
    assert transcript is not None
    tool_result = json.loads(transcript[-1].content)
    assert tool_result["success"] is True
    assert tool_result["summary"] == "ok"
    assert tool_result["stdout"] == "ok"
    assert tool_result["stderr"] is None
    assert tool_result["error_type"] is None
    assert tool_result["error_message"] is None
    assert tool_result["traceback_excerpt"] is None
    assert tool_result["artifacts"][0]["artifact_id"].startswith("art_")
    assert tool_result["artifacts"][0]["filename"] == "chart_market_share.png"
    assert tool_result["artifacts"][0]["mime_type"] == "image/png"
    assert tool_result["artifacts"][0]["canonical_path"].startswith(
        "mimir://artifact/art_"
    )
    assert transcript[-1].content != "Tool execution completed successfully."


@pytest.mark.asyncio
async def test_writer_tool_transcript_returns_summary_even_when_python_call_has_no_artifacts(
    make_stage6_client,
) -> None:
    writer_agent = ScriptedWriterAgent(build_writer_decision(tool_call_count=1))
    client = await make_stage6_client(
        outline_agent=ScriptedOutlineAgent(build_outline_decision()),
        writer_agent=writer_agent,
        sandbox_client=ScriptedSandboxClient(
            scenario=SandboxScenario(),
            artifacts_by_code={},
        ),
    )

    async with client:
        _, (stream_context, response, lines) = await _start_delivery_flow(client)
        await read_until_event(lines, {"report.completed"}, timeout=2.0)
        await _close_stream(stream_context, response)

    assert len(writer_agent.invocations) == 2
    transcript = writer_agent.invocations[1].prompt_bundle.transcript
    assert transcript is not None
    tool_result = json.loads(transcript[-1].content)
    assert tool_result["success"] is True
    assert tool_result["summary"] == "ok"
    assert tool_result["stdout"] == "ok"
    assert tool_result["stderr"] is None
    assert tool_result["error_type"] is None
    assert tool_result["error_message"] is None
    assert tool_result["traceback_excerpt"] is None
    assert tool_result["artifacts"] == []


@pytest.mark.asyncio
async def test_python_execution_failure_returns_structured_tool_result_and_writer_continues_next_round(
    make_stage6_client,
) -> None:
    writer_agent = ExecutionFailureAwareWriterAgent(
        tool_call=WriterToolCall(
            tool_call_id="call_writer_chart_failure",
            tool_name="python_interpreter",
            code="plot_failure",
        )
    )
    scenario = SandboxScenario()
    client = await make_stage6_client(
        outline_agent=ScriptedOutlineAgent(build_outline_decision()),
        writer_agent=writer_agent,
        sandbox_client=ScriptedSandboxClient(
            scenario=scenario,
            artifacts_by_code={},
            results_by_code={
                "plot_failure": SandboxExecutionResult(
                    success=False,
                    stdout="partial output",
                    stderr="Traceback (most recent call last):\nValueError: bad column",
                    error_type="ValueError",
                    error_message="bad column",
                    traceback_excerpt="Traceback (most recent call last):\nValueError: bad column",
                    artifacts=(),
                ),
            },
        ),
    )

    async with client:
        _, (stream_context, response, lines) = await _start_delivery_flow(client)
        requested = await read_until_event(lines, {"writer.tool_call.requested"}, timeout=2.0)
        completed = await read_until_event(lines, {"writer.tool_call.completed"}, timeout=2.0)
        _, report_completed_name, _ = await read_until_event(lines, {"report.completed"}, timeout=2.0)
        await _close_stream(stream_context, response)

    assert requested[1] == "writer.tool_call.requested"
    assert completed[1] == "writer.tool_call.completed"
    assert completed[2]["payload"]["success"] is False
    assert report_completed_name == "report.completed"
    assert len(scenario.executed_calls) == 1
    assert len(writer_agent.invocations) == 2
    transcript = writer_agent.invocations[1].prompt_bundle.transcript
    assert transcript is not None
    tool_result = json.loads(transcript[-1].content)
    assert tool_result["success"] is False
    assert tool_result["summary"].startswith("Python execution failed")
    assert tool_result["stdout"] == "partial output"
    assert tool_result["stderr"] == "Traceback (most recent call last):\nValueError: bad column"
    assert tool_result["error_type"] == "ValueError"
    assert tool_result["error_message"] == "bad column"
    assert tool_result["traceback_excerpt"] == "Traceback (most recent call last):\nValueError: bad column"
    assert tool_result["artifacts"] == []


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
                        content=_ONE_PIXEL_PNG,
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
async def test_markdown_zip_rewrites_canonical_artifact_refs_to_offline_paths(
    make_stage6_client,
) -> None:
    writer_agent = TranscriptAwareWriterAgent(
        tool_call=WriterToolCall(
            tool_call_id="call_writer_chart",
            tool_name="python_interpreter",
            code="plot_chart",
        ),
        image_alt="市场份额图",
    )
    client = await make_stage6_client(
        outline_agent=ScriptedOutlineAgent(build_outline_decision()),
        writer_agent=writer_agent,
        sandbox_client=ScriptedSandboxClient(
            scenario=SandboxScenario(),
            artifacts_by_code={
                "plot_chart": (
                    GeneratedArtifact(
                        filename="chart_market_share.png",
                        mime_type="image/png",
                        content=_ONE_PIXEL_PNG,
                    ),
                ),
            },
        ),
    )

    async with client:
        create_body, (stream_context, response, lines) = await _start_delivery_flow(client)
        await read_until_event(lines, {"report.completed"}, timeout=2.0)
        task_detail_response = await client.get(
            f"/api/v1/tasks/{create_body['task_id']}",
            headers={"Authorization": f"Bearer {create_body['task_token']}"},
        )
        assert task_detail_response.status_code == 200
        markdown_zip_url = task_detail_response.json()["delivery"]["markdown_zip_url"]
        markdown_zip_response = await client.get(markdown_zip_url)
        await _close_stream(stream_context, response)

    assert markdown_zip_response.status_code == 200
    with zipfile.ZipFile(BytesIO(markdown_zip_response.content)) as archive:
        report_markdown = archive.read("report.md").decode("utf-8")

    assert "mimir://artifact/" not in report_markdown
    assert "![市场份额图](artifacts/chart_market_share.png)" in report_markdown


@pytest.mark.asyncio
async def test_pdf_export_renders_canonical_artifact_refs(
    make_stage6_client,
) -> None:
    writer_agent = TranscriptAwareWriterAgent(
        tool_call=WriterToolCall(
            tool_call_id="call_writer_chart_pdf",
            tool_name="python_interpreter",
            code="plot_chart_pdf",
        ),
        image_alt="市场份额图",
    )
    client = await make_stage6_client(
        outline_agent=ScriptedOutlineAgent(build_outline_decision()),
        writer_agent=writer_agent,
        sandbox_client=ScriptedSandboxClient(
            scenario=SandboxScenario(),
            artifacts_by_code={
                "plot_chart_pdf": (
                    GeneratedArtifact(
                        filename="chart_market_share.png",
                        mime_type="image/png",
                        content=_ONE_PIXEL_PNG,
                    ),
                ),
            },
        ),
    )

    async with client:
        create_body, (stream_context, response, lines) = await _start_delivery_flow(client)
        await read_until_event(lines, {"report.completed"}, timeout=2.0)
        task_detail_response = await client.get(
            f"/api/v1/tasks/{create_body['task_id']}",
            headers={"Authorization": f"Bearer {create_body['task_token']}"},
        )
        assert task_detail_response.status_code == 200
        pdf_url = task_detail_response.json()["delivery"]["pdf_url"]
        pdf_response = await client.get(pdf_url)
        await _close_stream(stream_context, response)

    assert pdf_response.status_code == 200
    assert "中国 AI 搜索产品竞争格局研究" in _extract_pdf_text(pdf_response.content)
    assert _count_pdf_images(pdf_response.content) >= 1


@pytest.mark.asyncio
async def test_markdown_zip_does_not_rewrite_markdown_when_no_canonical_artifact_ref_exists(
    make_stage6_client,
) -> None:
    writer_agent = ScriptedWriterAgent(
        WriterDecision(
            text="# 中国 AI 搜索产品竞争格局研究\n\n正文没有图片引用。\n",
            tool_calls=(),
        )
    )
    client = await make_stage6_client(
        outline_agent=ScriptedOutlineAgent(build_outline_decision()),
        writer_agent=writer_agent,
        sandbox_client=ScriptedSandboxClient(
            scenario=SandboxScenario(),
            artifacts_by_code={},
        ),
    )

    async with client:
        create_body, (stream_context, response, lines) = await _start_delivery_flow(client)
        await read_until_event(lines, {"report.completed"}, timeout=2.0)
        task_detail_response = await client.get(
            f"/api/v1/tasks/{create_body['task_id']}",
            headers={"Authorization": f"Bearer {create_body['task_token']}"},
        )
        assert task_detail_response.status_code == 200
        markdown_zip_url = task_detail_response.json()["delivery"]["markdown_zip_url"]
        markdown_zip_response = await client.get(markdown_zip_url)
        await _close_stream(stream_context, response)

    assert markdown_zip_response.status_code == 200
    with zipfile.ZipFile(BytesIO(markdown_zip_response.content)) as archive:
        report_markdown = archive.read("report.md").decode("utf-8")

    assert report_markdown == "# 中国 AI 搜索产品竞争格局研究\n\n正文没有图片引用。\n"


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
                    content=_ONE_PIXEL_PNG,
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


@pytest.mark.asyncio
async def test_writer_retry_exhaustion_fails_task_and_closes_stream(
    make_stage6_client,
) -> None:
    client = await make_stage6_client(
        outline_agent=ScriptedOutlineAgent(build_outline_decision()),
        writer_agent=FailingWriterAgent(
            error=RetryableOperationError("temporary writer timeout"),
        ),
        sandbox_client=ScriptedSandboxClient(
            scenario=SandboxScenario(),
            artifacts_by_code={},
        ),
    )

    async with client:
        _, (stream_context, response, lines) = await _start_delivery_flow(client)
        _, failed_name, failed_payload = await read_until_event(
            lines,
            {"task.failed"},
            timeout=2.0,
        )
        await assert_stream_closed(lines)
        await _close_stream(stream_context, response)

    assert failed_name == "task.failed"
    assert failed_payload["payload"]["error"]["code"] == "upstream_service_error"


@pytest.mark.asyncio
async def test_unhandled_writer_exception_fails_task_instead_of_leaking_running_state(
    make_stage6_client,
) -> None:
    client = await make_stage6_client(
        outline_agent=ScriptedOutlineAgent(build_outline_decision()),
        writer_agent=FailingWriterAgent(
            error=RuntimeError("writer stream crashed"),
        ),
        sandbox_client=ScriptedSandboxClient(
            scenario=SandboxScenario(),
            artifacts_by_code={},
        ),
    )

    async with client:
        _, (stream_context, response, lines) = await _start_delivery_flow(client)
        _, failed_name, failed_payload = await read_until_event(
            lines,
            {"task.failed"},
            timeout=2.0,
        )
        await assert_stream_closed(lines)
        await _close_stream(stream_context, response)

    assert failed_name == "task.failed"
    assert failed_payload["payload"]["error"]["code"] == "upstream_service_error"


@pytest.mark.asyncio
async def test_writer_max_rounds_exhausted_with_pending_tool_calls_fails_without_report_completed(
    make_stage6_client,
) -> None:
    client = await make_stage6_client(
        outline_agent=ScriptedOutlineAgent(build_outline_decision()),
        writer_agent=PersistentToolCallWriterAgent(text="中间稿。"),
        sandbox_client=ScriptedSandboxClient(
            scenario=SandboxScenario(),
            artifacts_by_code={},
        ),
        writer_max_rounds=2,
    )

    async with client:
        _, (stream_context, response, lines) = await _start_delivery_flow(client)
        events = await _read_events_until(lines, stop_names={"task.failed"}, timeout=2.0)
        await assert_stream_closed(lines)
        await _close_stream(stream_context, response)

    event_names = [event_name for _, event_name, _ in events]
    failed_payload = next(payload for _, event_name, payload in events if event_name == "task.failed")

    assert "report.completed" not in event_names
    assert "task.awaiting_feedback" not in event_names
    assert failed_payload["payload"]["error"]["code"] == "upstream_service_error"


@pytest.mark.asyncio
async def test_writer_blank_markdown_fails_without_report_completed(
    make_stage6_client,
) -> None:
    client = await make_stage6_client(
        outline_agent=ScriptedOutlineAgent(build_outline_decision()),
        writer_agent=EmptyTextWriterAgent(),
        sandbox_client=ScriptedSandboxClient(
            scenario=SandboxScenario(),
            artifacts_by_code={},
        ),
    )

    async with client:
        _, (stream_context, response, lines) = await _start_delivery_flow(client)
        events = await _read_events_until(lines, stop_names={"task.failed"}, timeout=2.0)
        await assert_stream_closed(lines)
        await _close_stream(stream_context, response)

    event_names = [event_name for _, event_name, _ in events]
    failed_payload = next(payload for _, event_name, payload in events if event_name == "task.failed")

    assert "report.completed" not in event_names
    assert "task.awaiting_feedback" not in event_names
    assert failed_payload["payload"]["error"]["code"] == "upstream_service_error"
