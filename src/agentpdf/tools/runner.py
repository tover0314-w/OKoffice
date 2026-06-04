from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from agentpdf.agents.claude_code import setup_claude_code
from agentpdf.agents.codex import setup_codex
from agentpdf.agents.kilo_code import setup_kilo_code
from agentpdf.agents.openclaw import setup_openclaw
from agentpdf.artifacts.bundle import (
    build_artifact_graph,
    build_artifact_source_map,
    create_artifact_manifest,
    export_artifact_bundle,
    verify_artifact_bundle,
)
from agentpdf.authoring.design import select_design_tokens
from agentpdf.authoring.html_deck import write_authoring_html_package, write_raw_html_package
from agentpdf.authoring.pages import write_pages_from_storyboard
from agentpdf.authoring.qa import visual_report
from agentpdf.authoring.research import extract_evidence_cards, normalize_source_cards, plan_research
from agentpdf.authoring.revise import revise_pages
from agentpdf.authoring.router import plan_authoring_route
from agentpdf.authoring.storyboard import plan_storyboard
from agentpdf.authoring.workflow import plan_research_deck_workflow
from agentpdf.compose.blocks import (
    add_appendix_to_pdf,
    add_citation_to_pdf,
    add_code_block_to_pdf,
    add_figure_to_pdf,
    add_media_reference_to_pdf,
    add_slide_to_pdf,
    add_table_to_pdf,
)
from agentpdf.compose.context import (
    compose_from_context,
    list_target_profiles,
    plan_composition,
    render_composition_ir,
    select_target_profile,
    validate_target_profile,
)
from agentpdf.compare.local import semantic_diff_pdf, version_report_pdf, visual_diff_pdf
from agentpdf.conversion.local import (
    docx_to_pdf,
    html_to_pdf,
    pdf_to_docx,
    pdf_to_html,
    pdf_to_pptx,
    pdf_to_xlsx,
    pptx_to_pdf,
    url_to_pdf,
    xlsx_to_pdf,
)
from agentpdf.context.classify import classify_context
from agentpdf.context.image import analyze_image
from agentpdf.context.packet import (
    build_context_packet,
    build_reusable_context_packet,
    create_code_snapshot,
    ingest_context_item,
    profile_data_source,
)
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
from agentpdf.evidence.citations import cite_claims
from agentpdf.evidence.coverage import create_coverage_report
from agentpdf.evidence.context_packet_report import create_context_packet_report
from agentpdf.evidence.source_map import map_sources
from agentpdf.forms.local import create_form_pdf, import_form_data_pdf, validate_form_pdf
from agentpdf.ir.semantic import (
    parse_charts_pdf,
    parse_figures_pdf,
    parse_formulas_pdf,
    parse_references_pdf,
)
from agentpdf.ocr_scan.local import (
    despeckle_pdf,
    multilingual_ocr_pdf,
    ocr_pdf,
    remove_existing_ocr_pdf,
    searchable_pdf,
    scan_to_pdf,
)
from agentpdf.optimize.local import subset_fonts_pdf, to_pdfa_pdf
from agentpdf.patch.transaction import (
    apply_patch_transaction,
    plan_patch_transaction,
    preview_patch_transaction,
    verify_patch_transaction,
)
from agentpdf.renderers.html_package import render_html_package
from agentpdf.security.local import (
    decrypt_authorized_pdf,
    encrypt_pdf,
    inspect_health_pdf,
    malware_scan_pdf,
    protect_pdf,
    redact_pdf,
    redaction_check_pdf,
    sanitize_pdf,
    sign_pdf,
    unlock_authorized_pdf,
    verify_redaction_pdf,
    verify_signature_pdf,
)
from agentpdf.core.pdf import (
    add_margin_pdf,
    add_page_numbers_pdf,
    add_shape_pdf,
    add_text_watermark_pdf,
    add_underlay_pdf,
    booklet_pdf,
    compress_pdf,
    create_markdown_pdf,
    create_text_pdf,
    extract_fonts_pdf,
    extract_images_pdf,
    extract_pages_pdf,
    extract_text_pdf,
    freehand_draw_pdf,
    image_to_pdf,
    inspect_pdf,
    inspect_pdf_pages,
    insert_blank_pages_pdf,
    merge_pdfs,
    n_up_pdf,
    page_info_pdf,
    read_metadata_pdf,
    remove_pages_pdf,
    remove_metadata_pdf,
    remove_unused_objects_pdf,
    repair_pdf,
    resize_pages_pdf,
    render_pdf,
    reorder_pages_pdf,
    rotate_pages_pdf,
    split_pdf,
    strikeout_pdf,
    underline_pdf,
    update_metadata_pdf,
    update_outline_pdf,
    validate_pdfa_pdf,
)
from agentpdf.ir.lite import parse_lite_pdf, write_document_ir_json, write_document_ir_markdown
from agentpdf.office.deck import create_deck_from_outline, inspect_deck_presentation, validate_deck_presentation
from agentpdf.office.context import build_office_context_packet
from agentpdf.office.inspect import inspect_office_file
from agentpdf.office.sheet import (
    extract_sheet_tables,
    inspect_sheet_workbook,
    profile_sheet_data,
    read_sheet_workbook,
    validate_sheet_workbook,
    write_sheet_workbook,
)
from agentpdf.office.word import extract_word_tables, inspect_word_document
from agentpdf.office.workflows import board_pack, extract_to_sheet, sheet_to_deck, verify_board_pack
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
from agentpdf.validation.pdf import (
    blank_page_check_pdf,
    render_check_pdf,
    validate_pdf,
    visual_diff_check_pdf,
)
from agentpdf.workflows.planner import plan_workflow
from agentpdf.workflows.reporter import create_workflow_report
from agentpdf.workflows.createpdf import createpdf_html_first
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


def run_office_inspect_file(path: str | Path) -> ToolResult:
    return inspect_office_file(path)


def run_office_context_build_packet(
    files: list[str | Path],
    output_path: str | Path | None = None,
    title: str | None = None,
    intent: str | None = None,
) -> ToolResult:
    return build_office_context_packet(files, output_path, title=title, intent=intent)


def run_office_workflow_extract_to_sheet(
    input_paths: list[str | Path],
    output_path: str | Path,
    context_packet_path: str | Path | None = None,
) -> ToolResult:
    return extract_to_sheet(input_paths, output_path, context_packet_path=context_packet_path)


def run_office_workflow_sheet_to_deck(
    workbook_path: str | Path,
    output_path: str | Path,
    title: str | None = None,
    max_rows_per_sheet: int = 100,
) -> ToolResult:
    return sheet_to_deck(
        workbook_path,
        output_path,
        title=title,
        max_rows_per_sheet=max_rows_per_sheet,
    )


def run_office_workflow_board_pack(
    files: list[str | Path],
    output_path: str | Path,
    title: str | None = None,
) -> ToolResult:
    return board_pack(files, output_path, title=title)


