from __future__ import annotations

from typing import Literal

from mcp.server.fastmcp import FastMCP

from agentpdf.tools.registry import load_tool_manifest
from agentpdf.tools.runner import (
    run_agent_setup_claude_code,
    run_artifacts_export_bundle,
    run_artifacts_verify_bundle,
    run_blank_page_check,
    run_build_context_packet,
    run_compose_from_context,
    run_compress,
    run_create_markdown,
    run_create_text,
    run_create_agent,
    run_create_from_prompt,
    run_create_from_template_pack,
    run_plan_template_pack_creation,
    run_create_template_preview,
    run_create_template_packs,
    run_create_templates,
    run_validate_template_pack,
    run_evidence_coverage_report,
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
    run_patch_apply,
    run_patch_plan,
    run_patch_preview,
    run_patch_verify,
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
    run_target_profiles,
    run_validate_output,
    run_validate_target_profile,
    run_watermark,
    run_workflow_plan,
    run_workflow_report,
    run_workflow_run,
)


def create_mcp_server() -> FastMCP:
    server = FastMCP(
        "agentpdf",
        instructions=(
            "Local-first PDF tools for agents. Tools return structured AgentPDF "
            "ToolResult JSON and write artifacts to explicit local paths."
        ),
    )
    server.tool(name="agentpdf_tool_manifest")(agentpdf_tool_manifest)
    server.tool(name="agent_setup_claude_code")(agent_setup_claude_code)
    server.tool(name="pdf_inspect_document")(pdf_inspect_document)
    server.tool(name="pdf_inspect_pages")(pdf_inspect_pages)
    server.tool(name="pdf_workflow_plan")(pdf_workflow_plan)
    server.tool(name="pdf_workflow_run")(pdf_workflow_run)
    server.tool(name="pdf_workflow_report")(pdf_workflow_report)
    server.tool(name="pdf_merge")(pdf_merge)
    server.tool(name="pdf_split")(pdf_split)
    server.tool(name="pdf_extract_pages")(pdf_extract_pages)
    server.tool(name="pdf_remove_pages")(pdf_remove_pages)
    server.tool(name="pdf_rotate_pages")(pdf_rotate_pages)
    server.tool(name="pdf_reorder_pages")(pdf_reorder_pages)
    server.tool(name="pdf_insert_blank_pages")(pdf_insert_blank_pages)
    server.tool(name="pdf_optimize_compress")(pdf_optimize_compress)
    server.tool(name="pdf_optimize_repair")(pdf_optimize_repair)
    server.tool(name="pdf_image_to_pdf")(pdf_image_to_pdf)
    server.tool(name="pdf_watermark")(pdf_watermark)
    server.tool(name="pdf_add_page_numbers")(pdf_add_page_numbers)
    server.tool(name="pdf_create_text")(pdf_create_text)
    server.tool(name="pdf_create_markdown")(pdf_create_markdown)
    server.tool(name="pdf_ai_create_from_prompt")(pdf_ai_create_from_prompt)
    server.tool(name="pdf_ai_create_template_preview")(pdf_ai_create_template_preview)
    server.tool(name="pdf_ai_create_templates")(pdf_ai_create_templates)
    server.tool(name="pdf_ai_create_template_packs")(pdf_ai_create_template_packs)
    server.tool(name="pdf_ai_create_validate_template_pack")(pdf_ai_create_validate_template_pack)
    server.tool(name="pdf_ai_create_plan_template_pack")(pdf_ai_create_plan_template_pack)
    server.tool(name="pdf_ai_create_agent")(pdf_ai_create_agent)
    server.tool(name="pdf_ai_create_from_template_pack")(pdf_ai_create_from_template_pack)
    server.tool(name="pdf_context_build_packet")(pdf_context_build_packet)
    server.tool(name="pdf_compose_from_context")(pdf_compose_from_context)
    server.tool(name="pdf_target_profiles")(pdf_target_profiles)
    server.tool(name="pdf_target_validate_profile")(pdf_target_validate_profile)
    server.tool(name="pdf_evidence_coverage_report")(pdf_evidence_coverage_report)
    server.tool(name="pdf_artifacts_export_bundle")(pdf_artifacts_export_bundle)
    server.tool(name="pdf_artifacts_verify_bundle")(pdf_artifacts_verify_bundle)
    server.tool(name="pdf_patch_plan")(pdf_patch_plan)
    server.tool(name="pdf_patch_preview")(pdf_patch_preview)
    server.tool(name="pdf_patch_apply")(pdf_patch_apply)
    server.tool(name="pdf_patch_verify")(pdf_patch_verify)
    server.tool(name="pdf_render_pages")(pdf_render_pages)
    server.tool(name="pdf_extract_images")(pdf_extract_images)
    server.tool(name="pdf_extract_text")(pdf_extract_text)
    server.tool(name="pdf_pdf_to_json")(pdf_pdf_to_json)
    server.tool(name="pdf_pdf_to_markdown")(pdf_pdf_to_markdown)
    server.tool(name="pdf_metadata_read")(pdf_metadata_read)
    server.tool(name="pdf_metadata_update")(pdf_metadata_update)
    server.tool(name="pdf_metadata_remove")(pdf_metadata_remove)
    server.tool(name="pdf_validate_output")(pdf_validate_output)
    server.tool(name="pdf_render_check")(pdf_render_check)
    server.tool(name="pdf_blank_page_check")(pdf_blank_page_check)
    server.tool(name="pdf_ai_parse_lite")(pdf_ai_parse_lite)
    server.tool(name="pdf_ai_rag_ingest")(pdf_ai_rag_ingest)
    server.tool(name="pdf_ai_rag_cite_answer")(pdf_ai_rag_cite_answer)
    server.tool(name="pdf_ai_rag_chat")(pdf_ai_rag_chat)
    server.tool(name="pdf_ai_rag_export_report")(pdf_ai_rag_export_report)
    server.tool(name="pdf_ai_rag_highlight_sources")(pdf_ai_rag_highlight_sources)
    server.tool(name="pdf_ai_rag_query")(pdf_ai_rag_query)
    server.tool(name="pdf_ai_rag_search")(pdf_ai_rag_search)
    return server


