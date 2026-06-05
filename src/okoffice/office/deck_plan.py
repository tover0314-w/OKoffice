from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from okoffice.artifacts.store import build_artifact
from okoffice.office.sheet import profile_sheet_data, read_sheet_workbook
from okoffice.schemas.errors import OKofficeException
from okoffice.schemas.models import OKofficeError, ToolResult, ValidationCheck, ValidationReport
from okoffice.security.paths import resolve_input_path, resolve_output_path


TOOL_NAME = "deck.compose.plan"
COMPOSITION_SCHEMA = "okoffice.deck.composition"
COMPOSITION_VERSION = "okoffice.deck.composition.v0"
MAX_PROFILE_SLIDES = 8
MAX_SOURCE_REFS_PER_SLIDE = 20


def compose_deck_plan(
    workbook_path: str | Path,
    *,
    output_path: str | Path | None = None,
    title: str | None = None,
    style: str = "executive",
    max_rows_per_sheet: int = 100,
) -> ToolResult:
    """Create a deterministic, source-mapped deck Composition IR from a workbook."""
    try:
        input_path = resolve_input_path(workbook_path)
        output = resolve_output_path(output_path) if output_path is not None else None
    except OKofficeException as exc:
        return _failed(exc.to_error())
    if output is not None and output == input_path:
        return _failed(
            OKofficeError(
                code="unsafe_input_rejected",
                message="deck.compose.plan output_path must not point to the input workbook.",
                details={"workbook_path": input_path.as_posix(), "output_path": output.as_posix()},
            )
        )

    profile_result = profile_sheet_data(input_path, max_rows_per_sheet=max_rows_per_sheet)
    if profile_result.status == "failed":
        return _failed(
            profile_result.error
            or OKofficeError(code="unsupported_file_type", message="Workbook profile failed before deck planning."),
        )

    profile_usage = profile_result.usage
    summary = profile_usage.get("summary", {}) if isinstance(profile_usage.get("summary"), dict) else {}
    profiles = profile_usage.get("profiles", []) if isinstance(profile_usage.get("profiles"), list) else []
    profiled_profiles = [
        profile for profile in profiles if isinstance(profile, dict) and int(profile.get("data_row_count", 0)) > 0
    ]
    data_row_count = int(summary.get("data_row_count", 0))
    if data_row_count <= 0 or not profiled_profiles:
        return _failed(
            OKofficeError(
                code="unsafe_input_rejected",
                message="deck.compose.plan requires at least one profiled workbook data row.",
                details={"workbook_path": str(workbook_path), "profiled_sheet_count": len(profiled_profiles)},
            )
        )

    expected_source_ref_count = _coerce_non_negative_int(summary.get("source_ref_row_count"))
    read_result = read_sheet_workbook(
        input_path,
        max_rows_per_sheet=_source_ref_read_limit(
            max_rows_per_sheet=max_rows_per_sheet,
            expected_source_ref_count=expected_source_ref_count,
        ),
    )
    warnings = [*profile_result.warnings, *read_result.warnings]
    source_refs_by_record = _source_refs_by_record(read_result.usage if read_result.status == "succeeded" else {})
    loaded_source_ref_count = len(source_refs_by_record)
    if summary.get("source_coverage", {}).get("status") in {"missing", "partial"}:
        warnings.append("Deck plan source coverage is incomplete; source refs may be partial.")
    if expected_source_ref_count > loaded_source_ref_count:
        warnings.append(
            "Deck plan could not map every SourceRefs row; malformed or missing record indexes were skipped."
        )

    workbook = profile_usage.get("workbook", {}) if isinstance(profile_usage.get("workbook"), dict) else {}
    workbook_path_value = str(workbook.get("path") or input_path.as_posix())
    deck_title = (title or "").strip() or f"{Path(workbook_path_value).stem} Review"
    plan = _build_composition_plan(
        workbook_path=workbook_path_value,
        title=deck_title,
        style=(style or "executive").strip() or "executive",
        summary=summary,
        profiles=profiled_profiles,
        source_refs_by_record=source_refs_by_record,
        warnings=warnings,
    )

    artifacts = []
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(_plan_artifact_payload(plan, warnings), ensure_ascii=False, indent=2), encoding="utf-8")
        artifacts.append(build_artifact(output, TOOL_NAME))

    checks = [
        ValidationCheck(
            name="workbook_profiled",
            status="passed",
            details={
                "workbook_path": workbook_path_value,
                "profiled_sheet_count": summary.get("profiled_sheet_count", len(profiled_profiles)),
                "data_row_count": data_row_count,
                "source_coverage": summary.get("source_coverage", {}),
            },
        ),
        ValidationCheck(
            name="source_refs_loaded",
            status="passed" if expected_source_ref_count > 0 and loaded_source_ref_count >= expected_source_ref_count else "warning",
            details={
                "record_count": loaded_source_ref_count,
                "expected_record_count": expected_source_ref_count,
            },
            message=_source_refs_loaded_message(
                loaded_source_ref_count=loaded_source_ref_count,
                expected_source_ref_count=expected_source_ref_count,
            ),
        ),
        ValidationCheck(
            name="composition_ir_created",
            status="passed",
            details={
                "slide_count": len(plan["composition_ir"]["slides"]),
                "style": plan["composition_ir"]["style"],
            },
        ),
        ValidationCheck(
            name="plan_written",
            status="passed" if output is not None else "skipped",
            details={"path": output.as_posix() if output is not None else None},
        ),
    ]

    return ToolResult(
        job_id=_job_id(),
        status="succeeded",
        tool=TOOL_NAME,
        artifacts=artifacts,
        validation=ValidationReport(
            status=_validation_report_status(checks),
            checks=checks,
            warnings=warnings,
        ),
        warnings=warnings,
        usage={
            "summary": {
                "workbook_path": workbook_path_value,
                "slide_count": len(plan["composition_ir"]["slides"]),
                "profiled_sheet_count": summary.get("profiled_sheet_count", len(profiled_profiles)),
                "column_count": summary.get("column_count", 0),
                "data_row_count": data_row_count,
                "missing_cell_count": summary.get("missing_cell_count", 0),
                "formula_cell_count": summary.get("formula_cell_count", 0),
                "source_coverage": summary.get("source_coverage", {}),
            },
            **plan,
        },
        next_recommended_tools=[
            "deck.render.html",
            "deck.validation.html_preview",
            "deck.export.pptx",
            "deck.create.presentation",
            "deck.create.from_outline",
            "deck.validate.presentation",
            "office.workflow.sheet_to_deck",
            "office.workflow.board_pack",
        ],
    )


