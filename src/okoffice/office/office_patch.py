from __future__ import annotations

from pathlib import Path
from typing import Any

from okoffice.office.deck_patch import apply_deck_patch
from okoffice.office.inspect import inspect_office_file
from okoffice.office.shared import failed_result, job_id
from okoffice.office.sheet_patch import patch_sheet_cells, patch_sheet_formulas, patch_sheet_table
from okoffice.office.word_patch import apply_word_patch
from okoffice.schemas.errors import OKofficeException
from okoffice.schemas.models import OKofficeError, ToolResult, ValidationCheck, ValidationReport
from okoffice.security.paths import resolve_input_path, resolve_output_path


PLAN_TOOL = "office.patch.plan"
PREVIEW_TOOL = "office.patch.preview"
VERIFY_TOOL = "office.patch.verify"

SUPPORTED_OPS: dict[str, set[str]] = {
    "docx": {"replace_text", "update_style"},
    "xlsx": {"set_value", "replace_formula", "update_range"},
    "pptx": {"replace_text", "update_theme", "patch_slide", "patch_shape", "patch_notes", "patch_chart"},
}


def plan_office_patch(*, path: str | Path, operations: list[dict[str, Any]]) -> ToolResult:
    """Detect format and plan patch operations without applying them."""
    try:
        resolved = resolve_input_path(path)
        inspect_result = inspect_office_file(resolved)
        if inspect_result.status == "failed":
            return failed_result(PLAN_TOOL, inspect_result.error or OKofficeError(
                code="unsupported_file_type", message="Unable to inspect file for patch planning.",
            ))
        detected_format = str(inspect_result.usage["format"]["detected_format"])
        allowed = SUPPORTED_OPS.get(detected_format)
        if allowed is None:
            return failed_result(PLAN_TOOL, OKofficeError(
                code="unsupported_file_type",
                message=f"Patch planning is not supported for format: {detected_format}",
                details={"detected_format": detected_format},
            ))
        if not isinstance(operations, list) or not operations:
            raise OKofficeException("invalid_input", "operations must be a non-empty list.")
        supported_ops: list[dict[str, Any]] = []
        unsupported_ops: list[dict[str, Any]] = []
        for index, operation in enumerate(operations, start=1):
            if not isinstance(operation, dict):
                raise OKofficeException("invalid_input", f"Operation {index} must be an object.")
            op = str(operation.get("op") or "")
            entry = {"index": index, "op": op or "<missing>"}
            (supported_ops if op in allowed else unsupported_ops).append(entry)
        impact = "full" if not unsupported_ops else ("partial" if supported_ops else "none")
        return ToolResult(
            job_id=job_id(), status="succeeded", tool=PLAN_TOOL,
            validation=ValidationReport(status="passed", checks=[
                ValidationCheck(name="format_detected", status="passed", details={"detected_format": detected_format}),
                ValidationCheck(name="operations_validated", status="passed" if not unsupported_ops else "warning",
                                details={"supported": len(supported_ops), "unsupported": len(unsupported_ops)}),
            ]),
            usage={
                "summary": {"format": detected_format, "operation_count": len(operations), "estimated_impact": impact},
                "plan": {"format": detected_format, "operations": operations,
                         "supported": supported_ops, "unsupported": unsupported_ops},
            },
            next_recommended_tools=["office.patch.preview", "office.workflow.review_and_patch"],
        )
    except OKofficeException as exc:
        return failed_result(PLAN_TOOL, exc.to_error())


def preview_office_patch(*, path: str | Path, operations: list[dict[str, Any]]) -> ToolResult:
    """Preview patch effects without applying them."""
    try:
        resolved = resolve_input_path(path)
        inspect_result = inspect_office_file(resolved)
        if inspect_result.status == "failed":
            return failed_result(PREVIEW_TOOL, inspect_result.error or OKofficeError(
                code="unsupported_file_type", message="Unable to inspect file for patch preview.",
            ))
        detected_format = str(inspect_result.usage["format"]["detected_format"])
        allowed = SUPPORTED_OPS.get(detected_format)
        if allowed is None:
            return failed_result(PREVIEW_TOOL, OKofficeError(
                code="unsupported_file_type", message=f"Patch preview not supported for format: {detected_format}",
            ))
        if not isinstance(operations, list) or not operations:
            raise OKofficeException("invalid_input", "operations must be a non-empty list.")
        preview_items: list[dict[str, Any]] = []
        total_estimated = 0
        for index, operation in enumerate(operations, start=1):
            if not isinstance(operation, dict):
                raise OKofficeException("invalid_input", f"Operation {index} must be an object.")
            op = str(operation.get("op") or "")
            supported = op in allowed
            estimated_count = 1 if supported and op in {"replace_text", "patch_slide", "patch_notes"} else (1 if supported else 0)
            total_estimated += estimated_count
            affected = _affected_parts(detected_format, op, operation)
            preview_items.append({"operation_index": index, "op": op, "supported": supported,
                                  "estimated_count": estimated_count, "affected_parts": affected})
        return ToolResult(
            job_id=job_id(), status="succeeded", tool=PREVIEW_TOOL,
            validation=ValidationReport(status="passed", checks=[
                ValidationCheck(name="format_detected", status="passed", details={"detected_format": detected_format}),
                ValidationCheck(name="operations_previewed", status="passed", details={"count": len(preview_items)}),
            ]),
            usage={
                "summary": {"format": detected_format, "operation_count": len(operations), "estimated_replacements": total_estimated},
                "preview": preview_items,
            },
            next_recommended_tools=["office.patch.plan", "office.workflow.review_and_patch"],
        )
    except OKofficeException as exc:
        return failed_result(PREVIEW_TOOL, exc.to_error())


