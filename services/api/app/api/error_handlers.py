from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.errors import ApiError


def _error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    detail: dict[str, Any],
    trace_id: str | None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    response = JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "detail": detail,
                "request_id": getattr(request.state, "request_id", None),
                "trace_id": trace_id,
            }
        },
        headers=headers or {},
    )
    return response


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def handle_api_error(request: Request, exc: ApiError) -> JSONResponse:
        return _error_response(
            request,
            status_code=exc.status_code,
            code=exc.code,
            message=exc.message,
            detail=exc.detail,
            trace_id=exc.trace_id,
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return _error_response(
            request,
            status_code=422,
            code="validation_error",
            message="请求参数不合法。",
            detail={"errors": exc.errors()},
            trace_id=getattr(request.state, "trace_id", None),
        )