def run_office_bundle_verify(bundle_path: str | Path) -> ToolResult:
    return verify_board_pack(bundle_path)


def run_word_inspect_document(path: str | Path) -> ToolResult:
    return inspect_word_document(path)


def run_word_extract_tables(path: str | Path) -> ToolResult:
    return extract_word_tables(path)


def run_sheet_inspect_workbook(path: str | Path) -> ToolResult:
    return inspect_sheet_workbook(path)


def run_sheet_read_workbook(path: str | Path, max_rows_per_sheet: int = 100) -> ToolResult:
    return read_sheet_workbook(path, max_rows_per_sheet=max_rows_per_sheet)


def run_sheet_profile_data(
    path: str | Path,
    max_rows_per_sheet: int = 100,
    include_source_refs: bool = False,
) -> ToolResult:
    return profile_sheet_data(
        path,
        max_rows_per_sheet=max_rows_per_sheet,
        include_source_refs=include_source_refs,
    )


def run_sheet_extract_tables(path: str | Path) -> ToolResult:
    return extract_sheet_tables(path)


def run_sheet_write_workbook(data: dict[str, object] | list[dict[str, object]], output_path: str | Path) -> ToolResult:
    return write_sheet_workbook(data, output_path)


def run_sheet_validate_workbook(path: str | Path) -> ToolResult:
    return validate_sheet_workbook(path)


def run_deck_inspect_presentation(path: str | Path) -> ToolResult:
    return inspect_deck_presentation(path)


def run_deck_create_from_outline(outline: dict[str, object], output_path: str | Path) -> ToolResult:
    return create_deck_from_outline(outline, output_path)


def run_deck_validate_presentation(path: str | Path) -> ToolResult:
    return validate_deck_presentation(path)


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


def run_inspect_health(input_path: str | Path) -> ToolResult:
    try:
        return inspect_health_pdf(input_path)
    except AgentPDFException as exc:
        return _failed("pdf.inspect.health", exc.to_error())


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


def run_n_up(
    input_path: str | Path,
    output_path: str | Path,
    pages: str = "all",
    per_sheet: int = 2,
) -> ToolResult:
    try:
        return n_up_pdf(input_path, output_path=output_path, pages=pages, per_sheet=per_sheet)
    except AgentPDFException as exc:
        return _failed("pdf.organize.n_up", exc.to_error())


def run_booklet(input_path: str | Path, output_path: str | Path, pages: str = "all") -> ToolResult:
    try:
        return booklet_pdf(input_path, output_path=output_path, pages=pages)
    except AgentPDFException as exc:
        return _failed("pdf.organize.booklet", exc.to_error())


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


def run_remove_unused_objects(input_path: str | Path, output_path: str | Path) -> ToolResult:
    try:
        return remove_unused_objects_pdf(input_path, output_path=output_path)
    except AgentPDFException as exc:
        return _failed("pdf.optimize.remove_unused_objects", exc.to_error())


def run_validate_pdfa(input_path: str | Path) -> ToolResult:
    try:
        return validate_pdfa_pdf(input_path)
    except AgentPDFException as exc:
        return _failed("pdf.optimize.validate_pdfa", exc.to_error())


def run_subset_fonts(input_path: str | Path, output_path: str | Path) -> ToolResult:
    try:
        return subset_fonts_pdf(input_path, output_path=output_path)
    except AgentPDFException as exc:
        return _failed("pdf.optimize.subset_fonts", exc.to_error())


def run_to_pdfa(
    input_path: str | Path,
    output_path: str | Path,
    profile: str = "PDF/A-2B",
) -> ToolResult:
    try:
        return to_pdfa_pdf(input_path, output_path=output_path, profile=profile)
    except AgentPDFException as exc:
        return _failed("pdf.optimize.to_pdfa", exc.to_error())


def run_image_to_pdf(image_paths: list[str | Path], output_path: str | Path) -> ToolResult:
    try:
        return image_to_pdf(image_paths, output_path=output_path)
    except AgentPDFException as exc:
        return _failed("pdf.convert.image_to_pdf", exc.to_error())


def run_html_to_pdf(input_path: str | Path, output_path: str | Path) -> ToolResult:
    try:
        return html_to_pdf(input_path, output_path=output_path)
    except AgentPDFException as exc:
        return _failed("pdf.convert.html_to_pdf", exc.to_error())


def run_render_html_package(package_path: str | Path, output_path: str | Path) -> ToolResult:
    try:
        return render_html_package(package_path, output_path=output_path)
    except AgentPDFException as exc:
        return _failed("pdf.render.html_package", exc.to_error())


def run_url_to_pdf(
    url: str,
    output_path: str | Path,
    allow_private_hosts: bool = False,
    allow_file_urls: bool = False,
) -> ToolResult:
    try:
        return url_to_pdf(
            url,
            output_path=output_path,
            allow_private_hosts=allow_private_hosts,
            allow_file_urls=allow_file_urls,
        )
    except AgentPDFException as exc:
        return _failed("pdf.convert.url_to_pdf", exc.to_error())


def run_docx_to_pdf(input_path: str | Path, output_path: str | Path) -> ToolResult:
    try:
        return docx_to_pdf(input_path, output_path=output_path)
    except AgentPDFException as exc:
        return _failed("pdf.convert.docx_to_pdf", exc.to_error())


def run_pptx_to_pdf(input_path: str | Path, output_path: str | Path) -> ToolResult:
    try:
        return pptx_to_pdf(input_path, output_path=output_path)
    except AgentPDFException as exc:
        return _failed("pdf.convert.pptx_to_pdf", exc.to_error())


def run_xlsx_to_pdf(input_path: str | Path, output_path: str | Path) -> ToolResult:
    try:
        return xlsx_to_pdf(input_path, output_path=output_path)
    except AgentPDFException as exc:
        return _failed("pdf.convert.xlsx_to_pdf", exc.to_error())


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


def run_add_shape(
    input_path: str | Path,
    output_path: str | Path,
    shape: str,
    page: int,
    x: float,
    y: float,
    width: float,
    height: float,
    stroke_color: str = "#2563eb",
    fill_color: str | None = None,
    line_width: float = 1.5,
    opacity: float = 1.0,
) -> ToolResult:
    try:
        return add_shape_pdf(
            input_path,
            output_path=output_path,
            shape=shape,
            page=page,
            x=x,
            y=y,
            width=width,
            height=height,
            stroke_color=stroke_color,
            fill_color=fill_color,
            line_width=line_width,
            opacity=opacity,
        )
    except AgentPDFException as exc:
        return _failed("pdf.edit.add_shape", exc.to_error())


def run_underline(
    input_path: str | Path,
    output_path: str | Path,
    page: int,
    bbox: list[float],
    color: str = "#2563eb",
    line_width: float = 1.0,
) -> ToolResult:
    try:
        return underline_pdf(
            input_path,
            output_path=output_path,
            page=page,
            bbox=bbox,
            color=color,
            line_width=line_width,
        )
    except AgentPDFException as exc:
        return _failed("pdf.edit.underline", exc.to_error())


