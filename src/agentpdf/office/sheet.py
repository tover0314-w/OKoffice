from __future__ import annotations

import zipfile
from pathlib import Path, PurePosixPath
from typing import Any
from uuid import uuid4
from xml.etree import ElementTree

from agentpdf.office.ir import SheetLocator
from agentpdf.schemas.errors import AgentPDFException
from agentpdf.schemas.models import AgentPDFError, ToolResult, ValidationCheck, ValidationReport
from agentpdf.security.paths import resolve_input_path


S_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
REL_NS = "{http://schemas.openxmlformats.org/package/2006/relationships}"
OFFICE_R_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
DC_NS = "{http://purl.org/dc/elements/1.1/}"
CORE_NS = "{http://schemas.openxmlformats.org/package/2006/metadata/core-properties}"
WORKBOOK_PART = "xl/workbook.xml"
WORKBOOK_RELS_PART = "xl/_rels/workbook.xml.rels"


def inspect_sheet_workbook(path: str | Path) -> ToolResult:
    tool = "sheet.inspect.workbook"
    try:
        resolved = resolve_input_path(path)
        usage, warnings = _inspect_xlsx(resolved)
        unsafe_entries = list(usage["package"].get("unsafe_package_entries", []))
        if unsafe_entries:
            raise AgentPDFException(
                "unsafe_input_rejected",
                "Workbook package contains unsafe ZIP entry names.",
                details={"unsafe_package_entries": unsafe_entries},
            )
        return ToolResult(
            job_id=_job_id(),
            status="succeeded",
            tool=tool,
            validation=_validation_report(resolved, usage, warnings),
            warnings=warnings,
            usage=usage,
            next_recommended_tools=["sheet.validation.formulas", "office.context.build_packet"],
        )
    except AgentPDFException as exc:
        return _failed(tool, exc.to_error())


def _inspect_xlsx(path: Path) -> tuple[dict[str, Any], list[str]]:
    if path.suffix.lower() not in {".xlsx", ".xlsm"} or not zipfile.is_zipfile(path):
        raise AgentPDFException(
            "unsupported_file_type",
            f"Sheet inspect requires a readable XLSX/XLSM package: {path.name}",
            details={"path": path.as_posix()},
        )
    warnings: list[str] = []
    with zipfile.ZipFile(path) as archive:
        names = {name.replace("\\", "/") for name in archive.namelist()}
        if WORKBOOK_PART not in names:
            raise AgentPDFException(
                "unsupported_file_type",
                "Workbook package is missing xl/workbook.xml.",
                details={"path": path.as_posix()},
            )
        workbook = ElementTree.fromstring(archive.read(WORKBOOK_PART))
        workbook_rels = _read_relationships(archive, WORKBOOK_RELS_PART, WORKBOOK_PART, names)
        external_relationships = _external_relationships(archive, names)
        sheets, formulas, tables, comments, charts, data_model, chart_plan = _read_sheets(
            archive,
            workbook,
            workbook_rels,
            names,
        )
        named_ranges = _read_named_ranges(workbook)
        metadata = _read_core_metadata(archive, names)
        package = _package_markers(path, names, external_relationships)

    hidden_sheets = [sheet for sheet in sheets if sheet["hidden"]]
    if package["macro_enabled"]:
        warnings.append("Macro-enabled workbook package markers were detected; macros are not executed.")
    if package["has_external_relationships"]:
        warnings.append("External workbook relationship targets were detected.")
    if hidden_sheets:
        warnings.append("Hidden workbook sheets were detected.")

    usage = {
        "file": {
            "path": path.as_posix(),
            "name": path.name,
            "extension": path.suffix.lower(),
            "size_bytes": path.stat().st_size,
        },
        "summary": {
            "sheet_count": len(sheets),
            "visible_sheet_count": len(sheets) - len(hidden_sheets),
            "hidden_sheet_count": len(hidden_sheets),
            "table_count": len(tables),
            "formula_count": len(formulas),
            "chart_count": len(charts),
            "data_model_count": int(data_model.get("field_count", 0)),
            "chart_plan_count": int(chart_plan.get("chart_plan_count", 0)),
            "named_range_count": len(named_ranges),
            "comment_count": len(comments),
            "external_link_count": len(external_relationships),
        },
        "metadata": metadata,
        "package": package,
        "sheets": sheets,
        "tables": tables,
        "formulas": formulas,
        "charts": charts,
        "data_model": data_model,
        "chart_plan": chart_plan,
        "comments": comments,
        "named_ranges": named_ranges,
        "formula_evaluation": {
            "status": "structural_only",
            "evaluated": False,
            "reason": "Local OSS workbook inspect does not calculate formulas.",
        },
    }
    return usage, warnings


