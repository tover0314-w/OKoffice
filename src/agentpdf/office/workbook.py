from __future__ import annotations

import html
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from agentpdf.artifacts.store import build_artifact
from agentpdf.office.sheet import inspect_sheet_workbook
from agentpdf.schemas.errors import AgentPDFException
from agentpdf.schemas.models import AgentPDFError, ToolResult, ValidationCheck, ValidationReport
from agentpdf.security.paths import resolve_input_path, resolve_output_path


TOOL_NAME = "sheet.write.workbook"


class EvidenceField(BaseModel):
    name: str
    type: str = "string"
    aliases: list[str] = Field(default_factory=list)
    required: bool = False


class EvidenceRow(BaseModel):
    row_id: str
    values: dict[str, Any] = Field(default_factory=dict)
    field_evidence: dict[str, dict[str, Any]] = Field(default_factory=dict)


class EvidenceExtraction(BaseModel):
    extraction_id: str | None = None
    schema_name: str = "schema"
    fields: list[EvidenceField]
    rows: list[EvidenceRow] = Field(default_factory=list)
    source_refs: list[dict[str, Any]] = Field(default_factory=list)
    method: str | None = None


def write_sheet_workbook(
    *,
    evidence_path: str | Path | None = None,
    evidence: dict[str, Any] | None = None,
    output_path: str | Path,
) -> ToolResult:
    try:
        extraction, source_path = _load_evidence(evidence_path=evidence_path, evidence=evidence)
        output = resolve_output_path(output_path)
        if output.suffix.lower() != ".xlsx":
            raise AgentPDFException(
                "unsupported_file_type",
                "sheet.write.workbook writes .xlsx output files.",
                details={"output_path": output.as_posix()},
            )

        evidence_rows = _evidence_sheet_rows(extraction)
        source_map_rows = _source_map_rows(extraction)
        data_model_rows = _data_model_sheet_rows(extraction)
        chart_plan_rows = _chart_plan_sheet_rows(extraction)
        sheets = [
            _sheet_spec("Evidence", evidence_rows, "EvidenceTable"),
            _sheet_spec("SourceMap", source_map_rows, "SourceMapTable"),
            _sheet_spec("DataModel", data_model_rows, "DataModelTable"),
            _sheet_spec("Charts", chart_plan_rows, "ChartPlanTable"),
        ]
        _write_xlsx_package(output, sheets)
        inspected = inspect_sheet_workbook(output)
        if inspected.status != "succeeded":
            raise AgentPDFException(
                "output_validation_failed",
                "Generated evidence workbook could not be inspected.",
                details=inspected.error.model_dump(mode="json") if inspected.error else {},
            )

        artifacts = [build_artifact(output, source_tool=TOOL_NAME)]
        usage = _usage(extraction, output, source_path, sheets)
        return ToolResult(
            job_id=_job_id(),
            status="succeeded",
            tool=TOOL_NAME,
            artifacts=artifacts,
            validation=_validation_report(extraction, output, inspected, sheets),
            usage=usage,
            next_recommended_tools=[
                "sheet.inspect.workbook",
                "sheet.validation.formulas",
                "office.workflow.sheet_to_deck",
            ],
        )
    except AgentPDFException as exc:
        return _failed(exc.to_error())
    except (json.JSONDecodeError, ValueError) as exc:
        return _failed(AgentPDFError(code="invalid_input", message=str(exc)))


def _load_evidence(
    *,
    evidence_path: str | Path | None,
    evidence: dict[str, Any] | None,
) -> tuple[EvidenceExtraction, Path | None]:
    if evidence is None:
        if evidence_path is None:
            raise AgentPDFException("invalid_input", "evidence_path or evidence is required.")
        source = resolve_input_path(evidence_path)
        raw = json.loads(source.read_text(encoding="utf-8"))
    else:
        source = None
        raw = evidence
    if not isinstance(raw, dict):
        raise AgentPDFException("invalid_input", "Evidence JSON must be an object.")
    candidate = raw.get("usage", {}).get("extraction") if isinstance(raw.get("usage"), dict) else raw
    if not isinstance(candidate, dict):
        raise AgentPDFException("invalid_input", "Evidence JSON must include an extraction object.")
    extraction = EvidenceExtraction.model_validate(candidate)
    if not extraction.fields:
        raise AgentPDFException("invalid_input", "Evidence extraction must include at least one field.")
    return extraction, source


def _evidence_sheet_rows(extraction: EvidenceExtraction) -> list[list[str]]:
    headers = [field.name for field in extraction.fields]
    rows = [headers]
    for row in extraction.rows:
        rows.append([_cell_text(row.values.get(field.name)) for field in extraction.fields])
    return rows


