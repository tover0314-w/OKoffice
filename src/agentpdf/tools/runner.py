from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from agentpdf.agents.claude_code import setup_claude_code
from agentpdf.artifacts.bundle import export_artifact_bundle, verify_artifact_bundle
from agentpdf.compose.context import compose_from_context, list_target_profiles, validate_target_profile
from agentpdf.context.packet import build_context_packet
from agentpdf.creation.agent import (
    create_pdf_from_prompt,
    create_pdf_from_template_pack,
    create_pdf_with_agent,
    create_template_preview,
    list_create_templates,
    list_template_packs,
    plan_template_pack_creation,
    validate_template_pack,
)
from agentpdf.evidence.coverage import create_coverage_report
from agentpdf.patch.transaction import (
    apply_patch_transaction,
    plan_patch_transaction,
    preview_patch_transaction,
    verify_patch_transaction,
)
from agentpdf.core.pdf import (
    add_page_numbers_pdf,
    add_text_watermark_pdf,
    compress_pdf,
    create_markdown_pdf,
    create_text_pdf,
    extract_images_pdf,
    extract_pages_pdf,
    extract_text_pdf,
    image_to_pdf,
    inspect_pdf,
    inspect_pdf_pages,
    insert_blank_pages_pdf,
    merge_pdfs,
    read_metadata_pdf,
    remove_pages_pdf,
    remove_metadata_pdf,
    repair_pdf,
    render_pdf,
    reorder_pages_pdf,
    rotate_pages_pdf,
    split_pdf,
    update_metadata_pdf,
)
from agentpdf.ir.lite import parse_lite_pdf, write_document_ir_json, write_document_ir_markdown
from agentpdf.rag.local import (
    chat_pdf,
    cite_answer,
    export_report,
    highlight_sources,
    ingest_pdf,
    query_index,
    search_index,
)
from agentpdf.schemas.errors import AgentPDFException
from agentpdf.schemas.models import AgentPDFError, ToolResult
from agentpdf.validation.pdf import blank_page_check_pdf, render_check_pdf, validate_pdf
from agentpdf.workflows.planner import plan_workflow
from agentpdf.workflows.reporter import create_workflow_report
from agentpdf.workflows.runner import run_workflow


def run_inspect(path: str | Path) -> ToolResult:
    tool = "pdf.inspect.document"
    try:
        info = inspect_pdf(path)
        return ToolResult(
            job_id=_job_id(),
            status="succeeded",
            tool=tool,
            usage=info,
            next_recommended_tools=["pdf.validation.validate_output"],
        )
    except AgentPDFException as exc:
        return _failed(tool, exc.to_error())


def run_inspect_pages(
    input_path: str | Path,
    pages: str = "all",
    render_check: bool = False,
) -> ToolResult:
    tool = "pdf.inspect.pages"
    try:
        info = inspect_pdf_pages(input_path, pages=pages)
        validation = None
        status = "succeeded"
        warnings = list(info.get("warnings", []))
        if render_check:
            validation, _usage = render_check_pdf(input_path, pages=pages)
            render_by_page = {
                int(check.details.get("page_number", 0)): {
                    "status": check.status,
                    **check.details,
                    **({"message": check.message} if check.message else {}),
                }
                for check in validation.checks
                if check.details and "page_number" in check.details
            }
            for page in info["pages"]:
                page["render"] = render_by_page.get(page["page_number"], {"status": "skipped"})
            warnings.extend(validation.warnings or [])
            if validation.status == "failed":
                status = "failed"
        return ToolResult(
            job_id=_job_id(),
            status=status,
            tool=tool,
            validation=validation,
            warnings=warnings,
            usage=info,
            next_recommended_tools=["pdf.ai.parse.lite", "pdf.validation.blank_page_check"],
        )
    except AgentPDFException as exc:
        return _failed(tool, exc.to_error())


def run_merge(input_paths: list[str | Path], output_path: str | Path) -> ToolResult:
    try:
        return merge_pdfs(input_paths, output_path)
    except AgentPDFException as exc:
        return _failed("pdf.organize.merge", exc.to_error())


def run_split(input_path: str | Path, pages: str, output_path: str | Path) -> ToolResult:
    try:
        return split_pdf(input_path, pages=pages, output_path=output_path)
    except AgentPDFException as exc:
        return _failed("pdf.organize.split", exc.to_error())