def agentpdf_tool_manifest() -> str:
    """Return the complete AgentPDF tool manifest with implementation statuses."""
    return load_tool_manifest().model_dump_json()


def agent_setup_claude_code(
    output_path: str | None = None,
    safe_root: str = "${CLAUDE_PROJECT_DIR:-.}",
    command: str = "okpdf",
    args_prefix: list[str] | None = None,
    server_name: str = "agentpdf",
    scope: Literal["project", "local", "user"] = "project",
) -> str:
    """Generate a Claude Code MCP config for local AgentPDF tools."""
    return run_agent_setup_claude_code(
        output_path=output_path,
        safe_root=safe_root,
        command=command,
        args_prefix=args_prefix,
        server_name=server_name,
        scope=scope,
    ).model_dump_json()


def pdf_inspect_document(path: str) -> str:
    """Inspect a local PDF document."""
    return run_inspect(path).model_dump_json()


def pdf_inspect_pages(input_path: str, pages: str = "all", render_check: bool = False) -> str:
    """Inspect page-level facts for selected local PDF pages."""
    return run_inspect_pages(
        input_path,
        pages=pages,
        render_check=render_check,
    ).model_dump_json()


def pdf_workflow_plan(goal: str, input_path: str | None = None) -> str:
    """Plan a local-first agent PDF workflow."""
    return run_workflow_plan(goal=goal, input_path=input_path).model_dump_json()


def pdf_workflow_run(workflow: dict[str, object], dry_run: bool = False) -> str:
    """Run a local-first agent PDF workflow manifest."""
    return run_workflow_run(workflow=workflow, dry_run=dry_run).model_dump_json()


def pdf_workflow_report(workflow_run: dict[str, object], output_path: str | None = None) -> str:
    """Summarize a local workflow run with audit evidence."""
    return run_workflow_report(workflow_run=workflow_run, output_path=output_path).model_dump_json()


