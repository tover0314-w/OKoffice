from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.responses import JSONResponse

from agentpdf.schemas.errors import AgentPDFException
from agentpdf.schemas.models import AgentPDFError, ToolResult
from agentpdf.tools.registry import get_tool, load_tool_manifest
from agentpdf.tools.runner import (
    run_add_margin,
    run_add_shape,
    run_underlay,
    run_agent_setup_claude_code,
    run_agent_setup_codex,
    run_agent_setup_kilo_code,
    run_agent_setup_openclaw,
    run_artifacts_export_bundle,
    run_artifacts_graph,
    run_artifacts_manifest,
    run_artifacts_source_map,
    run_artifacts_verify_bundle,
    run_blank_page_check,
    run_booklet,
    run_build_context_packet,
    run_compose_add_appendix,
    run_compose_add_citation,
    run_compose_add_code_block,
    run_compose_add_figure,
    run_compose_add_media_reference,
    run_compose_add_slide,
    run_compose_add_table,
    run_compose_from_context,
    run_compose_plan,
    run_compose_render_ir,
    run_compress,
    run_compare_semantic_diff,
    run_compare_visual_diff,
    run_compare_version_report,
    run_create_markdown,
    run_create_text,
    run_create_agent,
    run_create_from_prompt,
    run_create_from_template_pack,
    run_plan_template_pack_creation,
    run_create_template_preview,
    run_create_template_packs,
    run_create_templates,
    run_context_packet_report,
    run_context_classify,
    run_context_code_snapshot,
    run_context_data_profile,
    run_context_image_analyze,
    run_context_ingest,
    run_context_packet,
    run_validate_template_pack,
    run_evidence_cite_claims,
    run_evidence_coverage_report,
    run_evidence_map_sources,
    run_docx_to_pdf,
    run_extract_fonts,
    run_extract_images,
    run_extract_pages,
    run_extract_text,
    run_forms_create,
    run_forms_import_data,
    run_forms_validate,
    run_freehand_draw,
    run_html_to_pdf,
    run_image_to_pdf,
    run_inspect,
    run_inspect_health,
    run_inspect_pages,
    run_insert_blank_pages,
    run_metadata_read,
    run_metadata_page_info,
    run_metadata_remove,
    run_metadata_update,
    run_metadata_update_outline,
    run_merge,
    run_n_up,
    run_page_numbers,
    run_patch_apply,
    run_patch_plan,
    run_patch_preview,
    run_patch_verify,
    run_parse_charts,
    run_parse_figures,
    run_parse_formulas,
    run_parse_lite,
    run_parse_references,
    run_pdf_to_docx,
    run_pdf_to_html,
    run_pdf_to_markdown,
    run_pdf_to_pptx,
    run_pdf_to_xlsx,
    run_pdf_to_json,
    run_pptx_to_pdf,
    run_rag_chat,
    run_rag_cite_answer,
    run_rag_export_report,
    run_rag_highlight_sources,
    run_rag_ingest,
    run_rag_query,
    run_rag_search,
    run_remove_pages,
    run_render_html_package,
    run_remove_unused_objects,
    run_render,
    run_render_check,
    run_repair,
    run_reorder_pages,
    run_resize_pages,
    run_rotate_pages,
    run_page_count_check,
    run_ocr_despeckle,
    run_ocr,
    run_ocr_multilingual,
    run_ocr_remove_existing,
    run_ocr_scan_to_pdf,
    run_ocr_searchable_pdf,
    run_security_decrypt_authorized,
    run_security_encrypt,
    run_security_malware_scan,
    run_security_remove_metadata,
    run_security_protect,
    run_security_redact,
    run_security_sanitize,
    run_security_sign,
    run_security_unlock_authorized,
    run_security_verify_redaction,
    run_security_verify_signature,
    run_select_target_profile,
    run_split,
    run_strikeout,
    run_subset_fonts,
    run_target_profiles,
    run_underline,
    run_validate_output,
    run_validate_pdfa,
    run_validate_target_profile,
    run_validation_redaction_check,
    run_validation_visual_diff,
    run_to_pdfa,
    run_url_to_pdf,
    run_watermark,
    run_workflow_plan,
    run_workflow_report,
    run_workflow_run,
    run_xlsx_to_pdf,
)


def create_app() -> FastAPI:
    app = FastAPI(
        title="AgentPDF Local API",
        version="0.1.0",
        description="Local-first PDF tools for agents and developer workflows.",
    )
    app.state.jobs = {}
    app.state.artifacts = {}

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok", "service": "agentpdf"}

    @app.get("/v1/tools")
    def list_tools() -> dict[str, Any]:
        return load_tool_manifest().model_dump(mode="json")

    @app.get("/v1/tools/{tool_name:path}")
    def show_tool(tool_name: str) -> JSONResponse:
        try:
            return JSONResponse(get_tool(tool_name).model_dump(mode="json"))
        except AgentPDFException as exc:
            return _error_response(exc.to_error(), status_code=404)

    @app.post("/v1/tools/{tool_name:path}/run")
    def run_tool(tool_name: str, payload: dict[str, Any]) -> JSONResponse:
        result = _run_tool(tool_name, payload)
        _record_result(app, result)
        if result.status == "failed":
            return JSONResponse(result.model_dump(mode="json"), status_code=400)
        return JSONResponse(result.model_dump(mode="json"))

    @app.get("/v1/jobs/{job_id}")
    def show_job(job_id: str) -> JSONResponse:
        result = app.state.jobs.get(job_id)
        if result is None:
            return _error_response(
                AgentPDFError(code="file_not_found", message=f"Job not found: {job_id}"),
                status_code=404,
            )
        return JSONResponse(result.model_dump(mode="json"))

    @app.get("/v1/artifacts/{artifact_id}")
    def show_artifact(artifact_id: str) -> JSONResponse:
        artifact = app.state.artifacts.get(artifact_id)
        if artifact is None:
            return _error_response(
                AgentPDFError(code="file_not_found", message=f"Artifact not found: {artifact_id}"),
                status_code=404,
            )
        return JSONResponse(artifact.model_dump(mode="json"))

    @app.get("/v1/artifacts/{artifact_id}/download", response_model=None)
    def download_artifact(artifact_id: str):
        artifact = app.state.artifacts.get(artifact_id)
        if artifact is None:
            return _error_response(
                AgentPDFError(code="file_not_found", message=f"Artifact not found: {artifact_id}"),
                status_code=404,
            )
        if not artifact.path.exists():
            return _error_response(
                AgentPDFError(code="file_not_found", message=f"Artifact file missing: {artifact.path}"),
                status_code=404,
            )
        return FileResponse(artifact.path, media_type=artifact.mime_type, filename=artifact.path.name)

    return app


