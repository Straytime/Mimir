import asyncio
from collections.abc import AsyncIterator, Callable
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from fastapi import Request
from sqlalchemy.orm import Session, sessionmaker

from app.application.services.clarification import ClarificationOrchestrator
from app.application.services.tasks import TaskService
from app.core.config import Settings
from app.domain.enums import TaskPhase, TaskStatus
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
        settings: Settings,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._task_service = task_service
        self._clarification_orchestrator = clarification_orchestrator
        self._settings = settings
        self._clock = clock or (lambda: datetime.now(UTC))
        self._runtimes: dict[str, TaskRuntime] = {}

    async def register_task(
        self,
        *,
        task_id: str,
        connect_deadline_at: datetime,
    ) -> None:
        runtime = self._runtimes.get(task_id)
        if runtime is None:
            runtime = TaskRuntime(connect_deadline_at=connect_deadline_at)
            self._runtimes[task_id] = runtime
        else:
            runtime.connect_deadline_at = connect_deadline_at

        self._ensure_monitor(task_id=task_id, runtime=runtime)

    async def prepare_event_stream(
        self,
        *,
        task_id: str,
        token: str,
    ) -> str:
        with self._session_factory() as session:
            task = self._task_service.get_task_for_token(
                session,
                task_id=task_id,
                token=token,
            )
            runtime = self._runtimes.get(task_id)
            if runtime is None:
                runtime = TaskRuntime(connect_deadline_at=task.connect_deadline_at)
                self._runtimes[task_id] = runtime

            if not runtime.first_connected:
                runtime.first_connected = True
                runtime.last_client_seen_at = self._clock()
                runtime.last_server_heartbeat_at = self._clock()
                self._task_service.ensure_task_created_event(
                    session,
                    task_id=task_id,
                )
                session.commit()
                if (
                    TaskStatus(task.status) is TaskStatus.RUNNING
                    and task.phase == "clarifying"
                ):
                    await self._clarification_orchestrator.ensure_started(task_id=task_id)

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
        with self._session_factory() as session:
            trace_id, _ = self._task_service.disconnect_task(
                session,
                task_id=task_id,
                token=token,
            )
            session.commit()
        await self._clarification_orchestrator.cancel(task_id=task_id)
        return trace_id

    async def submit_clarification(
        self,
        *,
        task_id: str,
        token: str,
        payload,
    ) -> tuple[str, object]:
        return await self._clarification_orchestrator.submit(
            task_id=task_id,
            token=token,
            payload=payload,
        )

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
            return event

    async def shutdown(self) -> None:
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

    def _ensure_monitor(self, *, task_id: str, runtime: TaskRuntime) -> None:
        if runtime.monitor_task is None or runtime.monitor_task.done():
            runtime.monitor_task = asyncio.create_task(self._monitor_task(task_id))

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
                    if not runtime.first_connected and now >= runtime.connect_deadline_at:
                        self._task_service.terminate_task(
                            session,
                            task_id=task_id,
                            reason="sse_connect_timeout",
                        )
                        session.commit()
                        await self._clarification_orchestrator.cancel(task_id=task_id)
                        if runtime.connection_count == 0:
                            self._runtimes.pop(task_id, None)
                        return

                    if runtime.first_connected and status in {
                        TaskStatus.RUNNING,
                        TaskStatus.AWAITING_USER_INPUT,
                        TaskStatus.AWAITING_FEEDBACK,
                    }:
                        if (
                            runtime.last_client_seen_at is not None
                            and now - runtime.last_client_seen_at
                            >= timedelta(
                                seconds=self._settings.client_heartbeat_timeout_seconds
                            )
                        ):
                            self._task_service.terminate_task(
                                session,
                                task_id=task_id,
                                reason="heartbeat_timeout",
                            )
                            session.commit()
                            await self._clarification_orchestrator.cancel(task_id=task_id)
                            if runtime.connection_count == 0:
                                self._runtimes.pop(task_id, None)
                            return

                    if (
                        status is TaskStatus.AWAITING_FEEDBACK
                        and task.expires_at is not None
                        and now >= task.expires_at.astimezone(UTC)
                    ):
                        self._task_service.expire_task(session, task_id=task_id)
                        session.commit()
                        await self._clarification_orchestrator.cancel(task_id=task_id)
                        if runtime.connection_count == 0:
                            self._runtimes.pop(task_id, None)
                        return

                await self._clarification_orchestrator.maybe_auto_submit(task_id=task_id)

                with self._session_factory() as session:
                    current_task = self._task_service.repository.get_task(
                        session=session,
                        task_id=task_id,
                    )
                    if current_task is None:
                        self._runtimes.pop(task_id, None)
                        return
                    current_status = TaskStatus(current_task.status)
                    if current_status in {
                        TaskStatus.TERMINATED,
                        TaskStatus.FAILED,
                        TaskStatus.EXPIRED,
                        TaskStatus.PURGED,
                    } and runtime.connection_count == 0:
                        self._runtimes.pop(task_id, None)
                        return
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
        with self._session_factory() as session:
            self._task_service.terminate_task(
                session,
                task_id=task_id,
                reason="client_disconnected",
            )
            session.commit()
        await self._clarification_orchestrator.cancel(task_id=task_id)

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

            if TaskStatus(task.status) in {
                TaskStatus.RUNNING,
                TaskStatus.AWAITING_USER_INPUT,
                TaskStatus.AWAITING_FEEDBACK,
            }:
                self._task_service.terminate_task(
                    session,
                    task_id=task_id,
                    reason="client_disconnected",
                )
                session.commit()
                await self._clarification_orchestrator.cancel(task_id=task_id)
            else:
                session.rollback()
