from base64 import b64decode
from io import BytesIO

import pytest
from pypdf import PdfReader
from reportlab.platypus import Spacer

from app.application.dto.delivery import GeneratedArtifact
from app.application.services.invocation import RetryableOperationError
import app.infrastructure.delivery.local as local_delivery
from app.infrastructure.delivery.local import LocalReportExportService

_ONE_PIXEL_PNG = b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO3Z7xQAAAAASUVORK5CYII="
)


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(pdf_bytes))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def _count_pdf_images(pdf_bytes: bytes) -> int:
    reader = PdfReader(BytesIO(pdf_bytes))
    count = 0

    for page in reader.pages:
        resources = page.get("/Resources")
        if resources is None:
            continue
        xobjects = resources.get("/XObject")
        if xobjects is None:
            continue
        for candidate in xobjects.values():
            obj = candidate.get_object()
            if obj.get("/Subtype") == "/Image":
                count += 1

    return count


def _build_multi_block_markdown() -> str:
    sections: list[str] = ["# 多页 PDF 导出稳定性验证"]
    for index in range(1, 19):
        sections.append(f"## 第 {index} 节")
        sections.append(
            "这是一段用于撑开 PDF 布局的较长正文，包含多个句子，用于验证 ReportLab 在多页渲染时不会因为复用同一个 Spacer flowable 而触发 LayoutError。"
            "我们需要让正文足够长，以便 story 跨页。"
        )
        sections.append("- 要点一：布局必须稳定。")
        sections.append("- 要点二：图片和列表要与段落共同出现。")
        if index in {3, 9}:
            artifact_id = "art_pdf_chart_1" if index == 3 else "art_pdf_chart_2"
            sections.append(f"![图表 {index}](mimir://artifact/{artifact_id})")
    return "\n\n".join(sections) + "\n"


def _build_footnote_markdown() -> str:
    return (
        "# 脚注 PDF 导出验证\n\n"
        "核心结论[^1] 与扩展判断[^2] 需要保留引用关系。\n\n"
        "[^1]: [第一来源](https://example.com/source-1)\n"
        "[^2]: [第二来源](https://example.com/source-2)\n"
    )


@pytest.mark.asyncio
async def test_build_pdf_returns_parseable_pdf_with_readable_text() -> None:
    pdf_bytes = await LocalReportExportService().build_pdf(
        markdown="# Seeded Report\n\nThis report can be opened by a real PDF reader.\n",
        artifacts=(),
    )

    reader = PdfReader(BytesIO(pdf_bytes))

    assert len(reader.pages) >= 1
    assert "Seeded Report" in _extract_pdf_text(pdf_bytes)
    assert "real PDF reader" in _extract_pdf_text(pdf_bytes)


@pytest.mark.asyncio
async def test_build_pdf_consumes_canonical_artifact_refs_without_renderer_errors() -> None:
    pdf_bytes = await LocalReportExportService().build_pdf(
        markdown=(
            "# Visual Report\n\n"
            "Intro paragraph.\n\n"
            "![Market share chart](mimir://artifact/art_pdf_chart)\n"
        ),
        artifacts=(
            GeneratedArtifact(
                artifact_id="art_pdf_chart",
                filename="chart_market_share.png",
                mime_type="image/png",
                content=_ONE_PIXEL_PNG,
            ),
        ),
    )

    assert "Visual Report" in _extract_pdf_text(pdf_bytes)
    assert _count_pdf_images(pdf_bytes) >= 1


@pytest.mark.asyncio
async def test_build_pdf_renders_gfm_footnotes_with_references_and_sources() -> None:
    pdf_bytes = await LocalReportExportService().build_pdf(
        markdown=_build_footnote_markdown(),
        artifacts=(),
    )

    pdf_text = _extract_pdf_text(pdf_bytes)

    assert "脚注 PDF 导出验证" in pdf_text
    assert "核心结论[1]" in pdf_text
    assert "扩展判断[2]" in pdf_text
    assert "[1] 第一来源" in pdf_text
    assert "[2] 第二来源" in pdf_text
    assert pdf_text.index("[1] 第一来源") < pdf_text.index("[2] 第二来源")


def test_build_pdf_story_uses_distinct_spacer_instances_per_block() -> None:
    html = local_delivery.render_markdown(
        _build_multi_block_markdown(),
        extensions=("extra", "sane_lists"),
    )

    story = local_delivery._build_pdf_story(html=html)
    spacers = [item for item in story if isinstance(item, Spacer)]

    assert len(spacers) >= 10
    assert len({id(item) for item in spacers}) == len(spacers)


@pytest.mark.asyncio
async def test_build_pdf_handles_multi_page_markdown_with_lists_and_images() -> None:
    pdf_bytes = await LocalReportExportService().build_pdf(
        markdown=_build_multi_block_markdown(),
        artifacts=(
            GeneratedArtifact(
                artifact_id="art_pdf_chart_1",
                filename="chart_market_share.png",
                mime_type="image/png",
                content=_ONE_PIXEL_PNG,
            ),
            GeneratedArtifact(
                artifact_id="art_pdf_chart_2",
                filename="chart_growth.png",
                mime_type="image/png",
                content=_ONE_PIXEL_PNG,
            ),
        ),
    )

    reader = PdfReader(BytesIO(pdf_bytes))

    assert len(reader.pages) >= 2
    assert "多页 PDF 导出稳定性验证" in _extract_pdf_text(pdf_bytes)
    assert _count_pdf_images(pdf_bytes) >= 2


@pytest.mark.asyncio
async def test_build_pdf_logs_real_exception_before_wrapping(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    def broken_story(*, html: str):
        raise ValueError("bad pdf story")

    monkeypatch.setattr(local_delivery, "_build_pdf_story", broken_story)

    with pytest.raises(RetryableOperationError, match="pdf render failed"):
        await LocalReportExportService().build_pdf(
            markdown="# Broken Report\n\nBody.\n",
            artifacts=(),
        )

    matching_logs = [
        record for record in caplog.records if record.message == "pdf export render failed"
    ]
    assert matching_logs
    assert matching_logs[-1].exception_type == "ValueError"
    assert matching_logs[-1].exception_message == "bad pdf story"
