from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any
from uuid import uuid4

from agentpdf.schemas.models import AgentPDFError, Artifact, ToolResult


SUPPORTED_LOCAL_WORKFLOW_TOOLS = {
    "deck.compose.plan",
    "deck.create.from_outline",
    "deck.create.presentation",
    "deck.inspect.presentation",
    "deck.patch.apply",
    "deck.validation.contact_sheet",
    "deck.validation.presentation",
    "deck.validate.presentation",
    "office.bundle.export",
    "office.bundle.verify",
    "office.context.build_packet",
    "office.extract.schema",
    "office.inspect.file",
    "office.validation.package",
    "office.workflow.board_pack",
    "office.workflow.docset_to_sheet",
    "office.workflow.extract_to_sheet",
    "office.workflow.sheet_to_deck",
    "office.workers.status",
    "pdf.inspect.document",
    "pdf.inspect.pages",
    "pdf.organize.merge",
    "pdf.organize.split",
    "pdf.organize.extract_pages",
    "pdf.organize.remove_pages",
    "pdf.organize.rotate_pages",
    "pdf.organize.reorder_pages",
    "pdf.organize.insert_blank_pages",
    "pdf.optimize.compress",
    "pdf.optimize.repair",
    "pdf.convert.image_to_pdf",
    "pdf.convert.markdown_to_pdf",
    "pdf.convert.text_to_pdf",
    "pdf.convert.extract_images",
    "pdf.convert.pdf_to_images",
    "pdf.convert.pdf_to_text",
    "pdf.convert.pdf_to_json",
    "pdf.convert.pdf_to_markdown",
    "pdf.edit.watermark",
    "pdf.edit.page_numbers",
    "pdf.metadata.read",
    "pdf.metadata.update",
    "pdf.metadata.remove",
    "pdf.validation.validate_output",
    "pdf.validation.render_check",
    "pdf.validation.blank_page_check",
    "pdf.ai.parse.lite",
    "pdf.ai.rag.ingest",
    "pdf.ai.rag.query",
    "pdf.ai.rag.search",
    "pdf.ai.rag.cite_answer",
    "pdf.ai.rag.chat",
    "pdf.ai.rag.export_report",
    "pdf.ai.rag.highlight_sources",
    "pdf.authoring.plan",
    "pdf.research.plan",
    "pdf.research.source_cards",
    "pdf.research.evidence_cards",
    "pdf.design.tokens",
    "pdf.storyboard.plan",
    "pdf.pages.write",
    "pdf.pages.revise",
    "pdf.create.html_package",
    "pdf.render.html_package",
    "pdf.qa.visual_report",
    "pdf.workflow.createpdf",
    "sheet.create.evidence_workbook",
    "sheet.extract.tables",
    "sheet.inspect.workbook",
    "sheet.profile.data",
    "sheet.read.workbook",
    "sheet.validate.workbook",
    "sheet.validation.formulas",
    "sheet.write.workbook",
    "word.create.report",
    "word.extract.tables",
    "word.inspect.document",
    "word.patch.apply",
    "word.patch.plan",
    "word.validation.document",
}


def _normalize_workflow_payload(workflow: Mapping[str, Any]) -> Mapping[str, Any]:
    usage = workflow.get("usage")
    if isinstance(usage, Mapping):
        nested = usage.get("workflow")
        if isinstance(nested, Mapping):
            return _merge_runner_overrides(workflow, nested)
    nested = workflow.get("workflow")
    if isinstance(nested, Mapping):
        return _merge_runner_overrides(workflow, nested)
    return workflow


def _merge_runner_overrides(source: Mapping[str, Any], nested: Mapping[str, Any]) -> dict[str, Any]:
    workflow = dict(nested)
    if "artifact_dir" in source:
        workflow["artifact_dir"] = source["artifact_dir"]
    if "bindings" in source:
        merged = dict(workflow.get("bindings", {}))
        if isinstance(source["bindings"], Mapping):
            merged.update(source["bindings"])
        workflow["bindings"] = merged
    return workflow


