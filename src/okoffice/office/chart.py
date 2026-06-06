from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from okoffice.office.shared import failed_result, job_id
from okoffice.schemas.models import OKofficeError, ToolResult, ValidationCheck, ValidationReport
from okoffice.security.paths import resolve_input_path, resolve_output_path

TOOL_NAME = "sheet.visualize.chart"
VALID_TYPES = {"bar", "line", "pie", "area", "scatter"}
_RANGE_RE = re.compile(r"^(?:'[^']+'!)?[A-Za-z]+\d+(?::[A-Za-z]+\d+)?$", re.IGNORECASE)


def create_chart(
    input_path: str | Path,
    output_path: str | Path,
    sheet: str | None = None,
    chart_type: str = "bar",
    data_range: str | None = None,
    title: str | None = None,
    categories_range: str | None = None,
    series_ranges: list[str] | None = None,
) -> ToolResult:
    try:
        if chart_type not in VALID_TYPES:
            return failed_result(
                TOOL_NAME,
                OKofficeError(
                    code="invalid_chart_type",
                    message=f"chart_type must be one of {sorted(VALID_TYPES)}, got '{chart_type}'",
                ),
            )

        if not series_ranges and not data_range:
            return failed_result(
                TOOL_NAME,
                OKofficeError(
                    code="missing_data_range",
                    message="At least one of series_ranges or data_range is required to create a chart.",
                ),
            )

        for label, val in (("data_range", data_range), ("categories_range", categories_range)):
            if val and not _RANGE_RE.match(val):
                return failed_result(
                    TOOL_NAME,
                    OKofficeError(code="invalid_range", message=f"Invalid {label}: '{val}'. Expected format like 'A1:B10' or 'Sheet1!A1:B10'."),
                )
        for i, sr in enumerate(series_ranges or []):
            if not _RANGE_RE.match(sr):
                return failed_result(
                    TOOL_NAME,
                    OKofficeError(code="invalid_range", message=f"Invalid series_ranges[{i}]: '{sr}'. Expected format like 'A1:B10' or 'Sheet1!A1:B10'."),
                )

        src = resolve_input_path(input_path)
        dest = resolve_output_path(output_path)
        dest.parent.mkdir(parents=True, exist_ok=True)

        try:
            from openpyxl import load_workbook
            from openpyxl.chart import (
                AreaChart,
                BarChart,
                LineChart,
                PieChart,
                Reference,
                ScatterChart,
            )
        except ImportError:
            return failed_result(
                TOOL_NAME,
                OKofficeError(
                    code="dependency_missing",
                    message="openpyxl is required for chart creation. Install with: pip install openpyxl",
                ),
            )

        wb = load_workbook(src.as_posix())
        ws = wb[sheet] if sheet else wb.active

        chart = _build_chart(chart_type, title)

        if series_ranges:
            for sr in series_ranges:
                values = Reference(ws, range_string=sr)
                chart.add_data(values, titles_from_data=True)
        elif data_range:
            values = Reference(ws, range_string=data_range)
            chart.add_data(values, titles_from_data=True)

        if categories_range:
            cats = Reference(ws, range_string=categories_range)
            chart.set_categories(cats)

        ws.add_chart(chart, "K1")
        wb.save(dest.as_posix())

        checks = [
            ValidationCheck(name="chart_created", status="passed", details={"chart_type": chart_type}),
            ValidationCheck(name="output_written", status="passed", details={"path": dest.as_posix()}),
        ]
        return ToolResult(
            job_id=job_id(),
            status="succeeded",
            tool=TOOL_NAME,
            validation=ValidationReport(status="passed", checks=checks),
            usage={"chart_type": chart_type, "sheet": sheet or ws.title, "title": title or ""},
            next_recommended_tools=["sheet.inspect.workbook", "sheet.extract.charts"],
        )
    except Exception as exc:
        return failed_result(TOOL_NAME, OKofficeError(code="chart_creation_failed", message=str(exc)))


def _build_chart(chart_type: str, title: str | None) -> Any:
    from openpyxl.chart import AreaChart, BarChart, LineChart, PieChart, ScatterChart

    chart_map = {
        "bar": BarChart,
        "line": LineChart,
        "pie": PieChart,
        "area": AreaChart,
        "scatter": ScatterChart,
    }
    chart_cls = chart_map[chart_type]
    chart = chart_cls()
    if title:
        chart.title = title
    chart.style = 10
    return chart
