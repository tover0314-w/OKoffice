"""Sheet extract tools for formulas, charts, named ranges, comments, and pivots."""
from __future__ import annotations

import re
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

from okoffice.office.inspect import inspect_office_file
from okoffice.office.ooxml import SHEET_NS, read_xml, sorted_members, zip_names
from okoffice.office.shared import failed_result, job_id
from okoffice.office.sheet import (
    RICH_SHEET_NS,
    _rich_charts,
    _rich_comments,
    _rich_formulas,
    _rich_locator,
    _rich_named_ranges,
    _rich_read_relationships,
    _rich_rels_part_for,
    _rich_text_content,
    _shared_strings,
    _sheet_names,
)
from okoffice.schemas.models import OKofficeError, ToolResult, ValidationCheck, ValidationReport

EXTRACT_FORMULAS_TOOL = "sheet.extract.formulas"
EXTRACT_CHARTS_TOOL = "sheet.extract.charts"
EXTRACT_NAMED_RANGES_TOOL = "sheet.extract.named_ranges"
EXTRACT_COMMENTS_TOOL = "sheet.extract.comments"
EXTRACT_PIVOTS_TOOL = "sheet.extract.pivots"
VOLATILE_FORMULA_RE = re.compile(r"\b(NOW|TODAY|RAND|RANDBETWEEN|OFFSET|INDIRECT)\s*\(", re.IGNORECASE)
EXTERNAL_FORMULA_REF_RE = re.compile(r"\[([^\]]+)\]([^'!]+)")


def _preflight(path: str | Path, tool: str) -> tuple[Path, Any] | ToolResult:
    preflight = inspect_office_file(Path(path))
    if preflight.status == "failed":
        return failed_result(
            tool,
            preflight.error or OKofficeError(code="unsupported_file_type", message="Preflight failed."),
        )
    if preflight.usage["format"]["detected_format"] != "xlsx":
        return failed_result(
            tool,
            OKofficeError(
                code="unsupported_file_type",
                message=f"{tool} requires an XLSX file.",
                details={"detected_format": preflight.usage["format"]["detected_format"]},
            ),
        )
    source_path = Path(preflight.usage["file"]["path"])
    workbook_root = read_xml(source_path, "xl/workbook.xml")
    if workbook_root is None:
        return failed_result(
            tool,
            OKofficeError(
                code="unsupported_file_type",
                message=f"{tool} requires xl/workbook.xml in the package.",
            ),
        )
    return source_path, preflight


# ---------------------------------------------------------------------------
# 1. extract_sheet_formulas
# ---------------------------------------------------------------------------

def extract_sheet_formulas(path: str | Path) -> ToolResult:
    result = _preflight(path, EXTRACT_FORMULAS_TOOL)
    if isinstance(result, ToolResult):
        return result
    source_path, preflight = result

    names = zip_names(source_path)
    workbook_root = read_xml(source_path, "xl/workbook.xml")
    sheet_names_list = _sheet_names(workbook_root)
    worksheet_members = sorted_members(names, prefix="xl/worksheets/sheet")
    shared_strings = _shared_strings(read_xml(source_path, "xl/sharedStrings.xml"))

    formulas: list[dict[str, Any]] = []
    for index, member in enumerate(worksheet_members, start=1):
        sheet_name = sheet_names_list[index - 1] if index <= len(sheet_names_list) else f"Sheet{index}"
        sheet_root = read_xml(source_path, member)
        if sheet_root is None:
            continue
        formulas.extend(_rich_formulas(sheet_root, sheet_name, shared_strings))

    external_ref_count = sum(1 for f in formulas if f.get("has_external_reference"))
    volatile_count = _count_volatile_formulas(formulas)

    return ToolResult(
        job_id=job_id(),
        status="succeeded",
        tool=EXTRACT_FORMULAS_TOOL,
        validation=ValidationReport(
            status="passed",
            checks=[
                ValidationCheck(name="format_is_xlsx", status="passed"),
                ValidationCheck(
                    name="formulas_extracted",
                    status="passed",
                    details={"formula_count": len(formulas), "sheet_count": len(worksheet_members)},
                ),
            ],
        ),
        usage={
            "summary": {
                "formula_count": len(formulas),
                "sheet_count": len(worksheet_members),
                "external_ref_count": external_ref_count,
                "volatile_count": volatile_count,
            },
            "formulas": formulas,
        },
        next_recommended_tools=["sheet.validate.formulas", "sheet.inspect.workbook"],
    )


