from typing import Protocol

from app.application.dto.delivery import (
    GeneratedArtifact,
    OutlineDecision,
    OutlineInvocation,
    SandboxExecutionResult,
    WriterDecision,
    WriterInvocation,
)


class OutlineAgent(Protocol):
    async def prepare(self, invocation: OutlineInvocation) -> OutlineDecision: ...


class WriterAgent(Protocol):
    async def write(self, invocation: WriterInvocation) -> WriterDecision: ...


class E2BSandboxClient(Protocol):
    async def create(self) -> str: ...

    async def execute_python(self, sandbox_id: str, code: str) -> SandboxExecutionResult: ...

    async def destroy(self, sandbox_id: str) -> None: ...


class ArtifactStore(Protocol):
    async def put(self, storage_key: str, content: bytes, mime_type: str) -> None: ...

    async def get(self, storage_key: str) -> bytes: ...


class ReportExportService(Protocol):
    async def build_markdown_zip(
        self,
        *,
        markdown: str,
        artifacts: tuple[GeneratedArtifact, ...],
    ) -> bytes: ...

    async def build_pdf(self, *, markdown: str) -> bytes: ...
