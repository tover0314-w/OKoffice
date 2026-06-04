from __future__ import annotations

import re
from pathlib import Path
from xml.etree import ElementTree
from uuid import uuid4

from agentpdf.office.inspect import inspect_office_file
from agentpdf.office.ooxml import SHEET_NS, count_members, read_xml, sorted_members, zip_names
from agentpdf.schemas.models import AgentPDFError, ToolResult, ValidationCheck, ValidationReport


INSPECT_TOOL_NAME = "sheet.inspect.workbook"
EXTRACT_TABLES_TOOL_NAME = "sheet.extract.tables"
CELL_REF_RE = re.compile(r"^([A-Z]+)([0-9]+)$", re.IGNORECASE)


def inspect_sheet_workbook(path: str | Path) -> ToolResult:
    preflight = inspect_office_file(path)
    if preflight.status == "failed":
        return _failed(
            INSPECT_TOOL_NAME,
            preflight.error or AgentPDFError(code="unsupported_file_type", message="Sheet inspect failed."),
        )
    if preflight.usage["format"]["detected_format"] != "xlsx":
        return _failed(
            INSPECT_TOOL_NAME,
            AgentPDFError(
                code="unsupported_file_type",
                message="sheet.inspect.workbook requires an XLSX-compatible OOXML package.",
                details={"detected_format": preflight.usage["format"]["detected_format"]},
            )
        )

    source_path = Path(preflight.usage["file"]["path"])
    names = zip_names(source_path)
    workbook_root = read_xml(source_path, "xl/workbook.xml")
    sheet_names = _sheet_names(workbook_root)
    worksheet_members = sorted_members(names, prefix="xl/worksheets/sheet")
    sheets = _sheet_summaries(source_path, worksheet_members, sheet_names)
    formula_count = sum(int(sheet["formula_count"]) for sheet in sheets)

    return ToolResult(
        job_id=_job_id(),
        status="succeeded",
        tool=INSPECT_TOOL_NAME,
        validation=ValidationReport(
            status="passed",
            checks=[
                ValidationCheck(name="format_is_xlsx", status="passed", details=preflight.usage["format"]),
                ValidationCheck(name="workbook_xml_present", status="passed"),
            ],
        ),
        usage={
            "workbook": {
                "path": source_path.as_posix(),
                "format": "xlsx",
                "package_type": preflight.usage["format"]["package_type"],
                "sheet_count": len(sheets),
            },
            "sheets": sheets,
            "formulas": {"formula_count": formula_count},
            "tables": {"table_count": count_members(names, prefix="xl/tables/")},
            "charts": {"chart_count": count_members(names, prefix="xl/charts/")},
            "links": {"external_link_count": count_members(names, prefix="xl/externalLinks/")},
            "safety": preflight.usage["safety"],
        },
        next_recommended_tools=["sheet.extract.tables", "sheet.profile.data", "office.context.build_packet"],
    )