def _count_volatile_formulas(formulas: list[dict[str, Any]]) -> int:
    count = 0
    for formula in formulas:
        text = formula.get("formula", "")
        if VOLATILE_FORMULA_RE.search(text):
            count += 1
    return count


# ---------------------------------------------------------------------------
# 2. extract_sheet_charts
# ---------------------------------------------------------------------------

def extract_sheet_charts(path: str | Path) -> ToolResult:
    result = _preflight(path, EXTRACT_CHARTS_TOOL)
    if isinstance(result, ToolResult):
        return result
    source_path, preflight = result

    names = zip_names(source_path)
    workbook_root = read_xml(source_path, "xl/workbook.xml")
    sheet_names_list = _sheet_names(workbook_root)
    worksheet_members = sorted_members(names, prefix="xl/worksheets/sheet")

    charts: list[dict[str, Any]] = []
    with zipfile.ZipFile(source_path) as archive:
        workbook_rels = _rich_read_relationships(
            archive, "xl/_rels/workbook.xml.rels", "xl/workbook.xml", names,
        )
        for index, member in enumerate(worksheet_members, start=1):
            sheet_name = sheet_names_list[index - 1] if index <= len(sheet_names_list) else f"Sheet{index}"
            sheet_rels = _rich_read_relationships(
                archive, _rich_rels_part_for(member), member, names,
            )
            charts.extend(_rich_charts(archive, sheet_name, sheet_rels, names))

    return ToolResult(
        job_id=job_id(),
        status="succeeded",
        tool=EXTRACT_CHARTS_TOOL,
        validation=ValidationReport(
            status="passed",
            checks=[
                ValidationCheck(name="format_is_xlsx", status="passed"),
                ValidationCheck(
                    name="charts_extracted",
                    status="passed",
                    details={"chart_count": len(charts)},
                ),
            ],
        ),
        usage={
            "summary": {"chart_count": len(charts)},
            "charts": charts,
        },
        next_recommended_tools=["sheet.inspect.workbook", "office.context.build_packet"],
    )


# ---------------------------------------------------------------------------
# 3. extract_sheet_named_ranges
# ---------------------------------------------------------------------------

def extract_sheet_named_ranges(path: str | Path) -> ToolResult:
    result = _preflight(path, EXTRACT_NAMED_RANGES_TOOL)
    if isinstance(result, ToolResult):
        return result
    source_path, preflight = result

    workbook_root = read_xml(source_path, "xl/workbook.xml")
    named_ranges = _rich_named_ranges(workbook_root)

    return ToolResult(
        job_id=job_id(),
        status="succeeded",
        tool=EXTRACT_NAMED_RANGES_TOOL,
        validation=ValidationReport(
            status="passed",
            checks=[
                ValidationCheck(name="format_is_xlsx", status="passed"),
                ValidationCheck(
                    name="named_ranges_extracted",
                    status="passed",
                    details={"named_range_count": len(named_ranges)},
                ),
            ],
        ),
        usage={
            "summary": {"named_range_count": len(named_ranges)},
            "named_ranges": named_ranges,
        },
        next_recommended_tools=["sheet.inspect.workbook", "office.context.build_packet"],
    )


# ---------------------------------------------------------------------------
# 4. extract_sheet_comments
# ---------------------------------------------------------------------------