def run_strikeout(
    input_path: str | Path,
    output_path: str | Path,
    page: int,
    bbox: list[float],
    color: str = "#dc2626",
    line_width: float = 1.0,
) -> ToolResult:
    try:
        return strikeout_pdf(
            input_path,
            output_path=output_path,
            page=page,
            bbox=bbox,
            color=color,
            line_width=line_width,
        )
    except AgentPDFException as exc:
        return _failed("pdf.edit.strikeout", exc.to_error())


def run_freehand_draw(
    input_path: str | Path,
    output_path: str | Path,
    page: int,
    points: list[list[float]],
    stroke_color: str = "#2563eb",
    line_width: float = 1.5,
    opacity: float = 1.0,
) -> ToolResult:
    try:
        return freehand_draw_pdf(
            input_path,
            output_path=output_path,
            page=page,
            points=points,
            stroke_color=stroke_color,
            line_width=line_width,
            opacity=opacity,
        )
    except AgentPDFException as exc:
        return _failed("pdf.edit.freehand_draw", exc.to_error())


def run_resize_pages(
    input_path: str | Path,
    output_path: str | Path,
    width: float,
    height: float,
    pages: str = "all",
) -> ToolResult:
    try:
        return resize_pages_pdf(
            input_path,
            output_path=output_path,
            width=width,
            height=height,
            pages=pages,
        )
    except AgentPDFException as exc:
        return _failed("pdf.edit.resize_pages", exc.to_error())


def run_add_margin(
    input_path: str | Path,
    output_path: str | Path,
    margin: float = 0,
    pages: str = "all",
    top: float | None = None,
    right: float | None = None,
    bottom: float | None = None,
    left: float | None = None,
) -> ToolResult:
    try:
        return add_margin_pdf(
            input_path,
            output_path=output_path,
            margin=margin,
            pages=pages,
            top=top,
            right=right,
            bottom=bottom,
            left=left,
        )
    except AgentPDFException as exc:
        return _failed("pdf.edit.add_margin", exc.to_error())


def run_underlay(
    input_path: str | Path,
    output_path: str | Path,
    text: str,
    pages: str = "all",
    font_size: int = 72,
    opacity: float = 0.12,
    angle: int = 45,
    color: str = "#64748b",
) -> ToolResult:
    try:
        return add_underlay_pdf(
            input_path,
            output_path=output_path,
            text=text,
            pages=pages,
            font_size=font_size,
            opacity=opacity,
            angle=angle,
            color=color,
        )
    except AgentPDFException as exc:
        return _failed("pdf.edit.underlay", exc.to_error())


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
    context_classification_output_path: str | Path | None = None,
    context_report_output_path: str | Path | None = None,
    context_report_json_output_path: str | Path | None = None,
    bundle_output_path: str | Path | None = None,
    preferred_template_id: str | None = None,
    preferred_color_scheme: str | None = None,
    title: str | None = None,
    prompt: str | None = None,
    style_pack: str | None = None,
    renderer: str = "markdown",
    html_output_path: str | Path | None = None,
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
            context_classification_output_path=context_classification_output_path,
            context_report_output_path=context_report_output_path,
            context_report_json_output_path=context_report_json_output_path,
            bundle_output_path=bundle_output_path,
            preferred_template_id=preferred_template_id,
            preferred_color_scheme=preferred_color_scheme,
            title=title,
            prompt=prompt,
            style_pack=style_pack,
            renderer=renderer,
            html_output_path=html_output_path,
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
    renderer: str = "markdown",
    html_output_path: str | Path | None = None,
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
            renderer=renderer,
            html_output_path=html_output_path,
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


def run_context_ingest(
    context_item: dict[str, object],
    output_path: str | Path | None = None,
) -> ToolResult:
    try:
        return ingest_context_item(
            context_item,
            output_path=output_path,
        )
    except AgentPDFException as exc:
        return _failed("pdf.context.ingest", exc.to_error())


def run_context_packet(
    context_items: list[dict[str, object]],
    output_path: str | Path,
    title: str | None = None,
    intent: str | None = None,
) -> ToolResult:
    try:
        return build_reusable_context_packet(
            context_items,
            output_path=output_path,
            title=title,
            intent=intent,
        )
    except AgentPDFException as exc:
        return _failed("pdf.context.packet", exc.to_error())


def run_context_classify(
    context_packet: dict[str, object] | str | Path,
    target_profile: dict[str, object] | str | None = None,
    output_path: str | Path | None = None,
) -> ToolResult:
    try:
        return classify_context(
            context_packet,
            target_profile=target_profile,
            output_path=output_path,
        )
    except AgentPDFException as exc:
        return _failed("pdf.context.classify", exc.to_error())


def run_context_code_snapshot(
    path: str | Path,
    output_path: str | Path | None = None,
    label: str | None = None,
    role: str = "code_evidence",
    context_item_id: str | None = None,
    line_start: int | None = None,
    line_end: int | None = None,
    repository_root: str | Path | None = None,
    include_dependencies: bool = False,
) -> ToolResult:
    try:
        return create_code_snapshot(
            path=path,
            output_path=output_path,
            label=label,
            role=role,
            context_item_id=context_item_id,
            line_start=line_start,
            line_end=line_end,
            repository_root=repository_root,
            include_dependencies=include_dependencies,
        )
    except AgentPDFException as exc:
        return _failed("pdf.context.code_snapshot", exc.to_error())


def run_context_data_profile(
    path: str | Path,
    output_path: str | Path | None = None,
    label: str | None = None,
    role: str = "data_evidence",
    context_item_id: str | None = None,
    sheet: str | None = None,
    max_rows: int = 100,
) -> ToolResult:
    try:
        return profile_data_source(
            path=path,
            output_path=output_path,
            label=label,
            role=role,
            context_item_id=context_item_id,
            sheet=sheet,
            max_rows=max_rows,
        )
    except AgentPDFException as exc:
        return _failed("pdf.context.data_profile", exc.to_error())


def run_context_image_analyze(
    input_path: str | Path,
    languages: list[str] | None = None,
    run_ocr: bool = True,
    engine: str = "tesseract",
    psm: int = 6,
) -> ToolResult:
    try:
        return analyze_image(
            input_path,
            languages=languages,
            run_ocr=run_ocr,
            engine=engine,
            psm=psm,
        )
    except AgentPDFException as exc:
        return _failed("pdf.context.image_analyze", exc.to_error())


