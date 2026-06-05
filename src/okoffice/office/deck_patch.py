from __future__ import annotations

import html
import re
import zipfile
from pathlib import Path
from typing import Any
from uuid import uuid4

from okoffice.artifacts.store import build_artifact
from okoffice.office.deck import inspect_deck_presentation
from okoffice.schemas.errors import OKofficeException
from okoffice.schemas.models import OKofficeError, ToolResult, ValidationCheck, ValidationReport
from okoffice.security.paths import resolve_input_path, resolve_output_path


TOOL_NAME = "deck.patch.apply"
THEME_PART = "ppt/theme/theme1.xml"


def apply_deck_patch(
    *,
    input_path: str | Path,
    output_path: str | Path,
    operations: list[dict[str, Any]],
) -> ToolResult:
    try:
        input_file = resolve_input_path(input_path)
        output_file = resolve_output_path(output_path)
        if input_file == output_file:
            raise OKofficeException(
                "invalid_input",
                "deck.patch.apply writes to a new output_path and never mutates the input presentation.",
                details={"input_path": input_file.as_posix(), "output_path": output_file.as_posix()},
            )
        if output_file.suffix.lower() != ".pptx":
            raise OKofficeException(
                "unsupported_file_type",
                "deck.patch.apply writes .pptx output files.",
                details={"output_path": output_file.as_posix()},
            )
        normalized = _normalize_operations(operations)
        summary = _write_patched_package(input_file, output_file, normalized)
        inspected = inspect_deck_presentation(output_file)
        if inspected.status != "succeeded":
            raise OKofficeException(
                "output_validation_failed",
                "Patched presentation could not be inspected.",
                details=inspected.error.model_dump(mode="json") if inspected.error else {},
            )
        return ToolResult(
            job_id=_job_id(),
            status="succeeded",
            tool=TOOL_NAME,
            artifacts=[build_artifact(output_file, source_tool=TOOL_NAME)],
            validation=_validation_report(input_file, output_file, inspected, normalized, summary),
            usage={
                "summary": {
                    "operation_count": len(normalized),
                    **summary,
                    "slide_count": inspected.usage.get("summary", {}).get("slide_count", 0),
                },
                "patch_transaction": {
                    "transaction_id": f"patch_{uuid4().hex[:16]}",
                    "input_path": input_file.as_posix(),
                    "output_path": output_file.as_posix(),
                    "mutates_inputs": False,
                    "operation_count": len(normalized),
                    "operations": normalized,
                    "rollback": {"strategy": "discard_output", "input_preserved": True},
                },
            },
            next_recommended_tools=["deck.inspect.presentation", "deck.validation.contact_sheet"],
        )
    except OKofficeException as exc:
        return _failed(exc.to_error())
    except (zipfile.BadZipFile, ValueError) as exc:
        return _failed(OKofficeError(code="invalid_input", message=str(exc)))