def _build_composition_plan(
    *,
    workbook_path: str,
    title: str,
    style: str,
    summary: dict[str, Any],
    profiles: list[dict[str, Any]],
    source_refs_by_record: dict[int, list[dict[str, Any]]],
    warnings: list[str],
) -> dict[str, Any]:
    coverage = summary.get("source_coverage", {}) if isinstance(summary.get("source_coverage"), dict) else {}
    coverage_status = str(coverage.get("status") or "unknown")
    slides: list[dict[str, Any]] = [
        _title_slide(title=title, workbook_path=workbook_path, summary=summary, coverage_status=coverage_status),
        _summary_slide(summary=summary, coverage_status=coverage_status),
    ]
    record_start = 1
    for profile in profiles[:MAX_PROFILE_SLIDES]:
        data_row_count = int(profile.get("data_row_count", 0))
        source_refs = _source_refs_for_records(
            source_refs_by_record,
            start=record_start,
            count=data_row_count,
        )
        slides.append(
            _profile_slide(
                slide_index=len(slides) + 1,
                profile=profile,
                coverage_status=coverage_status,
                source_refs=source_refs,
            )
        )
        record_start += data_row_count
    slides.append(_validation_slide(len(slides) + 1, summary=summary, coverage_status=coverage_status, warnings=warnings))
    outline = _outline_from_slides(title=title, style=style, workbook_path=workbook_path, slides=slides)
    return {
        "composition_ir": {
            "schema": COMPOSITION_SCHEMA,
            "composition_version": COMPOSITION_VERSION,
            "kind": "deck.composition",
            "title": title,
            "style": style,
            "source": {
                "type": "workbook_profile",
                "workbook_path": workbook_path,
                "profile_tool": "sheet.profile.data",
            },
            "slides": slides,
            "validation_expectations": [
                "deck.validate.presentation",
                "office.workflow.board_pack",
            ],
        },
        "outline": outline,
    }


