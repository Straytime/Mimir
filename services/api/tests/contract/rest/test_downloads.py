from urllib.parse import parse_qs, urlparse

import pytest
from httpx import AsyncClient

from tests.contract.rest.test_task_events import read_until_event
from tests.contract.rest.test_tasks import build_create_task_payload
from tests.fixtures.runtime import FakeClock


async def _complete_delivery(app_client: AsyncClient) -> tuple[dict[str, object], dict[str, object]]:
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
        clarification_response = await app_client.post(
            f"/api/v1/tasks/{create_body['task_id']}/clarification",
            headers={"Authorization": f"Bearer {create_body['task_token']}"},
            json={
                "mode": "natural",
                "answer_text": "重点看中国市场，偏商业分析，覆盖近两年变化。",
            },
        )
        assert clarification_response.status_code == 202
        _, _, report_completed_payload = await read_until_event(
            lines,
            {"report.completed"},
            timeout=2.0,
        )

    return create_body, report_completed_payload["payload"]["delivery"]


@pytest.mark.asyncio
async def test_download_and_artifact_endpoints_accept_refreshed_access_tokens(
    app_client: AsyncClient,
    fake_clock: FakeClock,
) -> None:
    create_body, delivery = await _complete_delivery(app_client)

    markdown_response = await app_client.get(delivery["markdown_zip_url"])
    pdf_response = await app_client.get(delivery["pdf_url"])
    artifact_response = await app_client.get(delivery["artifacts"][0]["url"])

    assert markdown_response.status_code == 200
    assert markdown_response.headers["content-type"] == "application/zip"
    assert markdown_response.headers["content-disposition"] == 'attachment; filename="mimir-report.zip"'
    assert markdown_response.headers["cache-control"] == "no-store"

    assert pdf_response.status_code == 200
    assert pdf_response.headers["content-type"] == "application/pdf"
    assert pdf_response.headers["content-disposition"] == 'attachment; filename="mimir-report.pdf"'
    assert pdf_response.headers["cache-control"] == "no-store"

    assert artifact_response.status_code == 200
    assert artifact_response.headers["content-type"] == "image/png"
    assert artifact_response.headers["cache-control"] == "no-store"

    fake_clock.advance(minutes=11)
    expired_response = await app_client.get(delivery["markdown_zip_url"])

    assert expired_response.status_code == 401
    assert expired_response.json()["error"]["code"] == "access_token_invalid"

    refreshed_task = await app_client.get(
        f"/api/v1/tasks/{create_body['task_id']}",
        headers={"Authorization": f"Bearer {create_body['task_token']}"},
    )
    refreshed_delivery = refreshed_task.json()["delivery"]

    assert refreshed_task.status_code == 200
    assert refreshed_delivery["markdown_zip_url"] != delivery["markdown_zip_url"]
    assert refreshed_delivery["pdf_url"] != delivery["pdf_url"]
    assert refreshed_delivery["artifacts"][0]["url"] != delivery["artifacts"][0]["url"]

    refreshed_markdown_response = await app_client.get(refreshed_delivery["markdown_zip_url"])
    refreshed_pdf_response = await app_client.get(refreshed_delivery["pdf_url"])
    refreshed_artifact_response = await app_client.get(refreshed_delivery["artifacts"][0]["url"])

    assert refreshed_markdown_response.status_code == 200
    assert refreshed_pdf_response.status_code == 200
    assert refreshed_artifact_response.status_code == 200

    refreshed_query = parse_qs(urlparse(refreshed_delivery["markdown_zip_url"]).query)
    assert "access_token" in refreshed_query


@pytest.mark.asyncio
async def test_download_endpoints_reject_invalid_access_tokens_with_contract_error_code(
    app_client: AsyncClient,
) -> None:
    create_body, delivery = await _complete_delivery(app_client)

    artifact_id = delivery["artifacts"][0]["artifact_id"]
    invalid_markdown = await app_client.get(
        f"/api/v1/tasks/{create_body['task_id']}/downloads/markdown.zip?access_token=invalid"
    )
    invalid_pdf = await app_client.get(
        f"/api/v1/tasks/{create_body['task_id']}/downloads/report.pdf?access_token=invalid"
    )
    invalid_artifact = await app_client.get(
        f"/api/v1/tasks/{create_body['task_id']}/artifacts/{artifact_id}?access_token=invalid"
    )

    assert invalid_markdown.status_code == 401
    assert invalid_markdown.json()["error"]["code"] == "access_token_invalid"
    assert invalid_pdf.status_code == 401
    assert invalid_pdf.json()["error"]["code"] == "access_token_invalid"
    assert invalid_artifact.status_code == 401
    assert invalid_artifact.json()["error"]["code"] == "access_token_invalid"