def extract_sheet_comments(path: str | Path) -> ToolResult:
    result = _preflight(path, EXTRACT_COMMENTS_TOOL)
    if isinstance(result, ToolResult):
        return result
    source_path, preflight = result

    names = zip_names(source_path)
    workbook_root = read_xml(source_path, "xl/workbook.xml")
    sheet_names_list = _sheet_names(workbook_root)
    worksheet_members = sorted_members(names, prefix="xl/worksheets/sheet")

    comments: list[dict[str, Any]] = []
    with zipfile.ZipFile(source_path) as archive:
        for index, member in enumerate(worksheet_members, start=1):
            sheet_name = sheet_names_list[index - 1] if index <= len(sheet_names_list) else f"Sheet{index}"
            sheet_rels = _rich_read_relationships(
                archive, _rich_rels_part_for(member), member, names,
            )
            comments.extend(_rich_comments(archive, sheet_name, sheet_rels, names))

    return ToolResult(
        job_id=job_id(),
        status="succeeded",
        tool=EXTRACT_COMMENTS_TOOL,
        validation=ValidationReport(
            status="passed",
            checks=[
                ValidationCheck(name="format_is_xlsx", status="passed"),
                ValidationCheck(
                    name="comments_extracted",
                    status="passed",
                    details={"comment_count": len(comments)},
                ),
            ],
        ),
        usage={
            "summary": {"comment_count": len(comments)},
            "comments": comments,
        },
        next_recommended_tools=["sheet.inspect.workbook", "office.context.build_packet"],
    )


# ---------------------------------------------------------------------------
# 5. extract_sheet_pivots
# ---------------------------------------------------------------------------

def extract_sheet_pivots(path: str | Path) -> ToolResult:
    result = _preflight(path, EXTRACT_PIVOTS_TOOL)
    if isinstance(result, ToolResult):
        return result
    source_path, preflight = result

    pivots: list[dict[str, Any]] = []
    with zipfile.ZipFile(source_path) as archive:
        pivot_parts = sorted(
            name for name in archive.namelist()
            if name.replace("\\", "/").startswith("xl/pivotCache/pivotCacheDefinition")
        )
        for part in pivot_parts:
            pivot = _parse_pivot_cache(archive, part)
            if pivot is not None:
                pivots.append(pivot)

    return ToolResult(
        job_id=job_id(),
        status="succeeded",
        tool=EXTRACT_PIVOTS_TOOL,
        validation=ValidationReport(
            status="passed",
            checks=[
                ValidationCheck(name="format_is_xlsx", status="passed"),
                ValidationCheck(
                    name="pivots_extracted",
                    status="passed",
                    details={"pivot_cache_count": len(pivots)},
                ),
            ],
        ),
        usage={
            "summary": {"pivot_cache_count": len(pivots)},
            "pivots": pivots,
        },
        next_recommended_tools=["sheet.inspect.workbook", "office.context.build_packet"],
    )


def _parse_pivot_cache(archive: zipfile.ZipFile, part: str) -> dict[str, Any] | None:
    try:
        root = ElementTree.fromstring(archive.read(part))
    except (ElementTree.ParseError, KeyError):
        return None

    cache_id = root.attrib.get("cacheId") or root.attrib.get("r:id", "")
    source_data = _pivot_source_data(root)
    record_count = _pivot_record_count(root, archive, part)

    return {
        "cache_id": cache_id,
        "source_data": source_data,
        "record_count": record_count,
        "part": part.replace("\\", "/"),
        "locator": {"kind": "sheet", "pivot_cache": cache_id, "part": part.replace("\\", "/")},
    }


def _pivot_source_data(root: ElementTree.Element) -> str:
    source_element = root.find(f"{RICH_SHEET_NS}SourceData")
    if source_element is not None:
        return _rich_text_content(source_element) or source_element.attrib.get("ref", "")
    range_attr = root.attrib.get("Range") or root.attrib.get("range", "")
    if range_attr:
        return range_attr
    worksheet_source = root.find(f"{RICH_SHEET_NS}worksheetSource")
    if worksheet_source is not None:
        return worksheet_source.attrib.get("ref", "") or worksheet_source.attrib.get("name", "")
    return ""


def _pivot_record_count(root: ElementTree.Element, archive: zipfile.ZipFile, part: str) -> int:
    records_element = root.find(f"{RICH_SHEET_NS}cacheRecords")
    if records_element is not None:
        count_attr = records_element.attrib.get("count")
        if count_attr and count_attr.isdigit():
            return int(count_attr)
        return len(records_element.findall(f"{RICH_SHEET_NS}r"))

    records_part = part.replace("pivotCacheDefinition", "pivotCacheRecords")
    try:
        records_root = ElementTree.fromstring(archive.read(records_part))
        return len(records_root.findall(f"{RICH_SHEET_NS}r"))
    except (KeyError, ElementTree.ParseError):
        return 0
