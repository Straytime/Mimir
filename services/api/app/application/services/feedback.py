import asyncio
from collections.abc import Awaitable, Callable
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session, sessionmaker

from app.application.dto.feedback import (
    FeedbackAcceptedResponse,
    FeedbackAnalysisInput,
    FeedbackSubmission,
)
from app.application.parsers.requirement import (
    RequirementDetailParseError,
    RequirementDetailParser,
)
from app.application.ports.llm import FeedbackAnalyzer
from app.application.prompts.feedback import build_feedback_analysis_prompt
from app.application.services.llm import RetryingLLMInvoker
from app.application.services.tasks import TaskService
from app.domain.enums import TaskPhase, TaskStatus
from app.domain.schemas import RequirementDetail


@dataclass(slots=True)
class FeedbackRuntime:
    analysis_task: asyncio.Task[None] | None = None


class FeedbackOrchestrator:
    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session],
        task_service: TaskService,
        feedback_analyzer: FeedbackAnalyzer,
        llm_invoker: RetryingLLMInvoker,
        on_feedback_completed: Callable[[str], Awaitable[None]] | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._task_service = task_service
        self._feedback_analyzer = feedback_analyzer
        self._llm_invoker = llm_invoker
        self._on_feedback_completed = on_feedback_completed
        self._clock = clock or (lambda: datetime.now(UTC))
        self._runtimes: dict[str, FeedbackRuntime] = {}

    async def submit(
        self,
        *,
        task_id: str,
        token: str,
        payload: FeedbackSubmission,
    ) -> tuple[str, FeedbackAcceptedResponse]:
        runtime = self._runtimes.setdefault(task_id, FeedbackRuntime())
        with self._session_factory() as session:
            task_with_revision = self._task_service.repository.get_task_with_revision(
                session=session,
                task_id=task_id,
            )
            if task_with_revision is None:
                raise self._task_not_found()

            task, revision = task_with_revision
            self._task_service.get_task_for_token(
                session,
                task_id=task_id,
                token=token,
            )
            if revision.requirement_detail_json is None:
                raise self._invalid_state(trace_id=task.trace_id)

            previous_detail = RequirementDetail.model_validate(
                revision.requirement_detail_json
            )
            response = self._task_service.begin_feedback_processing(
                session,
                task=task,
                revision=revision,
                feedback_text=payload.feedback_text,
            )
            session.commit()

        if runtime.analysis_task is not None and not runtime.analysis_task.done():
            runtime.analysis_task.cancel()
            with suppress(asyncio.CancelledError):
                await runtime.analysis_task

        runtime.analysis_task = asyncio.create_task(
            self._run_feedback_analysis(
                task_id=task_id,
                revision_id=response.revision_id,
                analysis_input=FeedbackAnalysisInput(
                    initial_query=task.initial_query,
                    previous_requirement_detail=previous_detail,
                    feedback_text=payload.feedback_text,
                ),
                client_timezone=task.client_timezone,
                client_locale=task.client_locale,
            )
        )
        return task.trace_id, response

    async def cancel(self, *, task_id: str) -> None:
        runtime = self._runtimes.pop(task_id, None)
        if runtime is None or runtime.analysis_task is None:
            return
        runtime.analysis_task.cancel()
        with suppress(asyncio.CancelledError):
            await runtime.analysis_task

    async def shutdown(self) -> None:
        for task_id in list(self._runtimes):
            await self.cancel(task_id=task_id)

    async def _run_feedback_analysis(
        self,
        *,
        task_id: str,
        revision_id: str,
        analysis_input: FeedbackAnalysisInput,
        client_timezone: str,
        client_locale: str,
    ) -> None:
        prompt = build_feedback_analysis_prompt(
            analysis_input=analysis_input,
            client_timezone=client_timezone,
            client_locale=client_locale,
            now=self._clock(),
        )
        generation = await self._llm_invoker.invoke(
            lambda: self._feedback_analyzer.analyze(prompt)
        )
        await self._emit_deltas(task_id=task_id, revision_id=revision_id, deltas=generation.deltas)

        parser = RequirementDetailParser()
        try:
            detail = parser.parse(generation.full_text)
        except RequirementDetailParseError:
            await self._fail_task(
                task_id=task_id,
                error_code="upstream_service_error",
                message="feedback analyzer 返回了无效的 RequirementDetail。",
            )
            return

        now = self._clock()
        with self._session_factory() as session:
            task_with_revision = self._task_service.repository.get_task_with_revision(
                session=session,
                task_id=task_id,
            )
            if task_with_revision is None:
                return
            task, revision = task_with_revision
            if (
                revision.revision_id != revision_id
                or TaskStatus(task.status) is not TaskStatus.RUNNING
                or TaskPhase(task.phase) is not TaskPhase.PROCESSING_FEEDBACK
            ):
                return

            self._task_service.repository.append_agent_run(
                session=session,
                task_id=task_id,
                revision_id=revision_id,
                subtask_id=None,
                agent_type="feedback_analyzer",
                prompt_name="feedback_analysis_round",
                status="completed",
                reasoning_text="\n".join(generation.deltas),
                content_text=generation.full_text,
                finish_reason="analysis_completed",
                tool_calls_json=None,
                created_at=now,
                updated_at=now,
            )
            self._task_service.complete_feedback_processing(
                session,
                task_id=task_id,
                revision_id=revision_id,
                detail=detail,
            )
            session.commit()

        if self._on_feedback_completed is not None:
            await self._on_feedback_completed(task_id)

    async def _emit_deltas(
        self,
        *,
        task_id: str,
        revision_id: str,
        deltas: tuple[str, ...],
    ) -> None:
        for delta in deltas:
            with self._session_factory() as session:
                task = self._task_service.repository.get_task(
                    session=session,
                    task_id=task_id,
                )
                if task is None:
                    return
                self._task_service.repository.append_event(
                    session=session,
                    task_id=task_id,
                    revision_id=revision_id,
                    event="analysis.delta",
                    phase=TaskPhase.PROCESSING_FEEDBACK.value,
                    payload={"delta": delta},
                    created_at=self._clock(),
                )
                session.commit()

    async def _fail_task(
        self,
        *,
        task_id: str,
        error_code: str,
        message: str,
    ) -> None:
        with self._session_factory() as session:
            self._task_service.fail_task(
                session,
                task_id=task_id,
                error_code=error_code,
                message=message,
            )
            session.commit()

    @staticmethod
    def _task_not_found() -> Exception:
        from app.api.errors import ApiError

        return ApiError(
            status_code=404,
            code="task_not_found",
            message="任务不存在或已清理。",
        )

    @staticmethod
    def _invalid_state(*, trace_id: str) -> Exception:
        from app.api.errors import ApiError

        return ApiError(
            status_code=409,
            code="invalid_task_state",
            message="当前任务状态不允许提交反馈。",
            trace_id=trace_id,
        )