def pdf_merge(input_paths: list[str], output_path: str) -> str:
    """Merge local PDF files into a new output PDF."""
    return run_merge(input_paths, output_path).model_dump_json()


def pdf_split(input_path: str, pages: str, output_path: str) -> str:
    """Extract selected pages from a local PDF into a new output PDF."""
    return run_split(input_path, pages=pages, output_path=output_path).model_dump_json()


def pdf_extract_pages(input_path: str, pages: str, output_path: str) -> str:
    """Extract selected pages from a local PDF into a new output PDF."""
    return run_extract_pages(input_path, pages=pages, output_path=output_path).model_dump_json()


def pdf_remove_pages(input_path: str, pages: str, output_path: str) -> str:
    """Remove selected pages from a local PDF and write a new output PDF."""
    return run_remove_pages(input_path, pages=pages, output_path=output_path).model_dump_json()


def pdf_rotate_pages(input_path: str, pages: str, degrees: int, output_path: str) -> str:
    """Rotate selected pages from a local PDF and write a new output PDF."""
    return run_rotate_pages(
        input_path,
        pages=pages,
        degrees=degrees,
        output_path=output_path,
    ).model_dump_json()


def pdf_reorder_pages(input_path: str, order: str, output_path: str) -> str:
    """Reorder local PDF pages and write a new output PDF."""
    return run_reorder_pages(input_path, order=order, output_path=output_path).model_dump_json()


def pdf_insert_blank_pages(
    input_path: str,
    after_page: int,
    count: int,
    output_path: str,
) -> str:
    """Insert blank pages into a local PDF and write a new output PDF."""
    return run_insert_blank_pages(
        input_path,
        after_page=after_page,
        count=count,
        output_path=output_path,
    ).model_dump_json()


def pdf_optimize_compress(input_path: str, output_path: str) -> str:
    """Compress local PDF content streams and write a new output PDF."""
    return run_compress(input_path, output_path=output_path).model_dump_json()


def pdf_optimize_repair(input_path: str, output_path: str) -> str:
    """Rewrite a parseable local PDF to rebuild output structure."""
    return run_repair(input_path, output_path=output_path).model_dump_json()


def pdf_image_to_pdf(image_paths: list[str], output_path: str) -> str:
    """Create a local PDF from image files."""
    return run_image_to_pdf(image_paths, output_path=output_path).model_dump_json()


def pdf_watermark(
    input_path: str,
    text: str,
    output_path: str,
    pages: str = "all",
    font_size: int = 48,
    opacity: float = 0.18,
    angle: int = 45,
) -> str:
    """Add a text watermark overlay to a local PDF."""
    return run_watermark(
        input_path,
        text=text,
        output_path=output_path,
        pages=pages,
        font_size=font_size,
        opacity=opacity,
        angle=angle,
    ).model_dump_json()


def pdf_add_page_numbers(
    input_path: str,
    output_path: str,
    pages: str = "all",
    template: str = "{page}",
    font_size: int = 10,
) -> str:
    """Add page number overlays to a local PDF."""
    return run_page_numbers(
        input_path,
        output_path=output_path,
        pages=pages,
        template=template,
        font_size=font_size,
    ).model_dump_json()


def pdf_create_text(text: str, output_path: str, title: str | None = None) -> str:
    """Create a local PDF from plain text."""
    return run_create_text(text, output_path=output_path, title=title).model_dump_json()


def pdf_create_markdown(
    markdown: str,
    output_path: str,
    title: str | None = None,
    style_pack: str = "plain_report",
) -> str:
    """Create a local PDF from Markdown content."""
    return run_create_markdown(
        markdown,
        output_path=output_path,
        title=title,
        style_pack=style_pack,
    ).model_dump_json()


def pdf_ai_create_from_prompt(
    prompt: str,
    output_path: str,
    template: str | None = None,
    style_pack: str | None = None,
    data: dict[str, object] | None = None,
    title: str | None = None,
    colors: dict[str, str] | None = None,
) -> str:
    """Create a validated local PDF from a prompt, template, and optional JSON data."""
    return run_create_from_prompt(
        prompt,
        output_path=output_path,
        template=template,
        style_pack=style_pack,
        data=data,
        title=title,
        colors=colors,
    ).model_dump_json()


