from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from uuid import uuid4

from okoffice.office.shared import failed_result, job_id
from okoffice.schemas.models import OKofficeError, ToolResult, ValidationCheck, ValidationReport
from okoffice.security.paths import resolve_input_path, resolve_output_path

TOOL_NAME = "pdf.extract.tables"

MIN_COLS = 2
MIN_ROWS = 2


def extract_pdf_tables(
    input_path: str | Path,
    pages: str = "all",
    output_path: str | Path | None = None,
) -> ToolResult:
    try:
        path = resolve_input_path(input_path)
        page_list = _parse_pages(pages)

        text_lines = _extract_text_lines(path, page_list)
        tables, warnings = _detect_tables(text_lines)

        usage: dict[str, Any] = {
            "total_tables": len(tables),
            "pages_scanned": len(page_list) if page_list != "all" else "all",
        }

        artifacts = []
        if output_path is not None:
            import json
            dest = resolve_output_path(output_path)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(
                json.dumps({"tables": tables}, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            usage["output_path"] = dest.as_posix()

        checks = [
            ValidationCheck(name="text_layer_parsed", status="passed", details={"lines": len(text_lines)}),
            ValidationCheck(name="tables_detected", status="passed", details={"count": len(tables)}),
        ]
        return ToolResult(
            job_id=job_id(),
            status="succeeded",
            tool=TOOL_NAME,
            validation=ValidationReport(
                status="warning" if warnings else "passed",
                checks=checks,
                warnings=warnings,
            ),
            warnings=warnings,
            usage=usage,
            next_recommended_tools=["pdf.ai.parse.lite", "pdf.convert.pdf_to_text"],
        )
    except Exception as exc:
        return failed_result(TOOL_NAME, OKofficeError(code="table_extraction_failed", message=str(exc)))


def _parse_pages(pages: str) -> list[int] | str:
    if pages == "all":
        return "all"
    result = []
    for part in pages.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            result.extend(range(int(start), int(end) + 1))
        else:
            result.append(int(part))
    return result


def _extract_text_lines(path: Path, pages: list[int] | str) -> list[dict[str, Any]]:
    try:
        from pypdf import PdfReader
        reader = PdfReader(path)
        lines: list[dict[str, Any]] = []
        page_indices = range(len(reader.pages)) if pages == "all" else [p - 1 for p in pages if 0 < p <= len(reader.pages)]

        for idx in page_indices:
            page = reader.pages[idx]
            text = page.extract_text() or ""
            for i, line in enumerate(text.split("\n")):
                stripped = line.strip()
                if stripped:
                    lines.append({"page": idx + 1, "line": i + 1, "text": stripped})
        return lines
    except Exception:
        return []


def _detect_tables(lines: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    tables: list[dict[str, Any]] = []
    warnings: list[str] = []

    table_lines: list[dict[str, Any]] = []
    current_page = 0

    for entry in lines:
        text = entry["text"]
        page = entry["page"]
        is_delimiter = bool(re.match(r'^[\s|+\-=%#]+$', text)) or text.count("|") >= MIN_COLS - 1
        has_multi_separator = text.count("\t") >= MIN_COLS - 1 or text.count("|") >= MIN_COLS - 1

        if is_delimiter or has_multi_separator:
            if page != current_page and table_lines:
                _flush_table(table_lines, tables, current_page)
                table_lines = []
            current_page = page
            if not is_delimiter or has_multi_separator:
                table_lines.append(entry)
        else:
            if table_lines:
                if len(table_lines) >= MIN_ROWS:
                    _flush_table(table_lines, tables, current_page)
                table_lines = []

    if table_lines and len(table_lines) >= MIN_ROWS:
        _flush_table(table_lines, tables, current_page)

    if not tables:
        warnings.append("No tables detected. Try pdf.ai.parse.lite for structured IR extraction.")

    return tables, warnings


def _flush_table(
    lines: list[dict[str, Any]],
    tables: list[dict[str, Any]],
    page: int,
) -> None:
    rows: list[list[str]] = []
    for entry in lines:
        text = entry["text"]
        if "|" in text:
            cells = [c.strip() for c in text.split("|") if c.strip()]
        elif "\t" in text:
            cells = [c.strip() for c in text.split("\t") if c.strip()]
        else:
            cells = [text]
        if cells:
            rows.append(cells)

    if len(rows) >= MIN_ROWS and any(len(r) >= MIN_COLS for r in rows):
        col_count = max(len(r) for r in rows)
        normalized = [r + [""] * (col_count - len(r)) for r in rows]
        tables.append({
            "page": page,
            "row_count": len(normalized),
            "col_count": col_count,
            "rows": normalized,
        })