def _source_map_rows(extraction: EvidenceExtraction) -> list[list[str]]:
    rows = [["field", "row_id", "source_ref", "source_type", "locator", "confidence", "excerpt"]]
    for row in extraction.rows:
        for field in extraction.fields:
            evidence = row.field_evidence.get(field.name, {})
            rows.append(
                [
                    field.name,
                    row.row_id,
                    _cell_text(evidence.get("source_ref")),
                    _cell_text(evidence.get("source_type")),
                    _json_cell(evidence.get("locator")),
                    _cell_text(evidence.get("confidence")),
                    _cell_text(evidence.get("excerpt")),
                ]
            )
    return rows


def _data_model_sheet_rows(extraction: EvidenceExtraction) -> list[list[str]]:
    rows = [["field", "type", "required", "aliases", "semantic_type", "source_ref_count"]]
    for field in extraction.fields:
        rows.append(
            [
                field.name,
                field.type,
                str(field.required).lower(),
                ", ".join(field.aliases),
                _semantic_type(field),
                str(_field_source_ref_count(extraction, field.name)),
            ]
        )
    return rows


def _chart_plan_sheet_rows(extraction: EvidenceExtraction) -> list[list[str]]:
    rows = [["chart_id", "chart_type", "title", "source_sheet", "source_range", "category_field", "series_field", "status"]]
    category_field = _first_field(extraction, semantic_types={"category", "string"})
    numeric_fields = [
        field for field in extraction.fields if _semantic_type(field) in {"number", "currency", "percentage"}
    ]
    for field in numeric_fields[:1]:
        rows.append(
            [
                f"{field.name}_by_{category_field.name if category_field else 'row'}",
                "bar",
                f"{_field_label(field.name)} by {_field_label(category_field.name) if category_field else 'row'}",
                "Evidence",
                "EvidenceTable",
                category_field.name if category_field else "",
                field.name,
                "planned",
            ]
        )
    risk_field = _field_by_name(extraction, "risk")
    if risk_field is not None:
        rows.append(
            [
                "risk_distribution",
                "column",
                "Risk distribution",
                "Evidence",
                "EvidenceTable",
                risk_field.name,
                "",
                "planned",
            ]
        )
    if len(rows) == 1:
        rows.append(
            [
                "evidence_rows",
                "table",
                "Evidence rows",
                "Evidence",
                "EvidenceTable",
                category_field.name if category_field else "",
                "",
                "planned",
            ]
        )
    return rows


def _sheet_spec(name: str, rows: list[list[str]], table_name: str) -> dict[str, Any]:
    column_count = max((len(row) for row in rows), default=1)
    normalized_rows = [row + [""] * (column_count - len(row)) for row in rows] or [[""]]
    row_count = len(normalized_rows)
    table_range = f"A1:{_xlsx_column(column_count)}{row_count}"
    return {
        "name": name,
        "rows": normalized_rows,
        "table_name": table_name,
        "range": table_range,
        "row_count": row_count,
        "column_count": column_count,
    }


def _write_xlsx_package(path: Path, sheets: list[dict[str, Any]]) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _content_types_xml(sheets))
        archive.writestr("_rels/.rels", _root_rels_xml())
        archive.writestr("docProps/core.xml", _core_props_xml())
        archive.writestr("docProps/app.xml", _app_props_xml(sheets))
        archive.writestr("xl/workbook.xml", _workbook_xml(sheets))
        archive.writestr("xl/_rels/workbook.xml.rels", _workbook_rels_xml(sheets))
        archive.writestr("xl/styles.xml", _styles_xml())
        for index, sheet in enumerate(sheets, start=1):
            archive.writestr(f"xl/worksheets/sheet{index}.xml", _worksheet_xml(sheet, index))
            archive.writestr(f"xl/worksheets/_rels/sheet{index}.xml.rels", _sheet_rels_xml(index))
            archive.writestr(f"xl/tables/table{index}.xml", _table_xml(sheet, index))


def _content_types_xml(sheets: list[dict[str, Any]]) -> str:
    table_overrides = "".join(
        f'<Override PartName="/xl/tables/table{index}.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.table+xml"/>'
        for index, _sheet in enumerate(sheets, start=1)
    )
    sheet_overrides = "".join(
        f'<Override PartName="/xl/worksheets/sheet{index}.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        for index, _sheet in enumerate(sheets, start=1)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/styles.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
        '<Override PartName="/docProps/core.xml" '
        'ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
        '<Override PartName="/docProps/app.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
        f"{sheet_overrides}{table_overrides}"
        "</Types>"
    )


def _root_rels_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/>'
        '<Relationship Id="rId2" '
        'Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" '
        'Target="docProps/core.xml"/>'
        '<Relationship Id="rId3" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" '
        'Target="docProps/app.xml"/>'
        "</Relationships>"
    )


