from __future__ import annotations

import unicodedata
from pathlib import Path
from typing import Any
from uuid import uuid4

from pypdf import PdfReader

from agentpdf.artifacts.store import build_artifact
from agentpdf.core.page_ranges import parse_page_range
from agentpdf.schemas.errors import AgentPDFException
from agentpdf.schemas.models import ToolResult
from agentpdf.security.paths import resolve_input_path
from agentpdf.security.paths import resolve_output_path


def parse_lite_pdf(input_path: str | Path, pages: str = "all") -> ToolResult:
    tool = "pdf.ai.parse.lite"
    resolved = resolve_input_path(input_path)
    reader = _reader_for_lite_parse(resolved)
    selected_pages = parse_page_range(pages, total_pages=len(reader.pages))
    document_ir = _document_ir(resolved, reader, selected_pages)
    warnings = _warnings_for_ir(document_ir)
    block_count = sum(len(page["blocks"]) for page in document_ir["pages"])
    text_length = sum(
        len(block.get("text", ""))
        for page in document_ir["pages"]
        for block in page["blocks"]
    )
    return ToolResult(
        job_id=_job_id(),
        status="succeeded",
        tool=tool,
        warnings=warnings,
        usage={
            "input": str(resolved),
            "pages": [page + 1 for page in selected_pages],
            "document_ir": document_ir,
            "page_count": len(document_ir["pages"]),
            "block_count": block_count,
            "text_length": text_length,
            "parser": "pypdf_text_layer_heuristic",
        },
        next_recommended_tools=["pdf.ai.rag.ingest", "pdf.convert.pdf_to_text"],
    )


def write_document_ir_json(
    input_path: str | Path,
    output_path: str | Path,
    pages: str = "all",
) -> ToolResult:
    tool = "pdf.convert.pdf_to_json"
    parsed = parse_lite_pdf(input_path, pages=pages)
    output = resolve_output_path(output_path)
    output.write_text(
        json_dumps(parsed.usage["document_ir"]),
        encoding="utf-8",
    )
    artifact = build_artifact(output, source_tool=tool)
    return ToolResult(
        job_id=_job_id(),
        status="succeeded",
        tool=tool,
        artifacts=[artifact],
        warnings=parsed.warnings,
        usage={
            "input": parsed.usage["input"],
            "output_path": str(output),
            "page_count": parsed.usage["page_count"],
            "block_count": parsed.usage["block_count"],
            "format": "document_ir_json",
        },
        next_recommended_tools=["pdf.ai.rag.ingest", "pdf.convert.pdf_to_text"],
    )


def write_document_ir_markdown(
    input_path: str | Path,
    output_path: str | Path,
    pages: str = "all",
) -> ToolResult:
    tool = "pdf.convert.pdf_to_markdown"
    parsed = parse_lite_pdf(input_path, pages=pages)
    document_ir = parsed.usage["document_ir"]
    output = resolve_output_path(output_path)
    output.write_text(_markdown_from_ir(document_ir), encoding="utf-8")
    artifact = build_artifact(output, source_tool=tool)
    artifact.mime_type = "text/markdown"
    return ToolResult(
        job_id=_job_id(),
        status="succeeded",
        tool=tool,
        artifacts=[artifact],
        warnings=parsed.warnings,
        usage={
            "input": parsed.usage["input"],
            "output_path": str(output),
            "page_count": parsed.usage["page_count"],
            "block_count": parsed.usage["block_count"],
            "format": "document_ir_markdown",
        },
        next_recommended_tools=["pdf.ai.rag.ingest", "pdf.convert.pdf_to_json"],
    )


def json_dumps(value: Any) -> str:
    import json

    return json.dumps(value, indent=2, ensure_ascii=False)


def _markdown_from_ir(document_ir: dict[str, Any]) -> str:
    lines = [
        "<!-- okpdf: format=document_ir_markdown ir_version="
        f"{document_ir.get('ir_version', 'unknown')} -->",
        "",
    ]
    metadata = document_ir.get("metadata") or {}
    title = metadata.get("Title") or metadata.get("title")
    if title:
        lines.extend([f"# {title}", ""])

    for page in document_ir["pages"]:
        blocks = page.get("blocks", [])
        if not blocks:
            lines.extend([f"<!-- okpdf: page={page['page_number']} empty=true -->", ""])
            continue
        for block in blocks:
            lines.extend(
                [
                    "<!-- okpdf: "
                    f"page={page['page_number']} "
                    f"block={block.get('id')} "
                    f"bbox={block.get('bbox')} "
                    f"source={block.get('source')} -->",
                    block.get("text", "").strip(),
                    "",
                ]
            )
    return "\n".join(lines).rstrip() + "\n"


def _document_ir(resolved: Path, reader: PdfReader, selected_pages: list[int]) -> dict[str, Any]:
    metadata = {
        key.lstrip("/"): str(value)
        for key, value in (reader.metadata or {}).items()
        if value is not None
    }
    return {
        "ir_version": "0.1",
        "document_id": f"doc_{resolved.stem}",
        "source": {"kind": "local_path", "path": str(resolved)},
        "metadata": metadata,
        "pages": [_page_ir(reader, page_index) for page_index in selected_pages],
    }


def _page_ir(reader: PdfReader, page_index: int) -> dict[str, Any]:
    page = reader.pages[page_index]
    width = float(page.mediabox.width)
    height = float(page.mediabox.height)
    text = _normalize_text(page.extract_text() or "")
    blocks = []
    if text:
        blocks.append(
            {
                "id": f"p{page_index + 1}_b1",
                "type": "paragraph",
                "text": text,
                "bbox": [0, 0, width, height],
                "confidence": 0.62,
                "source": "pypdf.extract_text",
                "metadata": {"bbox_precision": "page", "reading_order": 1},
            }
        )
    return {
        "page_number": page_index + 1,
        "width": width,
        "height": height,
        "rotation": int(page.get("/Rotate", 0) or 0),
        "coordinate_origin": "bottom_left",
        "blocks": blocks,
    }


def _normalize_text(text: str) -> str:
    cleaned = "".join(
        char if char == "\n" or char == "\t" or not unicodedata.category(char).startswith("C") else " "
        for char in text.replace("\r\n", "\n")
    )
    lines = [line.strip() for line in cleaned.split("\n")]
    return "\n".join(line for line in lines if line).strip()


def _warnings_for_ir(document_ir: dict[str, Any]) -> list[str]:
    warnings = []
    for page in document_ir["pages"]:
        if not page["blocks"]:
            warnings.append(f"No text-layer blocks found on page {page['page_number']}.")
    return warnings


def _reader_for_lite_parse(path: Path) -> PdfReader:
    if path.suffix.lower() != ".pdf":
        raise AgentPDFException("unsupported_file_type", "Only PDF files are supported.")
    try:
        reader = PdfReader(path)
    except Exception as exc:
        raise AgentPDFException("pdf_parse_failed", f"Unable to parse PDF: {path}") from exc
    if reader.is_encrypted:
        raise AgentPDFException(
            "encrypted_pdf_requires_password",
            "Encrypted PDFs require an authorized password before processing.",
        )
    return reader


def _job_id() -> str:
    return f"job_{uuid4().hex[:16]}"
