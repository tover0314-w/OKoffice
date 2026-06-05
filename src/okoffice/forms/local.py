from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from okoffice.artifacts.store import build_artifact
from okoffice.schemas.errors import OKofficeException
from okoffice.schemas.models import ToolResult, ValidationCheck, ValidationReport
from okoffice.security.paths import resolve_input_path, resolve_output_path
from okoffice.validation.pdf import validate_pdf


def create_form_pdf(output_path: str | Path, fields: list[dict[str, Any]]) -> ToolResult:
    tool = "pdf.forms.create"
    if not fields:
        raise OKofficeException("unsafe_input_rejected", "At least one form field is required.")
    output = resolve_output_path(output_path)
    document = canvas.Canvas(str(output), pagesize=letter)
    _width, height = letter
    y = height - 96
    created_fields = []
    for index, field in enumerate(fields, start=1):
        name = str(field.get("name") or f"field_{index}")
        label = str(field.get("label") or name)
        required = bool(field.get("required", False))
        x = float(field.get("x", 72))
        y = float(field.get("y", y))
        field_width = float(field.get("width", 240))
        field_height = float(field.get("height", 20))
        document.drawString(x, y + field_height + 4, label)
        document.acroForm.textfield(
            name=name,
            tooltip=label,
            x=x,
            y=y,
            width=field_width,
            height=field_height,
            value=str(field.get("value") or ""),
            borderWidth=1,
            forceBorder=True,
        )
        created_fields.append({"name": name, "label": label, "required": required})
        y -= 64
    document.save()
    artifact = build_artifact(output, source_tool=tool)
    validation = validate_pdf(output, expected_pages=1)
    return ToolResult(
        job_id=_job_id(),
        status="succeeded" if validation.status == "passed" else "failed",
        tool=tool,
        artifacts=[artifact],
        validation=validation,
        warnings=validation.warnings or [],
        usage={"output": str(output), "field_count": len(created_fields), "fields": created_fields},
        next_recommended_tools=["pdf.forms.validate", "pdf.forms.import_data"],
    )


def import_form_data_pdf(
    input_path: str | Path,
    data: dict[str, Any],
    output_path: str | Path,
) -> ToolResult:
    tool = "pdf.forms.import_data"
    source = resolve_input_path(input_path)
    reader = _reader(source)
    writer = PdfWriter()
    writer.clone_document_from_reader(reader)
    fields = reader.get_fields() or {}
    field_names = set(fields)
    applied = {}
    skipped = []
    for name, value in data.items():
        if name in field_names:
            applied[name] = "" if value is None else str(value)
        else:
            skipped.append(name)
    for page in writer.pages:
        writer.update_page_form_field_values(page, applied)
    try:
        writer.set_need_appearances_writer()
    except Exception:
        pass
    output = resolve_output_path(output_path)
    with output.open("wb") as handle:
        writer.write(handle)
    artifact = build_artifact(output, source_tool=tool)
    validation = validate_pdf(output, expected_pages=len(reader.pages))
    return ToolResult(
        job_id=_job_id(),
        status="succeeded" if validation.status == "passed" else "failed",
        tool=tool,
        artifacts=[artifact],
        validation=validation,
        warnings=([f"Unknown fields skipped: {', '.join(skipped)}"] if skipped else [])
        + (validation.warnings or []),
        usage={
            "input": str(source),
            "output": str(output),
            "applied_field_count": len(applied),
            "skipped_fields": skipped,
        },
        next_recommended_tools=["pdf.forms.validate", "pdf.forms.flatten"],
    )


def validate_form_pdf(
    input_path: str | Path,
    required_fields: list[str] | None = None,
) -> ToolResult:
    tool = "pdf.forms.validate"
    source = resolve_input_path(input_path)
    reader = _reader(source)
    fields = reader.get_fields() or {}
    values = {name: _field_value(field) for name, field in fields.items()}
    required = required_fields or []
    missing = [name for name in required if not values.get(name)]
    checks = [
        ValidationCheck(
            name="required_form_fields",
            status="passed" if not missing else "failed",
            details={"missing": missing, "required": required},
        )
    ]
    report = ValidationReport(
        status="passed" if not missing else "failed",
        checks=checks,
        page_count=len(reader.pages),
        warnings=[],
    )
    return ToolResult(
        job_id=_job_id(),
        status="succeeded" if report.status == "passed" else "failed",
        tool=tool,
        validation=report,
        warnings=report.warnings or [],
        usage={
            "input": str(source),
            "field_count": len(fields),
            "fields": [{"name": name, "value": value} for name, value in values.items()],
            "required_fields": required,
            "missing_required_fields": missing,
        },
        next_recommended_tools=["pdf.forms.import_data"] if missing else ["pdf.forms.flatten"],
    )


def _reader(path: Path) -> PdfReader:
    try:
        reader = PdfReader(path)
    except Exception as exc:
        raise OKofficeException("pdf_parse_failed", f"Unable to parse PDF: {path}") from exc
    if reader.is_encrypted:
        raise OKofficeException(
            "encrypted_pdf_requires_password",
            "Encrypted PDFs require authorized decryption before form operations.",
        )
    return reader


def _field_value(field: dict[str, Any]) -> str:
    value = field.get("/V") or field.get("V") or ""
    return str(value)


def _job_id() -> str:
    return f"job_{uuid4().hex[:16]}"