def run_compose_from_context(
    context_packet: dict[str, object] | str | Path,
    target_profile: dict[str, object] | str,
    output_path: str | Path,
    style_pack: str | None = None,
    title: str | None = None,
    renderer: str = "markdown",
    html_output_path: str | Path | None = None,
) -> ToolResult:
    try:
        return compose_from_context(
            context_packet,
            target_profile=target_profile,
            output_path=output_path,
            style_pack=style_pack,
            title=title,
            renderer=renderer,
            html_output_path=html_output_path,
        )
    except AgentPDFException as exc:
        return _failed("pdf.compose.from_context", exc.to_error())


def run_compose_plan(
    context_packet: dict[str, object] | str | Path,
    target_profile: dict[str, object] | str,
    output_path: str | Path | None = None,
    style_pack: str | None = None,
    title: str | None = None,
) -> ToolResult:
    try:
        return plan_composition(
            context_packet,
            target_profile=target_profile,
            output_path=output_path,
            style_pack=style_pack,
            title=title,
        )
    except AgentPDFException as exc:
        return _failed("pdf.compose.plan", exc.to_error())


def run_compose_render_ir(
    composition: dict[str, object] | str | Path,
    output_path: str | Path,
    style_pack: str | None = None,
    title: str | None = None,
) -> ToolResult:
    try:
        return render_composition_ir(
            composition,
            output_path=output_path,
            style_pack=style_pack,
            title=title,
        )
    except AgentPDFException as exc:
        return _failed("pdf.compose.render_ir", exc.to_error())


def run_compose_add_code_block(
    input_path: str | Path,
    output_path: str | Path,
    title: str,
    code: str,
    language: str = "text",
    source_refs: list[str] | None = None,
    block_id: str | None = None,
    target_slot: str | None = None,
    composition_path: str | Path | None = None,
    layer_manifest_path: str | Path | None = None,
    manifest_output_path: str | Path | None = None,
) -> ToolResult:
    try:
        return add_code_block_to_pdf(
            input_path=input_path,
            output_path=output_path,
            title=title,
            code=code,
            language=language,
            source_refs=source_refs,
            block_id=block_id,
            target_slot=target_slot,
            composition_path=composition_path,
            layer_manifest_path=layer_manifest_path,
            manifest_output_path=manifest_output_path,
        )
    except AgentPDFException as exc:
        return _failed("pdf.compose.add_code_block", exc.to_error())


def run_compose_add_table(
    input_path: str | Path,
    output_path: str | Path,
    title: str,
    columns: list[str],
    rows: list[list[object]],
    source_refs: list[str] | None = None,
    block_id: str | None = None,
    target_slot: str | None = None,
    composition_path: str | Path | None = None,
    layer_manifest_path: str | Path | None = None,
    manifest_output_path: str | Path | None = None,
) -> ToolResult:
    try:
        return add_table_to_pdf(
            input_path=input_path,
            output_path=output_path,
            title=title,
            columns=columns,
            rows=rows,
            source_refs=source_refs,
            block_id=block_id,
            target_slot=target_slot,
            composition_path=composition_path,
            layer_manifest_path=layer_manifest_path,
            manifest_output_path=manifest_output_path,
        )
    except AgentPDFException as exc:
        return _failed("pdf.compose.add_table", exc.to_error())


def run_compose_add_figure(
    input_path: str | Path,
    output_path: str | Path,
    title: str,
    image_path: str | Path,
    caption: str | None = None,
    source_refs: list[str] | None = None,
    block_id: str | None = None,
    target_slot: str | None = None,
    composition_path: str | Path | None = None,
    layer_manifest_path: str | Path | None = None,
    manifest_output_path: str | Path | None = None,
) -> ToolResult:
    try:
        return add_figure_to_pdf(
            input_path=input_path,
            output_path=output_path,
            title=title,
            image_path=image_path,
            caption=caption,
            source_refs=source_refs,
            block_id=block_id,
            target_slot=target_slot,
            composition_path=composition_path,
            layer_manifest_path=layer_manifest_path,
            manifest_output_path=manifest_output_path,
        )
    except AgentPDFException as exc:
        return _failed("pdf.compose.add_figure", exc.to_error())


def run_compose_add_appendix(
    input_path: str | Path,
    output_path: str | Path,
    title: str,
    markdown: str,
    source_refs: list[str] | None = None,
    block_id: str | None = None,
    target_slot: str | None = None,
    composition_path: str | Path | None = None,
    layer_manifest_path: str | Path | None = None,
    manifest_output_path: str | Path | None = None,
) -> ToolResult:
    try:
        return add_appendix_to_pdf(
            input_path=input_path,
            output_path=output_path,
            title=title,
            markdown=markdown,
            source_refs=source_refs,
            block_id=block_id,
            target_slot=target_slot,
            composition_path=composition_path,
            layer_manifest_path=layer_manifest_path,
            manifest_output_path=manifest_output_path,
        )
    except AgentPDFException as exc:
        return _failed("pdf.compose.add_appendix", exc.to_error())


def run_compose_add_citation(
    input_path: str | Path,
    output_path: str | Path,
    title: str,
    source: str,
    quote: str | None = None,
    page: str | None = None,
    source_refs: list[str] | None = None,
    block_id: str | None = None,
    target_slot: str | None = None,
    composition_path: str | Path | None = None,
    layer_manifest_path: str | Path | None = None,
    manifest_output_path: str | Path | None = None,
) -> ToolResult:
    try:
        return add_citation_to_pdf(
            input_path=input_path,
            output_path=output_path,
            title=title,
            source=source,
            quote=quote,
            page=page,
            source_refs=source_refs,
            block_id=block_id,
            target_slot=target_slot,
            composition_path=composition_path,
            layer_manifest_path=layer_manifest_path,
            manifest_output_path=manifest_output_path,
        )
    except AgentPDFException as exc:
        return _failed("pdf.compose.add_citation", exc.to_error())


def run_compose_add_media_reference(
    input_path: str | Path,
    output_path: str | Path,
    title: str,
    media_path: str | Path,
    media_kind: str = "media",
    transcript_excerpt: str | None = None,
    duration_seconds: float | int | None = None,
    chapter_count: int | None = None,
    keyframe_count: int | None = None,
    source_refs: list[str] | None = None,
    block_id: str | None = None,
    target_slot: str | None = None,
    composition_path: str | Path | None = None,
    layer_manifest_path: str | Path | None = None,
    manifest_output_path: str | Path | None = None,
) -> ToolResult:
    try:
        return add_media_reference_to_pdf(
            input_path=input_path,
            output_path=output_path,
            title=title,
            media_path=media_path,
            media_kind=media_kind,
            transcript_excerpt=transcript_excerpt,
            duration_seconds=duration_seconds,
            chapter_count=chapter_count,
            keyframe_count=keyframe_count,
            source_refs=source_refs,
            block_id=block_id,
            target_slot=target_slot,
            composition_path=composition_path,
            layer_manifest_path=layer_manifest_path,
            manifest_output_path=manifest_output_path,
        )
    except AgentPDFException as exc:
        return _failed("pdf.compose.add_media_reference", exc.to_error())