def _read_sheets(
    archive: zipfile.ZipFile,
    workbook: ElementTree.Element,
    workbook_rels: dict[str, dict[str, str]],
    names: set[str],
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[str, Any],
    dict[str, Any],
]:
    sheets: list[dict[str, Any]] = []
    formulas: list[dict[str, Any]] = []
    tables: list[dict[str, Any]] = []
    comments: list[dict[str, Any]] = []
    charts: list[dict[str, Any]] = []
    sheet_rows_by_name: dict[str, list[list[str]]] = {}

    for index, sheet in enumerate(workbook.findall(f"{S_NS}sheets/{S_NS}sheet")):
        sheet_name = str(sheet.attrib.get("name") or f"Sheet{index + 1}")
        rel_id = sheet.attrib.get(f"{OFFICE_R_NS}id")
        state = sheet.attrib.get("state", "visible")
        hidden = state in {"hidden", "veryHidden"}
        part = workbook_rels.get(str(rel_id), {}).get("target") if rel_id else None
        sheet_info = {
            "name": sheet_name,
            "sheet_id": sheet.attrib.get("sheetId"),
            "state": state,
            "hidden": hidden,
            "part": part,
            "used_range": None,
            "row_count": 0,
            "formula_count": 0,
            "table_count": 0,
            "chart_count": 0,
            "comment_count": 0,
            "locator": _locator(sheet=sheet_name),
        }
        if part and part in names:
            sheet_root = ElementTree.fromstring(archive.read(part))
            sheet_rows_by_name[sheet_name] = _worksheet_rows(sheet_root)
            sheet_info.update(_sheet_dimensions(sheet_root))
            sheet_formulas = _read_formulas(sheet_root, sheet_name)
            sheet_rels = _sheet_relationships(archive, part, names)
            sheet_tables = _read_tables(archive, sheet_name, sheet_rels, names)
            sheet_comments = _read_comments(archive, sheet_name, sheet_rels, names)
            sheet_charts = _read_charts(archive, sheet_name, sheet_rels, names)
            formulas.extend(sheet_formulas)
            tables.extend(sheet_tables)
            comments.extend(sheet_comments)
            charts.extend(sheet_charts)
            sheet_info["formula_count"] = len(sheet_formulas)
            sheet_info["table_count"] = len(sheet_tables)
            sheet_info["chart_count"] = len(sheet_charts)
            sheet_info["comment_count"] = len(sheet_comments)
        sheets.append(sheet_info)

    data_model = _data_model_from_rows(sheet_rows_by_name.get("DataModel", []))
    chart_plan = _chart_plan_from_rows(sheet_rows_by_name.get("Charts", []))
    charts.extend(_planned_charts_from_chart_plan(chart_plan))

    return sheets, formulas, tables, comments, charts, data_model, chart_plan


def _sheet_dimensions(sheet_root: ElementTree.Element) -> dict[str, Any]:
    dimension = sheet_root.find(f"{S_NS}dimension")
    used_range = dimension.attrib.get("ref") if dimension is not None else None
    rows = sheet_root.findall(f"{S_NS}sheetData/{S_NS}row")
    return {
        "used_range": used_range,
        "row_count": len(rows),
    }


def _read_formulas(sheet_root: ElementTree.Element, sheet_name: str) -> list[dict[str, Any]]:
    formulas = []
    for cell in sheet_root.findall(f".//{S_NS}c"):
        formula_node = cell.find(f"{S_NS}f")
        if formula_node is None:
            continue
        cell_ref = str(cell.attrib.get("r") or "")
        formula = formula_node.text or ""
        value_node = cell.find(f"{S_NS}v")
        formulas.append(
            {
                "sheet": sheet_name,
                "cell": cell_ref,
                "formula": formula,
                "cached_value": value_node.text if value_node is not None else None,
                "has_external_reference": "[" in formula,
                "locator": _locator(sheet=sheet_name, cell=cell_ref, formula=formula),
            }
        )
    return formulas


def _read_tables(
    archive: zipfile.ZipFile,
    sheet_name: str,
    relationships: dict[str, dict[str, str]],
    names: set[str],
) -> list[dict[str, Any]]:
    tables = []
    for relationship in relationships.values():
        if not relationship["type"].endswith("/table") or relationship["target"] not in names:
            continue
        root = ElementTree.fromstring(archive.read(relationship["target"]))
        name = root.attrib.get("displayName") or root.attrib.get("name") or root.attrib.get("id")
        table_range = root.attrib.get("ref")
        tables.append(
            {
                "sheet": sheet_name,
                "name": name,
                "range": table_range,
                "column_count": len(root.findall(f"{S_NS}tableColumns/{S_NS}tableColumn")),
                "locator": _locator(sheet=sheet_name, range=table_range, table=name),
            }
        )
    return tables