def run_extract_pages(input_path: str | Path, pages: str, output_path: str | Path) -> ToolResult:
    try:
        return extract_pages_pdf(input_path, pages=pages, output_path=output_path)
    except AgentPDFException as exc:
        return _failed("pdf.organize.extract_pages", exc.to_error())


def run_remove_pages(input_path: str | Path, pages: str, output_path: str | Path) -> ToolResult:
    try:
        return remove_pages_pdf(input_path, pages=pages, output_path=output_path)
    except AgentPDFException as exc:
        return _failed("pdf.organize.remove_pages", exc.to_error())


def run_rotate_pages(
    input_path: str | Path,
    pages: str,
    degrees: int,
    output_path: str | Path,
) -> ToolResult:
    try:
        return rotate_pages_pdf(input_path, pages=pages, degrees=degrees, output_path=output_path)
    except AgentPDFException as exc:
        return _failed("pdf.organize.rotate_pages", exc.to_error())


def run_reorder_pages(input_path: str | Path, order: str, output_path: str | Path) -> ToolResult:
    try:
        return reorder_pages_pdf(input_path, order=order, output_path=output_path)
    except AgentPDFException as exc:
        return _failed("pdf.organize.reorder_pages", exc.to_error())


def run_insert_blank_pages(
    input_path: str | Path,
    after_page: int,
    count: int,
    output_path: str | Path,
) -> ToolResult:
    try:
        return insert_blank_pages_pdf(
            input_path,
            after_page=after_page,
            count=count,
            output_path=output_path,
        )
    except AgentPDFException as exc:
        return _failed("pdf.organize.insert_blank_pages", exc.to_error())


def run_compress(input_path: str | Path, output_path: str | Path) -> ToolResult:
    try:
        return compress_pdf(input_path, output_path=output_path)
    except AgentPDFException as exc:
        return _failed("pdf.optimize.compress", exc.to_error())


def run_repair(input_path: str | Path, output_path: str | Path) -> ToolResult:
    try:
        return repair_pdf(input_path, output_path=output_path)
    except AgentPDFException as exc:
        return _failed("pdf.optimize.repair", exc.to_error())


def run_image_to_pdf(image_paths: list[str | Path], output_path: str | Path) -> ToolResult:
    try:
        return image_to_pdf(image_paths, output_path=output_path)
    except AgentPDFException as exc:
        return _failed("pdf.convert.image_to_pdf", exc.to_error())


def run_watermark(
    input_path: str | Path,
    text: str,
    output_path: str | Path,
    pages: str = "all",
    font_size: int = 48,
    opacity: float = 0.18,
    angle: int = 45,
) -> ToolResult:
    try:
        return add_text_watermark_pdf(
            input_path,
            text=text,
            output_path=output_path,
            pages=pages,
            font_size=font_size,
            opacity=opacity,
            angle=angle,
        )
    except AgentPDFException as exc:
        return _failed("pdf.edit.watermark", exc.to_error())


def run_page_numbers(
    input_path: str | Path,
    output_path: str | Path,
    pages: str = "all",
    template: str = "{page}",
    font_size: int = 10,
) -> ToolResult:
    try:
        return add_page_numbers_pdf(
            input_path,
            output_path=output_path,
            pages=pages,
            template=template,
            font_size=font_size,
        )
    except AgentPDFException as exc:
        return _failed("pdf.edit.page_numbers", exc.to_error())


def run_create_text(text: str, output_path: str | Path, title: str | None = None) -> ToolResult:
    try:
        return create_text_pdf(text, output_path=output_path, title=title)
    except AgentPDFException as exc:
        return _failed("pdf.convert.text_to_pdf", exc.to_error())


def run_create_markdown(
    markdown: str,
    output_path: str | Path,
    title: str | None = None,
    style_pack: str = "plain_report",
) -> ToolResult:
    try:
        return create_markdown_pdf(
            markdown,
            output_path=output_path,
            title=title,
            style_pack=style_pack,
        )
    except AgentPDFException as exc:
        return _failed("pdf.convert.markdown_to_pdf", exc.to_error())


def run_create_from_prompt(
    prompt: str,
    output_path: str | Path,
    template: str | None = None,
    style_pack: str | None = None,
    data: dict[str, object] | None = None,
    title: str | None = None,
    colors: dict[str, str] | None = None,
) -> ToolResult:
    try:
        return create_pdf_from_prompt(
            prompt,
            output_path=output_path,
            template=template,
            style_pack=style_pack,
            data=data,
            title=title,
            colors=colors,
        )
    except AgentPDFException as exc:
        return _failed("pdf.ai.create.from_prompt", exc.to_error())