def run_compose_add_slide(
    input_path: str | Path,
    output_path: str | Path,
    title: str,
    body: list[str] | None = None,
    subtitle: str | None = None,
    code: str | None = None,
    table: dict[str, object] | None = None,
    image_path: str | Path | None = None,
    source_refs: list[str] | None = None,
    block_id: str | None = None,
    target_slot: str | None = None,
    composition_path: str | Path | None = None,
    layer_manifest_path: str | Path | None = None,
    manifest_output_path: str | Path | None = None,
) -> ToolResult:
    try:
        return add_slide_to_pdf(
            input_path=input_path,
            output_path=output_path,
            title=title,
            body=body,
            subtitle=subtitle,
            code=code,
            table=table,
            image_path=image_path,
            source_refs=source_refs,
            block_id=block_id,
            target_slot=target_slot,
            composition_path=composition_path,
            layer_manifest_path=layer_manifest_path,
            manifest_output_path=manifest_output_path,
        )
    except AgentPDFException as exc:
        return _failed("pdf.compose.add_slide", exc.to_error())


def run_target_profiles(output_path: str | Path | None = None) -> ToolResult:
    try:
        return list_target_profiles(output_path=output_path)
    except AgentPDFException as exc:
        return _failed("pdf.target.profiles", exc.to_error())


def run_select_target_profile(
    goal: str = "",
    context_packet: dict[str, object] | str | Path | None = None,
    preferred_profile: str | None = None,
    output_path: str | Path | None = None,
) -> ToolResult:
    try:
        return select_target_profile(
            goal=goal,
            context_packet=context_packet,
            preferred_profile=preferred_profile,
            output_path=output_path,
        )
    except AgentPDFException as exc:
        return _failed("pdf.target.select_profile", exc.to_error())


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


def run_agent_setup_codex(
    output_path: str | Path | None = None,
    safe_root: str = ".",
    command: str = "okpdf",
    args_prefix: list[str] | None = None,
    server_name: str = "agentpdf",
) -> ToolResult:
    try:
        return setup_codex(
            output_path=output_path,
            safe_root=safe_root,
            command=command,
            args_prefix=args_prefix,
            server_name=server_name,
        )
    except AgentPDFException as exc:
        return _failed("agent.setup.codex", exc.to_error())


def run_agent_setup_kilo_code(
    output_path: str | Path | None = None,
    safe_root: str = ".",
    command: str = "okpdf",
    args_prefix: list[str] | None = None,
    server_name: str = "agentpdf",
) -> ToolResult:
    try:
        return setup_kilo_code(
            output_path=output_path,
            safe_root=safe_root,
            command=command,
            args_prefix=args_prefix,
            server_name=server_name,
        )
    except AgentPDFException as exc:
        return _failed("agent.setup.kilo_code", exc.to_error())


def run_agent_setup_openclaw(
    output_path: str | Path | None = None,
    safe_root: str = ".",
    command: str = "okpdf",
    args_prefix: list[str] | None = None,
    server_name: str = "agentpdf",
) -> ToolResult:
    try:
        return setup_openclaw(
            output_path=output_path,
            safe_root=safe_root,
            command=command,
            args_prefix=args_prefix,
            server_name=server_name,
        )
    except AgentPDFException as exc:
        return _failed("agent.setup.openclaw", exc.to_error())


def run_evidence_coverage_report(
    composition: dict[str, object] | str | Path,
    output_path: str | Path | None = None,
) -> ToolResult:
    try:
        return create_coverage_report(composition, output_path=output_path)
    except AgentPDFException as exc:
        return _failed("pdf.evidence.coverage_report", exc.to_error())


def run_evidence_map_sources(
    composition: dict[str, object] | str | Path | None = None,
    blocks: list[dict[str, object]] | None = None,
    claims: list[dict[str, object]] | None = None,
    context_packet: dict[str, object] | str | Path | None = None,
    output_path: str | Path | None = None,
) -> ToolResult:
    try:
        return map_sources(
            composition=composition,
            blocks=blocks,
            claims=claims,
            context_packet=context_packet,
            output_path=output_path,
        )
    except AgentPDFException as exc:
        return _failed("pdf.evidence.map_sources", exc.to_error())


def run_evidence_cite_claims(
    claims: list[dict[str, object]],
    composition: dict[str, object] | str | Path | None = None,
    source_map: dict[str, object] | list[dict[str, object]] | str | Path | None = None,
    context_packet: dict[str, object] | str | Path | None = None,
    output_path: str | Path | None = None,
) -> ToolResult:
    try:
        return cite_claims(
            claims=claims,
            composition=composition,
            source_map=source_map,
            context_packet=context_packet,
            output_path=output_path,
        )
    except AgentPDFException as exc:
        return _failed("pdf.evidence.cite_claims", exc.to_error())


def run_context_packet_report(
    context_packet: dict[str, object] | str | Path,
    output_path: str | Path,
    report_output_path: str | Path | None = None,
    title: str | None = None,
    style_pack: str = "paper_ink",
) -> ToolResult:
    try:
        return create_context_packet_report(
            context_packet,
            output_path=output_path,
            report_output_path=report_output_path,
            title=title,
            style_pack=style_pack,
        )
    except AgentPDFException as exc:
        return _failed("pdf.evidence.context_packet_report", exc.to_error())


def run_artifacts_manifest(
    artifact_paths: list[str | Path],
    output_path: str | Path | None = None,
    title: str | None = None,
    metadata: dict[str, object] | None = None,
) -> ToolResult:
    try:
        return create_artifact_manifest(
            artifact_paths=artifact_paths,
            output_path=output_path,
            title=title,
            metadata=metadata,
        )
    except AgentPDFException as exc:
        return _failed("pdf.artifacts.manifest", exc.to_error())


def run_artifacts_graph(
    artifact_manifest_path: str | Path | None = None,
    artifact_paths: list[str | Path] | None = None,
    output_path: str | Path | None = None,
    title: str | None = None,
) -> ToolResult:
    try:
        return build_artifact_graph(
            artifact_manifest_path=artifact_manifest_path,
            artifact_paths=artifact_paths,
            output_path=output_path,
            title=title,
        )
    except AgentPDFException as exc:
        return _failed("pdf.artifacts.graph", exc.to_error())


def run_artifacts_source_map(
    composition: dict[str, object] | str | Path | None = None,
    composition_path: str | Path | None = None,
    source_map: dict[str, object] | list[dict[str, object]] | str | Path | None = None,
    source_map_path: str | Path | None = None,
    context_packet: dict[str, object] | str | Path | None = None,
    context_packet_path: str | Path | None = None,
    artifact_manifest_path: str | Path | None = None,
    artifact_paths: list[str | Path] | None = None,
    output_path: str | Path | None = None,
    title: str | None = None,
) -> ToolResult:
    try:
        return build_artifact_source_map(
            composition=composition,
            composition_path=composition_path,
            source_map=source_map,
            source_map_path=source_map_path,
            context_packet=context_packet,
            context_packet_path=context_packet_path,
            artifact_manifest_path=artifact_manifest_path,
            artifact_paths=artifact_paths,
            output_path=output_path,
            title=title,
        )
    except AgentPDFException as exc:
        return _failed("pdf.artifacts.source_map", exc.to_error())


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


