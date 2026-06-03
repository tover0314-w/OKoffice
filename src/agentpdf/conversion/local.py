from __future__ import annotations

import html
import ipaddress
import re
import socket
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse
from urllib.request import Request, url2pathname, urlopen
from uuid import uuid4
from xml.etree import ElementTree as ET

from pypdf import PdfReader
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from agentpdf.artifacts.store import build_artifact
from agentpdf.core.page_ranges import parse_page_range
from agentpdf.schemas.errors import AgentPDFException
from agentpdf.schemas.models import ToolResult
from agentpdf.security.paths import resolve_input_path, resolve_output_path
from agentpdf.validation.pdf import validate_pdf


def html_to_pdf(input_path: str | Path, output_path: str | Path) -> ToolResult:
    tool = "pdf.convert.html_to_pdf"
    source = resolve_input_path(input_path)
    text = _html_to_text(source.read_text(encoding="utf-8", errors="replace"))
    return _text_pdf_result(
        tool,
        [line for line in text.splitlines() if line.strip()],
        output_path,
        {"input": str(source), "source_format": "html"},
        ["HTML/CSS layout is approximated as text in the local OSS converter."],
    )


def url_to_pdf(
    url: str,
    output_path: str | Path,
    *,
    allow_private_hosts: bool = False,
    allow_file_urls: bool = False,
) -> ToolResult:
    tool = "pdf.convert.url_to_pdf"
    parsed = urlparse(url)
    if parsed.scheme == "file":
        if not allow_file_urls:
            raise AgentPDFException(
                "unsafe_input_rejected",
                "file:// URL conversion requires explicit opt-in.",
            )
        source = _file_url_path(parsed.netloc, parsed.path)
        raw_html = source.read_text(encoding="utf-8", errors="replace")
        fetched = {"url": url, "scheme": "file", "bytes": len(raw_html.encode("utf-8"))}
    elif parsed.scheme in {"http", "https"}:
        _validate_public_url_host(parsed.hostname, allow_private_hosts)
        request = Request(url, headers={"User-Agent": "AgentPDF-Local/0.1"})
        with urlopen(request, timeout=10) as response:
            raw = response.read(1_000_000)
        raw_html = raw.decode("utf-8", errors="replace")
        fetched = {"url": url, "scheme": parsed.scheme, "bytes": len(raw)}
    else:
        raise AgentPDFException(
            "unsupported_file_type",
            "URL conversion supports http, https, and explicitly enabled file URLs.",
        )
    text = _html_to_text(raw_html)
    return _text_pdf_result(
        tool,
        [line for line in text.splitlines() if line.strip()],
        output_path,
        {"fetch": fetched, "source_format": "html"},
        ["HTML/CSS layout is approximated as text in the local OSS converter."],
    )


def docx_to_pdf(input_path: str | Path, output_path: str | Path) -> ToolResult:
    tool = "pdf.convert.docx_to_pdf"
    source = resolve_input_path(input_path)
    paragraphs = _read_docx_paragraphs(source)
    return _text_pdf_result(
        tool,
        paragraphs,
        output_path,
        {"input": str(source), "paragraph_count": len(paragraphs), "source_format": "docx"},
        ["DOCX styling, headers, footers, and tracked changes are not preserved."],
    )


def pptx_to_pdf(input_path: str | Path, output_path: str | Path) -> ToolResult:
    tool = "pdf.convert.pptx_to_pdf"
    source = resolve_input_path(input_path)
    slides = _read_pptx_slides(source)
    lines: list[str] = []
    for index, slide_lines in enumerate(slides, start=1):
        lines.append(f"Slide {index}")
        lines.extend(slide_lines or [""])
        lines.append("")
    return _text_pdf_result(
        tool,
        lines,
        output_path,
        {"input": str(source), "slide_count": len(slides), "source_format": "pptx"},
        ["Slide layout and speaker notes are approximated as text pages."],
    )


def xlsx_to_pdf(input_path: str | Path, output_path: str | Path) -> ToolResult:
    tool = "pdf.convert.xlsx_to_pdf"
    source = resolve_input_path(input_path)
    rows = _read_xlsx_rows(source)
    lines = [" | ".join(row) for row in rows]
    return _text_pdf_result(
        tool,
        lines,
        output_path,
        {"input": str(source), "row_count": len(rows), "source_format": "xlsx"},
        ["Workbook formulas, charts, styles, and multiple sheets are approximated as text rows."],
    )


