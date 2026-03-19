import asyncio
import logging
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Awaitable

from sqlalchemy.orm import Session, sessionmaker

logger = logging.getLogger(__name__)

from app.api.errors import ApiError
from app.application.dto.clarification import (
    ClarificationAcceptedResponse,
    ClarificationQuestionSet,
    ClarificationSubmission,
    NaturalClarificationSubmission,
    OptionsClarificationSubmission,
)
from app.application.dto.invocation import LLMInvocation
from app.application.invocation_contracts import build_stage_profile
from app.application.parsers.clarification import (
    ClarificationOptionsParseError,
    ClarificationOptionsParser,
)
from app.application.parsers.requirement import (
    RequirementDetailParseError,
    RequirementDetailParser,
)
from app.application.ports.llm import ClarificationGenerator, RequirementAnalyzer
from app.application.prompts.clarification import (
    build_natural_clarification_prompt,
    build_options_clarification_prompt,
)
from app.application.prompts.requirement import build_requirement_analysis_prompt
from app.application.services.llm import RetryingLLMInvoker
from app.application.services.llm import RetryableLLMError
from app.application.services.tasks import TaskService
from app.application.services.invocation import RiskControlTriggered
from app.domain.enums import ClarificationMode, TaskPhase, TaskStatus


@dataclass(frozen=True, slots=True)
class ClarificationAnswerSet:
    natural_answer: str | None
    selected_options: list[dict[str, str]]
    submitted_by_timeout: bool


@dataclass(frozen=True, slots=True)
class AnalysisInput:
    initial_query: str
    clarification_mode: str
    clarification_output: str
    clarification_answer_set: ClarificationAnswerSet

    def clarification_answer_text(self) -> str:
        if self.clarification_answer_set.natural_answer is not None:
            return self.clarification_answer_set.natural_answer
        selected_labels = [
            item["selected_label"]
            for item in self.clarification_answer_set.selected_options
            if item["selected_label"] != "自动"
        ]
        return "\n".join(selected_labels) if selected_labels else ""


@dataclass(slots=True)
class ClarificationRuntime:
    ready_question_set: ClarificationQuestionSet | None = None
    timeout_at: datetime | None = None
    clarification_output: str | None = None
    initial_task: asyncio.Task[None] | None = None
    analysis_task: asyncio.Task[None] | None = None