def run_workflow(workflow: Mapping[str, Any], dry_run: bool = False) -> ToolResult:
    tool = "pdf.workflow.run"
    run_id = f"wfrun_{uuid4().hex[:12]}"
    workflow = _normalize_workflow_payload(workflow)
    steps = workflow.get("steps", [])
    if not isinstance(steps, list):
        return _failed_result(
            run_id,
            error=AgentPDFError(
                code="unsafe_input_rejected",
                message="Workflow must contain a list of steps.",
            ),
            step_results=[],
        )

    step_results: list[dict[str, Any]] = []
    artifacts: list[Artifact] = []
    warnings: list[str] = []
    executed_steps = 0
    failed_steps = 0
    artifact_dir = Path(str(workflow.get("artifact_dir") or f".agentpdf-out/workflows/{run_id}"))
    bindings = _initial_bindings(workflow)

    for index, step in enumerate(steps, start=1):
        step_result = _prepare_step(step, index)
        if step_result["status"] == "failed":
            failed_steps += 1
            step_results.append(step_result)
            return _failed_result(
                run_id,
                error=AgentPDFError(
                    code=str(step_result["error"]["code"]),
                    message=str(step_result["error"]["message"]),
                ),
                step_results=step_results,
                artifacts=artifacts,
                warnings=warnings,
                executed_steps=executed_steps,
                failed_steps=failed_steps,
                dry_run=dry_run,
                planned_steps=len(steps),
            )

        if dry_run:
            step_result["status"] = "planned"
            step_results.append(step_result)
            continue

        _auto_bind_placeholders(step_result["input"], bindings=bindings, artifact_dir=artifact_dir)
        step_result["input"] = _resolve_placeholders(step_result["input"], bindings)
        unresolved = _find_unresolved_placeholder(step_result["input"])
        if unresolved:
            failed_steps += 1
            step_result["status"] = "failed"
            step_result["error"] = {
                "code": "unsafe_input_rejected",
                "message": f"Workflow step contains unresolved placeholder: {unresolved}",
            }
            step_results.append(step_result)
            return _failed_result(
                run_id,
                error=AgentPDFError(
                    code="unsafe_input_rejected",
                    message=f"Workflow step contains unresolved placeholder: {unresolved}",
                ),
                step_results=step_results,
                artifacts=artifacts,
                warnings=warnings,
                executed_steps=executed_steps,
                failed_steps=failed_steps,
                dry_run=dry_run,
                planned_steps=len(steps),
            )

        result = _run_local_step(step_result["tool"], step_result["input"])
        executed_steps += 1
        artifacts.extend(result.artifacts)
        warnings.extend(result.warnings)
        _record_result_bindings(step_result["tool"], result, bindings)
        step_result.update(_summarize_result(result))
        step_results.append(step_result)
        if result.status == "failed":
            failed_steps += 1
            return _failed_result(
                run_id,
                error=result.error
                or AgentPDFError(
                    code="output_validation_failed",
                    message=f"Workflow step failed: {step_result['tool']}",
                ),
                step_results=step_results,
                artifacts=artifacts,
                warnings=warnings,
                executed_steps=executed_steps,
                failed_steps=failed_steps,
                dry_run=dry_run,
                planned_steps=len(steps),
            )

    workflow_run = _workflow_usage(
        run_id=run_id,
        status="succeeded",
        dry_run=dry_run,
        planned_steps=len(steps),
        executed_steps=executed_steps,
        failed_steps=failed_steps,
        step_results=step_results,
        bindings=bindings,
    )
    return ToolResult(
        job_id=f"job_{uuid4().hex[:16]}",
        status="succeeded",
        tool=tool,
        artifacts=artifacts,
        warnings=warnings,
        usage={"workflow_run": workflow_run},
        next_recommended_tools=["pdf.workflow.report", "pdf.validation.validate_output"],
    )


def _prepare_step(step: Any, index: int) -> dict[str, Any]:
    if not isinstance(step, Mapping):
        return _failed_step(
            step_id=f"step_{index}",
            tool="",
            message="Workflow step must be an object.",
            code="unsafe_input_rejected",
        )
    tool = str(step.get("tool", ""))
    step_id = str(step.get("step_id") or f"step_{index}")
    payload = step.get("input", step.get("payload", {}))
    if tool not in SUPPORTED_LOCAL_WORKFLOW_TOOLS:
        return _failed_step(
            step_id=step_id,
            tool=tool,
            message=f"Workflow tool is not available in local runner: {tool}",
            code="tool_not_implemented",
        )
    if not isinstance(payload, Mapping):
        return _failed_step(
            step_id=step_id,
            tool=tool,
            message=f"Workflow step input must be an object: {step_id}",
            code="unsafe_input_rejected",
        )
    return {
        "step_id": step_id,
        "agent": step.get("agent"),
        "tool": tool,
        "status": "ready",
        "input": dict(payload),
        "job_id": None,
        "warnings": [],
        "artifact_ids": [],
        "next_recommended_tools": [],
    }


def _failed_step(step_id: str, tool: str, message: str, code: str) -> dict[str, Any]:
    return {
        "step_id": step_id,
        "agent": None,
        "tool": tool,
        "status": "failed",
        "input": {},
        "job_id": None,
        "warnings": [message],
        "artifact_ids": [],
        "next_recommended_tools": [],
        "error": {"code": code, "message": message},
    }