def _title_slide(
    *,
    title: str,
    workbook_path: str,
    summary: dict[str, Any],
    coverage_status: str,
) -> dict[str, Any]:
    bullets = [
        f"{summary.get('profiled_sheet_count', 0)} profiled sheet(s)",
        f"{summary.get('data_row_count', 0)} data rows across {summary.get('column_count', 0)} columns",
        f"Source coverage: {coverage_status}",
    ]
    return {
        "slide_id": "slide_001",
        "slide_index": 1,
        "slide_type": "title",
        "title": title,
        "subtitle": "Generated from an OKoffice workbook composition plan",
        "bullets": bullets,
        "claims": [_claim(1, 1, bullets[1], evidence_refs=[])],
        "workbook_ranges": [],
        "source_refs": [],
        "notes": f"Source workbook: {workbook_path}",
    }


def _summary_slide(summary: dict[str, Any], *, coverage_status: str) -> dict[str, Any]:
    bullets = [
        f"Workbook rows profiled: {summary.get('data_row_count', 0)}",
        f"Formula cells detected: {summary.get('formula_cell_count', 0)}",
        f"Missing cells detected: {summary.get('missing_cell_count', 0)}",
        f"Source refs: {coverage_status}",
    ]
    return {
        "slide_id": "slide_002",
        "slide_index": 2,
        "slide_type": "executive_summary",
        "title": "Executive Summary",
        "bullets": bullets,
        "claims": [_claim(2, index, bullet, evidence_refs=[]) for index, bullet in enumerate(bullets, start=1)],
        "workbook_ranges": [],
        "source_refs": [],
        "notes": "Review workbook profile warnings before writing the final deck.",
    }


def _profile_slide(
    *,
    slide_index: int,
    profile: dict[str, Any],
    coverage_status: str,
    source_refs: list[dict[str, Any]],
) -> dict[str, Any]:
    sheet_name = str(profile.get("sheet_name") or "Workbook Sheet")
    headers = [str(header) for header in profile.get("headers", []) if str(header).strip()]
    columns = profile.get("columns", []) if isinstance(profile.get("columns"), list) else []
    numeric_columns = _columns_by_semantic_type(columns, "number")
    text_columns = _columns_by_semantic_type(columns, "text")
    workbook_range = {
        "sheet_name": sheet_name,
        "range_ref": _profile_range(profile, headers),
        "header_count": len(headers),
        "data_row_count": int(profile.get("data_row_count", 0)),
    }
    bullets = [
        f"{profile.get('data_row_count', 0)} data rows across {len(headers)} columns",
        f"Key columns: {_join_limited(headers, fallback='none detected')}",
        f"Numeric columns: {_join_limited(numeric_columns, fallback='none detected')}",
        f"Text columns: {_join_limited(text_columns, fallback='none detected')}",
        f"Missing cells: {profile.get('missing_cell_count', 0)}; formula cells: {profile.get('formula_cell_count', 0)}",
        f"Source coverage: {coverage_status}",
    ]
    return {
        "slide_id": f"slide_{slide_index:03d}",
        "slide_index": slide_index,
        "slide_type": "sheet_snapshot",
        "title": f"{sheet_name} Snapshot",
        "bullets": bullets,
        "claims": [
            _claim(slide_index, index, bullet, evidence_refs=source_refs[:3], workbook_ranges=[workbook_range])
            for index, bullet in enumerate(bullets, start=1)
        ],
        "workbook_ranges": [workbook_range],
        "source_refs": source_refs,
        "notes": f"Source workbook sheet: {sheet_name}",
    }


