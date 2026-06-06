from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any
from okoffice.artifacts.store import build_artifact
from okoffice.office.deck import inspect_deck_presentation
from okoffice.office.shared import failed_result, job_id
from okoffice.schemas.errors import OKofficeException
from okoffice.schemas.models import OKofficeError, ToolResult, ValidationCheck, ValidationReport
from okoffice.security.paths import resolve_input_path, resolve_output_path


TOOL_NAME = "deck.patch.apply"
REVISE_TOOL_NAME = "deck.revise"
THEME_PART = "ppt/theme/theme1.xml"

NS_P = "http://schemas.openxmlformats.org/presentationml/2006/main"
NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_C = "http://schemas.openxmlformats.org/drawingml/2006/chart"


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
            job_id=job_id(),
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
                    "transaction_id": f"patch_{job_id().removeprefix('job_')}",
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
        return failed_result(TOOL_NAME, exc.to_error())
    except (zipfile.BadZipFile, ValueError) as exc:
        return failed_result(TOOL_NAME, OKofficeError(code="invalid_input", message=str(exc)))


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
        elif op == "patch_slide":
            slide = operation.get("slide")
            find = str(operation.get("find") or "")
            replace = str(operation.get("replace") or "")
            if slide is None:
                raise OKofficeException("invalid_input", f"Deck patch operation {index} requires a slide number.")
            if not find:
                raise OKofficeException("invalid_input", f"Deck patch operation {index} requires find text.")
            normalized.append({"op": op, "slide": int(slide), "find": find, "replace": replace})
        elif op == "patch_shape":
            slide = operation.get("slide")
            shape_id = str(operation.get("shape_id") or "")
            prop = str(operation.get("property") or "")
            value = str(operation.get("value") or "")
            if slide is None:
                raise OKofficeException("invalid_input", f"Deck patch operation {index} requires a slide number.")
            if not shape_id:
                raise OKofficeException("invalid_input", f"Deck patch operation {index} requires a shape_id.")
            if not prop:
                raise OKofficeException("invalid_input", f"Deck patch operation {index} requires a property name.")
            normalized.append({"op": op, "slide": int(slide), "shape_id": shape_id, "property": prop, "value": value})
        elif op == "patch_notes":
            slide = operation.get("slide")
            find = str(operation.get("find") or "")
            replace = str(operation.get("replace") or "")
            if slide is None:
                raise OKofficeException("invalid_input", f"Deck patch operation {index} requires a slide number.")
            if not find:
                raise OKofficeException("invalid_input", f"Deck patch operation {index} requires find text.")
            normalized.append({"op": op, "slide": int(slide), "find": find, "replace": replace})
        elif op == "patch_chart":
            chart_id = str(operation.get("chart_id") or "")
            title = str(operation.get("title") or "")
            if not chart_id:
                raise OKofficeException("invalid_input", f"Deck patch operation {index} requires a chart_id.")
            if not title:
                raise OKofficeException("invalid_input", f"Deck patch operation {index} requires a title.")
            normalized.append({"op": op, "chart_id": chart_id, "title": title})
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
    slide_patch_count = 0
    shape_patch_count = 0
    notes_patch_count = 0
    chart_patch_count = 0
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
        slide_patch_ops = [op for op in operations if op["op"] == "patch_slide"]
        shape_patch_ops = [op for op in operations if op["op"] == "patch_shape"]
        notes_patch_ops = [op for op in operations if op["op"] == "patch_notes"]
        chart_patch_ops = [op for op in operations if op["op"] == "patch_chart"]
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
                # patch_slide: scoped text replacement on a specific slide
                for operation in slide_patch_ops:
                    expected = f"ppt/slides/slide{operation['slide']}.xml"
                    if name == expected:
                        text, count = _replace_xml_text(text, str(operation["find"]), str(operation["replace"]))
                        slide_patch_count += count
                # patch_shape: modify a shape property on a specific slide
                for operation in shape_patch_ops:
                    expected = f"ppt/slides/slide{operation['slide']}.xml"
                    if name == expected:
                        data_new, did_patch = _patch_shape_property(data, operation["shape_id"], operation["property"], operation["value"])
                        if did_patch:
                            shape_patch_count += 1
                            text = data_new.decode("utf-8")
                data = text.encode("utf-8") if isinstance(text, str) else data
            elif name.startswith("ppt/notesSlides/notesSlide") and name.endswith(".xml"):
                text = data.decode("utf-8")
                for operation in notes_patch_ops:
                    expected = f"ppt/notesSlides/notesSlide{operation['slide']}.xml"
                    if name == expected:
                        text, count = _replace_xml_text(text, str(operation["find"]), str(operation["replace"]))
                        notes_patch_count += count
                data = text.encode("utf-8")
            elif name == THEME_PART and theme_operation is not None:
                data = _theme_xml(theme_operation).encode("utf-8")
                theme_update_count = 1
            elif name.startswith("ppt/charts/chart") and name.endswith(".xml"):
                for operation in chart_patch_ops:
                    expected = f"ppt/charts/chart{operation['chart_id']}.xml"
                    if name == expected:
                        data_new, did_patch = _patch_chart_title(data, operation["title"])
                        if did_patch:
                            chart_patch_count += 1
                            data = data_new
            target.writestr(name, data)
        if THEME_PART not in names and theme_operation is not None:
            target.writestr(THEME_PART, _theme_xml(theme_operation))
            theme_update_count = 1
    return {
        "text_replacement_count": text_replacement_count,
        "theme_update_count": theme_update_count,
        "slide_patch_count": slide_patch_count,
        "shape_patch_count": shape_patch_count,
        "notes_patch_count": notes_patch_count,
        "chart_patch_count": chart_patch_count,
    }