def _run_local_step(tool: str, payload: dict[str, Any]) -> ToolResult:
    from agentpdf.tools import runner

    if tool == "pdf.authoring.plan":
        return runner.run_authoring_plan(brief=dict(payload.get("brief", {})))
    if tool == "pdf.research.plan":
        return runner.run_research_plan(brief=dict(payload.get("brief", {})))
    if tool == "pdf.research.source_cards":
        sources = payload.get("sources")
        brief = payload.get("brief")
        return runner.run_research_source_cards(
            sources=sources if isinstance(sources, list) else None,
            brief=brief if isinstance(brief, dict) else None,
        )
    if tool == "pdf.research.evidence_cards":
        source_cards = payload.get("source_cards")
        return runner.run_research_evidence_cards(
            source_cards=source_cards if isinstance(source_cards, list) else None,
        )
    if tool == "pdf.design.tokens":
        overrides = payload.get("overrides")
        return runner.run_design_tokens(
            theme=str(payload.get("theme", "business_tech")),
            overrides=overrides if isinstance(overrides, dict) else None,
        )
    if tool == "pdf.storyboard.plan":
        authoring_plan = payload.get("authoring_plan")
        evidence_cards = payload.get("evidence_cards")
        return runner.run_storyboard_plan(
            brief=dict(payload.get("brief", {})),
            authoring_plan=authoring_plan if isinstance(authoring_plan, dict) else None,
            evidence_cards=evidence_cards if isinstance(evidence_cards, list) else None,
        )
    if tool == "pdf.pages.write":
        evidence_cards = payload.get("evidence_cards")
        design_tokens = payload.get("design_tokens")
        return runner.run_pages_write(
            brief=dict(payload.get("brief", {})),
            storyboard=dict(payload.get("storyboard", {})),
            evidence_cards=evidence_cards if isinstance(evidence_cards, list) else None,
            design_tokens=design_tokens if isinstance(design_tokens, dict) else None,
        )
    if tool == "pdf.pages.revise":
        revisions = payload.get("revisions")
        design_tokens = payload.get("design_tokens")
        return runner.run_pages_revise(
            page_document=dict(payload.get("page_document", {})),
            revisions=revisions if isinstance(revisions, list) else None,
            design_tokens=design_tokens if isinstance(design_tokens, dict) else None,
        )
    if tool == "pdf.create.html_package":
        page_document = payload.get("page_document")
        return runner.run_create_html_package(
            page_document=page_document if isinstance(page_document, dict) else None,
            html_output_path=payload.get("html_output_path", "deck.html"),
            title=str(payload["title"]) if payload.get("title") is not None else None,
            html=str(payload["html"]) if payload.get("html") is not None else None,
            html_path=payload.get("html_path") or payload.get("html_input_path"),
        )
    if tool == "pdf.render.html_package":
        return runner.run_render_html_package(
            package_path=payload.get("package_path", payload.get("input_path", "")),
            output_path=payload.get("output_path", "deck.pdf"),
        )
    if tool == "pdf.qa.visual_report":
        expected_page_count, error = _coerce_optional_int(
            payload.get("expected_page_count"),
            field_name="expected_page_count",
            tool=tool,
        )
        if error is not None:
            return error
        return runner.run_qa_visual_report(
            input_path=payload.get("input_path", payload.get("path", "")),
            expected_page_count=expected_page_count,
            html_package_manifest_path=payload.get("html_package_manifest_path"),
            pages=str(payload.get("pages", "all")),
        )
    if tool == "pdf.workflow.createpdf":
        page_document = payload.get("page_document")
        expected_page_count, error = _coerce_optional_int(
            payload.get("expected_page_count"),
            field_name="expected_page_count",
            tool=tool,
        )
        if error is not None:
            return error
        return runner.run_workflow_createpdf(
            pdf_output_path=payload.get("pdf_output_path", "createpdf.pdf"),
            html_output_path=payload.get("html_output_path"),
            html=str(payload["html"]) if payload.get("html") is not None else None,
            html_path=payload.get("html_path") or payload.get("html_input_path"),
            page_document=page_document if isinstance(page_document, dict) else None,
            title=str(payload["title"]) if payload.get("title") is not None else None,
            artifact_dir=payload.get("artifact_dir"),
            expected_page_count=expected_page_count,
            pages=str(payload.get("pages", "all")),
        )
    if tool == "office.inspect.file":
        return runner.run_office_inspect_file(payload.get("path", payload.get("input_path", "")))
    if tool == "office.context.build_packet":
        files = payload.get("files", payload.get("input_paths", payload.get("paths", [])))
        return runner.run_office_context_build_packet(
            files=files if isinstance(files, list) else [],
            output_path=payload.get("output_path", payload.get("output", ".okoffice-out/context.packet.json")),
            title=str(payload["title"]) if payload.get("title") is not None else None,
            intent=str(payload["intent"]) if payload.get("intent") is not None else None,
        )
    if tool == "office.extract.schema":
        return runner.run_office_extract_schema(
            context_packet=payload.get("context_packet") or payload.get("context_packet_path", ""),
            schema=payload.get("schema", {}),
            output_path=payload.get("output_path", payload.get("output")),
        )
    if tool == "office.validation.package":
        return runner.run_office_validation_package(payload.get("path", payload.get("input_path", "")))
    if tool == "office.workflow.docset_to_sheet":
        files = payload.get("files", payload.get("input_paths", payload.get("paths", [])))
        return runner.run_office_workflow_docset_to_sheet(
            files=files if isinstance(files, list) else [],
            schema=payload.get("schema", {}),
            output_path=payload.get("output_path", payload.get("output", ".okoffice-out/evidence.xlsx")),
            title=str(payload["title"]) if payload.get("title") is not None else None,
            intent=str(payload["intent"]) if payload.get("intent") is not None else None,
            context_output_path=payload.get("context_output_path"),
            evidence_output_path=payload.get("evidence_output_path"),
        )
    if tool == "office.workflow.extract_to_sheet":
        input_paths = payload.get("input_paths", payload.get("files", payload.get("paths", [])))
        return runner.run_office_workflow_extract_to_sheet(
            input_paths=input_paths if isinstance(input_paths, list) else [],
            output_path=payload.get("output_path", payload.get("output", ".okoffice-out/evidence.xlsx")),
            context_packet_path=payload.get("context_packet_path"),
        )
    if tool == "office.workflow.sheet_to_deck":
        return runner.run_office_workflow_sheet_to_deck(
            workbook_path=payload.get("workbook_path", payload.get("path", payload.get("input_path", ""))),
            output_path=payload.get("output_path", payload.get("output", ".okoffice-out/deck.pptx")),
            title=str(payload["title"]) if payload.get("title") is not None else None,
            max_rows_per_sheet=int(payload.get("max_rows_per_sheet", payload.get("max_rows", 100))),
        )
    if tool == "office.workflow.board_pack":
        files = payload.get("files", payload.get("input_paths", payload.get("paths", [])))
        return runner.run_office_workflow_board_pack(
            files=files if isinstance(files, list) else [],
            output_path=payload.get("output_path", payload.get("output", ".okoffice-out/board-pack.zip")),
            title=str(payload["title"]) if payload.get("title") is not None else None,
        )
    if tool == "office.workers.status":
        feature_flags = payload.get("feature_flags")
        command_paths = payload.get("command_paths")
        return runner.run_office_workers_status(
            feature_flags=feature_flags if isinstance(feature_flags, dict) else None,
            command_paths=command_paths if isinstance(command_paths, dict) else None,
        )
    if tool == "office.bundle.export":
        artifact_paths = payload.get("artifact_paths", payload.get("files", payload.get("paths", [])))
        return runner.run_office_bundle_export(
            artifact_paths=artifact_paths if isinstance(artifact_paths, list) else [],
            output_path=payload.get("output_path", payload.get("output", ".okoffice-out/artifacts.okoffice.zip")),
            title=str(payload["title"]) if payload.get("title") is not None else None,
            metadata=payload.get("metadata") if isinstance(payload.get("metadata"), dict) else None,
        )
    if tool == "office.bundle.verify":
        return runner.run_office_bundle_verify(
            payload.get("bundle_path", payload.get("path", payload.get("input_path", ""))),
        )
    if tool == "word.inspect.document":
        return runner.run_word_inspect_document(payload.get("path", payload.get("input_path", "")))
    if tool == "word.extract.tables":
        return runner.run_word_extract_tables(payload.get("path", payload.get("input_path", "")))
    if tool == "word.validation.document":
        return runner.run_word_validate_document(payload.get("path", payload.get("input_path", "")))
    if tool == "word.create.report":
        return runner.run_word_create_report(
            workbook_path=payload.get("workbook_path", payload.get("from_workbook", payload.get("input_path"))),
            output_path=payload.get("output_path", payload.get("output")),
            title=str(payload["title"]) if payload.get("title") is not None else None,
            profile=str(payload.get("profile", "executive_memo")),
        )
    if tool == "word.patch.plan":
        operations = payload.get("operations")
        return runner.run_word_patch_plan(
            input_path=payload.get("input_path", payload.get("path", "")),
            operations=operations if isinstance(operations, list) else [],
        )
    if tool == "word.patch.apply":
        operations = payload.get("operations")
        return runner.run_word_patch_apply(
            input_path=payload.get("input_path", payload.get("path", "")),
            output_path=payload.get("output_path", payload.get("output", "")),
            operations=operations if isinstance(operations, list) else [],
        )
    if tool == "sheet.inspect.workbook":
        return runner.run_sheet_inspect_workbook(payload.get("path", payload.get("input_path", "")))
    if tool == "sheet.read.workbook":
        return runner.run_sheet_read_workbook(
            payload.get("path", payload.get("input_path", "")),
            max_rows_per_sheet=int(payload.get("max_rows_per_sheet", payload.get("max_rows", 100))),
        )
    if tool == "sheet.profile.data":
        return runner.run_sheet_profile_data(
            payload.get("path", payload.get("input_path", "")),
            max_rows_per_sheet=int(payload.get("max_rows_per_sheet", payload.get("max_rows", 100))),
            include_source_refs=bool(payload.get("include_source_refs", False)),
        )
    if tool == "sheet.extract.tables":
        return runner.run_sheet_extract_tables(payload.get("path", payload.get("input_path", "")))
    if tool == "sheet.create.evidence_workbook":
        data = payload.get("data", payload)
        return runner.run_sheet_create_evidence_workbook(
            data=data if isinstance(data, (dict, list)) else {},
            output_path=payload.get("output_path", payload.get("output", ".okoffice-out/evidence.xlsx")),
        )
    if tool == "sheet.write.workbook":
        data = payload.get("data", payload)
        return runner.run_sheet_write_workbook(
            data=data if isinstance(data, (dict, list)) else {},
            output_path=payload.get("output_path", payload.get("output", ".okoffice-out/workbook.xlsx")),
            evidence_path=payload.get("evidence_path"),
            evidence=payload.get("evidence") if isinstance(payload.get("evidence"), dict) else None,
        )
    if tool == "sheet.validate.workbook":
        return runner.run_sheet_validate_workbook(payload.get("path", payload.get("input_path", "")))
    if tool == "sheet.validation.formulas":
        return runner.run_sheet_validate_formulas(payload.get("path", payload.get("input_path", "")))
    if tool == "deck.create.from_outline":
        outline = payload.get("outline", payload)
        return runner.run_deck_create_from_outline(
            outline=outline if isinstance(outline, dict) else {},
            output_path=payload.get("output_path", payload.get("output", ".okoffice-out/deck.pptx")),
        )
    if tool == "deck.create.presentation":
        return runner.run_deck_create_presentation(
            workbook_path=payload.get("workbook_path", payload.get("from_workbook", payload.get("input_path"))),
            output_path=payload.get("output_path", payload.get("output")),
            title=str(payload["title"]) if payload.get("title") is not None else None,
            profile=str(payload.get("profile", "board_review")),
            style=payload.get("style") if isinstance(payload.get("style"), dict) else None,
        )
    if tool == "deck.patch.apply":
        operations = payload.get("operations")
        return runner.run_deck_patch_apply(
            input_path=payload.get("input_path", payload.get("path", "")),
            output_path=payload.get("output_path", payload.get("output", "")),
            operations=operations if isinstance(operations, list) else [],
        )
    if tool == "deck.compose.plan":
        return runner.run_deck_compose_plan(
            workbook_path=payload.get("workbook_path", payload.get("path", payload.get("input_path", ""))),
            output_path=payload.get("output_path", payload.get("output")),
            title=str(payload["title"]) if payload.get("title") is not None else None,
            style=str(payload.get("style", "executive")),
            max_rows_per_sheet=int(payload.get("max_rows_per_sheet", payload.get("max_rows", 100))),
        )
    if tool == "deck.inspect.presentation":
        return runner.run_deck_inspect_presentation(payload.get("path", payload.get("input_path", "")))
    if tool == "deck.validation.contact_sheet":
        return runner.run_deck_validation_contact_sheet(payload.get("path", payload.get("input_path", "")))
    if tool == "deck.validation.presentation":
        return runner.run_deck_validation_presentation(payload.get("path", payload.get("input_path", "")))
    if tool == "deck.validate.presentation":
        return runner.run_deck_validate_presentation(payload.get("path", payload.get("input_path", "")))
    if tool == "pdf.inspect.document":
        return runner.run_inspect(payload.get("path", payload.get("input_path", "")))
    if tool == "pdf.inspect.pages":
        return runner.run_inspect_pages(
            payload.get("input_path", payload.get("path", "")),
            pages=str(payload.get("pages", "all")),
            render_check=bool(payload.get("render_check", False)),
        )
    if tool == "pdf.organize.merge":
        return runner.run_merge(payload.get("input_paths", []), payload.get("output_path", ""))
    if tool == "pdf.organize.split":
        return runner.run_split(
            payload.get("input_path", ""),
            pages=str(payload.get("pages", "")),
            output_path=payload.get("output_path", ""),
        )
    if tool == "pdf.organize.extract_pages":
        return runner.run_extract_pages(
            payload.get("input_path", ""),
            pages=str(payload.get("pages", "")),
            output_path=payload.get("output_path", ""),
        )
    if tool == "pdf.organize.remove_pages":
        return runner.run_remove_pages(
            payload.get("input_path", ""),
            pages=str(payload.get("pages", "")),
            output_path=payload.get("output_path", ""),
        )
    if tool == "pdf.organize.rotate_pages":
        return runner.run_rotate_pages(
            payload.get("input_path", ""),
            pages=str(payload.get("pages", "")),
            degrees=int(payload.get("degrees", 0)),
            output_path=payload.get("output_path", ""),
        )
    if tool == "pdf.organize.reorder_pages":
        return runner.run_reorder_pages(
            payload.get("input_path", ""),
            order=str(payload.get("order", "")),
            output_path=payload.get("output_path", ""),
        )
    if tool == "pdf.organize.insert_blank_pages":
        return runner.run_insert_blank_pages(
            payload.get("input_path", ""),
            after_page=int(payload.get("after_page", 0)),
            count=int(payload.get("count", 1)),
            output_path=payload.get("output_path", ""),
        )
    if tool == "pdf.optimize.compress":
        return runner.run_compress(payload.get("input_path", ""), payload.get("output_path", ""))
    if tool == "pdf.optimize.repair":
        return runner.run_repair(payload.get("input_path", ""), payload.get("output_path", ""))
    if tool == "pdf.convert.image_to_pdf":
        return runner.run_image_to_pdf(
            payload.get("image_paths", []),
            output_path=payload.get("output_path", ""),
        )
    if tool == "pdf.convert.markdown_to_pdf":
        return runner.run_create_markdown(
            str(payload.get("markdown", "")),
            output_path=payload.get("output_path", ""),
            title=payload.get("title"),
            style_pack=str(payload.get("style_pack", "plain_report")),
        )
    if tool == "pdf.convert.text_to_pdf":
        return runner.run_create_text(
            str(payload.get("text", "")),
            output_path=payload.get("output_path", ""),
            title=payload.get("title"),
        )
    if tool == "pdf.convert.extract_images":
        return runner.run_extract_images(
            payload.get("input_path", ""),
            pages=str(payload.get("pages", "all")),
            out_dir=payload.get("out_dir", "extracted-images"),
        )
    if tool == "pdf.convert.pdf_to_images":
        return runner.run_render(
            payload.get("input_path", ""),
            pages=str(payload.get("pages", "")),
            image_format=str(payload.get("image_format", "png")),
            out_dir=payload.get("out_dir", "renders"),
        )
    if tool == "pdf.convert.pdf_to_text":
        return runner.run_extract_text(
            payload.get("input_path", ""),
            pages=str(payload.get("pages", "all")),
        )
    if tool == "pdf.convert.pdf_to_json":
        return runner.run_pdf_to_json(
            payload.get("input_path", ""),
            output_path=payload.get("output_path", ""),
            pages=str(payload.get("pages", "all")),
        )
    if tool == "pdf.convert.pdf_to_markdown":
        return runner.run_pdf_to_markdown(
            payload.get("input_path", ""),
            output_path=payload.get("output_path", ""),
            pages=str(payload.get("pages", "all")),
        )
    if tool == "pdf.edit.watermark":
        return runner.run_watermark(
            payload.get("input_path", ""),
            text=str(payload.get("text", "")),
            output_path=payload.get("output_path", ""),
            pages=str(payload.get("pages", "all")),
            font_size=int(payload.get("font_size", 48)),
            opacity=float(payload.get("opacity", 0.18)),
            angle=int(payload.get("angle", 45)),
        )
    if tool == "pdf.edit.page_numbers":
        return runner.run_page_numbers(
            payload.get("input_path", ""),
            output_path=payload.get("output_path", ""),
            pages=str(payload.get("pages", "all")),
            template=str(payload.get("template", "{page}")),
            font_size=int(payload.get("font_size", 10)),
        )
    if tool == "pdf.metadata.read":
        return runner.run_metadata_read(payload.get("input_path", payload.get("path", "")))
    if tool == "pdf.metadata.update":
        return runner.run_metadata_update(
            payload.get("input_path", ""),
            metadata=dict(payload.get("metadata", {})),
            output_path=payload.get("output_path", ""),
        )
    if tool == "pdf.metadata.remove":
        return runner.run_metadata_remove(
            payload.get("input_path", ""),
            output_path=payload.get("output_path", ""),
        )
    if tool == "pdf.validation.validate_output":
        expected_pages = payload.get("expected_pages")
        return runner.run_validate_output(
            payload.get("path", payload.get("input_path", "")),
            expected_pages=int(expected_pages) if expected_pages is not None else None,
        )
    if tool == "pdf.validation.render_check":
        return runner.run_render_check(
            payload.get("path", payload.get("input_path", "")),
            pages=str(payload.get("pages", "all")),
        )
    if tool == "pdf.validation.blank_page_check":
        return runner.run_blank_page_check(
            payload.get("path", payload.get("input_path", "")),
            pages=str(payload.get("pages", "all")),
        )
    if tool == "pdf.ai.parse.lite":
        return runner.run_parse_lite(
            payload.get("input_path", ""),
            pages=str(payload.get("pages", "all")),
        )
    if tool == "pdf.ai.rag.ingest":
        return runner.run_rag_ingest(
            payload.get("input_path", ""),
            index_path=payload.get("index_path", ""),
            pages=str(payload.get("pages", "all")),
            max_chars=int(payload.get("max_chars", 1200)),
            overlap_chars=int(payload.get("overlap_chars", 120)),
        )
    if tool == "pdf.ai.rag.query":
        return runner.run_rag_query(
            payload.get("index_path", ""),
            query=str(payload.get("query", "")),
            top_k=int(payload.get("top_k", 5)),
        )
    if tool == "pdf.ai.rag.chat":
        return runner.run_rag_chat(
            payload.get("input_path", ""),
            question=str(payload.get("question", "")),
            index_path=payload.get("index_path"),
            report_output_path=payload.get("report_output_path"),
            highlight_output_path=payload.get("highlight_output_path"),
            pages=str(payload.get("pages", "all")),
            top_k=int(payload.get("top_k", 5)),
            max_chars=int(payload.get("max_chars", 1200)),
            overlap_chars=int(payload.get("overlap_chars", 120)),
            style_pack=str(payload.get("style_pack", "plain_report")),
            highlight_color=str(payload.get("highlight_color", "fff59d")),
        )
    if tool == "pdf.ai.rag.search":
        return runner.run_rag_search(
            payload.get("index_path", ""),
            query=str(payload.get("query", "")),
            top_k=int(payload.get("top_k", 5)),
        )
    if tool == "pdf.ai.rag.cite_answer":
        return runner.run_rag_cite_answer(
            payload.get("index_path", ""),
            answer=str(payload.get("answer", "")),
            top_k=int(payload.get("top_k", 5)),
        )
    if tool == "pdf.ai.rag.highlight_sources":
        return runner.run_rag_highlight_sources(
            payload.get("index_path", ""),
            output_path=payload.get("output_path", ""),
            answer=payload.get("answer"),
            query=payload.get("query"),
            top_k=int(payload.get("top_k", 5)),
            highlight_color=str(payload.get("highlight_color", "fff59d")),
        )
    if tool == "pdf.ai.rag.export_report":
        return runner.run_rag_export_report(
            payload.get("index_path", ""),
            output_path=payload.get("output_path", ""),
            question=str(payload.get("question", "")),
            answer=payload.get("answer"),
            top_k=int(payload.get("top_k", 5)),
            include_citations=bool(payload.get("include_citations", True)),
            title=payload.get("title"),
            style_pack=str(payload.get("style_pack", "plain_report")),
        )
    return ToolResult(
        job_id=f"job_{uuid4().hex[:16]}",
        status="failed",
        tool=tool,
        error=AgentPDFError(
            code="tool_not_implemented",
            message=f"No local workflow runner is registered for tool: {tool}",
        ),
        warnings=[f"No local workflow runner is registered for tool: {tool}"],
    )