def extract_sheet_tables(path: str | Path) -> ToolResult:
    preflight = inspect_office_file(path)
    if preflight.status == "failed":
        return _failed(
            EXTRACT_TABLES_TOOL_NAME,
            preflight.error or AgentPDFError(code="unsupported_file_type", message="Sheet table extraction failed."),
        )
    if preflight.usage["format"]["detected_format"] != "xlsx":
        return _failed(
            EXTRACT_TABLES_TOOL_NAME,
            AgentPDFError(
                code="unsupported_file_type",
                message="sheet.extract.tables requires an XLSX-compatible OOXML package.",
                details={"detected_format": preflight.usage["format"]["detected_format"]},
            ),
        )

    source_path = Path(preflight.usage["file"]["path"])
    names = zip_names(source_path)
    workbook_root = read_xml(source_path, "xl/workbook.xml")
    sheet_names = _sheet_names(workbook_root)
    worksheet_members = sorted_members(names, prefix="xl/worksheets/sheet")
    shared_strings = _shared_strings(read_xml(source_path, "xl/sharedStrings.xml"))
    tables = _extract_worksheet_tables(source_path, worksheet_members, sheet_names, shared_strings)
    row_count = sum(len(table["rows"]) for table in tables)
    cell_count = sum(len(row["cells"]) for table in tables for row in table["rows"])

    return ToolResult(
        job_id=_job_id(),
        status="succeeded",
        tool=EXTRACT_TABLES_TOOL_NAME,
        validation=ValidationReport(
            status="passed",
            checks=[
                ValidationCheck(name="format_is_xlsx", status="passed", details=preflight.usage["format"]),
                ValidationCheck(name="workbook_xml_present", status="passed"),
                ValidationCheck(
                    name="tables_extracted",
                    status="passed",
                    details={"table_count": len(tables), "row_count": row_count, "cell_count": cell_count},
                ),
            ],
        ),
        usage={
            "workbook": {
                "path": source_path.as_posix(),
                "format": "xlsx",
                "package_type": preflight.usage["format"]["package_type"],
                "sheet_count": len(worksheet_members),
            },
            "summary": {"table_count": len(tables), "row_count": row_count, "cell_count": cell_count},
            "tables": tables,
            "safety": preflight.usage["safety"],
        },
        next_recommended_tools=["sheet.write.workbook", "office.workflow.extract_to_sheet", "office.context.build_packet"],
    )


def _sheet_names(workbook_root: object | None) -> list[str]:
    if workbook_root is None:
        return []
    return [
        str(sheet.get("name") or f"Sheet {index}")
        for index, sheet in enumerate(workbook_root.findall(".//main:sheet", SHEET_NS), start=1)
    ]


def _sheet_summaries(path: Path, worksheet_members: list[str], sheet_names: list[str]) -> list[dict[str, object]]:
    summaries = []
    for index, member in enumerate(worksheet_members, start=1):
        worksheet_root = read_xml(path, member)
        dimension = ""
        formula_count = 0
        if worksheet_root is not None:
            dimension_element = worksheet_root.find(".//main:dimension", SHEET_NS)
            dimension = str(dimension_element.get("ref") or "") if dimension_element is not None else ""
            formula_count = len(worksheet_root.findall(".//main:f", SHEET_NS))
        summaries.append(
            {
                "name": sheet_names[index - 1] if index <= len(sheet_names) else f"Sheet {index}",
                "sheet_index": index,
                "member": member,
                "dimension": dimension,
                "formula_count": formula_count,
            }
        )
    return summaries


def _extract_worksheet_tables(
    path: Path,
    worksheet_members: list[str],
    sheet_names: list[str],
    shared_strings: list[str],
) -> list[dict[str, object]]:
    tables = []
    for sheet_index, member in enumerate(worksheet_members, start=1):
        worksheet_root = read_xml(path, member)
        if worksheet_root is None:
            continue
        sheet_name = sheet_names[sheet_index - 1] if sheet_index <= len(sheet_names) else f"Sheet {sheet_index}"
        rows = _worksheet_rows(path, worksheet_root, sheet_name, sheet_index, shared_strings)
        if not rows:
            continue
        range_ref = _worksheet_range(worksheet_root, rows)
        tables.append(
            {
                "table_id": f"sheet_{sheet_index}_table_1",
                "table_index": len(tables) + 1,
                "source": {
                    "workbook_path": path.as_posix(),
                    "sheet_name": sheet_name,
                    "sheet_index": sheet_index,
                    "member": member,
                    "range_ref": range_ref,
                },
                "rows": rows,
            }
        )
    return tables


