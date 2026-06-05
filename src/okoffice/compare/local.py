from __future__ import annotations

from difflib import SequenceMatcher, unified_diff
from pathlib import Path
from typing import Any
from uuid import uuid4

from pypdf import PdfReader

from okoffice.artifacts.store import build_artifact
from okoffice.core.page_ranges import parse_page_range
from okoffice.schemas.errors import OKofficeException
from okoffice.schemas.models import ToolResult
from okoffice.security.paths import resolve_input_path, resolve_output_path
from okoffice.validation.pdf import visual_diff_check_pdf


def semantic_diff_pdf(
    before_path: str | Path,
    after_path: str | Path,
    pages: str = "all",
) -> ToolResult:
    tool = "pdf.compare.semantic_diff"
    before = resolve_input_path(before_path)
    after = resolve_input_path(after_path)
    before_reader = _reader_for_compare(before)
    after_reader = _reader_for_compare(after)
    page_count = min(len(before_reader.pages), len(after_reader.pages))
    selected_pages = parse_page_range(pages, total_pages=page_count)
    changes = [
        _page_change(before_reader, after_reader, page_index)
        for page_index in selected_pages
    ]
    changed = [change for change in changes if change["change_type"] != "unchanged"]
    warnings = []
    if len(before_reader.pages) != len(after_reader.pages):
        warnings.append("Input PDFs have different page counts; comparison used overlapping pages.")
    return ToolResult(
        job_id=_job_id(),
        status="succeeded",
        tool=tool,
        warnings=warnings,
        usage={
            "before": str(before),
            "after": str(after),
            "page_range": pages,
            "selected_pages": [page + 1 for page in selected_pages],
            "before_page_count": len(before_reader.pages),
            "after_page_count": len(after_reader.pages),
            "changed_page_count": len(changed),
            "changes": changes,
            "diff_strategy": "local_text_similarity_sequence_matcher",
            "limitations": [
                "No model was used; semantic labels are heuristic.",
                "Visual/layout differences are not included.",
            ],
        },
        next_recommended_tools=["pdf.compare.version_report", "pdf.compare.visual_diff"],
    )


def version_report_pdf(
    before_path: str | Path,
    after_path: str | Path,
    output_path: str | Path | None = None,
    pages: str = "all",
) -> ToolResult:
    tool = "pdf.compare.version_report"
    diff = semantic_diff_pdf(before_path, after_path, pages=pages)
    report = _version_report_markdown(diff.usage)
    artifacts = []
    if output_path is not None:
        output = resolve_output_path(output_path)
        output.write_text(report, encoding="utf-8")
        artifact = build_artifact(output, source_tool=tool)
        artifact.mime_type = "text/markdown"
        artifacts.append(artifact)
    return ToolResult(
        job_id=_job_id(),
        status="succeeded",
        tool=tool,
        artifacts=artifacts,
        warnings=diff.warnings,
        usage={
            "before": diff.usage["before"],
            "after": diff.usage["after"],
            "report": {
                "changed_page_count": diff.usage["changed_page_count"],
                "markdown": report,
            },
            "diff_strategy": diff.usage["diff_strategy"],
        },
        next_recommended_tools=["pdf.compare.visual_diff", "pdf.evidence.cite_claims"],
    )


def visual_diff_pdf(
    before_path: str | Path,
    after_path: str | Path,
    pages: str = "all",
    max_difference_ratio: float = 0.001,
    render_scale: float = 0.5,
) -> ToolResult:
    tool = "pdf.compare.visual_diff"
    validation, usage = visual_diff_check_pdf(
        before_path,
        after_path,
        pages=pages,
        max_difference_ratio=max_difference_ratio,
        render_scale=render_scale,
    )
    return ToolResult(
        job_id=_job_id(),
        status="failed" if validation.status == "failed" else "succeeded",
        tool=tool,
        validation=validation,
        warnings=validation.warnings or [],
        usage=usage,
        next_recommended_tools=[
            "pdf.validation.visual_diff",
            "pdf.compare.semantic_diff",
        ],
    )


def _page_change(before_reader: PdfReader, after_reader: PdfReader, page_index: int) -> dict[str, Any]:
    before_text = _page_text(before_reader, page_index)
    after_text = _page_text(after_reader, page_index)
    similarity = SequenceMatcher(None, before_text, after_text).ratio()
    before_lines = _normalized_lines(before_text)
    after_lines = _normalized_lines(after_text)
    diff_lines = list(
        unified_diff(
            before_lines,
            after_lines,
            fromfile=f"before-page-{page_index + 1}",
            tofile=f"after-page-{page_index + 1}",
            lineterm="",
        )
    )
    return {
        "page_number": page_index + 1,
        "change_type": "unchanged" if similarity == 1 else "modified",
        "similarity": round(similarity, 4),
        "before_char_count": len(before_text),
        "after_char_count": len(after_text),
        "added_lines": [line[1:] for line in diff_lines if line.startswith("+") and not line.startswith("+++")],
        "removed_lines": [line[1:] for line in diff_lines if line.startswith("-") and not line.startswith("---")],
        "diff": diff_lines[:80],
    }


def _page_text(reader: PdfReader, page_index: int) -> str:
    if page_index >= len(reader.pages):
        return ""
    return reader.pages[page_index].extract_text() or ""


def _normalized_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def _version_report_markdown(usage: dict[str, Any]) -> str:
    lines = [
        "# OKoffice Version Report",
        "",
        f"- Before: `{usage['before']}`",
        f"- After: `{usage['after']}`",
        f"- Changed pages: {usage['changed_page_count']}",
        f"- Strategy: `{usage['diff_strategy']}`",
        "",
        "## Page Changes",
        "",
    ]
    for change in usage["changes"]:
        lines.extend(
            [
                f"### Page {change['page_number']}",
                "",
                f"- Change type: `{change['change_type']}`",
                f"- Similarity: {change['similarity']}",
            ]
        )
        if change["added_lines"]:
            lines.append(f"- Added lines: {len(change['added_lines'])}")
        if change["removed_lines"]:
            lines.append(f"- Removed lines: {len(change['removed_lines'])}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _reader_for_compare(path: Path) -> PdfReader:
    if path.suffix.lower() != ".pdf":
        raise OKofficeException("unsupported_file_type", "Only PDF files are supported.")
    try:
        reader = PdfReader(path)
    except Exception as exc:
        raise OKofficeException("pdf_parse_failed", f"Unable to parse PDF: {path}") from exc
    if reader.is_encrypted:
        raise OKofficeException(
            "encrypted_pdf_requires_password",
            "Encrypted PDFs require an authorized password before comparison.",
        )
    return reader


def _job_id() -> str:
    return f"job_{uuid4().hex[:16]}"