def _summarize_result(result: ToolResult) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "status": result.status,
        "job_id": result.job_id,
        "warnings": result.warnings,
        "artifact_ids": [artifact.artifact_id for artifact in result.artifacts],
        "next_recommended_tools": result.next_recommended_tools,
    }
    if result.error:
        summary["error"] = {
            "code": result.error.code,
            "message": result.error.message,
        }
    if result.validation:
        summary["validation"] = result.validation.model_dump(mode="json")
    return summary


def _initial_bindings(workflow: Mapping[str, Any]) -> dict[str, Any]:
    raw_bindings = workflow.get("bindings", {})
    bindings: dict[str, Any] = {}
    if isinstance(raw_bindings, Mapping):
        bindings.update({str(key): value for key, value in raw_bindings.items()})
    input_path = workflow.get("input_path")
    if input_path:
        bindings.setdefault("<input.pdf>", str(input_path))
        bindings.setdefault("<final.pdf>", str(input_path))
        bindings.setdefault("<compressed-or-input.pdf>", str(input_path))
    return bindings


def _auto_bind_placeholders(
    value: Any,
    bindings: dict[str, Any],
    artifact_dir: Path,
) -> None:
    for placeholder in _collect_placeholders(value):
        if placeholder in bindings:
            continue
        generated = _generated_placeholder_value(placeholder, bindings, artifact_dir)
        if generated is not None:
            bindings[placeholder] = generated