def run_create_templates() -> ToolResult:
    return list_create_templates()


def run_create_template_preview(
    template: str,
    output_path: str | Path,
    style_pack: str | None = None,
    data: dict[str, object] | None = None,
    colors: dict[str, str] | None = None,
) -> ToolResult:
    try:
        return create_template_preview(
            template,
            output_path=output_path,
            style_pack=style_pack,
            data=data,
            colors=colors,
        )
    except AgentPDFException as exc:
        return _failed("pdf.ai.create.template_preview", exc.to_error())


def run_create_template_packs(output_path: str | Path | None = None) -> ToolResult:
    try:
        return list_template_packs(output_path=output_path)
    except AgentPDFException as exc:
        return _failed("pdf.ai.create.template_packs", exc.to_error())


def run_validate_template_pack(
    template_pack: dict[str, object] | str | Path,
    output_path: str | Path | None = None,
) -> ToolResult:
    try:
        return validate_template_pack(template_pack=template_pack, output_path=output_path)
    except AgentPDFException as exc:
        return _failed("pdf.ai.create.validate_template_pack", exc.to_error())


def run_plan_template_pack_creation(
    template_pack: dict[str, object] | str | Path,
    target_profile: dict[str, object] | str | None = None,
    context_packet: dict[str, object] | str | Path | None = None,
    context_packet_path: str | Path | None = None,
    planned_output_path: str | Path | None = None,
    output_path: str | Path | None = None,
    preferred_template_id: str | None = None,
    preferred_color_scheme: str | None = None,
) -> ToolResult:
    try:
        return plan_template_pack_creation(
            template_pack=template_pack,
            target_profile=target_profile,
            context_packet=context_packet,
            context_packet_path=context_packet_path,
            planned_output_path=planned_output_path,
            output_path=output_path,
            preferred_template_id=preferred_template_id,
            preferred_color_scheme=preferred_color_scheme,
        )
    except AgentPDFException as exc:
        return _failed("pdf.ai.create.plan_template_pack", exc.to_error())


def run_create_agent(
    template_pack: dict[str, object] | str | Path,
    target_profile: dict[str, object] | str | None,
    context_packet: dict[str, object] | str | Path | None = None,
    context_packet_path: str | Path | None = None,
    output_path: str | Path = ".agentpdf-out/create-agent.pdf",
    plan_output_path: str | Path | None = None,
    coverage_output_path: str | Path | None = None,
    preferred_template_id: str | None = None,
    preferred_color_scheme: str | None = None,
    title: str | None = None,
    prompt: str | None = None,
    style_pack: str | None = None,
) -> ToolResult:
    try:
        return create_pdf_with_agent(
            template_pack=template_pack,
            target_profile=target_profile,
            context_packet=context_packet,
            context_packet_path=context_packet_path,
            output_path=output_path,
            plan_output_path=plan_output_path,
            coverage_output_path=coverage_output_path,
            preferred_template_id=preferred_template_id,
            preferred_color_scheme=preferred_color_scheme,
            title=title,
            prompt=prompt,
            style_pack=style_pack,
        )
    except AgentPDFException as exc:
        return _failed("pdf.ai.create.agent", exc.to_error())


def run_create_from_template_pack(
    template_pack: dict[str, object] | str | Path,
    template_id: str,
    output_path: str | Path,
    color_scheme: str | None = None,
    data: dict[str, object] | None = None,
    context_packet: dict[str, object] | str | Path | None = None,
    context_packet_path: str | Path | None = None,
    title: str | None = None,
    prompt: str | None = None,
    style_pack: str | None = None,
) -> ToolResult:
    try:
        return create_pdf_from_template_pack(
            template_pack=template_pack,
            template_id=template_id,
            output_path=output_path,
            color_scheme=color_scheme,
            data=data,
            context_packet=context_packet,
            context_packet_path=context_packet_path,
            title=title,
            prompt=prompt,
            style_pack=style_pack,
        )
    except AgentPDFException as exc:
        return _failed("pdf.ai.create.from_template_pack", exc.to_error())


