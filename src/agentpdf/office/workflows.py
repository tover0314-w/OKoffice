from __future__ import annotations

import html
from pathlib import Path
from typing import Any
from uuid import uuid4

from agentpdf.office.context import build_office_context_packet
from agentpdf.office.bundle import export_office_bundle, verify_office_bundle
from agentpdf.office.deck import inspect_deck_presentation
from agentpdf.office.deck_validation import validate_deck_contact_sheet, validate_deck_presentation
from agentpdf.office.deck_writer import create_deck_presentation
from agentpdf.office.extract import extract_schema_from_context
from agentpdf.office.sheet import inspect_sheet_workbook
from agentpdf.office.validation import validate_sheet_formulas
from agentpdf.office.workbook import write_sheet_workbook
from agentpdf.office.word_report import create_word_report
from agentpdf.schemas.models import AgentPDFError, Artifact, ToolResult, ValidationCheck, ValidationReport
from agentpdf.security.paths import resolve_output_path
from agentpdf.workflows.createpdf import createpdf_html_first


DOCSET_TO_SHEET_TOOL = "office.workflow.docset_to_sheet"
SHEET_TO_DECK_TOOL = "office.workflow.sheet_to_deck"
BOARD_PACK_TOOL = "office.workflow.board_pack"


def docset_to_sheet(
    *,
    files: list[str | Path | dict[str, Any]],
    schema: dict[str, Any] | str | Path,
    output_path: str | Path,
    title: str | None = None,
    intent: str | None = None,
    context_output_path: str | Path | None = None,
    evidence_output_path: str | Path | None = None,
) -> ToolResult:
    output = resolve_output_path(output_path)
    context_path = resolve_output_path(context_output_path or output.with_suffix(".context.json"))
    evidence_path = resolve_output_path(evidence_output_path or output.with_suffix(".evidence.json"))

    context_result = build_office_context_packet(
        files=files,
        output_path=context_path,
        title=title or "OKoffice Docset To Sheet Context",
        intent=intent or "Build an evidence-backed workbook from source documents.",
    )
    if context_result.status != "succeeded":
        return _failed_from_step(DOCSET_TO_SHEET_TOOL, context_result, [context_result])

    extract_result = extract_schema_from_context(
        context_packet=context_result.usage["context_packet"],
        schema=schema,
        output_path=evidence_path,
    )
    if extract_result.status != "succeeded":
        return _failed_from_step(DOCSET_TO_SHEET_TOOL, extract_result, [context_result, extract_result])

    workbook_result = write_sheet_workbook(evidence_path=evidence_path, output_path=output)
    if workbook_result.status != "succeeded":
        return _failed_from_step(DOCSET_TO_SHEET_TOOL, workbook_result, [context_result, extract_result, workbook_result])

    validation_result = validate_sheet_formulas(output)
    if validation_result.status != "succeeded":
        return _failed_from_step(
            DOCSET_TO_SHEET_TOOL,
            validation_result,
            [context_result, extract_result, workbook_result, validation_result],
        )

    step_results = [context_result, extract_result, workbook_result, validation_result]
    warnings = _dedupe([warning for result in step_results for warning in result.warnings])
    artifacts = _dedupe_artifacts([artifact for result in step_results for artifact in result.artifacts])
    validation = _validation_report(step_results, warnings)
    extraction_summary = extract_result.usage.get("summary", {})
    return ToolResult(
        job_id=_job_id(),
        status="succeeded",
        tool=DOCSET_TO_SHEET_TOOL,
        artifacts=artifacts,
        validation=validation,
        warnings=warnings,
        usage={
            "summary": {
                "file_count": len(files),
                "field_count": int(extraction_summary.get("field_count", 0)),
                "row_count": int(extraction_summary.get("row_count", 0)),
                "filled_value_count": int(extraction_summary.get("filled_value_count", 0)),
                "artifact_count": len(artifacts),
                "workbook_validation_status": validation_result.validation.status if validation_result.validation else "skipped",
            },
            "workflow": {
                "workflow_id": f"docset_to_sheet_{uuid4().hex[:16]}",
                "output_path": output.as_posix(),
                "sidecars": {
                    "context_packet_path": context_path.as_posix(),
                    "evidence_path": evidence_path.as_posix(),
                },
                "mutates_inputs": False,
            },
            "steps": [_step_summary(result) for result in step_results],
            "context_packet": {
                "context_packet_id": context_result.usage.get("context_packet_id"),
                "item_count": context_result.usage.get("item_count"),
                "domains": context_result.usage.get("domains", []),
            },
            "extraction": extract_result.usage.get("extraction", {}),
            "workbook": workbook_result.usage,
            "workbook_validation": validation_result.model_dump(mode="json"),
        },
        next_recommended_tools=["sheet.inspect.workbook", "office.workflow.sheet_to_deck", "office.bundle.export"],
    )