def pdf_ai_create_templates() -> str:
    """List local PDF creation templates, style packs, and color keys."""
    return run_create_templates().model_dump_json()


def pdf_ai_create_template_packs(output_path: str | None = None) -> str:
    """List local template packs for agent-created PDFs."""
    return run_create_template_packs(output_path=output_path).model_dump_json()


def pdf_ai_create_validate_template_pack(
    template_pack: dict[str, object] | str,
    output_path: str | None = None,
) -> str:
    """Validate a local template pack contract."""
    return run_validate_template_pack(
        template_pack=template_pack,
        output_path=output_path,
    ).model_dump_json()


def pdf_ai_create_plan_template_pack(
    template_pack: dict[str, object] | str,
    target_profile: dict[str, object] | str | None = None,
    context_packet: dict[str, object] | str | None = None,
    context_packet_path: str | None = None,
    planned_output_path: str | None = None,
    output_path: str | None = None,
    preferred_template_id: str | None = None,
    preferred_color_scheme: str | None = None,
) -> str:
    """Plan a local template-pack PDF creation call from target and context evidence."""
    return run_plan_template_pack_creation(
        template_pack=template_pack,
        target_profile=target_profile,
        context_packet=context_packet,
        context_packet_path=context_packet_path,
        planned_output_path=planned_output_path,
        output_path=output_path,
        preferred_template_id=preferred_template_id,
        preferred_color_scheme=preferred_color_scheme,
    ).model_dump_json()


def pdf_ai_create_agent(
    template_pack: dict[str, object] | str,
    target_profile: dict[str, object] | str | None,
    context_packet: dict[str, object] | str | None = None,
    context_packet_path: str | None = None,
    output_path: str = ".agentpdf-out/create-agent.pdf",
    plan_output_path: str | None = None,
    coverage_output_path: str | None = None,
    preferred_template_id: str | None = None,
    preferred_color_scheme: str | None = None,
    title: str | None = None,
    prompt: str | None = None,
    style_pack: str | None = None,
) -> str:
    """Run the local create agent: plan, create, render-check, blank-check, and coverage."""
    return run_create_agent(
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
    ).model_dump_json()


def pdf_ai_create_from_template_pack(
    template_pack: dict[str, object] | str,
    template_id: str,
    output_path: str,
    color_scheme: str | None = None,
    data: dict[str, object] | None = None,
    context_packet: dict[str, object] | str | None = None,
    context_packet_path: str | None = None,
    title: str | None = None,
    prompt: str | None = None,
    style_pack: str | None = None,
) -> str:
    """Create a validated local PDF from a template pack."""
    return run_create_from_template_pack(
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
    ).model_dump_json()


def pdf_ai_create_template_preview(
    template: str,
    output_path: str,
    style_pack: str | None = None,
    data: dict[str, object] | None = None,
    colors: dict[str, str] | None = None,
) -> str:
    """Generate and validate a local preview PDF for a creation template."""
    return run_create_template_preview(
        template,
        output_path=output_path,
        style_pack=style_pack,
        data=data,
        colors=colors,
    ).model_dump_json()


def pdf_context_build_packet(
    context_items: list[dict[str, object]],
    output_path: str,
    title: str | None = None,
    intent: str | None = None,
) -> str:
    """Build a local Context Packet with source graph metadata."""
    return run_build_context_packet(
        context_items,
        output_path=output_path,
        title=title,
        intent=intent,
    ).model_dump_json()


def pdf_compose_from_context(
    context_packet: dict[str, object] | str,
    output_path: str,
    target_profile: dict[str, object] | str = "research_brief",
    style_pack: str | None = None,
    title: str | None = None,
) -> str:
    """Compose a validated target PDF from a Context Packet and target profile."""
    return run_compose_from_context(
        context_packet,
        target_profile=target_profile,
        output_path=output_path,
        style_pack=style_pack,
        title=title,
    ).model_dump_json()