def run_build_context_packet(
    context_items: list[dict[str, object]],
    output_path: str | Path,
    title: str | None = None,
    intent: str | None = None,
) -> ToolResult:
    try:
        return build_context_packet(
            context_items,
            output_path=output_path,
            title=title,
            intent=intent,
        )
    except AgentPDFException as exc:
        return _failed("pdf.context.build_packet", exc.to_error())


def run_compose_from_context(
    context_packet: dict[str, object] | str | Path,
    target_profile: dict[str, object] | str,
    output_path: str | Path,
    style_pack: str | None = None,
    title: str | None = None,
) -> ToolResult:
    try:
        return compose_from_context(
            context_packet,
            target_profile=target_profile,
            output_path=output_path,
            style_pack=style_pack,
            title=title,
        )
    except AgentPDFException as exc:
        return _failed("pdf.compose.from_context", exc.to_error())


def run_target_profiles(output_path: str | Path | None = None) -> ToolResult:
    try:
        return list_target_profiles(output_path=output_path)
    except AgentPDFException as exc:
        return _failed("pdf.target.profiles", exc.to_error())


def run_validate_target_profile(
    target_profile: dict[str, object] | str,
    output_path: str | Path | None = None,
) -> ToolResult:
    try:
        return validate_target_profile(target_profile, output_path=output_path)
    except AgentPDFException as exc:
        return _failed("pdf.target.validate_profile", exc.to_error())


def run_agent_setup_claude_code(
    output_path: str | Path | None = None,
    safe_root: str = "${CLAUDE_PROJECT_DIR:-.}",
    command: str = "okpdf",
    args_prefix: list[str] | None = None,
    server_name: str = "agentpdf",
    scope: str = "project",
) -> ToolResult:
    try:
        return setup_claude_code(
            output_path=output_path,
            safe_root=safe_root,
            command=command,
            args_prefix=args_prefix,
            server_name=server_name,
            scope=scope,  # type: ignore[arg-type]
        )
    except AgentPDFException as exc:
        return _failed("agent.setup.claude_code", exc.to_error())


def run_evidence_coverage_report(
    composition: dict[str, object] | str | Path,
    output_path: str | Path | None = None,
) -> ToolResult:
    try:
        return create_coverage_report(composition, output_path=output_path)
    except AgentPDFException as exc:
        return _failed("pdf.evidence.coverage_report", exc.to_error())


def run_artifacts_export_bundle(
    artifact_paths: list[str | Path],
    output_path: str | Path,
    title: str | None = None,
    metadata: dict[str, object] | None = None,
) -> ToolResult:
    try:
        return export_artifact_bundle(
            artifact_paths=artifact_paths,
            output_path=output_path,
            title=title,
            metadata=metadata,
        )
    except AgentPDFException as exc:
        return _failed("pdf.artifacts.export_bundle", exc.to_error())


def run_artifacts_verify_bundle(bundle_path: str | Path) -> ToolResult:
    try:
        return verify_artifact_bundle(bundle_path=bundle_path)
    except AgentPDFException as exc:
        return _failed("pdf.artifacts.verify_bundle", exc.to_error())


def run_patch_plan(
    input_path: str | Path,
    operations: list[dict[str, object]],
    output_path: str | Path,
    composition_path: str | Path | None = None,
    layer_manifest_path: str | Path | None = None,
    reason: str | None = None,
) -> ToolResult:
    try:
        return plan_patch_transaction(
            input_path=input_path,
            operations=operations,
            output_path=output_path,
            composition_path=composition_path,
            layer_manifest_path=layer_manifest_path,
            reason=reason,
        )
    except AgentPDFException as exc:
        return _failed("pdf.patch.plan", exc.to_error())


def run_patch_preview(
    patch_manifest: dict[str, object] | str | Path,
    output_path: str | Path | None = None,
) -> ToolResult:
    try:
        return preview_patch_transaction(patch_manifest, output_path=output_path)
    except AgentPDFException as exc:
        return _failed("pdf.patch.preview", exc.to_error())


def run_patch_apply(
    patch_manifest: dict[str, object] | str | Path,
    output_path: str | Path,
) -> ToolResult:
    try:
        return apply_patch_transaction(patch_manifest, output_path=output_path)
    except AgentPDFException as exc:
        return _failed("pdf.patch.apply", exc.to_error())


def run_patch_verify(
    patch_manifest: dict[str, object] | str | Path,
    patched_path: str | Path,
) -> ToolResult:
    try:
        return verify_patch_transaction(patch_manifest, patched_path=patched_path)
    except AgentPDFException as exc:
        return _failed("pdf.patch.verify", exc.to_error())


