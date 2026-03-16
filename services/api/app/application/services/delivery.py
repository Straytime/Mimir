import asyncio
import contextlib
import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session, sessionmaker

from app.application.dto.delivery import (
    GeneratedArtifact,
    OutlineDecision,
    OutlineInvocation,
    ResearchOutline,
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
from app.application.prompts.delivery import build_outline_prompt, build_writer_prompt
from app.application.services.invocation import (
    RetryableOperationError,
    RetryingOperationInvoker,
    RiskControlTriggered,
)
from app.application.services.tasks import TaskService
from app.core.config import Settings
from app.core.ids import generate_id
from app.domain.enums import AccessTokenResourceType, TaskPhase, TaskStatus
from app.domain.schemas import RequirementDetail


@dataclass(slots=True)
class DeliveryRuntime:
    loop_task: asyncio.Task[None] | None = None
    sandbox_id: str | None = None
    cancelled: bool = False


class DeliveryOrchestrator:
    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session],
        task_service: TaskService,
        outline_agent: OutlineAgent,
        writer_agent: WriterAgent,
        sandbox_client: E2BSandboxClient,
        artifact_store: ArtifactStore,
        report_export_service: ReportExportService,
        operation_invoker: RetryingOperationInvoker[object],
        settings: Settings,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._task_service = task_service
        self._outline_agent = outline_agent
        self._writer_agent = writer_agent
        self._sandbox_client = sandbox_client
        self._artifact_store = artifact_store
        self._report_export_service = report_export_service
        self._operation_invoker = operation_invoker
        self._settings = settings
        self._clock = clock or (lambda: datetime.now(UTC))
        self._runtimes: dict[str, DeliveryRuntime] = {}

    async def ensure_started(self, *, task_id: str) -> None:
        runtime = self._runtimes.setdefault(task_id, DeliveryRuntime())
        if runtime.loop_task is not None and not runtime.loop_task.done():
            return
        runtime.loop_task = asyncio.create_task(self._run_delivery_loop(task_id=task_id))

    async def cancel(self, *, task_id: str) -> None:
        runtime = self._runtimes.pop(task_id, None)
        if runtime is None:
            return
        runtime.cancelled = True
        if runtime.loop_task is not None:
            runtime.loop_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await runtime.loop_task
        with contextlib.suppress(RetryableOperationError):
            await self._destroy_sandbox(runtime=runtime)

    async def shutdown(self) -> None:
        for task_id in list(self._runtimes):
            await self.cancel(task_id=task_id)

    async def _run_delivery_loop(self, *, task_id: str) -> None:
        runtime = self._runtimes.setdefault(task_id, DeliveryRuntime())
        try:
            with self._session_factory() as session:
                task_with_revision = self._task_service.repository.get_task_with_revision(
                    session=session,
                    task_id=task_id,
                )
                if task_with_revision is None:
                    return
                task, revision = task_with_revision
                if TaskStatus(task.status) is not TaskStatus.RUNNING:
                    return
                if revision.requirement_detail_json is None:
                    return
                requirement_detail = RequirementDetail.model_validate(
                    revision.requirement_detail_json
                )
                formatted_sources = self._task_service.repository.list_merged_sources(
                    session=session,
                    revision_id=revision.revision_id,
                )
                if not formatted_sources:
                    return

            if task.phase == TaskPhase.MERGING_SOURCES.value:
                await self._transition_phase(
                    task_id=task_id,
                    target_phase=TaskPhase.PREPARING_OUTLINE,
                )

            outline_decision = await self._run_outline(
                task_id=task_id,
                revision_id=revision.revision_id,
                requirement_detail=requirement_detail,
                formatted_sources=formatted_sources,
            )
            if outline_decision is None or await self._is_terminal(task_id=task_id):
                return

            await self._transition_phase(
                task_id=task_id,
                target_phase=TaskPhase.WRITING_REPORT,
            )

            writer_decision = await self._run_writer(
                task_id=task_id,
                revision_id=revision.revision_id,
                requirement_detail=requirement_detail,
                formatted_sources=formatted_sources,
                outline=outline_decision.outline,
            )
            if writer_decision is None or await self._is_terminal(task_id=task_id):
                return

            ready_artifacts: list = []
            for tool_call in writer_decision.tool_calls:
                stored_artifacts = await self._run_writer_tool_call(
                    task_id=task_id,
                    revision_id=revision.revision_id,
                    runtime=runtime,
                    tool_call=tool_call,
                )
                if stored_artifacts is None or await self._is_terminal(task_id=task_id):
                    return
                ready_artifacts.extend(stored_artifacts)

            for delta in writer_decision.content_deltas:
                await self._append_event(
                    task_id=task_id,
                    event="writer.delta",
                    payload={"delta": delta},
                )
            for artifact_record in ready_artifacts:
                with self._session_factory() as session:
                    task = self._task_service.repository.get_task(session=session, task_id=task_id)
                    if task is None:
                        return
                    summary = self._task_service.build_artifact_summary(
                        task=task,
                        artifact=artifact_record,
                    )
                await self._append_event(
                    task_id=task_id,
                    event="artifact.ready",
                    payload={"artifact": summary.model_dump(mode="json")},
                )

            finalized = await self._finalize_delivery(
                task_id=task_id,
                revision_id=revision.revision_id,
                runtime=runtime,
                final_markdown=writer_decision.final_markdown,
            )
            if not finalized:
                return
        finally:
            self._runtimes.pop(task_id, None)

    async def _run_outline(
        self,
        *,
        task_id: str,
        revision_id: str,
        requirement_detail: RequirementDetail,
        formatted_sources,
    ) -> OutlineDecision | None:
        invocation = OutlineInvocation(
            prompt_name="outline_round",
            requirement_detail=requirement_detail,
            formatted_sources=formatted_sources,
            now=self._clock(),
        )
        prompt = build_outline_prompt(invocation=invocation)
        try:
            decision = await self._invoke_operation(
                lambda: self._outline_agent.prepare(invocation)
            )
        except RiskControlTriggered:
            await self._fail_task(
                task_id=task_id,
                error_code="risk_control_triggered",
                message="outline 阶段触发风控。",
            )
            return None
        except RetryableOperationError:
            await self._fail_task(
                task_id=task_id,
                error_code="upstream_service_error",
                message="outline 调用失败且重试耗尽。",
            )
            return None

        now = self._clock()
        with self._session_factory() as session:
            self._task_service.repository.append_agent_run(
                session=session,
                task_id=task_id,
                revision_id=revision_id,
                subtask_id=None,
                agent_type="outliner",
                prompt_name=invocation.prompt_name,
                status="completed",
                reasoning_text="\n".join(decision.deltas),
                content_text=json.dumps(
                    {
                        "prompt": prompt,
                        "outline": _outline_to_payload(decision.outline),
                    },
                    ensure_ascii=False,
                ),
                finish_reason="outline_completed",
                tool_calls_json=None,
                created_at=now,
                updated_at=now,
            )
            session.commit()

        for delta in decision.deltas:
            await self._append_event(
                task_id=task_id,
                event="outline.delta",
                payload={"delta": delta},
            )
        await self._append_event(
            task_id=task_id,
            event="outline.completed",
            payload={"outline": _outline_to_payload(decision.outline)},
        )
        return decision

    async def _run_writer(
        self,
        *,
        task_id: str,
        revision_id: str,
        requirement_detail: RequirementDetail,
        formatted_sources,
        outline: ResearchOutline,
    ) -> WriterDecision | None:
        invocation = WriterInvocation(
            prompt_name="writer_round",
            requirement_detail=requirement_detail,
            formatted_sources=formatted_sources,
            outline=outline,
            now=self._clock(),
        )
        prompt = build_writer_prompt(invocation=invocation)
        try:
            decision = await self._invoke_operation(lambda: self._writer_agent.write(invocation))
        except RiskControlTriggered:
            await self._fail_task(
                task_id=task_id,
                error_code="risk_control_triggered",
                message="writer 阶段触发风控。",
            )
            return None
        except RetryableOperationError:
            await self._fail_task(
                task_id=task_id,
                error_code="upstream_service_error",
                message="writer 调用失败且重试耗尽。",
            )
            return None

        now = self._clock()
        with self._session_factory() as session:
            self._task_service.repository.append_agent_run(
                session=session,
                task_id=task_id,
                revision_id=revision_id,
                subtask_id=None,
                agent_type="writer",
                prompt_name=invocation.prompt_name,
                status="completed",
                reasoning_text="\n".join(decision.reasoning_deltas),
                content_text=json.dumps(
                    {
                        "prompt": prompt,
                        "final_markdown": decision.final_markdown,
                        "tool_calls": [
                            {
                                "tool_call_id": tool_call.tool_call_id,
                                "tool_name": tool_call.tool_name,
                            }
                            for tool_call in decision.tool_calls
                        ],
                    },
                    ensure_ascii=False,
                ),
                finish_reason="writer_completed",
                tool_calls_json={
                    "tool_calls": [
                        {
                            "tool_call_id": tool_call.tool_call_id,
                            "tool_name": tool_call.tool_name,
                        }
                        for tool_call in decision.tool_calls
                    ]
                },
                created_at=now,
                updated_at=now,
            )
            session.commit()

        for delta in decision.reasoning_deltas:
            await self._append_event(
                task_id=task_id,
                event="writer.reasoning.delta",
                payload={"delta": delta},
            )
        return decision

    async def _run_writer_tool_call(
        self,
        *,
        task_id: str,
        revision_id: str,
        runtime: DeliveryRuntime,
        tool_call: WriterToolCall,
    ):
        await self._append_event(
            task_id=task_id,
            event="writer.tool_call.requested",
            payload={
                "tool_call_id": tool_call.tool_call_id,
                "tool_name": tool_call.tool_name,
            },
        )
        try:
            sandbox_id = await self._ensure_sandbox(runtime=runtime)
            result = await self._invoke_operation(
                lambda: self._sandbox_client.execute_python(sandbox_id, tool_call.code)
            )
            stored_artifacts = await self._store_generated_artifacts(
                task_id=task_id,
                revision_id=revision_id,
                generated_artifacts=result.artifacts,
            )
        except RetryableOperationError:
            await self._record_tool_call(
                task_id=task_id,
                revision_id=revision_id,
                tool_call=tool_call,
                status="failed",
                error_code="retry_exhausted",
                response_json=None,
            )
            await self._append_event(
                task_id=task_id,
                event="writer.tool_call.completed",
                payload={
                    "tool_call_id": tool_call.tool_call_id,
                    "tool_name": tool_call.tool_name,
                    "success": False,
                },
            )
            await self._fail_task(
                task_id=task_id,
                error_code="upstream_service_error",
                message="python_interpreter 调用或 artifact 上传失败且重试耗尽。",
            )
            await self._destroy_sandbox(runtime=runtime)
            return None

        await self._record_tool_call(
            task_id=task_id,
            revision_id=revision_id,
            tool_call=tool_call,
            status="completed",
            error_code=None,
            response_json={
                "stdout": result.stdout,
                "artifact_count": len(stored_artifacts),
            },
        )
        await self._append_event(
            task_id=task_id,
            event="writer.tool_call.completed",
            payload={
                "tool_call_id": tool_call.tool_call_id,
                "tool_name": tool_call.tool_name,
                "success": True,
            },
        )
        return stored_artifacts

    async def _store_generated_artifacts(
        self,
        *,
        task_id: str,
        revision_id: str,
        generated_artifacts: tuple[GeneratedArtifact, ...],
    ) -> list:
        now = self._clock()
        stored_records: list = []
        for artifact in generated_artifacts:
            artifact_id = generate_id("art")
            storage_key = (
                f"tasks/{task_id}/{revision_id}/artifacts/{artifact_id}_{artifact.filename}"
            )
            await self._invoke_operation(
                lambda storage_key=storage_key, artifact=artifact: self._artifact_store.put(
                    storage_key,
                    artifact.content,
                    artifact.mime_type,
                )
            )
            with self._session_factory() as session:
                record = self._task_service.repository.append_artifact(
                    session=session,
                    artifact_id=artifact_id,
                    task_id=task_id,
                    revision_id=revision_id,
                    resource_type=AccessTokenResourceType.ARTIFACT.value,
                    filename=artifact.filename,
                    mime_type=artifact.mime_type,
                    storage_key=storage_key,
                    byte_size=len(artifact.content),
                    metadata_json=None,
                    created_at=now,
                )
                session.commit()
                stored_records.append(record)
        return stored_records

    async def _finalize_delivery(
        self,
        *,
        task_id: str,
        revision_id: str,
        runtime: DeliveryRuntime,
        final_markdown: str,
    ) -> bool:
        with self._session_factory() as session:
            image_artifacts = self._task_service.repository.list_artifacts(
                session=session,
                revision_id=revision_id,
                resource_type=AccessTokenResourceType.ARTIFACT.value,
            )
        generated_artifacts_list: list[GeneratedArtifact] = []
        for artifact in image_artifacts:
            generated_artifacts_list.append(
                GeneratedArtifact(
                    filename=artifact.filename,
                    mime_type=artifact.mime_type,
                    content=await self._artifact_store.get(artifact.storage_key),
                )
            )
        generated_artifacts = tuple(generated_artifacts_list)

        try:
            markdown_zip_bytes = await self._invoke_operation(
                lambda: self._report_export_service.build_markdown_zip(
                    markdown=final_markdown,
                    artifacts=generated_artifacts,
                )
            )
            pdf_bytes = await self._invoke_operation(
                lambda: self._report_export_service.build_pdf(markdown=final_markdown)
            )
        except RetryableOperationError:
            await self._fail_task(
                task_id=task_id,
                error_code="upstream_service_error",
                message="报告导出失败且重试耗尽。",
            )
            await self._destroy_sandbox(runtime=runtime)
            return False

        now = self._clock()
        word_count = len([token for token in final_markdown.replace("\n", " ").split(" ") if token.strip()])
        for resource_type, filename, mime_type, content in (
            (
                AccessTokenResourceType.MARKDOWN_DOWNLOAD,
                "mimir-report.zip",
                "application/zip",
                markdown_zip_bytes,
            ),
            (
                AccessTokenResourceType.PDF_DOWNLOAD,
                "mimir-report.pdf",
                "application/pdf",
                pdf_bytes,
            ),
        ):
            storage_key = f"tasks/{task_id}/{revision_id}/downloads/{filename}"
            try:
                await self._invoke_operation(
                    lambda storage_key=storage_key, content=content, mime_type=mime_type: self._artifact_store.put(
                        storage_key,
                        content,
                        mime_type,
                    )
                )
            except RetryableOperationError:
                await self._fail_task(
                    task_id=task_id,
                    error_code="upstream_service_error",
                    message="报告导出文件上传失败且重试耗尽。",
                )
                await self._destroy_sandbox(runtime=runtime)
                return False

            with self._session_factory() as session:
                self._task_service.repository.append_artifact(
                    session=session,
                    artifact_id=generate_id("art"),
                    task_id=task_id,
                    revision_id=revision_id,
                    resource_type=resource_type.value,
                    filename=filename,
                    mime_type=mime_type,
                    storage_key=storage_key,
                    byte_size=len(content),
                    metadata_json={"word_count": word_count},
                    created_at=now,
                )
                session.commit()

        try:
            await self._destroy_sandbox(runtime=runtime)
        except RetryableOperationError:
            await self._fail_task(
                task_id=task_id,
                error_code="upstream_service_error",
                message="sandbox 销毁失败且重试耗尽。",
            )
            return False

        with self._session_factory() as session:
            self._task_service.complete_delivery(
                session,
                task_id=task_id,
            )
            session.commit()
        return True

    async def _record_tool_call(
        self,
        *,
        task_id: str,
        revision_id: str,
        tool_call: WriterToolCall,
        status: str,
        error_code: str | None,
        response_json: dict[str, object] | None,
    ) -> None:
        with self._session_factory() as session:
            self._task_service.repository.append_tool_call(
                session=session,
                task_id=task_id,
                revision_id=revision_id,
                subtask_id=None,
                tool_call_id=tool_call.tool_call_id,
                tool_name=tool_call.tool_name,
                status=status,
                error_code=error_code,
                request_json={"code": tool_call.code},
                response_json=response_json,
                created_at=self._clock(),
            )
            session.commit()

    async def _ensure_sandbox(self, *, runtime: DeliveryRuntime) -> str:
        if runtime.sandbox_id is None:
            runtime.sandbox_id = await self._invoke_operation(self._sandbox_client.create)
        return runtime.sandbox_id

    async def _destroy_sandbox(self, *, runtime: DeliveryRuntime) -> None:
        if runtime.sandbox_id is None:
            return
        sandbox_id = runtime.sandbox_id
        runtime.sandbox_id = None
        await self._invoke_operation(lambda: self._sandbox_client.destroy(sandbox_id))

    async def _append_event(
        self,
        *,
        task_id: str,
        event: str,
        payload: dict[str, object],
    ) -> None:
        with self._session_factory() as session:
            appended = self._task_service.append_task_event(
                session,
                task_id=task_id,
                event=event,
                payload=payload,
            )
            if appended is None:
                session.rollback()
                return
            session.commit()

    async def _transition_phase(self, *, task_id: str, target_phase: TaskPhase) -> None:
        with self._session_factory() as session:
            self._task_service.transition_phase(
                session,
                task_id=task_id,
                target_phase=target_phase,
            )
            session.commit()

    async def _fail_task(self, *, task_id: str, error_code: str, message: str) -> None:
        with self._session_factory() as session:
            self._task_service.fail_task(
                session,
                task_id=task_id,
                error_code=error_code,
                message=message,
            )
            session.commit()

    async def _is_terminal(self, *, task_id: str) -> bool:
        with self._session_factory() as session:
            task = self._task_service.repository.get_task(session=session, task_id=task_id)
            if task is None:
                return True
            return TaskStatus(task.status) in {
                TaskStatus.TERMINATED,
                TaskStatus.FAILED,
                TaskStatus.EXPIRED,
                TaskStatus.PURGED,
            }

    async def _invoke_operation(self, operation: Callable[[], Awaitable[object]]) -> object:
        return await self._operation_invoker.invoke(operation)


def _outline_to_payload(outline: ResearchOutline) -> dict[str, object]:
    return {
        "title": outline.title,
        "sections": [
            {
                "section_id": section.section_id,
                "title": section.title,
                "description": section.description,
                "order": section.order,
            }
            for section in outline.sections
        ],
        "entities": list(outline.entities),
    }
