from base64 import b64decode, b64encode
import logging
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from tempfile import TemporaryDirectory
import zipfile

from bs4 import BeautifulSoup, Tag
from markdown import markdown as render_markdown

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

logger = logging.getLogger(__name__)
_ONE_PIXEL_PNG = b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO3Z7xQAAAAASUVORK5CYII="
)
_PDF_FONT_PATH = (
    Path(__file__).resolve().parents[3]
    / "assets"
    / "fonts"
    / "NotoSansCJKsc-Regular.otf"
)
_PDF_ALLOWED_TAGS = {
    "a",
    "blockquote",
    "br",
    "code",
    "del",
    "div",
    "em",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "img",
    "li",
    "ol",
    "p",
    "pre",
    "span",
    "strong",
    "sup",
    "table",
    "tbody",
    "td",
    "thead",
    "th",
    "tr",
    "ul",
}
_PDF_DANGEROUS_TAGS = {
    "button",
    "embed",
    "form",
    "iframe",
    "input",
    "link",
    "meta",
    "object",
    "script",
    "select",
    "style",
    "svg",
    "textarea",
}
_PDF_ALLOWED_CLASSES = {
    "a": {"footnote-ref", "footnote-backref"},
    "div": {"footnote"},
    "span": {"footnote-label"},
}
_PDF_ALLOWED_ATTRIBUTES = {
    "a": {"class", "href"},
    "div": {"class"},
    "img": {"alt", "src"},
    "span": {"class"},
    "td": {"colspan", "rowspan"},
    "th": {"colspan", "rowspan"},
}


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
                "## 一、研究背景与问题定义\n"
                "中国 AI 搜索市场在近两年快速演进。\n\n"
                "## 二、竞争格局与主要玩家\n"
                "核心玩家围绕搜索体验、模型能力与商业化路径展开竞争。\n"
            ),
            tool_calls=(),
        )


class LocalStubSandboxClient:
    async def create(self) -> str:
        return "sandbox_local_1"

    async def execute_python(
        self,
        sandbox_id: str,
        code: str,
    ) -> SandboxExecutionResult:
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
    def __init__(self, *, chromium_executable: str | None = None) -> None:
        self._chromium_executable = chromium_executable

    async def build_markdown_zip(
        self,
        *,
        markdown: str,
        artifacts: tuple[GeneratedArtifact, ...],
    ) -> bytes:
        buffer = tempfile.SpooledTemporaryFile()
        try:
            with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("report.md", markdown)
                for artifact in artifacts:
                    archive.writestr(f"artifacts/{artifact.filename}", artifact.content)
            buffer.seek(0)
            return buffer.read()
        finally:
            buffer.close()

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
                html_body = _render_gfm_html(markdown=pdf_markdown)
                html_document = _build_pdf_html_document(html_body=html_body)
                return _render_pdf_from_html_document(
                    html_document=html_document,
                    temp_dir=temp_dir,
                    chromium_executable=self._chromium_executable,
                )
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
        rewritten = rewritten.replace(
            build_canonical_artifact_path(artifact.artifact_id),
            _build_data_uri(artifact.content, artifact.mime_type),
        )
    return rewritten


def _render_gfm_html(*, markdown: str) -> str:
    html = render_markdown(
        markdown,
        extensions=("extra", "sane_lists"),
        output_format="html5",
    )
    normalized_html = _normalize_gfm_html_for_pdf(html)
    return _sanitize_html_for_pdf(normalized_html)