class ClarificationOrchestrator:
    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session],
        task_service: TaskService,
        clarification_generator: ClarificationGenerator,
        requirement_analyzer: RequirementAnalyzer,
        llm_invoker: RetryingLLMInvoker,
        settings,
        on_requirement_completed: Callable[[str], Awaitable[None]] | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._task_service = task_service
        self._clarification_generator = clarification_generator
        self._requirement_analyzer = requirement_analyzer
        self._llm_invoker = llm_invoker
        self._settings = settings
        self._on_requirement_completed = on_requirement_completed
        self._clock = clock or (lambda: datetime.now(UTC))
        self._runtimes: dict[str, ClarificationRuntime] = {}

    async def ensure_started(self, *, task_id: str) -> None:
        runtime = self._runtimes.setdefault(task_id, ClarificationRuntime())
        if runtime.initial_task is not None and not runtime.initial_task.done():
            return
        runtime.initial_task = asyncio.create_task(
            self._run_initial_clarification(task_id=task_id)
        )

    async def submit(
        self,
        *,
        task_id: str,
        token: str,
        payload: ClarificationSubmission,
    ) -> tuple[str, ClarificationAcceptedResponse]:
        runtime = self._runtimes.setdefault(task_id, ClarificationRuntime())

        with self._session_factory() as session:
            task = self._task_service.get_task_for_token(
                session,
                task_id=task_id,
                token=token,
            )
            task_mode = ClarificationMode(task.clarification_mode)
            payload_mode = ClarificationMode(payload.mode)
            if task_mode is not payload_mode:
                raise ApiError(
                    status_code=409,
                    code="invalid_task_state",
                    message="当前任务状态不允许提交该类型的澄清。",
                    trace_id=task.trace_id,
                )

            if isinstance(payload, NaturalClarificationSubmission):
                answer_set = ClarificationAnswerSet(
                    natural_answer=payload.answer_text,
                    selected_options=[],
                    submitted_by_timeout=False,
                )
            elif isinstance(payload, OptionsClarificationSubmission):
                if runtime.ready_question_set is None:
                    raise ApiError(
                        status_code=409,
                        code="invalid_task_state",
                        message="当前任务状态不允许提交澄清。",
                        trace_id=task.trace_id,
                    )
                answer_set = ClarificationAnswerSet(
                    natural_answer=None,
                    selected_options=self._resolve_option_answers(
                        runtime.ready_question_set,
                        payload.answers,
                    ),
                    submitted_by_timeout=payload.submitted_by_timeout,
                )
            else:
                raise ApiError(
                    status_code=422,
                    code="validation_error",
                    message="请求参数不合法。",
                    trace_id=task.trace_id,
                )

            snapshot = self._task_service.begin_requirement_analysis(
                session,
                task_id=task_id,
                task=task,
            )
            session.commit()

        runtime.timeout_at = None
        runtime.ready_question_set = None
        if runtime.analysis_task is not None and not runtime.analysis_task.done():
            runtime.analysis_task.cancel()
            with suppress(asyncio.CancelledError):
                await runtime.analysis_task
        runtime.analysis_task = asyncio.create_task(
            self._run_requirement_analysis(
                task_id=task_id,
                analysis_input=AnalysisInput(
                    initial_query=task.initial_query,
                    clarification_mode=payload.mode,
                    clarification_output=runtime.clarification_output or "",
                    clarification_answer_set=answer_set,
                ),
            )
        )
        return task.trace_id, ClarificationAcceptedResponse(
            accepted=True,
            snapshot=snapshot,
        )

    async def maybe_auto_submit(self, *, task_id: str) -> None:
        runtime = self._runtimes.get(task_id)
        if (
            runtime is None
            or runtime.timeout_at is None
            or runtime.ready_question_set is None
            or self._clock() < runtime.timeout_at
        ):
            return

        with self._session_factory() as session:
            task = self._task_service.repository.get_task(session=session, task_id=task_id)
            if task is None:
                runtime.timeout_at = None
                runtime.ready_question_set = None
                return
            if TaskStatus(task.status) is not TaskStatus.AWAITING_USER_INPUT:
                runtime.timeout_at = None
                runtime.ready_question_set = None
                return
            if TaskPhase(task.phase) is not TaskPhase.CLARIFYING:
                runtime.timeout_at = None
                runtime.ready_question_set = None
                return

            answer_set = ClarificationAnswerSet(
                natural_answer=None,
                selected_options=[
                    {
                        "question": question.question,
                        "selected_label": "自动",
                    }
                    for question in runtime.ready_question_set.questions
                ],
                submitted_by_timeout=True,
            )
            snapshot = self._task_service.begin_requirement_analysis(
                session,
                task_id=task_id,
                task=task,
            )
            session.commit()

        runtime.timeout_at = None
        runtime.ready_question_set = None
        runtime.analysis_task = asyncio.create_task(
            self._run_requirement_analysis(
                task_id=task_id,
                analysis_input=AnalysisInput(
                    initial_query=task.initial_query,
                    clarification_mode=ClarificationMode.OPTIONS.value,
                    clarification_output=runtime.clarification_output or "",
                    clarification_answer_set=answer_set,
                ),
            )
        )

    async def cancel(self, *, task_id: str) -> None:
        runtime = self._runtimes.pop(task_id, None)
        if runtime is None:
            return

        for task in (runtime.initial_task, runtime.analysis_task):
            if task is None:
                continue
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

    async def shutdown(self) -> None:
        for task_id in list(self._runtimes):
            await self.cancel(task_id=task_id)

    async def _run_initial_clarification(self, *, task_id: str) -> None:
        with self._session_factory() as session:
            task = self._task_service.repository.get_task(session=session, task_id=task_id)
            if task is None:
                return
            if TaskStatus(task.status) is not TaskStatus.RUNNING:
                return
            if TaskPhase(task.phase) is not TaskPhase.CLARIFYING:
                return

            mode = ClarificationMode(task.clarification_mode)
            initial_query = task.initial_query

        if mode is ClarificationMode.NATURAL:
            await self._run_natural_clarification(
                task_id=task_id,
                initial_query=initial_query,
            )
            return

        await self._run_options_clarification(
            task_id=task_id,
            initial_query=initial_query,
        )

    async def _run_natural_clarification(
        self,
        *,
        task_id: str,
        initial_query: str,
    ) -> None:
        prompt = build_natural_clarification_prompt(
            initial_query=initial_query,
            now=self._clock(),
        )
        invocation = LLMInvocation(
            profile=build_stage_profile(
                settings=self._settings,
                stage="clarification_natural",
            ),
            prompt_bundle=prompt,
        )
        logger.info("natural clarification starting", extra={"task_id": task_id})
        try:
            generation = await self._llm_invoker.invoke(
                lambda: self._clarification_generator.generate_natural(invocation)
            )
        except RiskControlTriggered:
            logger.error("clarification risk control triggered", extra={"task_id": task_id, "error_code": "risk_control_triggered"}, exc_info=True)
            await self._fail_task(
                task_id=task_id,
                error_code="risk_control_triggered",
                message="澄清阶段触发风控。",
            )
            return
        except RetryableLLMError:
            logger.error("clarification upstream error after retries", extra={"task_id": task_id, "error_code": "upstream_service_error"}, exc_info=True)
            await self._fail_task(
                task_id=task_id,
                error_code="upstream_service_error",
                message="澄清生成失败且重试耗尽。",
            )
            return
        logger.info("natural clarification completed", extra={"task_id": task_id})
        await self._emit_deltas(task_id=task_id, event="clarification.delta", deltas=generation.deltas)

        runtime = self._runtimes.setdefault(task_id, ClarificationRuntime())
        runtime.clarification_output = generation.full_text

        with self._session_factory() as session:
            snapshot = self._task_service.enter_awaiting_user_input(
                session,
                task_id=task_id,
            )
            self._task_service.append_task_event(
                session,
                task_id=task_id,
                event="clarification.natural.ready",
                payload={
                    "status": snapshot.status.value,
                    "available_actions": [
                        action.value for action in snapshot.available_actions
                    ],
                },
            )
            session.commit()

    async def _run_options_clarification(
        self,
        *,
        task_id: str,
        initial_query: str,
    ) -> None:
        prompt = build_options_clarification_prompt(
            initial_query=initial_query,
            now=self._clock(),
        )
        invocation = LLMInvocation(
            profile=build_stage_profile(
                settings=self._settings,
                stage="clarification_options",
            ),
            prompt_bundle=prompt,
        )
        logger.info("options clarification starting", extra={"task_id": task_id})
        try:
            generation = await self._llm_invoker.invoke(
                lambda: self._clarification_generator.generate_options(invocation)
            )
        except RiskControlTriggered:
            logger.error("clarification risk control triggered", extra={"task_id": task_id, "error_code": "risk_control_triggered"}, exc_info=True)
            await self._fail_task(
                task_id=task_id,
                error_code="risk_control_triggered",
                message="澄清阶段触发风控。",
            )
            return
        except RetryableLLMError:
            logger.error("clarification upstream error after retries", extra={"task_id": task_id, "error_code": "upstream_service_error"}, exc_info=True)
            await self._fail_task(
                task_id=task_id,
                error_code="upstream_service_error",
                message="澄清生成失败且重试耗尽。",
            )
            return
        logger.info("options clarification completed", extra={"task_id": task_id})
        await self._emit_deltas(task_id=task_id, event="clarification.delta", deltas=generation.deltas)

        parser = ClarificationOptionsParser()
        try:
            question_set = parser.parse(generation.full_text)
        except ClarificationOptionsParseError:
            with self._session_factory() as session:
                self._task_service.update_clarification_mode(
                    session,
                    task_id=task_id,
                    clarification_mode=ClarificationMode.NATURAL,
                )
                self._task_service.append_task_event(
                    session,
                    task_id=task_id,
                    event="clarification.fallback_to_natural",
                    payload={"reason": "parse_failed"},
                )
                session.commit()
            await self._run_natural_clarification(
                task_id=task_id,
                initial_query=initial_query,
            )
            return

        runtime = self._runtimes.setdefault(task_id, ClarificationRuntime())
        runtime.clarification_output = generation.full_text
        runtime.ready_question_set = question_set
        runtime.timeout_at = self._clock() + timedelta(
            seconds=self._settings.clarification_backend_timeout_seconds
        )

        with self._session_factory() as session:
            snapshot = self._task_service.enter_awaiting_user_input(
                session,
                task_id=task_id,
            )
            now = self._clock()
            self._task_service.append_task_event(
                session,
                task_id=task_id,
                event="clarification.options.ready",
                payload={
                    "status": snapshot.status.value,
                    "available_actions": [
                        action.value for action in snapshot.available_actions
                    ],
                    "question_set": question_set.model_dump(mode="json"),
                },
            )
            self._task_service.append_task_event(
                session,
                task_id=task_id,
                event="clarification.countdown.started",
                payload={
                    "duration_seconds": self._settings.clarification_countdown_seconds,
                    "started_at": now.isoformat().replace("+00:00", "Z"),
                },
            )
            session.commit()

    async def _run_requirement_analysis(
        self,
        *,
        task_id: str,
        analysis_input: AnalysisInput,
    ) -> None:
        prompt = build_requirement_analysis_prompt(
            analysis_input=analysis_input,
            now=self._clock(),
        )
        invocation = LLMInvocation(
            profile=build_stage_profile(
                settings=self._settings,
                stage="requirement_analysis",
            ),
            prompt_bundle=prompt,
        )
        logger.info("requirement analysis starting", extra={"task_id": task_id})
        try:
            generation = await self._llm_invoker.invoke(
                lambda: self._requirement_analyzer.analyze(invocation)
            )
        except RiskControlTriggered:
            logger.error("requirement analysis risk control triggered", extra={"task_id": task_id, "error_code": "risk_control_triggered"}, exc_info=True)
            await self._fail_task(
                task_id=task_id,
                error_code="risk_control_triggered",
                message="需求分析阶段触发风控。",
            )
            return
        except RetryableLLMError:
            logger.error("requirement analysis upstream error after retries", extra={"task_id": task_id, "error_code": "upstream_service_error"}, exc_info=True)
            await self._fail_task(
                task_id=task_id,
                error_code="upstream_service_error",
                message="需求分析调用失败且重试耗尽。",
            )
            return
        logger.info("requirement analysis completed", extra={"task_id": task_id})
        await self._emit_deltas(task_id=task_id, event="analysis.delta", deltas=generation.deltas)

        parser = RequirementDetailParser()
        try:
            detail = parser.parse(generation.full_text)
        except RequirementDetailParseError:
            await self._fail_task(
                task_id=task_id,
                error_code="requirement_parse_failed",
                message="需求分析结果解析失败。",
            )
            return

        with self._session_factory() as session:
            self._task_service.complete_requirement_analysis(
                session,
                task_id=task_id,
                detail=detail,
            )
            session.commit()
        if self._on_requirement_completed is not None:
            await self._on_requirement_completed(task_id)

    async def _emit_deltas(
        self,
        *,
        task_id: str,
        event: str,
        deltas: tuple[str, ...],
    ) -> None:
        for delta in deltas:
            with self._session_factory() as session:
                appended = self._task_service.append_task_event(
                    session,
                    task_id=task_id,
                    event=event,
                    payload={"delta": delta},
                )
                if appended is None:
                    session.rollback()
                    return
                session.commit()

    def _resolve_option_answers(
        self,
        question_set: ClarificationQuestionSet,
        answers,
    ) -> list[dict[str, str]]:
        question_map = {question.question_id: question for question in question_set.questions}
        resolved: list[dict[str, str]] = []
        for answer in answers:
            question = question_map.get(answer.question_id)
            if question is None:
                raise ApiError(
                    status_code=422,
                    code="validation_error",
                    message="请求参数不合法。",
                    detail={"field": "answers.question_id"},
                )
            option = next(
                (
                    item
                    for item in question.options
                    if item.option_id == answer.selected_option_id
                ),
                None,
            )
            if option is None:
                raise ApiError(
                    status_code=422,
                    code="validation_error",
                    message="请求参数不合法。",
                    detail={"field": "answers.selected_option_id"},
                )
            resolved.append(
                {
                    "question": question.question,
                    "selected_label": answer.selected_label or option.label,
                }
            )
        return resolved

    async def _fail_task(
        self,
        *,
        task_id: str,
        error_code: str,
        message: str,
    ) -> None:
        logger.error(
            "clarification task failed: %s",
            message,
            extra={"task_id": task_id, "error_code": error_code},
        )
        with self._session_factory() as session:
            self._task_service.fail_task(
                session,
                task_id=task_id,
                error_code=error_code,
                message=message,
            )
            session.commit()
