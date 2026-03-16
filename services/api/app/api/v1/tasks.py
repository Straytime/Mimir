import json

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import (
    get_artifact_store,
    get_db_session,
    get_task_lifecycle,
    get_task_service,
)
from app.api.errors import ApiError
from app.application.dto.clarification import (
    ClarificationAcceptedResponse,
    ClarificationSubmission,
)
from app.application.ports.delivery import ArtifactStore
from app.application.dto.tasks import (
    AcceptedResponse,
    CreateTaskRequest,
    CreateTaskResponse,
    DisconnectRequestBody,
    HeartbeatRequest,
    TaskDetailResponse,
)
from app.application.services.tasks import TaskService
from app.domain.enums import AccessTokenResourceType
from app.infrastructure.streaming.broker import TaskLifecycleManager

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
async def post_tasks(
    request: Request,
    payload: CreateTaskRequest,
    session: Session = Depends(get_db_session),
    service: TaskService = Depends(get_task_service),
    lifecycle: TaskLifecycleManager = Depends(get_task_lifecycle),
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
    await lifecycle.register_task(
        task_id=response.task_id,
        connect_deadline_at=response.connect_deadline_at,
    )
    request.state.trace_id = response.trace_id
    return response


@router.get("/tasks/{task_id}", response_model=TaskDetailResponse)
async def get_task(
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


@router.get("/tasks/{task_id}/events")
async def get_task_events(
    task_id: str,
    request: Request,
    lifecycle: TaskLifecycleManager = Depends(get_task_lifecycle),
) -> StreamingResponse:
    token = _extract_bearer_token(request.headers.get("Authorization"))
    if token is None:
        raise ApiError(
            status_code=401,
            code="task_token_invalid",
            message="任务 token 无效或不匹配。",
        )

    trace_id = await lifecycle.prepare_event_stream(task_id=task_id, token=token)
    request.state.trace_id = trace_id
    return StreamingResponse(
        lifecycle.stream_events(request=request, task_id=task_id),
        media_type="text/event-stream",
        headers={
            "Connection": "keep-alive",
            "Cache-Control": "no-store",
        },
    )


@router.post("/tasks/{task_id}/heartbeat", status_code=204)
async def post_heartbeat(
    task_id: str,
    payload: HeartbeatRequest,
    request: Request,
    lifecycle: TaskLifecycleManager = Depends(get_task_lifecycle),
) -> Response:
    token = _extract_bearer_token(request.headers.get("Authorization"))
    if token is None:
        raise ApiError(
            status_code=401,
            code="task_token_invalid",
            message="任务 token 无效或不匹配。",
        )

    trace_id = await lifecycle.record_client_heartbeat(
        task_id=task_id,
        token=token,
    )
    request.state.trace_id = trace_id
    return Response(status_code=204)


@router.post(
    "/tasks/{task_id}/clarification",
    response_model=ClarificationAcceptedResponse,
    status_code=202,
)
async def post_clarification(
    task_id: str,
    payload: ClarificationSubmission,
    request: Request,
    lifecycle: TaskLifecycleManager = Depends(get_task_lifecycle),
) -> ClarificationAcceptedResponse:
    token = _extract_bearer_token(request.headers.get("Authorization"))
    if token is None:
        raise ApiError(
            status_code=401,
            code="task_token_invalid",
            message="任务 token 无效或不匹配。",
        )

    trace_id, response = await lifecycle.submit_clarification(
        task_id=task_id,
        token=token,
        payload=payload,
    )
    request.state.trace_id = trace_id
    return response


@router.post("/tasks/{task_id}/disconnect", response_model=AcceptedResponse, status_code=202)
async def post_disconnect(
    task_id: str,
    request: Request,
    lifecycle: TaskLifecycleManager = Depends(get_task_lifecycle),
) -> AcceptedResponse:
    header_token = _extract_bearer_token(request.headers.get("Authorization"))
    if header_token is not None:
        trace_id = await lifecycle.disconnect_task(
            task_id=task_id,
            token=header_token,
        )
        request.state.trace_id = trace_id
        return AcceptedResponse(accepted=True)

    body = await _extract_disconnect_body(request)
    if body is None or body.task_token is None:
        raise ApiError(
            status_code=401,
            code="task_token_invalid",
            message="任务 token 无效或不匹配。",
        )

    trace_id = await lifecycle.disconnect_task(
        task_id=task_id,
        token=body.task_token,
    )
    request.state.trace_id = trace_id
    return AcceptedResponse(accepted=True)


@router.get("/tasks/{task_id}/downloads/markdown.zip")
async def get_markdown_download(
    task_id: str,
    request: Request,
    access_token: str | None = Query(default=None),
    session: Session = Depends(get_db_session),
    service: TaskService = Depends(get_task_service),
    artifact_store: ArtifactStore = Depends(get_artifact_store),
) -> Response:
    trace_id, artifact = service.get_binary_resource(
        session,
        task_id=task_id,
        access_token=access_token,
        resource_type=AccessTokenResourceType.MARKDOWN_DOWNLOAD,
    )
    request.state.trace_id = trace_id
    return Response(
        content=await artifact_store.get(artifact.storage_key),
        media_type=artifact.mime_type,
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": 'attachment; filename="mimir-report.zip"',
        },
    )


@router.get("/tasks/{task_id}/downloads/report.pdf")
async def get_pdf_download(
    task_id: str,
    request: Request,
    access_token: str | None = Query(default=None),
    session: Session = Depends(get_db_session),
    service: TaskService = Depends(get_task_service),
    artifact_store: ArtifactStore = Depends(get_artifact_store),
) -> Response:
    trace_id, artifact = service.get_binary_resource(
        session,
        task_id=task_id,
        access_token=access_token,
        resource_type=AccessTokenResourceType.PDF_DOWNLOAD,
    )
    request.state.trace_id = trace_id
    return Response(
        content=await artifact_store.get(artifact.storage_key),
        media_type=artifact.mime_type,
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": 'attachment; filename="mimir-report.pdf"',
        },
    )


@router.get("/tasks/{task_id}/artifacts/{artifact_id}")
async def get_artifact(
    task_id: str,
    artifact_id: str,
    request: Request,
    access_token: str | None = Query(default=None),
    session: Session = Depends(get_db_session),
    service: TaskService = Depends(get_task_service),
    artifact_store: ArtifactStore = Depends(get_artifact_store),
) -> Response:
    trace_id, artifact = service.get_binary_resource(
        session,
        task_id=task_id,
        access_token=access_token,
        resource_type=AccessTokenResourceType.ARTIFACT,
        artifact_id=artifact_id,
    )
    request.state.trace_id = trace_id
    return Response(
        content=await artifact_store.get(artifact.storage_key),
        media_type=artifact.mime_type,
        headers={"Cache-Control": "no-store"},
    )