def run_render(
    input_path: str | Path,
    pages: str,
    image_format: str,
    out_dir: str | Path,
) -> ToolResult:
    try:
        return render_pdf(
            input_path=input_path,
            pages=pages,
            image_format=image_format,
            out_dir=out_dir,
        )
    except AgentPDFException as exc:
        return _failed("pdf.convert.pdf_to_images", exc.to_error())


def run_extract_images(
    input_path: str | Path,
    pages: str = "all",
    out_dir: str | Path = "extracted-images",
) -> ToolResult:
    try:
        return extract_images_pdf(
            input_path=input_path,
            pages=pages,
            out_dir=out_dir,
        )
    except AgentPDFException as exc:
        return _failed("pdf.convert.extract_images", exc.to_error())


def run_extract_text(input_path: str | Path, pages: str = "all") -> ToolResult:
    try:
        return extract_text_pdf(input_path, pages=pages)
    except AgentPDFException as exc:
        return _failed("pdf.convert.pdf_to_text", exc.to_error())


def run_pdf_to_json(
    input_path: str | Path,
    output_path: str | Path,
    pages: str = "all",
) -> ToolResult:
    try:
        return write_document_ir_json(input_path, output_path=output_path, pages=pages)
    except AgentPDFException as exc:
        return _failed("pdf.convert.pdf_to_json", exc.to_error())


def run_pdf_to_markdown(
    input_path: str | Path,
    output_path: str | Path,
    pages: str = "all",
) -> ToolResult:
    try:
        return write_document_ir_markdown(input_path, output_path=output_path, pages=pages)
    except AgentPDFException as exc:
        return _failed("pdf.convert.pdf_to_markdown", exc.to_error())


def run_metadata_read(input_path: str | Path) -> ToolResult:
    try:
        return read_metadata_pdf(input_path)
    except AgentPDFException as exc:
        return _failed("pdf.metadata.read", exc.to_error())


def run_metadata_update(
    input_path: str | Path,
    metadata: dict[str, object],
    output_path: str | Path,
) -> ToolResult:
    try:
        return update_metadata_pdf(input_path, metadata=metadata, output_path=output_path)
    except AgentPDFException as exc:
        return _failed("pdf.metadata.update", exc.to_error())


def run_metadata_remove(input_path: str | Path, output_path: str | Path) -> ToolResult:
    try:
        return remove_metadata_pdf(input_path, output_path=output_path)
    except AgentPDFException as exc:
        return _failed("pdf.metadata.remove", exc.to_error())


def run_validate_output(path: str | Path, expected_pages: int | None = None) -> ToolResult:
    tool = "pdf.validation.validate_output"
    try:
        report = validate_pdf(path, expected_pages=expected_pages)
    except AgentPDFException as exc:
        return _failed(tool, exc.to_error())
    return ToolResult(
        job_id=_job_id(),
        status="succeeded" if report.status == "passed" else "failed",
        tool=tool,
        validation=report,
        next_recommended_tools=["pdf.inspect.document"],
    )


def run_render_check(path: str | Path, pages: str = "all") -> ToolResult:
    tool = "pdf.validation.render_check"
    try:
        report, usage = render_check_pdf(path, pages=pages)
    except AgentPDFException as exc:
        return _failed(tool, exc.to_error())
    return ToolResult(
        job_id=_job_id(),
        status="succeeded" if report.status == "passed" else "failed",
        tool=tool,
        validation=report,
        warnings=report.warnings,
        usage=usage,
        next_recommended_tools=["pdf.validation.blank_page_check", "pdf.inspect.document"],
    )


def run_blank_page_check(path: str | Path, pages: str = "all") -> ToolResult:
    tool = "pdf.validation.blank_page_check"
    try:
        report, usage = blank_page_check_pdf(path, pages=pages)
    except AgentPDFException as exc:
        return _failed(tool, exc.to_error())
    blank_pages = usage.get("blank_pages", [])
    next_tools = ["pdf.organize.remove_pages", "pdf.inspect.document"] if blank_pages else ["pdf.inspect.document"]
    return ToolResult(
        job_id=_job_id(),
        status="failed" if report.status == "failed" else "succeeded",
        tool=tool,
        validation=report,
        warnings=report.warnings,
        usage=usage,
        next_recommended_tools=next_tools,
    )