def _collect_placeholders(value: Any) -> set[str]:
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("<") and stripped.endswith(">"):
            return {stripped}
        return set()
    if isinstance(value, Mapping):
        placeholders: set[str] = set()
        for child in value.values():
            placeholders.update(_collect_placeholders(child))
        return placeholders
    if isinstance(value, list):
        placeholders = set()
        for child in value:
            placeholders.update(_collect_placeholders(child))
        return placeholders
    return set()


def _generated_placeholder_value(
    placeholder: str,
    bindings: dict[str, Any],
    artifact_dir: Path,
) -> Any | None:
    if placeholder == "<final.pdf>":
        return bindings.get("<last.pdf>") or bindings.get("<input.pdf>")
    if placeholder == "<compressed-or-input.pdf>":
        return bindings.get("<compressed.pdf>") or bindings.get("<input.pdf>")

    filename_by_placeholder = {
        "<output.index.json>": "output.index.json",
        "<compressed.pdf>": "compressed.pdf",
        "<repaired.pdf>": "repaired.pdf",
        "<output.pdf>": "output.pdf",
        "<deck.html>": "deck.html",
        "<deck.pdf>": "deck.pdf",
        "<highlighted.pdf>": "highlighted.pdf",
        "<rag-report.pdf>": "rag-report.pdf",
    }
    if placeholder in filename_by_placeholder:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        return str(artifact_dir / filename_by_placeholder[placeholder])

    if placeholder == "<images-dir>":
        image_dir = artifact_dir / "images"
        image_dir.mkdir(parents=True, exist_ok=True)
        return str(image_dir)
    return None