def _normalize_gfm_html_for_pdf(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    for footnote_ref in soup.select("sup a.footnote-ref"):
        label = footnote_ref.get_text("", strip=True)
        if label:
            footnote_ref.string = f"[{label}]"

    for backref in soup.select("a.footnote-backref"):
        backref.decompose()

    for index, footnote_item in enumerate(soup.select("div.footnote > ol > li"), start=1):
        label = _extract_footnote_label(footnote_item, fallback_index=index)
        label_tag = soup.new_tag("span")
        label_tag["class"] = ["footnote-label"]
        label_tag.string = f"[{label}] "
        first_paragraph = footnote_item.find("p", recursive=False)
        if first_paragraph is not None:
            first_paragraph.insert(0, label_tag)
        else:
            footnote_item.insert(0, label_tag)

    return str(soup)


def _sanitize_html_for_pdf(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    for tag in list(soup.find_all(True)):
        if tag.name in _PDF_DANGEROUS_TAGS:
            tag.decompose()
            continue
        if tag.name not in _PDF_ALLOWED_TAGS:
            tag.unwrap()
            continue
        _sanitize_tag_attributes(tag)

    return str(soup)


def _sanitize_tag_attributes(tag: Tag) -> None:
    allowed_attributes = _PDF_ALLOWED_ATTRIBUTES.get(tag.name, set())
    for attribute_name in list(tag.attrs):
        if attribute_name.startswith("on"):
            del tag.attrs[attribute_name]
            continue
        if attribute_name not in allowed_attributes:
            del tag.attrs[attribute_name]
            continue

        if attribute_name == "class":
            allowed_classes = _PDF_ALLOWED_CLASSES.get(tag.name, set())
            values = tag.get(attribute_name) or []
            if isinstance(values, str):
                values = [values]
            sanitized = [value for value in values if value in allowed_classes]
            if sanitized:
                tag.attrs[attribute_name] = sanitized
            else:
                del tag.attrs[attribute_name]
            continue

        if attribute_name == "href":
            href = str(tag.attrs[attribute_name]).strip()
            if _is_safe_link_href(href):
                tag.attrs[attribute_name] = href
            else:
                del tag.attrs[attribute_name]
            continue

        if attribute_name == "src":
            src = str(tag.attrs[attribute_name]).strip()
            if tag.name == "img" and _is_safe_image_src(src):
                tag.attrs[attribute_name] = src
            else:
                del tag.attrs[attribute_name]


def _is_safe_link_href(value: str) -> bool:
    lower_value = value.lower()
    return (
        lower_value.startswith("http://")
        or lower_value.startswith("https://")
        or lower_value.startswith("mailto:")
        or value.startswith("#")
    )


def _is_safe_image_src(value: str) -> bool:
    lower_value = value.lower()
    return lower_value.startswith("data:image/png;base64,")


def _build_data_uri(content: bytes, mime_type: str) -> str:
    encoded = b64encode(content).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def _extract_footnote_label(item: Tag, *, fallback_index: int) -> str:
    item_id = item.get("id")
    if item_id and item_id.startswith("fn:"):
        suffix = item_id.split("fn:", 1)[1].strip()
        if suffix:
            return suffix
    return str(fallback_index)


def _build_pdf_html_document(*, html_body: str) -> str:
    return f"""<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <style>
{_build_pdf_stylesheet()}
    </style>
  </head>
  <body>
    <main class="report-body">
      {html_body}
    </main>
  </body>
</html>
""".strip()


def _build_pdf_stylesheet() -> str:
    font_face = ""
    if _PDF_FONT_PATH.exists():
        font_data = b64encode(_PDF_FONT_PATH.read_bytes()).decode("ascii")
        font_face = f"""
@font-face {{
  font-family: "MimirCJK";
  src: url("data:font/otf;base64,{font_data}") format("opentype");
}}
""".strip()

    return f"""
{font_face}

@page {{
  size: A4;
  margin: 18mm 16mm 18mm 16mm;
}}

html {{
  color: #111827;
  font-size: 11pt;
  line-height: 1.65;
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
}}

body {{
  margin: 0;
  font-family: "MimirCJK", "Noto Sans CJK SC", "PingFang SC", "Microsoft YaHei", sans-serif;
  word-break: break-word;
  overflow-wrap: anywhere;
}}

.report-body {{
  font-kerning: normal;
}}

h1, h2, h3, h4, h5, h6 {{
  color: #111827;
  font-weight: 700;
  line-height: 1.3;
  margin: 1.2em 0 0.6em;
  page-break-after: avoid;
  break-after: avoid-page;
}}

h1 {{
  font-size: 22pt;
  margin-top: 0;
}}

h2 {{
  font-size: 17pt;
}}

h3 {{
  font-size: 14pt;
}}

p, ul, ol, blockquote, table, pre {{
  margin: 0 0 0.95em;
}}

ul, ol {{
  padding-left: 1.4em;
}}

li + li {{
  margin-top: 0.2em;
}}

blockquote {{
  border-left: 3px solid #d0d7de;
  color: #374151;
  padding-left: 0.9em;
}}

code {{
  font-family: "SFMono-Regular", "Menlo", "Consolas", monospace;
  font-size: 0.92em;
  background: #f6f8fa;
  padding: 0.08em 0.28em;
  border-radius: 4px;
}}

pre {{
  white-space: pre-wrap;
  background: #f6f8fa;
  padding: 0.8em 0.95em;
  border-radius: 8px;
}}

pre code {{
  background: transparent;
  padding: 0;
}}

table {{
  width: 100%;
  border-collapse: collapse;
  border-spacing: 0;
  font-size: 10.2pt;
  table-layout: fixed;
}}

thead {{
  display: table-header-group;
}}

tr {{
  break-inside: avoid;
}}

th, td {{
  border: 1px solid #d0d7de;
  padding: 6px 8px;
  text-align: left;
  vertical-align: top;
}}

th {{
  background: #f6f8fa;
  font-weight: 700;
}}

img {{
  display: block;
  max-width: 100%;
  max-height: 220mm;
  height: auto;
  margin: 0.9em auto;
  break-inside: avoid;
}}

a {{
  color: #0b57d0;
  text-decoration: underline;
}}

sup {{
  font-size: 0.75em;
  line-height: 0;
}}

a.footnote-ref {{
  text-decoration: none;
  color: inherit;
}}

a.footnote-backref {{
  display: none;
}}

.footnote {{
  margin-top: 1.6em;
  padding-top: 0.6em;
  border-top: 1px solid #d0d7de;
  font-size: 9.6pt;
}}

.footnote ol {{
  list-style-type: none;
  padding-left: 0;
}}

.footnote li {{
  margin-bottom: 0.45em;
}}
""".strip()


def _render_pdf_from_html_document(
    *,
    html_document: str,
    temp_dir: Path,
    chromium_executable: str | None,
) -> bytes:
    input_path = temp_dir / "report.html"
    output_path = temp_dir / "report.pdf"
    input_path.write_text(html_document, encoding="utf-8")

    executable = _resolve_chromium_executable(chromium_executable)
    last_message = ""
    for headless_flag in ("--headless=new", "--headless"):
        if output_path.exists():
            output_path.unlink()
        command = [
            executable,
            headless_flag,
            "--disable-gpu",
            "--disable-dev-shm-usage",
            "--no-sandbox",
            "--no-pdf-header-footer",
            f"--print-to-pdf={output_path}",
            input_path.as_uri(),
        ]
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=90,
        )
        if result.returncode == 0 and output_path.exists():
            return output_path.read_bytes()
        last_message = (result.stderr or result.stdout or "").strip()

    raise RuntimeError(
        "chromium print-to-pdf failed"
        + (f": {last_message}" if last_message else "")
    )


def _resolve_chromium_executable(configured_executable: str | None) -> str:
    if configured_executable:
        configured_path = Path(configured_executable).expanduser()
        if _is_executable_file(configured_path):
            return str(configured_path)
        raise FileNotFoundError(
            f"Configured Chromium executable does not exist or is not executable: {configured_executable}"
        )

    for candidate in _iter_chromium_executable_candidates():
        if _is_executable_file(candidate):
            return str(candidate)

    raise FileNotFoundError(
        "Chromium executable not found. Install a headless Chromium runtime or set MIMIR_PDF_CHROMIUM_EXECUTABLE."
    )


def _iter_chromium_executable_candidates() -> tuple[Path, ...]:
    candidates: list[Path] = []

    home = Path.home()
    playwright_globs = (
        home / "Library" / "Caches" / "ms-playwright",
        home / ".cache" / "ms-playwright",
    )
    for root in playwright_globs:
        if not root.exists():
            continue
        candidates.extend(
            sorted(
                root.glob(
                    "chromium-*/chrome-mac*/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
                )
            )
        )
        candidates.extend(sorted(root.glob("chromium-*/chrome-linux/chrome")))
        candidates.extend(sorted(root.glob("chromium-*/chrome-linux64/chrome")))

    for name in (
        "chromium",
        "chromium-browser",
        "google-chrome",
        "google-chrome-stable",
        "chrome",
    ):
        resolved = shutil.which(name)
        if resolved:
            candidates.append(Path(resolved))

    if os.name == "posix" and Path("/Applications/Google Chrome.app").exists():
        candidates.append(
            Path(
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
            )
        )
    if os.name == "posix" and Path("/Applications/Chromium.app").exists():
        candidates.append(
            Path("/Applications/Chromium.app/Contents/MacOS/Chromium")
        )

    deduped: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)
    return tuple(deduped)


def _is_executable_file(path: Path) -> bool:
    return path.is_file() and os.access(path, os.X_OK)