def pdf_target_profiles(output_path: str | None = None) -> str:
    """List built-in target PDF profiles with layout slots and accepted block types."""
    return run_target_profiles(output_path=output_path).model_dump_json()


def pdf_target_validate_profile(
    target_profile: dict[str, object] | str = "research_brief",
    output_path: str | None = None,
) -> str:
    """Validate a built-in or custom target PDF profile."""
    return run_validate_target_profile(target_profile=target_profile, output_path=output_path).model_dump_json()


def pdf_evidence_coverage_report(
    composition: dict[str, object] | str,
    output_path: str | None = None,
) -> str:
    """Create an evidence coverage report from a composition artifact."""
    return run_evidence_coverage_report(composition, output_path=output_path).model_dump_json()


def pdf_artifacts_export_bundle(
    artifact_paths: list[str],
    output_path: str,
    title: str | None = None,
    metadata: dict[str, object] | None = None,
) -> str:
    """Export local artifacts into a portable audit bundle."""
    return run_artifacts_export_bundle(
        artifact_paths=artifact_paths,
        output_path=output_path,
        title=title,
        metadata=metadata,
    ).model_dump_json()


def pdf_artifacts_verify_bundle(bundle_path: str) -> str:
    """Verify a portable audit bundle manifest and checksums."""
    return run_artifacts_verify_bundle(bundle_path=bundle_path).model_dump_json()


def pdf_patch_plan(
    input_path: str,
    operations: list[dict[str, object]],
    output_path: str,
    composition_path: str | None = None,
    layer_manifest_path: str | None = None,
    reason: str | None = None,
) -> str:
    """Create a structured patch manifest without mutating the input PDF."""
    return run_patch_plan(
        input_path=input_path,
        operations=operations,
        output_path=output_path,
        composition_path=composition_path,
        layer_manifest_path=layer_manifest_path,
        reason=reason,
    ).model_dump_json()


def pdf_patch_preview(patch_manifest: dict[str, object] | str, output_path: str | None = None) -> str:
    """Preview patch effects and validation requirements."""
    return run_patch_preview(patch_manifest, output_path=output_path).model_dump_json()


def pdf_patch_apply(patch_manifest: dict[str, object] | str, output_path: str) -> str:
    """Apply a patch transaction to a new output PDF artifact."""
    return run_patch_apply(patch_manifest, output_path=output_path).model_dump_json()


def pdf_patch_verify(patch_manifest: dict[str, object] | str, patched_path: str) -> str:
    """Verify a patched PDF against a patch manifest."""
    return run_patch_verify(patch_manifest, patched_path=patched_path).model_dump_json()


def pdf_render_pages(
    input_path: str,
    pages: str,
    image_format: Literal["png", "jpeg", "jpg", "webp"] = "png",
    out_dir: str = "renders",
) -> str:
    """Render selected local PDF pages to image artifacts."""
    return run_render(
        input_path,
        pages=pages,
        image_format=image_format,
        out_dir=out_dir,
    ).model_dump_json()


def pdf_extract_images(input_path: str, pages: str = "all", out_dir: str = "extracted-images") -> str:
    """Extract embedded images from selected local PDF pages."""
    return run_extract_images(input_path, pages=pages, out_dir=out_dir).model_dump_json()


def pdf_extract_text(input_path: str, pages: str = "all") -> str:
    """Extract text from selected local PDF pages."""
    return run_extract_text(input_path, pages=pages).model_dump_json()


def pdf_pdf_to_json(input_path: str, output_path: str, pages: str = "all") -> str:
    """Export a local PDF to Document IR JSON."""
    return run_pdf_to_json(input_path, output_path=output_path, pages=pages).model_dump_json()


def pdf_pdf_to_markdown(input_path: str, output_path: str, pages: str = "all") -> str:
    """Export a local PDF to cited Markdown via Document IR."""
    return run_pdf_to_markdown(input_path, output_path=output_path, pages=pages).model_dump_json()


def pdf_metadata_read(input_path: str) -> str:
    """Read local PDF document metadata."""
    return run_metadata_read(input_path).model_dump_json()


