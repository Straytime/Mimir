import pytest
from httpx import AsyncClient

from tests.contract.rest.test_task_events import read_until_event
from tests.contract.rest.test_tasks import build_create_task_payload


@pytest.mark.asyncio
async def test_delivery_loop_streams_stage_six_contract_events(
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

        clarification_response = await app_client.post(
            f"/api/v1/tasks/{create_body['task_id']}/clarification",
            headers={"Authorization": f"Bearer {create_body['task_token']}"},
            json={
                "mode": "natural",
                "answer_text": "重点看中国市场，偏商业分析，覆盖近两年变化。",
            },
        )

        _, outline_delta_name, outline_delta_payload = await read_until_event(
            lines,
            {"outline.delta"},
            timeout=2.0,
        )
        _, outline_completed_name, outline_completed_payload = await read_until_event(
            lines,
            {"outline.completed"},
            timeout=2.0,
        )
        _, writer_reasoning_name, writer_reasoning_payload = await read_until_event(
            lines,
            {"writer.reasoning.delta"},
            timeout=2.0,
        )
        _, tool_requested_name, tool_requested_payload = await read_until_event(
            lines,
            {"writer.tool_call.requested"},
            timeout=2.0,
        )
        _, tool_completed_name, tool_completed_payload = await read_until_event(
            lines,
            {"writer.tool_call.completed"},
            timeout=2.0,
        )
        _, writer_delta_name, writer_delta_payload = await read_until_event(
            lines,
            {"writer.delta"},
            timeout=2.0,
        )
        _, artifact_ready_name, artifact_ready_payload = await read_until_event(
            lines,
            {"artifact.ready"},
            timeout=2.0,
        )
        _, report_completed_name, report_completed_payload = await read_until_event(
            lines,
            {"report.completed"},
            timeout=2.0,
        )

    assert clarification_response.status_code == 202
    assert outline_delta_name == "outline.delta"
    assert outline_delta_payload["payload"]["delta"]
    assert outline_completed_name == "outline.completed"
    assert outline_completed_payload["payload"]["outline"]["title"]
    assert outline_completed_payload["payload"]["outline"]["sections"]
    assert writer_reasoning_name == "writer.reasoning.delta"
    assert writer_reasoning_payload["payload"]["delta"]
    assert tool_requested_name == "writer.tool_call.requested"
    assert tool_requested_payload["payload"] == {
        "tool_call_id": tool_requested_payload["payload"]["tool_call_id"],
        "tool_name": "python_interpreter",
    }
    assert tool_completed_name == "writer.tool_call.completed"
    assert tool_completed_payload["payload"]["tool_call_id"] == tool_requested_payload["payload"]["tool_call_id"]
    assert tool_completed_payload["payload"]["tool_name"] == "python_interpreter"
    assert tool_completed_payload["payload"]["success"] is True
    assert writer_delta_name == "writer.delta"
    assert writer_delta_payload["payload"]["delta"]
    assert artifact_ready_name == "artifact.ready"
    assert artifact_ready_payload["payload"]["artifact"]["artifact_id"].startswith("art_")
    assert "access_token=" in artifact_ready_payload["payload"]["artifact"]["url"]
    assert report_completed_name == "report.completed"
    assert report_completed_payload["payload"]["delivery"]["markdown_zip_url"].endswith(".zip?access_token=" + report_completed_payload["payload"]["delivery"]["markdown_zip_url"].split("access_token=")[1])
    assert report_completed_payload["payload"]["delivery"]["pdf_url"].endswith(".pdf?access_token=" + report_completed_payload["payload"]["delivery"]["pdf_url"].split("access_token=")[1])
    assert report_completed_payload["payload"]["delivery"]["artifacts"]