def pdf_to_html(
    input_path: str | Path,
    output_path: str | Path,
    pages: str = "all",
) -> ToolResult:
    tool = "pdf.convert.pdf_to_html"
    source, reader, selected_pages = _pdf_context(input_path, pages)
    page_blocks = []
    for page_index in selected_pages:
        text = reader.pages[page_index].extract_text() or ""
        page_blocks.append(
            f'<section data-page="{page_index + 1}">\n'
            f"<pre>{html.escape(text)}</pre>\n"
            f"</section>"
        )
    document = "\n".join(
        [
            "<!doctype html>",
            '<html lang="en">',
            "<head><meta charset=\"utf-8\"><title>AgentPDF HTML Export</title></head>",
            "<body>",
            *page_blocks,
            "</body></html>",
        ]
    )
    output = resolve_output_path(output_path)
    output.write_text(document, encoding="utf-8")
    artifact = build_artifact(output, source_tool=tool)
    artifact.mime_type = "text/html"
    return ToolResult(
        job_id=_job_id(),
        status="succeeded",
        tool=tool,
        artifacts=[artifact],
        warnings=["PDF layout is exported as escaped text blocks, not layout-faithful HTML."],
        usage={
            "input": str(source),
            "selected_pages": [page + 1 for page in selected_pages],
            "html_sections": len(page_blocks),
        },
        next_recommended_tools=["pdf.convert.pdf_to_markdown"],
    )


def pdf_to_docx(
    input_path: str | Path,
    output_path: str | Path,
    pages: str = "all",
) -> ToolResult:
    tool = "pdf.convert.pdf_to_docx"
    source, reader, selected_pages = _pdf_context(input_path, pages)
    paragraphs = _pdf_page_texts(reader, selected_pages)
    output = resolve_output_path(output_path)
    _write_docx(output, paragraphs)
    artifact = build_artifact(output, source_tool=tool)
    return ToolResult(
        job_id=_job_id(),
        status="succeeded",
        tool=tool,
        artifacts=[artifact],
        warnings=["PDF text is exported as DOCX paragraphs; layout is not preserved."],
        usage={
            "input": str(source),
            "selected_pages": [page + 1 for page in selected_pages],
            "paragraph_count": len(paragraphs),
        },
        next_recommended_tools=["pdf.convert.pdf_to_markdown"],
    )


def pdf_to_pptx(
    input_path: str | Path,
    output_path: str | Path,
    pages: str = "all",
) -> ToolResult:
    tool = "pdf.convert.pdf_to_pptx"
    source, reader, selected_pages = _pdf_context(input_path, pages)
    slides = [[f"Page {page + 1}", reader.pages[page].extract_text() or ""] for page in selected_pages]
    output = resolve_output_path(output_path)
    _write_pptx(output, slides)
    artifact = build_artifact(output, source_tool=tool)
    return ToolResult(
        job_id=_job_id(),
        status="succeeded",
        tool=tool,
        artifacts=[artifact],
        warnings=["Each PDF page is exported as a simple text slide; layout is not preserved."],
        usage={
            "input": str(source),
            "selected_pages": [page + 1 for page in selected_pages],
            "slide_count": len(slides),
        },
        next_recommended_tools=["pdf.convert.pdf_to_images"],
    )


def pdf_to_xlsx(
    input_path: str | Path,
    output_path: str | Path,
    pages: str = "all",
) -> ToolResult:
    tool = "pdf.convert.pdf_to_xlsx"
    source, reader, selected_pages = _pdf_context(input_path, pages)
    rows = [["page_number", "text"]]
    for page_index in selected_pages:
        rows.append([str(page_index + 1), reader.pages[page_index].extract_text() or ""])
    output = resolve_output_path(output_path)
    _write_xlsx(output, rows)
    artifact = build_artifact(output, source_tool=tool)
    return ToolResult(
        job_id=_job_id(),
        status="succeeded",
        tool=tool,
        artifacts=[artifact],
        warnings=["Table reconstruction is not attempted; page text is exported row-by-row."],
        usage={
            "input": str(source),
            "selected_pages": [page + 1 for page in selected_pages],
            "row_count": len(rows),
        },
        next_recommended_tools=["pdf.ai.parse.tables"],
    )


