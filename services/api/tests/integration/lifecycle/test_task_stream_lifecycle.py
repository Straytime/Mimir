import asyncio
from datetime import timedelta

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.enums import TaskPhase
from app.infrastructure.db.models import ResearchTaskRecord, SystemLockRecord, TaskEventRecord
from tests.contract.rest.test_task_events import assert_stream_closed, read_sse_event, read_until_event
from tests.contract.rest.test_tasks import build_create_task_payload
from tests.fixtures.runtime import FakeClock


def count_task_events(db_session: Session, task_id: str) -> int:
    db_session.expire_all()
    return db_session.scalar(
        select(func.count()).select_from(TaskEventRecord).where(TaskEventRecord.task_id == task_id)
    ) or 0


@pytest.mark.asyncio
async def test_no_events_are_persisted_until_first_sse_connection(
    app_client: AsyncClient,
    db_session: Session,
) -> None:
    create_response = await app_client.post("/api/v1/tasks", json=build_create_task_payload())
    create_body = create_response.json()

    assert count_task_events(db_session, create_body["task_id"]) == 0

    async with app_client.stream(
        "GET",
        f"/api/v1/tasks/{create_body['task_id']}/events",
        headers={"Authorization": f"Bearer {create_body['task_token']}"},
    ) as response:
        lines = response.aiter_lines()
        _, event_name, _ = await read_sse_event(lines)
        assert event_name == "task.created"

        await asyncio.sleep(0.1)
        assert count_task_events(db_session, create_body["task_id"]) >= 1


@pytest.mark.asyncio
async def test_connect_deadline_without_first_sse_connection_terminates_task(
    app_client: AsyncClient,
    db_session: Session,
    fake_clock: FakeClock,
) -> None:
    create_response = await app_client.post("/api/v1/tasks", json=build_create_task_payload())
    create_body = create_response.json()

    fake_clock.advance(seconds=11)
    await asyncio.sleep(0.1)
    db_session.expire_all()

    events = list(
        db_session.scalars(
            select(TaskEventRecord)
            .where(TaskEventRecord.task_id == create_body["task_id"])
            .order_by(TaskEventRecord.seq.asc())
        )
    )
    lock = db_session.get(SystemLockRecord, "global_active_task")
    task = db_session.get(ResearchTaskRecord, create_body["task_id"])

    assert [event.event for event in events] == ["task.terminated"]
    assert events[0].seq == 1
    assert events[0].payload_json == {"reason": "sse_connect_timeout"}
    assert lock is None
    assert task is not None
    assert task.status == "terminated"


@pytest.mark.asyncio
async def test_phase_changed_then_failed_keeps_terminal_event_last(
    app_client: AsyncClient,
    app_instance: FastAPI,
) -> None:
    create_response = await app_client.post("/api/v1/tasks", json=build_create_task_payload())
    create_body = create_response.json()

    async with app_client.stream(
        "GET",
        f"/api/v1/tasks/{create_body['task_id']}/events",
        headers={"Authorization": f"Bearer {create_body['task_token']}"},
    ) as response:
        lines = response.aiter_lines()
        await read_sse_event(lines)

        await app_instance.state.task_lifecycle.transition_phase(
            task_id=create_body["task_id"],
            target_phase=TaskPhase.ANALYZING_REQUIREMENT,
        )
        phase_event_id, phase_event_name, phase_payload = await read_until_event(
            lines,
            {"phase.changed"},
        )

        await app_instance.state.task_lifecycle.fail_task(
            task_id=create_body["task_id"],
            error_code="upstream_service_error",
            message="上游服务异常",
        )
        event_id, failed_event_name, failed_payload = await read_until_event(lines, {"task.failed"})
        await assert_stream_closed(lines)

    assert phase_event_name == "phase.changed"
    assert phase_payload["payload"] == {
        "from_phase": "clarifying",
        "to_phase": "analyzing_requirement",
        "status": "running",
    }
    assert int(event_id or "0") > int(phase_event_id or "0")
    assert failed_event_name == "task.failed"
    assert failed_payload["payload"] == {
        "error": {"code": "upstream_service_error", "message": "上游服务异常"}
    }


@pytest.mark.asyncio
async def test_heartbeat_timeout_terminates_connected_task(
    app_client: AsyncClient,
    fake_clock: FakeClock,
) -> None:
    create_response = await app_client.post("/api/v1/tasks", json=build_create_task_payload())
    create_body = create_response.json()

    async with app_client.stream(
        "GET",
        f"/api/v1/tasks/{create_body['task_id']}/events",
        headers={"Authorization": f"Bearer {create_body['task_token']}"},
    ) as response:
        lines = response.aiter_lines()
        await read_sse_event(lines)

        fake_clock.advance(seconds=46)
        await asyncio.sleep(0.1)
        _, event_name, payload = await read_until_event(lines, {"task.terminated"})
        await assert_stream_closed(lines)

    assert event_name == "task.terminated"
    assert payload["payload"] == {"reason": "heartbeat_timeout"}


@pytest.mark.asyncio
async def test_task_expired_is_last_event_for_awaiting_feedback_task(
    app_client: AsyncClient,
    db_session: Session,
    fake_clock: FakeClock,
) -> None:
    create_response = await app_client.post("/api/v1/tasks", json=build_create_task_payload())
    create_body = create_response.json()

    task = db_session.get(ResearchTaskRecord, create_body["task_id"])
    assert task is not None
    task.status = "awaiting_feedback"
    task.phase = "delivered"
    task.expires_at = fake_clock.now() + timedelta(seconds=5)
    task.updated_at = fake_clock.now()
    db_session.commit()

    async with app_client.stream(
        "GET",
        f"/api/v1/tasks/{create_body['task_id']}/events",
        headers={"Authorization": f"Bearer {create_body['task_token']}"},
    ) as response:
        lines = response.aiter_lines()
        await read_sse_event(lines)

        fake_clock.advance(seconds=6)
        await asyncio.sleep(0.1)
        event_id, event_name, payload = await read_sse_event(lines)
        await assert_stream_closed(lines)

    assert event_id == "2"
    assert event_name == "task.expired"
    assert payload["phase"] == "delivered"
    assert payload["payload"]["expired_at"] == fake_clock.now().isoformat().replace("+00:00", "Z")