def _record_result(app: FastAPI, result: ToolResult) -> None:
    app.state.jobs[result.job_id] = result
    for artifact in result.artifacts:
        app.state.artifacts[artifact.artifact_id] = artifact


def _run_tool(tool_name: str, payload: dict[str, Any]) -> ToolResult:
    if tool_name == "agent.setup.claude_code":
        args_prefix = payload.get("args_prefix")
        return run_agent_setup_claude_code(
            output_path=payload.get("output_path"),
            safe_root=str(payload.get("safe_root", "${CLAUDE_PROJECT_DIR:-.}")),
            command=str(payload.get("command", "okpdf")),
            args_prefix=[str(arg) for arg in args_prefix] if isinstance(args_prefix, list) else None,
            server_name=str(payload.get("server_name", "agentpdf")),
            scope=str(payload.get("scope", "project")),
        )
    if tool_name == "agent.setup.codex":
        args_prefix = payload.get("args_prefix")
        return run_agent_setup_codex(
            output_path=payload.get("output_path"),
            safe_root=str(payload.get("safe_root", ".")),
            command=str(payload.get("command", "okpdf")),
            args_prefix=[str(arg) for arg in args_prefix] if isinstance(args_prefix, list) else None,
            server_name=str(payload.get("server_name", "agentpdf")),
        )
    if tool_name == "agent.setup.kilo_code":
        args_prefix = payload.get("args_prefix")
        return run_agent_setup_kilo_code(
            output_path=payload.get("output_path"),
            safe_root=str(payload.get("safe_root", ".")),
            command=str(payload.get("command", "okpdf")),
            args_prefix=[str(arg) for arg in args_prefix] if isinstance(args_prefix, list) else None,
            server_name=str(payload.get("server_name", "agentpdf")),
        )
    if tool_name == "agent.setup.openclaw":
        args_prefix = payload.get("args_prefix")
        return run_agent_setup_openclaw(
            output_path=payload.get("output_path"),
            safe_root=str(payload.get("safe_root", ".")),
            command=str(payload.get("command", "okpdf")),
            args_prefix=[str(arg) for arg in args_prefix] if isinstance(args_prefix, list) else None,
            server_name=str(payload.get("server_name", "agentpdf")),
        )
    if tool_name == "pdf.inspect.document":
        return run_inspect(payload.get("path", ""))
    if tool_name == "pdf.inspect.pages":
        return run_inspect_pages(
            payload.get("input_path", payload.get("path", "")),
            pages=str(payload.get("pages", "all")),
            render_check=bool(payload.get("render_check", False)),
        )
    if tool_name == "pdf.inspect.health":
        return run_inspect_health(payload.get("input_path", payload.get("path", "")))
    if tool_name == "pdf.workflow.plan":
        return run_workflow_plan(
            goal=str(payload.get("goal", "")),
            input_path=payload.get("input_path"),
        )
    if tool_name == "pdf.workflow.run":
        workflow = payload.get("workflow", payload)
        return run_workflow_run(
            workflow=workflow if isinstance(workflow, dict) else {},
            dry_run=bool(payload.get("dry_run", False)),
        )
    if tool_name == "pdf.workflow.report":
        workflow_run = payload.get("workflow_run", payload)
        return run_workflow_report(
            workflow_run=workflow_run if isinstance(workflow_run, dict) else {},
            output_path=payload.get("output_path"),
        )
    if tool_name == "pdf.organize.merge":
        return run_merge(payload.get("input_paths", []), payload.get("output_path", ""))
    if tool_name == "pdf.organize.split":
        return run_split(
            payload.get("input_path", ""),
            pages=str(payload.get("pages", "")),
            output_path=payload.get("output_path", ""),
        )
    if tool_name == "pdf.organize.extract_pages":
        return run_extract_pages(
            payload.get("input_path", ""),
            pages=str(payload.get("pages", "")),
            output_path=payload.get("output_path", ""),
        )
    if tool_name == "pdf.organize.remove_pages":
        return run_remove_pages(
            payload.get("input_path", ""),
            pages=str(payload.get("pages", "")),
            output_path=payload.get("output_path", ""),
        )
    if tool_name == "pdf.organize.rotate_pages":
        return run_rotate_pages(
            payload.get("input_path", ""),
            pages=str(payload.get("pages", "")),
            degrees=int(payload.get("degrees", 0)),
            output_path=payload.get("output_path", ""),
        )
    if tool_name == "pdf.organize.reorder_pages":
        return run_reorder_pages(
            payload.get("input_path", ""),
            order=str(payload.get("order", "")),
            output_path=payload.get("output_path", ""),
        )
    if tool_name == "pdf.organize.insert_blank_pages":
        return run_insert_blank_pages(
            payload.get("input_path", ""),
            after_page=int(payload.get("after_page", 0)),
            count=int(payload.get("count", 1)),
            output_path=payload.get("output_path", ""),
        )
    if tool_name == "pdf.organize.n_up":
        return run_n_up(
            payload.get("input_path", ""),
            output_path=payload.get("output_path", ""),
            pages=str(payload.get("pages", "all")),
            per_sheet=int(payload.get("per_sheet", 2)),
        )
    if tool_name == "pdf.organize.booklet":
        return run_booklet(
            payload.get("input_path", ""),
            output_path=payload.get("output_path", ""),
            pages=str(payload.get("pages", "all")),
        )
    if tool_name == "pdf.optimize.compress":
        return run_compress(
            payload.get("input_path", ""),
            output_path=payload.get("output_path", ""),
        )
    if tool_name == "pdf.optimize.repair":
        return run_repair(
            payload.get("input_path", ""),
            output_path=payload.get("output_path", ""),
        )
    if tool_name == "pdf.optimize.remove_unused_objects":
        return run_remove_unused_objects(
            payload.get("input_path", ""),
            output_path=payload.get("output_path", ""),
        )
    if tool_name == "pdf.optimize.subset_fonts":
        return run_subset_fonts(
            payload.get("input_path", ""),
            output_path=payload.get("output_path", ""),
        )
    if tool_name == "pdf.optimize.to_pdfa":
        return run_to_pdfa(
            payload.get("input_path", ""),
            output_path=payload.get("output_path", ""),
            profile=str(payload.get("profile", "PDF/A-2B")),
        )
    if tool_name == "pdf.optimize.validate_pdfa":
        return run_validate_pdfa(payload.get("input_path", ""))
    if tool_name == "pdf.convert.image_to_pdf":
        return run_image_to_pdf(
            payload.get("image_paths", []),
            output_path=payload.get("output_path", ""),
        )
    if tool_name == "pdf.convert.html_to_pdf":
        return run_html_to_pdf(
            payload.get("input_path", ""),
            output_path=payload.get("output_path", ""),
        )
    if tool_name == "pdf.render.html_package":
        return run_render_html_package(
            payload.get("package_path") or payload.get("input_path", ""),
            output_path=payload.get("output_path", ""),
        )
    if tool_name == "pdf.convert.url_to_pdf":
        return run_url_to_pdf(
            str(payload.get("url", "")),
            output_path=payload.get("output_path", ""),
            allow_private_hosts=bool(payload.get("allow_private_hosts", False)),
            allow_file_urls=bool(payload.get("allow_file_urls", False)),
        )
    if tool_name == "pdf.convert.docx_to_pdf":
        return run_docx_to_pdf(
            payload.get("input_path", ""),
            output_path=payload.get("output_path", ""),
        )
    if tool_name == "pdf.convert.pptx_to_pdf":
        return run_pptx_to_pdf(
            payload.get("input_path", ""),
            output_path=payload.get("output_path", ""),
        )
    if tool_name == "pdf.convert.xlsx_to_pdf":
        return run_xlsx_to_pdf(
            payload.get("input_path", ""),
            output_path=payload.get("output_path", ""),
        )
    if tool_name == "pdf.edit.watermark":
        return run_watermark(
            payload.get("input_path", ""),
            text=str(payload.get("text", "")),
            output_path=payload.get("output_path", ""),
            pages=str(payload.get("pages", "all")),
            font_size=int(payload.get("font_size", 48)),
            opacity=float(payload.get("opacity", 0.18)),
            angle=int(payload.get("angle", 45)),
        )
    if tool_name == "pdf.edit.page_numbers":
        return run_page_numbers(
            payload.get("input_path", ""),
            output_path=payload.get("output_path", ""),
            pages=str(payload.get("pages", "all")),
            template=str(payload.get("template", "{page}")),
            font_size=int(payload.get("font_size", 10)),
        )
    if tool_name == "pdf.edit.add_shape":
        return run_add_shape(
            payload.get("input_path", ""),
            output_path=payload.get("output_path", ""),
            shape=str(payload.get("shape", "rectangle")),
            page=int(payload.get("page", 1)),
            x=float(payload.get("x", 0)),
            y=float(payload.get("y", 0)),
            width=float(payload.get("width", 0)),
            height=float(payload.get("height", 0)),
            stroke_color=str(payload.get("stroke_color", "#2563eb")),
            fill_color=payload.get("fill_color"),
            line_width=float(payload.get("line_width", 1.5)),
            opacity=float(payload.get("opacity", 1.0)),
        )
    if tool_name == "pdf.edit.underline":
        return run_underline(
            payload.get("input_path", ""),
            output_path=payload.get("output_path", ""),
            page=int(payload.get("page", 1)),
            bbox=_float_list(payload.get("bbox")),
            color=str(payload.get("color", "#2563eb")),
            line_width=float(payload.get("line_width", 1.0)),
        )
    if tool_name == "pdf.edit.strikeout":
        return run_strikeout(
            payload.get("input_path", ""),
            output_path=payload.get("output_path", ""),
            page=int(payload.get("page", 1)),
            bbox=_float_list(payload.get("bbox")),
            color=str(payload.get("color", "#dc2626")),
            line_width=float(payload.get("line_width", 1.0)),
        )
    if tool_name == "pdf.edit.freehand_draw":
        return run_freehand_draw(
            payload.get("input_path", ""),
            output_path=payload.get("output_path", ""),
            page=int(payload.get("page", 1)),
            points=_point_list(payload.get("points")),
            stroke_color=str(payload.get("stroke_color", "#2563eb")),
            line_width=float(payload.get("line_width", 1.5)),
            opacity=float(payload.get("opacity", 1.0)),
        )
    if tool_name == "pdf.edit.resize_pages":
        return run_resize_pages(
            payload.get("input_path", ""),
            output_path=payload.get("output_path", ""),
            width=float(payload.get("width", 0)),
            height=float(payload.get("height", 0)),
            pages=str(payload.get("pages", "all")),
        )
    if tool_name == "pdf.edit.add_margin":
        return run_add_margin(
            payload.get("input_path", ""),
            output_path=payload.get("output_path", ""),
            margin=float(payload.get("margin", 0)),
            pages=str(payload.get("pages", "all")),
            top=_optional_float(payload.get("top")),
            right=_optional_float(payload.get("right")),
            bottom=_optional_float(payload.get("bottom")),
            left=_optional_float(payload.get("left")),
        )
    if tool_name == "pdf.edit.underlay":
        return run_underlay(
            payload.get("input_path", ""),
            output_path=payload.get("output_path", ""),
            text=str(payload.get("text", "")),
            pages=str(payload.get("pages", "all")),
            font_size=int(payload.get("font_size", 72)),
            opacity=float(payload.get("opacity", 0.12)),
            angle=int(payload.get("angle", 45)),
            color=str(payload.get("color", "#64748b")),
        )
    if tool_name == "pdf.convert.text_to_pdf":
        return run_create_text(
            payload.get("text", ""),
            output_path=payload.get("output_path", ""),
            title=payload.get("title"),
        )
    if tool_name == "pdf.convert.markdown_to_pdf":
        return run_create_markdown(
            payload.get("markdown", ""),
            output_path=payload.get("output_path", ""),
            title=payload.get("title"),
            style_pack=str(payload.get("style_pack", "plain_report")),
        )
    if tool_name == "pdf.ai.create.from_prompt":
        data = payload.get("data")
        colors = payload.get("colors")
        return run_create_from_prompt(
            prompt=str(payload.get("prompt", "")),
            output_path=payload.get("output_path", ""),
            template=payload.get("template"),
            style_pack=payload.get("style_pack"),
            data=data if isinstance(data, dict) else None,
            title=payload.get("title"),
            colors={str(key): str(value) for key, value in colors.items()}
            if isinstance(colors, dict)
            else None,
        )
    if tool_name == "pdf.ai.create.templates":
        return run_create_templates()
    if tool_name == "pdf.ai.create.template_packs":
        return run_create_template_packs(output_path=payload.get("output_path"))
    if tool_name == "pdf.ai.create.validate_template_pack":
        return run_validate_template_pack(
            template_pack=payload.get("template_pack") or payload.get("template_pack_path", ""),
            output_path=payload.get("output_path"),
        )
    if tool_name == "pdf.ai.create.plan_template_pack":
        context_packet = payload.get("context_packet")
        return run_plan_template_pack_creation(
            template_pack=payload.get("template_pack") or payload.get("template_pack_path", ""),
            target_profile=payload.get("target_profile") or payload.get("profile"),
            context_packet=context_packet if isinstance(context_packet, dict) else None,
            context_packet_path=payload.get("context_packet_path"),
            planned_output_path=payload.get("planned_output_path") or payload.get("planned_output"),
            output_path=payload.get("output_path"),
            preferred_template_id=payload.get("preferred_template_id") or payload.get("preferred_template"),
            preferred_color_scheme=payload.get("preferred_color_scheme") or payload.get("preferred_color"),
        )
    if tool_name == "pdf.ai.create.agent":
        context_packet = payload.get("context_packet")
        return run_create_agent(
            template_pack=payload.get("template_pack") or payload.get("template_pack_path", ""),
            target_profile=payload.get("target_profile") or payload.get("profile"),
            context_packet=context_packet if isinstance(context_packet, dict) else None,
            context_packet_path=payload.get("context_packet_path"),
            output_path=payload.get("output_path", ""),
            plan_output_path=payload.get("plan_output_path"),
            coverage_output_path=payload.get("coverage_output_path"),
            context_classification_output_path=payload.get("context_classification_output_path"),
            context_report_output_path=payload.get("context_report_output_path"),
            context_report_json_output_path=payload.get("context_report_json_output_path"),
            bundle_output_path=payload.get("bundle_output_path"),
            preferred_template_id=payload.get("preferred_template_id") or payload.get("preferred_template"),
            preferred_color_scheme=payload.get("preferred_color_scheme") or payload.get("preferred_color"),
            title=payload.get("title"),
            prompt=payload.get("prompt"),
            style_pack=payload.get("style_pack"),
        )
    if tool_name == "pdf.ai.create.from_template_pack":
        data = payload.get("data")
        context_packet = payload.get("context_packet")
        return run_create_from_template_pack(
            template_pack=payload.get("template_pack") or payload.get("template_pack_path", ""),
            template_id=str(payload.get("template_id") or payload.get("template", "")),
            output_path=payload.get("output_path", ""),
            color_scheme=payload.get("color_scheme"),
            data=data if isinstance(data, dict) else None,
            context_packet=context_packet if isinstance(context_packet, dict) else None,
            context_packet_path=payload.get("context_packet_path"),
            title=payload.get("title"),
            prompt=payload.get("prompt"),
            style_pack=payload.get("style_pack"),
        )
    if tool_name == "pdf.ai.create.template_preview":
        data = payload.get("data")
        colors = payload.get("colors")
        return run_create_template_preview(
            template=str(payload.get("template", "")),
            output_path=payload.get("output_path", ""),
            style_pack=payload.get("style_pack"),
            data=data if isinstance(data, dict) else None,
            colors={str(key): str(value) for key, value in colors.items()}
            if isinstance(colors, dict)
            else None,
        )
    if tool_name == "pdf.context.build_packet":
        context_items = payload.get("context_items", [])
        return run_build_context_packet(
            context_items if isinstance(context_items, list) else [],
            output_path=payload.get("output_path", ""),
            title=payload.get("title"),
            intent=payload.get("intent"),
        )
    if tool_name == "pdf.context.ingest":
        context_item = payload.get("context_item")
        if not isinstance(context_item, dict):
            context_item = {
                key: value
                for key, value in payload.items()
                if key not in {"output_path", "output"}
            }
        return run_context_ingest(
            context_item,
            output_path=payload.get("output_path") or payload.get("output"),
        )
    if tool_name == "pdf.context.packet":
        context_items = payload.get("context_items", [])
        return run_context_packet(
            context_items if isinstance(context_items, list) else [],
            output_path=payload.get("output_path", ""),
            title=payload.get("title"),
            intent=payload.get("intent"),
        )
    if tool_name == "pdf.context.classify":
        context_packet = payload.get("context_packet") or payload.get("context_packet_path", "")
        target_profile = payload.get("target_profile") or payload.get("profile")
        return run_context_classify(
            context_packet=context_packet,
            target_profile=target_profile if isinstance(target_profile, (dict, str)) else None,
            output_path=payload.get("output_path"),
        )
    if tool_name == "pdf.context.code_snapshot":
        return run_context_code_snapshot(
            path=payload.get("path", ""),
            output_path=payload.get("output_path"),
            label=payload.get("label"),
            role=str(payload.get("role", "code_evidence")),
            context_item_id=payload.get("context_item_id"),
            line_start=_optional_int(payload.get("line_start")),
            line_end=_optional_int(payload.get("line_end")),
            repository_root=payload.get("repository_root"),
            include_dependencies=bool(payload.get("include_dependencies", False)),
        )
    if tool_name == "pdf.context.data_profile":
        return run_context_data_profile(
            path=payload.get("path", ""),
            output_path=payload.get("output_path"),
            label=payload.get("label"),
            role=str(payload.get("role", "data_evidence")),
            context_item_id=payload.get("context_item_id"),
            sheet=payload.get("sheet"),
            max_rows=_optional_int(payload.get("max_rows")) or 100,
        )
    if tool_name == "pdf.context.image_analyze":
        return run_context_image_analyze(
            input_path=payload.get("input_path", payload.get("path", "")),
            languages=_string_list(payload.get("languages")),
            run_ocr=bool(payload.get("run_ocr", True)),
            engine=str(payload.get("engine", "tesseract")),
            psm=int(payload.get("psm", 6)),
        )
    if tool_name == "pdf.compose.plan":
        context_packet = payload.get("context_packet") or payload.get("context_packet_path", "")
        target_profile = payload.get("target_profile") or payload.get("profile") or "research_brief"
        return run_compose_plan(
            context_packet=context_packet,
            target_profile=target_profile if isinstance(target_profile, (dict, str)) else "research_brief",
            output_path=payload.get("output_path"),
            style_pack=payload.get("style_pack"),
            title=payload.get("title"),
        )
    if tool_name == "pdf.compose.render_ir":
        composition = payload.get("composition") or payload.get("composition_path", "")
        return run_compose_render_ir(
            composition=composition,
            output_path=payload.get("output_path", ""),
            style_pack=payload.get("style_pack"),
            title=payload.get("title"),
        )
    if tool_name == "pdf.compose.from_context":
        context_packet = payload.get("context_packet") or payload.get("context_packet_path", "")
        target_profile = payload.get("target_profile") or payload.get("profile") or "research_brief"
        return run_compose_from_context(
            context_packet=context_packet,
            target_profile=target_profile,
            output_path=payload.get("output_path", ""),
            style_pack=payload.get("style_pack"),
            title=payload.get("title"),
            renderer=str(payload.get("renderer", "markdown")),
            html_output_path=payload.get("html_output_path") or payload.get("html_output"),
        )
    if tool_name == "pdf.compose.add_code_block":
        return run_compose_add_code_block(
            input_path=payload.get("input_path", ""),
            output_path=payload.get("output_path", ""),
            title=str(payload.get("title", "Code Block")),
            code=str(payload.get("code", "")),
            language=str(payload.get("language", "text")),
            source_refs=_string_list(payload.get("source_refs")),
            block_id=payload.get("block_id"),
            target_slot=payload.get("target_slot"),
            composition_path=payload.get("composition_path"),
            layer_manifest_path=payload.get("layer_manifest_path") or payload.get("layers_path"),
            manifest_output_path=payload.get("manifest_output_path"),
        )
    if tool_name == "pdf.compose.add_table":
        rows = payload.get("rows", [])
        return run_compose_add_table(
            input_path=payload.get("input_path", ""),
            output_path=payload.get("output_path", ""),
            title=str(payload.get("title", "Table")),
            columns=_string_list(payload.get("columns")),
            rows=rows if isinstance(rows, list) else [],
            source_refs=_string_list(payload.get("source_refs")),
            block_id=payload.get("block_id"),
            target_slot=payload.get("target_slot"),
            composition_path=payload.get("composition_path"),
            layer_manifest_path=payload.get("layer_manifest_path") or payload.get("layers_path"),
            manifest_output_path=payload.get("manifest_output_path"),
        )
    if tool_name == "pdf.compose.add_figure":
        return run_compose_add_figure(
            input_path=payload.get("input_path", ""),
            output_path=payload.get("output_path", ""),
            title=str(payload.get("title", "Figure")),
            image_path=payload.get("image_path") or payload.get("path", ""),
            caption=payload.get("caption"),
            source_refs=_string_list(payload.get("source_refs")),
            block_id=payload.get("block_id"),
            target_slot=payload.get("target_slot"),
            composition_path=payload.get("composition_path"),
            layer_manifest_path=payload.get("layer_manifest_path") or payload.get("layers_path"),
            manifest_output_path=payload.get("manifest_output_path"),
        )
    if tool_name == "pdf.compose.add_appendix":
        return run_compose_add_appendix(
            input_path=payload.get("input_path", ""),
            output_path=payload.get("output_path", ""),
            title=str(payload.get("title", "Appendix")),
            markdown=str(payload.get("markdown", "")),
            source_refs=_string_list(payload.get("source_refs")),
            block_id=payload.get("block_id"),
            target_slot=payload.get("target_slot"),
            composition_path=payload.get("composition_path"),
            layer_manifest_path=payload.get("layer_manifest_path") or payload.get("layers_path"),
            manifest_output_path=payload.get("manifest_output_path"),
        )
    if tool_name == "pdf.compose.add_citation":
        return run_compose_add_citation(
            input_path=payload.get("input_path", ""),
            output_path=payload.get("output_path", ""),
            title=str(payload.get("title", "Citation")),
            source=str(payload.get("source", "")),
            quote=payload.get("quote"),
            page=payload.get("page"),
            source_refs=_string_list(payload.get("source_refs")),
            block_id=payload.get("block_id"),
            target_slot=payload.get("target_slot"),
            composition_path=payload.get("composition_path"),
            layer_manifest_path=payload.get("layer_manifest_path") or payload.get("layers_path"),
            manifest_output_path=payload.get("manifest_output_path"),
        )
    if tool_name == "pdf.compose.add_media_reference":
        return run_compose_add_media_reference(
            input_path=payload.get("input_path", ""),
            output_path=payload.get("output_path", ""),
            title=str(payload.get("title", "Media Reference")),
            media_path=payload.get("media_path") or payload.get("media") or payload.get("path", ""),
            media_kind=str(payload.get("media_kind", "media")),
            transcript_excerpt=payload.get("transcript_excerpt"),
            duration_seconds=payload.get("duration_seconds"),
            chapter_count=payload.get("chapter_count"),
            keyframe_count=payload.get("keyframe_count"),
            source_refs=_string_list(payload.get("source_refs")),
            block_id=payload.get("block_id"),
            target_slot=payload.get("target_slot"),
            composition_path=payload.get("composition_path"),
            layer_manifest_path=payload.get("layer_manifest_path") or payload.get("layers_path"),
            manifest_output_path=payload.get("manifest_output_path"),
        )
    if tool_name == "pdf.compose.add_slide":
        table = payload.get("table")
        return run_compose_add_slide(
            input_path=payload.get("input_path", ""),
            output_path=payload.get("output_path", ""),
            title=str(payload.get("title", "Slide")),
            subtitle=payload.get("subtitle"),
            body=_string_list(payload.get("body")),
            code=payload.get("code"),
            table=table if isinstance(table, dict) else None,
            image_path=payload.get("image_path") or payload.get("image"),
            source_refs=_string_list(payload.get("source_refs")),
            block_id=payload.get("block_id"),
            target_slot=payload.get("target_slot"),
            composition_path=payload.get("composition_path"),
            layer_manifest_path=payload.get("layer_manifest_path") or payload.get("layers_path"),
            manifest_output_path=payload.get("manifest_output_path"),
        )
    if tool_name == "pdf.target.profiles":
        return run_target_profiles(output_path=payload.get("output_path"))
    if tool_name == "pdf.target.select_profile":
        context_packet = payload.get("context_packet")
        return run_select_target_profile(
            goal=str(payload.get("goal", "")),
            context_packet=context_packet if isinstance(context_packet, dict) else payload.get("context_packet_path"),
            preferred_profile=payload.get("preferred_profile") or payload.get("profile"),
            output_path=payload.get("output_path"),
        )
    if tool_name == "pdf.target.validate_profile":
        target_profile = payload.get("target_profile") or payload.get("profile") or "research_brief"
        return run_validate_target_profile(
            target_profile=target_profile,
            output_path=payload.get("output_path"),
        )
    if tool_name == "pdf.evidence.coverage_report":
        return run_evidence_coverage_report(
            payload.get("composition") or payload.get("composition_path", ""),
            output_path=payload.get("output_path"),
        )
    if tool_name == "pdf.evidence.map_sources":
        context_packet = payload.get("context_packet")
        return run_evidence_map_sources(
            composition=payload.get("composition") or payload.get("composition_path"),
            blocks=_object_list(payload.get("blocks")),
            claims=_object_list(payload.get("claims")),
            context_packet=context_packet if isinstance(context_packet, dict) else payload.get("context_packet_path"),
            output_path=payload.get("output_path"),
        )
    if tool_name == "pdf.evidence.cite_claims":
        context_packet = payload.get("context_packet")
        return run_evidence_cite_claims(
            claims=_object_list(payload.get("claims")) or [],
            composition=payload.get("composition") or payload.get("composition_path"),
            source_map=payload.get("source_map") or payload.get("source_map_path"),
            context_packet=context_packet if isinstance(context_packet, dict) else payload.get("context_packet_path"),
            output_path=payload.get("output_path"),
        )
    if tool_name == "pdf.evidence.context_packet_report":
        context_packet = payload.get("context_packet") or payload.get("context_packet_path", "")
        return run_context_packet_report(
            context_packet=context_packet,
            output_path=payload.get("output_path", ""),
            report_output_path=payload.get("report_output_path"),
            title=payload.get("title"),
            style_pack=str(payload.get("style_pack", "paper_ink")),
        )
    if tool_name == "pdf.artifacts.export_bundle":
        artifact_paths = payload.get("artifact_paths") or payload.get("files") or []
        metadata = payload.get("metadata")
        return run_artifacts_export_bundle(
            artifact_paths=artifact_paths if isinstance(artifact_paths, list) else [],
            output_path=payload.get("output_path", ""),
            title=payload.get("title"),
            metadata=metadata if isinstance(metadata, dict) else None,
        )
    if tool_name == "pdf.artifacts.manifest":
        artifact_paths = payload.get("artifact_paths") or payload.get("files") or []
        metadata = payload.get("metadata")
        return run_artifacts_manifest(
            artifact_paths=artifact_paths if isinstance(artifact_paths, list) else [],
            output_path=payload.get("output_path"),
            title=payload.get("title"),
            metadata=metadata if isinstance(metadata, dict) else None,
        )
    if tool_name == "pdf.artifacts.graph":
        artifact_paths = payload.get("artifact_paths") or payload.get("files") or []
        return run_artifacts_graph(
            artifact_manifest_path=payload.get("artifact_manifest_path") or payload.get("manifest_path"),
            artifact_paths=artifact_paths if isinstance(artifact_paths, list) else [],
            output_path=payload.get("output_path"),
            title=payload.get("title"),
        )
    if tool_name == "pdf.artifacts.source_map":
        artifact_paths = payload.get("artifact_paths") or payload.get("files") or []
        context_packet = payload.get("context_packet")
        return run_artifacts_source_map(
            composition=payload.get("composition"),
            composition_path=payload.get("composition_path"),
            source_map=payload.get("source_map"),
            source_map_path=payload.get("source_map_path"),
            context_packet=context_packet if isinstance(context_packet, dict) else None,
            context_packet_path=payload.get("context_packet_path"),
            artifact_manifest_path=payload.get("artifact_manifest_path") or payload.get("manifest_path"),
            artifact_paths=artifact_paths if isinstance(artifact_paths, list) else [],
            output_path=payload.get("output_path"),
            title=payload.get("title"),
        )
    if tool_name == "pdf.artifacts.verify_bundle":
        return run_artifacts_verify_bundle(payload.get("bundle_path") or payload.get("input_path", ""))
    if tool_name == "pdf.patch.plan":
        operations = payload.get("operations", [])
        return run_patch_plan(
            input_path=payload.get("input_path", ""),
            operations=operations if isinstance(operations, list) else [],
            output_path=payload.get("output_path", ""),
            composition_path=payload.get("composition_path"),
            layer_manifest_path=payload.get("layer_manifest_path"),
            reason=payload.get("reason"),
        )
    if tool_name == "pdf.patch.preview":
        return run_patch_preview(
            payload.get("patch_manifest") or payload.get("patch_manifest_path", ""),
            output_path=payload.get("output_path"),
        )
    if tool_name == "pdf.patch.apply":
        return run_patch_apply(
            payload.get("patch_manifest") or payload.get("patch_manifest_path", ""),
            output_path=payload.get("output_path", ""),
        )
    if tool_name == "pdf.patch.verify":
        return run_patch_verify(
            payload.get("patch_manifest") or payload.get("patch_manifest_path", ""),
            patched_path=payload.get("patched_path", ""),
        )
    if tool_name == "pdf.convert.pdf_to_images":
        return run_render(
            payload.get("input_path", ""),
            pages=str(payload.get("pages", "")),
            image_format=str(payload.get("image_format", "png")),
            out_dir=payload.get("out_dir", "renders"),
        )
    if tool_name == "pdf.convert.extract_images":
        return run_extract_images(
            payload.get("input_path", ""),
            pages=str(payload.get("pages", "all")),
            out_dir=payload.get("out_dir", "extracted-images"),
        )
    if tool_name == "pdf.convert.pdf_to_text":
        return run_extract_text(
            payload.get("input_path", ""),
            pages=str(payload.get("pages", "all")),
        )
    if tool_name == "pdf.convert.extract_fonts":
        return run_extract_fonts(
            payload.get("input_path", ""),
            pages=str(payload.get("pages", "all")),
        )
    if tool_name == "pdf.convert.pdf_to_json":
        return run_pdf_to_json(
            payload.get("input_path", ""),
            output_path=payload.get("output_path", ""),
            pages=str(payload.get("pages", "all")),
        )
    if tool_name == "pdf.convert.pdf_to_markdown":
        return run_pdf_to_markdown(
            payload.get("input_path", ""),
            output_path=payload.get("output_path", ""),
            pages=str(payload.get("pages", "all")),
        )
    if tool_name == "pdf.convert.pdf_to_html":
        return run_pdf_to_html(
            payload.get("input_path", ""),
            output_path=payload.get("output_path", ""),
            pages=str(payload.get("pages", "all")),
        )
    if tool_name == "pdf.convert.pdf_to_docx":
        return run_pdf_to_docx(
            payload.get("input_path", ""),
            output_path=payload.get("output_path", ""),
            pages=str(payload.get("pages", "all")),
        )
    if tool_name == "pdf.convert.pdf_to_pptx":
        return run_pdf_to_pptx(
            payload.get("input_path", ""),
            output_path=payload.get("output_path", ""),
            pages=str(payload.get("pages", "all")),
        )
    if tool_name == "pdf.convert.pdf_to_xlsx":
        return run_pdf_to_xlsx(
            payload.get("input_path", ""),
            output_path=payload.get("output_path", ""),
            pages=str(payload.get("pages", "all")),
        )
    if tool_name == "pdf.metadata.read":
        return run_metadata_read(payload.get("input_path", ""))
    if tool_name == "pdf.metadata.page_info":
        return run_metadata_page_info(
            payload.get("input_path", payload.get("path", "")),
            pages=str(payload.get("pages", "all")),
        )
    if tool_name == "pdf.metadata.update":
        return run_metadata_update(
            payload.get("input_path", ""),
            metadata=payload.get("metadata", {}),
            output_path=payload.get("output_path", ""),
        )
    if tool_name == "pdf.metadata.update_outline":
        return run_metadata_update_outline(
            payload.get("input_path", ""),
            outline=_object_list(payload.get("outline")) or [],
            output_path=payload.get("output_path", ""),
        )
    if tool_name == "pdf.metadata.remove":
        return run_metadata_remove(
            payload.get("input_path", ""),
            output_path=payload.get("output_path", ""),
        )
    if tool_name == "pdf.security.remove_metadata":
        return run_security_remove_metadata(
            payload.get("input_path", ""),
            output_path=payload.get("output_path", ""),
        )
    if tool_name == "pdf.security.protect":
        return run_security_protect(
            payload.get("input_path", ""),
            output_path=payload.get("output_path", ""),
            password=str(payload.get("password", "")),
            owner_password=payload.get("owner_password"),
        )
    if tool_name == "pdf.security.encrypt":
        return run_security_encrypt(
            payload.get("input_path", ""),
            output_path=payload.get("output_path", ""),
            password=str(payload.get("password", "")),
            owner_password=payload.get("owner_password"),
        )
    if tool_name == "pdf.security.unlock_authorized":
        return run_security_unlock_authorized(
            payload.get("input_path", ""),
            output_path=payload.get("output_path", ""),
            password=str(payload.get("password", "")),
        )
    if tool_name == "pdf.security.decrypt_authorized":
        return run_security_decrypt_authorized(
            payload.get("input_path", ""),
            output_path=payload.get("output_path", ""),
            password=str(payload.get("password", "")),
        )
    if tool_name == "pdf.security.sign":
        return run_security_sign(
            payload.get("input_path", ""),
            output_path=payload.get("output_path", ""),
            secret=payload.get("secret"),
        )
    if tool_name == "pdf.security.verify_signature":
        return run_security_verify_signature(
            payload.get("input_path", ""),
            signature_path=payload.get("signature_path", ""),
            secret=payload.get("secret"),
        )
    if tool_name == "pdf.security.malware_scan":
        return run_security_malware_scan(payload.get("input_path", ""))
    if tool_name == "pdf.security.sanitize":
        return run_security_sanitize(
            payload.get("input_path", ""),
            output_path=payload.get("output_path", ""),
            remove_metadata=bool(payload.get("remove_metadata", True)),
        )
    if tool_name == "pdf.security.redact":
        return run_security_redact(
            payload.get("input_path", ""),
            output_path=payload.get("output_path", ""),
            regions=_object_list(payload.get("regions")) or [],
            fill_color=str(payload.get("fill_color", "#000000")),
            render_scale=float(payload.get("render_scale", 2.0)),
        )
    if tool_name == "pdf.security.verify_redaction":
        return run_security_verify_redaction(
            payload.get("input_path", ""),
            search_terms=_string_list(payload.get("search_terms")),
        )
    if tool_name == "pdf.forms.create":
        return run_forms_create(
            output_path=payload.get("output_path", ""),
            fields=_object_list(payload.get("fields")) or [],
        )
    if tool_name == "pdf.forms.import_data":
        data = payload.get("data")
        return run_forms_import_data(
            payload.get("input_path", ""),
            data=data if isinstance(data, dict) else {},
            output_path=payload.get("output_path", ""),
        )
    if tool_name == "pdf.forms.validate":
        return run_forms_validate(
            payload.get("input_path", ""),
            required_fields=_string_list(payload.get("required_fields")),
        )
    if tool_name == "pdf.validation.validate_output":
        expected_pages = payload.get("expected_pages")
        return run_validate_output(
            payload.get("path", ""),
            expected_pages=int(expected_pages) if expected_pages is not None else None,
        )
    if tool_name == "pdf.validation.page_count_check":
        return run_page_count_check(
            payload.get("path", payload.get("input_path", "")),
            expected_pages=int(payload.get("expected_pages", 0)),
        )
    if tool_name == "pdf.validation.render_check":
        return run_render_check(
            payload.get("path", ""),
            pages=str(payload.get("pages", "all")),
        )
    if tool_name == "pdf.validation.blank_page_check":
        return run_blank_page_check(
            payload.get("path", ""),
            pages=str(payload.get("pages", "all")),
        )
    if tool_name == "pdf.validation.visual_diff":
        return run_validation_visual_diff(
            payload.get("before_path", payload.get("left_path", "")),
            payload.get("after_path", payload.get("right_path", "")),
            pages=str(payload.get("pages", "all")),
            max_difference_ratio=float(payload.get("max_difference_ratio", 0.001)),
            render_scale=float(payload.get("render_scale", 0.5)),
        )
    if tool_name == "pdf.validation.redaction_check":
        return run_validation_redaction_check(
            payload.get("input_path", ""),
            search_terms=_string_list(payload.get("search_terms")),
        )
    if tool_name == "pdf.compare.semantic_diff":
        return run_compare_semantic_diff(
            payload.get("before_path", payload.get("left_path", "")),
            payload.get("after_path", payload.get("right_path", "")),
            pages=str(payload.get("pages", "all")),
        )
    if tool_name == "pdf.compare.visual_diff":
        return run_compare_visual_diff(
            payload.get("before_path", payload.get("left_path", "")),
            payload.get("after_path", payload.get("right_path", "")),
            pages=str(payload.get("pages", "all")),
            max_difference_ratio=float(payload.get("max_difference_ratio", 0.001)),
            render_scale=float(payload.get("render_scale", 0.5)),
        )
    if tool_name == "pdf.compare.version_report":
        return run_compare_version_report(
            payload.get("before_path", payload.get("left_path", "")),
            payload.get("after_path", payload.get("right_path", "")),
            output_path=payload.get("output_path"),
            pages=str(payload.get("pages", "all")),
        )
    if tool_name == "pdf.ai.parse.lite":
        return run_parse_lite(
            payload.get("input_path", ""),
            pages=str(payload.get("pages", "all")),
        )
    if tool_name == "pdf.ai.parse.figures":
        return run_parse_figures(
            payload.get("input_path", payload.get("path", "")),
            pages=str(payload.get("pages", "all")),
        )
    if tool_name == "pdf.ai.parse.formulas":
        return run_parse_formulas(
            payload.get("input_path", payload.get("path", "")),
            pages=str(payload.get("pages", "all")),
        )
    if tool_name == "pdf.ai.parse.charts":
        return run_parse_charts(
            payload.get("input_path", payload.get("path", "")),
            pages=str(payload.get("pages", "all")),
        )
    if tool_name == "pdf.ai.parse.references":
        return run_parse_references(
            payload.get("input_path", payload.get("path", "")),
            pages=str(payload.get("pages", "all")),
        )
    if tool_name == "pdf.ocr_scan.scan_to_pdf":
        return run_ocr_scan_to_pdf(
            payload.get("image_paths", []),
            output_path=payload.get("output_path", ""),
        )
    if tool_name == "pdf.ocr_scan.ocr":
        return run_ocr(
            payload.get("input_path", payload.get("path", "")),
            pages=str(payload.get("pages", "all")),
            languages=_string_list(payload.get("languages")),
            dpi=int(payload.get("dpi", 200)),
            engine=str(payload.get("engine", "tesseract")),
            psm=int(payload.get("psm", 6)),
        )
    if tool_name == "pdf.ocr_scan.searchable_pdf":
        return run_ocr_searchable_pdf(
            payload.get("input_path", ""),
            output_path=payload.get("output_path", ""),
            pages=str(payload.get("pages", "all")),
            languages=_string_list(payload.get("languages")),
            dpi=int(payload.get("dpi", 200)),
            engine=str(payload.get("engine", "tesseract")),
            psm=int(payload.get("psm", 6)),
        )
    if tool_name == "pdf.ocr_scan.despeckle":
        return run_ocr_despeckle(
            payload.get("input_path", ""),
            output_path=payload.get("output_path", ""),
        )
    if tool_name == "pdf.ocr_scan.remove_existing_ocr":
        return run_ocr_remove_existing(
            payload.get("input_path", ""),
            output_path=payload.get("output_path", ""),
        )
    if tool_name == "pdf.ocr_scan.multilingual_ocr":
        return run_ocr_multilingual(
            payload.get("input_path", ""),
            output_path=payload.get("output_path", ""),
            languages=_string_list(payload.get("languages")),
        )
    if tool_name == "pdf.ai.rag.ingest":
        return run_rag_ingest(
            payload.get("input_path", ""),
            index_path=payload.get("index_path", ""),
            pages=str(payload.get("pages", "all")),
            max_chars=int(payload.get("max_chars", 1200)),
            overlap_chars=int(payload.get("overlap_chars", 120)),
        )
    if tool_name == "pdf.ai.rag.query":
        return run_rag_query(
            payload.get("index_path", ""),
            query=str(payload.get("query", "")),
            top_k=int(payload.get("top_k", 5)),
        )
    if tool_name == "pdf.ai.rag.chat":
        return run_rag_chat(
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
    if tool_name == "pdf.ai.rag.search":
        return run_rag_search(
            payload.get("index_path", ""),
            query=str(payload.get("query", "")),
            top_k=int(payload.get("top_k", 5)),
        )
    if tool_name == "pdf.ai.rag.cite_answer":
        return run_rag_cite_answer(
            payload.get("index_path", ""),
            answer=str(payload.get("answer", "")),
            top_k=int(payload.get("top_k", 5)),
        )
    if tool_name == "pdf.ai.rag.highlight_sources":
        return run_rag_highlight_sources(
            payload.get("index_path", ""),
            output_path=payload.get("output_path", ""),
            answer=payload.get("answer"),
            query=payload.get("query"),
            top_k=int(payload.get("top_k", 5)),
            highlight_color=str(payload.get("highlight_color", "fff59d")),
        )
    if tool_name == "pdf.ai.rag.export_report":
        return run_rag_export_report(
            payload.get("index_path", ""),
            output_path=payload.get("output_path", ""),
            question=str(payload.get("question", "")),
            answer=payload.get("answer"),
            top_k=int(payload.get("top_k", 5)),
            include_citations=bool(payload.get("include_citations", True)),
            title=payload.get("title"),
            style_pack=str(payload.get("style_pack", "plain_report")),
        )

    try:
        tool = get_tool(tool_name)
        if not tool.implemented:
            return _failed(
                tool_name,
                AgentPDFError(
                    code="tool_not_implemented",
                    message=f"Tool is not implemented in the local server: {tool_name}",
                ),
            )
    except AgentPDFException as exc:
        return _failed(tool_name, exc.to_error())

    return _failed(
        tool_name,
        AgentPDFError(
            code="tool_not_implemented",
            message=f"No local runner is registered for tool: {tool_name}",
        ),
    )


def _string_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def _object_list(value: object) -> list[dict[str, object]] | None:
    if value is None:
        return None
    if isinstance(value, list) and all(isinstance(item, dict) for item in value):
        return value
    return None


def _float_list(value: object) -> list[float]:
    if isinstance(value, str):
        parts = [part.strip() for part in value.split(",") if part.strip()]
    elif isinstance(value, list):
        parts = value
    else:
        return []
    try:
        return [float(part) for part in parts]
    except (TypeError, ValueError):
        return []


def _point_list(value: object) -> list[list[float]]:
    if not isinstance(value, list):
        return []
    points = []
    for point in value:
        if not isinstance(point, list) or len(point) != 2:
            return []
        try:
            points.append([float(point[0]), float(point[1])])
        except (TypeError, ValueError):
            return []
    return points


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _failed(tool: str, error: AgentPDFError) -> ToolResult:
    return ToolResult(
        job_id=f"job_failed_{error.code}",
        status="failed",
        tool=tool,
        error=error,
        warnings=[error.message],
    )


def _error_response(error: AgentPDFError, status_code: int) -> JSONResponse:
    return JSONResponse({"error": error.model_dump(mode="json")}, status_code=status_code)
