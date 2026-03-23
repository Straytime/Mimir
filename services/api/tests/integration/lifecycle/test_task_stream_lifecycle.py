import asyncio
from datetime import timedelta

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.enums import TaskPhase
from app.infrastructure.db.models import ResearchTaskRecord, SystemLockRecord, TaskEventRecord, TaskRevisionRecord
from tests.contract.rest.test_task_events import assert_stream_closed, read_sse_event, read_until_event
from tests.contract.rest.test_tasks import build_create_task_payload
from tests.fixtures.runtime import FakeClock


def count_task_events(db_session: Session, task_id: str) -> int:
    db_session.expire_all()
    return db_session.scalar(
        select(func.count()).select_from(TaskEventRecord).where(TaskEventRecord.task_id == task_id)
    ) or 0


@pytest.mark.asyncio
async def test_task_created_event_is_persisted_before_first_sse_connection(
    app_client: AsyncClient,
    db_session: Session,
) -> None:
    create_response = await app_client.post("/api/v1/tasks", json=build_create_task_payload())
    create_body = create_response.json()

    db_session.expire_all()
    events = list(
        db_session.scalars(
            select(TaskEventRecord)
            .where(TaskEventRecord.task_id == create_body["task_id"])
            .order_by(TaskEventRecord.seq.asc())
        )
    )
    assert events
    assert events[0].event == "task.created"

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
async def test_task_remains_alive_without_first_sse_connection_after_connect_deadline(
    app_client: AsyncClient,
    db_session: Session,
    fake_clock: FakeClock,
) -> None:
    create_response = await app_client.post("/api/v1/tasks", json=build_create_task_payload())
    create_body = create_response.json()

    fake_clock.advance(seconds=11)
    await asyncio.sleep(0.1)
    db_session.expire_all()

    lock = db_session.get(SystemLockRecord, "global_active_task")
    task = db_session.get(ResearchTaskRecord, create_body["task_id"])
    assert task is not None
    assert task.status in {"running", "awaiting_user_input"}
    assert lock is not None
    assert lock.task_id == create_body["task_id"]

    terminated_events = list(
        db_session.scalars(
            select(TaskEventRecord)
            .where(
                TaskEventRecord.task_id == create_body["task_id"],
                TaskEventRecord.event == "task.terminated",
            )
            .order_by(TaskEventRecord.seq.asc())
        )
    )
    assert terminated_events == []


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
async def test_missing_heartbeat_does_not_terminate_connected_task(
    app_client: AsyncClient,
    db_session: Session,
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
        _, event_name, payload = await read_until_event(lines, {"heartbeat"})

        db_session.expire_all()
        task = db_session.get(ResearchTaskRecord, create_body["task_id"])
        assert task is not None
        assert task.status in {"running", "awaiting_user_input"}
        terminated_events = list(
            db_session.scalars(
                select(TaskEventRecord)
                .where(
                    TaskEventRecord.task_id == create_body["task_id"],
                    TaskEventRecord.event == "task.terminated",
                )
                .order_by(TaskEventRecord.seq.asc())
            )
        )
        assert terminated_events == []

    assert event_name == "heartbeat"
    assert payload["task_id"] == create_body["task_id"]


@pytest.mark.asyncio
async def test_closing_sse_stream_does_not_terminate_active_task(
    app_client: AsyncClient,
    db_session: Session,
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

    await asyncio.sleep(0.1)
    db_session.expire_all()
    task = db_session.get(ResearchTaskRecord, create_body["task_id"])
    assert task is not None
    assert task.status in {"running", "awaiting_user_input"}

    terminated_events = list(
        db_session.scalars(
            select(TaskEventRecord)
            .where(
                TaskEventRecord.task_id == create_body["task_id"],
                TaskEventRecord.event == "task.terminated",
            )
            .order_by(TaskEventRecord.seq.asc())
        )
    )
    assert terminated_events == []


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
        event_id, event_name, payload = await read_until_event(lines, {"task.expired"})
        await assert_stream_closed(lines)

    assert int(event_id or "0") >= 2
    assert event_name == "task.expired"
    assert payload["phase"] == "delivered"
    assert payload["payload"]["expired_at"] == fake_clock.now().isoformat().replace("+00:00", "Z")


@pytest.mark.asyncio
async def test_submit_clarification_refreshes_last_client_seen_at(
    app_client: AsyncClient,
    app_instance: FastAPI,
    fake_clock: FakeClock,
) -> None:
    create_response = await app_client.post(
        "/api/v1/tasks",
        json=build_create_task_payload(clarification_mode="natural"),
    )
    create_body = create_response.json()
    task_id = create_body["task_id"]

    async with app_client.stream(
        "GET",
        f"/api/v1/tasks/{task_id}/events",
        headers={"Authorization": f"Bearer {create_body['task_token']}"},
    ) as response:
        lines = response.aiter_lines()
        await read_until_event(lines, {"clarification.natural.ready"})

        lifecycle = app_instance.state.task_lifecycle
        runtime = lifecycle._runtimes.get(task_id)
        assert runtime is not None
        before = runtime.last_client_seen_at

        fake_clock.advance(seconds=10)

        await app_client.post(
            f"/api/v1/tasks/{task_id}/clarification",
            headers={"Authorization": f"Bearer {create_body['task_token']}"},
            json={
                "mode": "natural",
                "answer_text": "重点看中国市场。",
            },
        )

        after = runtime.last_client_seen_at
        assert after is not None
        assert before is not None
        assert after > before


@pytest.mark.asyncio
async def test_submit_feedback_refreshes_last_client_seen_at(
    app_client: AsyncClient,
    app_instance: FastAPI,
    db_session: Session,
    fake_clock: FakeClock,
) -> None:
    create_response = await app_client.post(
        "/api/v1/tasks",
        json=build_create_task_payload(clarification_mode="natural"),
    )
    create_body = create_response.json()
    task_id = create_body["task_id"]

    async with app_client.stream(
        "GET",
        f"/api/v1/tasks/{task_id}/events",
        headers={"Authorization": f"Bearer {create_body['task_token']}"},
    ) as response:
        lines = response.aiter_lines()
        await read_sse_event(lines)

        # Force task into awaiting_feedback state
        db_session.expire_all()
        task = db_session.get(ResearchTaskRecord, task_id)
        assert task is not None
        task.status = "awaiting_feedback"
        task.phase = "delivered"
        task.updated_at = fake_clock.now()
        task.expires_at = fake_clock.now() + timedelta(hours=24)

        revision = db_session.get(TaskRevisionRecord, task.active_revision_id)
        assert revision is not None
        revision.requirement_detail_json = {
            "research_goal": "test goal",
            "domain": "technology",
            "requirement_details": "test details",
            "output_format": "general",
            "freshness_requirement": "normal",
            "language": "zh-CN",
        }
        db_session.commit()

        lifecycle = app_instance.state.task_lifecycle
        runtime = lifecycle._runtimes.get(task_id)
        assert runtime is not None
        before = runtime.last_client_seen_at

        fake_clock.advance(seconds=10)

        feedback_response = await app_client.post(
            f"/api/v1/tasks/{task_id}/feedback",
            headers={"Authorization": f"Bearer {create_body['task_token']}"},
            json={"feedback_text": "请补充更多信息。"},
        )

        after = runtime.last_client_seen_at
        assert after is not None
        assert before is not None
        assert after > before
