import asyncio
from collections.abc import AsyncIterator
from contextlib import suppress
from typing import Any

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import AsyncBaseTransport, AsyncClient, AsyncByteStream, Request, Response

from app.core.config import Settings
from app.infrastructure.delivery.local import LocalArtifactStore
from app.main import create_app
from tests.fixtures.runtime import FakeClock


class StreamingASGIResponseStream(AsyncByteStream):
    def __init__(
        self,
        *,
        body_queue: asyncio.Queue[bytes | None],
        disconnect_event: asyncio.Event,
        response_complete: asyncio.Event,
        app_task: asyncio.Task[None],
    ) -> None:
        self._body_queue = body_queue
        self._disconnect_event = disconnect_event
        self._response_complete = response_complete
        self._app_task = app_task

    async def __aiter__(self) -> AsyncIterator[bytes]:
        while True:
            chunk = await self._body_queue.get()
            if chunk is None:
                return
            yield chunk

    async def aclose(self) -> None:
        self._disconnect_event.set()
        if self._app_task.done():
            with suppress(asyncio.CancelledError):
                await self._app_task
            return

        try:
            await asyncio.wait_for(self._app_task, timeout=0.5)
        except asyncio.TimeoutError:
            self._app_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._app_task


class StreamingASGITransport(AsyncBaseTransport):
    def __init__(
        self,
        *,
        app: FastAPI,
        client: tuple[str, int],
        raise_app_exceptions: bool = True,
        root_path: str = "",
    ) -> None:
        self.app = app
        self.client = client
        self.raise_app_exceptions = raise_app_exceptions
        self.root_path = root_path

    async def handle_async_request(self, request: Request) -> Response:
        request_body_chunks = request.stream.__aiter__()
        request_complete = False
        response_started = asyncio.Event()
        response_complete = asyncio.Event()
        disconnect_event = asyncio.Event()
        body_queue: asyncio.Queue[bytes | None] = asyncio.Queue()
        status_code: int | None = None
        response_headers: list[tuple[bytes, bytes]] | None = None
        app_exception: BaseException | None = None

        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": request.method,
            "headers": [(k.lower(), v) for (k, v) in request.headers.raw],
            "scheme": request.url.scheme,
            "path": request.url.path,
            "raw_path": request.url.raw_path.split(b"?")[0],
            "query_string": request.url.query,
            "server": (request.url.host, request.url.port),
            "client": self.client,
            "root_path": self.root_path,
        }

        async def receive() -> dict[str, Any]:
            nonlocal request_complete

            if request_complete:
                if disconnect_event.is_set():
                    return {"type": "http.disconnect"}

                done, _ = await asyncio.wait(
                    {
                        asyncio.create_task(response_complete.wait()),
                        asyncio.create_task(disconnect_event.wait()),
                    },
                    return_when=asyncio.FIRST_COMPLETED,
                )
                for task in done:
                    task.cancel()
                if disconnect_event.is_set():
                    return {"type": "http.disconnect"}
                return {"type": "http.disconnect"}

            try:
                body = await request_body_chunks.__anext__()
            except StopAsyncIteration:
                request_complete = True
                return {"type": "http.request", "body": b"", "more_body": False}
            return {"type": "http.request", "body": body, "more_body": True}

        async def send(message: dict[str, Any]) -> None:
            nonlocal status_code, response_headers

            if message["type"] == "http.response.start":
                status_code = message["status"]
                response_headers = message.get("headers", [])
                response_started.set()
                return

            if message["type"] == "http.response.body":
                body = message.get("body", b"")
                if body and request.method != "HEAD":
                    await body_queue.put(body)
                if not message.get("more_body", False):
                    await body_queue.put(None)
                    response_complete.set()

        async def run_app() -> None:
            nonlocal app_exception, status_code, response_headers
            try:
                await self.app(scope, receive, send)
            except BaseException as exc:
                app_exception = exc
                if self.raise_app_exceptions:
                    raise
                if status_code is None:
                    status_code = 500
                    response_headers = []
                    response_started.set()
                await body_queue.put(None)
                response_complete.set()

        app_task = asyncio.create_task(run_app())
        await response_started.wait()

        if app_exception is not None and self.raise_app_exceptions:
            raise app_exception

        assert status_code is not None
        assert response_headers is not None
        stream = StreamingASGIResponseStream(
            body_queue=body_queue,
            disconnect_event=disconnect_event,
            response_complete=response_complete,
            app_task=app_task,
        )
        return Response(status_code, headers=response_headers, stream=stream)


@pytest.fixture
def allowed_origin() -> str:
    return "https://app.example.com"


@pytest.fixture
def denied_origin() -> str:
    return "https://denied.example.com"


@pytest.fixture
def settings(
    migrated_database_url: str,
    allowed_origin: str,
) -> Settings:
    return Settings(
        database_url=migrated_database_url,
        cors_allow_origins=(allowed_origin,),
        task_token_secret="task-secret",
        access_token_secret="access-secret",
        lifecycle_poll_interval_seconds=0.02,
        cleanup_scan_interval_seconds=0.02,
    )


@pytest.fixture
def app_instance(
    settings: Settings,
    fake_clock: FakeClock,
    temp_artifact_dir,
) -> FastAPI:
    return create_app(
        settings=settings,
        clock=fake_clock.now,
        artifact_store=LocalArtifactStore(root_dir=temp_artifact_dir),
    )


@pytest_asyncio.fixture
async def app_client(app_instance: FastAPI) -> AsyncIterator[AsyncClient]:
    app = app_instance
    await app.router.startup()

    transport = StreamingASGITransport(app=app, client=("203.0.113.10", 51000))
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        yield client

    await app.state.task_lifecycle.shutdown()
    await app.router.shutdown()