def _worksheet_rows(
    path: Path,
    worksheet_root: ElementTree.Element,
    sheet_name: str,
    sheet_index: int,
    shared_strings: list[str],
) -> list[dict[str, object]]:
    rows = []
    for row_element in worksheet_root.findall(".//main:sheetData/main:row", SHEET_NS):
        row_index = _row_index(row_element)
        cells = []
        for cell_element in row_element.findall("./main:c", SHEET_NS):
            cell_ref = str(cell_element.get("r") or "")
            parsed_ref = _parse_cell_ref(cell_ref)
            if parsed_ref is None:
                column_index = len(cells) + 1
                resolved_ref = f"{_column_letters(column_index)}{row_index}"
            else:
                row_index, column_index = parsed_ref
                resolved_ref = cell_ref.upper()
            value = _cell_value(cell_element, shared_strings)
            if value == "":
                continue
            source = {
                "workbook_path": path.as_posix(),
                "sheet_name": sheet_name,
                "sheet_index": sheet_index,
                "cell_ref": resolved_ref,
                "row_index": row_index,
                "column_index": column_index,
            }
            cell_payload: dict[str, object] = {
                "cell_ref": resolved_ref,
                "row_index": row_index,
                "column_index": column_index,
                "value": value,
                "data_type": str(cell_element.get("t") or "number"),
                "source": source,
            }
            formula = cell_element.find("./main:f", SHEET_NS)
            if formula is not None and formula.text:
                cell_payload["formula"] = formula.text
            cells.append(cell_payload)
        if cells:
            rows.append({"row_index": row_index, "cells": cells})
    return rows


def _worksheet_range(worksheet_root: ElementTree.Element, rows: list[dict[str, object]]) -> str:
    dimension_element = worksheet_root.find(".//main:dimension", SHEET_NS)
    if dimension_element is not None and dimension_element.get("ref"):
        return str(dimension_element.get("ref"))
    row_numbers = [int(row["row_index"]) for row in rows]
    column_numbers = [
        int(cell["column_index"])
        for row in rows
        for cell in row["cells"]
        if isinstance(cell, dict) and "column_index" in cell
    ]
    if not row_numbers or not column_numbers:
        return ""
    return f"{_column_letters(min(column_numbers))}{min(row_numbers)}:{_column_letters(max(column_numbers))}{max(row_numbers)}"


def _shared_strings(root: ElementTree.Element | None) -> list[str]:
    if root is None:
        return []
    values = []
    for item in root.findall(".//main:si", SHEET_NS):
        values.append("".join(node.text or "" for node in item.findall(".//main:t", SHEET_NS)).strip())
    return values


def _cell_value(cell: ElementTree.Element, shared_strings: list[str]) -> str:
    data_type = str(cell.get("t") or "")
    if data_type == "inlineStr":
        return "".join(node.text or "" for node in cell.findall(".//main:t", SHEET_NS)).strip()
    value = cell.find("./main:v", SHEET_NS)
    raw = (value.text or "").strip() if value is not None else ""
    if data_type == "s" and raw.isdigit():
        index = int(raw)
        return shared_strings[index] if index < len(shared_strings) else raw
    return raw


def _row_index(row_element: ElementTree.Element) -> int:
    row_ref = str(row_element.get("r") or "")
    return int(row_ref) if row_ref.isdigit() else 1


def _parse_cell_ref(cell_ref: str) -> tuple[int, int] | None:
    match = CELL_REF_RE.match(cell_ref)
    if match is None:
        return None
    column_letters, row_number = match.groups()
    return int(row_number), _column_number(column_letters)


def _column_number(column_letters: str) -> int:
    number = 0
    for char in column_letters.upper():
        number = number * 26 + (ord(char) - ord("A") + 1)
    return number


def _column_letters(column_number: int) -> str:
    letters = ""
    while column_number:
        column_number, remainder = divmod(column_number - 1, 26)
        letters = chr(ord("A") + remainder) + letters
    return letters or "A"


def _failed(tool: str, error: AgentPDFError) -> ToolResult:
    return ToolResult(
        job_id=_job_id(),
        status="failed",
        tool=tool,
        warnings=[error.message],
        error=error,
    )


def _job_id() -> str:
    return f"job_{uuid4().hex[:16]}"
