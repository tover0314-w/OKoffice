from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from uuid import uuid4

from pypdf import PdfReader

from okoffice.core.page_ranges import parse_page_range
from okoffice.schemas.errors import OKofficeException
from okoffice.schemas.models import ToolResult
from okoffice.security.paths import resolve_input_path


FIGURE_RE = re.compile(r"\b(?:fig(?:ure)?\.?\s*\d+[:.\-]?\s+.+)", re.IGNORECASE)
CHART_RE = re.compile(r"\b(?:chart|graph|plot)\s*\d*[:.\-]?\s+.+", re.IGNORECASE)
FORMULA_RE = re.compile(r"(?=.*[=+\-*/^])(?=.*[A-Za-z0-9]).{3,}")
REFERENCE_RE = re.compile(r"^(?:\[\d+\]|\d+\.|\w.+\(\d{4}\)|https?://|doi:)", re.IGNORECASE)


def parse_figures_pdf(input_path: str | Path, pages: str = "all") -> ToolResult:
    tool = "pdf.ai.parse.figures"
    resolved, reader, selected_pages = _parse_context(input_path, pages)
    findings = []
    for page_index in selected_pages:
        captions = _matching_lines(reader, page_index, FIGURE_RE)
        image_count = _count_page_images(reader.pages[page_index])
        for caption in captions:
            findings.append(
                {
                    "page_number": page_index + 1,
                    "caption": caption,
                    "image_count_on_page": image_count,
                    "bbox": [0, 0, float(reader.pages[page_index].mediabox.width), float(reader.pages[page_index].mediabox.height)],
                    "confidence": 0.58 if image_count else 0.42,
                    "source": "text_caption_image_count_heuristic",
                }
            )
        if image_count and not captions:
            findings.append(
                {
                    "page_number": page_index + 1,
                    "caption": None,
                    "image_count_on_page": image_count,
                    "bbox": [0, 0, float(reader.pages[page_index].mediabox.width), float(reader.pages[page_index].mediabox.height)],
                    "confidence": 0.36,
                    "source": "image_xobject_heuristic",
                }
            )
    return _semantic_result(
        tool,
        resolved,
        selected_pages,
        "figures",
        findings,
        "figure_count",
        ["pdf.convert.extract_images", "pdf.ai.parse.charts"],
    )


def parse_formulas_pdf(input_path: str | Path, pages: str = "all") -> ToolResult:
    tool = "pdf.ai.parse.formulas"
    resolved, reader, selected_pages = _parse_context(input_path, pages)
    findings = []
    for page_index in selected_pages:
        for line in _matching_lines(reader, page_index, FORMULA_RE):
            if any(marker in line for marker in ["=", "^", "\\frac", "\\sum", "\\int"]):
                findings.append(
                    {
                        "page_number": page_index + 1,
                        "text": line,
                        "bbox": [0, 0, float(reader.pages[page_index].mediabox.width), float(reader.pages[page_index].mediabox.height)],
                        "confidence": 0.52,
                        "source": "text_formula_heuristic",
                    }
                )
    return _semantic_result(
        tool,
        resolved,
        selected_pages,
        "formulas",
        findings,
        "formula_count",
        ["pdf.ai.parse.lite", "pdf.convert.pdf_to_markdown"],
    )


def parse_charts_pdf(input_path: str | Path, pages: str = "all") -> ToolResult:
    tool = "pdf.ai.parse.charts"
    resolved, reader, selected_pages = _parse_context(input_path, pages)
    findings = []
    for page_index in selected_pages:
        image_count = _count_page_images(reader.pages[page_index])
        for caption in _matching_lines(reader, page_index, CHART_RE):
            findings.append(
                {
                    "page_number": page_index + 1,
                    "caption": caption,
                    "image_count_on_page": image_count,
                    "bbox": [0, 0, float(reader.pages[page_index].mediabox.width), float(reader.pages[page_index].mediabox.height)],
                    "confidence": 0.56 if image_count else 0.44,
                    "source": "chart_caption_heuristic",
                }
            )
    return _semantic_result(
        tool,
        resolved,
        selected_pages,
        "charts",
        findings,
        "chart_count",
        ["pdf.ai.parse.figures", "pdf.convert.extract_images"],
    )


def parse_references_pdf(input_path: str | Path, pages: str = "all") -> ToolResult:
    tool = "pdf.ai.parse.references"
    resolved, reader, selected_pages = _parse_context(input_path, pages)
    findings = []
    for page_index in selected_pages:
        for line in _matching_lines(reader, page_index, REFERENCE_RE):
            findings.append(
                {
                    "page_number": page_index + 1,
                    "text": line,
                    "kind": _reference_kind(line),
                    "confidence": 0.62,
                    "source": "reference_line_heuristic",
                }
            )
    return _semantic_result(
        tool,
        resolved,
        selected_pages,
        "references",
        findings,
        "reference_count",
        ["pdf.evidence.cite_claims", "pdf.ai.rag.ingest"],
    )


def _parse_context(input_path: str | Path, pages: str) -> tuple[Path, PdfReader, list[int]]:
    resolved = resolve_input_path(input_path)
    if resolved.suffix.lower() != ".pdf":
        raise OKofficeException("unsupported_file_type", "Only PDF files are supported.")
    try:
        reader = PdfReader(resolved)
    except Exception as exc:
        raise OKofficeException("pdf_parse_failed", f"Unable to parse PDF: {resolved}") from exc
    if reader.is_encrypted:
        raise OKofficeException(
            "encrypted_pdf_requires_password",
            "Encrypted PDFs require an authorized password before local parse.",
        )
    return resolved, reader, parse_page_range(pages, total_pages=len(reader.pages))


def _matching_lines(reader: PdfReader, page_index: int, pattern: re.Pattern[str]) -> list[str]:
    text = reader.pages[page_index].extract_text() or ""
    return [line.strip() for line in text.splitlines() if pattern.search(line.strip())]


def _semantic_result(
    tool: str,
    resolved: Path,
    selected_pages: list[int],
    usage_key: str,
    findings: list[dict[str, Any]],
    count_key: str,
    next_tools: list[str],
) -> ToolResult:
    warnings = [] if findings else ["No matching local text-layer evidence found."]
    return ToolResult(
        job_id=_job_id(),
        status="succeeded",
        tool=tool,
        warnings=warnings,
        usage={
            "input": str(resolved),
            "selected_pages": [page + 1 for page in selected_pages],
            count_key: len(findings),
            usage_key: findings,
            "parser": "okoffice_local_text_layer_heuristic",
            "limitations": ["No OCR, vision model, or layout model was used."],
        },
        next_recommended_tools=next_tools,
    )


def _reference_kind(line: str) -> str:
    normalized = line.lower()
    if normalized.startswith("http"):
        return "url"
    if normalized.startswith("doi:"):
        return "doi"
    if normalized.startswith("[") or normalized[:1].isdigit():
        return "numbered_reference"
    return "citation_text"


def _count_page_images(page: Any) -> int:
    try:
        return len(list(getattr(page, "images", [])))
    except Exception:
        return 0


def _job_id() -> str:
    return f"job_{uuid4().hex[:16]}"