def _replace_xml_text(xml: str, find: str, replace: str) -> tuple[str, int]:
    escaped_find = html.escape(find, quote=False)
    escaped_replace = html.escape(replace, quote=False)
    return xml.replace(escaped_find, escaped_replace), xml.count(escaped_find)


def _patch_shape_property(data: bytes, shape_id: str, prop: str, value: str) -> tuple[bytes, bool]:
    """Patch a shape property on a slide XML part.

    Finds ``<p:cNvPr id="{shape_id}">`` and updates the attribute named *prop*
    to *value*.  Returns (new_bytes, patched).
    """
    try:
        root = ET.fromstring(data)
    except ET.ParseError:
        return data, False
    found = False
    for cnv_pr in root.iter(f"{{{NS_P}}}cNvPr"):
        if cnv_pr.get("id") == shape_id:
            cnv_pr.set(prop, value)
            found = True
    if not found:
        return data, False
    _register_namespaces(root)
    return ET.tostring(root, encoding="unicode", xml_declaration=True).encode("utf-8"), True


def _patch_chart_title(data: bytes, title: str) -> tuple[bytes, bool]:
    """Set or replace the chart title in a chart XML part.

    Looks for ``<c:title>`` and replaces the text.  If an
    ``<c:autoTitleDeleted>`` element exists instead, it is replaced with a
    proper ``<c:title>`` block.  Returns (new_bytes, patched).
    """
    try:
        root = ET.fromstring(data)
    except ET.ParseError:
        return data, False
    title_elem = root.find(f".//{{{NS_C}}}title")
    if title_elem is not None:
        _set_chart_title_text(title_elem, title)
        _register_namespaces(root)
        return ET.tostring(root, encoding="unicode", xml_declaration=True).encode("utf-8"), True
    auto_deleted = root.find(f".//{{{NS_C}}}autoTitleDeleted")
    if auto_deleted is not None:
        parent = _find_parent(root, auto_deleted)
        if parent is not None:
            idx = list(parent).index(auto_deleted)
            new_title = _build_chart_title_element(title)
            parent.remove(auto_deleted)
            parent.insert(idx, new_title)
            _register_namespaces(root)
            return ET.tostring(root, encoding="unicode", xml_declaration=True).encode("utf-8"), True
    return data, False


def _set_chart_title_text(title_elem: ET.Element, title: str) -> None:
    """Replace the text inside an existing ``<c:title>`` element."""
    tx_pr = title_elem.find(f"{{{NS_C}}}tx")
    if tx_pr is None:
        tx_pr = ET.SubElement(title_elem, f"{{{NS_C}}}tx")
    rich = tx_pr.find(f"{{{NS_C}}}rich")
    if rich is None:
        rich = ET.SubElement(tx_pr, f"{{{NS_C}}}rich")
        ET.SubElement(rich, f"{{{NS_A}}}bodyPr")
        ET.SubElement(rich, f"{{{NS_A}}}lstStyle")
    for p_elem in rich.findall(f"{{{NS_A}}}p"):
        rich.remove(p_elem)
    p_elem = ET.SubElement(rich, f"{{{NS_A}}}p")
    r_elem = ET.SubElement(p_elem, f"{{{NS_A}}}r")
    t_elem = ET.SubElement(r_elem, f"{{{NS_A}}}t")
    t_elem.text = title


