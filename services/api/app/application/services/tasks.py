from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.errors import ApiError
from app.application.dto.tasks import (
    AcceptedResponse,
    CreateTaskRequest,
    CreateTaskResponse,
    TaskDetailResponse,
    TaskUrls,
)
from app.application.policies.activity_lock import ActivityLockPolicy
from app.application.policies.ip_quota import IPQuotaPolicy
from app.application.ports.security import AccessTokenSigner, TaskTokenSigner
from app.core.config import Settings
from app.core.ids import generate_id, hash_secret
from app.domain.enums import RevisionStatus, TaskPhase, TaskStatus
from app.domain.schemas import EventEnvelope, RevisionSummary, TaskSnapshot
from app.domain.state_machine import TaskLifecycleState, TaskStateMachine
from app.domain.tokens import TaskTokenPayload
from app.infrastructure.db.models import ResearchTaskRecord, TaskRevisionRecord
from app.infrastructure.db.repositories import TaskRepository
from app.infrastructure.security.hmac_signers import TokenVerificationError


def _hash_ip(ip_address: str) -> str:
    return sha256(ip_address.encode("utf-8")).hexdigest()


@dataclass(slots=True)
class TaskService:
    repository: TaskRepository
    task_token_signer: TaskTokenSigner
    access_token_signer: AccessTokenSigner
    activity_lock_policy: ActivityLockPolicy
    ip_quota_policy: IPQuotaPolicy
    settings: Settings
    clock: Callable[[], datetime] = lambda: datetime.now(UTC)

    def create_task(
        self,
        session: Session,
        *,
        payload: CreateTaskRequest,
        client_ip: str,
    ) -> CreateTaskResponse:
        now = self.clock()
        ip_hash = _hash_ip(client_ip)

        quota_decision = self.ip_quota_policy.evaluate(
            created_at_values=self.repository.list_ip_usage(
                session=session,
                ip_hash=ip_hash,
                since=now - timedelta(hours=self.settings.ip_quota_window_hours),
            ),
            now=now,
        )
        if not quota_decision.allowed:
            raise ApiError(
                status_code=429,
                code="ip_quota_exceeded",
                message="24 小时内创建任务次数已达上限，请稍后再试。",
                detail={
                    "quota_limit": quota_decision.quota_limit,
                    "quota_used": quota_decision.quota_used,
                    "next_available_at": quota_decision.next_available_at.isoformat(),
                },
                headers={"Retry-After": str(quota_decision.retry_after_seconds)},
            )

        lock_decision = self.activity_lock_policy.evaluate(
            active_task_id=self.repository.get_active_lock_holder(session=session)
        )
        if not lock_decision.allowed:
            raise ApiError(
                status_code=409,
                code="resource_busy",
                message="当前已有研究任务在执行，请稍后再试。",
            )

        task_id = generate_id("tsk")
        revision_id = generate_id("rev")
        trace_id = generate_id("trc")
        connect_deadline_at = now + timedelta(
            seconds=self.settings.connect_deadline_seconds
        )
        task_token = self.task_token_signer.sign(
            TaskTokenPayload(
                task_id=task_id,
                issued_at=now,
                expires_at=now + timedelta(hours=self.settings.task_token_ttl_hours),
            )
        )
        snapshot = TaskSnapshot(
            task_id=task_id,
            status=TaskStatus.RUNNING,
            phase=TaskPhase.CLARIFYING,
            active_revision_id=revision_id,
            active_revision_number=1,
            clarification_mode=payload.config.clarification_mode,
            created_at=now,
            updated_at=now,
            expires_at=None,
            available_actions=[],
        )
        revision_summary = RevisionSummary(
            revision_id=revision_id,
            revision_number=1,
            revision_status=RevisionStatus.IN_PROGRESS,
            started_at=now,
            finished_at=None,
            requirement_detail=None,
        )

        try:
            self.repository.create_task(
                session=session,
                task=ResearchTaskRecord(
                    task_id=task_id,
                    trace_id=trace_id,
                    status=snapshot.status.value,
                    phase=snapshot.phase.value,
                    clarification_mode=snapshot.clarification_mode.value,
                    initial_query=payload.initial_query,
                    client_timezone=payload.client.timezone,
                    client_locale=payload.client.locale,
                    ip_hash=ip_hash,
                    task_token_hash=hash_secret(task_token),
                    active_revision_id=revision_id,
                    active_revision_number=1,
                    created_at=now,
                    updated_at=now,
                    expires_at=None,
                    connect_deadline_at=connect_deadline_at,
                ),
                revision=TaskRevisionRecord(
                    revision_id=revision_id,
                    task_id=task_id,
                    revision_number=revision_summary.revision_number,
                    revision_status=revision_summary.revision_status.value,
                    started_at=now,
                    finished_at=None,
                    requirement_detail_json=None,
                ),
                ip_hash=ip_hash,
                created_at=now,
            )
            session.commit()
        except IntegrityError:
            session.rollback()
            raise ApiError(
                status_code=409,
                code="resource_busy",
                message="当前已有研究任务在执行，请稍后再试。",
            ) from None

        return CreateTaskResponse(
            task_id=task_id,
            task_token=task_token,
            trace_id=trace_id,
            snapshot=snapshot,
            urls=TaskUrls(
                events=f"/api/v1/tasks/{task_id}/events",
                heartbeat=f"/api/v1/tasks/{task_id}/heartbeat",
                disconnect=f"/api/v1/tasks/{task_id}/disconnect",
            ),
            connect_deadline_at=connect_deadline_at,
        )

    def get_task_detail(
        self,
        session: Session,
        *,
        task_id: str,
        token: str,
    ) -> tuple[str, TaskDetailResponse]:
        task_with_revision = self.repository.get_task_with_revision(
            session=session,
            task_id=task_id,
        )
        if task_with_revision is None:
            raise ApiError(
                status_code=404,
                code="task_not_found",
                message="任务不存在或已清理。",
            )

        task, revision = task_with_revision
        self._validate_task_token(
            task_id=task_id,
            token=token,
            token_hash=task.task_token_hash,
        )
        return task.trace_id, self.repository.build_task_detail_response(
            task=task,
            revision=revision,
        )

    def get_task_for_token(
        self,
        session: Session,
        *,
        task_id: str,
        token: str,
    ) -> ResearchTaskRecord:
        task = self.repository.get_task(session=session, task_id=task_id)
        if task is None:
            raise ApiError(
                status_code=404,
                code="task_not_found",
                message="任务不存在或已清理。",
            )

        self._validate_task_token(
            task_id=task_id,
            token=token,
            token_hash=task.task_token_hash,
        )
        return task

    def ensure_task_created_event(
        self,
        session: Session,
        *,
        task_id: str,
    ) -> EventEnvelope | None:
        task = self.repository.get_task(session=session, task_id=task_id)
        if task is None or self.repository.has_events(session=session, task_id=task_id):
            return None

        snapshot = self.repository.build_snapshot(task=task)
        return self.repository.append_event(
            session=session,
            task_id=task.task_id,
            revision_id=task.active_revision_id,
            event="task.created",
            phase=task.phase,
            payload={"snapshot": snapshot.model_dump(mode="json")},
            created_at=self.clock(),
        )

    def list_events_after(
        self,
        session: Session,
        *,
        task_id: str,
        after_seq: int,
    ) -> list[EventEnvelope]:
        return self.repository.list_events_after(
            session=session,
            task_id=task_id,
            after_seq=after_seq,
        )

    def accept_client_heartbeat(
        self,
        session: Session,
        *,
        task_id: str,
        token: str,
    ) -> str:
        task = self.get_task_for_token(session, task_id=task_id, token=token)
        if TaskStatus(task.status) not in {
            TaskStatus.RUNNING,
            TaskStatus.AWAITING_USER_INPUT,
            TaskStatus.AWAITING_FEEDBACK,
        }:
            raise ApiError(
                status_code=409,
                code="invalid_task_state",
                message="当前任务状态不接受 heartbeat。",
                trace_id=task.trace_id,
            )
        return task.trace_id

    def emit_server_heartbeat(
        self,
        session: Session,
        *,
        task_id: str,
    ) -> EventEnvelope | None:
        task = self.repository.get_task(session=session, task_id=task_id)
        if task is None:
            return None

        if TaskStatus(task.status) not in {
            TaskStatus.RUNNING,
            TaskStatus.AWAITING_USER_INPUT,
            TaskStatus.AWAITING_FEEDBACK,
        }:
            return None

        now = self.clock()
        return self.repository.append_event(
            session=session,
            task_id=task.task_id,
            revision_id=task.active_revision_id,
            event="heartbeat",
            phase=task.phase,
            payload={"server_time": now.isoformat().replace("+00:00", "Z")},
            created_at=now,
        )

    def transition_phase(
        self,
        session: Session,
        *,
        task_id: str,
        target_phase: TaskPhase,
    ) -> EventEnvelope:
        task = self.repository.get_task(session=session, task_id=task_id)
        if task is None:
            raise ApiError(
                status_code=404,
                code="task_not_found",
                message="任务不存在或已清理。",
            )

        current_state = TaskLifecycleState(
            status=TaskStatus(task.status),
            phase=TaskPhase(task.phase),
        )
        target_state = TaskStateMachine.transition(
            current=current_state,
            target=TaskLifecycleState(
                status=TaskStatus.RUNNING,
                phase=target_phase,
            ),
        )
        now = self.clock()
        self.repository.update_task_state(
            session=session,
            task_id=task_id,
            status=target_state.status.value,
            phase=target_state.phase.value,
            updated_at=now,
        )
        return self.repository.append_event(
            session=session,
            task_id=task_id,
            revision_id=task.active_revision_id,
            event="phase.changed",
            phase=target_state.phase.value,
            payload={
                "from_phase": current_state.phase.value,
                "to_phase": target_state.phase.value,
                "status": target_state.status.value,
            },
            created_at=now,
        )

    def fail_task(
        self,
        session: Session,
        *,
        task_id: str,
        error_code: str,
        message: str,
    ) -> EventEnvelope | None:
        task = self.repository.get_task(session=session, task_id=task_id)
        if task is None:
            return None

        if TaskStatus(task.status) in {
            TaskStatus.FAILED,
            TaskStatus.TERMINATED,
            TaskStatus.EXPIRED,
            TaskStatus.PURGED,
        }:
            return None

        current_state = TaskLifecycleState(
            status=TaskStatus(task.status),
            phase=TaskPhase(task.phase),
        )
        target_state = TaskStateMachine.transition(
            current=current_state,
            target=TaskLifecycleState(
                status=TaskStatus.FAILED,
                phase=current_state.phase,
            ),
        )
        now = self.clock()
        self.repository.update_task_state(
            session=session,
            task_id=task_id,
            status=target_state.status.value,
            phase=target_state.phase.value,
            updated_at=now,
        )
        self.repository.release_lock(session=session, task_id=task_id)
        self.repository.update_revision_status(
            session=session,
            revision_id=task.active_revision_id,
            revision_status=RevisionStatus.FAILED.value,
            finished_at=now,
        )
        return self.repository.append_event(
            session=session,
            task_id=task.task_id,
            revision_id=task.active_revision_id,
            event="task.failed",
            phase=target_state.phase.value,
            payload={"error": {"code": error_code, "message": message}},
            created_at=now,
        )

    def disconnect_task(
        self,
        session: Session,
        *,
        task_id: str,
        token: str,
    ) -> tuple[str, AcceptedResponse]:
        task = self.get_task_for_token(session, task_id=task_id, token=token)
        self.terminate_task(
            session,
            task_id=task_id,
            reason="sendbeacon_received",
        )
        return task.trace_id, AcceptedResponse(accepted=True)

    def terminate_task(
        self,
        session: Session,
        *,
        task_id: str,
        reason: str,
    ) -> EventEnvelope | None:
        task = self.repository.get_task(session=session, task_id=task_id)
        if task is None:
            return None

        current_status = TaskStatus(task.status)
        if current_status in {
            TaskStatus.TERMINATED,
            TaskStatus.FAILED,
            TaskStatus.EXPIRED,
            TaskStatus.PURGED,
        }:
            return None

        current_state = TaskLifecycleState(
            status=current_status,
            phase=TaskPhase(task.phase),
        )
        target_state = TaskStateMachine.transition(
            current=current_state,
            target=TaskLifecycleState(
                status=TaskStatus.TERMINATED,
                phase=current_state.phase,
            ),
        )
        now = self.clock()
        self.repository.update_task_state(
            session=session,
            task_id=task_id,
            status=target_state.status.value,
            phase=target_state.phase.value,
            updated_at=now,
        )
        self.repository.release_lock(session=session, task_id=task_id)
        if current_status is not TaskStatus.AWAITING_FEEDBACK:
            self.repository.update_revision_status(
                session=session,
                revision_id=task.active_revision_id,
                revision_status=RevisionStatus.TERMINATED.value,
                finished_at=now,
            )
        return self.repository.append_event(
            session=session,
            task_id=task.task_id,
            revision_id=task.active_revision_id,
            event="task.terminated",
            phase=target_state.phase.value,
            payload={"reason": reason},
            created_at=now,
        )

    def expire_task(
        self,
        session: Session,
        *,
        task_id: str,
    ) -> EventEnvelope | None:
        task = self.repository.get_task(session=session, task_id=task_id)
        if task is None:
            return None

        if TaskStatus(task.status) is not TaskStatus.AWAITING_FEEDBACK:
            return None

        current_state = TaskLifecycleState(
            status=TaskStatus(task.status),
            phase=TaskPhase(task.phase),
        )
        target_state = TaskStateMachine.transition(
            current=current_state,
            target=TaskLifecycleState(
                status=TaskStatus.EXPIRED,
                phase=TaskPhase.DELIVERED,
            ),
        )
        now = self.clock()
        self.repository.update_task_state(
            session=session,
            task_id=task_id,
            status=target_state.status.value,
            phase=target_state.phase.value,
            updated_at=now,
            expires_at=now,
        )
        self.repository.release_lock(session=session, task_id=task_id)
        return self.repository.append_event(
            session=session,
            task_id=task.task_id,
            revision_id=task.active_revision_id,
            event="task.expired",
            phase=target_state.phase.value,
            payload={"expired_at": now.isoformat().replace("+00:00", "Z")},
            created_at=now,
        )

    def _validate_task_token(
        self,
        *,
        task_id: str,
        token: str,
        token_hash: str,
    ) -> None:
        try:
            payload = self.task_token_signer.verify(token)
        except TokenVerificationError as exc:
            raise ApiError(
                status_code=401,
                code="task_token_invalid",
                message="任务 token 无效或不匹配。",
            ) from exc

        if payload.task_id != task_id or hash_secret(token) != token_hash:
            raise ApiError(
                status_code=401,
                code="task_token_invalid",
                message="任务 token 无效或不匹配。",
            )
