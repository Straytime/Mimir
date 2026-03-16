from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.errors import ApiError
from app.application.dto.tasks import (
    AcceptedResponse,
    ArtifactSummary,
    CreateTaskRequest,
    CreateTaskResponse,
    DeliverySummary,
    TaskDetailResponse,
    TaskUrls,
)
from app.application.policies.activity_lock import ActivityLockPolicy
from app.application.policies.ip_quota import IPQuotaPolicy
from app.application.ports.security import AccessTokenSigner, TaskTokenSigner
from app.core.config import Settings
from app.core.ids import generate_id, hash_secret
from app.domain.enums import (
    AccessTokenResourceType,
    ClarificationMode,
    RevisionStatus,
    TaskPhase,
    TaskStatus,
)
from app.domain.schemas import EventEnvelope, RequirementDetail, RevisionSummary, TaskSnapshot
from app.domain.state_machine import TaskLifecycleState, TaskStateMachine
from app.domain.tokens import AccessTokenPayload, TaskTokenPayload
from app.infrastructure.db.models import ArtifactRecord, ResearchTaskRecord, TaskRevisionRecord
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
            delivery=self._build_delivery_summary(
                session=session,
                task=task,
                revision=revision,
            ),
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

    def enter_awaiting_user_input(
        self,
        session: Session,
        *,
        task_id: str,
    ) -> TaskSnapshot:
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
        if current_state == TaskLifecycleState(
            status=TaskStatus.AWAITING_USER_INPUT,
            phase=TaskPhase.CLARIFYING,
        ):
            return self.repository.build_snapshot(task=task)

        target_state = TaskStateMachine.transition(
            current=current_state,
            target=TaskLifecycleState(
                status=TaskStatus.AWAITING_USER_INPUT,
                phase=TaskPhase.CLARIFYING,
            ),
        )
        now = self.clock()
        updated_task = self.repository.update_task_state(
            session=session,
            task_id=task_id,
            status=target_state.status.value,
            phase=target_state.phase.value,
            updated_at=now,
        )
        assert updated_task is not None
        return self.repository.build_snapshot(task=updated_task)

    def begin_requirement_analysis(
        self,
        session: Session,
        *,
        task_id: str,
        task: ResearchTaskRecord,
    ) -> TaskSnapshot:
        current_state = TaskLifecycleState(
            status=TaskStatus(task.status),
            phase=TaskPhase(task.phase),
        )
        if current_state != TaskLifecycleState(
            status=TaskStatus.AWAITING_USER_INPUT,
            phase=TaskPhase.CLARIFYING,
        ):
            raise ApiError(
                status_code=409,
                code="invalid_task_state",
                message="当前任务状态不允许提交澄清。",
                trace_id=task.trace_id,
            )

        target_state = TaskStateMachine.transition(
            current=current_state,
            target=TaskLifecycleState(
                status=TaskStatus.RUNNING,
                phase=TaskPhase.ANALYZING_REQUIREMENT,
            ),
        )
        now = self.clock()
        updated_task = self.repository.update_task_state(
            session=session,
            task_id=task_id,
            status=target_state.status.value,
            phase=target_state.phase.value,
            updated_at=now,
        )
        assert updated_task is not None
        self.repository.append_event(
            session=session,
            task_id=task.task_id,
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
        return self.repository.build_snapshot(task=updated_task)

    def update_clarification_mode(
        self,
        session: Session,
        *,
        task_id: str,
        clarification_mode: ClarificationMode,
    ) -> None:
        task = self.repository.update_task_clarification_mode(
            session=session,
            task_id=task_id,
            clarification_mode=clarification_mode.value,
        )
        if task is None:
            raise ApiError(
                status_code=404,
                code="task_not_found",
                message="任务不存在或已清理。",
            )

    def append_task_event(
        self,
        session: Session,
        *,
        task_id: str,
        event: str,
        payload: dict[str, object],
    ) -> EventEnvelope | None:
        task = self.repository.get_task(session=session, task_id=task_id)
        if task is None:
            return None

        if TaskStatus(task.status) in {
            TaskStatus.TERMINATED,
            TaskStatus.FAILED,
            TaskStatus.EXPIRED,
            TaskStatus.PURGED,
        }:
            return None

        return self.repository.append_event(
            session=session,
            task_id=task.task_id,
            revision_id=task.active_revision_id,
            event=event,
            phase=task.phase,
            payload=payload,
            created_at=self.clock(),
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

    def complete_requirement_analysis(
        self,
        session: Session,
        *,
        task_id: str,
        detail: RequirementDetail,
    ) -> EventEnvelope:
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
        now = self.clock()
        self.repository.update_task_state(
            session=session,
            task_id=task_id,
            status=task.status,
            phase=task.phase,
            updated_at=now,
        )
        self.repository.update_revision_requirement_detail(
            session=session,
            revision_id=revision.revision_id,
            requirement_detail_json=detail.model_dump(
                mode="json",
                exclude_none=True,
            ),
        )
        return self.repository.append_event(
            session=session,
            task_id=task.task_id,
            revision_id=task.active_revision_id,
            event="analysis.completed",
            phase=task.phase,
            payload={
                "requirement_detail": detail.model_dump(
                    mode="json",
                    exclude={"raw_llm_output"},
                )
            },
            created_at=now,
        )

    def complete_delivery(
        self,
        session: Session,
        *,
        task_id: str,
    ) -> EventEnvelope:
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
        current_state = TaskLifecycleState(
            status=TaskStatus(task.status),
            phase=TaskPhase(task.phase),
        )
        target_state = TaskStateMachine.transition(
            current=current_state,
            target=TaskLifecycleState(
                status=TaskStatus.AWAITING_FEEDBACK,
                phase=TaskPhase.DELIVERED,
            ),
        )
        now = self.clock()
        delivered_task = self.repository.update_task_state(
            session=session,
            task_id=task_id,
            status=target_state.status.value,
            phase=target_state.phase.value,
            updated_at=now,
            expires_at=now + timedelta(minutes=30),
        )
        assert delivered_task is not None
        self.repository.release_lock(session=session, task_id=task_id)
        updated_revision = self.repository.update_revision_status(
            session=session,
            revision_id=revision.revision_id,
            revision_status=RevisionStatus.COMPLETED.value,
            finished_at=now,
        )
        assert updated_revision is not None
        delivered_snapshot = self.repository.build_snapshot(task=delivered_task)
        delivery = self._build_delivery_summary(
            session=session,
            task=delivered_task,
            revision=updated_revision,
        )
        assert delivery is not None
        self.repository.append_event(
            session=session,
            task_id=task.task_id,
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
        self.repository.append_event(
            session=session,
            task_id=task.task_id,
            revision_id=task.active_revision_id,
            event="report.completed",
            phase=target_state.phase.value,
            payload={"delivery": delivery.model_dump(mode="json")},
            created_at=now,
        )
        return self.repository.append_event(
            session=session,
            task_id=task.task_id,
            revision_id=task.active_revision_id,
            event="task.awaiting_feedback",
            phase=target_state.phase.value,
            payload={
                "expires_at": (
                    delivered_snapshot.expires_at.isoformat().replace("+00:00", "Z")
                    if delivered_snapshot.expires_at is not None
                    else None
                ),
                "available_actions": [
                    action.value for action in delivered_snapshot.available_actions
                ],
            },
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

    def get_binary_resource(
        self,
        session: Session,
        *,
        task_id: str,
        access_token: str | None,
        resource_type: AccessTokenResourceType,
        artifact_id: str | None = None,
    ) -> tuple[str, ArtifactRecord]:
        task = self.repository.get_task(session=session, task_id=task_id)
        if task is None:
            raise ApiError(
                status_code=404,
                code="task_not_found",
                message="任务不存在或已清理。",
            )

        if resource_type is AccessTokenResourceType.ARTIFACT:
            if artifact_id is None:
                raise ApiError(
                    status_code=404,
                    code="task_not_found",
                    message="任务不存在或制品已清理。",
                )
            artifact = self.repository.get_artifact(session=session, artifact_id=artifact_id)
            if artifact is None or artifact.task_id != task_id:
                raise ApiError(
                    status_code=404,
                    code="task_not_found",
                    message="任务不存在或制品已清理。",
                )
        else:
            artifact = self.repository.get_download_artifact(
                session=session,
                revision_id=task.active_revision_id,
                resource_type=resource_type,
            )
            if artifact is None:
                raise ApiError(
                    status_code=404,
                    code="task_not_found",
                    message="任务不存在或制品已清理。",
                )

        self._validate_access_token(
            task_id=task_id,
            access_token=access_token,
            resource_type=resource_type,
            resource_scope=artifact.artifact_id,
        )
        return task.trace_id, artifact

    def build_artifact_summary(
        self,
        *,
        task: ResearchTaskRecord,
        artifact: ArtifactRecord,
    ) -> ArtifactSummary:
        access_expires_at = self._access_token_expires_at(task=task)
        access_token = self.access_token_signer.sign(
            AccessTokenPayload(
                task_id=task.task_id,
                resource_type=AccessTokenResourceType.ARTIFACT,
                resource_scope=artifact.artifact_id,
                issued_at=self.clock(),
                expires_at=access_expires_at,
            )
        )
        return ArtifactSummary(
            artifact_id=artifact.artifact_id,
            filename=artifact.filename,
            mime_type=artifact.mime_type,
            url=(
                f"/api/v1/tasks/{task.task_id}/artifacts/{artifact.artifact_id}"
                f"?access_token={access_token}"
            ),
            access_expires_at=access_expires_at,
        )

    def build_download_url(
        self,
        *,
        task: ResearchTaskRecord,
        artifact: ArtifactRecord,
        resource_type: AccessTokenResourceType,
    ) -> str:
        access_token = self.access_token_signer.sign(
            AccessTokenPayload(
                task_id=task.task_id,
                resource_type=resource_type,
                resource_scope=artifact.artifact_id,
                issued_at=self.clock(),
                expires_at=self._access_token_expires_at(task=task),
            )
        )
        if resource_type is AccessTokenResourceType.MARKDOWN_DOWNLOAD:
            return f"/api/v1/tasks/{task.task_id}/downloads/markdown.zip?access_token={access_token}"
        return f"/api/v1/tasks/{task.task_id}/downloads/report.pdf?access_token={access_token}"

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

    def _validate_access_token(
        self,
        *,
        task_id: str,
        access_token: str | None,
        resource_type: AccessTokenResourceType,
        resource_scope: str,
    ) -> None:
        if access_token is None:
            raise ApiError(
                status_code=401,
                code="access_token_invalid",
                message="access token 无效或已过期。",
            )
        try:
            payload = self.access_token_signer.verify(access_token)
        except TokenVerificationError as exc:
            raise ApiError(
                status_code=401,
                code="access_token_invalid",
                message="access token 无效或已过期。",
            ) from exc

        if (
            payload.task_id != task_id
            or payload.resource_type is not resource_type
            or payload.resource_scope != resource_scope
        ):
            raise ApiError(
                status_code=401,
                code="access_token_invalid",
                message="access token 无效或已过期。",
            )

    def _build_delivery_summary(
        self,
        *,
        session: Session,
        task: ResearchTaskRecord,
        revision: TaskRevisionRecord,
    ) -> DeliverySummary | None:
        markdown_artifact = self.repository.get_download_artifact(
            session=session,
            revision_id=revision.revision_id,
            resource_type=AccessTokenResourceType.MARKDOWN_DOWNLOAD,
        )
        pdf_artifact = self.repository.get_download_artifact(
            session=session,
            revision_id=revision.revision_id,
            resource_type=AccessTokenResourceType.PDF_DOWNLOAD,
        )
        if markdown_artifact is None or pdf_artifact is None:
            return None

        image_artifacts = self.repository.list_artifacts(
            session=session,
            revision_id=revision.revision_id,
            resource_type=AccessTokenResourceType.ARTIFACT.value,
        )
        metadata = markdown_artifact.metadata_json or {}
        word_count = int(metadata.get("word_count", 0))
        return DeliverySummary(
            revision_id=revision.revision_id,
            revision_number=revision.revision_number,
            word_count=word_count,
            artifact_count=len(image_artifacts),
            markdown_zip_url=self.build_download_url(
                task=task,
                artifact=markdown_artifact,
                resource_type=AccessTokenResourceType.MARKDOWN_DOWNLOAD,
            ),
            pdf_url=self.build_download_url(
                task=task,
                artifact=pdf_artifact,
                resource_type=AccessTokenResourceType.PDF_DOWNLOAD,
            ),
            artifacts=[
                self.build_artifact_summary(task=task, artifact=artifact)
                for artifact in image_artifacts
            ],
        )

    def _access_token_expires_at(self, *, task: ResearchTaskRecord) -> datetime:
        now = self.clock()
        default_expiry = now + timedelta(minutes=self.settings.access_token_ttl_minutes)
        if task.expires_at is None:
            return default_expiry
        return min(default_expiry, task.expires_at.astimezone(UTC))
