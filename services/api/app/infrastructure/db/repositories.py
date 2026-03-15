from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.application.dto.tasks import TaskDetailResponse
from app.domain.enums import ClarificationMode, RevisionStatus, TaskPhase, TaskStatus
from app.domain.schemas import RevisionSummary, TaskSnapshot
from app.infrastructure.db.models import (
    IPUsageCounterRecord,
    ResearchTaskRecord,
    SystemLockRecord,
    TaskRevisionRecord,
)


class TaskRepository:
    def get_active_lock_holder(self, *, session: Session) -> str | None:
        return session.scalar(
            select(SystemLockRecord.task_id).where(
                SystemLockRecord.lock_name == "global_active_task"
            )
        )

    def list_ip_usage(
        self,
        *,
        session: Session,
        ip_hash: str,
        since: datetime,
    ) -> list[datetime]:
        return list(
            session.scalars(
                select(IPUsageCounterRecord.created_at)
                .where(IPUsageCounterRecord.ip_hash == ip_hash)
                .where(IPUsageCounterRecord.created_at >= since)
                .order_by(IPUsageCounterRecord.created_at.asc())
            )
        )

    def create_task(
        self,
        *,
        session: Session,
        task: ResearchTaskRecord,
        revision: TaskRevisionRecord,
        ip_hash: str,
        created_at: datetime,
    ) -> None:
        session.add(task)
        session.add(revision)
        session.add(
            SystemLockRecord(
                lock_name="global_active_task",
                task_id=task.task_id,
                acquired_at=created_at,
            )
        )
        session.add(IPUsageCounterRecord(ip_hash=ip_hash, created_at=created_at))
        session.flush()

    def get_task_with_revision(
        self,
        *,
        session: Session,
        task_id: str,
    ) -> tuple[ResearchTaskRecord, TaskRevisionRecord] | None:
        task = self.get_task(session=session, task_id=task_id)
        if task is None:
            return None

        revision = session.get(TaskRevisionRecord, task.active_revision_id)
        if revision is None:
            return None

        return task, revision

    def get_task(self, *, session: Session, task_id: str) -> ResearchTaskRecord | None:
        return session.get(ResearchTaskRecord, task_id)

    def terminate_task(
        self,
        *,
        session: Session,
        task_id: str,
        status: str,
        phase: str,
        updated_at: datetime,
    ) -> None:
        task = session.get(ResearchTaskRecord, task_id)
        if task is None:
            return

        task.status = status
        task.phase = phase
        task.updated_at = updated_at
        session.execute(
            delete(SystemLockRecord).where(SystemLockRecord.task_id == task_id)
        )
        session.flush()

    def build_task_detail_response(
        self,
        *,
        task: ResearchTaskRecord,
        revision: TaskRevisionRecord,
    ) -> TaskDetailResponse:
        requirement_detail = None
        if revision.requirement_detail_json is not None:
            requirement_detail = revision.requirement_detail_json

        return TaskDetailResponse(
            task_id=task.task_id,
            snapshot=TaskSnapshot(
                task_id=task.task_id,
                status=TaskStatus(task.status),
                phase=TaskPhase(task.phase),
                active_revision_id=task.active_revision_id,
                active_revision_number=task.active_revision_number,
                clarification_mode=ClarificationMode(task.clarification_mode),
                created_at=_as_utc(task.created_at),
                updated_at=_as_utc(task.updated_at),
                expires_at=_as_utc(task.expires_at),
                available_actions=[],
            ),
            current_revision=RevisionSummary(
                revision_id=revision.revision_id,
                revision_number=revision.revision_number,
                revision_status=RevisionStatus(revision.revision_status),
                started_at=_as_utc(revision.started_at),
                finished_at=_as_utc(revision.finished_at),
                requirement_detail=requirement_detail,
            ),
            delivery=None,
        )


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.astimezone(UTC)
