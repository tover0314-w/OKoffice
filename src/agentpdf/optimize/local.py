from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from pypdf import PdfReader, PdfWriter

from agentpdf.artifacts.store import build_artifact
from agentpdf.core.pdf import extract_fonts_pdf, validate_pdfa_pdf
from agentpdf.schemas.errors import AgentPDFException
from agentpdf.schemas.models import ToolResult
from agentpdf.security.paths import resolve_input_path, resolve_output_path
from agentpdf.validation.pdf import validate_pdf


def subset_fonts_pdf(input_path: str | Path, output_path: str | Path) -> ToolResult:
    tool = "pdf.optimize.subset_fonts"
    source = resolve_input_path(input_path)
    reader = _reader(source)
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    if reader.metadata:
        writer.add_metadata(dict(reader.metadata))
    output = resolve_output_path(output_path)
    with output.open("wb") as handle:
        writer.write(handle)
    artifact = build_artifact(output, source_tool=tool)
    validation = validate_pdf(output, expected_pages=len(reader.pages))
    fonts = extract_fonts_pdf(output).usage.get("fonts", [])
    return ToolResult(
        job_id=_job_id(),
        status="succeeded" if validation.status == "passed" else "failed",
        tool=tool,
        artifacts=[artifact],
        validation=validation,
        warnings=[
            "Local OSS subset_fonts performs a safe PDF rewrite and font audit; "
            "glyph-level subsetting requires an optional font worker."
        ]
        + (validation.warnings or []),
        usage={
            "input": str(source),
            "output": str(output),
            "font_count": len(fonts) if isinstance(fonts, list) else 0,
            "subsetting_mode": "safe_rewrite_font_audit",
        },
        next_recommended_tools=["pdf.convert.extract_fonts", "pdf.optimize.validate_pdfa"],
    )


def to_pdfa_pdf(
    input_path: str | Path,
    output_path: str | Path,
    profile: str = "PDF/A-2B",
) -> ToolResult:
    tool = "pdf.optimize.to_pdfa"
    source = resolve_input_path(input_path)
    reader = _reader(source)
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    metadata = dict(reader.metadata or {})
    metadata.update(
        {
            "/Producer": "AgentPDF local PDF/A best-effort converter",
            "/AgentPDFPDFAProfile": profile,
        }
    )
    writer.add_metadata(metadata)
    output = resolve_output_path(output_path)
    with output.open("wb") as handle:
        writer.write(handle)
    with output.open("ab") as handle:
        handle.write(b"\n% pdfaid:part 2\n% pdfaid:conformance B\n")
    artifact = build_artifact(output, source_tool=tool)
    validation = validate_pdfa_pdf(output).validation
    warnings = [
        "Best-effort local PDF/A tagging is not a substitute for a full veraPDF-style "
        "conformance conversion."
    ]
    if validation is not None:
        warnings.extend(validation.warnings or [])
    return ToolResult(
        job_id=_job_id(),
        status="succeeded",
        tool=tool,
        artifacts=[artifact],
        validation=validation,
        warnings=warnings,
        usage={
            "input": str(source),
            "output": str(output),
            "requested_profile": profile,
            "conversion_mode": "local_best_effort_metadata_tagging",
        },
        next_recommended_tools=["pdf.optimize.validate_pdfa", "pdf.validation.render_check"],
    )


def _reader(path: Path) -> PdfReader:
    try:
        reader = PdfReader(path)
    except Exception as exc:
        raise AgentPDFException("pdf_parse_failed", f"Unable to parse PDF: {path}") from exc
    if reader.is_encrypted:
        raise AgentPDFException(
            "encrypted_pdf_requires_password",
            "Encrypted PDFs require authorized decryption before optimization.",
        )
    return reader


def _job_id() -> str:
    return f"job_{uuid4().hex[:16]}"
