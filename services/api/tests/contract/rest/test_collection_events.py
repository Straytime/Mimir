import pytest
from httpx import AsyncClient

from tests.contract.rest.test_task_events import read_until_event
from tests.contract.rest.test_tasks import build_create_task_payload


@pytest.mark.asyncio
async def test_collection_loop_streams_stage_five_contract_events(
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

        _, planner_reasoning_name, planner_reasoning_payload = await read_until_event(
            lines,
            {"planner.reasoning.delta"},
        )
        _, tool_requested_name, tool_requested_payload = await read_until_event(
            lines,
            {"planner.tool_call.requested"},
        )
        _, collector_reasoning_name, collector_reasoning_payload = await read_until_event(
            lines,
            {"collector.reasoning.delta"},
        )
        _, search_started_name, search_started_payload = await read_until_event(
            lines,
            {"collector.search.started"},
        )
        _, search_completed_name, search_completed_payload = await read_until_event(
            lines,
            {"collector.search.completed"},
        )
        _, fetch_started_name, fetch_started_payload = await read_until_event(
            lines,
            {"collector.fetch.started"},
        )
        _, fetch_completed_name, fetch_completed_payload = await read_until_event(
            lines,
            {"collector.fetch.completed"},
        )
        _, collector_completed_name, collector_completed_payload = await read_until_event(
            lines,
            {"collector.completed"},
        )
        _, summary_completed_name, summary_completed_payload = await read_until_event(
            lines,
            {"summary.completed"},
        )
        _, merged_name, merged_payload = await read_until_event(
            lines,
            {"sources.merged"},
        )

    assert clarification_response.status_code == 202
    assert planner_reasoning_name == "planner.reasoning.delta"
    assert planner_reasoning_payload["payload"]["delta"]
    assert tool_requested_name == "planner.tool_call.requested"
    assert tool_requested_payload["payload"]["tool_call_id"].startswith("call_")
    assert tool_requested_payload["payload"]["collect_target"]
    assert collector_reasoning_name == "collector.reasoning.delta"
    assert collector_reasoning_payload["payload"]["subtask_id"].startswith("sub_")
    assert search_started_name == "collector.search.started"
    assert search_started_payload["payload"]["search_recency_filter"] == "noLimit"
    assert search_completed_name == "collector.search.completed"
    assert search_completed_payload["payload"]["result_count"] >= 1
    assert fetch_started_name == "collector.fetch.started"
    assert fetch_completed_name == "collector.fetch.completed"
    assert fetch_completed_payload["payload"]["success"] is True
    assert collector_completed_name == "collector.completed"
    assert collector_completed_payload["payload"]["status"] in {"completed", "partial"}
    assert summary_completed_name == "summary.completed"
    assert summary_completed_payload["payload"]["status"] in {
        "completed",
        "partial",
        "risk_blocked",
    }
    assert merged_name == "sources.merged"
    assert merged_payload["payload"]["source_count_before_merge"] >= 1
    assert merged_payload["payload"]["source_count_after_merge"] >= 1
    assert merged_payload["payload"]["reference_count"] == merged_payload["payload"][
        "source_count_after_merge"
    ]