def _core_props_xml() -> str:
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" '
        'xmlns:dcterms="http://purl.org/dc/terms/" '
        'xmlns:dcmitype="http://purl.org/dc/dcmitype/" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
        "<dc:title>okoffice evidence workbook</dc:title>"
        "<dc:creator>okoffice</dc:creator>"
        "<cp:lastModifiedBy>okoffice</cp:lastModifiedBy>"
        f'<dcterms:created xsi:type="dcterms:W3CDTF">{timestamp}</dcterms:created>'
        f'<dcterms:modified xsi:type="dcterms:W3CDTF">{timestamp}</dcterms:modified>'
        "</cp:coreProperties>"
    )


def _app_props_xml(sheets: list[dict[str, Any]]) -> str:
    sheet_names = "".join(f"<vt:lpstr>{_xml_text(sheet['name'])}</vt:lpstr>" for sheet in sheets)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" '
        'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
        "<Application>okoffice</Application>"
        f'<TitlesOfParts><vt:vector size="{len(sheets)}" baseType="lpstr">'
        f"{sheet_names}"
        "</vt:vector></TitlesOfParts>"
        "</Properties>"
    )


def _workbook_xml(sheets: list[dict[str, Any]]) -> str:
    sheet_nodes = "".join(
        f'<sheet name="{_xml_attr(sheet["name"])}" sheetId="{index}" r:id="rId{index}"/>'
        for index, sheet in enumerate(sheets, start=1)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f"<sheets>{sheet_nodes}</sheets>"
        '<calcPr calcMode="manual"/>'
        "</workbook>"
    )


def _workbook_rels_xml(sheets: list[dict[str, Any]]) -> str:
    sheet_relationships = "".join(
        f'<Relationship Id="rId{index}" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        f'Target="worksheets/sheet{index}.xml"/>'
        for index, _sheet in enumerate(sheets, start=1)
    )
    styles_id = len(sheets) + 1
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f"{sheet_relationships}"
        f'<Relationship Id="rId{styles_id}" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
        'Target="styles.xml"/>'
        "</Relationships>"
    )


def _styles_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts>'
        '<fills count="1"><fill><patternFill patternType="none"/></fill></fills>'
        '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
        '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
        '<cellXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/></cellXfs>'
        '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
        "</styleSheet>"
    )


def _worksheet_xml(sheet: dict[str, Any], index: int) -> str:
    rows_xml = []
    for row_index, row in enumerate(sheet["rows"], start=1):
        cells = []
        for column_index, value in enumerate(row, start=1):
            cell_ref = f"{_xlsx_column(column_index)}{row_index}"
            cells.append(f'<c r="{cell_ref}" t="inlineStr"><is><t>{_xml_text(value)}</t></is></c>')
        rows_xml.append(f'<row r="{row_index}">{"".join(cells)}</row>')
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<dimension ref="{sheet["range"]}"/>'
        f"<sheetData>{''.join(rows_xml)}</sheetData>"
        f'<tableParts count="1"><tablePart r:id="rIdTable{index}"/></tableParts>'
        "</worksheet>"
    )


def _sheet_rels_xml(index: int) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f'<Relationship Id="rIdTable{index}" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/table" '
        f'Target="../tables/table{index}.xml"/>'
        "</Relationships>"
    )


def _table_xml(sheet: dict[str, Any], index: int) -> str:
    columns = "".join(
        f'<tableColumn id="{column_index}" name="{_xml_attr(header)}"/>'
        for column_index, header in enumerate(sheet["rows"][0], start=1)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<table xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" id="{index}" '
        f'name="{_xml_attr(sheet["table_name"])}" displayName="{_xml_attr(sheet["table_name"])}" '
        f'ref="{sheet["range"]}" totalsRowShown="0">'
        f'<autoFilter ref="{sheet["range"]}"/>'
        f'<tableColumns count="{sheet["column_count"]}">{columns}</tableColumns>'
        '<tableStyleInfo name="TableStyleMedium2" showFirstColumn="0" showLastColumn="0" '
        'showRowStripes="1" showColumnStripes="0"/>'
        "</table>"
    )


