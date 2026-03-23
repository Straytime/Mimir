import asyncio
import contextlib
import json
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

logger = logging.getLogger(__name__)

from app.application.dto.invocation import PromptBundle, PromptMessage, dump_prompt_bundle
from app.application.dto.research import (
    CollectResult,
    CollectedSourceItem,
    CollectorDecision,
    CollectorInvocation,
    CollectorToolCall,
    PlannerInvocation,
    SummaryInvocation,
)
from app.application.invocation_contracts import (
    build_collect_agent_tool_schema,
    build_stage_profile,
    build_web_fetch_tool_schema,
    build_web_search_tool_schema,
)
from app.application.ports.research import (
    CollectorAgent,
    PlannerAgent,
    SummaryAgent,
    WebFetchClient,
    WebSearchClient,
)
from app.application.prompts.collection import (
    build_collector_prompt,
    build_planner_prompt,
    build_summary_prompt,
)
from app.application.services.invocation import (
    RetryableOperationError,
    RetryingOperationInvoker,
    RiskControlTriggered,
)
from app.application.services.merge import SourceMergeService
from app.application.services.tasks import TaskService
from app.core.config import Settings
from app.core.ids import generate_id
from app.domain.enums import CollectSummaryStatus, TaskPhase, TaskStatus
from app.domain.schemas import CollectPlan, CollectSummary, RequirementDetail
from app.infrastructure.db.models import AgentRunRecord


@dataclass(slots=True)
class CollectionRuntime:
    loop_task: asyncio.Task[None] | None = None
    risk_blocked_count: int = 0
    cancelled: bool = False