def sheet_to_deck(
    *,
    workbook_path: str | Path,
    output_path: str | Path,
    title: str | None = None,
    profile: str = "board_review",
) -> ToolResult:
    output = resolve_output_path(output_path)

    workbook_result = inspect_sheet_workbook(workbook_path)
    if workbook_result.status != "succeeded":
        return _failed_from_step(SHEET_TO_DECK_TOOL, workbook_result, [workbook_result])

    formula_result = validate_sheet_formulas(workbook_path)
    if formula_result.status != "succeeded":
        return _failed_from_step(SHEET_TO_DECK_TOOL, formula_result, [workbook_result, formula_result])

    deck_result = create_deck_presentation(
        workbook_path=workbook_path,
        output_path=output,
        title=title,
        profile=profile,
    )
    if deck_result.status != "succeeded":
        return _failed_from_step(SHEET_TO_DECK_TOOL, deck_result, [workbook_result, formula_result, deck_result])

    deck_inspection_result = inspect_deck_presentation(output)
    if deck_inspection_result.status != "succeeded":
        return _failed_from_step(
            SHEET_TO_DECK_TOOL,
            deck_inspection_result,
            [workbook_result, formula_result, deck_result, deck_inspection_result],
        )

    deck_validation_result = validate_deck_presentation(output)
    if deck_validation_result.status != "succeeded":
        return _failed_from_step(
            SHEET_TO_DECK_TOOL,
            deck_validation_result,
            [workbook_result, formula_result, deck_result, deck_inspection_result, deck_validation_result],
        )

    contact_sheet_result = validate_deck_contact_sheet(output)
    if contact_sheet_result.status != "succeeded":
        return _failed_from_step(
            SHEET_TO_DECK_TOOL,
            contact_sheet_result,
            [
                workbook_result,
                formula_result,
                deck_result,
                deck_inspection_result,
                deck_validation_result,
                contact_sheet_result,
            ],
        )

    step_results = [
        workbook_result,
        formula_result,
        deck_result,
        deck_inspection_result,
        deck_validation_result,
        contact_sheet_result,
    ]
    warnings = _dedupe([warning for result in step_results for warning in result.warnings])
    artifacts = _dedupe_artifacts([artifact for result in step_results for artifact in result.artifacts])
    deck_summary = deck_result.usage.get("summary", {})
    workbook_summary = workbook_result.usage.get("summary", {})
    deck_inspection_status = deck_inspection_result.validation.status if deck_inspection_result.validation else "skipped"
    deck_validation_status = deck_validation_result.validation.status if deck_validation_result.validation else "skipped"
    contact_sheet_status = contact_sheet_result.validation.status if contact_sheet_result.validation else "skipped"
    return ToolResult(
        job_id=_job_id(),
        status="succeeded",
        tool=SHEET_TO_DECK_TOOL,
        artifacts=artifacts,
        validation=_validation_report(step_results, warnings),
        warnings=warnings,
        usage={
            "summary": {
                "sheet_count": int(workbook_summary.get("sheet_count", 0)),
                "source_row_count": int(deck_summary.get("row_count", 0)),
                "slide_count": int(deck_summary.get("slide_count", 0)),
                "source_ref_count": int(deck_summary.get("source_ref_count", 0)),
                "deck_inspection_status": deck_inspection_status,
                "deck_validation_status": deck_validation_status,
                "contact_sheet_status": contact_sheet_status,
            },
            "workflow": {
                "workflow_id": f"sheet_to_deck_{uuid4().hex[:16]}",
                "output_path": output.as_posix(),
                "profile": profile,
                "mutates_inputs": False,
            },
            "steps": [_step_summary(result) for result in step_results],
            "workbook": workbook_result.usage,
            "formula_validation": formula_result.model_dump(mode="json"),
            "deck": deck_result.usage,
            "deck_inspection": deck_inspection_result.model_dump(mode="json"),
            "deck_validation": deck_validation_result.model_dump(mode="json"),
            "contact_sheet_validation": contact_sheet_result.model_dump(mode="json"),
        },
        next_recommended_tools=["deck.inspect.presentation", "office.bundle.export", "office.workflow.board_pack"],
    )