def _read_comments(
    archive: zipfile.ZipFile,
    sheet_name: str,
    relationships: dict[str, dict[str, str]],
    names: set[str],
) -> list[dict[str, Any]]:
    comments: list[dict[str, Any]] = []
    for relationship in relationships.values():
        if not relationship["type"].endswith("/comments") or relationship["target"] not in names:
            continue
        root = ElementTree.fromstring(archive.read(relationship["target"]))
        authors = [author.text or "" for author in root.findall(f"{S_NS}authors/{S_NS}author")]
        for comment in root.findall(f"{S_NS}commentList/{S_NS}comment"):
            author_index = int(comment.attrib.get("authorId", "0"))
            cell_ref = str(comment.attrib.get("ref") or "")
            comments.append(
                {
                    "sheet": sheet_name,
                    "cell": cell_ref,
                    "author": authors[author_index] if author_index < len(authors) else None,
                    "text": _text_content(comment),
                    "locator": _locator(sheet=sheet_name, cell=cell_ref),
                }
            )
    return comments


def _read_charts(
    archive: zipfile.ZipFile,
    sheet_name: str,
    relationships: dict[str, dict[str, str]],
    names: set[str],
) -> list[dict[str, Any]]:
    charts = []
    for relationship in relationships.values():
        if not relationship["type"].endswith("/drawing") or relationship["target"] not in names:
            continue
        drawing_rels_part = _rels_part_for(relationship["target"])
        drawing_rels = _read_relationships(archive, drawing_rels_part, relationship["target"], names)
        for drawing_relationship in drawing_rels.values():
            if not drawing_relationship["type"].endswith("/chart"):
                continue
            chart_id = PurePosixPath(drawing_relationship["target"]).stem
            charts.append(
                {
                    "sheet": sheet_name,
                    "chart_id": chart_id,
                    "part": drawing_relationship["target"],
                    "locator": _locator(sheet=sheet_name, chart=chart_id),
                }
            )
    return charts


def _read_named_ranges(workbook: ElementTree.Element) -> list[dict[str, Any]]:
    named_ranges = []
    for defined_name in workbook.findall(f"{S_NS}definedNames/{S_NS}definedName"):
        named_ranges.append(
            {
                "name": defined_name.attrib.get("name"),
                "refers_to": defined_name.text or "",
                "scope": defined_name.attrib.get("localSheetId"),
            }
        )
    return named_ranges


def _worksheet_rows(sheet_root: ElementTree.Element) -> list[list[str]]:
    rows = []
    for row in sheet_root.findall(f"{S_NS}sheetData/{S_NS}row"):
        cells: dict[int, str] = {}
        for cell in row.findall(f"{S_NS}c"):
            cell_ref = str(cell.attrib.get("r") or "")
            column = _column_index(cell_ref)
            if column == 0:
                continue
            cells[column] = _cell_display_text(cell)
        if cells:
            rows.append([cells.get(index, "") for index in range(1, max(cells) + 1)])
    return rows


def _cell_display_text(cell: ElementTree.Element) -> str:
    inline = cell.find(f"{S_NS}is/{S_NS}t")
    if inline is not None:
        return inline.text or ""
    value = cell.find(f"{S_NS}v")
    return value.text if value is not None and value.text is not None else ""


def _data_model_from_rows(rows: list[list[str]]) -> dict[str, Any]:
    fields = _table_dicts(rows)
    return {
        "field_count": len(fields),
        "fields": fields,
    }


def _chart_plan_from_rows(rows: list[list[str]]) -> dict[str, Any]:
    charts = _table_dicts(rows)
    return {
        "chart_plan_count": len(charts),
        "charts": charts,
    }


def _planned_charts_from_chart_plan(chart_plan: dict[str, Any]) -> list[dict[str, Any]]:
    charts = []
    for chart in chart_plan.get("charts", []):
        chart_id = str(chart.get("chart_id") or "")
        if not chart_id:
            continue
        charts.append(
            {
                "sheet": str(chart.get("source_sheet") or "Evidence"),
                "chart_id": chart_id,
                "chart_type": chart.get("chart_type"),
                "title": chart.get("title"),
                "source_range": chart.get("source_range"),
                "planned": True,
                "locator": _locator(sheet=str(chart.get("source_sheet") or "Evidence"), chart=chart_id),
            }
        )
    return charts


def _table_dicts(rows: list[list[str]]) -> list[dict[str, str]]:
    if not rows:
        return []
    headers = [header.strip() for header in rows[0]]
    records = []
    for row in rows[1:]:
        records.append({header: row[index] if index < len(row) else "" for index, header in enumerate(headers) if header})
    return records


def _column_index(cell_ref: str) -> int:
    value = 0
    for char in cell_ref.upper():
        if not ("A" <= char <= "Z"):
            break
        value = value * 26 + ord(char) - 64
    return value