def _validation_slide(
    slide_index: int,
    *,
    summary: dict[str, Any],
    coverage_status: str,
    warnings: list[str],
) -> dict[str, Any]:
    bullets = [
        f"Source coverage: {coverage_status}",
        f"Source ref rows: {summary.get('source_ref_row_count', 0)}",
        f"Missing cells: {summary.get('missing_cell_count', 0)}",
        f"Formula cells: {summary.get('formula_cell_count', 0)}",
        f"Warnings: {len(warnings)}",
    ]
    return {
        "slide_id": f"slide_{slide_index:03d}",
        "slide_index": slide_index,
        "slide_type": "validation_source_map",
        "title": "Validation & Source Map",
        "bullets": bullets,
        "claims": [_claim(slide_index, index, bullet, evidence_refs=[]) for index, bullet in enumerate(bullets, start=1)],
        "workbook_ranges": [],
        "source_refs": [],
        "notes": "Run deck.validate.presentation and office.workflow.board_pack before delivery.",
    }


def _outline_from_slides(*, title: str, style: str, workbook_path: str, slides: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "title": title,
        "style": style,
        "source": {
            "type": "deck.composition",
            "workbook_path": workbook_path,
            "composition_tool": TOOL_NAME,
        },
        "slides": [
            {
                "title": slide["title"],
                **({"subtitle": slide["subtitle"]} if slide.get("subtitle") else {}),
                "bullets": list(slide.get("bullets", [])),
                "notes": str(slide.get("notes", "")),
            }
            for slide in slides
        ],
    }


def _claim(
    slide_index: int,
    claim_index: int,
    text: str,
    *,
    evidence_refs: list[dict[str, Any]],
    workbook_ranges: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "claim_id": f"slide_{slide_index:03d}_claim_{claim_index:02d}",
        "text": text,
        "evidence_refs": evidence_refs,
        "workbook_ranges": workbook_ranges or [],
    }


def _source_refs_by_record(read_usage: dict[str, Any]) -> dict[int, list[dict[str, Any]]]:
    sheets = read_usage.get("sheets", []) if isinstance(read_usage.get("sheets"), list) else []
    for sheet in sheets:
        if not isinstance(sheet, dict) or not _is_source_refs_sheet(sheet):
            continue
        rows = sheet.get("rows", []) if isinstance(sheet.get("rows"), list) else []
        if not rows:
            return {}
        headers = _row_values(rows[0])
        refs_by_record: dict[int, list[dict[str, Any]]] = {}
        for row in rows[1:]:
            row_map = _row_map(headers, row)
            record_index = _coerce_int(row_map.get("record_index"))
            if record_index <= 0:
                continue
            refs_by_record[record_index] = _normalize_source_refs(
                row_map.get("source_refs_json") or row_map.get("source_ref_json"),
                source_path=row_map.get("source_path", ""),
            )
        return refs_by_record
    return {}


def _source_ref_read_limit(*, max_rows_per_sheet: int, expected_source_ref_count: int) -> int:
    return max(0, int(max_rows_per_sheet), expected_source_ref_count + 1)


def _source_refs_loaded_message(*, loaded_source_ref_count: int, expected_source_ref_count: int) -> str | None:
    if expected_source_ref_count == 0:
        return "No SourceRefs rows were found in the workbook."
    if loaded_source_ref_count < expected_source_ref_count:
        return "Some SourceRefs rows were skipped because their record indexes were missing or malformed."
    return None


def _is_source_refs_sheet(sheet: dict[str, Any]) -> bool:
    normalized_name = str(sheet.get("name", "")).replace(" ", "").replace("_", "").lower()
    return normalized_name == "sourcerefs"