def pdf_metadata_update(input_path: str, metadata: dict[str, object], output_path: str) -> str:
    """Update local PDF metadata and write a new PDF."""
    return run_metadata_update(input_path, metadata=metadata, output_path=output_path).model_dump_json()


def pdf_metadata_remove(input_path: str, output_path: str) -> str:
    """Remove local PDF metadata and write a new PDF."""
    return run_metadata_remove(input_path, output_path=output_path).model_dump_json()


def pdf_validate_output(path: str, expected_pages: int | None = None) -> str:
    """Validate generated local PDF output."""
    return run_validate_output(path, expected_pages=expected_pages).model_dump_json()


def pdf_render_check(path: str, pages: str = "all") -> str:
    """Render selected local PDF pages in memory to verify renderability."""
    return run_render_check(path, pages=pages).model_dump_json()


def pdf_blank_page_check(path: str, pages: str = "all") -> str:
    """Detect blank pages in a local PDF."""
    return run_blank_page_check(path, pages=pages).model_dump_json()


def pdf_ai_parse_lite(input_path: str, pages: str = "all") -> str:
    """Parse a local PDF text layer into Document IR."""
    return run_parse_lite(input_path, pages=pages).model_dump_json()


def pdf_ai_rag_ingest(
    input_path: str,
    index_path: str,
    pages: str = "all",
    max_chars: int = 1200,
    overlap_chars: int = 120,
) -> str:
    """Build a local cited keyword index for a PDF."""
    return run_rag_ingest(
        input_path,
        index_path=index_path,
        pages=pages,
        max_chars=max_chars,
        overlap_chars=overlap_chars,
    ).model_dump_json()


def pdf_ai_rag_query(index_path: str, query: str, top_k: int = 5) -> str:
    """Query a local PDF index and return extractive citations."""
    return run_rag_query(index_path, query=query, top_k=top_k).model_dump_json()


def pdf_ai_rag_chat(
    input_path: str,
    question: str,
    index_path: str | None = None,
    report_output_path: str | None = None,
    highlight_output_path: str | None = None,
    pages: str = "all",
    top_k: int = 5,
    max_chars: int = 1200,
    overlap_chars: int = 120,
    style_pack: str = "plain_report",
    highlight_color: str = "fff59d",
) -> str:
    """Ask a local PDF and return answer, citations, report, and highlights."""
    return run_rag_chat(
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
    ).model_dump_json()


def pdf_ai_rag_cite_answer(index_path: str, answer: str, top_k: int = 5) -> str:
    """Find page/bbox citations that support an answer from a local index."""
    return run_rag_cite_answer(index_path, answer=answer, top_k=top_k).model_dump_json()


def pdf_ai_rag_highlight_sources(
    index_path: str,
    output_path: str,
    answer: str | None = None,
    query: str | None = None,
    top_k: int = 5,
    highlight_color: str = "fff59d",
) -> str:
    """Create a highlighted source PDF from local RAG citations."""
    return run_rag_highlight_sources(
        index_path,
        output_path=output_path,
        answer=answer,
        query=query,
        top_k=top_k,
        highlight_color=highlight_color,
    ).model_dump_json()


def pdf_ai_rag_export_report(
    index_path: str,
    output_path: str,
    question: str,
    answer: str | None = None,
    top_k: int = 5,
    include_citations: bool = True,
    title: str | None = None,
    style_pack: str = "plain_report",
) -> str:
    """Create a cited local PDF report from a RAG answer."""
    return run_rag_export_report(
        index_path,
        output_path=output_path,
        question=question,
        answer=answer,
        top_k=top_k,
        include_citations=include_citations,
        title=title,
        style_pack=style_pack,
    ).model_dump_json()


def pdf_ai_rag_search(index_path: str, query: str, top_k: int = 5) -> str:
    """Search a local PDF index and return cited chunks."""
    return run_rag_search(index_path, query=query, top_k=top_k).model_dump_json()


def run_mcp_server(transport: Literal["stdio", "sse", "streamable-http"] = "stdio") -> None:
    create_mcp_server().run(transport=transport)
