from base64 import b64decode
from html import escape
from io import BytesIO
import logging
from pathlib import Path
import re
import tempfile
from tempfile import TemporaryDirectory
from urllib.parse import urlparse
import zipfile

from bs4 import BeautifulSoup, NavigableString, Tag
from markdown import markdown as render_markdown
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import Image as PlatypusImage
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

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
    build_canonical_artifact_path,
)
from app.application.services.invocation import RetryableOperationError

_PDF_FONT_NAME = "STSong-Light"
logger = logging.getLogger(__name__)
_ONE_PIXEL_PNG = b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO3Z7xQAAAAASUVORK5CYII="
)


def _block_spacer() -> Spacer:
    return Spacer(1, 0.16 * inch)


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
            success=True,
            stdout=f"executed:{sandbox_id}:{code}",
            artifacts=(
                GeneratedArtifact(
                    filename="chart_market_share.png",
                    mime_type="image/png",
                    content=_ONE_PIXEL_PNG,
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

    async def build_pdf(
        self,
        *,
        markdown: str,
        artifacts: tuple[GeneratedArtifact, ...],
    ) -> bytes:
        try:
            with TemporaryDirectory(prefix="mimir-pdf-export-") as temp_dir_name:
                temp_dir = Path(temp_dir_name)
                pdf_markdown = _rewrite_markdown_artifact_refs_for_pdf(
                    markdown=markdown,
                    artifacts=artifacts,
                    temp_dir=temp_dir,
                )
                html = render_markdown(
                    pdf_markdown,
                    extensions=("extra", "sane_lists"),
                )
                story = _build_pdf_story(html=html)
                buffer = BytesIO()
                document = SimpleDocTemplate(
                    buffer,
                    pagesize=A4,
                    leftMargin=0.75 * inch,
                    rightMargin=0.75 * inch,
                    topMargin=0.75 * inch,
                    bottomMargin=0.75 * inch,
                    title="Mimir Report",
                )
                document.build(story or [Paragraph(" ", _pdf_styles()["body"])])
                return buffer.getvalue()
        except RetryableOperationError:
            raise
        except Exception as exc:  # pragma: no cover - defensive wrapper
            logger.error(
                "pdf export render failed",
                extra={
                    "markdown_chars": len(markdown),
                    "artifact_count": len(artifacts),
                    "artifact_filenames": [artifact.filename for artifact in artifacts],
                    "exception_type": type(exc).__name__,
                    "exception_message": str(exc),
                },
                exc_info=True,
            )
            raise RetryableOperationError("pdf render failed") from exc


def _ensure_pdf_font_registered() -> None:
    if _PDF_FONT_NAME not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(UnicodeCIDFont(_PDF_FONT_NAME))


def _pdf_styles() -> dict[str, ParagraphStyle]:
    _ensure_pdf_font_registered()
    stylesheet = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "MimirPdfTitle",
            parent=stylesheet["Heading1"],
            fontName=_PDF_FONT_NAME,
            fontSize=20,
            leading=28,
            spaceAfter=14,
        ),
        "heading_2": ParagraphStyle(
            "MimirPdfHeading2",
            parent=stylesheet["Heading2"],
            fontName=_PDF_FONT_NAME,
            fontSize=16,
            leading=22,
            spaceBefore=6,
            spaceAfter=10,
        ),
        "heading_3": ParagraphStyle(
            "MimirPdfHeading3",
            parent=stylesheet["Heading3"],
            fontName=_PDF_FONT_NAME,
            fontSize=13,
            leading=18,
            spaceBefore=4,
            spaceAfter=8,
        ),
        "body": ParagraphStyle(
            "MimirPdfBody",
            parent=stylesheet["BodyText"],
            fontName=_PDF_FONT_NAME,
            fontSize=10.5,
            leading=16,
            spaceAfter=8,
        ),
        "bullet": ParagraphStyle(
            "MimirPdfBullet",
            parent=stylesheet["BodyText"],
            fontName=_PDF_FONT_NAME,
            fontSize=10.5,
            leading=16,
            leftIndent=14,
            firstLineIndent=-10,
            spaceAfter=6,
        ),
        "footnote": ParagraphStyle(
            "MimirPdfFootnote",
            parent=stylesheet["BodyText"],
            fontName=_PDF_FONT_NAME,
            fontSize=9.5,
            leading=14,
            leftIndent=10,
            spaceAfter=5,
        ),
    }


