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
from app.domain.enums import ClarificationMode, RevisionStatus, TaskPhase, TaskStatus
from app.domain.schemas import RevisionSummary, TaskSnapshot
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

    def create_task(
        self,
        session: Session,
        *,
        payload: CreateTaskRequest,
        client_ip: str,
    ) -> CreateTaskResponse:
        now = datetime.now(UTC)
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
        self._validate_task_token(task_id=task_id, token=token, token_hash=task.task_token_hash)
        return task.trace_id, self.repository.build_task_detail_response(
            task=task,
            revision=revision,
        )

    def disconnect_task(
        self,
        session: Session,
        *,
        task_id: str,
        token: str,
    ) -> tuple[str, AcceptedResponse]:
        task = self.repository.get_task(session=session, task_id=task_id)
        if task is None:
            raise ApiError(
                status_code=404,
                code="task_not_found",
                message="任务不存在。",
            )

        self._validate_task_token(task_id=task_id, token=token, token_hash=task.task_token_hash)
        current_state = TaskLifecycleState(
            status=TaskStatus(task.status),
            phase=TaskPhase(task.phase),
        )
        target_state = current_state
        if current_state.status not in {
            TaskStatus.TERMINATED,
            TaskStatus.FAILED,
            TaskStatus.EXPIRED,
        }:
            target_state = TaskStateMachine.transition(
                current=current_state,
                target=TaskLifecycleState(
                    status=TaskStatus.TERMINATED,
                    phase=current_state.phase,
                ),
            )

        self.repository.terminate_task(
            session=session,
            task_id=task_id,
            status=target_state.status.value,
            phase=target_state.phase.value,
            updated_at=datetime.now(UTC),
        )
        session.commit()
        return task.trace_id, AcceptedResponse(accepted=True)

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
