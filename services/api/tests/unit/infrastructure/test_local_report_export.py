from base64 import b64decode
from io import BytesIO

import pytest
from pypdf import PdfReader

from app.application.dto.delivery import GeneratedArtifact
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