def _normalize_operations(operations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(operations, list) or not operations:
        raise OKofficeException("invalid_input", "Deck patch operations must be a non-empty list.")
    normalized = []
    for index, operation in enumerate(operations, start=1):
        if not isinstance(operation, dict):
            raise OKofficeException("invalid_input", f"Deck patch operation {index} must be an object.")
        op = str(operation.get("op") or "")
        if op == "replace_text":
            find = str(operation.get("find") or "")
            replace = str(operation.get("replace") or "")
            if not find:
                raise OKofficeException("invalid_input", f"Deck patch operation {index} requires find text.")
            normalized.append({"op": op, "find": find, "replace": replace})
        elif op == "update_theme":
            normalized.append({"op": op, **_style_from_operation(operation)})
        else:
            raise OKofficeException("invalid_input", f"Unsupported Deck patch operation: {op or '<missing>'}")
    return normalized


def _write_patched_package(
    input_file: Path,
    output_file: Path,
    operations: list[dict[str, Any]],
) -> dict[str, int]:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    text_replacement_count = 0
    theme_update_count = 0
    with zipfile.ZipFile(input_file) as source, zipfile.ZipFile(output_file, "w", zipfile.ZIP_DEFLATED) as target:
        names = {info.filename.replace("\\", "/") for info in source.infolist()}
        unsafe_entries = [name for name in names if _unsafe_zip_entry(name)]
        if unsafe_entries:
            raise OKofficeException(
                "unsafe_input_rejected",
                "Presentation package contains unsafe ZIP entry names.",
                details={"unsafe_package_entries": unsafe_entries},
            )
        theme_operation = next((operation for operation in operations if operation["op"] == "update_theme"), None)
        for info in source.infolist():
            name = info.filename.replace("\\", "/")
            data = source.read(info.filename)
            if name.startswith("ppt/slides/slide") and name.endswith(".xml"):
                text = data.decode("utf-8")
                for operation in operations:
                    if operation["op"] != "replace_text":
                        continue
                    text, count = _replace_xml_text(text, str(operation["find"]), str(operation["replace"]))
                    text_replacement_count += count
                data = text.encode("utf-8")
            elif name == THEME_PART and theme_operation is not None:
                data = _theme_xml(theme_operation).encode("utf-8")
                theme_update_count = 1
            target.writestr(name, data)
        if THEME_PART not in names and theme_operation is not None:
            target.writestr(THEME_PART, _theme_xml(theme_operation))
            theme_update_count = 1
    return {
        "text_replacement_count": text_replacement_count,
        "theme_update_count": theme_update_count,
    }


def _replace_xml_text(xml: str, find: str, replace: str) -> tuple[str, int]:
    escaped_find = html.escape(find, quote=False)
    escaped_replace = html.escape(replace, quote=False)
    return xml.replace(escaped_find, escaped_replace), xml.count(escaped_find)


def _style_from_operation(operation: dict[str, Any]) -> dict[str, str]:
    return {
        "theme_name": str(operation.get("theme_name") or "OKoffice Theme"),
        "primary_color": _color(operation.get("primary_color"), fallback="111827"),
        "accent_color": _color(operation.get("accent_color"), fallback="2563EB"),
        "font_family": str(operation.get("font_family") or "Aptos"),
    }


def _theme_xml(style: dict[str, Any]) -> str:
    theme_name = _xml_attr(style.get("theme_name") or "OKoffice Theme")
    primary = _xml_attr(_color(style.get("primary_color"), fallback="111827"))
    accent = _xml_attr(_color(style.get("accent_color"), fallback="2563EB"))
    font = _xml_attr(style.get("font_family") or "Aptos")
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="{theme_name}">'
        f'<a:themeElements><a:clrScheme name="{theme_name}">'
        f'<a:dk1><a:srgbClr val="{primary}"/></a:dk1>'
        '<a:lt1><a:srgbClr val="FFFFFF"/></a:lt1>'
        f'<a:accent1><a:srgbClr val="{accent}"/></a:accent1>'
        f'</a:clrScheme><a:fontScheme name="{theme_name}">'
        f'<a:majorFont><a:latin typeface="{font}"/></a:majorFont>'
        f'<a:minorFont><a:latin typeface="{font}"/></a:minorFont>'
        '</a:fontScheme><a:fmtScheme name="OKoffice"/></a:themeElements></a:theme>'
    )


def _color(value: Any, *, fallback: str) -> str:
    candidate = str(value or fallback).strip().lstrip("#").upper()
    if not re.fullmatch(r"[0-9A-F]{6}", candidate):
        raise OKofficeException("invalid_input", f"Invalid hex color: {value}")
    return candidate


def _validation_report(
    input_file: Path,
    output_file: Path,
    inspected: ToolResult,
    operations: list[dict[str, Any]],
    summary: dict[str, int],
) -> ValidationReport:
    return ValidationReport(
        status="passed",
        checks=[
            ValidationCheck(name="input_path_safe", status="passed", details={"path": input_file.as_posix()}),
            ValidationCheck(name="output_path_distinct", status="passed", details={"path": output_file.as_posix()}),
            ValidationCheck(name="operations_applied", status="passed", details={"operation_count": len(operations), **summary}),
            ValidationCheck(
                name="deck_patch_reopened_by_inspect",
                status="passed",
                details=inspected.usage.get("summary", {}),
            ),
        ],
    )


def _unsafe_zip_entry(name: str) -> bool:
    normalized = name.replace("\\", "/")
    return normalized.startswith("/") or normalized.startswith("../") or "/../" in normalized


def _xml_attr(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


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