class CollectionOrchestrator:
    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session],
        task_service: TaskService,
        planner_agent: PlannerAgent,
        collector_agent: CollectorAgent,
        summary_agent: SummaryAgent,
        web_search_client: WebSearchClient,
        web_fetch_client: WebFetchClient,
        operation_invoker: RetryingOperationInvoker[object],
        merge_service: SourceMergeService,
        settings: Settings,
        on_sources_merged: Callable[[str], Awaitable[None]] | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._task_service = task_service
        self._planner_agent = planner_agent
        self._collector_agent = collector_agent
        self._summary_agent = summary_agent
        self._web_search_client = web_search_client
        self._web_fetch_client = web_fetch_client
        self._operation_invoker = operation_invoker
        self._merge_service = merge_service
        self._settings = settings
        self._on_sources_merged = on_sources_merged
        self._clock = clock or (lambda: datetime.now(UTC))
        self._runtimes: dict[str, CollectionRuntime] = {}

    async def ensure_started(self, *, task_id: str) -> None:
        runtime = self._runtimes.setdefault(task_id, CollectionRuntime())
        if runtime.loop_task is not None and not runtime.loop_task.done():
            return
        runtime.loop_task = asyncio.create_task(self._run_collection_loop(task_id=task_id))

    async def cancel(self, *, task_id: str) -> None:
        runtime = self._runtimes.pop(task_id, None)
        if runtime is None:
            return
        runtime.cancelled = True
        if runtime.loop_task is None:
            return
        runtime.loop_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await runtime.loop_task

    async def shutdown(self) -> None:
        for task_id in list(self._runtimes):
            await self.cancel(task_id=task_id)

    async def _run_collection_loop(self, *, task_id: str) -> None:
        try:
            await self._run_collection_loop_inner(task_id=task_id)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.critical(
                "unhandled exception in collection loop",
                extra={"task_id": task_id},
                exc_info=True,
            )

    async def _run_collection_loop_inner(self, *, task_id: str) -> None:
        summaries: list[CollectSummary] = []
        planner_call_index = 1
        runtime = self._runtimes.setdefault(task_id, CollectionRuntime())

        while not runtime.cancelled:
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

            if task.phase == TaskPhase.ANALYZING_REQUIREMENT.value:
                await self._transition_phase(
                    task_id=task_id,
                    target_phase=TaskPhase.PLANNING_COLLECTION,
                )

            planner_decision = await self._run_planner_round(
                task_id=task_id,
                requirement_detail=requirement_detail,
                revision_id=revision.revision_id,
                summaries=tuple(summaries),
                collect_agent_calls_used=revision.collect_agent_calls_used,
                call_index=planner_call_index,
            )
            if planner_decision is None:
                return

            if planner_decision.stop:
                await self._transition_phase(
                    task_id=task_id,
                    target_phase=TaskPhase.MERGING_SOURCES,
                )
                await self._run_merge(task_id=task_id, revision_id=revision.revision_id)
                if self._on_sources_merged is not None:
                    await self._on_sources_merged(task_id)
                return

            if not planner_decision.plans:
                if summaries:
                    # Non-first round with existing data: treat as implicit stop
                    logger.info(
                        "planner returned empty plans with existing data, skipping to merge",
                        extra={"task_id": task_id},
                    )
                    await self._transition_phase(
                        task_id=task_id,
                        target_phase=TaskPhase.MERGING_SOURCES,
                    )
                    await self._run_merge(task_id=task_id, revision_id=revision.revision_id)
                    if self._on_sources_merged is not None:
                        await self._on_sources_merged(task_id)
                    return
                await self._fail_task(
                    task_id=task_id,
                    error_code="planner_invalid_output",
                    message="planner 未返回有效 CollectPlan。",
                )
                return

            if len(planner_decision.plans) > self._settings.planner_parallel_limit:
                await self._fail_task(
                    task_id=task_id,
                    error_code="planner_parallel_limit_exceeded",
                    message="planner 超出单轮 CollectPlan 并发上限。",
                )
                return

            reserved = self._reserve_collect_agent_calls(
                revision_id=revision.revision_id,
                additional_calls=len(planner_decision.plans),
            )
            if not reserved:
                # PRD func_7: 达到调用次数上限 → 进入搜集结果汇总
                logger.info(
                    "collect_agent limit reached, skipping to merge",
                    extra={"task_id": task_id},
                )
                await self._transition_phase(
                    task_id=task_id,
                    target_phase=TaskPhase.MERGING_SOURCES,
                )
                await self._run_merge(task_id=task_id, revision_id=revision.revision_id)
                if self._on_sources_merged is not None:
                    await self._on_sources_merged(task_id)
                return

            await self._transition_phase(task_id=task_id, target_phase=TaskPhase.COLLECTING)
            collect_results = await asyncio.gather(
                *[
                    self._run_collect_subtask(
                        task_id=task_id,
                        revision_id=revision.revision_id,
                        plan=plan.model_copy(update={"revision_id": revision.revision_id}),
                        subtask_id=generate_id("sub"),
                    )
                    for plan in planner_decision.plans
                ]
            )

            if await self._is_terminal(task_id=task_id):
                return

            await self._transition_phase(
                task_id=task_id,
                target_phase=TaskPhase.SUMMARIZING_COLLECTION,
            )
            round_summaries = await self._run_summary_round(
                task_id=task_id,
                revision_id=revision.revision_id,
                plans=tuple(
                    plan.model_copy(update={"revision_id": revision.revision_id})
                    for plan in planner_decision.plans
                ),
                collect_results=tuple(collect_results),
                runtime=runtime,
            )

            if await self._is_terminal(task_id=task_id):
                return

            summaries.extend(round_summaries)
            await self._transition_phase(
                task_id=task_id,
                target_phase=TaskPhase.PLANNING_COLLECTION,
            )
            planner_call_index += 1

    async def _run_planner_round(
        self,
        *,
        task_id: str,
        requirement_detail: RequirementDetail,
        revision_id: str,
        summaries: tuple[CollectSummary, ...],
        collect_agent_calls_used: int,
        call_index: int,
    ):
        logger.info(
            "planner round starting",
            extra={"task_id": task_id, "call_index": call_index, "summaries_count": len(summaries)},
        )
        invocation = PlannerInvocation(
            prompt_name="planner_round",
            requirement_detail=requirement_detail,
            summaries=summaries,
            call_index=call_index,
            collect_agent_calls_used=collect_agent_calls_used,
            now=self._clock(),
            transcript=self._load_planner_history_transcript(
                task_id=task_id,
                revision_id=revision_id,
                summaries=summaries,
            ),
            profile=build_stage_profile(
                settings=self._settings,
                stage="planner",
            ),
            tool_schemas=(build_collect_agent_tool_schema(),),
        )
        prompt_bundle = build_planner_prompt(invocation=invocation)
        invocation = replace(invocation, prompt_bundle=prompt_bundle)
        try:
            decision = await self._invoke_operation(
                lambda: self._planner_agent.plan(invocation)
            )
        except RiskControlTriggered:
            logger.error(
                "planner risk control triggered",
                extra={"task_id": task_id, "error_code": "risk_control_triggered"},
                exc_info=True,
            )
            await self._fail_task(
                task_id=task_id,
                error_code="risk_control_triggered",
                message="planner 阶段触发风控。",
            )
            return None
        except RetryableOperationError:
            logger.error(
                "planner upstream error after retries",
                extra={"task_id": task_id, "error_code": "upstream_service_error"},
                exc_info=True,
            )
            await self._fail_task(
                task_id=task_id,
                error_code="upstream_service_error",
                message="planner 调用失败且重试耗尽。",
            )
            return None
        logger.info(
            "planner round completed",
            extra={"task_id": task_id, "stop": decision.stop, "plans_count": len(decision.plans)},
        )

        for delta in decision.reasoning_deltas:
            await self._append_event(
                task_id=task_id,
                event="planner.reasoning.delta",
                payload={"delta": delta},
            )

        now = self._clock()
        with self._session_factory() as session:
            self._task_service.repository.append_agent_run(
                session=session,
                task_id=task_id,
                revision_id=revision_id,
                subtask_id=None,
                agent_type="planner",
                prompt_name=invocation.prompt_name,
                status="stop" if decision.stop else "completed",
                reasoning_text="\n".join(decision.reasoning_deltas),
                content_text=json.dumps(
                    {
                        "stop": decision.stop,
                        "plans": [
                            plan.model_dump(mode="json")
                            for plan in decision.plans
                        ],
                        "prompt_bundle": dump_prompt_bundle(prompt_bundle),
                    },
                    ensure_ascii=False,
                ),
                finish_reason="stop" if decision.stop else "plans_generated",
                provider_finish_reason=decision.provider_finish_reason,
                provider_usage_json=decision.provider_usage,
                tool_calls_json={
                    "summary_messages": [
                        summary.model_dump(mode="json", exclude_none=True)
                        for summary in summaries
                    ]
                },
                created_at=now,
                updated_at=now,
            )
            session.commit()

        for plan in decision.plans:
            await self._append_event(
                task_id=task_id,
                event="planner.tool_call.requested",
                payload={
                    "tool_call_id": plan.tool_call_id,
                    "collect_target": plan.collect_target,
                    "additional_info": plan.additional_info,
                },
            )

        return decision

    async def _run_collect_subtask(
        self,
        *,
        task_id: str,
        revision_id: str,
        plan: CollectPlan,
        subtask_id: str,
    ) -> CollectResult:
        logger.info(
            "collector subtask starting",
            extra={
                "task_id": task_id,
                "subtask_id": subtask_id,
                "collect_target": plan.collect_target,
            },
        )

        call_index = 1
        transcript: list[PromptMessage] = []
        search_queries: list[str] = []
        collected_items: list[CollectedSourceItem] = []
        tool_call_count = 0
        partial = False

        while True:
            invocation = CollectorInvocation(
                prompt_name="collector_round",
                subtask_id=subtask_id,
                plan=plan,
                call_index=call_index,
                tool_call_limit=self._settings.subtask_tool_call_limit,
                now=self._clock(),
                transcript=tuple(transcript),
                profile=build_stage_profile(
                    settings=self._settings,
                    stage="collector",
                ),
                tool_schemas=(
                    build_web_search_tool_schema(),
                    build_web_fetch_tool_schema(),
                ),
            )
            prompt_bundle = build_collector_prompt(invocation=invocation)
            invocation = replace(invocation, prompt_bundle=prompt_bundle)
            try:
                decision = await self._invoke_operation(
                    lambda: self._collector_agent.plan(invocation)
                )
            except RiskControlTriggered:
                logger.error(
                    "collector risk control triggered",
                    extra={
                        "task_id": task_id,
                        "subtask_id": subtask_id,
                        "error_code": "risk_control_triggered",
                    },
                    exc_info=True,
                )
                return await self._build_risk_blocked_collect_result(
                    task_id=task_id,
                    revision_id=revision_id,
                    subtask_id=subtask_id,
                    plan=plan,
                    prompt=prompt_bundle,
                    reasoning_text="collector 风控",
                )
            except RetryableOperationError:
                logger.error(
                    "collector upstream error after retries",
                    extra={
                        "task_id": task_id,
                        "subtask_id": subtask_id,
                        "error_code": "upstream_service_error",
                    },
                    exc_info=True,
                )
                await self._fail_task(
                    task_id=task_id,
                    error_code="upstream_service_error",
                    message="collector 调用失败且重试耗尽。",
                )
                return CollectResult(
                    subtask_id=subtask_id,
                    tool_call_id=plan.tool_call_id,
                    collect_target=plan.collect_target,
                    status=CollectSummaryStatus.PARTIAL,
                    search_queries=tuple(search_queries),
                    tool_call_count=tool_call_count,
                    items=tuple(),
                )

            if decision.reasoning_text.strip():
                await self._append_event(
                    task_id=task_id,
                    event="collector.reasoning.delta",
                    payload={
                        "subtask_id": subtask_id,
                        "tool_call_id": plan.tool_call_id,
                        "delta": decision.reasoning_text.strip(),
                    },
                )

            now = self._clock()
            with self._session_factory() as session:
                self._task_service.repository.append_agent_run(
                    session=session,
                    task_id=task_id,
                    revision_id=revision_id,
                    subtask_id=subtask_id,
                    agent_type="collector",
                    prompt_name=invocation.prompt_name,
                    status="stop" if decision.stop else "completed",
                    reasoning_text=decision.reasoning_text or None,
                    content_text=json.dumps(
                        {
                            "prompt_bundle": dump_prompt_bundle(prompt_bundle),
                            "content_text": decision.content_text,
                            "items": [
                                {
                                    "title": item.title,
                                    "link": item.link,
                                    "info": item.info,
                                }
                                for item in decision.items
                            ],
                        },
                        ensure_ascii=False,
                    ),
                    finish_reason="stop" if decision.stop else "tool_calls_requested",
                    provider_finish_reason=decision.provider_finish_reason,
                    provider_usage_json=decision.provider_usage,
                    tool_calls_json={
                        "tool_calls": [
                            {
                                "tool_call_id": tool_call.tool_call_id,
                                "tool_name": tool_call.tool_name,
                                "arguments_json": tool_call.arguments_json,
                            }
                            for tool_call in decision.tool_calls
                        ]
                    }
                    if decision.tool_calls
                    else None,
                    created_at=now,
                    updated_at=now,
                )
                session.commit()

            if decision.stop:
                final_items = decision.items or tuple(collected_items)
                status = (
                    CollectSummaryStatus.PARTIAL
                    if partial or not final_items
                    else CollectSummaryStatus.COMPLETED
                )
                result = CollectResult(
                    subtask_id=subtask_id,
                    tool_call_id=plan.tool_call_id,
                    collect_target=plan.collect_target,
                    status=status,
                    search_queries=tuple(search_queries),
                    tool_call_count=tool_call_count,
                    items=tuple(final_items),
                )
                await self._persist_collect_result(
                    task_id=task_id,
                    revision_id=revision_id,
                    result=result,
                )
                await self._append_event(
                    task_id=task_id,
                    event="collector.completed",
                    payload={
                        "subtask_id": subtask_id,
                        "tool_call_id": plan.tool_call_id,
                        "status": result.status.value,
                        "item_count": len(result.items),
                        "search_queries": list(result.search_queries),
                    },
                )
                return result

            if not decision.tool_calls:
                await self._fail_task(
                    task_id=task_id,
                    error_code="collector_invalid_output",
                    message="collector 未返回有效工具调用或最终结果。",
                )
                return CollectResult(
                    subtask_id=subtask_id,
                    tool_call_id=plan.tool_call_id,
                    collect_target=plan.collect_target,
                    status=CollectSummaryStatus.PARTIAL,
                    search_queries=tuple(search_queries),
                    tool_call_count=tool_call_count,
                    items=tuple(collected_items),
                )

            assistant_tool_calls = _collector_tool_call_payloads(decision.tool_calls)
            transcript.append(
                PromptMessage(
                    role="assistant",
                    content=decision.content_text,
                    tool_calls=assistant_tool_calls,
                    reasoning_content=decision.reasoning_text or None,
                )
            )

            tool_messages: list[PromptMessage] = []
            for tool_call in decision.tool_calls:
                if tool_call_count >= self._settings.subtask_tool_call_limit:
                    partial = True
                    break
                try:
                    tool_message, tool_payload, new_items = await self._execute_collector_tool_call(
                        task_id=task_id,
                        revision_id=revision_id,
                        subtask_id=subtask_id,
                        plan=plan,
                        tool_call=tool_call,
                    )
                except RiskControlTriggered:
                    return await self._build_risk_blocked_collect_result(
                        task_id=task_id,
                        revision_id=revision_id,
                        subtask_id=subtask_id,
                        plan=plan,
                        prompt=prompt_bundle,
                        reasoning_text=decision.reasoning_text,
                    )
                tool_messages.append(tool_message)
                if tool_call.tool_name == "web_search":
                    search_query = str(tool_call.arguments_json.get("search_query") or "")
                    if search_query:
                        search_queries.append(search_query)
                collected_items.extend(new_items)
                tool_call_count += 1
                if tool_payload.get("success") is False:
                    partial = True
                if tool_call_count >= self._settings.subtask_tool_call_limit:
                    partial = True
                    break

            transcript.extend(tool_messages)
            if partial and tool_call_count >= self._settings.subtask_tool_call_limit:
                result = CollectResult(
                    subtask_id=subtask_id,
                    tool_call_id=plan.tool_call_id,
                    collect_target=plan.collect_target,
                    status=CollectSummaryStatus.PARTIAL,
                    search_queries=tuple(search_queries),
                    tool_call_count=tool_call_count,
                    items=tuple(collected_items),
                )
                await self._persist_collect_result(
                    task_id=task_id,
                    revision_id=revision_id,
                    result=result,
                )
                await self._append_event(
                    task_id=task_id,
                    event="collector.completed",
                    payload={
                        "subtask_id": subtask_id,
                        "tool_call_id": plan.tool_call_id,
                        "status": result.status.value,
                        "item_count": len(result.items),
                        "search_queries": list(result.search_queries),
                    },
                )
                return result

            call_index += 1

    async def _execute_collector_tool_call(
        self,
        *,
        task_id: str,
        revision_id: str,
        subtask_id: str,
        plan: CollectPlan,
        tool_call: CollectorToolCall,
    ) -> tuple[PromptMessage, dict[str, object], tuple[CollectedSourceItem, ...]]:
        if tool_call.tool_name == "web_search":
            return await self._execute_collector_search(
                task_id=task_id,
                revision_id=revision_id,
                subtask_id=subtask_id,
                plan=plan,
                tool_call=tool_call,
            )
        if tool_call.tool_name == "web_fetch":
            return await self._execute_collector_fetch(
                task_id=task_id,
                revision_id=revision_id,
                subtask_id=subtask_id,
                plan=plan,
                tool_call=tool_call,
            )
        payload = {
            "success": False,
            "error_code": "unsupported_tool",
            "tool_name": tool_call.tool_name,
        }
        return (
            PromptMessage(
                role="tool",
                name=tool_call.tool_name,
                tool_call_id=tool_call.tool_call_id,
                content=json.dumps(payload, ensure_ascii=False, indent=2),
            ),
            payload,
            (),
        )

    async def _execute_collector_search(
        self,
        *,
        task_id: str,
        revision_id: str,
        subtask_id: str,
        plan: CollectPlan,
        tool_call: CollectorToolCall,
    ) -> tuple[PromptMessage, dict[str, object], tuple[CollectedSourceItem, ...]]:
        search_query = str(tool_call.arguments_json.get("search_query") or "").strip()
        search_recency_filter = str(
            tool_call.arguments_json.get("search_recency_filter") or "noLimit"
        ).strip()
        await self._append_event(
            task_id=task_id,
            event="collector.search.started",
            payload={
                "subtask_id": subtask_id,
                "tool_call_id": plan.tool_call_id,
                "search_query": search_query,
                "search_recency_filter": search_recency_filter,
            },
        )
        try:
            search_response = await self._invoke_operation(
                lambda: self._web_search_client.search(search_query, search_recency_filter)
            )
            status = "completed"
            error_code = None
        except RiskControlTriggered:
            raise
        except RetryableOperationError:
            search_response = None
            status = "failed"
            error_code = "retry_exhausted"

        with self._session_factory() as session:
            self._task_service.repository.append_tool_call(
                session=session,
                task_id=task_id,
                revision_id=revision_id,
                subtask_id=subtask_id,
                tool_call_id=tool_call.tool_call_id,
                tool_name="web_search",
                status=status,
                error_code=error_code,
                request_json={
                    "search_query": search_query,
                    "search_recency_filter": search_recency_filter,
                },
                response_json=None
                if search_response is None
                else {
                    "result_count": len(search_response.results),
                    "titles": [result.title for result in search_response.results],
                },
                created_at=self._clock(),
            )
            session.commit()

        titles = [] if search_response is None else [result.title for result in search_response.results]
        await self._append_event(
            task_id=task_id,
            event="collector.search.completed",
            payload={
                "subtask_id": subtask_id,
                "tool_call_id": plan.tool_call_id,
                "search_query": search_query,
                "result_count": 0 if search_response is None else len(search_response.results),
                "titles": titles,
            },
        )

        payload: dict[str, object] = {
            "success": search_response is not None,
            "search_query": search_query,
            "search_recency_filter": search_recency_filter,
            "results": []
            if search_response is None
            else [
                {
                    "title": result.title,
                    "link": result.link,
                    "snippet": result.snippet,
                }
                for result in search_response.results
            ],
        }
        if error_code is not None:
            payload["error_code"] = error_code
        return (
            PromptMessage(
                role="tool",
                name="web_search",
                tool_call_id=tool_call.tool_call_id,
                content=json.dumps(payload, ensure_ascii=False, indent=2),
            ),
            payload,
            (),
        )

    async def _execute_collector_fetch(
        self,
        *,
        task_id: str,
        revision_id: str,
        subtask_id: str,
        plan: CollectPlan,
        tool_call: CollectorToolCall,
    ) -> tuple[PromptMessage, dict[str, object], tuple[CollectedSourceItem, ...]]:
        url = str(tool_call.arguments_json.get("url") or "").strip()
        await self._append_event(
            task_id=task_id,
            event="collector.fetch.started",
            payload={
                "subtask_id": subtask_id,
                "tool_call_id": plan.tool_call_id,
                "url": url,
            },
        )
        try:
            fetch_response = await self._invoke_operation(
                lambda: self._web_fetch_client.fetch(url)
            )
            status = "completed"
            error_code = None
        except RetryableOperationError:
            fetch_response = None
            status = "failed"
            error_code = "retry_exhausted"

        with self._session_factory() as session:
            self._task_service.repository.append_tool_call(
                session=session,
                task_id=task_id,
                revision_id=revision_id,
                subtask_id=subtask_id,
                tool_call_id=tool_call.tool_call_id,
                tool_name="web_fetch",
                status=status,
                error_code=error_code,
                request_json={"url": url},
                response_json=None
                if fetch_response is None
                else {
                    "success": fetch_response.success,
                    "title": fetch_response.title,
                },
                created_at=self._clock(),
            )
            session.commit()

        await self._append_event(
            task_id=task_id,
            event="collector.fetch.completed",
            payload={
                "subtask_id": subtask_id,
                "tool_call_id": plan.tool_call_id,
                "url": url,
                "success": False if fetch_response is None else fetch_response.success,
                "title": None if fetch_response is None else fetch_response.title,
            },
        )

        truncated_content = None
        collected_items: tuple[CollectedSourceItem, ...] = ()
        if fetch_response is not None and fetch_response.success:
            truncated_content = (fetch_response.content or "")[: self._settings.fetched_content_limit]
            collected_items = (
                CollectedSourceItem(
                    title=fetch_response.title or url,
                    link=url,
                    info=truncated_content,
                ),
            )

        payload: dict[str, object] = {
            "success": fetch_response is not None and fetch_response.success,
            "url": url,
            "title": None if fetch_response is None else fetch_response.title,
            "content": truncated_content,
        }
        if error_code is not None:
            payload["error_code"] = error_code
        return (
            PromptMessage(
                role="tool",
                name="web_fetch",
                tool_call_id=tool_call.tool_call_id,
                content=json.dumps(payload, ensure_ascii=False, indent=2),
            ),
            payload,
            collected_items,
        )

    async def _persist_collect_result(
        self,
        *,
        task_id: str,
        revision_id: str,
        result: CollectResult,
    ) -> None:
        if not result.items:
            return
        with self._session_factory() as session:
            self._task_service.repository.append_collected_sources(
                session=session,
                task_id=task_id,
                revision_id=revision_id,
                subtask_id=result.subtask_id,
                tool_call_id=result.tool_call_id,
                items=result.items,
                created_at=self._clock(),
            )
            session.commit()

    async def _run_summary_round(
        self,
        *,
        task_id: str,
        revision_id: str,
        plans: tuple[CollectPlan, ...],
        collect_results: tuple[CollectResult, ...],
        runtime: CollectionRuntime,
    ) -> list[CollectSummary]:
        summaries: list[CollectSummary] = []
        for plan, result in zip(plans, collect_results, strict=True):
            summary = await self._run_single_summary(
                task_id=task_id,
                revision_id=revision_id,
                plan=plan,
                result=result,
            )
            summaries.append(summary)
            if summary.status is CollectSummaryStatus.RISK_BLOCKED:
                runtime.risk_blocked_count += 1
                if runtime.risk_blocked_count >= self._settings.collect_risk_block_threshold:
                    with self._session_factory() as session:
                        self._task_service.terminate_task(
                            session,
                            task_id=task_id,
                            reason="risk_control_threshold_exceeded",
                        )
                        session.commit()
                    runtime.cancelled = True
                    break
        return summaries

    async def _run_single_summary(
        self,
        *,
        task_id: str,
        revision_id: str,
        plan: CollectPlan,
        result: CollectResult,
    ) -> CollectSummary:
        now = self._clock()
        if result.status is CollectSummaryStatus.RISK_BLOCKED:
            summary = CollectSummary(
                tool_call_id=plan.tool_call_id,
                subtask_id=result.subtask_id,
                status=CollectSummaryStatus.RISK_BLOCKED,
                message="触发风控敏感，请重新规划",
            )
            with self._session_factory() as session:
                self._task_service.repository.append_agent_run(
                    session=session,
                    task_id=task_id,
                    revision_id=revision_id,
                    subtask_id=result.subtask_id,
                    agent_type="summary",
                    prompt_name="summary_round",
                    status=summary.status.value,
                    reasoning_text=None,
                    content_text=json.dumps(
                        summary.model_dump(mode="json", exclude_none=True),
                        ensure_ascii=False,
                    ),
                    finish_reason="risk_blocked",
                    tool_calls_json=None,
                    created_at=now,
                    updated_at=now,
                )
                session.commit()
            await self._append_event(
                task_id=task_id,
                event="summary.completed",
                payload=summary.model_dump(mode="json", exclude_none=True),
            )
            return summary

        invocation = SummaryInvocation(
            prompt_name="summary_round",
            subtask_id=result.subtask_id,
            plan=plan,
            result_status=result.status.value,
            search_queries=result.search_queries,
            item_payloads=tuple(
                {
                    "title": item.title,
                    "link": item.link,
                    "info": item.info,
                }
                for item in result.items
            ),
            now=now,
            profile=build_stage_profile(
                settings=self._settings,
                stage="summary",
            ),
        )
        prompt_bundle = build_summary_prompt(invocation=invocation)
        invocation = replace(invocation, prompt_bundle=prompt_bundle)
        try:
            decision = await self._invoke_operation(
                lambda: self._summary_agent.summarize(invocation)
            )
        except RiskControlTriggered:
            logger.error(
                "summary risk control triggered",
                extra={"task_id": task_id, "subtask_id": result.subtask_id, "error_code": "risk_control_triggered"},
                exc_info=True,
            )
            decision = None
        except RetryableOperationError:
            logger.error(
                "summary upstream error after retries",
                extra={"task_id": task_id, "subtask_id": result.subtask_id, "error_code": "upstream_service_error"},
                exc_info=True,
            )
            await self._fail_task(
                task_id=task_id,
                error_code="upstream_service_error",
                message="summary 调用失败且重试耗尽。",
            )
            return CollectSummary(
                tool_call_id=plan.tool_call_id,
                subtask_id=result.subtask_id,
                status=CollectSummaryStatus.PARTIAL,
                collect_target=plan.collect_target,
                search_queries=list(result.search_queries),
                key_findings_markdown="- summary 调用失败，结果不完整。",
                additional_info=plan.additional_info,
                freshness_requirement=plan.freshness_requirement.value,
            )

        if decision is None:
            summary = CollectSummary(
                tool_call_id=plan.tool_call_id,
                subtask_id=result.subtask_id,
                status=CollectSummaryStatus.RISK_BLOCKED,
                message="触发风控敏感，请重新规划",
            )
        else:
            summary = CollectSummary(
                tool_call_id=plan.tool_call_id,
                subtask_id=result.subtask_id,
                collect_target=plan.collect_target,
                status=decision.status,
                search_queries=list(result.search_queries),
                key_findings_markdown=decision.key_findings_markdown,
                message=decision.message,
                additional_info=plan.additional_info,
                freshness_requirement=plan.freshness_requirement.value,
            )

        with self._session_factory() as session:
            self._task_service.repository.append_agent_run(
                session=session,
                task_id=task_id,
                revision_id=revision_id,
                subtask_id=result.subtask_id,
                agent_type="summary",
                prompt_name=invocation.prompt_name,
                status=summary.status.value,
                reasoning_text=None,
                content_text=json.dumps(
                    {
                        "prompt_bundle": dump_prompt_bundle(prompt_bundle),
                        "summary": summary.model_dump(mode="json", exclude_none=True),
                    },
                    ensure_ascii=False,
                ),
                finish_reason=summary.status.value,
                provider_finish_reason=(
                    decision.provider_finish_reason if decision is not None else None
                ),
                provider_usage_json=(
                    decision.provider_usage if decision is not None else None
                ),
                tool_calls_json=None,
                created_at=now,
                updated_at=now,
            )
            session.commit()

        await self._append_event(
            task_id=task_id,
            event="summary.completed",
            payload=summary.model_dump(mode="json", exclude_none=True),
        )
        return summary

    async def _run_merge(self, *, task_id: str, revision_id: str) -> None:
        with self._session_factory() as session:
            raw_records = self._task_service.repository.list_collected_sources(
                session=session,
                revision_id=revision_id,
            )
        merged_sources = self._merge_service.merge(
            tuple(
                CollectedSourceItem(
                    title=record.title,
                    link=record.link,
                    info=record.info,
                )
                for record in raw_records
            )
        )
        with self._session_factory() as session:
            self._task_service.repository.persist_merged_sources(
                session=session,
                revision_id=revision_id,
                merged_sources=merged_sources,
            )
            session.commit()
        await self._append_event(
            task_id=task_id,
            event="sources.merged",
            payload={
                "source_count_before_merge": len(raw_records),
                "source_count_after_merge": len(merged_sources),
                "reference_count": len(merged_sources),
            },
        )

    async def _build_risk_blocked_collect_result(
        self,
        *,
        task_id: str,
        revision_id: str,
        subtask_id: str,
        plan: CollectPlan,
        prompt: PromptBundle,
        reasoning_text: str,
    ) -> CollectResult:
        now = self._clock()
        with self._session_factory() as session:
            self._task_service.repository.append_agent_run(
                session=session,
                task_id=task_id,
                revision_id=revision_id,
                subtask_id=subtask_id,
                agent_type="collector",
                prompt_name="collector_round",
                status=CollectSummaryStatus.RISK_BLOCKED.value,
                reasoning_text=reasoning_text,
                content_text=json.dumps(
                    {"prompt_bundle": dump_prompt_bundle(prompt)},
                    ensure_ascii=False,
                ),
                finish_reason="risk_blocked",
                tool_calls_json=None,
                created_at=now,
                updated_at=now,
            )
            session.commit()
        result = CollectResult(
            subtask_id=subtask_id,
            tool_call_id=plan.tool_call_id,
            collect_target=plan.collect_target,
            status=CollectSummaryStatus.RISK_BLOCKED,
            search_queries=tuple(),
            tool_call_count=0,
            items=tuple(),
        )
        await self._append_event(
            task_id=task_id,
            event="collector.completed",
            payload={
                "subtask_id": subtask_id,
                "tool_call_id": plan.tool_call_id,
                "status": result.status.value,
                "item_count": 0,
                "search_queries": [],
            },
        )
        return result

    def _load_planner_history_transcript(
        self,
        *,
        task_id: str,
        revision_id: str,
        summaries: tuple[CollectSummary, ...],
    ) -> tuple[PromptMessage, ...]:
        if not summaries:
            return ()
        with self._session_factory() as session:
            prior_runs = list(
                session.scalars(
                    select(AgentRunRecord)
                    .where(AgentRunRecord.task_id == task_id)
                    .where(AgentRunRecord.revision_id == revision_id)
                    .where(AgentRunRecord.agent_type == "planner")
                    .order_by(AgentRunRecord.created_at.asc(), AgentRunRecord.id.asc())
                )
            )
        if not prior_runs:
            return ()

        transcript: list[PromptMessage] = []
        summary_index = 0
        for run in prior_runs:
            plan_payloads = _extract_planner_plan_payloads(run.content_text)
            if not plan_payloads:
                continue

            tool_calls = _planner_tool_call_payloads_from_plan_payloads(plan_payloads)
            transcript.append(
                PromptMessage(
                    role="assistant",
                    content="",
                    tool_calls=tool_calls,
                    reasoning_content=run.reasoning_text or None,
                )
            )

            round_summaries = summaries[summary_index : summary_index + len(plan_payloads)]
            if len(round_summaries) != len(plan_payloads):
                return ()
            transcript.extend(_planner_tool_messages(round_summaries))
            summary_index += len(plan_payloads)

        if summary_index != len(summaries):
            return ()
        return tuple(transcript)

    async def _invoke_operation(self, operation: Callable[[], Awaitable[object]]) -> object:
        return await self._operation_invoker.invoke(operation)

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
        logger.error(
            "collection task failed: %s",
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

    def _reserve_collect_agent_calls(self, *, revision_id: str, additional_calls: int) -> bool:
        with self._session_factory() as session:
            revision = self._task_service.repository.get_revision(
                session=session,
                revision_id=revision_id,
            )
            if revision is None:
                session.rollback()
                return False
            if (
                revision.collect_agent_calls_used + additional_calls
                > self._settings.revision_collect_agent_limit
            ):
                session.rollback()
                return False
            self._task_service.repository.increment_collect_agent_calls_used(
                session=session,
                revision_id=revision_id,
                increment_by=additional_calls,
            )
            session.commit()
            return True


def _extract_planner_plan_payloads(content_text: str | None) -> tuple[dict[str, object], ...]:
    if not content_text:
        return ()
    try:
        payload = json.loads(content_text)
    except json.JSONDecodeError:
        return ()
    raw_plans = payload.get("plans")
    if not isinstance(raw_plans, list):
        return ()
    return tuple(item for item in raw_plans if isinstance(item, dict))


def _planner_tool_call_payloads_from_plan_payloads(
    plans: tuple[dict[str, object], ...],
) -> tuple[dict[str, object], ...]:
    return tuple(
        {
            "id": str(plan.get("tool_call_id") or ""),
            "type": "function",
            "function": {
                "name": "collect_agent",
                "arguments": json.dumps(
                    {
                        key: value
                        for key, value in {
                            "collect_target": plan.get("collect_target"),
                            "additional_info": plan.get("additional_info"),
                            "freshness_requirement": plan.get("freshness_requirement"),
                        }.items()
                        if value is not None
                    },
                    ensure_ascii=False,
                ),
            },
        }
        for plan in plans
    )


def _collector_tool_call_payloads(
    tool_calls: tuple[CollectorToolCall, ...],
) -> tuple[dict[str, object], ...]:
    return tuple(
        {
            "id": tool_call.tool_call_id,
            "type": "function",
            "function": {
                "name": tool_call.tool_name,
                "arguments": json.dumps(tool_call.arguments_json, ensure_ascii=False),
            },
        }
        for tool_call in tool_calls
    )


def _planner_tool_messages(
    summaries: tuple[CollectSummary, ...],
) -> tuple[PromptMessage, ...]:
    return tuple(
        PromptMessage(
            role="tool",
            name="collect_agent",
            tool_call_id=summary.tool_call_id,
            content=json.dumps(
                summary.model_dump(mode="json", exclude_none=True),
                ensure_ascii=False,
                indent=2,
            ),
        )
        for summary in summaries
    )