def run_parse_lite(input_path: str | Path, pages: str = "all") -> ToolResult:
    try:
        return parse_lite_pdf(input_path, pages=pages)
    except AgentPDFException as exc:
        return _failed("pdf.ai.parse.lite", exc.to_error())


def run_rag_ingest(
    input_path: str | Path,
    index_path: str | Path,
    pages: str = "all",
    max_chars: int = 1200,
    overlap_chars: int = 120,
) -> ToolResult:
    try:
        return ingest_pdf(
            input_path,
            index_path=index_path,
            pages=pages,
            max_chars=max_chars,
            overlap_chars=overlap_chars,
        )
    except AgentPDFException as exc:
        return _failed("pdf.ai.rag.ingest", exc.to_error())


def run_rag_query(index_path: str | Path, query: str, top_k: int = 5) -> ToolResult:
    try:
        return query_index(index_path, query=query, top_k=top_k)
    except AgentPDFException as exc:
        return _failed("pdf.ai.rag.query", exc.to_error())


def run_rag_search(index_path: str | Path, query: str, top_k: int = 5) -> ToolResult:
    try:
        return search_index(index_path, query=query, top_k=top_k)
    except AgentPDFException as exc:
        return _failed("pdf.ai.rag.search", exc.to_error())


def run_rag_cite_answer(index_path: str | Path, answer: str, top_k: int = 5) -> ToolResult:
    try:
        return cite_answer(index_path, answer=answer, top_k=top_k)
    except AgentPDFException as exc:
        return _failed("pdf.ai.rag.cite_answer", exc.to_error())


def run_rag_highlight_sources(
    index_path: str | Path,
    output_path: str | Path,
    answer: str | None = None,
    query: str | None = None,
    top_k: int = 5,
    highlight_color: str = "fff59d",
) -> ToolResult:
    try:
        return highlight_sources(
            index_path,
            output_path=output_path,
            answer=answer,
            query=query,
            top_k=top_k,
            highlight_color=highlight_color,
        )
    except AgentPDFException as exc:
        return _failed("pdf.ai.rag.highlight_sources", exc.to_error())


def run_rag_export_report(
    index_path: str | Path,
    output_path: str | Path,
    question: str,
    answer: str | None = None,
    top_k: int = 5,
    include_citations: bool = True,
    title: str | None = None,
    style_pack: str = "plain_report",
) -> ToolResult:
    try:
        return export_report(
            index_path,
            output_path=output_path,
            question=question,
            answer=answer,
            top_k=top_k,
            include_citations=include_citations,
            title=title,
            style_pack=style_pack,
        )
    except AgentPDFException as exc:
        return _failed("pdf.ai.rag.export_report", exc.to_error())


def run_rag_chat(
    input_path: str | Path,
    question: str,
    index_path: str | Path | None = None,
    report_output_path: str | Path | None = None,
    highlight_output_path: str | Path | None = None,
    pages: str = "all",
    top_k: int = 5,
    max_chars: int = 1200,
    overlap_chars: int = 120,
    style_pack: str = "plain_report",
    highlight_color: str = "fff59d",
) -> ToolResult:
    try:
        return chat_pdf(
            input_path,
            question=question,
            index_path=index_path,
            report_output_path=report_output_path,
            highlight_output_path=highlight_output_path,
            pages=pages,
            top_k=top_k,
            max_chars=max_chars,
            overlap_chars=overlap_chars,
            style_pack=style_pack,
            highlight_color=highlight_color,
        )
    except AgentPDFException as exc:
        return _failed("pdf.ai.rag.chat", exc.to_error())


def run_workflow_plan(goal: str, input_path: str | None = None) -> ToolResult:
    return plan_workflow(goal=goal, input_path=input_path)


def run_workflow_run(workflow: dict[str, object], dry_run: bool = False) -> ToolResult:
    return run_workflow(workflow=workflow, dry_run=dry_run)


def run_workflow_report(
    workflow_run: dict[str, object],
    output_path: str | Path | None = None,
) -> ToolResult:
    return create_workflow_report(workflow_run=workflow_run, output_path=output_path)


def _failed(tool: str, error: AgentPDFError) -> ToolResult:
    return ToolResult(
        job_id=_job_id(),
        status="failed",
        tool=tool,
        error=error,
        warnings=[error.message],
    )


def _job_id() -> str:
    return f"job_{uuid4().hex[:16]}"
