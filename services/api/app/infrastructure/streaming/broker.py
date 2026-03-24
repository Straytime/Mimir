import asyncio
import logging
from collections.abc import AsyncIterator, Callable
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

logger = logging.getLogger(__name__)

from fastapi import Request
from sqlalchemy.orm import Session, sessionmaker

from app.application.ports.delivery import ArtifactStore, E2BSandboxClient
from app.application.services.collection import CollectionOrchestrator
from app.application.services.clarification import ClarificationOrchestrator
from app.application.services.delivery import DeliveryOrchestrator
from app.application.services.feedback import FeedbackOrchestrator
from app.application.services.invocation import RetryingOperationInvoker
from app.application.services.tasks import TaskService
from app.core.config import Settings
from app.domain.enums import TaskStatus
from app.domain.schemas import EventEnvelope


TERMINAL_EVENTS = {"task.failed", "task.terminated", "task.expired"}


@dataclass(slots=True)
class TaskRuntime:
    connect_deadline_at: datetime
    first_connected: bool = False
    connection_count: int = 0
    last_client_seen_at: datetime | None = None
    last_server_heartbeat_at: datetime | None = None
    monitor_task: asyncio.Task[None] | None = None


def serialize_sse_event(event: EventEnvelope) -> bytes:
    return (
        f"id: {event.seq}\n"
        f"event: {event.event}\n"
        f"data: {event.model_dump_json()}\n\n"
    ).encode("utf-8")


