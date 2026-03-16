import json

import pytest
from httpx import AsyncClient


def build_create_task_payload(
    *,
    clarification_mode: str = "natural",
) -> dict[str, object]:
    return {
        "initial_query": "帮我研究中国 AI 搜索产品竞争格局和未来机会",
        "config": {"clarification_mode": clarification_mode},
        "client": {"timezone": "Asia/Shanghai", "locale": "zh-CN"},
    }


@pytest.mark.asyncio
async def test_post_tasks_and_get_task_detail_form_stage_two_minimal_closure(
    app_client: AsyncClient,
    allowed_origin: str,
) -> None:
    create_response = await app_client.post(
        "/api/v1/tasks",
        json=build_create_task_payload(),
        headers={
            "Origin": allowed_origin,
            "X-Request-ID": "req_client_123",
        },
    )

    assert create_response.status_code == 201
    assert create_response.headers["x-request-id"] == "req_client_123"
    assert create_response.headers["access-control-allow-origin"] == allowed_origin

    create_body = create_response.json()
    assert create_response.headers["x-trace-id"] == create_body["trace_id"]
    assert create_body["task_id"].startswith("tsk_")
    assert create_body["task_token"]
    assert create_body["trace_id"].startswith("trc_")
    assert create_body["snapshot"]["status"] == "running"
    assert create_body["snapshot"]["phase"] == "clarifying"
    assert create_body["urls"]["events"].endswith("/events")
    assert create_body["urls"]["heartbeat"].endswith("/heartbeat")
    assert create_body["urls"]["disconnect"].endswith("/disconnect")
    assert create_body["connect_deadline_at"]

    task_id = create_body["task_id"]
    task_token = create_body["task_token"]

    get_response = await app_client.get(
        f"/api/v1/tasks/{task_id}",
        headers={"Authorization": f"Bearer {task_token}"},
    )

    assert get_response.status_code == 200
    assert get_response.headers["x-trace-id"] == create_body["trace_id"]
    get_body = get_response.json()
    assert get_body == {
        "task_id": task_id,
        "snapshot": create_body["snapshot"],
        "current_revision": {
            "revision_id": create_body["snapshot"]["active_revision_id"],
            "revision_number": 1,
            "revision_status": "in_progress",
            "started_at": create_body["snapshot"]["created_at"],
            "finished_at": None,
            "requirement_detail": None,
        },
        "delivery": None,
    }


@pytest.mark.asyncio
async def test_get_task_rejects_missing_or_invalid_auth_with_contract_error_code(
    app_client: AsyncClient,
) -> None:
    create_response = await app_client.post(
        "/api/v1/tasks",
        json=build_create_task_payload(),
    )
    task_id = create_response.json()["task_id"]

    missing_auth = await app_client.get(f"/api/v1/tasks/{task_id}")
    invalid_auth = await app_client.get(
        f"/api/v1/tasks/{task_id}",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert missing_auth.status_code == 401
    assert missing_auth.json()["error"]["code"] == "task_token_invalid"
    assert invalid_auth.status_code == 401
    assert invalid_auth.json()["error"]["code"] == "task_token_invalid"


@pytest.mark.asyncio
async def test_post_tasks_enforces_single_activity_lock(app_client: AsyncClient) -> None:
    first = await app_client.post("/api/v1/tasks", json=build_create_task_payload())
    second = await app_client.post("/api/v1/tasks", json=build_create_task_payload())

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "resource_busy"


@pytest.mark.asyncio
async def test_post_tasks_enforces_ip_quota_and_returns_retry_after(
    app_client: AsyncClient,
) -> None:
    for _ in range(3):
        response = await app_client.post("/api/v1/tasks", json=build_create_task_payload())
        task_id = response.json()["task_id"]
        task_token = response.json()["task_token"]

        disconnect = await app_client.post(
            f"/api/v1/tasks/{task_id}/disconnect",
            json={"reason": "client_manual_abort", "task_token": task_token},
        )
        assert disconnect.status_code == 202

    quota_response = await app_client.post("/api/v1/tasks", json=build_create_task_payload())

    assert quota_response.status_code == 429
    assert int(quota_response.headers["retry-after"]) > 0
    assert quota_response.json()["error"]["code"] == "ip_quota_exceeded"
    assert quota_response.json()["error"]["detail"]["quota_limit"] == 3
    assert quota_response.json()["error"]["detail"]["quota_used"] == 3


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("content_type", "body"),
    [
        ("application/json", {"reason": "pagehide", "task_token": "from-payload"}),
        (
            "text/plain",
            json.dumps({"reason": "beforeunload", "task_token": "from-payload"}),
        ),
    ],
)
async def test_disconnect_accepts_body_token_in_json_or_text_plain(
    app_client: AsyncClient,
    content_type: str,
    body: dict[str, str] | str,
) -> None:
    create_response = await app_client.post("/api/v1/tasks", json=build_create_task_payload())
    task_id = create_response.json()["task_id"]
    task_token = create_response.json()["task_token"]

    if isinstance(body, dict):
        body["task_token"] = task_token
        disconnect = await app_client.post(
            f"/api/v1/tasks/{task_id}/disconnect",
            json=body,
        )
    else:
        disconnect = await app_client.post(
            f"/api/v1/tasks/{task_id}/disconnect",
            content=json.dumps({"reason": "beforeunload", "task_token": task_token}),
            headers={"Content-Type": content_type},
        )

    assert disconnect.status_code == 202
    assert disconnect.json() == {"accepted": True}


