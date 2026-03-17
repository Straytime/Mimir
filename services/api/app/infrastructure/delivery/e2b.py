from collections.abc import Awaitable, Callable
from pathlib import PurePosixPath
from typing import Any, Protocol

from app.application.dto.delivery import GeneratedArtifact, SandboxExecutionResult
from app.application.services.invocation import RetryableOperationError


class E2BFilesystem(Protocol):
    async def list(
        self,
        path: str,
        depth: int | None = 1,
        user: str | None = None,
        request_timeout: float | None = None,
    ) -> list[Any]: ...

    async def read(
        self,
        path: str,
        format: str = "text",
        user: str | None = None,
        request_timeout: float | None = None,
    ) -> Any: ...


class E2BSandbox(Protocol):
    sandbox_id: str
    files: E2BFilesystem

    async def run_code(
        self,
        code: str,
        language: str | None = None,
        timeout: float | None = None,
        request_timeout: float | None = None,
    ) -> Any: ...

    async def kill(self, **opts: Any) -> bool: ...


class E2BSandboxFactory(Protocol):
    async def create(
        self,
        *,
        timeout: int | None = None,
        request_timeout: float | None = None,
        api_key: str | None = None,
    ) -> E2BSandbox: ...


def create_default_e2b_sandbox_factory() -> E2BSandboxFactory:
    from e2b_code_interpreter import AsyncSandbox

    return AsyncSandbox


class E2BRealSandboxClient:
    def __init__(
        self,
        *,
        api_key: str,
        request_timeout_seconds: float,
        execution_timeout_seconds: float,
        sandbox_timeout_seconds: int,
        sandbox_factory: E2BSandboxFactory | None = None,
        artifact_scan_root: str = ".",
    ) -> None:
        self._api_key = api_key
        self._request_timeout_seconds = request_timeout_seconds
        self._execution_timeout_seconds = execution_timeout_seconds
        self._sandbox_timeout_seconds = sandbox_timeout_seconds
        self._sandbox_factory = sandbox_factory or create_default_e2b_sandbox_factory()
        self._artifact_scan_root = artifact_scan_root
        self._sandboxes: dict[str, E2BSandbox] = {}

    async def create(self) -> str:
        try:
            sandbox = await self._sandbox_factory.create(
                timeout=self._sandbox_timeout_seconds,
                request_timeout=self._request_timeout_seconds,
                api_key=self._api_key,
            )
        except Exception as exc:
            raise RetryableOperationError("e2b sandbox create failed") from exc

        self._sandboxes[sandbox.sandbox_id] = sandbox
        return sandbox.sandbox_id

    async def execute_python(self, sandbox_id: str, code: str) -> SandboxExecutionResult:
        sandbox = self._sandboxes.get(sandbox_id)
        if sandbox is None:
            raise RetryableOperationError("e2b sandbox execute failed")

        try:
            before_paths = await self._list_png_paths(sandbox)
            execution = await sandbox.run_code(
                code,
                language="python",
                timeout=self._execution_timeout_seconds,
                request_timeout=self._request_timeout_seconds,
            )
        except Exception as exc:
            raise RetryableOperationError("e2b sandbox execute failed") from exc

        if getattr(execution, "error", None) is not None:
            raise RetryableOperationError("e2b sandbox execute failed")

        try:
            after_paths = await self._list_png_paths(sandbox)
            artifacts = await self._load_new_artifacts(
                sandbox=sandbox,
                before_paths=before_paths,
                after_paths=after_paths,
            )
        except Exception as exc:
            raise RetryableOperationError("e2b sandbox artifact read failed") from exc

        return SandboxExecutionResult(
            stdout=_extract_execution_stdout(execution),
            artifacts=artifacts,
        )

    async def destroy(self, sandbox_id: str) -> None:
        sandbox = self._sandboxes.pop(sandbox_id, None)
        if sandbox is None:
            return
        try:
            await sandbox.kill(
                api_key=self._api_key,
                request_timeout=self._request_timeout_seconds,
            )
        except Exception as exc:
            raise RetryableOperationError("e2b sandbox destroy failed") from exc

    async def shutdown(self) -> None:
        pending_ids = tuple(self._sandboxes)
        for sandbox_id in pending_ids:
            try:
                await self.destroy(sandbox_id)
            except RetryableOperationError:
                continue

    async def _list_png_paths(self, sandbox: E2BSandbox) -> set[str]:
        entries = await sandbox.files.list(
            self._artifact_scan_root,
            depth=4,
            request_timeout=self._request_timeout_seconds,
        )
        paths: set[str] = set()
        for entry in entries:
            path = str(getattr(entry, "path", "") or "")
            if path.lower().endswith(".png"):
                paths.add(path)
        return paths

    async def _load_new_artifacts(
        self,
        *,
        sandbox: E2BSandbox,
        before_paths: set[str],
        after_paths: set[str],
    ) -> tuple[GeneratedArtifact, ...]:
        artifacts: list[GeneratedArtifact] = []
        for path in sorted(after_paths - before_paths):
            content = await sandbox.files.read(
                path,
                format="bytes",
                request_timeout=self._request_timeout_seconds,
            )
            artifacts.append(
                GeneratedArtifact(
                    filename=PurePosixPath(path).name,
                    mime_type="image/png",
                    content=bytes(content),
                )
            )
        return tuple(artifacts)


def _extract_execution_stdout(execution: Any) -> str:
    logs = getattr(execution, "logs", None)
    if logs is not None:
        stdout_lines = getattr(logs, "stdout", None)
        if isinstance(stdout_lines, list):
            return "\n".join(str(line) for line in stdout_lines)
    text = getattr(execution, "text", None)
    if isinstance(text, str):
        return text
    return ""
