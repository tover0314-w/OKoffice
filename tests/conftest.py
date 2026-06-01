from pathlib import Path

import pytest
from pypdf import PdfWriter
from reportlab.pdfgen import canvas


@pytest.fixture()
def fixture_dir() -> Path:
    root = Path(__file__).parent / "fixtures"
    root.mkdir(parents=True, exist_ok=True)
    _write_blank_pdf(root / "simple.pdf", pages=1)
    _write_blank_pdf(root / "two_pages.pdf", pages=2)
    return root


@pytest.fixture()
def simple_pdf(fixture_dir: Path) -> Path:
    return fixture_dir / "simple.pdf"


@pytest.fixture()
def two_page_pdf(fixture_dir: Path) -> Path:
    return fixture_dir / "two_pages.pdf"


@pytest.fixture()
def text_pdf(fixture_dir: Path) -> Path:
    path = fixture_dir / "text.pdf"
    _write_text_pdf(path, "AgentPDF local text layer")
    return path


@pytest.fixture()
def metadata_pdf(fixture_dir: Path) -> Path:
    path = fixture_dir / "metadata.pdf"
    _write_text_pdf(path, "Metadata fixture", title="Original Title", author="AgentPDF Tests")
    return path


def _write_blank_pdf(path: Path, pages: int) -> None:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=612, height=792)
    with path.open("wb") as handle:
        writer.write(handle)


def _write_text_pdf(
    path: Path,
    text: str,
    title: str | None = None,
    author: str | None = None,
) -> None:
    doc = canvas.Canvas(str(path))
    if title:
        doc.setTitle(title)
    if author:
        doc.setAuthor(author)
    doc.drawString(72, 720, text)
    doc.save()