@pytest.mark.asyncio
async def test_disconnect_accepts_header_token_and_prefers_header_over_body(
    app_client: AsyncClient,
) -> None:
    create_response = await app_client.post("/api/v1/tasks", json=build_create_task_payload())
    task_id = create_response.json()["task_id"]
    task_token = create_response.json()["task_token"]

    header_success = await app_client.post(
        f"/api/v1/tasks/{task_id}/disconnect",
        json={"reason": "pagehide"},
        headers={"Authorization": f"Bearer {task_token}"},
    )

    assert header_success.status_code == 202
    assert header_success.headers["x-trace-id"] == create_response.json()["trace_id"]

    next_create = await app_client.post("/api/v1/tasks", json=build_create_task_payload())
    next_task_id = next_create.json()["task_id"]
    next_task_token = next_create.json()["task_token"]

    precedence = await app_client.post(
        f"/api/v1/tasks/{next_task_id}/disconnect",
        json={"reason": "pagehide", "task_token": next_task_token},
        headers={"Authorization": "Bearer invalid-header-token"},
    )

    assert precedence.status_code == 401
    assert precedence.json()["error"]["code"] == "task_token_invalid"


@pytest.mark.asyncio
async def test_cors_allows_whitelisted_origin_and_echoes_generated_request_id(
    app_client: AsyncClient,
    allowed_origin: str,
) -> None:
    response = await app_client.post(
        "/api/v1/tasks",
        json=build_create_task_payload(),
        headers={"Origin": allowed_origin},
    )

    assert response.status_code == 201
    assert response.headers["access-control-allow-origin"] == allowed_origin
    assert response.headers["x-request-id"].startswith("req_")


@pytest.mark.asyncio
async def test_cors_does_not_allow_non_whitelisted_origin(
    app_client: AsyncClient,
    denied_origin: str,
) -> None:
    response = await app_client.post(
        "/api/v1/tasks",
        json=build_create_task_payload(),
        headers={"Origin": denied_origin},
    )

    assert response.status_code == 201
    assert "access-control-allow-origin" not in response.headers


@pytest.mark.asyncio
async def test_options_preflight_returns_authorization_for_whitelisted_origin(
    app_client: AsyncClient,
    allowed_origin: str,
) -> None:
    response = await app_client.options(
        "/api/v1/tasks/example/disconnect",
        headers={
            "Origin": allowed_origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Authorization,Content-Type,X-Request-ID",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == allowed_origin
    assert "Authorization" in response.headers["access-control-allow-headers"]
