import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.orm import Session

from tests.contract.rest.test_tasks import build_create_task_payload
from tests.fixtures.tasks import seed_delivered_task


@pytest.mark.asyncio
async def test_post_feedback_returns_new_revision_metadata_for_delivered_task(
    app_client: AsyncClient,
    app_instance: FastAPI,
    db_session: Session,
    fake_clock,
) -> None:
    seeded = await seed_delivered_task(
        session=db_session,
        task_service=app_instance.state.task_service,
        artifact_store=app_instance.state.artifact_store,
        now=fake_clock.now(),
        suffix="contract_feedback_ok",
    )

    response = await app_client.post(
        f"/api/v1/tasks/{seeded.task_id}/feedback",
        headers={"Authorization": f"Bearer {seeded.task_token}"},
        json={
            "feedback_text": "补充比较各家产品在 B 端场景的落地情况，并删掉不够确定的推测。"
        },
    )

    assert response.status_code == 202
    assert response.headers["x-trace-id"] == seeded.trace_id
    assert response.json()["accepted"] is True
    assert response.json()["revision_id"].startswith("rev_")
    assert response.json()["revision_number"] == 2


@pytest.mark.asyncio
async def test_post_feedback_returns_validation_error_for_invalid_body(
    app_client: AsyncClient,
    app_instance: FastAPI,
    db_session: Session,
    fake_clock,
) -> None:
    seeded = await seed_delivered_task(
        session=db_session,
        task_service=app_instance.state.task_service,
        artifact_store=app_instance.state.artifact_store,
        now=fake_clock.now(),
        suffix="contract_feedback_422",
    )

    response = await app_client.post(
        f"/api/v1/tasks/{seeded.task_id}/feedback",
        headers={"Authorization": f"Bearer {seeded.task_token}"},
        json={"feedback_text": ""},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


@pytest.mark.asyncio
async def test_post_feedback_returns_invalid_task_state_before_delivery(
    app_client: AsyncClient,
) -> None:
    create_response = await app_client.post(
        "/api/v1/tasks",
        json=build_create_task_payload(clarification_mode="natural"),
    )
    create_body = create_response.json()

    response = await app_client.post(
        f"/api/v1/tasks/{create_body['task_id']}/feedback",
        headers={"Authorization": f"Bearer {create_body['task_token']}"},
        json={"feedback_text": "请补充 B 端商业化落地。"},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "invalid_task_state"
