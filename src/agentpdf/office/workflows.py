from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4
from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile

from agentpdf.artifacts.store import build_artifact
from agentpdf.office.deck import create_deck_from_outline, validate_deck_presentation
from agentpdf.office.context import build_office_context_packet
from agentpdf.office.extract import extract_schema
from agentpdf.office.inspect import inspect_office_file
from agentpdf.office.sheet import extract_sheet_tables, profile_sheet_data, validate_sheet_workbook
from agentpdf.office.validation import validate_sheet_formulas
from agentpdf.office.word import extract_word_tables, inspect_word_document
from agentpdf.office.workbook import write_sheet_workbook as write_evidence_workbook
from agentpdf.office.xlsx import write_xlsx
from agentpdf.schemas.errors import AgentPDFException
from agentpdf.schemas.models import AgentPDFError, ToolResult, ValidationCheck, ValidationReport
from agentpdf.security.paths import resolve_input_path, resolve_output_path


EXTRACT_TO_SHEET_TOOL_NAME = "office.workflow.extract_to_sheet"
DOCSET_TO_SHEET_TOOL_NAME = "office.workflow.docset_to_sheet"
SHEET_TO_DECK_TOOL_NAME = "office.workflow.sheet_to_deck"
BOARD_PACK_TOOL_NAME = "office.workflow.board_pack"
BUNDLE_VERIFY_TOOL_NAME = "office.bundle.verify"
TOOL_NAME = EXTRACT_TO_SHEET_TOOL_NAME
XLSX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
PPTX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
ZIP_MIME_TYPE = "application/zip"


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
    try:
        output = resolve_output_path(output_path)
        context_path = resolve_output_path(context_output_path or output.with_suffix(".context.json"))
        evidence_path = resolve_output_path(evidence_output_path or output.with_suffix(".evidence.json"))
        schema_obj = _workflow_schema_object(schema)
    except (AgentPDFException, json.JSONDecodeError) as exc:
        error = exc.to_error() if isinstance(exc, AgentPDFException) else AgentPDFError(code="invalid_input", message=str(exc))
        return _failed(error, tool=DOCSET_TO_SHEET_TOOL_NAME)

    context_result = build_office_context_packet(
        files=files,
        output_path=context_path,
        title=title or "OKoffice Docset To Sheet Context",
        intent=intent or "Build an evidence-backed workbook from source documents.",
    )
    if context_result.status != "succeeded":
        return _failed_from_workflow_step(DOCSET_TO_SHEET_TOOL_NAME, context_result, [context_result])

    extract_result = extract_schema(context_result.usage["context_packet"], schema_obj)
    if extract_result.status != "succeeded":
        return _failed_from_workflow_step(DOCSET_TO_SHEET_TOOL_NAME, extract_result, [context_result, extract_result])

    extraction = _workflow_extraction_payload(extract_result, schema_obj)
    evidence_path.write_text(json.dumps(extraction, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    evidence_artifact = build_artifact(evidence_path, DOCSET_TO_SHEET_TOOL_NAME)

    workbook_result = write_evidence_workbook(evidence=extraction, output_path=output)
    if workbook_result.status != "succeeded":
        return _failed_from_workflow_step(
            DOCSET_TO_SHEET_TOOL_NAME,
            workbook_result,
            [context_result, extract_result, workbook_result],
        )

    validation_result = validate_sheet_formulas(output)
    if validation_result.status != "succeeded":
        return _failed_from_workflow_step(
            DOCSET_TO_SHEET_TOOL_NAME,
            validation_result,
            [context_result, extract_result, workbook_result, validation_result],
        )

    step_results = [context_result, extract_result, workbook_result, validation_result]
    warnings = _dedupe_workflow_warnings([warning for result in step_results for warning in result.warnings])
    artifacts = _dedupe_workflow_artifacts([*context_result.artifacts, evidence_artifact, *workbook_result.artifacts])
    values = extraction["rows"][0]["values"] if extraction["rows"] else {}
    filled_value_count = len([value for value in values.values() if value not in {None, ""}])
    checks = [
        ValidationCheck(
            name=result.tool.replace(".", "_"),
            status=result.validation.status if result.validation is not None else "skipped",
            details={"job_id": result.job_id, "artifact_count": len(result.artifacts)},
        )
        for result in step_results
    ]
    return ToolResult(
        job_id=_job_id(),
        status="succeeded",
        tool=DOCSET_TO_SHEET_TOOL_NAME,
        artifacts=artifacts,
        validation=ValidationReport(
            status=_validation_report_status_from_checks(checks),
            checks=checks,
            warnings=warnings,
        ),
        warnings=warnings,
        usage={
            "summary": {
                "file_count": len(files),
                "field_count": len(extraction["fields"]),
                "row_count": len(extraction["rows"]),
                "filled_value_count": filled_value_count,
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
            "steps": [_workflow_step_summary(result) for result in step_results],
            "context_packet": context_result.usage.get("context_packet", {}),
            "extraction": extraction,
            "workbook": workbook_result.usage,
            "workbook_validation": validation_result.model_dump(mode="json"),
        },
        next_recommended_tools=["sheet.inspect.workbook", "office.workflow.sheet_to_deck", "office.bundle.export"],
    )


def extract_to_sheet(
    input_paths: list[str | Path],
    output_path: str | Path,
    *,
    context_packet: dict[str, Any] | str | Path | None = None,
    context_packet_path: str | Path | None = None,
) -> ToolResult:
    try:
        output = resolve_output_path(output_path)
        packet = _load_context_packet(context_packet=context_packet, context_packet_path=context_packet_path)
    except AgentPDFException as exc:
        return _failed(exc.to_error())

    effective_input_paths = _workflow_input_paths(input_paths, packet)
    source_graph = _source_graph_context(packet)
    records: list[dict[str, Any]] = []
    cell_records: list[dict[str, Any]] = []
    source_summaries: list[dict[str, Any]] = []
    warnings: list[str] = []

    for input_path in effective_input_paths:
        source_summary, source_records, source_cells, source_warnings = _extract_source(input_path)
        _attach_source_graph_refs(source_records, source_cells, source_graph)
        source_summaries.append(source_summary)
        records.extend(source_records)
        cell_records.extend(source_cells)
        warnings.extend(source_warnings)

    if not records:
        return _failed(
            AgentPDFError(
                code="unsupported_file_type",
                message="No supported Word or Excel tables were extracted for office.workflow.extract_to_sheet.",
                details={"input_count": len(effective_input_paths), "sources": source_summaries},
            )
        )

    _write_evidence_workbook(output, records=records, cell_records=cell_records, source_graph=source_graph)
    artifact = build_artifact(output, TOOL_NAME)
    table_count = len({record["table_record_id"] for record in records})
    cell_count = len(cell_records)
    workbook_sheets = ["Tables", "Cells", *([] if source_graph["node_count"] == 0 else ["SourceGraph"])]
    summary = {
        "source_count": len(effective_input_paths),
        "supported_source_count": _supported_count(source_summaries),
        "table_count": table_count,
        "row_count": len(records),
        "cell_count": cell_count,
    }
    if source_graph["context_packet_id"]:
        summary.update(
            {
                "context_packet_id": source_graph["context_packet_id"],
                "source_graph_id": source_graph["source_graph_id"],
                "source_graph_node_count": source_graph["node_count"],
            }
        )

    return ToolResult(
        job_id=_job_id(),
        status="succeeded",
        tool=TOOL_NAME,
        artifacts=[artifact],
        validation=ValidationReport(
            status="warning" if warnings else "passed",
            checks=[
                ValidationCheck(
                    name="sources_scanned",
                    status="passed",
                    details={
                        "source_count": len(effective_input_paths),
                        "supported_source_count": _supported_count(source_summaries),
                    },
                ),
                ValidationCheck(
                    name="evidence_rows_extracted",
                    status="passed",
                    details={"table_count": table_count, "row_count": len(records), "cell_count": cell_count},
                ),
                ValidationCheck(
                    name="context_source_graph_loaded",
                    status="passed" if source_graph["node_count"] else "skipped",
                    details={
                        "context_packet_id": source_graph["context_packet_id"],
                        "source_graph_id": source_graph["source_graph_id"],
                        "node_count": source_graph["node_count"],
                    },
                ),
                ValidationCheck(
                    name="evidence_workbook_written",
                    status="passed",
                    details={"path": output.as_posix(), "mime_type": XLSX_MIME_TYPE},
                ),
            ],
            warnings=warnings,
        ),
        warnings=warnings,
        usage={
            "summary": summary,
            "evidence_workbook": {
                "path": output.as_posix(),
                "format": "xlsx",
                "sheets": workbook_sheets,
                "artifact_id": artifact.artifact_id,
            },
            "source_graph": _source_graph_usage(source_graph),
            "sources": source_summaries,
            "records": records,
            "cell_records": cell_records,
        },
        next_recommended_tools=[
            "sheet.inspect.workbook",
            "sheet.profile.data",
            "office.workflow.sheet_to_deck",
            "office.context.build_packet",
        ],
    )


def sheet_to_deck(
    workbook_path: str | Path,
    output_path: str | Path,
    *,
    title: str | None = None,
    max_rows_per_sheet: int = 100,
) -> ToolResult:
    try:
        output = resolve_output_path(output_path)
    except AgentPDFException as exc:
        return _failed(exc.to_error(), tool=SHEET_TO_DECK_TOOL_NAME)

    profile_result = profile_sheet_data(workbook_path, max_rows_per_sheet=max_rows_per_sheet)
    if profile_result.status == "failed":
        return _failed(
            profile_result.error
            or AgentPDFError(code="unsupported_file_type", message="Workbook profile failed before deck creation."),
            tool=SHEET_TO_DECK_TOOL_NAME,
        )

    profile_usage = profile_result.usage
    summary = profile_usage.get("summary", {}) if isinstance(profile_usage.get("summary"), dict) else {}
    profiles = profile_usage.get("profiles", []) if isinstance(profile_usage.get("profiles"), list) else []
    data_row_count = int(summary.get("data_row_count", 0))
    profiled_profiles = [profile for profile in profiles if isinstance(profile, dict) and int(profile.get("data_row_count", 0)) > 0]
    if data_row_count <= 0 or not profiled_profiles:
        return _failed(
            AgentPDFError(
                code="unsafe_input_rejected",
                message="office.workflow.sheet_to_deck requires at least one profiled workbook data row.",
                details={"workbook_path": str(workbook_path), "profiled_sheet_count": len(profiled_profiles)},
            ),
            tool=SHEET_TO_DECK_TOOL_NAME,
        )

    outline = _sheet_profile_outline(
        workbook_path=workbook_path,
        title=title,
        profile_summary=summary,
        profiles=profiled_profiles,
        warnings=profile_result.warnings,
    )
    deck_result = create_deck_from_outline(outline, output)
    if deck_result.status == "failed":
        return _failed(
            deck_result.error or AgentPDFError(code="artifact_validation_failed", message="Deck creation failed."),
            tool=SHEET_TO_DECK_TOOL_NAME,
        )

    artifact = build_artifact(output, SHEET_TO_DECK_TOOL_NAME)
    deck_summary = deck_result.usage.get("summary", {}) if isinstance(deck_result.usage.get("summary"), dict) else {}
    warnings = [*profile_result.warnings, *deck_result.warnings]
    checks = [
        ValidationCheck(
            name="workbook_profiled",
            status="passed",
            details={
                "workbook_path": str(workbook_path),
                "profiled_sheet_count": summary.get("profiled_sheet_count", 0),
                "data_row_count": data_row_count,
                "source_coverage": summary.get("source_coverage", {}),
            },
        ),
        ValidationCheck(
            name="deck_outline_created",
            status="passed",
            details={
                "slide_count": len(outline["slides"]),
                "style": outline["style"],
                "source": outline["source"],
            },
        ),
        ValidationCheck(
            name="pptx_written",
            status="passed",
            details={"path": output.as_posix(), "mime_type": PPTX_MIME_TYPE},
        ),
        ValidationCheck(
            name="deck_validated",
            status=deck_result.validation.status if deck_result.validation is not None else "warning",
            details={
                "slide_count": deck_summary.get("slide_count", len(outline["slides"])),
                "text_run_count": deck_summary.get("text_run_count", 0),
            },
        ),
    ]

    return ToolResult(
        job_id=_job_id(),
        status="succeeded",
        tool=SHEET_TO_DECK_TOOL_NAME,
        artifacts=[artifact],
        validation=ValidationReport(
            status="warning" if warnings else "passed",
            checks=checks,
            warnings=warnings,
        ),
        warnings=warnings,
        usage={
            "summary": {
                "workbook_path": str(workbook_path),
                "deck_path": output.as_posix(),
                "slide_count": deck_summary.get("slide_count", len(outline["slides"])),
                "profiled_sheet_count": summary.get("profiled_sheet_count", len(profiled_profiles)),
                "column_count": summary.get("column_count", 0),
                "data_row_count": data_row_count,
                "missing_cell_count": summary.get("missing_cell_count", 0),
                "formula_cell_count": summary.get("formula_cell_count", 0),
                "source_coverage": summary.get("source_coverage", {}),
            },
            "workbook_profile": {
                "summary": summary,
                "profiles": profiled_profiles,
            },
            "outline": outline,
            "deck": {
                "path": output.as_posix(),
                "format": "pptx",
                "artifact_id": artifact.artifact_id,
            },
        },
        next_recommended_tools=[
            "deck.inspect.presentation",
            "deck.validate.presentation",
            "office.workflow.board_pack",
            "office.context.build_packet",
        ],
    )


def board_pack(
    files: list[str | Path],
    output_path: str | Path,
    *,
    title: str | None = None,
) -> ToolResult:
    try:
        output = resolve_output_path(output_path)
    except AgentPDFException as exc:
        return _failed(exc.to_error(), tool=BOARD_PACK_TOOL_NAME)
    if not files:
        return _failed(
            AgentPDFError(
                code="unsafe_input_rejected",
                message="office.workflow.board_pack requires at least one input file.",
            ),
            tool=BOARD_PACK_TOOL_NAME,
        )

    file_entries: list[dict[str, Any]] = []
    validation_results: list[dict[str, Any]] = []
    warnings: list[str] = []
    archive_paths: set[str] = set()

    for file_index, file_path in enumerate(files, start=1):
        inspect_result = inspect_office_file(file_path)
        if inspect_result.status == "failed":
            return _failed(
                inspect_result.error
                or AgentPDFError(code="unsupported_file_type", message=f"Unable to inspect board pack file: {file_path}"),
                tool=BOARD_PACK_TOOL_NAME,
            )
        source_path = Path(inspect_result.usage["file"]["path"])
        archive_path = _artifact_archive_path(source_path, archive_paths)
        validation_result = _validate_board_pack_file(source_path, inspect_result)
        validation_results.append(_pack_validation_result(source_path, inspect_result, validation_result))
        warnings.extend(validation_result.warnings)
        artifact = build_artifact(source_path, BOARD_PACK_TOOL_NAME)
        file_entries.append(
            {
                "index": file_index,
                "path": source_path.as_posix(),
                "name": source_path.name,
                "archive_path": archive_path,
                "artifact_id": artifact.artifact_id,
                "mime_type": artifact.mime_type,
                "size_bytes": artifact.size_bytes,
                "sha256": artifact.sha256,
                "detected_format": inspect_result.usage["format"]["detected_format"],
                "domain": inspect_result.usage["format"]["domain"],
                "validation_tool": validation_result.tool,
                "validation_status": validation_result.validation.status if validation_result.validation is not None else "skipped",
            }
        )

    manifest = _board_pack_manifest(title=title, files=file_entries)
    validation_report = _board_pack_validation_report(validation_results=validation_results, warnings=warnings)
    _write_board_pack_zip(output, file_entries=file_entries, manifest=manifest, validation_report=validation_report)
    bundle_artifact = build_artifact(output, BOARD_PACK_TOOL_NAME)
    checks = [
        ValidationCheck(
            name="input_files_scanned",
            status="passed",
            details={"input_count": len(files), "packaged_file_count": len(file_entries)},
        ),
        ValidationCheck(
            name="artifact_validations_collected",
            status=_validation_report_status_from_strings(
                [str(result.get("validation_status", "skipped")) for result in validation_results]
            ),
            details={"validation_result_count": len(validation_results)},
        ),
        ValidationCheck(
            name="board_pack_zip_written",
            status="passed",
            details={"path": output.as_posix(), "mime_type": ZIP_MIME_TYPE},
        ),
    ]
    return ToolResult(
        job_id=_job_id(),
        status="succeeded",
        tool=BOARD_PACK_TOOL_NAME,
        artifacts=[bundle_artifact],
        validation=ValidationReport(
            status=_validation_report_status_from_checks(checks),
            checks=checks,
            warnings=warnings,
        ),
        warnings=warnings,
        usage={
            "summary": {
                "input_count": len(files),
                "packaged_file_count": len(file_entries),
                "validation_result_count": len(validation_results),
                "warning_count": len(warnings),
                "bundle_path": output.as_posix(),
            },
            "bundle": {
                "path": output.as_posix(),
                "format": "zip",
                "artifact_id": bundle_artifact.artifact_id,
                "manifest_member": "okoffice-manifest.json",
                "validation_member": "okoffice-validation.json",
            },
            "files": file_entries,
            "validation_results": validation_results,
        },
        next_recommended_tools=[
            "office.bundle.verify",
            "office.artifacts.source_map",
            "office.context.build_packet",
        ],
    )


def verify_board_pack(bundle_path: str | Path) -> ToolResult:
    try:
        bundle = resolve_input_path(bundle_path)
    except AgentPDFException as exc:
        return _failed(exc.to_error(), tool=BUNDLE_VERIFY_TOOL_NAME)

    warnings: list[str] = []
    try:
        with ZipFile(bundle, "r") as archive:
            member_names = archive.namelist()
            member_set = set(member_names)
            manifest, manifest_status = _read_bundle_json_member(
                archive,
                member_set=member_set,
                member_name="okoffice-manifest.json",
                warnings=warnings,
            )
            validation_report, validation_status = _read_bundle_json_member(
                archive,
                member_set=member_set,
                member_name="okoffice-validation.json",
                warnings=warnings,
            )
            files = manifest.get("files") if isinstance(manifest.get("files"), list) else []
            expected_file_count = _coerce_non_negative_int(manifest.get("file_count"), fallback=len(files))
            validation_results = (
                validation_report.get("validation_results")
                if isinstance(validation_report.get("validation_results"), list)
                else []
            )
            verified_files = _verify_bundle_files(archive, member_set=member_set, files=files, warnings=warnings)
    except BadZipFile:
        return _failed(
            AgentPDFError(
                code="unsupported_file_type",
                message="OKoffice board pack is not a readable ZIP file.",
                details={"bundle_path": str(bundle_path)},
            ),
            tool=BUNDLE_VERIFY_TOOL_NAME,
        )
    except OSError as exc:
        return _failed(
            AgentPDFError(
                code="artifact_validation_failed",
                message=f"Unable to read OKoffice board pack: {exc}",
                details={"bundle_path": str(bundle_path)},
            ),
            tool=BUNDLE_VERIFY_TOOL_NAME,
        )

    missing_file_count = sum(1 for file in verified_files if not file["member_present"])
    hash_mismatch_count = sum(1 for file in verified_files if file["hash_status"] == "failed")
    size_mismatch_count = sum(1 for file in verified_files if file["size_status"] == "failed")
    verified_file_count = sum(1 for file in verified_files if file["integrity_status"] == "passed")
    checks = [
        ValidationCheck(
            name="zip_readable",
            status="passed",
            details={"path": bundle.as_posix(), "member_count": len(member_names)},
        ),
        ValidationCheck(
            name="manifest_present",
            status="passed" if manifest_status == "passed" else "failed",
            details={"member": "okoffice-manifest.json", "status": manifest_status},
        ),
        ValidationCheck(
            name="validation_report_present",
            status="passed" if validation_status == "passed" else "failed",
            details={"member": "okoffice-validation.json", "status": validation_status},
        ),
        ValidationCheck(
            name="manifest_product_ok",
            status=_passed_or_failed(manifest.get("product") == "okoffice"),
            details={"product": manifest.get("product")},
        ),
        ValidationCheck(
            name="manifest_workflow_ok",
            status=_passed_or_failed(manifest.get("workflow") == BOARD_PACK_TOOL_NAME),
            details={"workflow": manifest.get("workflow"), "expected_workflow": BOARD_PACK_TOOL_NAME},
        ),
        ValidationCheck(
            name="validation_report_product_ok",
            status=_passed_or_failed(validation_report.get("product") == "okoffice"),
            details={"product": validation_report.get("product")},
        ),
        ValidationCheck(
            name="validation_report_workflow_ok",
            status=_passed_or_failed(validation_report.get("workflow") == BOARD_PACK_TOOL_NAME),
            details={"workflow": validation_report.get("workflow"), "expected_workflow": BOARD_PACK_TOOL_NAME},
        ),
        ValidationCheck(
            name="manifest_file_count_matches",
            status=_passed_or_failed(expected_file_count == len(files)),
            details={"file_count": expected_file_count, "manifest_file_entries": len(files)},
        ),
        ValidationCheck(
            name="artifact_members_present",
            status=_passed_or_failed(missing_file_count == 0),
            details={"manifest_file_count": len(files), "missing_file_count": missing_file_count},
        ),
        ValidationCheck(
            name="artifact_hashes_match",
            status=_passed_or_failed(hash_mismatch_count == 0),
            details={"checked_file_count": len(files), "hash_mismatch_count": hash_mismatch_count},
        ),
        ValidationCheck(
            name="artifact_sizes_match",
            status=_passed_or_failed(size_mismatch_count == 0),
            details={"checked_file_count": len(files), "size_mismatch_count": size_mismatch_count},
        ),
        ValidationCheck(
            name="validation_result_count_matches",
            status=_passed_or_failed(len(validation_results) == len(files)),
            details={"validation_result_count": len(validation_results), "manifest_file_count": len(files)},
        ),
    ]
    artifact = build_artifact(bundle, BUNDLE_VERIFY_TOOL_NAME)
    return ToolResult(
        job_id=_job_id(),
        status="succeeded",
        tool=BUNDLE_VERIFY_TOOL_NAME,
        artifacts=[artifact],
        validation=ValidationReport(
            status=_validation_report_status_from_checks(checks),
            checks=checks,
            warnings=warnings,
        ),
        warnings=warnings,
        usage={
            "summary": {
                "bundle_path": bundle.as_posix(),
                "member_count": len(member_names),
                "manifest_file_count": len(files),
                "expected_file_count": expected_file_count,
                "validation_result_count": len(validation_results),
                "verified_file_count": verified_file_count,
                "missing_file_count": missing_file_count,
                "hash_mismatch_count": hash_mismatch_count,
                "size_mismatch_count": size_mismatch_count,
                "warning_count": len(warnings),
            },
            "bundle": {
                "path": bundle.as_posix(),
                "format": "zip",
                "artifact_id": artifact.artifact_id,
                "manifest_member": "okoffice-manifest.json",
                "validation_member": "okoffice-validation.json",
            },
            "manifest": manifest,
            "validation_report_summary": {
                "product": validation_report.get("product"),
                "workflow": validation_report.get("workflow"),
                "status": validation_report.get("status"),
                "warning_count": validation_report.get("warning_count", 0),
                "validation_result_count": len(validation_results),
            },
            "files": verified_files,
        },
        next_recommended_tools=[
            "office.artifacts.source_map",
            "office.context.build_packet",
            "office.workflow.extract_to_sheet",
        ],
    )


def _workflow_schema_object(schema: dict[str, Any] | str | Path) -> dict[str, Any]:
    if isinstance(schema, dict):
        return schema
    if isinstance(schema, Path) or (isinstance(schema, str) and Path(schema).exists()):
        data = json.loads(Path(schema).read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise AgentPDFException("invalid_input", "Schema JSON must be an object.")
        return data
    if isinstance(schema, str):
        data = json.loads(schema)
        if not isinstance(data, dict):
            raise AgentPDFException("invalid_input", "Schema JSON must be an object.")
        return data
    raise AgentPDFException("invalid_input", "schema must be a JSON object, JSON string, or path.")


def _workflow_extraction_payload(extract_result: ToolResult, schema: dict[str, Any]) -> dict[str, Any]:
    evidence = extract_result.usage.get("evidence", {}) if isinstance(extract_result.usage.get("evidence"), dict) else {}
    records = [record for record in evidence.get("records", []) if isinstance(record, dict)]
    fields = evidence.get("fields") if isinstance(evidence.get("fields"), list) else schema.get("fields", [])
    normalized_fields = [_workflow_field(field) for field in fields if isinstance(field, dict)]
    values = {str(record.get("field")): record.get("value", "") for record in records if record.get("field")}
    field_evidence = {
        str(record.get("field")): {
            "source_ref": record.get("source_ref"),
            "source_type": record.get("source_type"),
            "locator": record.get("locator"),
            "confidence": record.get("confidence"),
            "excerpt": record.get("matched_text"),
        }
        for record in records
        if record.get("field")
    }
    source_refs = _workflow_source_refs(records)
    return {
        "extraction_id": f"extract_{uuid4().hex[:16]}",
        "schema_name": str(schema.get("name") or "schema"),
        "context_packet_id": evidence.get("context_packet_id"),
        "source_graph_id": evidence.get("source_graph_id"),
        "fields": normalized_fields,
        "rows": [
            {
                "row_id": "row_001",
                "values": values,
                "field_evidence": field_evidence,
            }
        ],
        "source_refs": source_refs,
        "method": str(evidence.get("method") or "local_label_value_match_v0"),
    }


def _workflow_field(field: dict[str, Any]) -> dict[str, Any]:
    name = str(field.get("name") or "")
    aliases = field.get("aliases") if isinstance(field.get("aliases"), list) else []
    return {
        "name": name,
        "type": str(field.get("type") or "string"),
        "aliases": [str(alias) for alias in aliases],
        "required": bool(field.get("required", False)),
    }


def _workflow_source_refs(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    seen: set[str] = set()
    for record in records:
        source_ref = str(record.get("source_ref") or "")
        if not source_ref or source_ref in seen:
            continue
        seen.add(source_ref)
        refs.append(
            {
                "source_ref": source_ref,
                "source_type": record.get("source_type"),
                "locator": record.get("locator"),
            }
        )
    return refs


def _workflow_step_summary(result: ToolResult) -> dict[str, Any]:
    return {
        "tool": result.tool,
        "status": result.status,
        "job_id": result.job_id,
        "artifact_count": len(result.artifacts),
        "validation_status": result.validation.status if result.validation is not None else "skipped",
        "warning_count": len(result.warnings),
    }


def _dedupe_workflow_warnings(warnings: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for warning in warnings:
        if warning and warning not in seen:
            seen.add(warning)
            deduped.append(warning)
    return deduped


def _dedupe_workflow_artifacts(artifacts: list[Any]) -> list[Any]:
    deduped = []
    seen: set[str] = set()
    for artifact in artifacts:
        key = getattr(artifact, "artifact_id", "")
        if key and key not in seen:
            seen.add(key)
            deduped.append(artifact)
    return deduped


def _failed_from_workflow_step(tool: str, failed_result: ToolResult, step_results: list[ToolResult]) -> ToolResult:
    error = failed_result.error or AgentPDFError(
        code="output_validation_failed",
        message=f"Workflow step failed: {failed_result.tool}",
    )
    warnings = _dedupe_workflow_warnings([warning for result in step_results for warning in result.warnings])
    return ToolResult(
        job_id=_job_id(),
        status="failed",
        tool=tool,
        artifacts=_dedupe_workflow_artifacts([artifact for result in step_results for artifact in result.artifacts]),
        validation=ValidationReport(
            status="failed",
            checks=[
                ValidationCheck(
                    name=result.tool.replace(".", "_"),
                    status="failed" if result is failed_result else result.validation.status if result.validation else "skipped",
                    details={"job_id": result.job_id, "artifact_count": len(result.artifacts)},
                )
                for result in step_results
            ],
            warnings=warnings,
        ),
        warnings=warnings or [error.message],
        error=error,
        usage={"steps": [_workflow_step_summary(result) for result in step_results]},
    )


def _board_pack_manifest(*, title: str | None, files: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "product": "okoffice",
        "workflow": BOARD_PACK_TOOL_NAME,
        "title": (title or "OKoffice Board Pack").strip(),
        "created_at": datetime.now(UTC).isoformat(),
        "file_count": len(files),
        "files": files,
    }


def _board_pack_validation_report(
    *,
    validation_results: list[dict[str, Any]],
    warnings: list[str],
) -> dict[str, Any]:
    return {
        "product": "okoffice",
        "workflow": BOARD_PACK_TOOL_NAME,
        "status": _validation_report_status_from_strings(
            [str(result.get("validation_status", "skipped")) for result in validation_results]
        ),
        "warning_count": len(warnings),
        "warnings": warnings,
        "validation_results": validation_results,
    }


def _validate_board_pack_file(path: Path, inspect_result: ToolResult) -> ToolResult:
    detected_format = str(inspect_result.usage["format"]["detected_format"])
    if detected_format == "xlsx":
        return validate_sheet_workbook(path)
    if detected_format == "pptx":
        return validate_deck_presentation(path)
    if detected_format == "docx":
        return inspect_word_document(path)
    return inspect_result


def _pack_validation_result(
    path: Path,
    inspect_result: ToolResult,
    validation_result: ToolResult,
) -> dict[str, Any]:
    validation_status = validation_result.validation.status if validation_result.validation is not None else "skipped"
    summary = validation_result.usage.get("summary", {}) if isinstance(validation_result.usage.get("summary"), dict) else {}
    return {
        "path": path.as_posix(),
        "name": path.name,
        "detected_format": inspect_result.usage["format"]["detected_format"],
        "domain": inspect_result.usage["format"]["domain"],
        "tool": validation_result.tool,
        "status": validation_result.status,
        "validation_status": validation_status,
        "warnings": list(validation_result.warnings),
        "summary": summary,
    }


def _write_board_pack_zip(
    output: Path,
    *,
    file_entries: list[dict[str, Any]],
    manifest: dict[str, Any],
    validation_report: dict[str, Any],
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        for entry in file_entries:
            archive.write(Path(entry["path"]), arcname=str(entry["archive_path"]))
        archive.writestr(
            "okoffice-manifest.json",
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True),
        )
        archive.writestr(
            "okoffice-validation.json",
            json.dumps(validation_report, ensure_ascii=False, indent=2, sort_keys=True),
        )


def _read_bundle_json_member(
    archive: ZipFile,
    *,
    member_set: set[str],
    member_name: str,
    warnings: list[str],
) -> tuple[dict[str, Any], str]:
    if member_name not in member_set:
        warnings.append(f"Board pack JSON member missing: {member_name}")
        return {}, "missing"
    try:
        payload = json.loads(archive.read(member_name).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        warnings.append(f"Board pack JSON member invalid: {member_name} ({exc})")
        return {}, "invalid"
    if not isinstance(payload, dict):
        warnings.append(f"Board pack JSON member must be an object: {member_name}")
        return {}, "invalid"
    return payload, "passed"


def _verify_bundle_files(
    archive: ZipFile,
    *,
    member_set: set[str],
    files: list[Any],
    warnings: list[str],
) -> list[dict[str, Any]]:
    verified_files: list[dict[str, Any]] = []
    for index, raw_entry in enumerate(files, start=1):
        entry = raw_entry if isinstance(raw_entry, dict) else {}
        archive_path = str(entry.get("archive_path") or "")
        expected_sha256 = str(entry.get("sha256") or "")
        expected_size = _coerce_int(entry.get("size_bytes"), fallback=-1)
        member_present = bool(archive_path and archive_path in member_set)
        actual_sha256: str | None = None
        actual_size: int | None = None
        hash_status = "skipped"
        size_status = "skipped"

        if not archive_path:
            warnings.append(f"Board pack artifact entry missing archive_path at index {index}")
        elif not member_present:
            warnings.append(f"Board pack artifact missing from ZIP: {archive_path}")
        else:
            data = archive.read(archive_path)
            actual_sha256 = hashlib.sha256(data).hexdigest()
            actual_size = len(data)
            hash_status = "passed" if expected_sha256 and actual_sha256 == expected_sha256 else "failed"
            size_status = "passed" if expected_size >= 0 and actual_size == expected_size else "failed"
            if hash_status == "failed":
                warnings.append(f"Board pack artifact sha256 mismatch: {archive_path}")
            if size_status == "failed":
                warnings.append(f"Board pack artifact size mismatch: {archive_path}")

        integrity_status = "passed" if member_present and hash_status == "passed" and size_status == "passed" else "failed"
        verified_files.append(
            {
                "index": index,
                "archive_path": archive_path,
                "name": entry.get("name"),
                "detected_format": entry.get("detected_format"),
                "domain": entry.get("domain"),
                "validation_tool": entry.get("validation_tool"),
                "validation_status": entry.get("validation_status"),
                "member_present": member_present,
                "expected_sha256": expected_sha256,
                "actual_sha256": actual_sha256,
                "hash_status": hash_status,
                "expected_size_bytes": expected_size if expected_size >= 0 else None,
                "actual_size_bytes": actual_size,
                "size_status": size_status,
                "integrity_status": integrity_status,
            }
        )
    return verified_files


def _passed_or_failed(condition: bool) -> str:
    return "passed" if condition else "failed"


def _coerce_non_negative_int(value: Any, *, fallback: int) -> int:
    coerced = _coerce_int(value, fallback=fallback)
    return coerced if coerced >= 0 else fallback


def _coerce_int(value: Any, *, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _artifact_archive_path(path: Path, used_paths: set[str]) -> str:
    base_name = path.name.replace("\\", "_").replace("/", "_")
    candidate = f"artifacts/{base_name}"
    if candidate not in used_paths:
        used_paths.add(candidate)
        return candidate
    stem = path.stem
    suffix = path.suffix
    index = 2
    while True:
        candidate = f"artifacts/{stem}-{index}{suffix}"
        if candidate not in used_paths:
            used_paths.add(candidate)
            return candidate
        index += 1


def _validation_report_status_from_strings(statuses: list[str]) -> str:
    if "failed" in statuses:
        return "failed"
    if "warning" in statuses:
        return "warning"
    if all(status == "skipped" for status in statuses):
        return "skipped"
    return "passed"


def _validation_report_status_from_checks(checks: list[ValidationCheck]) -> str:
    return _validation_report_status_from_strings([check.status for check in checks])


def _sheet_profile_outline(
    *,
    workbook_path: str | Path,
    title: str | None,
    profile_summary: dict[str, Any],
    profiles: list[dict[str, Any]],
    warnings: list[str],
) -> dict[str, Any]:
    deck_title = (title or "").strip() or f"{Path(workbook_path).stem} Review"
    source_coverage = profile_summary.get("source_coverage", {})
    coverage_status = source_coverage.get("status", "unknown") if isinstance(source_coverage, dict) else "unknown"
    slides: list[dict[str, Any]] = [
        {
            "title": deck_title,
            "subtitle": "Generated from an OKoffice workbook profile",
            "bullets": [
                f"{profile_summary.get('profiled_sheet_count', len(profiles))} profiled sheet(s)",
                f"{profile_summary.get('data_row_count', 0)} data rows across {profile_summary.get('column_count', 0)} columns",
                f"Source coverage: {coverage_status}",
            ],
            "notes": f"Source workbook: {workbook_path}",
        },
        {
            "title": "Executive Summary",
            "bullets": [
                f"Workbook rows profiled: {profile_summary.get('data_row_count', 0)}",
                f"Formula cells detected: {profile_summary.get('formula_cell_count', 0)}",
                f"Missing cells detected: {profile_summary.get('missing_cell_count', 0)}",
                f"Source refs: {coverage_status}",
            ],
        },
    ]
    for profile in profiles[:8]:
        slides.append(_profile_slide(profile, coverage_status=coverage_status))

    validation_bullets = [
        f"Source coverage: {coverage_status}",
        f"Source ref rows: {profile_summary.get('source_ref_row_count', 0)}",
        f"Missing cells: {profile_summary.get('missing_cell_count', 0)}",
        f"Formula cells: {profile_summary.get('formula_cell_count', 0)}",
    ]
    if warnings:
        validation_bullets.append(f"Warnings: {len(warnings)}")
    slides.append(
        {
            "title": "Validation & Source Map",
            "bullets": validation_bullets,
            "notes": "Run deck.inspect.presentation and office.workflow.board_pack before delivery.",
        }
    )
    return {
        "title": deck_title,
        "style": "executive",
        "source": {
            "type": "workbook_profile",
            "workbook_path": str(workbook_path),
            "profile_tool": "sheet.profile.data",
        },
        "slides": slides,
    }


def _profile_slide(profile: dict[str, Any], *, coverage_status: str) -> dict[str, Any]:
    sheet_name = str(profile.get("sheet_name") or "Workbook Sheet")
    headers = [str(header) for header in profile.get("headers", []) if str(header).strip()]
    columns = profile.get("columns", []) if isinstance(profile.get("columns"), list) else []
    numeric_columns = _columns_by_semantic_type(columns, "number")
    text_columns = _columns_by_semantic_type(columns, "text")
    bullets = [
        f"{profile.get('data_row_count', 0)} data rows across {len(headers)} columns",
        f"Key columns: {_join_limited(headers, fallback='none detected')}",
        f"Numeric columns: {_join_limited(numeric_columns, fallback='none detected')}",
        f"Text columns: {_join_limited(text_columns, fallback='none detected')}",
        f"Missing cells: {profile.get('missing_cell_count', 0)}; formula cells: {profile.get('formula_cell_count', 0)}",
        f"Source coverage: {coverage_status}",
    ]
    return {
        "title": f"{sheet_name} Snapshot",
        "bullets": bullets,
        "notes": f"Source workbook sheet: {sheet_name}",
    }


def _columns_by_semantic_type(columns: list[Any], semantic_type: str) -> list[str]:
    names: list[str] = []
    for column in columns:
        if not isinstance(column, dict):
            continue
        if column.get("semantic_type") == semantic_type:
            names.append(str(column.get("header") or f"column_{column.get('column_index', '')}").strip())
    return [name for name in names if name]


def _join_limited(values: list[str], *, fallback: str, limit: int = 5) -> str:
    cleaned = [value for value in values if value][:limit]
    if not cleaned:
        return fallback
    suffix = "" if len(values) <= limit else f" (+{len(values) - limit} more)"
    return ", ".join(cleaned) + suffix


def _load_context_packet(
    *,
    context_packet: dict[str, Any] | str | Path | None,
    context_packet_path: str | Path | None,
) -> dict[str, Any] | None:
    payload = context_packet if context_packet is not None else context_packet_path
    if payload is None:
        return None
    if isinstance(payload, dict):
        packet = payload
    else:
        path = resolve_input_path(payload)
        try:
            packet = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise AgentPDFException("invalid_context_packet", f"Context packet JSON is invalid: {path}") from exc
    if not isinstance(packet, dict) or not isinstance(packet.get("items"), list):
        raise AgentPDFException("invalid_context_packet", "Context packet must include an items array.")
    if not isinstance(packet.get("source_graph"), dict):
        raise AgentPDFException("invalid_context_packet", "Context packet must include a source_graph object.")
    return packet


def _workflow_input_paths(input_paths: list[str | Path], packet: dict[str, Any] | None) -> list[str | Path]:
    paths: list[str | Path] = list(input_paths)
    if not paths and packet is not None:
        paths.extend(_context_packet_paths(packet))
    return _unique_paths(paths)


def _context_packet_paths(packet: dict[str, Any]) -> list[str]:
    paths: list[str] = []
    for item in packet.get("items", []):
        if isinstance(item, dict) and item.get("uri"):
            paths.append(str(item["uri"]))
    if paths:
        return paths
    graph = packet.get("source_graph", {}) if isinstance(packet.get("source_graph"), dict) else {}
    for node in graph.get("nodes", []):
        if not isinstance(node, dict):
            continue
        if node.get("type") != "file":
            continue
        locator = _first_locator(node)
        path = locator.get("path") or node.get("uri")
        if path:
            paths.append(str(path))
    return paths


def _unique_paths(paths: list[str | Path]) -> list[str | Path]:
    unique: list[str | Path] = []
    seen: set[str] = set()
    for path in paths:
        key = _path_key(path)
        if key in seen:
            continue
        seen.add(key)
        unique.append(path)
    return unique


def _source_graph_context(packet: dict[str, Any] | None) -> dict[str, Any]:
    if packet is None:
        return {
            "context_packet_id": None,
            "source_graph_id": None,
            "nodes": [],
            "node_count": 0,
            "edge_count": 0,
            "node_type_counts": {},
            "table_refs": {},
        }
    graph = packet.get("source_graph", {}) if isinstance(packet.get("source_graph"), dict) else {}
    nodes = [node for node in graph.get("nodes", []) if isinstance(node, dict)]
    edges = [edge for edge in graph.get("edges", []) if isinstance(edge, dict)]
    return {
        "context_packet_id": str(packet.get("context_packet_id") or ""),
        "source_graph_id": str(graph.get("source_graph_id") or ""),
        "nodes": nodes,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "node_type_counts": _counts(node.get("type") for node in nodes),
        "table_refs": _source_graph_table_refs(nodes),
    }


def _source_graph_table_refs(nodes: list[dict[str, Any]]) -> dict[tuple[str, int], list[dict[str, Any]]]:
    refs: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for node in nodes:
        node_type = str(node.get("type") or "")
        if node_type not in {"word.table", "sheet.table"}:
            continue
        locator = _first_locator(node)
        path = locator.get("path") or node.get("uri")
        table_index = _node_table_index(node, locator)
        if path is None or table_index <= 0:
            continue
        refs.setdefault((_path_key(path), table_index), []).append(_source_node_ref(node))
    return refs


def _attach_source_graph_refs(
    records: list[dict[str, Any]],
    cell_records: list[dict[str, Any]],
    source_graph: dict[str, Any],
) -> None:
    if not source_graph["context_packet_id"]:
        return
    for record in records:
        refs = _table_source_refs(record, source_graph)
        record["context_packet_id"] = source_graph["context_packet_id"]
        record["source_graph_id"] = source_graph["source_graph_id"]
        record["source_node_refs"] = refs
    for cell in cell_records:
        refs = _table_source_refs(cell, source_graph)
        cell["context_packet_id"] = source_graph["context_packet_id"]
        cell["source_graph_id"] = source_graph["source_graph_id"]
        cell["source_node_refs"] = refs


def _table_source_refs(row: dict[str, Any], source_graph: dict[str, Any]) -> list[dict[str, Any]]:
    table_index = int(row.get("table_index") or _table_index_from_table_id(str(row.get("table_id") or "")))
    return list(source_graph["table_refs"].get((_path_key(str(row.get("source_path") or "")), table_index), []))


def _source_graph_usage(source_graph: dict[str, Any]) -> dict[str, Any]:
    return {
        "context_packet_id": source_graph["context_packet_id"],
        "source_graph_id": source_graph["source_graph_id"],
        "node_count": source_graph["node_count"],
        "edge_count": source_graph["edge_count"],
        "node_type_counts": source_graph["node_type_counts"],
    }


def _first_locator(node: dict[str, Any]) -> dict[str, Any]:
    locators = node.get("locators")
    if isinstance(locators, list) and locators and isinstance(locators[0], dict):
        return locators[0]
    locator = node.get("locator")
    if isinstance(locator, dict):
        return locator
    return {}


def _source_node_ref(node: dict[str, Any]) -> dict[str, Any]:
    return {
        "node_id": node.get("node_id"),
        "type": node.get("type"),
        "source_ref": node.get("source_ref"),
        "locators": node.get("locators", []),
    }


def _node_table_index(node: dict[str, Any], locator: dict[str, Any]) -> int:
    if locator.get("table_index") is not None:
        return int(locator["table_index"])
    return _table_index_from_table_id(str(node.get("source_ref") or node.get("node_id") or ""))


def _table_index_from_table_id(value: str) -> int:
    tail = value.rsplit(":", 1)[-1].rsplit("_", 1)[-1]
    try:
        return int(tail)
    except ValueError:
        return 0


def _path_key(path: str | Path) -> str:
    try:
        return Path(path).expanduser().resolve().as_posix().lower()
    except (OSError, RuntimeError, ValueError):
        return str(path).replace("\\", "/").lower()


def _counts(values: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        key = str(value)
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def _extract_source(
    input_path: str | Path,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    preflight = inspect_office_file(input_path)
    if preflight.status == "failed":
        message = preflight.error.message if preflight.error else f"Unable to inspect source: {input_path}"
        return (
            {"path": str(input_path), "status": "failed", "table_count": 0, "row_count": 0, "cell_count": 0},
            [],
            [],
            [message],
        )

    source_path = str(preflight.usage["file"]["path"])
    source_format = str(preflight.usage["format"]["detected_format"])
    if source_format == "docx":
        result = extract_word_tables(source_path)
    elif source_format == "xlsx":
        result = extract_sheet_tables(source_path)
    else:
        warning = f"office.workflow.extract_to_sheet currently skips {source_format} sources: {source_path}"
        return (
            {
                "path": source_path,
                "format": source_format,
                "status": "skipped",
                "table_count": 0,
                "row_count": 0,
                "cell_count": 0,
                "reason": "unsupported_in_local_extract_to_sheet_v0",
            },
            [],
            [],
            [warning],
        )

    if result.status == "failed":
        message = result.error.message if result.error else f"Unable to extract source tables: {source_path}"
        return (
            {
                "path": source_path,
                "format": source_format,
                "status": "failed",
                "table_count": 0,
                "row_count": 0,
                "cell_count": 0,
            },
            [],
            [],
            [message],
        )

    records, cell_records = _normalize_table_result(source_path, source_format, result.usage["tables"])
    return (
        {
            "path": source_path,
            "format": source_format,
            "status": "extracted",
            "table_count": result.usage["summary"]["table_count"],
            "row_count": len(records),
            "cell_count": len(cell_records),
            "extract_tool": result.tool,
        },
        records,
        cell_records,
        list(result.warnings),
    )


def _normalize_table_result(
    source_path: str,
    source_format: str,
    tables: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    records = []
    cell_records = []
    for table in tables:
        table_id = str(table["table_id"])
        table_source = table.get("source", {}) if isinstance(table.get("source"), dict) else {}
        sheet_name = str(table_source.get("sheet_name") or "")
        table_record_id = f"{source_format}:{source_path}:{table_id}"
        for row in table.get("rows", []):
            row_index = int(row.get("row_index", 0))
            cells = row.get("cells", []) if isinstance(row.get("cells"), list) else []
            values = [_cell_text(cell) for cell in cells if isinstance(cell, dict)]
            source_refs = [cell.get("source", {}) for cell in cells if isinstance(cell, dict)]
            records.append(
                {
                    "table_record_id": table_record_id,
                    "source_path": source_path,
                    "source_format": source_format,
                    "table_id": table_id,
                    "table_index": int(table.get("table_index", 0)),
                    "source_sheet": sheet_name,
                    "source_row_index": row_index,
                    "values": values,
                    "source_refs": source_refs,
                }
            )
            for fallback_index, cell in enumerate(cells, start=1):
                if not isinstance(cell, dict):
                    continue
                source_ref = cell.get("source", {}) if isinstance(cell.get("source"), dict) else {}
                cell_records.append(
                    {
                        "source_path": source_path,
                        "source_format": source_format,
                        "table_id": table_id,
                        "table_index": int(table.get("table_index", 0)),
                        "source_sheet": sheet_name,
                        "source_row_index": row_index,
                        "source_cell_index": int(cell.get("cell_index") or source_ref.get("column_index") or fallback_index),
                        "cell_ref": str(cell.get("cell_ref") or source_ref.get("cell_ref") or ""),
                        "value": _cell_text(cell),
                        "source_ref": source_ref,
                    }
                )
    return records, cell_records


def _cell_text(cell: dict[str, Any]) -> str:
    return str(cell.get("text", cell.get("value", "")))


def _write_evidence_workbook(
    path: Path,
    *,
    records: list[dict[str, Any]],
    cell_records: list[dict[str, Any]],
    source_graph: dict[str, Any],
) -> None:
    max_columns = max((len(record["values"]) for record in records), default=0)
    table_headers = [
        "source_path",
        "source_format",
        "table_id",
        "source_sheet",
        "source_row_index",
        *[f"col_{index}" for index in range(1, max_columns + 1)],
        "source_node_refs_json",
        "source_refs_json",
    ]
    table_rows = [table_headers]
    for record in records:
        values = list(record["values"])
        table_rows.append(
            [
                record["source_path"],
                record["source_format"],
                record["table_id"],
                record["source_sheet"],
                str(record["source_row_index"]),
                *values,
                *([""] * (max_columns - len(values))),
                json.dumps(record.get("source_node_refs", []), ensure_ascii=False, sort_keys=True),
                json.dumps(record["source_refs"], ensure_ascii=False, sort_keys=True),
            ]
        )

    cell_headers = [
        "source_path",
        "source_format",
        "table_id",
        "source_sheet",
        "source_row_index",
        "source_cell_index",
        "cell_ref",
        "value",
        "source_node_refs_json",
        "source_ref_json",
    ]
    cell_rows = [cell_headers]
    for cell in cell_records:
        cell_rows.append(
            [
                cell["source_path"],
                cell["source_format"],
                cell["table_id"],
                cell["source_sheet"],
                str(cell["source_row_index"]),
                str(cell["source_cell_index"]),
                cell["cell_ref"],
                cell["value"],
                json.dumps(cell.get("source_node_refs", []), ensure_ascii=False, sort_keys=True),
                json.dumps(cell["source_ref"], ensure_ascii=False, sort_keys=True),
            ]
        )

    sheets = [("Tables", table_rows), ("Cells", cell_rows)]
    if source_graph["node_count"]:
        sheets.append(("SourceGraph", _source_graph_rows(source_graph)))
    write_xlsx(path, sheets)


def _source_graph_rows(source_graph: dict[str, Any]) -> list[list[object]]:
    rows: list[list[object]] = [
        [
            "context_packet_id",
            "source_graph_id",
            "node_id",
            "type",
            "role",
            "label",
            "uri",
            "locators_json",
            "evidence_json",
        ]
    ]
    for node in source_graph["nodes"]:
        rows.append(
            [
                source_graph["context_packet_id"],
                source_graph["source_graph_id"],
                str(node.get("node_id") or ""),
                str(node.get("type") or ""),
                str(node.get("role") or ""),
                str(node.get("label") or ""),
                str(node.get("uri") or ""),
                json.dumps(node.get("locators", []), ensure_ascii=False, sort_keys=True),
                json.dumps(node.get("evidence", {}), ensure_ascii=False, sort_keys=True),
            ]
        )
    return rows


def _supported_count(sources: list[dict[str, Any]]) -> int:
    return sum(1 for source in sources if source.get("status") == "extracted")


def _failed(error: AgentPDFError, *, tool: str = TOOL_NAME) -> ToolResult:
    return ToolResult(
        job_id=_job_id(),
        status="failed",
        tool=tool,
        error=error,
        warnings=[error.message],
    )


def _job_id() -> str:
    return f"job_{uuid4().hex[:16]}"
