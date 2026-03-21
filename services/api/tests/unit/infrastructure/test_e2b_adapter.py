from dataclasses import replace
from types import SimpleNamespace

import pytest

from app.application.services.invocation import RetryableOperationError
from app.core.config import Settings
from app.infrastructure.delivery.e2b import E2BRealSandboxClient
from app.infrastructure.providers import build_provider_runtime


class FakeFilesystem:
    def __init__(
        self,
        *,
        list_results: list[list[object]],
        read_results: dict[str, bytes] | None = None,
        read_error: Exception | None = None,
    ) -> None:
        self.list_results = list_results
        self.read_results = read_results or {}
        self.read_error = read_error
        self.read_calls: list[tuple[str, str]] = []

    async def list(
        self,
        path: str,
        depth: int | None = 1,
        user: str | None = None,
        request_timeout: float | None = None,
    ) -> list[object]:
        if self.list_results:
            return self.list_results.pop(0)
        return []

    async def read(
        self,
        path: str,
        format: str = "text",
        user: str | None = None,
        request_timeout: float | None = None,
    ):
        self.read_calls.append((path, format))
        if self.read_error is not None:
            raise self.read_error
        return bytearray(self.read_results[path])


class FakeSandbox:
    def __init__(
        self,
        *,
        sandbox_id: str = "sbox_1",
        files: FakeFilesystem,
        execution: object | None = None,
        run_error: Exception | None = None,
        kill_error: Exception | None = None,
    ) -> None:
        self.sandbox_id = sandbox_id
        self.files = files
        self.execution = execution or SimpleNamespace(
            logs=SimpleNamespace(stdout=["ok"]),
            error=None,
            text="ok",
        )
        self.run_error = run_error
        self.kill_error = kill_error
        self.run_calls: list[tuple[str, str | None, float | None, float | None]] = []
        self.kill_calls: list[dict[str, object]] = []

    async def run_code(
        self,
        code: str,
        language: str | None = None,
        timeout: float | None = None,
        request_timeout: float | None = None,
    ):
        self.run_calls.append((code, language, timeout, request_timeout))
        if self.run_error is not None:
            raise self.run_error
        return self.execution

    async def kill(self, **opts):
        self.kill_calls.append(opts)
        if self.kill_error is not None:
            raise self.kill_error
        return True


class FakeSandboxFactory:
    def __init__(
        self,
        *,
        sandbox: FakeSandbox | None = None,
        create_error: Exception | None = None,
    ) -> None:
        self.sandbox = sandbox
        self.create_error = create_error
        self.create_calls: list[dict[str, object]] = []

    async def create(
        self,
        *,
        timeout: int | None = None,
        request_timeout: float | None = None,
        api_key: str | None = None,
    ) -> FakeSandbox:
        self.create_calls.append(
            {
                "timeout": timeout,
                "request_timeout": request_timeout,
                "api_key": api_key,
            }
        )
        if self.create_error is not None:
            raise self.create_error
        assert self.sandbox is not None
        return self.sandbox


def test_build_provider_runtime_uses_real_e2b_adapter_when_e2b_mode_is_real() -> None:
    runtime = build_provider_runtime(
        replace(
            Settings(),
            provider_mode="stub",
            e2b_provider_mode="real",
            e2b_api_key="e2b-key",
        )
    )

    assert isinstance(runtime.sandbox_client, E2BRealSandboxClient)


@pytest.mark.asyncio
async def test_e2b_adapter_maps_generated_png_files_into_artifacts() -> None:
    filesystem = FakeFilesystem(
        list_results=[
            [],
            [SimpleNamespace(path="./chart.png")],
        ],
        read_results={"./chart.png": b"png-bytes"},
    )
    sandbox = FakeSandbox(files=filesystem)
    factory = FakeSandboxFactory(sandbox=sandbox)
    adapter = E2BRealSandboxClient(
        api_key="e2b-secret-key",
        request_timeout_seconds=12.0,
        execution_timeout_seconds=34.0,
        sandbox_timeout_seconds=600,
        sandbox_factory=factory,
    )

    sandbox_id = await adapter.create()
    result = await adapter.execute_python(
        sandbox_id,
        "print('ok')",
    )
    await adapter.destroy(sandbox_id)

    assert sandbox_id == "sbox_1"
    assert factory.create_calls == [
        {
            "timeout": 600,
            "request_timeout": 12.0,
            "api_key": "e2b-secret-key",
        }
    ]
    assert sandbox.run_calls == [("print('ok')", "python", 34.0, 12.0)]
    assert result.stdout == "ok"
    assert len(result.artifacts) == 1
    assert result.artifacts[0].filename == "chart.png"
    assert result.artifacts[0].mime_type == "image/png"
    assert result.artifacts[0].content == b"png-bytes"
    assert filesystem.read_calls == [("./chart.png", "bytes")]
    assert sandbox.kill_calls == [
        {"api_key": "e2b-secret-key", "request_timeout": 12.0}
    ]