def _resolve_placeholders(value: Any, bindings: dict[str, Any]) -> Any:
    if isinstance(value, str):
        return bindings.get(value.strip(), value)
    if isinstance(value, Mapping):
        return {key: _resolve_placeholders(child, bindings) for key, child in value.items()}
    if isinstance(value, list):
        return [_resolve_placeholders(child, bindings) for child in value]
    return value


def _record_result_bindings(tool: str, result: ToolResult, bindings: dict[str, Any]) -> None:
    if tool == "pdf.authoring.plan":
        plan = result.usage.get("authoring_plan", {})
        if isinstance(plan, Mapping):
            bindings["<authoring_plan>"] = dict(plan)
    if tool == "pdf.storyboard.plan":
        storyboard = result.usage.get("storyboard", {})
        if isinstance(storyboard, Mapping):
            bindings["<storyboard>"] = dict(storyboard)
    if tool == "pdf.pages.write":
        page_document = result.usage.get("page_document", {})
        if isinstance(page_document, Mapping):
            bindings["<page_document>"] = dict(page_document)
    if tool == "pdf.create.html_package":
        manifest_path = result.usage.get("html_package_manifest_path")
        if manifest_path:
            bindings["<html_package_manifest_path>"] = str(manifest_path)
    if tool == "pdf.render.html_package":
        if result.validation and result.validation.page_count is not None:
            bindings["<rendered_page_count>"] = result.validation.page_count
        if result.artifacts:
            bindings["<final.pdf>"] = str(result.artifacts[0].path)
    for artifact in result.artifacts:
        path = str(artifact.path)
        if artifact.mime_type == "application/pdf":
            bindings["<last.pdf>"] = path
            bindings["<final.pdf>"] = path
        if tool == "pdf.ai.rag.ingest" and artifact.mime_type == "application/json":
            bindings.setdefault("<output.index.json>", path)
        if tool == "pdf.optimize.compress" and artifact.mime_type == "application/pdf":
            bindings["<compressed.pdf>"] = path
            bindings["<compressed-or-input.pdf>"] = path
        if tool == "pdf.optimize.repair" and artifact.mime_type == "application/pdf":
            bindings["<repaired.pdf>"] = path
        if tool == "pdf.ai.rag.export_report" and artifact.mime_type == "application/pdf":
            bindings["<rag-report.pdf>"] = path