def run_extract_fonts(input_path: str | Path, pages: str = "all") -> ToolResult:
    try:
        return extract_fonts_pdf(input_path, pages=pages)
    except AgentPDFException as exc:
        return _failed("pdf.convert.extract_fonts", exc.to_error())


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


def run_pdf_to_html(
    input_path: str | Path,
    output_path: str | Path,
    pages: str = "all",
) -> ToolResult:
    try:
        return pdf_to_html(input_path, output_path=output_path, pages=pages)
    except AgentPDFException as exc:
        return _failed("pdf.convert.pdf_to_html", exc.to_error())


def run_pdf_to_docx(
    input_path: str | Path,
    output_path: str | Path,
    pages: str = "all",
) -> ToolResult:
    try:
        return pdf_to_docx(input_path, output_path=output_path, pages=pages)
    except AgentPDFException as exc:
        return _failed("pdf.convert.pdf_to_docx", exc.to_error())


def run_pdf_to_pptx(
    input_path: str | Path,
    output_path: str | Path,
    pages: str = "all",
) -> ToolResult:
    try:
        return pdf_to_pptx(input_path, output_path=output_path, pages=pages)
    except AgentPDFException as exc:
        return _failed("pdf.convert.pdf_to_pptx", exc.to_error())


def run_pdf_to_xlsx(
    input_path: str | Path,
    output_path: str | Path,
    pages: str = "all",
) -> ToolResult:
    try:
        return pdf_to_xlsx(input_path, output_path=output_path, pages=pages)
    except AgentPDFException as exc:
        return _failed("pdf.convert.pdf_to_xlsx", exc.to_error())


def run_metadata_read(input_path: str | Path) -> ToolResult:
    try:
        return read_metadata_pdf(input_path)
    except AgentPDFException as exc:
        return _failed("pdf.metadata.read", exc.to_error())


def run_metadata_page_info(input_path: str | Path, pages: str = "all") -> ToolResult:
    try:
        return page_info_pdf(input_path, pages=pages)
    except AgentPDFException as exc:
        return _failed("pdf.metadata.page_info", exc.to_error())


def run_metadata_update(
    input_path: str | Path,
    metadata: dict[str, object],
    output_path: str | Path,
) -> ToolResult:
    try:
        return update_metadata_pdf(input_path, metadata=metadata, output_path=output_path)
    except AgentPDFException as exc:
        return _failed("pdf.metadata.update", exc.to_error())


def run_metadata_update_outline(
    input_path: str | Path,
    outline: list[dict[str, object]],
    output_path: str | Path,
) -> ToolResult:
    try:
        return update_outline_pdf(input_path, outline=outline, output_path=output_path)
    except AgentPDFException as exc:
        return _failed("pdf.metadata.update_outline", exc.to_error())


def run_metadata_remove(input_path: str | Path, output_path: str | Path) -> ToolResult:
    try:
        return remove_metadata_pdf(input_path, output_path=output_path)
    except AgentPDFException as exc:
        return _failed("pdf.metadata.remove", exc.to_error())


def run_security_remove_metadata(input_path: str | Path, output_path: str | Path) -> ToolResult:
    tool = "pdf.security.remove_metadata"
    try:
        result = remove_metadata_pdf(input_path, output_path=output_path)
    except AgentPDFException as exc:
        return _failed(tool, exc.to_error())
    return ToolResult(
        job_id=result.job_id,
        status=result.status,
        tool=tool,
        artifacts=[artifact.model_copy(update={"source_tool": tool}) for artifact in result.artifacts],
        validation=result.validation,
        warnings=result.warnings,
        usage={**result.usage, "security_action": "remove_metadata"},
        next_recommended_tools=["pdf.metadata.read", "pdf.validation.validate_output"],
    )


def run_security_protect(
    input_path: str | Path,
    output_path: str | Path,
    password: str,
    owner_password: str | None = None,
) -> ToolResult:
    try:
        return protect_pdf(
            input_path,
            output_path=output_path,
            password=password,
            owner_password=owner_password,
        )
    except AgentPDFException as exc:
        return _failed("pdf.security.protect", exc.to_error())


def run_security_encrypt(
    input_path: str | Path,
    output_path: str | Path,
    password: str,
    owner_password: str | None = None,
) -> ToolResult:
    try:
        return encrypt_pdf(
            input_path,
            output_path=output_path,
            password=password,
            owner_password=owner_password,
        )
    except AgentPDFException as exc:
        return _failed("pdf.security.encrypt", exc.to_error())


def run_security_unlock_authorized(
    input_path: str | Path,
    output_path: str | Path,
    password: str,
) -> ToolResult:
    try:
        return unlock_authorized_pdf(input_path, output_path=output_path, password=password)
    except AgentPDFException as exc:
        return _failed("pdf.security.unlock_authorized", exc.to_error())


def run_security_decrypt_authorized(
    input_path: str | Path,
    output_path: str | Path,
    password: str,
) -> ToolResult:
    try:
        return decrypt_authorized_pdf(input_path, output_path=output_path, password=password)
    except AgentPDFException as exc:
        return _failed("pdf.security.decrypt_authorized", exc.to_error())


def run_security_sign(
    input_path: str | Path,
    output_path: str | Path,
    secret: str | None = None,
) -> ToolResult:
    try:
        return sign_pdf(input_path, output_path=output_path, secret=secret)
    except AgentPDFException as exc:
        return _failed("pdf.security.sign", exc.to_error())


def run_security_verify_signature(
    input_path: str | Path,
    signature_path: str | Path,
    secret: str | None = None,
) -> ToolResult:
    try:
        return verify_signature_pdf(input_path, signature_path=signature_path, secret=secret)
    except AgentPDFException as exc:
        return _failed("pdf.security.verify_signature", exc.to_error())


def run_security_malware_scan(input_path: str | Path) -> ToolResult:
    try:
        return malware_scan_pdf(input_path)
    except AgentPDFException as exc:
        return _failed("pdf.security.malware_scan", exc.to_error())


def run_security_sanitize(
    input_path: str | Path,
    output_path: str | Path,
    remove_metadata: bool = True,
) -> ToolResult:
    try:
        return sanitize_pdf(input_path, output_path=output_path, remove_metadata=remove_metadata)
    except AgentPDFException as exc:
        return _failed("pdf.security.sanitize", exc.to_error())