def board_pack(
    *,
    files: list[str | Path | dict[str, Any]],
    schema: dict[str, Any] | str | Path,
    out_dir: str | Path,
    title: str | None = None,
    profile: str = "board_review",
    intent: str | None = None,
    include_pdf_handout: bool = False,
    pdf_renderer_backend: str = "auto",
) -> ToolResult:
    output_dir = _resolve_output_dir(out_dir)
    workflow_title = title or "OKoffice Board Pack"
    workbook_path = output_dir / "evidence.xlsx"
    memo_path = output_dir / "memo.docx"
    deck_path = output_dir / "board-deck.pptx"
    handout_html_path = output_dir / "handout.html"
    handout_pdf_path = output_dir / "handout.pdf"
    bundle_path = output_dir / "board-pack.okoffice.zip"

    workbook_result = docset_to_sheet(
        files=files,
        schema=schema,
        output_path=workbook_path,
        title=f"{workflow_title} Context",
        intent=intent or "Build board-pack evidence workbook from source documents.",
        context_output_path=output_dir / "evidence.context.json",
        evidence_output_path=output_dir / "evidence.evidence.json",
    )
    if workbook_result.status != "succeeded":
        return _failed_from_step(BOARD_PACK_TOOL, workbook_result, [workbook_result])

    memo_result = create_word_report(
        workbook_path=workbook_path,
        output_path=memo_path,
        title=f"{workflow_title} Memo",
        profile="executive_memo",
    )
    if memo_result.status != "succeeded":
        return _failed_from_step(BOARD_PACK_TOOL, memo_result, [workbook_result, memo_result])

    deck_result = sheet_to_deck(
        workbook_path=workbook_path,
        output_path=deck_path,
        title=workflow_title,
        profile=profile,
    )
    if deck_result.status != "succeeded":
        return _failed_from_step(BOARD_PACK_TOOL, deck_result, [workbook_result, memo_result, deck_result])

    pdf_handout_result: ToolResult | None = None
    if include_pdf_handout:
        pdf_handout_result = createpdf_html_first(
            html=_board_pack_handout_html(
                title=workflow_title,
                workbook_result=workbook_result,
                memo_result=memo_result,
                deck_result=deck_result,
            ),
            html_output_path=handout_html_path,
            pdf_output_path=handout_pdf_path,
            title=f"{workflow_title} Handout",
            artifact_dir=output_dir,
            renderer_backend=pdf_renderer_backend,
        )
        if pdf_handout_result.status != "succeeded":
            return _failed_from_step(
                BOARD_PACK_TOOL,
                pdf_handout_result,
                [workbook_result, memo_result, deck_result, pdf_handout_result],
            )

    bundle_inputs = _dedupe_paths(
        [
            artifact.path
            for artifact in [
                *workbook_result.artifacts,
                *memo_result.artifacts,
                *deck_result.artifacts,
                *((pdf_handout_result.artifacts if pdf_handout_result is not None else [])),
            ]
        ]
    )
    bundle_result = export_office_bundle(
        artifact_paths=bundle_inputs,
        output_path=bundle_path,
        title=workflow_title,
        metadata={"workflow": "office.workflow.board_pack", "profile": profile},
    )
    if bundle_result.status != "succeeded":
        return _failed_from_step(
            BOARD_PACK_TOOL,
            bundle_result,
            _compact_results([workbook_result, memo_result, deck_result, pdf_handout_result, bundle_result]),
        )

    bundle_verify_result = verify_office_bundle(bundle_path)
    if bundle_verify_result.status != "succeeded":
        return _failed_from_step(
            BOARD_PACK_TOOL,
            bundle_verify_result,
            _compact_results(
                [workbook_result, memo_result, deck_result, pdf_handout_result, bundle_result, bundle_verify_result]
            ),
        )

    step_results = _compact_results([workbook_result, memo_result, deck_result, pdf_handout_result, bundle_result, bundle_verify_result])
    warnings = _dedupe([warning for result in step_results for warning in result.warnings])
    artifacts = _dedupe_artifacts([artifact for result in step_results for artifact in result.artifacts])
    workbook_summary = workbook_result.usage.get("summary", {})
    memo_summary = memo_result.usage.get("summary", {})
    deck_summary = deck_result.usage.get("summary", {})
    bundle_validation_status = bundle_verify_result.validation.status if bundle_verify_result.validation else "skipped"
    summary = {
        "file_count": len(files),
        "artifact_count": len(artifacts),
        "workbook_rows": int(workbook_summary.get("row_count", 0)),
        "memo_paragraphs": int(memo_summary.get("paragraph_count", 0)),
        "deck_slides": int(deck_summary.get("slide_count", 0)),
        "bundle_validation_status": bundle_validation_status,
        "contact_sheet_status": str(deck_summary.get("contact_sheet_status", "skipped")),
    }
    paths = {
        "workbook": workbook_path.as_posix(),
        "memo": memo_path.as_posix(),
        "deck": deck_path.as_posix(),
        "bundle": bundle_path.as_posix(),
    }
    if pdf_handout_result is not None:
        summary["pdf_handout_status"] = pdf_handout_result.validation.status if pdf_handout_result.validation else "skipped"
        paths.update(
            {
                "handout_html": handout_html_path.resolve().as_posix(),
                "handout_pdf": handout_pdf_path.resolve().as_posix(),
                "handout_qa": (output_dir / "handout.qa.json").resolve().as_posix(),
                "handout_artifact_manifest": (output_dir / "handout.artifact-manifest.json").resolve().as_posix(),
                "handout_artifact_graph": (output_dir / "handout.artifact-graph.json").resolve().as_posix(),
            }
        )
    return ToolResult(
        job_id=_job_id(),
        status="succeeded",
        tool=BOARD_PACK_TOOL,
        artifacts=artifacts,
        validation=_validation_report(step_results, warnings),
        warnings=warnings,
        usage={
            "summary": summary,
            "workflow": {
                "workflow_id": f"board_pack_{uuid4().hex[:16]}",
                "out_dir": output_dir.as_posix(),
                "profile": profile,
                "mutates_inputs": False,
                "include_pdf_handout": include_pdf_handout,
                "pdf_renderer_backend": pdf_renderer_backend,
                "paths": paths,
            },
            "steps": [_step_summary(result) for result in step_results],
            "workbook": workbook_result.usage,
            "memo": memo_result.usage,
            "deck": deck_result.usage,
            **({"pdf_handout": pdf_handout_result.usage} if pdf_handout_result is not None else {}),
            "bundle": bundle_result.usage,
            "bundle_verification": bundle_verify_result.usage,
        },
        next_recommended_tools=["office.bundle.verify", "office.bundle.export"],
    )


