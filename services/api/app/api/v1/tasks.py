import json

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import get_db_session, get_task_service
from app.api.errors import ApiError
from app.application.dto.tasks import (
    AcceptedResponse,
    CreateTaskRequest,
    CreateTaskResponse,
    DisconnectRequestBody,
    TaskDetailResponse,
)
from app.application.services.tasks import TaskService

router = APIRouter(tags=["tasks"])


def _extract_bearer_token(authorization_header: str | None) -> str | None:
    if not authorization_header:
        return None
    scheme, _, token = authorization_header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token


async def _extract_disconnect_body(request: Request) -> DisconnectRequestBody | None:
    raw_body = await request.body()
    if not raw_body:
        return None

    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        return DisconnectRequestBody.model_validate_json(raw_body)

    if "text/plain" in content_type:
        return DisconnectRequestBody.model_validate(json.loads(raw_body.decode("utf-8")))

    return DisconnectRequestBody.model_validate_json(raw_body)


@router.post("/tasks", response_model=CreateTaskResponse, status_code=201)
def post_tasks(
    request: Request,
    payload: CreateTaskRequest,
    session: Session = Depends(get_db_session),
    service: TaskService = Depends(get_task_service),
) -> CreateTaskResponse:
    client_ip = request.headers.get("X-Forwarded-For")
    if client_ip:
        client_ip = client_ip.split(",", maxsplit=1)[0].strip()
    else:
        client_ip = request.client.host if request.client else "127.0.0.1"

    response = service.create_task(
        session,
        payload=payload,
        client_ip=client_ip,
    )
    request.state.trace_id = response.trace_id
    return response


@router.get("/tasks/{task_id}", response_model=TaskDetailResponse)
def get_task(
    task_id: str,
    request: Request,
    session: Session = Depends(get_db_session),
    service: TaskService = Depends(get_task_service),
) -> TaskDetailResponse:
    token = _extract_bearer_token(request.headers.get("Authorization"))
    if token is None:
        raise ApiError(
            status_code=401,
            code="task_token_invalid",
            message="任务 token 无效或不匹配。",
        )

    trace_id, response = service.get_task_detail(session, task_id=task_id, token=token)
    request.state.trace_id = trace_id
    return response


@router.post("/tasks/{task_id}/disconnect", response_model=AcceptedResponse, status_code=202)
async def post_disconnect(
    task_id: str,
    request: Request,
    session: Session = Depends(get_db_session),
    service: TaskService = Depends(get_task_service),
) -> AcceptedResponse:
    header_token = _extract_bearer_token(request.headers.get("Authorization"))
    if header_token is not None:
        trace_id, response = service.disconnect_task(
            session,
            task_id=task_id,
            token=header_token,
        )
        request.state.trace_id = trace_id
        return response

    body = await _extract_disconnect_body(request)
    if body is None or body.task_token is None:
        raise ApiError(
            status_code=401,
            code="task_token_invalid",
            message="任务 token 无效或不匹配。",
        )

    trace_id, response = service.disconnect_task(
        session,
        task_id=task_id,
        token=body.task_token,
    )
    request.state.trace_id = trace_id
    return response