def _build_chart_title_element(title: str) -> ET.Element:
    """Build a new ``<c:title>`` element with the given text."""
    title_elem = ET.Element(f"{{{NS_C}}}title")
    overlay = ET.SubElement(title_elem, f"{{{NS_C}}}overlay", val="0")
    tx = ET.SubElement(title_elem, f"{{{NS_C}}}tx")
    rich = ET.SubElement(tx, f"{{{NS_C}}}rich")
    ET.SubElement(rich, f"{{{NS_A}}}bodyPr")
    ET.SubElement(rich, f"{{{NS_A}}}lstStyle")
    p_elem = ET.SubElement(rich, f"{{{NS_A}}}p")
    r_elem = ET.SubElement(p_elem, f"{{{NS_A}}}r")
    rPr = ET.SubElement(r_elem, f"{{{NS_A}}}rPr", lang="en-US")
    rPr.set("dirty", "0")
    t_elem = ET.SubElement(r_elem, f"{{{NS_A}}}t")
    t_elem.text = title
    return title_elem


def _find_parent(root: ET.Element, child: ET.Element) -> ET.Element | None:
    """Find the parent element of *child* within *root*."""
    parent_map = {c: p for p in root.iter() for c in p}
    return parent_map.get(child)


def _register_namespaces(root: ET.Element) -> None:
    """Register common OOXML namespaces so ET.tostring preserves prefixes."""
    ET.register_namespace("p", NS_P)
    ET.register_namespace("a", NS_A)
    ET.register_namespace("r", NS_R)
    ET.register_namespace("c", NS_C)


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


def revise_deck(
    *,
    input_path: str | Path,
    output_path: str | Path,
    operations: list[dict[str, Any]],
) -> ToolResult:
    """Apply revisions to a deck and re-run validation.

    A higher-level wrapper around apply_deck_patch that also runs
    structural validation and optional taste review on the result.
    """
    patch_result = apply_deck_patch(
        input_path=input_path,
        output_path=output_path,
        operations=operations,
    )
    if patch_result.status != "succeeded":
        return ToolResult(
            job_id=job_id(),
            status="failed",
            tool=REVISE_TOOL_NAME,
            error=patch_result.error or OKofficeError(code="revision_failed", message="Patch application failed."),
            warnings=patch_result.warnings,
            usage={
                "revision": {
                    "input_path": str(input_path),
                    "output_path": str(output_path),
                    "operation_count": len(operations),
                    "patch_status": "failed",
                },
            },
        )

    output_file = Path(output_path).expanduser().resolve()
    validation_result = _run_post_revision_validation(output_file)

    patch_summary = patch_result.usage.get("summary", {})
    patch_transaction = patch_result.usage.get("patch_transaction", {})

    checks = list(patch_result.validation.checks) if patch_result.validation else []
    checks.extend(validation_result.get("checks", []))

    return ToolResult(
        job_id=job_id(),
        status="succeeded",
        tool=REVISE_TOOL_NAME,
        artifacts=patch_result.artifacts,
        validation=ValidationReport(
            status=_revision_status(checks),
            checks=checks,
            warnings=patch_result.warnings,
        ),
        warnings=patch_result.warnings,
        usage={
            "summary": {
                **patch_summary,
                "validation_status": validation_result.get("status", "skipped"),
            },
            "revision": {
                "input_path": str(input_path),
                "output_path": output_file.as_posix(),
                "operation_count": len(operations),
                "patch_status": "succeeded",
                "validation_status": validation_result.get("status", "skipped"),
            },
            "patch_transaction": patch_transaction,
            "post_revision_validation": validation_result,
        },
        next_recommended_tools=[
            "deck.validate.presentation",
            "deck.inspect.presentation",
            "office.bundle.export",
        ],
    )


def _run_post_revision_validation(output_path: Path) -> dict[str, Any]:
    inspected = inspect_deck_presentation(output_path)
    if inspected.status != "succeeded":
        return {
            "status": "skipped",
            "checks": [
                ValidationCheck(
                    name="post_revision_validation",
                    status="skipped",
                    message="Post-revision deck inspection failed.",
                ),
            ],
        }

    summary = inspected.usage.get("summary", {})
    slides = inspected.usage.get("slides", [])
    missing_titles = [s for s in slides if isinstance(s, dict) and not str(s.get("title") or "").strip()]
    validation_status = "passed" if not missing_titles else "warning"
    return {
        "status": validation_status,
        "slide_count": int(summary.get("slide_count", 0)),
        "checks": [
            ValidationCheck(
                name="post_revision_slide_count",
                status="passed" if int(summary.get("slide_count", 0)) > 0 else "warning",
                details={"slide_count": summary.get("slide_count", 0)},
            ),
            ValidationCheck(
                name="post_revision_titles_present",
                status="passed" if not missing_titles else "warning",
                details={"missing_title_count": len(missing_titles)},
            ),
        ],
    }


def _revision_status(checks: list[ValidationCheck]) -> str:
    statuses = [check.status for check in checks]
    if "failed" in statuses:
        return "failed"
    if "warning" in statuses:
        return "warning"
    if all(status == "skipped" for status in statuses):
        return "skipped"
    return "passed"