def _validation_report(step_results: list[ToolResult], warnings: list[str]) -> ValidationReport:
    checks = []
    for result in step_results:
        status = result.validation.status if result.validation is not None else "skipped"
        checks.append(
            ValidationCheck(
                name=result.tool.replace(".", "_"),
                status=status,
                details={"job_id": result.job_id, "artifact_count": len(result.artifacts)},
            )
        )
    report_status = "warning" if warnings or any(check.status == "warning" for check in checks) else "passed"
    return ValidationReport(status=report_status, checks=checks, warnings=warnings)


def _board_pack_handout_html(
    *,
    title: str,
    workbook_result: ToolResult,
    memo_result: ToolResult,
    deck_result: ToolResult,
) -> str:
    workbook_summary = workbook_result.usage.get("summary", {})
    memo_summary = memo_result.usage.get("summary", {})
    deck_summary = deck_result.usage.get("summary", {})
    extraction = workbook_result.usage.get("extraction", {})
    rows = extraction.get("rows", []) if isinstance(extraction, dict) else []
    first_row = rows[0] if rows and isinstance(rows[0], dict) else {}
    values = first_row.get("values", {}) if isinstance(first_row.get("values", {}), dict) else {}
    field_rows = "\n".join(
        f"<tr><th>{html.escape(str(key))}</th><td>{html.escape(str(value))}</td></tr>"
        for key, value in sorted(values.items())
    )
    if not field_rows:
        field_rows = '<tr><td colspan="2">No extracted field values were available.</td></tr>'
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{html.escape(title)} Handout</title>
  <style>
    body {{ font-family: Arial, sans-serif; color: #172033; margin: 40px; line-height: 1.45; }}
    h1 {{ font-size: 28px; margin: 0 0 12px; }}
    h2 {{ font-size: 18px; margin-top: 28px; border-bottom: 1px solid #d8dee9; padding-bottom: 6px; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 12px; }}
    th, td {{ border: 1px solid #d8dee9; padding: 8px 10px; text-align: left; vertical-align: top; }}
    th {{ width: 32%; background: #f5f7fb; }}
    .meta {{ color: #4c5870; }}
  </style>
</head>
<body>
  <h1>{html.escape(title)} Handout</h1>
  <p class="meta">Generated locally by okoffice from the validated board-pack workflow.</p>
  <h2>Workflow Summary</h2>
  <table>
    <tr><th>Evidence rows</th><td>{html.escape(str(workbook_summary.get("row_count", 0)))}</td></tr>
    <tr><th>Memo paragraphs</th><td>{html.escape(str(memo_summary.get("paragraph_count", 0)))}</td></tr>
    <tr><th>Deck slides</th><td>{html.escape(str(deck_summary.get("slide_count", 0)))}</td></tr>
    <tr><th>Contact-sheet validation</th><td>{html.escape(str(deck_summary.get("contact_sheet_status", "skipped")))}</td></tr>
  </table>
  <h2>Extracted Evidence</h2>
  <table>
    {field_rows}
  </table>
</body>
</html>
"""


def _step_summary(result: ToolResult) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "tool": result.tool,
        "status": result.status,
        "job_id": result.job_id,
        "warnings": result.warnings,
        "artifact_ids": [artifact.artifact_id for artifact in result.artifacts],
        "next_recommended_tools": result.next_recommended_tools,
    }
    if result.validation is not None:
        summary["validation"] = result.validation.model_dump(mode="json")
    if result.error is not None:
        summary["error"] = result.error.model_dump(mode="json")
    return summary


def _failed_from_step(tool_name: str, result: ToolResult, step_results: list[ToolResult]) -> ToolResult:
    error = result.error or AgentPDFError(
        code="output_validation_failed",
        message=f"Workflow step failed: {result.tool}",
    )
    return ToolResult(
        job_id=_job_id(),
        status="failed",
        tool=tool_name,
        artifacts=_dedupe_artifacts([artifact for step in step_results for artifact in step.artifacts]),
        validation=ValidationReport(
            status="failed",
            checks=[
                ValidationCheck(
                    name=step.tool.replace(".", "_"),
                    status="failed" if step is result else "passed",
                    details={"job_id": step.job_id},
                )
                for step in step_results
            ],
            warnings=[warning for step in step_results for warning in step.warnings],
        ),
        warnings=[warning for step in step_results for warning in step.warnings] or [error.message],
        usage={"steps": [_step_summary(step) for step in step_results]},
        error=error,
    )


def _dedupe(values: list[str]) -> list[str]:
    deduped: list[str] = []
    for value in values:
        if value and value not in deduped:
            deduped.append(value)
    return deduped


def _dedupe_artifacts(artifacts: list[Artifact]) -> list[Artifact]:
    by_id: dict[str, Artifact] = {}
    for artifact in artifacts:
        by_id.setdefault(artifact.artifact_id, artifact)
    return list(by_id.values())


def _compact_results(results: list[ToolResult | None]) -> list[ToolResult]:
    return [result for result in results if result is not None]


def _dedupe_paths(paths: list[Path]) -> list[Path]:
    deduped: dict[str, Path] = {}
    for path in paths:
        deduped.setdefault(path.resolve().as_posix(), path)
    return list(deduped.values())


def _resolve_output_dir(path: str | Path) -> Path:
    marker = resolve_output_path(Path(path) / ".okoffice-dir")
    marker.parent.mkdir(parents=True, exist_ok=True)
    return marker.parent


def _job_id() -> str:
    return f"job_{uuid4().hex[:16]}"
