import asyncio
import json
from datetime import timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.db.models import ResearchTaskRecord
from tests.contract.rest.test_tasks import build_create_task_payload
from tests.fixtures.tasks import seed_delivered_task
from tests.fixtures.runtime import FakeClock


async def _read_sse_event(lines) -> tuple[str | None, str | None, dict[str, object]]:
    event_id: str | None = None
    event_name: str | None = None
    data_lines: list[str] = []

    while True:
        line = await anext(lines)
        if line == "":
            payload = json.loads("".join(data_lines))
            return event_id, event_name, payload

        field, _, value = line.partition(":")
        value = value.lstrip()
        if field == "id":
            event_id = value
        elif field == "event":
            event_name = value
        elif field == "data":
            data_lines.append(value)


async def read_sse_event(lines, *, timeout: float = 1.0) -> tuple[str | None, str | None, dict[str, object]]:
    return await asyncio.wait_for(_read_sse_event(lines), timeout=timeout)


async def read_until_event(
    lines,
    expected_names: set[str],
    *,
    timeout: float = 1.0,
) -> tuple[str | None, str | None, dict[str, object]]:
    while True:
        event = await read_sse_event(lines, timeout=timeout)
        if event[1] in expected_names:
            return event


async def assert_stream_closed(lines, *, timeout: float = 0.5) -> None:
    with pytest.raises(StopAsyncIteration):
        await asyncio.wait_for(anext(lines), timeout=timeout)


@pytest.mark.asyncio
async def test_get_events_streams_task_created_on_first_connect(
    app_client: AsyncClient,
) -> None:
    create_response = await app_client.post("/api/v1/tasks", json=build_create_task_payload())
    create_body = create_response.json()

    async with app_client.stream(
        "GET",
        f"/api/v1/tasks/{create_body['task_id']}/events",
        headers={
            "Authorization": f"Bearer {create_body['task_token']}",
            "Accept": "text/event-stream",
        },
    ) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["connection"] == "keep-alive"
        assert response.headers["x-trace-id"] == create_body["trace_id"]

        lines = response.aiter_lines()
        event_id, event_name, payload = await read_sse_event(lines)

    assert event_id == "1"
    assert event_name == "task.created"
    assert payload["seq"] == 1
    assert payload["task_id"] == create_body["task_id"]
    assert payload["revision_id"] == create_body["snapshot"]["active_revision_id"]
    assert payload["phase"] == "clarifying"
    assert payload["payload"] == {"snapshot": create_body["snapshot"]}


@pytest.mark.asyncio
async def test_seeded_delivered_task_bootstraps_task_created_on_first_events_connect(
    app_instance,
    app_client: AsyncClient,
    db_session: Session,
    fake_clock: FakeClock,
) -> None:
    seeded = await seed_delivered_task(
        session=db_session,
        task_service=app_instance.state.task_service,
        artifact_store=app_instance.state.artifact_store,
        now=fake_clock.now(),
        suffix="events_bootstrap",
    )

    async with app_client.stream(
        "GET",
        f"/api/v1/tasks/{seeded.task_id}/events",
        headers={"Authorization": f"Bearer {seeded.task_token}"},
    ) as response:
        lines = response.aiter_lines()
        event_id, event_name, payload = await read_sse_event(lines)

    assert event_id == "1"
    assert event_name == "task.created"
    assert payload["task_id"] == seeded.task_id
    assert payload["revision_id"] == seeded.revision_id
    assert payload["phase"] == "delivered"
    assert payload["payload"]["snapshot"]["task_id"] == seeded.task_id
    assert payload["payload"]["snapshot"]["status"] == "awaiting_feedback"
    assert payload["payload"]["snapshot"]["phase"] == "delivered"


@pytest.mark.asyncio
async def test_server_heartbeat_event_and_post_heartbeat_contract(
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

        fake_clock.advance(seconds=16)
        await asyncio.sleep(0.1)
        event_id, event_name, payload = await read_until_event(lines, {"heartbeat"})

        heartbeat_response = await app_client.post(
            f"/api/v1/tasks/{create_body['task_id']}/heartbeat",
            headers={"Authorization": f"Bearer {create_body['task_token']}"},
            json={"client_time": fake_clock.now().isoformat()},
        )

    assert int(event_id or "0") >= 2
    assert event_name == "heartbeat"
    assert payload["seq"] == int(event_id or "0")
    assert payload["task_id"] == create_body["task_id"]
    assert payload["payload"]["server_time"] == fake_clock.now().isoformat().replace("+00:00", "Z")
    assert heartbeat_response.status_code == 204
    assert heartbeat_response.headers["x-trace-id"] == create_body["trace_id"]


@pytest.mark.asyncio
async def test_disconnect_while_streaming_emits_terminal_event_and_closes(
    app_client: AsyncClient,
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

        disconnect_response = await app_client.post(
            f"/api/v1/tasks/{create_body['task_id']}/disconnect",
            headers={"Authorization": f"Bearer {create_body['task_token']}"},
            json={"reason": "client_manual_abort"},
        )

        event_id, event_name, payload = await read_until_event(lines, {"task.terminated"})
        await assert_stream_closed(lines)

    assert disconnect_response.status_code == 202
    assert int(event_id or "0") >= 2
    assert event_name == "task.terminated"
    assert payload["payload"] == {"reason": "sendbeacon_received"}


@pytest.mark.asyncio
async def test_awaiting_feedback_stream_stays_open_and_allows_heartbeat_and_disconnect(
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
    task.expires_at = fake_clock.now() + timedelta(minutes=30)
    task.updated_at = fake_clock.now()
    db_session.commit()

    async with app_client.stream(
        "GET",
        f"/api/v1/tasks/{create_body['task_id']}/events",
        headers={"Authorization": f"Bearer {create_body['task_token']}"},
    ) as response:
        lines = response.aiter_lines()
        _, created_name, created_payload = await read_sse_event(lines)
        fake_clock.advance(seconds=16)
        await asyncio.sleep(0.1)
        _, heartbeat_name, heartbeat_payload = await read_until_event(lines, {"heartbeat"})

        heartbeat_response = await app_client.post(
            f"/api/v1/tasks/{create_body['task_id']}/heartbeat",
            headers={"Authorization": f"Bearer {create_body['task_token']}"},
            json={"client_time": fake_clock.now().isoformat()},
        )
        disconnect_response = await app_client.post(
            f"/api/v1/tasks/{create_body['task_id']}/disconnect",
            headers={"Authorization": f"Bearer {create_body['task_token']}"},
            json={"reason": "pagehide"},
        )
        _, terminated_name, terminated_payload = await read_until_event(lines, {"task.terminated"})

    assert created_name == "task.created"
    assert created_payload["payload"]["snapshot"]["task_id"] == create_body["task_id"]
    assert heartbeat_name == "heartbeat"
    assert heartbeat_payload["phase"] == "delivered"
    assert heartbeat_response.status_code == 204
    assert disconnect_response.status_code == 202
    assert terminated_name == "task.terminated"
    assert terminated_payload["payload"]["reason"] == "sendbeacon_received"