def _rewrite_markdown_artifact_refs_for_pdf(
    *,
    markdown: str,
    artifacts: tuple[GeneratedArtifact, ...],
    temp_dir: Path,
) -> str:
    rewritten = markdown
    for artifact in artifacts:
        if artifact.artifact_id is None:
            continue
        safe_filename = f"{artifact.artifact_id}_{Path(artifact.filename).name}"
        path = temp_dir / safe_filename
        path.write_bytes(artifact.content)
        rewritten = rewritten.replace(
            build_canonical_artifact_path(artifact.artifact_id),
            path.as_uri(),
        )
    return rewritten


def _build_pdf_story(*, html: str) -> list:
    styles = _pdf_styles()
    soup = BeautifulSoup(f"<body>{html}</body>", "html.parser")
    body = soup.body
    if body is None:
        return []

    story: list = []
    for node in body.children:
        if isinstance(node, NavigableString):
            if node.strip():
                story.append(Paragraph(escape(node.strip()), styles["body"]))
                story.append(_block_spacer())
            continue
        if not isinstance(node, Tag):
            continue
        story.extend(_render_html_block(node=node, styles=styles))
    return story


def _render_html_block(*, node: Tag, styles: dict[str, ParagraphStyle]) -> list:
    if node.name == "div" and "footnote" in (node.get("class") or []):
        return _render_footnote_block(node=node, styles=styles)
    if node.name == "h1":
        return [Paragraph(escape(node.get_text(" ", strip=True)), styles["title"])]
    if node.name == "h2":
        return [Paragraph(escape(node.get_text(" ", strip=True)), styles["heading_2"])]
    if node.name == "h3":
        return [Paragraph(escape(node.get_text(" ", strip=True)), styles["heading_3"])]
    if node.name in {"p", "div"}:
        return _render_paragraph_like(node=node, styles=styles)
    if node.name in {"ul", "ol"}:
        return _render_list(node=node, styles=styles)
    if node.name == "blockquote":
        markup = _render_inline_markup(node)
        if not markup:
            return []
        return [Paragraph(markup, styles["body"]), _block_spacer()]
    if node.name == "hr":
        return [_block_spacer()]
    markup = _render_inline_markup(node)
    if not markup:
        return []
    return [Paragraph(markup, styles["body"]), _block_spacer()]


def _render_paragraph_like(*, node: Tag, styles: dict[str, ParagraphStyle]) -> list:
    story: list = []
    markup = _render_inline_markup(node)
    if markup:
        story.append(Paragraph(markup, styles["body"]))
    for image in node.find_all("img"):
        flowable = _build_image_flowable(src=image.get("src"))
        if flowable is not None:
            story.append(flowable)
    if story:
        story.append(_block_spacer())
    return story


def _render_list(*, node: Tag, styles: dict[str, ParagraphStyle]) -> list:
    story: list = []
    ordered = node.name == "ol"
    for index, item in enumerate(node.find_all("li", recursive=False), start=1):
        prefix = f"{index}. " if ordered else "• "
        markup = _render_inline_markup(item)
        if markup:
            story.append(Paragraph(f"{escape(prefix)}{markup}", styles["bullet"]))
        for image in item.find_all("img"):
            flowable = _build_image_flowable(src=image.get("src"))
            if flowable is not None:
                story.append(flowable)
    if story:
        story.append(_block_spacer())
    return story


