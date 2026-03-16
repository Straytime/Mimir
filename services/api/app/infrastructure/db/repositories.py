from datetime import UTC, datetime
from typing import Final

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.application.dto.tasks import TaskDetailResponse
from app.domain.enums import (
    AvailableAction,
    ClarificationMode,
    RevisionStatus,
    TaskPhase,
    TaskStatus,
)
from app.domain.schemas import EventEnvelope, RequirementDetail, RevisionSummary, TaskSnapshot
from app.infrastructure.db.models import (
    IPUsageCounterRecord,
    ResearchTaskRecord,
    SystemLockRecord,
    TaskEventRecord,
    TaskRevisionRecord,
)


_UNSET: Final = object()


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

    def get_task(
        self,
        *,
        session: Session,
        task_id: str,
        for_update: bool = False,
    ) -> ResearchTaskRecord | None:
        statement = select(ResearchTaskRecord).where(ResearchTaskRecord.task_id == task_id)
        if for_update:
            statement = statement.with_for_update()
        return session.scalar(statement)

    def get_revision(
        self,
        *,
        session: Session,
        revision_id: str,
    ) -> TaskRevisionRecord | None:
        return session.get(TaskRevisionRecord, revision_id)

    def release_lock(self, *, session: Session, task_id: str) -> None:
        session.execute(
            delete(SystemLockRecord).where(SystemLockRecord.task_id == task_id)
        )
        session.flush()

    def update_task_state(
        self,
        *,
        session: Session,
        task_id: str,
        status: str,
        phase: str,
        updated_at: datetime,
        expires_at: datetime | None | object = _UNSET,
    ) -> ResearchTaskRecord | None:
        task = self.get_task(session=session, task_id=task_id, for_update=True)
        if task is None:
            return None

        task.status = status
        task.phase = phase
        task.updated_at = updated_at
        if expires_at is not _UNSET:
            task.expires_at = expires_at
        session.flush()
        return task

    def update_task_clarification_mode(
        self,
        *,
        session: Session,
        task_id: str,
        clarification_mode: str,
    ) -> ResearchTaskRecord | None:
        task = self.get_task(session=session, task_id=task_id, for_update=True)
        if task is None:
            return None

        task.clarification_mode = clarification_mode
        session.flush()
        return task

    def update_revision_status(
        self,
        *,
        session: Session,
        revision_id: str,
        revision_status: str,
        finished_at: datetime | None | object = _UNSET,
    ) -> TaskRevisionRecord | None:
        revision = self.get_revision(session=session, revision_id=revision_id)
        if revision is None:
            return None

        revision.revision_status = revision_status
        if finished_at is not _UNSET:
            revision.finished_at = finished_at
        session.flush()
        return revision

    def update_revision_requirement_detail(
        self,
        *,
        session: Session,
        revision_id: str,
        requirement_detail_json: dict[str, object],
    ) -> TaskRevisionRecord | None:
        revision = self.get_revision(session=session, revision_id=revision_id)
        if revision is None:
            return None

        revision.requirement_detail_json = requirement_detail_json
        session.flush()
        return revision

    def list_events_after(
        self,
        *,
        session: Session,
        task_id: str,
        after_seq: int,
    ) -> list[EventEnvelope]:
        records = list(
            session.scalars(
                select(TaskEventRecord)
                .where(TaskEventRecord.task_id == task_id)
                .where(TaskEventRecord.seq > after_seq)
                .order_by(TaskEventRecord.seq.asc())
            )
        )
        return [self.build_event_envelope(record=record) for record in records]

    def has_events(self, *, session: Session, task_id: str) -> bool:
        return (
            session.scalar(
                select(func.count())
                .select_from(TaskEventRecord)
                .where(TaskEventRecord.task_id == task_id)
            )
            or 0
        ) > 0

    def append_event(
        self,
        *,
        session: Session,
        task_id: str,
        revision_id: str | None,
        event: str,
        phase: str,
        payload: dict[str, object],
        created_at: datetime,
    ) -> EventEnvelope:
        task = self.get_task(session=session, task_id=task_id, for_update=True)
        if task is None:
            raise LookupError(f"Task {task_id} not found")

        next_seq = (
            session.scalar(
                select(func.coalesce(func.max(TaskEventRecord.seq), 0) + 1).where(
                    TaskEventRecord.task_id == task_id
                )
            )
            or 1
        )
        record = TaskEventRecord(
            task_id=task_id,
            seq=int(next_seq),
            event=event,
            revision_id=revision_id,
            phase=phase,
            payload_json=payload,
            created_at=created_at,
        )
        session.add(record)
        session.flush()
        return self.build_event_envelope(record=record)

    def build_task_detail_response(
        self,
        *,
        task: ResearchTaskRecord,
        revision: TaskRevisionRecord,
    ) -> TaskDetailResponse:
        requirement_detail = None
        if revision.requirement_detail_json is not None:
            requirement_detail = RequirementDetail.model_validate(
                revision.requirement_detail_json
            ).model_dump(
                mode="json",
                exclude={"raw_llm_output"},
            )

        return TaskDetailResponse(
            task_id=task.task_id,
            snapshot=self.build_snapshot(task=task),
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

    def build_snapshot(self, *, task: ResearchTaskRecord) -> TaskSnapshot:
        status = TaskStatus(task.status)
        phase = TaskPhase(task.phase)
        return TaskSnapshot(
            task_id=task.task_id,
            status=status,
            phase=phase,
            active_revision_id=task.active_revision_id,
            active_revision_number=task.active_revision_number,
            clarification_mode=ClarificationMode(task.clarification_mode),
            created_at=_as_utc(task.created_at),
            updated_at=_as_utc(task.updated_at),
            expires_at=_as_utc(task.expires_at),
            available_actions=_available_actions_for(status=status, phase=phase),
        )

    def build_event_envelope(self, *, record: TaskEventRecord) -> EventEnvelope:
        return EventEnvelope(
            seq=record.seq,
            event=record.event,
            task_id=record.task_id,
            revision_id=record.revision_id,
            phase=TaskPhase(record.phase),
            timestamp=_as_utc(record.created_at),
            payload=record.payload_json,
        )


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.astimezone(UTC)


def _available_actions_for(
    *,
    status: TaskStatus,
    phase: TaskPhase,
) -> list[AvailableAction]:
    if status is TaskStatus.AWAITING_USER_INPUT and phase is TaskPhase.CLARIFYING:
        return [AvailableAction.SUBMIT_CLARIFICATION]

    if status is TaskStatus.AWAITING_FEEDBACK and phase is TaskPhase.DELIVERED:
        return [
            AvailableAction.SUBMIT_FEEDBACK,
            AvailableAction.DOWNLOAD_MARKDOWN,
            AvailableAction.DOWNLOAD_PDF,
        ]

    return []
