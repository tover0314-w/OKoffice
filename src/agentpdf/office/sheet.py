from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from agentpdf.office.inspect import inspect_office_file
from agentpdf.office.ooxml import SHEET_NS, count_members, read_xml, sorted_members, zip_names
from agentpdf.schemas.models import AgentPDFError, ToolResult, ValidationCheck, ValidationReport


TOOL_NAME = "sheet.inspect.workbook"


def inspect_sheet_workbook(path: str | Path) -> ToolResult:
    preflight = inspect_office_file(path)
    if preflight.status == "failed":
        return _failed(preflight.error or AgentPDFError(code="unsupported_file_type", message="Sheet inspect failed."))
    if preflight.usage["format"]["detected_format"] != "xlsx":
        return _failed(
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
        tool=TOOL_NAME,
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


def _failed(error: AgentPDFError) -> ToolResult:
    return ToolResult(
        job_id=_job_id(),
        status="failed",
        tool=TOOL_NAME,
        warnings=[error.message],
        error=error,
    )


def _job_id() -> str:
    return f"job_{uuid4().hex[:16]}"