def run_security_redact(
    input_path: str | Path,
    output_path: str | Path,
    regions: list[dict[str, object]],
    fill_color: str = "#000000",
    render_scale: float = 2.0,
) -> ToolResult:
    try:
        return redact_pdf(
            input_path,
            output_path=output_path,
            regions=regions,
            fill_color=fill_color,
            render_scale=render_scale,
        )
    except AgentPDFException as exc:
        return _failed("pdf.security.redact", exc.to_error())


def run_security_verify_redaction(
    input_path: str | Path,
    search_terms: list[str] | None = None,
) -> ToolResult:
    try:
        return verify_redaction_pdf(input_path, search_terms=search_terms)
    except AgentPDFException as exc:
        return _failed("pdf.security.verify_redaction", exc.to_error())


def run_forms_create(output_path: str | Path, fields: list[dict[str, object]]) -> ToolResult:
    try:
        return create_form_pdf(output_path=output_path, fields=fields)
    except AgentPDFException as exc:
        return _failed("pdf.forms.create", exc.to_error())


def run_forms_import_data(
    input_path: str | Path,
    data: dict[str, object],
    output_path: str | Path,
) -> ToolResult:
    try:
        return import_form_data_pdf(input_path, data=data, output_path=output_path)
    except AgentPDFException as exc:
        return _failed("pdf.forms.import_data", exc.to_error())


def run_forms_validate(
    input_path: str | Path,
    required_fields: list[str] | None = None,
) -> ToolResult:
    try:
        return validate_form_pdf(input_path, required_fields=required_fields)
    except AgentPDFException as exc:
        return _failed("pdf.forms.validate", exc.to_error())


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


