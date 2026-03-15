from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import Settings
from app.core.ids import generate_id


def install_middlewares(app: FastAPI, *, settings: Settings) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_allow_origins),
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "Last-Event-ID",
            "X-Request-ID",
        ],
    )

    @app.middleware("http")
    async def add_response_metadata(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request.state.request_id = request.headers.get("X-Request-ID") or generate_id(
            "req"
        )
        response = await call_next(request)
        response.headers.setdefault("X-Request-ID", request.state.request_id)

        trace_id = getattr(request.state, "trace_id", None)
        if trace_id:
            response.headers.setdefault("X-Trace-ID", trace_id)

        response.headers.setdefault("Cache-Control", "no-store")
        return response
