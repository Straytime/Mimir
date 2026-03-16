import pytest
from httpx import AsyncClient

from tests.contract.rest.test_task_events import read_sse_event, read_until_event
from tests.contract.rest.test_tasks import build_create_task_payload


@pytest.mark.asyncio
async def test_post_clarification_accepts_natural_body_and_returns_analyzing_snapshot(
    app_client: AsyncClient,
) -> None:
    create_response = await app_client.post(
        "/api/v1/tasks",
        json=build_create_task_payload(clarification_mode="natural"),
    )
    create_body = create_response.json()

    async with app_client.stream(
        "GET",
        f"/api/v1/tasks/{create_body['task_id']}/events",
        headers={"Authorization": f"Bearer {create_body['task_token']}"},
    ) as response:
        lines = response.aiter_lines()
        await read_until_event(lines, {"clarification.natural.ready"})

        submit_response = await app_client.post(
            f"/api/v1/tasks/{create_body['task_id']}/clarification",
            headers={"Authorization": f"Bearer {create_body['task_token']}"},
            json={
                "mode": "natural",
                "answer_text": "重点看中国市场，偏商业分析，覆盖近两年变化。",
            },
        )
        _, phase_event_name, _ = await read_until_event(lines, {"phase.changed"})

    assert submit_response.status_code == 202
    assert submit_response.headers["x-trace-id"] == create_body["trace_id"]
    assert submit_response.json() == {
        "accepted": True,
        "snapshot": {
            **create_body["snapshot"],
            "status": "running",
            "phase": "analyzing_requirement",
            "updated_at": submit_response.json()["snapshot"]["updated_at"],
            "available_actions": [],
        },
    }
    assert phase_event_name == "phase.changed"


@pytest.mark.asyncio
async def test_post_clarification_accepts_options_body_and_returns_analyzing_snapshot(
    app_client: AsyncClient,
) -> None:
    create_response = await app_client.post(
        "/api/v1/tasks",
        json=build_create_task_payload(clarification_mode="options"),
    )
    create_body = create_response.json()

    async with app_client.stream(
        "GET",
        f"/api/v1/tasks/{create_body['task_id']}/events",
        headers={"Authorization": f"Bearer {create_body['task_token']}"},
    ) as response:
        lines = response.aiter_lines()
        _, _, ready_payload = await read_until_event(lines, {"clarification.options.ready"})
        question = ready_payload["payload"]["question_set"]["questions"][0]
        selected_option = question["options"][0]

        submit_response = await app_client.post(
            f"/api/v1/tasks/{create_body['task_id']}/clarification",
            headers={"Authorization": f"Bearer {create_body['task_token']}"},
            json={
                "mode": "options",
                "submitted_by_timeout": False,
                "answers": [
                    {
                        "question_id": question["question_id"],
                        "selected_option_id": selected_option["option_id"],
                        "selected_label": selected_option["label"],
                    }
                ],
            },
        )

    assert submit_response.status_code == 202
    assert submit_response.json()["accepted"] is True
    assert submit_response.json()["snapshot"]["status"] == "running"
    assert submit_response.json()["snapshot"]["phase"] == "analyzing_requirement"
    assert submit_response.json()["snapshot"]["available_actions"] == []


@pytest.mark.asyncio
async def test_post_clarification_returns_validation_error_for_invalid_body(
    app_client: AsyncClient,
) -> None:
    create_response = await app_client.post(
        "/api/v1/tasks",
        json=build_create_task_payload(clarification_mode="natural"),
    )
    create_body = create_response.json()

    async with app_client.stream(
        "GET",
        f"/api/v1/tasks/{create_body['task_id']}/events",
        headers={"Authorization": f"Bearer {create_body['task_token']}"},
    ) as response:
        lines = response.aiter_lines()
        await read_until_event(lines, {"clarification.natural.ready"})

        submit_response = await app_client.post(
            f"/api/v1/tasks/{create_body['task_id']}/clarification",
            headers={"Authorization": f"Bearer {create_body['task_token']}"},
            json={
                "mode": "natural",
                "answer_text": "x" * 501,
            },
        )

    assert submit_response.status_code == 422
    assert submit_response.json()["error"]["code"] == "validation_error"


@pytest.mark.asyncio
async def test_post_clarification_returns_invalid_task_state_before_ready(
    app_client: AsyncClient,
) -> None:
    create_response = await app_client.post(
        "/api/v1/tasks",
        json=build_create_task_payload(clarification_mode="natural"),
    )
    create_body = create_response.json()

    submit_response = await app_client.post(
        f"/api/v1/tasks/{create_body['task_id']}/clarification",
        headers={"Authorization": f"Bearer {create_body['task_token']}"},
        json={
            "mode": "natural",
            "answer_text": "重点看中国市场。",
        },
    )

    assert submit_response.status_code == 409
    assert submit_response.json()["error"]["code"] == "invalid_task_state"
