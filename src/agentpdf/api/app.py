from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.responses import JSONResponse

from agentpdf.schemas.errors import AgentPDFException
from agentpdf.schemas.models import AgentPDFError, ToolResult
from agentpdf.tools.registry import get_tool, load_tool_manifest
from agentpdf.tools.runner import (
    run_blank_page_check,
    run_compress,
    run_create_markdown,
    run_create_text,
    run_extract_images,
    run_extract_pages,
    run_extract_text,
    run_image_to_pdf,
    run_inspect,
    run_inspect_pages,
    run_insert_blank_pages,
    run_metadata_read,
    run_metadata_remove,
    run_metadata_update,
    run_merge,
    run_page_numbers,
    run_parse_lite,
    run_pdf_to_markdown,
    run_pdf_to_json,
    run_rag_chat,
    run_rag_cite_answer,
    run_rag_export_report,
    run_rag_highlight_sources,
    run_rag_ingest,
    run_rag_query,
    run_rag_search,
    run_remove_pages,
    run_render,
    run_render_check,
    run_repair,
    run_reorder_pages,
    run_rotate_pages,
    run_split,
    run_validate_output,
    run_watermark,
    run_workflow_plan,
    run_workflow_report,
    run_workflow_run,
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
    if tool_name == "pdf.inspect.document":
        return run_inspect(payload.get("path", ""))
    if tool_name == "pdf.inspect.pages":
        return run_inspect_pages(
            payload.get("input_path", payload.get("path", "")),
            pages=str(payload.get("pages", "all")),
            render_check=bool(payload.get("render_check", False)),
        )
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
    if tool_name == "pdf.convert.image_to_pdf":
        return run_image_to_pdf(
            payload.get("image_paths", []),
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
    if tool_name == "pdf.metadata.read":
        return run_metadata_read(payload.get("input_path", ""))
    if tool_name == "pdf.metadata.update":
        return run_metadata_update(
            payload.get("input_path", ""),
            metadata=payload.get("metadata", {}),
            output_path=payload.get("output_path", ""),
        )
    if tool_name == "pdf.metadata.remove":
        return run_metadata_remove(
            payload.get("input_path", ""),
            output_path=payload.get("output_path", ""),
        )
    if tool_name == "pdf.validation.validate_output":
        expected_pages = payload.get("expected_pages")
        return run_validate_output(
            payload.get("path", ""),
            expected_pages=int(expected_pages) if expected_pages is not None else None,
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
    if tool_name == "pdf.ai.parse.lite":
        return run_parse_lite(
            payload.get("input_path", ""),
            pages=str(payload.get("pages", "all")),
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