@pytest.mark.asyncio
async def test_e2b_adapter_create_error_maps_to_retryable_without_leaking_key() -> None:
    adapter = E2BRealSandboxClient(
        api_key="super-secret-e2b-key",
        request_timeout_seconds=12.0,
        execution_timeout_seconds=34.0,
        sandbox_timeout_seconds=600,
        sandbox_factory=FakeSandboxFactory(
            create_error=RuntimeError("provider exploded super-secret-e2b-key")
        ),
    )

    with pytest.raises(RetryableOperationError, match="e2b sandbox create failed") as exc:
        await adapter.create()

    assert "super-secret-e2b-key" not in str(exc.value)


@pytest.mark.asyncio
async def test_e2b_adapter_execute_error_maps_to_retryable() -> None:
    sandbox = FakeSandbox(
        files=FakeFilesystem(list_results=[[]]),
        run_error=RuntimeError("sandbox run failed"),
    )
    adapter = E2BRealSandboxClient(
        api_key="e2b-key",
        request_timeout_seconds=12.0,
        execution_timeout_seconds=34.0,
        sandbox_timeout_seconds=600,
        sandbox_factory=FakeSandboxFactory(sandbox=sandbox),
    )

    sandbox_id = await adapter.create()
    with pytest.raises(RetryableOperationError, match="e2b sandbox execute failed"):
        await adapter.execute_python(sandbox_id, "print('boom')")


@pytest.mark.asyncio
async def test_e2b_adapter_execution_error_returns_structured_failure_result() -> None:
    sandbox = FakeSandbox(
        files=FakeFilesystem(
            list_results=[
                [],
                [],
            ],
        ),
        execution=SimpleNamespace(
            logs=SimpleNamespace(
                stdout=["partial output"],
                stderr=["Traceback (most recent call last):", "ValueError: boom"],
            ),
            error=SimpleNamespace(
                name="ValueError",
                value="boom",
                traceback="Traceback (most recent call last):\nValueError: boom",
            ),
            text="partial output",
        ),
    )
    adapter = E2BRealSandboxClient(
        api_key="e2b-key",
        request_timeout_seconds=12.0,
        execution_timeout_seconds=34.0,
        sandbox_timeout_seconds=600,
        sandbox_factory=FakeSandboxFactory(sandbox=sandbox),
    )

    sandbox_id = await adapter.create()
    result = await adapter.execute_python(sandbox_id, "print('boom')")

    assert result.success is False
    assert result.stdout == "partial output"
    assert result.stderr == "Traceback (most recent call last):\nValueError: boom"
    assert result.error_type == "ValueError"
    assert result.error_message == "boom"
    assert result.traceback_excerpt == "Traceback (most recent call last):\nValueError: boom"
    assert result.artifacts == ()


@pytest.mark.asyncio
async def test_e2b_adapter_destroy_error_maps_to_retryable() -> None:
    sandbox = FakeSandbox(
        files=FakeFilesystem(list_results=[[]]),
        kill_error=RuntimeError("sandbox kill failed"),
    )
    adapter = E2BRealSandboxClient(
        api_key="e2b-key",
        request_timeout_seconds=12.0,
        execution_timeout_seconds=34.0,
        sandbox_timeout_seconds=600,
        sandbox_factory=FakeSandboxFactory(sandbox=sandbox),
    )

    sandbox_id = await adapter.create()
    with pytest.raises(RetryableOperationError, match="e2b sandbox destroy failed"):
        await adapter.destroy(sandbox_id)
