import json
import re
from datetime import UTC, datetime
from typing import Final

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.application.dto.tasks import TaskDetailResponse
from app.application.dto.research import CollectedSourceItem, FormattedSource
from app.domain.enums import (
    AccessTokenResourceType,
    AvailableAction,
    ClarificationMode,
    RevisionStatus,
    TaskPhase,
    TaskStatus,
)
from app.domain.schemas import EventEnvelope, RequirementDetail, RevisionSummary, TaskSnapshot
from app.infrastructure.db.models import (
    AgentRunRecord,
    ArtifactRecord,
    CollectedSourceRecord,
    IPUsageCounterRecord,
    ResearchTaskRecord,
    SystemLockRecord,
    TaskToolCallRecord,
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

    def increment_collect_agent_calls_used(
        self,
        *,
        session: Session,
        revision_id: str,
        increment_by: int,
    ) -> TaskRevisionRecord | None:
        revision = self.get_revision(session=session, revision_id=revision_id)
        if revision is None:
            return None

        revision.collect_agent_calls_used += increment_by
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

    def append_agent_run(
        self,
        *,
        session: Session,
        task_id: str,
        revision_id: str,
        subtask_id: str | None,
        agent_type: str,
        prompt_name: str,
        status: str | None,
        reasoning_text: str | None,
        content_text: str | None,
        finish_reason: str | None,
        tool_calls_json: dict[str, object] | None,
        created_at: datetime,
        updated_at: datetime,
    ) -> AgentRunRecord:
        record = AgentRunRecord(
            task_id=task_id,
            revision_id=revision_id,
            subtask_id=subtask_id,
            agent_type=agent_type,
            prompt_name=prompt_name,
            status=status,
            reasoning_text=reasoning_text,
            content_text=content_text,
            finish_reason=finish_reason,
            tool_calls_json=tool_calls_json,
            compressed=False,
            created_at=created_at,
            updated_at=updated_at,
        )
        session.add(record)
        session.flush()
        return record

    def append_tool_call(
        self,
        *,
        session: Session,
        task_id: str,
        revision_id: str,
        subtask_id: str | None,
        tool_call_id: str | None,
        tool_name: str,
        status: str,
        error_code: str | None,
        request_json: dict[str, object],
        response_json: dict[str, object] | None,
        created_at: datetime,
    ) -> TaskToolCallRecord:
        record = TaskToolCallRecord(
            task_id=task_id,
            revision_id=revision_id,
            subtask_id=subtask_id,
            tool_call_id=tool_call_id,
            tool_name=tool_name,
            status=status,
            error_code=error_code,
            request_json=request_json,
            response_json=response_json,
            created_at=created_at,
        )
        session.add(record)
        session.flush()
        return record

    def append_collected_sources(
        self,
        *,
        session: Session,
        task_id: str,
        revision_id: str,
        subtask_id: str,
        tool_call_id: str,
        items: tuple[CollectedSourceItem, ...],
        created_at: datetime,
    ) -> None:
        for item in items:
            session.add(
                CollectedSourceRecord(
                    task_id=task_id,
                    revision_id=revision_id,
                    subtask_id=subtask_id,
                    tool_call_id=tool_call_id,
                    title=item.title,
                    link=item.link,
                    info=item.info,
                    source_key=_source_key(item.link),
                    refer=None,
                    is_merged=False,
                    created_at=created_at,
                )
            )
        session.flush()

    def list_collected_sources(
        self,
        *,
        session: Session,
        revision_id: str,
    ) -> list[CollectedSourceRecord]:
        records = list(
            session.scalars(
                select(CollectedSourceRecord)
                .where(CollectedSourceRecord.revision_id == revision_id)
                .where(CollectedSourceRecord.is_merged.is_(False))
                .order_by(CollectedSourceRecord.id.asc())
            )
        )
        return sorted(
            records,
            key=lambda record: (
                _natural_sort_key(record.tool_call_id),
                record.id,
            ),
        )

    def list_merged_sources(
        self,
        *,
        session: Session,
        revision_id: str,
    ) -> tuple[FormattedSource, ...]:
        records = list(
            session.scalars(
                select(CollectedSourceRecord)
                .where(CollectedSourceRecord.revision_id == revision_id)
                .where(CollectedSourceRecord.is_merged.is_(True))
                .order_by(CollectedSourceRecord.id.asc())
            )
        )
        return tuple(
            FormattedSource(
                refer=record.refer or "",
                title=record.title,
                link=record.link,
                info=record.info,
            )
            for record in records
            if record.refer is not None
        )

    def persist_merged_sources(
        self,
        *,
        session: Session,
        revision_id: str,
        merged_sources: tuple[FormattedSource, ...],
    ) -> None:
        raw_records = self.list_collected_sources(session=session, revision_id=revision_id)
        session.execute(
            delete(CollectedSourceRecord)
            .where(CollectedSourceRecord.revision_id == revision_id)
            .where(CollectedSourceRecord.is_merged.is_(True))
        )

        used_record_ids: set[int] = set()
        for merged_source in merged_sources:
            matching_record = next(
                (
                    record
                    for record in raw_records
                    if record.id not in used_record_ids
                    and record.source_key == _source_key(merged_source.link)
                ),
                None,
            )
            if matching_record is None:
                continue
            session.add(
                CollectedSourceRecord(
                    task_id=matching_record.task_id,
                    revision_id=matching_record.revision_id,
                    subtask_id=matching_record.subtask_id,
                    tool_call_id=matching_record.tool_call_id,
                    title=merged_source.title,
                    link=merged_source.link,
                    info=merged_source.info,
                    source_key=_source_key(merged_source.link),
                    refer=merged_source.refer,
                    is_merged=True,
                    created_at=matching_record.created_at,
                )
            )
            used_record_ids.add(matching_record.id)
        session.flush()

    def append_artifact(
        self,
        *,
        session: Session,
        artifact_id: str,
        task_id: str,
        revision_id: str,
        resource_type: str,
        filename: str,
        mime_type: str,
        storage_key: str,
        byte_size: int,
        metadata_json: dict[str, object] | None,
        created_at: datetime,
    ) -> ArtifactRecord:
        record = ArtifactRecord(
            artifact_id=artifact_id,
            task_id=task_id,
            revision_id=revision_id,
            resource_type=resource_type,
            filename=filename,
            mime_type=mime_type,
            storage_key=storage_key,
            byte_size=byte_size,
            metadata_json=metadata_json,
            created_at=created_at,
        )
        session.add(record)
        session.flush()
        return record

    def list_artifacts(
        self,
        *,
        session: Session,
        revision_id: str,
        resource_type: str | None = None,
    ) -> list[ArtifactRecord]:
        statement = select(ArtifactRecord).where(ArtifactRecord.revision_id == revision_id)
        if resource_type is not None:
            statement = statement.where(ArtifactRecord.resource_type == resource_type)
        statement = statement.order_by(ArtifactRecord.created_at.asc(), ArtifactRecord.artifact_id.asc())
        return list(session.scalars(statement))

    def get_artifact(
        self,
        *,
        session: Session,
        artifact_id: str,
    ) -> ArtifactRecord | None:
        return session.get(ArtifactRecord, artifact_id)

    def get_download_artifact(
        self,
        *,
        session: Session,
        revision_id: str,
        resource_type: AccessTokenResourceType,
    ) -> ArtifactRecord | None:
        return session.scalar(
            select(ArtifactRecord)
            .where(ArtifactRecord.revision_id == revision_id)
            .where(ArtifactRecord.resource_type == resource_type.value)
        )

    def build_task_detail_response(
        self,
        *,
        task: ResearchTaskRecord,
        revision: TaskRevisionRecord,
        delivery,
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
            delivery=delivery,
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


def _source_key(link: str) -> str:
    return link.strip().lower()


def _natural_sort_key(value: str | None) -> tuple[object, ...]:
    if value is None:
        return ("",)

    parts = re.split(r"(\d+)", value)
    normalized: list[object] = []
    for part in parts:
        if not part:
            continue
        if part.isdigit():
            normalized.append(int(part))
        else:
            normalized.append(part)
    return tuple(normalized)


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