def _row_map(headers: list[str], row: Any) -> dict[str, str]:
    values = _row_values(row)
    return {
        header: values[index] if index < len(values) else ""
        for index, header in enumerate(headers)
        if header
    }


def _row_values(row: Any) -> list[str]:
    if not isinstance(row, dict):
        return []
    cells = row.get("cells", []) if isinstance(row.get("cells"), list) else []
    max_column = max((int(cell.get("column_index", 0)) for cell in cells if isinstance(cell, dict)), default=0)
    values = [""] * max_column
    for cell in cells:
        if not isinstance(cell, dict):
            continue
        column_index = int(cell.get("column_index", 0))
        if column_index <= 0:
            continue
        values[column_index - 1] = str(cell.get("value", "")).strip()
    return values


def _normalize_source_refs(raw_json: str | None, *, source_path: str) -> list[dict[str, Any]]:
    if not raw_json:
        return []
    try:
        payload = json.loads(raw_json)
    except json.JSONDecodeError:
        return [{"source_path": source_path, "raw_source_ref": raw_json}]
    refs = payload if isinstance(payload, list) else [payload]
    normalized = []
    for ref in refs:
        if not isinstance(ref, dict):
            continue
        next_ref = dict(ref)
        if source_path and not next_ref.get("source_path"):
            next_ref["source_path"] = source_path
        normalized.append(next_ref)
    return normalized


def _source_refs_for_records(
    refs_by_record: dict[int, list[dict[str, Any]]],
    *,
    start: int,
    count: int,
) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for record_index in range(start, start + max(0, count)):
        for ref in refs_by_record.get(record_index, []):
            refs.append({"record_index": record_index, **ref})
            if len(refs) >= MAX_SOURCE_REFS_PER_SLIDE:
                return refs
    return refs


def _profile_range(profile: dict[str, Any], headers: list[str]) -> str:
    row_count = int(profile.get("data_row_count", 0)) + 1
    column_count = max(1, len(headers))
    return f"A1:{_column_letters(column_count)}{max(1, row_count)}"


def _columns_by_semantic_type(columns: list[Any], semantic_type: str) -> list[str]:
    names: list[str] = []
    for column in columns:
        if not isinstance(column, dict) or column.get("semantic_type") != semantic_type:
            continue
        names.append(str(column.get("header") or f"column_{column.get('column_index', '')}").strip())
    return [name for name in names if name]


def _join_limited(values: list[str], *, fallback: str, limit: int = 5) -> str:
    cleaned = [value for value in values if value][:limit]
    if not cleaned:
        return fallback
    suffix = "" if len(values) <= limit else f" (+{len(values) - limit} more)"
    return ", ".join(cleaned) + suffix


def _column_letters(column_number: int) -> str:
    letters = ""
    while column_number:
        column_number, remainder = divmod(column_number - 1, 26)
        letters = chr(ord("A") + remainder) + letters
    return letters or "A"


def _coerce_int(value: object) -> int:
    try:
        return int(float(str(value)))
    except (OverflowError, TypeError, ValueError):
        return 0


def _coerce_non_negative_int(value: object) -> int:
    return max(0, _coerce_int(value))


def _plan_artifact_payload(plan: dict[str, Any], warnings: list[str]) -> dict[str, Any]:
    return {
        "tool": TOOL_NAME,
        "composition_ir": plan["composition_ir"],
        "outline": plan["outline"],
        "warnings": warnings,
    }


def _validation_report_status(checks: list[ValidationCheck]) -> str:
    statuses = [check.status for check in checks]
    if "failed" in statuses:
        return "failed"
    if "warning" in statuses:
        return "warning"
    return "passed"


def _failed(error: OKofficeError) -> ToolResult:
    return ToolResult(
        job_id=_job_id(),
        status="failed",
        tool=TOOL_NAME,
        error=error,
        warnings=[error.message],
    )


def _job_id() -> str:
    return f"job_{uuid4().hex[:16]}"