def _text_pdf_result(
    tool: str,
    lines: list[str],
    output_path: str | Path,
    usage: dict[str, Any],
    warnings: list[str],
) -> ToolResult:
    output = resolve_output_path(output_path)
    _write_text_pdf(output, lines or [""])
    artifact = build_artifact(output, source_tool=tool)
    validation = validate_pdf(output)
    return ToolResult(
        job_id=_job_id(),
        status="succeeded" if validation.status == "passed" else "failed",
        tool=tool,
        artifacts=[artifact],
        validation=validation,
        warnings=warnings + (validation.warnings or []),
        usage={**usage, "output": str(output), "line_count": len(lines)},
        next_recommended_tools=["pdf.inspect.document", "pdf.validation.render_check"],
    )


def _write_text_pdf(path: Path, lines: list[str]) -> None:
    document = canvas.Canvas(str(path), pagesize=letter)
    width, height = letter
    margin = 72
    y = height - margin
    for raw_line in lines:
        chunks = _wrap_text(raw_line, 92)
        for line in chunks or [""]:
            if y < margin:
                document.showPage()
                y = height - margin
            document.drawString(margin, y, line)
            y -= 16
    document.save()


def _wrap_text(text: str, size: int) -> list[str]:
    if len(text) <= size:
        return [text]
    return [text[index : index + size] for index in range(0, len(text), size)]


def _pdf_context(input_path: str | Path, pages: str) -> tuple[Path, PdfReader, list[int]]:
    source = resolve_input_path(input_path)
    try:
        reader = PdfReader(source)
    except Exception as exc:
        raise AgentPDFException("pdf_parse_failed", f"Unable to parse PDF: {source}") from exc
    if reader.is_encrypted:
        raise AgentPDFException(
            "encrypted_pdf_requires_password",
            "Encrypted PDFs require an authorized password before conversion.",
        )
    selected_pages = parse_page_range(pages, total_pages=len(reader.pages))
    return source, reader, selected_pages


def _pdf_page_texts(reader: PdfReader, selected_pages: list[int]) -> list[str]:
    paragraphs = []
    for page_index in selected_pages:
        text = reader.pages[page_index].extract_text() or ""
        paragraphs.extend(line.strip() for line in text.splitlines() if line.strip())
    return paragraphs


def _read_docx_paragraphs(path: Path) -> list[str]:
    if path.suffix.lower() != ".docx":
        raise AgentPDFException("unsupported_file_type", "Only .docx files are supported.")
    try:
        with zipfile.ZipFile(path) as archive:
            xml = archive.read("word/document.xml")
    except Exception as exc:
        raise AgentPDFException("pdf_parse_failed", f"Unable to parse DOCX: {path}") from exc
    root = ET.fromstring(xml)
    paragraphs = []
    for para in root.findall(".//{*}p"):
        text = "".join(node.text or "" for node in para.findall(".//{*}t")).strip()
        if text:
            paragraphs.append(text)
    return paragraphs