def _usage(
    extraction: EvidenceExtraction,
    output: Path,
    source_path: Path | None,
    sheets: list[dict[str, Any]],
) -> dict[str, Any]:
    source_map_count = max(len(sheets[1]["rows"]) - 1, 0)
    data_model_rows = _rows_as_dicts(sheets[2]["rows"])
    chart_plan_rows = _rows_as_dicts(sheets[3]["rows"])
    return {
        "summary": {
            "row_count": len(extraction.rows),
            "field_count": len(extraction.fields),
            "sheet_count": len(sheets),
            "source_map_count": source_map_count,
            "data_model_count": len(data_model_rows),
            "chart_plan_count": len(chart_plan_rows),
        },
        "evidence": {
            "schema_name": extraction.schema_name,
            "extraction_id": extraction.extraction_id,
            "source_path": source_path.as_posix() if source_path else None,
            "method": extraction.method,
        },
        "sheets": [
            {
                "name": sheet["name"],
                "range": sheet["range"],
                "row_count": sheet["row_count"],
                "column_count": sheet["column_count"],
                "table": sheet["table_name"],
            }
            for sheet in sheets
        ],
        "data_model": {
            "field_count": len(data_model_rows),
            "fields": data_model_rows,
        },
        "chart_plan": chart_plan_rows,
        "workbook_manifest": {
            "output_path": output.as_posix(),
            "format": "xlsx",
            "mutates_inputs": False,
            "package_type": "ooxml_xlsx",
            "macro_enabled": False,
            "external_relationships": [],
        },
    }


def _validation_report(
    extraction: EvidenceExtraction,
    output: Path,
    inspected: ToolResult,
    sheets: list[dict[str, Any]],
) -> ValidationReport:
    return ValidationReport(
        status="passed",
        checks=[
            ValidationCheck(
                name="evidence_rows_loaded",
                status="passed",
                details={"row_count": len(extraction.rows), "field_count": len(extraction.fields)},
            ),
            ValidationCheck(
                name="workbook_written",
                status="passed",
                details={"output_path": output.as_posix(), "sheet_count": len(sheets)},
            ),
            ValidationCheck(
                name="source_map_written",
                status="passed",
                details={"source_map_rows": max(len(sheets[1]["rows"]) - 1, 0)},
            ),
            ValidationCheck(
                name="data_model_written",
                status="passed",
                details={"field_count": max(len(sheets[2]["rows"]) - 1, 0), "table": sheets[2]["table_name"]},
            ),
            ValidationCheck(
                name="chart_plan_written",
                status="passed",
                details={"chart_plan_count": max(len(sheets[3]["rows"]) - 1, 0), "table": sheets[3]["table_name"]},
            ),
            ValidationCheck(
                name="workbook_reopened_by_inspect",
                status="passed",
                details=inspected.usage.get("summary", {}),
            ),
        ],
    )


def _cell_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _semantic_type(field: EvidenceField) -> str:
    raw_type = field.type.lower().strip()
    name = field.name.lower()
    if raw_type in {"number", "integer", "float", "decimal"}:
        return "number"
    if raw_type in {"currency", "money"} or "amount" in name or "cost" in name or "revenue" in name:
        return "currency"
    if raw_type in {"percent", "percentage"} or "rate" in name:
        return "percentage"
    if raw_type in {"date", "datetime"} or "date" in name:
        return "date"
    if name in {"vendor", "customer", "company", "risk", "category", "status"}:
        return "category"
    return raw_type or "string"


def _field_source_ref_count(extraction: EvidenceExtraction, field_name: str) -> int:
    values = []
    for row in extraction.rows:
        source_ref = row.field_evidence.get(field_name, {}).get("source_ref")
        if source_ref:
            values.append(str(source_ref))
    return len(set(values))


def _first_field(extraction: EvidenceExtraction, *, semantic_types: set[str]) -> EvidenceField | None:
    for field in extraction.fields:
        if _semantic_type(field) in semantic_types:
            return field
    return extraction.fields[0] if extraction.fields else None


def _field_by_name(extraction: EvidenceExtraction, name: str) -> EvidenceField | None:
    for field in extraction.fields:
        if field.name.lower() == name.lower():
            return field
    return None


def _field_label(field: str) -> str:
    return field.replace("_", " ").capitalize()


def _rows_as_dicts(rows: list[list[str]]) -> list[dict[str, str]]:
    if not rows:
        return []
    headers = [str(header) for header in rows[0]]
    records = []
    for row in rows[1:]:
        records.append({header: row[index] if index < len(row) else "" for index, header in enumerate(headers) if header})
    return records


def _json_cell(value: Any) -> str:
    if value is None or value == "":
        return ""
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _xml_text(value: Any) -> str:
    return html.escape(_cell_text(value), quote=False)


def _xml_attr(value: Any) -> str:
    return html.escape(_cell_text(value), quote=True)


def _xlsx_column(index: int) -> str:
    name = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name or "A"


def _failed(error: AgentPDFError) -> ToolResult:
    return ToolResult(
        job_id=_job_id(),
        status="failed",
        tool=TOOL_NAME,
        error=error,
        warnings=[error.message],
    )


def _job_id() -> str:
    return f"job_{uuid4().hex[:16]}"