class TaskLifecycleManager:
    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session],
        task_service: TaskService,
        clarification_orchestrator: ClarificationOrchestrator,
        collection_orchestrator: CollectionOrchestrator,
        delivery_orchestrator: DeliveryOrchestrator,
        feedback_orchestrator: FeedbackOrchestrator,
        artifact_store: ArtifactStore,
        sandbox_client: E2BSandboxClient,
        operation_invoker: RetryingOperationInvoker[object],
        settings: Settings,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._task_service = task_service
        self._clarification_orchestrator = clarification_orchestrator
        self._collection_orchestrator = collection_orchestrator
        self._delivery_orchestrator = delivery_orchestrator
        self._feedback_orchestrator = feedback_orchestrator
        self._artifact_store = artifact_store
        self._sandbox_client = sandbox_client
        self._operation_invoker = operation_invoker
        self._settings = settings
        self._clock = clock or (lambda: datetime.now(UTC))
        self._runtimes: dict[str, TaskRuntime] = {}
        self._cleanup_task: asyncio.Task[None] | None = None
        self._cleanup_lock = asyncio.Lock()

    async def register_task(
        self,
        *,
        task_id: str,
        connect_deadline_at: datetime,
    ) -> None:
        self._ensure_cleanup_loop()
        runtime = self._runtimes.get(task_id)
        if runtime is None:
            runtime = TaskRuntime(connect_deadline_at=connect_deadline_at)
            self._runtimes[task_id] = runtime
        else:
            runtime.connect_deadline_at = connect_deadline_at

        should_start_clarification = False
        with self._session_factory() as session:
            task = self._task_service.repository.get_task(session=session, task_id=task_id)
            if task is not None:
                event = self._task_service.ensure_task_created_event(
                    session,
                    task_id=task_id,
                )
                if event is not None:
                    session.commit()
                else:
                    session.rollback()
                should_start_clarification = (
                    TaskStatus(task.status) is TaskStatus.RUNNING
                    and task.phase == "clarifying"
                )

        if should_start_clarification:
            await self._clarification_orchestrator.ensure_started(task_id=task_id)

        self._ensure_monitor(task_id=task_id, runtime=runtime)

    async def prepare_event_stream(
        self,
        *,
        task_id: str,
        token: str,
    ) -> str:
        self._ensure_cleanup_loop()
        with self._session_factory() as session:
            task = self._task_service.get_task_for_token(
                session,
                task_id=task_id,
                token=token,
            )
            created_event = self._task_service.ensure_task_created_event(
                session,
                task_id=task_id,
            )
            if created_event is not None:
                session.commit()
            else:
                session.rollback()
            runtime = self._runtimes.get(task_id)
            if runtime is None:
                runtime = TaskRuntime(connect_deadline_at=task.connect_deadline_at)
                self._runtimes[task_id] = runtime

            if not runtime.first_connected:
                runtime.first_connected = True
                runtime.last_client_seen_at = self._clock()
                runtime.last_server_heartbeat_at = self._clock()
                session.rollback()

            runtime.connection_count += 1
            self._ensure_monitor(task_id=task_id, runtime=runtime)
            return task.trace_id

    async def stream_events(
        self,
        *,
        request: Request,
        task_id: str,
    ) -> AsyncIterator[bytes]:
        last_seq = 0
        try:
            while True:
                emitted = False

                with self._session_factory() as session:
                    events = self._task_service.list_events_after(
                        session,
                        task_id=task_id,
                        after_seq=last_seq,
                    )

                for event in events:
                    emitted = True
                    last_seq = event.seq
                    runtime = self._runtimes.get(task_id)
                    if runtime is not None and event.event == "heartbeat":
                        runtime.last_server_heartbeat_at = event.timestamp
                    yield serialize_sse_event(event)
                    if event.event in TERMINAL_EVENTS:
                        return

                if await request.is_disconnected():
                    await self._handle_stream_disconnect(task_id=task_id)
                    return

                if not emitted:
                    if await self._maybe_emit_server_heartbeat(task_id=task_id):
                        continue
                    await asyncio.sleep(self._settings.lifecycle_poll_interval_seconds)
        finally:
            await self._finalize_stream(task_id=task_id)

    async def record_client_heartbeat(
        self,
        *,
        task_id: str,
        token: str,
    ) -> str:
        self._ensure_cleanup_loop()
        with self._session_factory() as session:
            trace_id = self._task_service.accept_client_heartbeat(
                session,
                task_id=task_id,
                token=token,
            )

        runtime = self._runtimes.get(task_id)
        if runtime is not None:
            runtime.last_client_seen_at = self._clock()
        return trace_id

    async def disconnect_task(
        self,
        *,
        task_id: str,
        token: str,
    ) -> str:
        self._ensure_cleanup_loop()
        with self._session_factory() as session:
            trace_id, _ = self._task_service.disconnect_task(
                session,
                task_id=task_id,
                token=token,
            )
            session.commit()
        await self._cancel_all_orchestrators(task_id=task_id)
        await self._mark_cleanup_pending(task_id=task_id)
        await self._maybe_cleanup_task(task_id=task_id)
        return trace_id

    async def submit_clarification(
        self,
        *,
        task_id: str,
        token: str,
        payload,
    ) -> tuple[str, object]:
        self._ensure_cleanup_loop()
        result = await self._clarification_orchestrator.submit(
            task_id=task_id,
            token=token,
            payload=payload,
        )
        runtime = self._runtimes.get(task_id)
        if runtime is not None:
            runtime.last_client_seen_at = self._clock()
        return result

    async def submit_feedback(
        self,
        *,
        task_id: str,
        token: str,
        payload,
    ) -> tuple[str, object]:
        self._ensure_cleanup_loop()
        result = await self._feedback_orchestrator.submit(
            task_id=task_id,
            token=token,
            payload=payload,
        )
        runtime = self._runtimes.get(task_id)
        if runtime is not None:
            runtime.last_client_seen_at = self._clock()
        return result

    async def transition_phase(
        self,
        *,
        task_id: str,
        target_phase,
    ) -> EventEnvelope:
        with self._session_factory() as session:
            event = self._task_service.transition_phase(
                session,
                task_id=task_id,
                target_phase=target_phase,
            )
            session.commit()
            return event

    async def fail_task(
        self,
        *,
        task_id: str,
        error_code: str,
        message: str,
    ) -> EventEnvelope | None:
        with self._session_factory() as session:
            event = self._task_service.fail_task(
                session,
                task_id=task_id,
                error_code=error_code,
                message=message,
            )
            session.commit()
        await self._mark_cleanup_pending(task_id=task_id)
        await self._maybe_cleanup_task(task_id=task_id)
        return event

    async def run_cleanup_compensation(self) -> None:
        self._ensure_cleanup_loop()
        async with self._cleanup_lock:
            now = self._clock()
            with self._session_factory() as session:
                expired_tasks = self._task_service.repository.list_expired_feedback_tasks(
                    session=session,
                    now=now,
                )

            for task in expired_tasks:
                with self._session_factory() as session:
                    self._task_service.expire_task(session, task_id=task.task_id)
                    session.commit()
                await self._cancel_all_orchestrators(task_id=task.task_id)
                await self._mark_cleanup_pending(task_id=task.task_id)
                await self._maybe_cleanup_task(task_id=task.task_id)

            with self._session_factory() as session:
                pending_tasks = self._task_service.repository.list_cleanup_pending_tasks(
                    session=session
                )
                self._task_service.repository.prune_ip_usage_before(
                    session=session,
                    cutoff=now - timedelta(hours=48),
                )
                self._task_service.repository.prune_llm_call_traces_before(
                    session=session,
                    cutoff=now - timedelta(hours=self._settings.llm_trace_retention_hours),
                )
                session.commit()

            for task in pending_tasks:
                await self._maybe_cleanup_task(task_id=task.task_id)

    async def shutdown(self) -> None:
        if self._cleanup_task is not None:
            self._cleanup_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._cleanup_task
        for runtime in list(self._runtimes.values()):
            if runtime.monitor_task is None:
                continue
            runtime.monitor_task.cancel()
        for runtime in list(self._runtimes.values()):
            if runtime.monitor_task is None:
                continue
            with suppress(asyncio.CancelledError):
                await runtime.monitor_task
        await self._clarification_orchestrator.shutdown()
        await self._collection_orchestrator.shutdown()
        await self._delivery_orchestrator.shutdown()
        await self._feedback_orchestrator.shutdown()

    def _ensure_monitor(self, *, task_id: str, runtime: TaskRuntime) -> None:
        if runtime.monitor_task is None or runtime.monitor_task.done():
            runtime.monitor_task = asyncio.create_task(self._monitor_task(task_id))

    def _ensure_cleanup_loop(self) -> None:
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._monitor_cleanup())

    async def _monitor_cleanup(self) -> None:
        try:
            while True:
                await asyncio.sleep(self._settings.cleanup_scan_interval_seconds)
                await self.run_cleanup_compensation()
        except asyncio.CancelledError:
            raise

    async def _monitor_task(self, task_id: str) -> None:
        try:
            while True:
                await asyncio.sleep(self._settings.lifecycle_poll_interval_seconds)

                runtime = self._runtimes.get(task_id)
                if runtime is None:
                    return

                with self._session_factory() as session:
                    task = self._task_service.repository.get_task(
                        session=session,
                        task_id=task_id,
                    )
                    if task is None:
                        self._runtimes.pop(task_id, None)
                        return

                    now = self._clock()
                    status = TaskStatus(task.status)
                    if (
                        status is TaskStatus.AWAITING_FEEDBACK
                        and task.expires_at is not None
                        and now >= task.expires_at.astimezone(UTC)
                    ):
                        self._task_service.expire_task(session, task_id=task_id)
                        session.commit()
                        await self._cancel_all_orchestrators(task_id=task_id)
                        await self._mark_cleanup_pending(task_id=task_id)
                        await self._maybe_cleanup_task(task_id=task_id)
                        if runtime.connection_count == 0:
                            self._runtimes.pop(task_id, None)
                        return

                    if status in {
                        TaskStatus.TERMINATED,
                        TaskStatus.FAILED,
                        TaskStatus.EXPIRED,
                        TaskStatus.PURGED,
                    }:
                        session.rollback()
                        await self._mark_cleanup_pending(task_id=task_id)
                        await self._maybe_cleanup_task(task_id=task_id)
                        if runtime.connection_count == 0:
                            self._runtimes.pop(task_id, None)
                        return

                await self._clarification_orchestrator.maybe_auto_submit(task_id=task_id)
        except asyncio.CancelledError:
            raise

    async def _maybe_emit_server_heartbeat(self, *, task_id: str) -> bool:
        runtime = self._runtimes.get(task_id)
        if runtime is None or not runtime.first_connected:
            return False

        last_heartbeat_at = runtime.last_server_heartbeat_at
        if last_heartbeat_at is not None and (
            self._clock() - last_heartbeat_at
            < timedelta(seconds=self._settings.sse_heartbeat_interval_seconds)
        ):
            return False

        with self._session_factory() as session:
            event = self._task_service.emit_server_heartbeat(session, task_id=task_id)
            if event is None:
                return False
            session.commit()

        runtime.last_server_heartbeat_at = event.timestamp
        return True

    async def _handle_stream_disconnect(self, *, task_id: str) -> None:
        logger.info(
            "sse stream disconnected without explicit abort",
            extra={"task_id": task_id},
        )

    async def _finalize_stream(self, *, task_id: str) -> None:
        runtime = self._runtimes.get(task_id)
        if runtime is None:
            return

        runtime.connection_count = max(0, runtime.connection_count - 1)
        if runtime.connection_count > 0:
            return

        with self._session_factory() as session:
            task = self._task_service.repository.get_task(
                session=session,
                task_id=task_id,
            )
            if task is None:
                self._runtimes.pop(task_id, None)
                return

            status = TaskStatus(task.status)
            if status in {
                TaskStatus.TERMINATED,
                TaskStatus.FAILED,
                TaskStatus.EXPIRED,
                TaskStatus.PURGED,
            }:
                session.rollback()
                await self._maybe_cleanup_task(task_id=task_id)
                return

            session.rollback()

    async def _cancel_all_orchestrators(self, *, task_id: str) -> None:
        await self._clarification_orchestrator.cancel(task_id=task_id)
        await self._collection_orchestrator.cancel(task_id=task_id)
        await self._delivery_orchestrator.cancel(task_id=task_id)
        await self._feedback_orchestrator.cancel(task_id=task_id)

    async def _mark_cleanup_pending(self, *, task_id: str) -> None:
        with self._session_factory() as session:
            task = self._task_service.repository.get_task(session=session, task_id=task_id)
            if task is None:
                return
            if not task.cleanup_pending:
                self._task_service.repository.mark_cleanup_pending(
                    session=session,
                    task_id=task_id,
                    updated_at=self._clock(),
                )
                session.commit()
            else:
                session.rollback()

    async def _maybe_cleanup_task(self, *, task_id: str) -> bool:
        runtime = self._runtimes.get(task_id)
        if runtime is not None and runtime.connection_count > 0:
            return False
        return await self._cleanup_task_records(task_id=task_id)

    async def _cleanup_task_records(self, *, task_id: str) -> bool:
        with self._session_factory() as session:
            task = self._task_service.repository.get_task(session=session, task_id=task_id)
            if task is None:
                self._runtimes.pop(task_id, None)
                return True
            artifacts = self._task_service.repository.list_task_artifacts(
                session=session,
                task_id=task_id,
            )
            revisions = self._task_service.repository.list_revisions_for_task(
                session=session,
                task_id=task_id,
            )

        try:
            for revision in revisions:
                if revision.sandbox_id is None:
                    continue
                sandbox_id = revision.sandbox_id
                await self._operation_invoker.invoke(
                    lambda sandbox_id=sandbox_id: self._sandbox_client.destroy(sandbox_id)
                )
                with self._session_factory() as session:
                    self._task_service.repository.update_revision_sandbox_id(
                        session=session,
                        revision_id=revision.revision_id,
                        sandbox_id=None,
                    )
                    session.commit()

            for artifact in artifacts:
                await self._operation_invoker.invoke(
                    lambda storage_key=artifact.storage_key: self._artifact_store.delete(
                        storage_key
                    )
                )
        except Exception:
            return False

        with self._session_factory() as session:
            self._task_service.repository.delete_task(session=session, task_id=task_id)
            session.commit()

        self._runtimes.pop(task_id, None)
        return True