def _read_pptx_slides(path: Path) -> list[list[str]]:
    if path.suffix.lower() != ".pptx":
        raise AgentPDFException("unsupported_file_type", "Only .pptx files are supported.")
    try:
        with zipfile.ZipFile(path) as archive:
            names = sorted(
                [name for name in archive.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", name)],
                key=_natural_key,
            )
            slides = []
            for name in names:
                root = ET.fromstring(archive.read(name))
                slides.append([node.text or "" for node in root.findall(".//{*}t") if node.text])
            return slides
    except Exception as exc:
        raise AgentPDFException("pdf_parse_failed", f"Unable to parse PPTX: {path}") from exc


def _read_xlsx_rows(path: Path) -> list[list[str]]:
    if path.suffix.lower() != ".xlsx":
        raise AgentPDFException("unsupported_file_type", "Only .xlsx files are supported.")
    try:
        with zipfile.ZipFile(path) as archive:
            sheet_names = [name for name in archive.namelist() if name.startswith("xl/worksheets/")]
            if not sheet_names:
                return []
            root = ET.fromstring(archive.read(sorted(sheet_names)[0]))
            rows = []
            for row in root.findall(".//{*}row"):
                values = []
                for cell in row.findall("{*}c"):
                    text_node = cell.find(".//{*}t")
                    value_node = cell.find("{*}v")
                    values.append((text_node.text if text_node is not None else value_node.text if value_node is not None else "") or "")
                rows.append(values)
            return rows
    except Exception as exc:
        raise AgentPDFException("pdf_parse_failed", f"Unable to parse XLSX: {path}") from exc


def _write_docx(path: Path, paragraphs: list[str]) -> None:
    body = "".join(
        f"<w:p><w:r><w:t>{html.escape(paragraph)}</w:t></w:r></w:p>"
        for paragraph in paragraphs
    )
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            (
                '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                '<Default Extension="xml" ContentType="application/xml"/>'
                '<Override PartName="/word/document.xml" '
                'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
                "</Types>"
            ),
        )
        archive.writestr(
            "_rels/.rels",
            (
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
                'Target="word/document.xml"/></Relationships>'
            ),
        )
        archive.writestr(
            "word/document.xml",
            (
                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                f"<w:body>{body}</w:body></w:document>"
            ),
        )


def _write_pptx(path: Path, slides: list[list[str]]) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types />")
        archive.writestr("_rels/.rels", "<Relationships />")
        archive.writestr("ppt/presentation.xml", "<presentation />")
        for index, lines in enumerate(slides, start=1):
            text = " ".join(html.escape(line) for line in lines if line)
            archive.writestr(
                f"ppt/slides/slide{index}.xml",
                (
                    '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
                    'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
                    f"<p:cSld><p:spTree><p:sp><p:txBody><a:p><a:r><a:t>{text}</a:t></a:r>"
                    "</a:p></p:txBody></p:sp></p:spTree></p:cSld></p:sld>"
                ),
            )


def _write_xlsx(path: Path, rows: list[list[str]]) -> None:
    row_xml = []
    for row_index, row in enumerate(rows, start=1):
        cells = []
        for column_index, value in enumerate(row, start=1):
            cell_ref = f"{_xlsx_column(column_index)}{row_index}"
            cells.append(
                f'<c r="{cell_ref}" t="inlineStr"><is><t>{html.escape(value)}</t></is></c>'
            )
        row_xml.append(f'<row r="{row_index}">{"".join(cells)}</row>')
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types />")
        archive.writestr("_rels/.rels", "<Relationships />")
        archive.writestr("xl/workbook.xml", "<workbook />")
        archive.writestr(
            "xl/worksheets/sheet1.xml",
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            f"<sheetData>{''.join(row_xml)}</sheetData></worksheet>",
        )


def _xlsx_column(index: int) -> str:
    name = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"p", "br", "div", "section", "article", "h1", "h2", "h3", "li"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if text:
            self.parts.append(text)

    def text(self) -> str:
        return "\n".join(part.strip() for part in self.parts if part.strip())


def _html_to_text(raw_html: str) -> str:
    parser = _TextExtractor()
    parser.feed(raw_html)
    return parser.text()


def _validate_public_url_host(hostname: str | None, allow_private_hosts: bool) -> None:
    if allow_private_hosts:
        return
    if not hostname:
        raise AgentPDFException("unsafe_input_rejected", "URL must include a host.")
    try:
        addresses = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise AgentPDFException("pdf_parse_failed", f"Unable to resolve URL host: {hostname}") from exc
    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast:
            raise AgentPDFException(
                "unsafe_input_rejected",
                "Private or local URL hosts are blocked by default.",
            )


def _file_url_path(netloc: str, path: str) -> Path:
    if netloc and netloc.lower() != "localhost":
        raise AgentPDFException(
            "unsafe_input_rejected",
            "file:// URL conversion only supports local file URLs.",
        )
    return Path(url2pathname(unquote(path))).resolve()


def _natural_key(name: str) -> list[int | str]:
    return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", name)]


def _job_id() -> str:
    return f"job_{uuid4().hex[:16]}"