def _read_relationships(
    archive: zipfile.ZipFile,
    rels_part: str,
    source_part: str,
    names: set[str],
) -> dict[str, dict[str, str]]:
    if rels_part not in names:
        return {}
    root = ElementTree.fromstring(archive.read(rels_part))
    relationships = {}
    for relationship in root.findall(f"{REL_NS}Relationship"):
        rel_id = str(relationship.attrib.get("Id") or "")
        target = str(relationship.attrib.get("Target") or "")
        relationships[rel_id] = {
            "id": rel_id,
            "type": str(relationship.attrib.get("Type") or ""),
            "target": _resolve_target(source_part, target),
            "target_mode": str(relationship.attrib.get("TargetMode") or ""),
        }
    return relationships


def _sheet_relationships(archive: zipfile.ZipFile, sheet_part: str, names: set[str]) -> dict[str, dict[str, str]]:
    return _read_relationships(archive, _rels_part_for(sheet_part), sheet_part, names)


def _rels_part_for(part: str) -> str:
    path = PurePosixPath(part)
    return str(path.parent / "_rels" / f"{path.name}.rels")


def _resolve_target(source_part: str, target: str) -> str:
    if "://" in target:
        return target
    if target.startswith("/"):
        return target.lstrip("/")
    path = PurePosixPath(source_part).parent / target
    parts: list[str] = []
    for part in path.parts:
        if part in {"", "."}:
            continue
        if part == "..":
            if parts:
                parts.pop()
            continue
        parts.append(part)
    return "/".join(parts)


def _external_relationships(archive: zipfile.ZipFile, names: set[str]) -> list[dict[str, str]]:
    relationships = []
    for name in sorted(names):
        if not name.endswith(".rels"):
            continue
        root = ElementTree.fromstring(archive.read(name))
        for relationship in root.findall(f"{REL_NS}Relationship"):
            if relationship.attrib.get("TargetMode") == "External":
                relationships.append(
                    {
                        "relationship_part": name,
                        "type": str(relationship.attrib.get("Type") or ""),
                        "target": str(relationship.attrib.get("Target") or ""),
                    }
                )
    return relationships


def _read_core_metadata(archive: zipfile.ZipFile, names: set[str]) -> dict[str, Any]:
    if "docProps/core.xml" not in names:
        return {}
    root = ElementTree.fromstring(archive.read("docProps/core.xml"))
    return {
        "title": _first_text(root, f"{DC_NS}title"),
        "creator": _first_text(root, f"{DC_NS}creator"),
        "last_modified_by": _first_text(root, f"{CORE_NS}lastModifiedBy"),
    }


def _package_markers(path: Path, names: set[str], external_relationships: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "package_type": "ooxml_xlsx",
        "zip_entry_count": len(names),
        "macro_enabled": path.suffix.lower() == ".xlsm" or any(name.lower().endswith("vbaproject.bin") for name in names),
        "has_external_relationships": bool(external_relationships),
        "external_relationships": external_relationships,
        "unsafe_package_entries": [name for name in names if _unsafe_zip_entry(name)],
    }


def _unsafe_zip_entry(name: str) -> bool:
    normalized = name.replace("\\", "/")
    return normalized.startswith("/") or normalized.startswith("../") or "/../" in normalized


def _text_content(element: ElementTree.Element) -> str:
    values = []
    for node in element.iter():
        if node.tag == f"{S_NS}t" and node.text:
            values.append(node.text)
    return "".join(values).strip()


def _first_text(root: ElementTree.Element, tag: str) -> str | None:
    node = root.find(tag)
    return node.text if node is not None else None


def _locator(**kwargs: Any) -> dict[str, Any]:
    return SheetLocator(**kwargs).model_dump(mode="json", exclude_none=True)


def _validation_report(path: Path, usage: dict[str, Any], warnings: list[str]) -> ValidationReport:
    return ValidationReport(
        status="warning" if warnings else "passed",
        checks=[
            ValidationCheck(name="input_path_safe", status="passed", message="Input path passed local safety checks."),
            ValidationCheck(name="workbook_xml_present", status="passed", details={"path": path.as_posix()}),
            ValidationCheck(name="structure_extracted", status="passed", details=usage["summary"]),
            ValidationCheck(
                name="formula_evaluation_explicit",
                status="passed",
                details=usage["formula_evaluation"],
            ),
        ],
        warnings=warnings,
    )


def _failed(tool: str, error: AgentPDFError) -> ToolResult:
    return ToolResult(
        job_id=_job_id(),
        status="failed",
        tool=tool,
        error=error,
        warnings=[error.message],
    )


def _job_id() -> str:
    return f"job_{uuid4().hex[:16]}"
