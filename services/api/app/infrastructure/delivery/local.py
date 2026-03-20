from io import BytesIO
from pathlib import Path
import tempfile
import zipfile

from app.application.dto.delivery import (
    GeneratedArtifact,
    OutlineDecision,
    OutlineInvocation,
    OutlineSection,
    ResearchOutline,
    SandboxExecutionResult,
    WriterDecision,
    WriterInvocation,
    WriterToolCall,
)


class LocalStubOutlineAgent:
    async def prepare(self, invocation: OutlineInvocation) -> OutlineDecision:
        return OutlineDecision(
            deltas=(),
            outline=ResearchOutline(
                title=f"{invocation.requirement_detail.research_goal}研究",
                sections=(
                    OutlineSection(
                        section_id="section_1",
                        title="研究背景与问题定义",
                        description="界定研究边界与分析框架。",
                        order=1,
                    ),
                    OutlineSection(
                        section_id="section_2",
                        title="竞争格局与主要玩家",
                        description="对比主要厂商与差异化能力。",
                        order=2,
                    ),
                ),
                entities=("AI 搜索产品", "中国市场", "竞争格局"),
            ),
        )


class LocalStubWriterAgent:
    async def write(self, invocation: WriterInvocation) -> WriterDecision:
        has_transcript = (
            invocation.prompt_bundle is not None
            and len(invocation.prompt_bundle.transcript) > 0
        )
        if not has_transcript:
            return WriterDecision(
                text="",
                tool_calls=(
                    WriterToolCall(
                        tool_call_id="call_writer_local_1",
                        tool_name="python_interpreter",
                        code="plot_local_market_share",
                    ),
                ),
            )
        return WriterDecision(
            text=(
                f"# {invocation.outline.title}\n\n"
                "## \u4e00\u3001\u7814\u7a76\u80cc\u666f\u4e0e\u95ee\u9898\u5b9a\u4e49\n"
                "\u4e2d\u56fd AI \u641c\u7d22\u5e02\u573a\u5728\u8fd1\u4e24\u5e74"
                "\u5feb\u901f\u6f14\u8fdb\u3002\n\n"
                "## \u4e8c\u3001\u7ade\u4e89\u683c\u5c40\u4e0e\u4e3b\u8981\u73a9\u5bb6\n"
                "\u6838\u5fc3\u73a9\u5bb6\u56f4\u7ed5\u641c\u7d22\u4f53\u9a8c\u3001"
                "\u6a21\u578b\u80fd\u529b\u4e0e\u5546\u4e1a\u5316\u8def\u5f84"
                "\u5c55\u5f00\u7ade\u4e89\u3002\n"
            ),
            tool_calls=(),
        )


class LocalStubSandboxClient:
    async def create(self) -> str:
        return "sandbox_local_1"

    async def execute_python(self, sandbox_id: str, code: str) -> SandboxExecutionResult:
        return SandboxExecutionResult(
            stdout=f"executed:{sandbox_id}:{code}",
            artifacts=(
                GeneratedArtifact(
                    filename="chart_market_share.png",
                    mime_type="image/png",
                    content=b"png-local-chart",
                ),
            ),
        )

    async def destroy(self, sandbox_id: str) -> None:
        return None


class LocalArtifactStore:
    def __init__(self, *, root_dir: Path | None = None) -> None:
        self.root_dir = root_dir or Path(tempfile.mkdtemp(prefix="mimir-artifacts-"))
        self.root_dir.mkdir(parents=True, exist_ok=True)

    async def put(self, storage_key: str, content: bytes, mime_type: str) -> None:
        path = self.root_dir / storage_key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    async def get(self, storage_key: str) -> bytes:
        return (self.root_dir / storage_key).read_bytes()

    async def delete(self, storage_key: str) -> None:
        path = self.root_dir / storage_key
        if not path.exists():
            return
        path.unlink()
        parent = path.parent
        while parent != self.root_dir and parent.exists():
            try:
                parent.rmdir()
            except OSError:
                break
            parent = parent.parent


class LocalReportExportService:
    async def build_markdown_zip(
        self,
        *,
        markdown: str,
        artifacts: tuple[GeneratedArtifact, ...],
    ) -> bytes:
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("report.md", markdown)
            for artifact in artifacts:
                archive.writestr(f"artifacts/{artifact.filename}", artifact.content)
        return buffer.getvalue()

    async def build_pdf(self, *, markdown: str) -> bytes:
        body = markdown.encode("utf-8")
        return b"%PDF-1.4\n" + body + b"\n%%EOF"