def verify_office_patch(*, input_path: str | Path, output_path: str | Path,
                        patch_manifest: dict[str, Any] | None = None) -> ToolResult:
    """Verify a patched file against the original."""
    try:
        input_file = resolve_input_path(input_path)
        output_file = resolve_output_path(output_path)
        if not output_file.exists():
            raise OKofficeException("file_not_found", f"Patched output not found: {output_file.as_posix()}")
        input_inspect = inspect_office_file(input_file)
        output_inspect = inspect_office_file(output_file)
        if input_inspect.status == "failed":
            return failed_result(VERIFY_TOOL, input_inspect.error or OKofficeError(
                code="inspect_failed", message="Unable to inspect input file.",
            ))
        if output_inspect.status == "failed":
            return failed_result(VERIFY_TOOL, output_inspect.error or OKofficeError(
                code="inspect_failed", message="Unable to inspect output file.",
            ))
        input_format = str(input_inspect.usage["format"]["detected_format"])
        output_format = str(output_inspect.usage["format"]["detected_format"])
        input_size = int(input_inspect.usage["file"]["size_bytes"])
        output_size = int(output_inspect.usage["file"]["size_bytes"])
        input_entries = input_inspect.usage["safety"].get("zip_entry_count", 0)
        output_entries = output_inspect.usage["safety"].get("zip_entry_count", 0)
        entry_delta = output_entries - input_entries
        format_match = input_format == output_format
        verification_status = "passed" if format_match else "warning"
        return ToolResult(
            job_id=job_id(), status="succeeded", tool=VERIFY_TOOL,
            validation=ValidationReport(status=verification_status, checks=[
                ValidationCheck(name="output_exists", status="passed", details={"path": output_file.as_posix()}),
                ValidationCheck(name="format_match", status="passed" if format_match else "warning",
                                details={"input_format": input_format, "output_format": output_format}),
                ValidationCheck(name="output_inspectable", status="passed"),
                ValidationCheck(name="size_delta", status="passed",
                                details={"input_bytes": input_size, "output_bytes": output_size, "delta": output_size - input_size}),
            ]),
            usage={
                "summary": {"input_format": input_format, "output_format": output_format,
                            "entry_count_delta": entry_delta, "verification_status": verification_status},
                "verification": {"input_size_bytes": input_size, "output_size_bytes": output_size,
                                 "input_entries": input_entries, "output_entries": output_entries,
                                 "format_match": format_match, "manifest": patch_manifest},
            },
            next_recommended_tools=["office.patch.plan", "office.bundle.export"],
        )
    except OKofficeException as exc:
        return failed_result(VERIFY_TOOL, exc.to_error())


def _affected_parts(fmt: str, op: str, operation: dict[str, Any]) -> list[str]:
    """Return which document parts an operation is estimated to affect."""
    if fmt == "docx":
        if op == "replace_text":
            return ["word/document.xml"]
        if op == "update_style":
            return ["word/styles.xml"]
    elif fmt == "xlsx":
        if op == "set_value":
            return [f"xl/worksheets/sheet ({operation.get('sheet', '?')})"]
        if op == "replace_formula":
            return [f"xl/worksheets/sheet ({operation.get('sheet', '?')})"]
        if op == "update_range":
            return ["xl/tables/"]
    elif fmt == "pptx":
        if op == "replace_text":
            return ["ppt/slides/"]
        if op == "update_theme":
            return ["ppt/theme/theme1.xml"]
        if op == "patch_slide":
            return [f"ppt/slides/slide{operation.get('slide', '?')}.xml"]
        if op == "patch_shape":
            return [f"ppt/slides/slide{operation.get('slide', '?')}.xml"]
        if op == "patch_notes":
            return [f"ppt/notesSlides/notesSlide{operation.get('slide', '?')}.xml"]
        if op == "patch_chart":
            return [f"ppt/charts/chart{operation.get('chart_id', '?')}.xml"]
    return []