def run_page_count_check(path: str | Path, expected_pages: int) -> ToolResult:
    tool = "pdf.validation.page_count_check"
    try:
        report = validate_pdf(path, expected_pages=expected_pages)
    except AgentPDFException as exc:
        return _failed(tool, exc.to_error())
    return ToolResult(
        job_id=_job_id(),
        status="succeeded" if report.status == "passed" else "failed",
        tool=tool,
        validation=report,
        warnings=report.warnings,
        usage={
            "input": str(Path(path).resolve()),
            "expected_pages": expected_pages,
            "actual_pages": report.page_count,
        },
        next_recommended_tools=["pdf.inspect.document", "pdf.validation.render_check"],
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


def run_validation_visual_diff(
    before_path: str | Path,
    after_path: str | Path,
    pages: str = "all",
    max_difference_ratio: float = 0.001,
    render_scale: float = 0.5,
) -> ToolResult:
    tool = "pdf.validation.visual_diff"
    try:
        report, usage = visual_diff_check_pdf(
            before_path,
            after_path,
            pages=pages,
            max_difference_ratio=max_difference_ratio,
            render_scale=render_scale,
        )
    except AgentPDFException as exc:
        return _failed(tool, exc.to_error())
    return ToolResult(
        job_id=_job_id(),
        status="failed" if report.status == "failed" else "succeeded",
        tool=tool,
        validation=report,
        warnings=report.warnings,
        usage=usage,
        next_recommended_tools=["pdf.compare.semantic_diff", "pdf.evidence.coverage_report"],
    )


def run_validation_redaction_check(
    input_path: str | Path,
    search_terms: list[str] | None = None,
) -> ToolResult:
    try:
        return redaction_check_pdf(input_path, search_terms=search_terms)
    except AgentPDFException as exc:
        return _failed("pdf.validation.redaction_check", exc.to_error())


def run_parse_lite(input_path: str | Path, pages: str = "all") -> ToolResult:
    try:
        return parse_lite_pdf(input_path, pages=pages)
    except AgentPDFException as exc:
        return _failed("pdf.ai.parse.lite", exc.to_error())


def run_compare_semantic_diff(
    before_path: str | Path,
    after_path: str | Path,
    pages: str = "all",
) -> ToolResult:
    try:
        return semantic_diff_pdf(before_path, after_path, pages=pages)
    except AgentPDFException as exc:
        return _failed("pdf.compare.semantic_diff", exc.to_error())


def run_compare_visual_diff(
    before_path: str | Path,
    after_path: str | Path,
    pages: str = "all",
    max_difference_ratio: float = 0.001,
    render_scale: float = 0.5,
) -> ToolResult:
    try:
        return visual_diff_pdf(
            before_path,
            after_path,
            pages=pages,
            max_difference_ratio=max_difference_ratio,
            render_scale=render_scale,
        )
    except AgentPDFException as exc:
        return _failed("pdf.compare.visual_diff", exc.to_error())


def run_compare_version_report(
    before_path: str | Path,
    after_path: str | Path,
    output_path: str | Path | None = None,
    pages: str = "all",
) -> ToolResult:
    try:
        return version_report_pdf(
            before_path,
            after_path,
            output_path=output_path,
            pages=pages,
        )
    except AgentPDFException as exc:
        return _failed("pdf.compare.version_report", exc.to_error())


def run_parse_figures(input_path: str | Path, pages: str = "all") -> ToolResult:
    try:
        return parse_figures_pdf(input_path, pages=pages)
    except AgentPDFException as exc:
        return _failed("pdf.ai.parse.figures", exc.to_error())


def run_parse_formulas(input_path: str | Path, pages: str = "all") -> ToolResult:
    try:
        return parse_formulas_pdf(input_path, pages=pages)
    except AgentPDFException as exc:
        return _failed("pdf.ai.parse.formulas", exc.to_error())


def run_parse_charts(input_path: str | Path, pages: str = "all") -> ToolResult:
    try:
        return parse_charts_pdf(input_path, pages=pages)
    except AgentPDFException as exc:
        return _failed("pdf.ai.parse.charts", exc.to_error())


def run_parse_references(input_path: str | Path, pages: str = "all") -> ToolResult:
    try:
        return parse_references_pdf(input_path, pages=pages)
    except AgentPDFException as exc:
        return _failed("pdf.ai.parse.references", exc.to_error())


def run_ocr_scan_to_pdf(image_paths: list[str | Path], output_path: str | Path) -> ToolResult:
    try:
        return scan_to_pdf(image_paths, output_path=output_path)
    except AgentPDFException as exc:
        return _failed("pdf.ocr_scan.scan_to_pdf", exc.to_error())


def run_ocr(
    input_path: str | Path,
    pages: str = "all",
    languages: list[str] | None = None,
    dpi: int = 200,
    engine: str = "tesseract",
    psm: int = 6,
) -> ToolResult:
    try:
        return ocr_pdf(
            input_path,
            pages=pages,
            languages=languages,
            dpi=dpi,
            engine=engine,
            psm=psm,
        )
    except AgentPDFException as exc:
        return _failed("pdf.ocr_scan.ocr", exc.to_error())


def run_ocr_searchable_pdf(
    input_path: str | Path,
    output_path: str | Path,
    pages: str = "all",
    languages: list[str] | None = None,
    dpi: int = 200,
    engine: str = "tesseract",
    psm: int = 6,
) -> ToolResult:
    try:
        return searchable_pdf(
            input_path,
            output_path=output_path,
            pages=pages,
            languages=languages,
            dpi=dpi,
            engine=engine,
            psm=psm,
        )
    except AgentPDFException as exc:
        return _failed("pdf.ocr_scan.searchable_pdf", exc.to_error())


def run_ocr_despeckle(input_path: str | Path, output_path: str | Path) -> ToolResult:
    try:
        return despeckle_pdf(input_path, output_path=output_path)
    except AgentPDFException as exc:
        return _failed("pdf.ocr_scan.despeckle", exc.to_error())


def run_ocr_remove_existing(input_path: str | Path, output_path: str | Path) -> ToolResult:
    try:
        return remove_existing_ocr_pdf(input_path, output_path=output_path)
    except AgentPDFException as exc:
        return _failed("pdf.ocr_scan.remove_existing_ocr", exc.to_error())


def run_ocr_multilingual(
    input_path: str | Path,
    output_path: str | Path,
    languages: list[str] | None = None,
) -> ToolResult:
    try:
        return multilingual_ocr_pdf(input_path, output_path=output_path, languages=languages)
    except AgentPDFException as exc:
        return _failed("pdf.ocr_scan.multilingual_ocr", exc.to_error())


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


def run_workflow_createpdf(
    *,
    pdf_output_path: str | Path,
    html_output_path: str | Path | None = None,
    html: str | None = None,
    html_path: str | Path | None = None,
    page_document: dict[str, object] | None = None,
    title: str | None = None,
    artifact_dir: str | Path | None = None,
    expected_page_count: int | None = None,
    pages: str = "all",
) -> ToolResult:
    try:
        return createpdf_html_first(
            pdf_output_path=pdf_output_path,
            html_output_path=html_output_path,
            html=html,
            html_path=html_path,
            page_document=page_document,
            title=title,
            artifact_dir=artifact_dir,
            expected_page_count=expected_page_count,
            pages=pages,
        )
    except AgentPDFException as exc:
        return _failed("pdf.workflow.createpdf", exc.to_error())


def run_authoring_plan(brief: dict[str, object]) -> ToolResult:
    try:
        return plan_authoring_route(brief)
    except AgentPDFException as exc:
        return _failed("pdf.authoring.plan", exc.to_error())


def run_storyboard_plan(
    brief: dict[str, object],
    authoring_plan: dict[str, object] | None = None,
    evidence_cards: list[dict[str, object]] | None = None,
) -> ToolResult:
    try:
        return plan_storyboard(
            brief=brief,
            authoring_plan=authoring_plan,
            evidence_cards=evidence_cards,
        )
    except AgentPDFException as exc:
        return _failed("pdf.storyboard.plan", exc.to_error())


def run_pages_write(
    brief: dict[str, object],
    storyboard: dict[str, object],
    evidence_cards: list[dict[str, object]] | None = None,
    design_tokens: dict[str, object] | None = None,
) -> ToolResult:
    try:
        return write_pages_from_storyboard(
            brief=brief,
            storyboard=storyboard,
            evidence_cards=evidence_cards,
            design_tokens=design_tokens,
        )
    except AgentPDFException as exc:
        return _failed("pdf.pages.write", exc.to_error())


def run_research_plan(brief: dict[str, object]) -> ToolResult:
    try:
        return plan_research(brief)
    except AgentPDFException as exc:
        return _failed("pdf.research.plan", exc.to_error())


def run_research_source_cards(
    sources: list[dict[str, object]] | None = None,
    brief: dict[str, object] | None = None,
) -> ToolResult:
    try:
        return normalize_source_cards(brief=brief, sources=sources)
    except AgentPDFException as exc:
        return _failed("pdf.research.source_cards", exc.to_error())


def run_research_evidence_cards(source_cards: list[dict[str, object]] | None = None) -> ToolResult:
    try:
        return extract_evidence_cards(source_cards=source_cards)
    except AgentPDFException as exc:
        return _failed("pdf.research.evidence_cards", exc.to_error())


def run_design_tokens(
    theme: str = "business_tech",
    overrides: dict[str, object] | None = None,
) -> ToolResult:
    return select_design_tokens(theme=theme, overrides=overrides)


def run_pages_revise(
    page_document: dict[str, object],
    revisions: list[dict[str, object]] | None = None,
    design_tokens: dict[str, object] | None = None,
) -> ToolResult:
    try:
        return revise_pages(
            page_document=page_document,
            revisions=revisions,
            design_tokens=design_tokens,
        )
    except AgentPDFException as exc:
        return _failed("pdf.pages.revise", exc.to_error())


def run_create_html_package(
    page_document: dict[str, object] | None,
    html_output_path: str | Path,
    title: str | None = None,
    html: str | None = None,
    html_path: str | Path | None = None,
) -> ToolResult:
    try:
        if page_document:
            return write_authoring_html_package(
                page_document=page_document,
                html_output_path=html_output_path,
                title=title,
            )
        return write_raw_html_package(
            html_source=html,
            html_input_path=html_path,
            html_output_path=html_output_path,
            title=title,
        )
    except AgentPDFException as exc:
        return _failed("pdf.create.html_package", exc.to_error())


def run_qa_visual_report(
    input_path: str | Path,
    expected_page_count: int | None = None,
    html_package_manifest_path: str | Path | None = None,
    pages: str = "all",
) -> ToolResult:
    try:
        return visual_report(
            input_path=input_path,
            expected_page_count=expected_page_count,
            html_package_manifest_path=html_package_manifest_path,
            pages=pages,
        )
    except AgentPDFException as exc:
        return _failed("pdf.qa.visual_report", exc.to_error())


def run_workflow_research_deck(
    brief: dict[str, object],
    evidence_cards: list[dict[str, object]] | None = None,
    html_output_path: str = "<deck.html>",
    pdf_output_path: str = "<deck.pdf>",
    artifact_dir: str | Path | None = None,
    execute: bool = False,
) -> ToolResult:
    try:
        plan = plan_research_deck_workflow(
            brief=brief,
            evidence_cards=evidence_cards,
            html_output_path=html_output_path,
            pdf_output_path=pdf_output_path,
        )
        workflow = dict(plan.usage["workflow"])
        if artifact_dir is not None:
            workflow["artifact_dir"] = str(artifact_dir)
        if not execute:
            plan.usage["workflow"] = workflow
            return plan
        run = run_workflow(workflow)
        return ToolResult(
            job_id=run.job_id,
            status=run.status,
            tool="pdf.workflow.research_deck",
            artifacts=run.artifacts,
            validation=run.validation,
            warnings=run.warnings,
            usage={
                "workflow": workflow,
                "workflow_run": run.usage.get("workflow_run", {}),
            },
            next_recommended_tools=["pdf.workflow.report"],
            error=run.error,
        )
    except AgentPDFException as exc:
        return _failed("pdf.workflow.research_deck", exc.to_error())


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