def _find_unresolved_placeholder(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("<") and stripped.endswith(">"):
            return stripped
        return None
    if isinstance(value, Mapping):
        for child in value.values():
            found = _find_unresolved_placeholder(child)
            if found:
                return found
    if isinstance(value, list):
        for child in value:
            found = _find_unresolved_placeholder(child)
            if found:
                return found
    return None


def _coerce_optional_int(value: Any, field_name: str, tool: str) -> tuple[int | None, ToolResult | None]:
    if value is None:
        return None, None
    try:
        return int(value), None
    except (TypeError, ValueError):
        message = f"{field_name} must be an integer."
        return None, ToolResult(
            job_id=f"job_{uuid4().hex[:16]}",
            status="failed",
            tool=tool,
            error=AgentPDFError(code="unsafe_input_rejected", message=message),
            warnings=[message],
        )


def _failed_result(
    run_id: str,
    error: AgentPDFError,
    step_results: list[dict[str, Any]],
    artifacts: list[Artifact] | None = None,
    warnings: list[str] | None = None,
    bindings: dict[str, Any] | None = None,
    executed_steps: int = 0,
    failed_steps: int = 1,
    dry_run: bool = False,
    planned_steps: int | None = None,
) -> ToolResult:
    all_warnings = list(warnings or [])
    all_warnings.append(error.message)
    return ToolResult(
        job_id=f"job_{uuid4().hex[:16]}",
        status="failed",
        tool="pdf.workflow.run",
        artifacts=artifacts or [],
        warnings=all_warnings,
        usage={
            "workflow_run": _workflow_usage(
                run_id=run_id,
                status="failed",
                dry_run=dry_run,
                planned_steps=planned_steps if planned_steps is not None else len(step_results),
                executed_steps=executed_steps,
                failed_steps=failed_steps,
                step_results=step_results,
                bindings=bindings or {},
            )
        },
        next_recommended_tools=["pdf.workflow.plan"],
        error=error,
    )


def _workflow_usage(
    run_id: str,
    status: str,
    dry_run: bool,
    planned_steps: int,
    executed_steps: int,
    failed_steps: int,
    step_results: list[dict[str, Any]],
    bindings: dict[str, Any],
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "status": status,
        "dry_run": dry_run,
        "planned_steps": planned_steps,
        "executed_steps": executed_steps,
        "failed_steps": failed_steps,
        "bindings": dict(sorted(bindings.items())),
        "step_results": step_results,
    }