def _render_footnote_block(*, node: Tag, styles: dict[str, ParagraphStyle]) -> list:
    story: list = []
    footnotes = node.select("ol > li")
    for index, item in enumerate(footnotes, start=1):
        label = _extract_footnote_label(item=item, fallback_index=index)
        markup = _render_inline_markup(item)
        if not markup:
            continue
        story.append(Paragraph(f"[{escape(label)}] {markup}", styles["footnote"]))
    if story:
        story.append(_block_spacer())
    return story


def _extract_footnote_label(*, item: Tag, fallback_index: int) -> str:
    item_id = item.get("id")
    if item_id and item_id.startswith("fn:"):
        suffix = item_id.split("fn:", 1)[1].strip()
        if suffix:
            return suffix
    return str(fallback_index)


def _render_inline_markup(node: Tag) -> str:
    rendered = "".join(_render_inline_node(child) for child in node.children)
    return _normalize_inline_markup(rendered)


def _render_inline_node(node: Tag | NavigableString) -> str:
    if isinstance(node, NavigableString):
        return escape(str(node).replace("\xa0", " "))
    if not isinstance(node, Tag):
        return ""
    if node.name == "img":
        return ""
    if node.name == "br":
        return "<br/>"
    if node.name == "sup":
        if any(
            isinstance(child, Tag) and "footnote-ref" in (child.get("class") or [])
            for child in node.children
        ):
            return "".join(_render_inline_node(child) for child in node.children)
        content = _normalize_inline_markup(
            "".join(_render_inline_node(child) for child in node.children)
        )
        if not content:
            return ""
        return f"<super>{content}</super>"
    if node.name == "a":
        classes = set(node.get("class") or [])
        if "footnote-backref" in classes:
            return ""
        if "footnote-ref" in classes:
            number = escape(node.get_text("", strip=True))
            return f"<super>[{number}]</super>" if number else ""

        content = _normalize_inline_markup(
            "".join(_render_inline_node(child) for child in node.children)
        )
        if not content:
            return ""

        href = (node.get("href") or "").strip()
        if not href or href.startswith("#"):
            return content
        return f'<link href="{escape(href, quote=True)}">{content}</link>'
    if node.name in {"strong", "b"}:
        content = _normalize_inline_markup(
            "".join(_render_inline_node(child) for child in node.children)
        )
        return f"<b>{content}</b>" if content else ""
    if node.name in {"em", "i"}:
        content = _normalize_inline_markup(
            "".join(_render_inline_node(child) for child in node.children)
        )
        return f"<i>{content}</i>" if content else ""
    if node.name == "code":
        content = _normalize_inline_markup(
            "".join(_render_inline_node(child) for child in node.children)
        )
        return f'<font name="Courier">{content}</font>' if content else ""
    return "".join(_render_inline_node(child) for child in node.children)


def _normalize_inline_markup(markup: str) -> str:
    if not markup:
        return ""
    normalized = markup.replace("\r", " ").replace("\n", " ").replace("\xa0", " ")
    normalized = re.sub(r"[ \t\f\v]+", " ", normalized)
    normalized = re.sub(r"\s*<br/>\s*", "<br/>", normalized)
    return normalized.strip()


def _build_image_flowable(*, src: str | None):
    if not src:
        return None
    path = _resolve_pdf_image_path(src)
    if path is None or not path.exists():
        return None
    width, height = ImageReader(str(path)).getSize()
    if width <= 0 or height <= 0:
        return None
    max_width = 6.5 * inch
    max_height = 6.5 * inch
    scale = min(max_width / width, max_height / height, 1)
    image = PlatypusImage(str(path), width=width * scale, height=height * scale)
    image.hAlign = "LEFT"
    return image


def _resolve_pdf_image_path(src: str) -> Path | None:
    parsed = urlparse(src)
    if parsed.scheme == "file":
        return Path(parsed.path)
    if parsed.scheme:
        return None
    return Path(src)
