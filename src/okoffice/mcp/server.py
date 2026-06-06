from __future__ import annotations

import json

from typing import Literal

from mcp.server.fastmcp import FastMCP

from okoffice.tools.registry import load_tool_manifest
from okoffice.tools.registry_okoffice import load_okoffice_manifest
from okoffice.tools.runner import (
    run_add_margin,
    run_add_shape,
    run_underlay,
    run_agent_setup_claude_code,
    run_agent_setup_codex,
    run_agent_setup_kilo_code,
    run_agent_setup_openclaw,
    run_agent_setup_cursor,
    run_agent_setup_openai_agents,
    run_artifacts_export_bundle,
    run_artifacts_graph,
    run_artifacts_manifest,
    run_artifacts_source_map,
    run_artifacts_verify_bundle,
    run_authoring_plan,
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
    run_deck_compose_plan,
    run_deck_create_from_outline,
    run_deck_create_presentation,
    run_deck_export_pptx,
    run_deck_extract_charts,
    run_deck_extract_media,
    run_deck_extract_notes,
    run_deck_extract_shapes,
    run_deck_extract_text,
    run_deck_extract_theme,
    run_deck_inspect_presentation,
    run_deck_patch_apply,
    run_deck_render_html,
    run_deck_validate_contact_sheet,
    run_deck_validate_html_preview,
    run_deck_validation_presentation,
    run_deck_validate_presentation,
    run_create_markdown,
    run_create_text,
    run_create_agent,
    run_create_resume_pdf,
    run_create_from_prompt,
    run_create_from_template_pack,
    run_create_html_package,
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
    run_context_web_capture,
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
    run_office_bundle_verify,
    run_office_bundle_export,
    run_office_artifacts_bundle,
    run_office_context_build_packet,
    run_office_extract_schema,
    run_office_inspect_file,
    run_office_validation_package,
    run_office_workflow_board_pack,
    run_office_workflow_docset_to_sheet,
    run_office_workflow_extract_to_sheet,
    run_office_workflow_plan,
    run_office_workflow_sheet_to_deck,
    run_office_workflow_source_to_board_pack,
    run_office_workflow_source_to_deck,
    run_office_workflow_source_to_doc,
    run_office_workflow_multi_format_brief,
    run_deck_export_pdf,
    run_deck_edit_apply_theme,
    run_office_workers_status,
    run_page_numbers,
    run_watermark,
    run_patch_apply,
    run_patch_plan,
    run_patch_preview,
    run_patch_verify,
    run_composition_ir_patch_plan,
    run_composition_ir_patch_apply,
    run_composition_ir_patch_verify,
    run_design_tokens,
    run_pages_write,
    run_pages_revise,
    run_parse_charts,
    run_parse_figures,
    run_parse_formulas,
    run_parse_lite,
    run_parse_references,
    run_pdf_convert_to_docx,
    run_pdf_convert_to_pptx,
    run_pdf_convert_to_xlsx,
    run_pdf_extract_tables,
    run_pdf_read_document,
    run_office_workflow_extract_to_sheet,
    run_office_workflow_source_to_board_pack_alias,
    run_word_read_document,
    run_word_write_document,
    run_sheet_edit_patch,
    run_word_edit_patch,
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
    run_qa_visual_report,
    run_research_evidence_cards,
    run_research_plan,
    run_research_source_cards,
    run_remove_pages,
    run_render_html_package,
    run_remove_unused_objects,
    run_render,
    run_render_check,
    run_repair,
    run_reorder_pages,
    run_resize_pages,
    run_rotate_pages,
    run_ocr,
    run_ocr_despeckle,
    run_ocr_multilingual,
    run_ocr_remove_existing,
    run_ocr_scan_to_pdf,
    run_ocr_searchable_pdf,
    run_page_count_check,
    run_security_decrypt_authorized,
    run_security_encrypt,
    run_security_malware_scan,
    run_security_remove_metadata,
    run_security_sanitize,
    run_security_protect,
    run_security_redact,
    run_security_sign,
    run_security_unlock_authorized,
    run_security_verify_redaction,
    run_security_verify_signature,
    run_select_target_profile,
    run_sheet_create_evidence_workbook,
    run_sheet_extract_charts,
    run_sheet_extract_comments,
    run_sheet_extract_formulas,
    run_sheet_extract_named_ranges,
    run_sheet_extract_pivots,
    run_sheet_extract_tables,
    run_sheet_inspect_workbook,
    run_sheet_profile_data,
    run_sheet_read_workbook,
    run_sheet_validate_external_links,
    run_sheet_validate_formulas,
    run_sheet_validate_model_checks,
    run_sheet_validate_workbook,
    run_sheet_write_workbook,
    run_sheet_visualize_chart,
    run_patch_sheet_cells,
    run_patch_sheet_table,
    run_patch_sheet_formulas,
    run_patch_sheet_chart,
    run_review_sheet_model,
    run_review_sheet_number_consistency,
    run_split,
    run_strikeout,
    run_storyboard_plan,
    run_subset_fonts,
    run_target_profiles,
    run_underline,
    run_validate_output,
    run_validate_pdfa,
    run_validate_target_profile,
    run_validation_redaction_check,
    run_validation_visual_diff,
    run_ats_compliance,
    run_to_pdfa,
    run_workflow_createpdf,
    run_workflow_research_deck,
    run_workflow_report,
    run_workflow_run,
    run_workflow_plan,
    run_word_extract_comments,
    run_word_extract_fields,
    run_word_extract_outline,
    run_word_extract_revisions,
    run_word_extract_styles,
    run_word_extract_structure,
    run_word_extract_tables,
    run_word_extract_text,
    run_word_comment_review,
    run_word_convert_from_pdf,
    run_word_convert_to_pdf,
    run_word_inspect_document,
    run_word_create_report,
    run_create_word_document,
    run_create_word_memo,
    run_word_patch_apply,
    run_word_patch_plan,
    run_word_validate_document,
    run_xlsx_to_pdf,
    run_deck_review_story,
    run_deck_review_claims,
    run_deck_validate_notes,
    run_deck_validate_placeholders,
    run_deck_template_list,
    run_deck_template_preview,
    run_deck_create_from_template,
    run_deck_spec_lock_create,
    run_deck_spec_lock_check_drift,
    run_deck_animation_apply,
    run_word_review_style,
    run_word_validate_metadata,
    run_word_validate_accessibility,
    run_extract_office_claims,
    run_extract_office_entities,
    run_extract_office_obligations,
    run_inspect_office_batch,
    run_map_office_evidence_sources,
    run_report_office_evidence_coverage,
    run_classify_office_context,
    run_verify_office_evidence_citations,
    run_report_office_bundle,
    run_validate_office_output,
    run_plan_office_patch,
    run_preview_office_patch,
    run_verify_office_patch,
    run_review_and_patch_workflow,
    run_build_redaction_packet,
    run_build_artifact_graph,
)


def _project_root():
    from pathlib import Path
    return Path(__file__).resolve().parent.parent.parent.parent


def _schema_resource(server, uri, filename, schemas_dir):
    """Register a JSON schema file as an MCP resource."""
    def decorator(fn):
        server.resource(uri, mime_type="application/json")(fn)
        return fn
    return decorator


def pdf_create_resume_pdf(
    resume_data: dict,
    output_path: str,
    layout: str = "single_column",
    design_tokens: str | dict = "resume_modern",
    ats_mode: bool = True,
    title: str | None = None,
    renderer: str = "auto",
) -> str:
    """Create a structured resume PDF with ATS-safe layout and design tokens.

    Args:
        renderer: Backend to use — 'auto' (Typst if available, else ReportLab),
            'typst', or 'reportlab'.
    """
    return run_create_resume_pdf(
        resume_data=resume_data,
        output_path=output_path,
        layout=layout,
        design_tokens=design_tokens,
        ats_mode=ats_mode,
        title=title,
        renderer=renderer,
    ).model_dump_json()


def pdf_validation_ats_compliance_check(
    path: str,
    keywords: list[str] | None = None,
) -> str:
    """Validate a resume PDF for ATS compliance: text layer, fonts, layout, keywords."""
    return run_ats_compliance(path, keywords=keywords).model_dump_json()


def _infer_tool_annotations(name: str):
    """Auto-infer MCP safety annotations from tool name conventions."""
    from mcp.types import ToolAnnotations

    _READONLY = ToolAnnotations(readOnlyHint=True, idempotentHint=True, openWorldHint=False)
    _WRITE = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False)
    _DESTRUCTIVE = ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=False)
    _NETWORK = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=True)

    if any(p in name for p in ("web_capture", "url_to_pdf")):
        return _NETWORK
    if any(p in name for p in ("redact", "sanitize", "remove_pages", "remove_existing")):
        return _DESTRUCTIVE

    # Write tools that contain read-only-sounding substrings — exclude first
    _WRITE_DESPITE_PATTERN = (
        "extract_pages", "extract_images", "extract_to_sheet",
        "create_evidence", "create_plan_template", "create_template_preview",
        "create_validate_template", "artifacts_manifest", "artifacts_graph",
        "bundle_graph", "context_packet_report",
        "ocr_searchable_pdf", "scan_to_pdf",
    )
    if any(p in name for p in _WRITE_DESPITE_PATTERN):
        return _WRITE

    read_only_patterns = (
        "inspect", "validate", "check", "extract", "read_",
        "parse", "profile", "compare", "search", "query",
        "status", "manifest", "verify", "review",
        "evidence", "source_map", "graph",
        "design_tokens", "target_profile", "template_preview",
        "plan", "patch_preview",
    )
    if any(p in name for p in read_only_patterns):
        return _READONLY

    return _WRITE


def create_mcp_server() -> FastMCP:
    server = FastMCP(
        "okoffice",
        instructions=(
            "Local-first PDF tools for agents. Tools return structured OKoffice "
            "ToolResult JSON and write artifacts to explicit local paths."
        ),
    )

    # Wrap server.tool to auto-inject safety annotations based on tool name
    _original_tool = server.tool
    def _tool_with_annotations(name=None, **kwargs):
        if name and "annotations" not in kwargs:
            kwargs["annotations"] = _infer_tool_annotations(name)
        return _original_tool(name=name, **kwargs)
    server.tool = _tool_with_annotations
    server.tool(name="agentpdf_tool_manifest")(agentpdf_tool_manifest)  # compat alias, prefer okoffice_tool_manifest
    server.tool(name="okoffice_tool_manifest")(okoffice_tool_manifest)
    server.tool(name="agent_setup_claude_code")(agent_setup_claude_code)
    server.tool(name="agent_setup_codex")(agent_setup_codex)
    server.tool(name="agent_setup_kilo_code")(agent_setup_kilo_code)
    server.tool(name="agent_setup_openclaw")(agent_setup_openclaw)
    server.tool(name="agent_setup_cursor")(agent_setup_cursor)
    server.tool(name="agent_setup_openai_agents")(agent_setup_openai_agents)
    server.tool(name="office_inspect_file")(office_inspect_file)
    server.tool(name="office_context_build_packet")(office_context_build_packet)
    server.tool(name="office_extract_schema")(office_extract_schema)
    server.tool(name="office_validation_package")(office_validation_package)
    server.tool(name="office_workflow_plan")(office_workflow_plan)
    server.tool(name="office_workflow_docset_to_sheet")(office_workflow_docset_to_sheet)
    server.tool(name="office_workflow_extract_to_sheet")(office_workflow_extract_to_sheet)
    server.tool(name="office_workflow_sheet_to_deck")(office_workflow_sheet_to_deck)
    server.tool(name="office_workflow_board_pack")(office_workflow_board_pack)
    server.tool(name="office_workflow_source_to_board_pack")(office_workflow_source_to_board_pack)
    server.tool(name="office_workers_status")(office_workers_status)
    server.tool(name="office_bundle_export")(office_bundle_export)
    server.tool(name="office_bundle_verify")(office_bundle_verify)
    server.tool(name="word_inspect_document")(word_inspect_document)
    server.tool(name="word_validate_document")(word_validate_document)
    server.tool(name="word_review_style")(word_review_style)
    server.tool(name="word_validation_metadata")(word_validation_metadata)
    server.tool(name="word_validation_accessibility")(word_validation_accessibility)
    server.tool(name="word_create_report")(word_create_report)
    server.tool(name="word_create_document")(word_create_document)
    server.tool(name="word_create_memo")(word_create_memo)
    server.tool(name="word_patch_plan")(word_patch_plan)
    server.tool(name="word_patch_apply")(word_patch_apply)
    server.tool(name="word_extract_tables")(word_extract_tables)
    server.tool(name="word_extract_text")(word_extract_text)
    server.tool(name="word_extract_outline")(word_extract_outline)
    server.tool(name="word_extract_comments")(word_extract_comments)
    server.tool(name="word_extract_revisions")(word_extract_revisions)
    server.tool(name="word_extract_fields")(word_extract_fields)
    server.tool(name="word_extract_styles")(word_extract_styles)
    server.tool(name="sheet_inspect_workbook")(sheet_inspect_workbook)
    server.tool(name="sheet_read_workbook")(sheet_read_workbook)
    server.tool(name="sheet_profile_data")(sheet_profile_data)
    server.tool(name="sheet_extract_tables")(sheet_extract_tables)
    server.tool(name="sheet_extract_formulas")(sheet_extract_formulas)
    server.tool(name="sheet_extract_charts")(sheet_extract_charts)
    server.tool(name="sheet_extract_named_ranges")(sheet_extract_named_ranges)
    server.tool(name="sheet_extract_comments")(sheet_extract_comments)
    server.tool(name="sheet_extract_pivots")(sheet_extract_pivots)
    server.tool(name="sheet_create_evidence_workbook")(sheet_create_evidence_workbook)
    server.tool(name="sheet_write_workbook")(sheet_write_workbook)
    server.tool(name="sheet_validate_workbook")(sheet_validate_workbook)
    server.tool(name="sheet_validate_formulas")(sheet_validate_formulas)
    server.tool(name="sheet_validate_model_checks")(sheet_validate_model_checks)
    server.tool(name="sheet_validate_external_links")(sheet_validate_external_links)
    server.tool(name="sheet_patch_cells")(sheet_patch_cells)
    server.tool(name="sheet_patch_table")(sheet_patch_table)
    server.tool(name="sheet_patch_formulas")(sheet_patch_formulas)
    server.tool(name="sheet_patch_chart")(sheet_patch_chart)
    server.tool(name="sheet_review_model")(sheet_review_model)
    server.tool(name="sheet_review_number_consistency")(sheet_review_number_consistency)
    server.tool(name="deck_inspect_presentation")(deck_inspect_presentation)
    server.tool(name="deck_extract_text")(deck_extract_text)
    server.tool(name="deck_extract_notes")(deck_extract_notes)
    server.tool(name="deck_extract_shapes")(deck_extract_shapes)
    server.tool(name="deck_extract_media")(deck_extract_media)
    server.tool(name="deck_extract_charts")(deck_extract_charts)
    server.tool(name="deck_extract_theme")(deck_extract_theme)
    server.tool(name="deck_compose_plan")(deck_compose_plan)
    server.tool(name="deck_create_from_outline")(deck_create_from_outline)
    server.tool(name="deck_create_presentation")(deck_create_presentation)
    server.tool(name="deck_patch_apply")(deck_patch_apply)
    server.tool(name="deck_revise")(deck_revise)
    server.tool(name="deck_validate_contact_sheet")(deck_validate_contact_sheet)
    server.tool(name="deck_review_taste")(deck_review_taste)
    server.tool(name="deck_review_story")(deck_review_story)
    server.tool(name="deck_review_claims")(deck_review_claims)
    server.tool(name="deck_validation_notes")(deck_validation_notes)
    server.tool(name="deck_validation_placeholders")(deck_validation_placeholders)
    server.tool(name="deck_render_html")(deck_render_html)
    server.tool(name="deck_validation_html_preview")(deck_validation_html_preview)
    server.tool(name="deck_export_pptx")(deck_export_pptx)
    server.tool(name="deck_validate_presentation")(deck_validate_presentation)
    server.tool(name="deck_validation_presentation")(deck_validation_presentation)
    server.tool(name="deck_template_list")(deck_template_list)
    server.tool(name="deck_template_preview")(deck_template_preview)
    server.tool(name="deck_spec_lock_create")(deck_spec_lock_create)
    server.tool(name="deck_spec_lock_check_drift")(deck_spec_lock_check_drift)
    server.tool(name="deck_animation_apply")(deck_animation_apply)
    server.tool(name="deck_create_from_template")(deck_create_from_template)
    server.tool(name="pdf_inspect_document")(pdf_inspect_document)
    server.tool(name="pdf_inspect_pages")(pdf_inspect_pages)
    server.tool(name="pdf_inspect_health")(pdf_inspect_health)
    server.tool(name="pdf_workflow_plan")(pdf_workflow_plan)
    server.tool(name="pdf_workflow_run")(pdf_workflow_run)
    server.tool(name="pdf_workflow_report")(pdf_workflow_report)
    server.tool(name="pdf_workflow_createpdf")(pdf_workflow_createpdf)
    server.tool(name="pdf_workflow_research_deck")(pdf_workflow_research_deck)
    server.tool(name="pdf_authoring_plan")(pdf_authoring_plan)
    server.tool(name="pdf_storyboard_plan")(pdf_storyboard_plan)
    server.tool(name="pdf_pages_write")(pdf_pages_write)
    server.tool(name="pdf_research_plan")(pdf_research_plan)
    server.tool(name="pdf_research_source_cards")(pdf_research_source_cards)
    server.tool(name="pdf_research_evidence_cards")(pdf_research_evidence_cards)
    server.tool(name="pdf_design_tokens")(pdf_design_tokens)
    server.tool(name="pdf_pages_revise")(pdf_pages_revise)
    server.tool(name="pdf_create_html_package")(pdf_create_html_package)
    server.tool(name="pdf_qa_visual_report")(pdf_qa_visual_report)
    server.tool(name="pdf_merge")(pdf_merge)
    server.tool(name="pdf_split")(pdf_split)
    server.tool(name="pdf_extract_pages")(pdf_extract_pages)
    server.tool(name="pdf_remove_pages")(pdf_remove_pages)
    server.tool(name="pdf_rotate_pages")(pdf_rotate_pages)
    server.tool(name="pdf_reorder_pages")(pdf_reorder_pages)
    server.tool(name="pdf_insert_blank_pages")(pdf_insert_blank_pages)
    server.tool(name="pdf_n_up")(pdf_n_up)
    server.tool(name="pdf_booklet")(pdf_booklet)
    server.tool(name="pdf_optimize_compress")(pdf_optimize_compress)
    server.tool(name="pdf_optimize_repair")(pdf_optimize_repair)
    server.tool(name="pdf_optimize_remove_unused_objects")(pdf_optimize_remove_unused_objects)
    server.tool(name="pdf_optimize_subset_fonts")(pdf_optimize_subset_fonts)
    server.tool(name="pdf_optimize_to_pdfa")(pdf_optimize_to_pdfa)
    server.tool(name="pdf_optimize_validate_pdfa")(pdf_optimize_validate_pdfa)
    server.tool(name="pdf_image_to_pdf")(pdf_image_to_pdf)
    server.tool(name="pdf_html_to_pdf")(pdf_html_to_pdf)
    server.tool(name="pdf_render_html_package")(pdf_render_html_package)
    server.tool(name="pdf_url_to_pdf")(pdf_url_to_pdf)
    server.tool(name="pdf_docx_to_pdf")(pdf_docx_to_pdf)
    server.tool(name="pdf_pptx_to_pdf")(pdf_pptx_to_pdf)
    server.tool(name="pdf_xlsx_to_pdf")(pdf_xlsx_to_pdf)
    server.tool(name="pdf_watermark")(pdf_watermark)
    server.tool(name="pdf_add_page_numbers")(pdf_add_page_numbers)
    server.tool(name="pdf_add_shape")(pdf_add_shape)
    server.tool(name="pdf_underline")(pdf_underline)
    server.tool(name="pdf_strikeout")(pdf_strikeout)
    server.tool(name="pdf_freehand_draw")(pdf_freehand_draw)
    server.tool(name="pdf_resize_pages")(pdf_resize_pages)
    server.tool(name="pdf_add_margin")(pdf_add_margin)
    server.tool(name="pdf_underlay")(pdf_underlay)
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
    server.tool(name="pdf_context_ingest")(pdf_context_ingest)
    server.tool(name="pdf_context_packet")(pdf_context_packet)
    server.tool(name="pdf_context_web_capture")(pdf_context_web_capture)
    server.tool(name="pdf_context_classify")(pdf_context_classify)
    server.tool(name="pdf_context_code_snapshot")(pdf_context_code_snapshot)
    server.tool(name="pdf_context_data_profile")(pdf_context_data_profile)
    server.tool(name="pdf_context_image_analyze")(pdf_context_image_analyze)
    server.tool(name="pdf_compose_plan")(pdf_compose_plan)
    server.tool(name="pdf_compose_render_ir")(pdf_compose_render_ir)
    server.tool(name="pdf_compose_from_context")(pdf_compose_from_context)
    server.tool(name="pdf_compose_add_code_block")(pdf_compose_add_code_block)
    server.tool(name="pdf_compose_add_table")(pdf_compose_add_table)
    server.tool(name="pdf_compose_add_figure")(pdf_compose_add_figure)
    server.tool(name="pdf_compose_add_appendix")(pdf_compose_add_appendix)
    server.tool(name="pdf_compose_add_citation")(pdf_compose_add_citation)
    server.tool(name="pdf_compose_add_media_reference")(pdf_compose_add_media_reference)
    server.tool(name="pdf_compose_add_slide")(pdf_compose_add_slide)
    server.tool(name="pdf_target_profiles")(pdf_target_profiles)
    server.tool(name="pdf_target_select_profile")(pdf_target_select_profile)
    server.tool(name="pdf_target_validate_profile")(pdf_target_validate_profile)
    server.tool(name="pdf_evidence_map_sources")(pdf_evidence_map_sources)
    server.tool(name="pdf_evidence_cite_claims")(pdf_evidence_cite_claims)
    server.tool(name="pdf_evidence_coverage_report")(pdf_evidence_coverage_report)
    server.tool(name="pdf_evidence_context_packet_report")(pdf_evidence_context_packet_report)
    server.tool(name="pdf_artifacts_export_bundle")(pdf_artifacts_export_bundle)
    server.tool(name="pdf_artifacts_manifest")(pdf_artifacts_manifest)
    server.tool(name="pdf_artifacts_graph")(pdf_artifacts_graph)
    server.tool(name="pdf_artifacts_source_map")(pdf_artifacts_source_map)
    server.tool(name="pdf_artifacts_verify_bundle")(pdf_artifacts_verify_bundle)
    server.tool(name="pdf_patch_plan")(pdf_patch_plan)
    server.tool(name="pdf_patch_preview")(pdf_patch_preview)
    server.tool(name="pdf_patch_apply")(pdf_patch_apply)
    server.tool(name="pdf_patch_verify")(pdf_patch_verify)
    server.tool(name="pdf_patch_composition_ir_plan")(pdf_patch_composition_ir_plan)
    server.tool(name="pdf_patch_composition_ir_apply")(pdf_patch_composition_ir_apply)
    server.tool(name="pdf_patch_composition_ir_verify")(pdf_patch_composition_ir_verify)
    server.tool(name="pdf_render_pages")(pdf_render_pages)
    server.tool(name="pdf_extract_images")(pdf_extract_images)
    server.tool(name="pdf_extract_text")(pdf_extract_text)
    server.tool(name="pdf_extract_fonts")(pdf_extract_fonts)
    server.tool(name="pdf_pdf_to_json")(pdf_pdf_to_json)
    server.tool(name="pdf_pdf_to_markdown")(pdf_pdf_to_markdown)
    server.tool(name="pdf_pdf_to_html")(pdf_pdf_to_html)
    server.tool(name="pdf_pdf_to_docx")(pdf_pdf_to_docx)
    server.tool(name="pdf_pdf_to_pptx")(pdf_pdf_to_pptx)
    server.tool(name="pdf_pdf_to_xlsx")(pdf_pdf_to_xlsx)
    server.tool(name="pdf_metadata_read")(pdf_metadata_read)
    server.tool(name="pdf_metadata_page_info")(pdf_metadata_page_info)
    server.tool(name="pdf_metadata_update")(pdf_metadata_update)
    server.tool(name="pdf_metadata_update_outline")(pdf_metadata_update_outline)
    server.tool(name="pdf_metadata_remove")(pdf_metadata_remove)
    server.tool(name="pdf_security_remove_metadata")(pdf_security_remove_metadata)
    server.tool(name="pdf_security_protect")(pdf_security_protect)
    server.tool(name="pdf_security_encrypt")(pdf_security_encrypt)
    server.tool(name="pdf_security_unlock_authorized")(pdf_security_unlock_authorized)
    server.tool(name="pdf_security_decrypt_authorized")(pdf_security_decrypt_authorized)
    server.tool(name="pdf_security_sign")(pdf_security_sign)
    server.tool(name="pdf_security_verify_signature")(pdf_security_verify_signature)
    server.tool(name="pdf_security_malware_scan")(pdf_security_malware_scan)
    server.tool(name="pdf_security_sanitize")(pdf_security_sanitize)
    server.tool(name="pdf_security_redact")(pdf_security_redact)
    server.tool(name="pdf_security_verify_redaction")(pdf_security_verify_redaction)
    server.tool(name="pdf_validate_output")(pdf_validate_output)
    server.tool(name="pdf_page_count_check")(pdf_page_count_check)
    server.tool(name="pdf_render_check")(pdf_render_check)
    server.tool(name="pdf_blank_page_check")(pdf_blank_page_check)
    server.tool(name="pdf_compare_semantic_diff")(pdf_compare_semantic_diff)
    server.tool(name="pdf_compare_visual_diff")(pdf_compare_visual_diff)
    server.tool(name="pdf_compare_version_report")(pdf_compare_version_report)
    server.tool(name="pdf_validation_visual_diff")(pdf_validation_visual_diff)
    server.tool(name="pdf_validation_redaction_check")(pdf_validation_redaction_check)
    server.tool(name="pdf_ai_parse_lite")(pdf_ai_parse_lite)
    server.tool(name="pdf_ai_parse_figures")(pdf_ai_parse_figures)
    server.tool(name="pdf_ai_parse_formulas")(pdf_ai_parse_formulas)
    server.tool(name="pdf_ai_parse_charts")(pdf_ai_parse_charts)
    server.tool(name="pdf_ai_parse_references")(pdf_ai_parse_references)
    server.tool(name="pdf_forms_create")(pdf_forms_create)
    server.tool(name="pdf_forms_import_data")(pdf_forms_import_data)
    server.tool(name="pdf_forms_validate")(pdf_forms_validate)
    server.tool(name="pdf_ocr")(pdf_ocr)
    server.tool(name="pdf_ocr_searchable_pdf")(pdf_ocr_searchable_pdf)
    server.tool(name="pdf_ocr_scan_to_pdf")(pdf_ocr_scan_to_pdf)
    server.tool(name="pdf_ocr_despeckle")(pdf_ocr_despeckle)
    server.tool(name="pdf_ocr_remove_existing_ocr")(pdf_ocr_remove_existing_ocr)
    server.tool(name="pdf_ocr_multilingual_ocr")(pdf_ocr_multilingual_ocr)
    server.tool(name="pdf_ai_rag_ingest")(pdf_ai_rag_ingest)
    server.tool(name="pdf_ai_rag_cite_answer")(pdf_ai_rag_cite_answer)
    server.tool(name="pdf_ai_rag_chat")(pdf_ai_rag_chat)
    server.tool(name="pdf_ai_rag_export_report")(pdf_ai_rag_export_report)
    server.tool(name="pdf_ai_rag_highlight_sources")(pdf_ai_rag_highlight_sources)
    server.tool(name="pdf_ai_rag_query")(pdf_ai_rag_query)
    server.tool(name="pdf_ai_rag_search")(pdf_ai_rag_search)
    server.tool(name="pdf_create_resume_pdf")(pdf_create_resume_pdf)
    server.tool(name="pdf_validation_ats_compliance_check")(pdf_validation_ats_compliance_check)
    server.tool(name="office_extract_claims")(office_extract_claims)
    server.tool(name="office_extract_entities")(office_extract_entities)
    server.tool(name="office_extract_obligations")(office_extract_obligations)
    server.tool(name="office_inspect_batch")(office_inspect_batch)
    server.tool(name="office_evidence_map_sources")(office_evidence_map_sources)
    server.tool(name="office_evidence_coverage")(office_evidence_coverage)
    server.tool(name="office_context_classify")(office_context_classify)
    server.tool(name="office_evidence_verify_citations")(office_evidence_verify_citations)
    server.tool(name="office_bundle_report")(office_bundle_report)
    server.tool(name="office_validate_output")(office_validate_output)
    server.tool(name="office_patch_plan")(office_patch_plan)
    server.tool(name="office_patch_preview")(office_patch_preview)
    server.tool(name="office_patch_verify")(office_patch_verify)
    server.tool(name="office_workflow_review_and_patch")(office_workflow_review_and_patch)
    server.tool(name="office_workflow_redaction_packet")(office_workflow_redaction_packet)
    server.tool(name="office_bundle_graph")(office_bundle_graph)
    server.tool(name="office_artifacts_bundle")(office_artifacts_bundle)
    server.tool(name="word_extract_structure")(word_extract_structure)
    server.tool(name="word_convert_to_pdf")(word_convert_to_pdf)
    server.tool(name="word_convert_from_pdf")(word_convert_from_pdf)
    server.tool(name="pdf_read_document")(pdf_read_document)
    server.tool(name="pdf_convert_to_docx")(pdf_convert_to_docx)
    server.tool(name="pdf_convert_to_xlsx")(pdf_convert_to_xlsx)
    server.tool(name="pdf_convert_to_pptx")(pdf_convert_to_pptx)
    server.tool(name="office_workflow_source_to_deck")(office_workflow_source_to_deck)
    server.tool(name="office_workflow_source_to_doc")(office_workflow_source_to_doc)
    server.tool(name="deck_export_pdf")(deck_export_pdf_handler)
    server.tool(name="office_workflow_multi_format_brief")(office_workflow_multi_format_brief_handler)
    server.tool(name="word_comment_review")(word_comment_review_handler)
    server.tool(name="sheet_visualize_chart")(sheet_visualize_chart_handler)
    server.tool(name="deck_edit_apply_theme")(deck_edit_apply_theme_handler)
    server.tool(name="pdf_extract_tables")(pdf_extract_tables_handler)

    # Phase 5 alias tools
    server.tool(name="office_workflow_extract_to_sheet")(office_workflow_extract_to_sheet_handler)
    server.tool(name="office_workflow_source_to_board_pack")(office_workflow_source_to_board_pack_alias_handler)
    server.tool(name="word_read_document")(word_read_document_handler)
    server.tool(name="word_write_document")(word_write_document_handler)
    server.tool(name="sheet_edit_patch")(sheet_edit_patch_handler)
    server.tool(name="word_edit_patch")(word_edit_patch_handler)

    # Schema resources for agents
    _schemas_dir = _project_root() / "schemas"

    @_schema_resource(server, "okoffice://schemas/resume-data", "resume-data.schema.json", _schemas_dir)
    def _resume_data_schema() -> str:
        return (_schemas_dir / "resume-data.schema.json").read_text(encoding="utf-8")

    @_schema_resource(server, "okoffice://schemas/resume-layout", "resume-section-layout.schema.json", _schemas_dir)
    def _resume_layout_schema() -> str:
        return (_schemas_dir / "resume-section-layout.schema.json").read_text(encoding="utf-8")

    @_schema_resource(server, "okoffice://schemas/resume-design-tokens", "resume-design-tokens.schema.json", _schemas_dir)
    def _resume_design_tokens_schema() -> str:
        return (_schemas_dir / "resume-design-tokens.schema.json").read_text(encoding="utf-8")

    @_schema_resource(server, "okoffice://schemas/composition-ir", "composition-ir.schema.json", _schemas_dir)
    def _composition_ir_schema() -> str:
        return (_schemas_dir / "composition-ir.schema.json").read_text(encoding="utf-8")

    @_schema_resource(server, "okoffice://schemas/context-packet", "context-packet.schema.json", _schemas_dir)
    def _context_packet_schema() -> str:
        return (_schemas_dir / "context-packet.schema.json").read_text(encoding="utf-8")

    @_schema_resource(server, "okoffice://schemas/template-pack", "template-pack.schema.json", _schemas_dir)
    def _template_pack_schema() -> str:
        return (_schemas_dir / "template-pack.schema.json").read_text(encoding="utf-8")

    @_schema_resource(server, "okoffice://schemas/tool-result", "tool-result.schema.json", _schemas_dir)
    def _tool_result_schema() -> str:
        return (_schemas_dir / "tool-result.schema.json").read_text(encoding="utf-8")

    @_schema_resource(server, "okoffice://schemas/target-pdf-profile", "target-pdf-profile.schema.json", _schemas_dir)
    def _target_pdf_profile_schema() -> str:
        return (_schemas_dir / "target-pdf-profile.schema.json").read_text(encoding="utf-8")

    @_schema_resource(server, "okoffice://schemas/patch-manifest", "patch-manifest.schema.json", _schemas_dir)
    def _patch_manifest_schema() -> str:
        return (_schemas_dir / "patch-manifest.schema.json").read_text(encoding="utf-8")

    @_schema_resource(server, "okoffice://schemas/artifact", "artifact.schema.json", _schemas_dir)
    def _artifact_schema() -> str:
        return (_schemas_dir / "artifact.schema.json").read_text(encoding="utf-8")

    return server


def agentpdf_tool_manifest() -> str:
    """Return the complete OKoffice tool manifest with implementation statuses."""
    return load_tool_manifest().model_dump_json()


def okoffice_tool_manifest() -> str:
    """Return the OKoffice target manifest plus compatibility tool metadata."""
    return json.dumps(load_okoffice_manifest(), ensure_ascii=False)


def agent_setup_claude_code(
    output_path: str | None = None,
    safe_root: str = "${CLAUDE_PROJECT_DIR:-.}",
    command: str = "okoffice",
    args_prefix: list[str] | None = None,
    server_name: str = "okoffice",
    scope: Literal["project", "local", "user"] = "project",
) -> str:
    """Generate a Claude Code MCP config for local OKoffice tools."""
    return run_agent_setup_claude_code(
        output_path=output_path,
        safe_root=safe_root,
        command=command,
        args_prefix=args_prefix,
        server_name=server_name,
        scope=scope,
    ).model_dump_json()


def agent_setup_codex(
    output_path: str | None = None,
    safe_root: str = ".",
    command: str = "okoffice",
    args_prefix: list[str] | None = None,
    server_name: str = "okoffice",
) -> str:
    """Generate a Codex MCP config for local OKoffice tools."""
    return run_agent_setup_codex(
        output_path=output_path,
        safe_root=safe_root,
        command=command,
        args_prefix=args_prefix,
        server_name=server_name,
    ).model_dump_json()


def agent_setup_kilo_code(
    output_path: str | None = None,
    safe_root: str = ".",
    command: str = "okoffice",
    args_prefix: list[str] | None = None,
    server_name: str = "okoffice",
) -> str:
    """Generate a Kilo Code MCP config for local OKoffice tools."""
    return run_agent_setup_kilo_code(
        output_path=output_path,
        safe_root=safe_root,
        command=command,
        args_prefix=args_prefix,
        server_name=server_name,
    ).model_dump_json()


def agent_setup_openclaw(
    output_path: str | None = None,
    safe_root: str = ".",
    command: str = "okoffice",
    args_prefix: list[str] | None = None,
    server_name: str = "okoffice",
) -> str:
    """Generate an OpenClaw MCP config for local OKoffice tools."""
    return run_agent_setup_openclaw(
        output_path=output_path,
        safe_root=safe_root,
        command=command,
        args_prefix=args_prefix,
        server_name=server_name,
    ).model_dump_json()


def agent_setup_cursor(
    output_path: str | None = None,
    safe_root: str = ".",
    command: str = "okoffice",
    args_prefix: list[str] | None = None,
    server_name: str = "okoffice",
) -> str:
    """Generate a Cursor MCP config for local OKoffice tools."""
    return run_agent_setup_cursor(
        output_path=output_path,
        safe_root=safe_root,
        command=command,
        args_prefix=args_prefix,
        server_name=server_name,
    ).model_dump_json()


def agent_setup_openai_agents(
    output_path: str | None = None,
    safe_root: str = ".",
    command: str = "okoffice",
    args_prefix: list[str] | None = None,
    server_name: str = "okoffice",
) -> str:
    """Generate an OpenAI Agents MCP config for local OKoffice tools."""
    return run_agent_setup_openai_agents(
        output_path=output_path,
        safe_root=safe_root,
        command=command,
        args_prefix=args_prefix,
        server_name=server_name,
    ).model_dump_json()


def pdf_inspect_document(path: str) -> str:
    """Inspect a local PDF document."""
    return run_inspect(path).model_dump_json()


def office_inspect_file(path: str) -> str:
    """Inspect a local Office-compatible file and recommend next tools."""
    return run_office_inspect_file(path).model_dump_json()


def office_context_build_packet(
    files: list[str],
    output_path: str,
    title: str | None = None,
    intent: str | None = None,
) -> str:
    """Build a local OKoffice context packet and source graph from Office-compatible files."""
    return run_office_context_build_packet(files, output_path, title=title, intent=intent).model_dump_json()


def office_extract_schema(context_packet_path: str, schema: dict[str, object], output_path: str | None = None) -> str:
    """Extract schema-shaped evidence from an OKoffice context packet."""
    return run_office_extract_schema(context_packet_path, schema, output_path).model_dump_json()


def office_validation_package(path: str) -> str:
    """Validate a local Office package baseline without executing embedded code."""
    return run_office_validation_package(path).model_dump_json()


def office_workflow_plan(
    goal: str,
    input_paths: list[str] | None = None,
    output_paths: list[str] | None = None,
) -> str:
    """Plan a local-first cross-format OKoffice workflow without mutating files."""
    return run_office_workflow_plan(
        goal=goal,
        input_paths=input_paths or [],
        output_paths=output_paths or [],
    ).model_dump_json()


def office_workflow_extract_to_sheet(
    input_paths: list[str],
    output_path: str,
    context_packet_path: str | None = None,
) -> str:
    """Extract Word and Excel source tables into an auditable evidence workbook."""
    return run_office_workflow_extract_to_sheet(
        input_paths,
        output_path,
        context_packet_path=context_packet_path,
    ).model_dump_json()


def office_workflow_sheet_to_deck(
    workbook_path: str,
    output_path: str,
    title: str | None = None,
    max_rows_per_sheet: int = 100,
) -> str:
    """Turn an evidence workbook into a local editable PowerPoint deck."""
    return run_office_workflow_sheet_to_deck(
        workbook_path,
        output_path,
        title=title,
        max_rows_per_sheet=max_rows_per_sheet,
    ).model_dump_json()


def office_workflow_board_pack(files: list[str], output_path: str, title: str | None = None) -> str:
    """Create a local OKoffice board pack ZIP with artifacts, manifest, and validation report."""
    return run_office_workflow_board_pack(files, output_path, title=title).model_dump_json()


def office_workflow_source_to_board_pack(
    files: list[str],
    schema: dict[str, object],
    output_path: str,
    title: str | None = None,
    intent: str | None = None,
    deck_title: str | None = None,
    max_rows_per_sheet: int = 100,
) -> str:
    """End-to-end: source documents -> evidence workbook -> deck -> board pack ZIP."""
    return run_office_workflow_source_to_board_pack(
        files=files,
        schema=schema,
        output_path=output_path,
        title=title,
        intent=intent,
        deck_title=deck_title,
        max_rows_per_sheet=max_rows_per_sheet,
    ).model_dump_json()


def office_workflow_docset_to_sheet(
    files: list[str],
    schema: dict[str, object],
    output_path: str,
    title: str | None = None,
    intent: str | None = None,
    context_output_path: str | None = None,
    evidence_output_path: str | None = None,
) -> str:
    """Build a context packet, extract evidence, write an XLSX model, and validate formulas."""
    return run_office_workflow_docset_to_sheet(
        files=files,
        schema=schema,
        output_path=output_path,
        title=title,
        intent=intent,
        context_output_path=context_output_path,
        evidence_output_path=evidence_output_path,
    ).model_dump_json()


def office_workers_status(
    feature_flags: dict[str, bool] | None = None,
    command_paths: dict[str, str] | None = None,
) -> str:
    """Report optional Office worker contracts, flags, dependency status, and license boundaries."""
    return run_office_workers_status(feature_flags=feature_flags, command_paths=command_paths).model_dump_json()


def office_bundle_export(
    artifact_paths: list[str],
    output_path: str,
    title: str | None = None,
    metadata: dict[str, object] | None = None,
) -> str:
    """Export local Office artifacts into a portable OKoffice bundle ZIP."""
    return run_office_bundle_export(
        artifact_paths=artifact_paths,
        output_path=output_path,
        title=title,
        metadata=metadata,
    ).model_dump_json()


def office_bundle_verify(bundle_path: str) -> str:
    """Verify an OKoffice board pack ZIP manifest, validation report, artifact members, and checksums."""
    return run_office_bundle_verify(bundle_path).model_dump_json()


def word_inspect_document(path: str) -> str:
    """Inspect a local Word document and recommend next tools."""
    return run_word_inspect_document(path).model_dump_json()


def word_validate_document(path: str) -> str:
    """Validate a local Word document for structure, safety, comments, and render-preview readiness."""
    return run_word_validate_document(path).model_dump_json()


def word_review_style(path: str) -> str:
    """Review style consistency in a Word document."""
    return run_word_review_style(path).model_dump_json()


def word_validation_metadata(path: str) -> str:
    """Validate metadata completeness for a Word document."""
    return run_word_validate_metadata(path).model_dump_json()


def word_validation_accessibility(path: str) -> str:
    """Heuristic accessibility analysis for a Word document."""
    return run_word_validate_accessibility(path).model_dump_json()


def word_create_report(
    workbook_path: str,
    output_path: str,
    title: str | None = None,
    profile: str = "executive_memo",
) -> str:
    """Create a local editable Word report from an evidence workbook."""
    return run_word_create_report(
        workbook_path=workbook_path,
        output_path=output_path,
        title=title,
        profile=profile,
    ).model_dump_json()


def word_create_document(output_path: str, document_ir: dict[str, object]) -> str:
    """Create a DOCX from a structured document IR with sections, headings, paragraphs, and tables."""
    return run_create_word_document(output_path=output_path, document_ir=document_ir).model_dump_json()


def word_create_memo(output_path: str, memo_ir: dict[str, object]) -> str:
    """Create a DOCX memo with To/From/Date/Subject header fields and body paragraphs."""
    return run_create_word_memo(output_path=output_path, memo_ir=memo_ir).model_dump_json()


def word_patch_plan(input_path: str, operations: list[dict[str, object]]) -> str:
    """Preview a non-mutating Word patch transaction."""
    return run_word_patch_plan(input_path=input_path, operations=operations).model_dump_json()


def word_patch_apply(input_path: str, output_path: str, operations: list[dict[str, object]]) -> str:
    """Apply a non-mutating Word patch transaction into a new DOCX output."""
    return run_word_patch_apply(
        input_path=input_path,
        output_path=output_path,
        operations=operations,
    ).model_dump_json()


def word_extract_tables(path: str) -> str:
    """Extract Word tables into normalized records with source cell locations."""
    return run_word_extract_tables(path).model_dump_json()


def word_extract_text(path: str) -> str:
    """Extract Word text with paragraph locations, styles, and heading levels."""
    return run_word_extract_text(path).model_dump_json()


def word_extract_outline(path: str) -> str:
    """Extract a Word document outline with headings, sections, and navigation anchors."""
    return run_word_extract_outline(path).model_dump_json()


def word_extract_comments(path: str) -> str:
    """Extract Word comments with author, date, reference ranges, and reply threads."""
    return run_word_extract_comments(path).model_dump_json()


def word_extract_revisions(path: str) -> str:
    """Extract Word tracked revisions with author, date, type, and text ranges."""
    return run_word_extract_revisions(path).model_dump_json()


def word_extract_fields(path: str) -> str:
    """Extract Word fields with types, instructions, cached results, and locations."""
    return run_word_extract_fields(path).model_dump_json()


def word_extract_styles(path: str) -> str:
    """Extract Word style definitions with names, types, base styles, and formatting."""
    return run_word_extract_styles(path).model_dump_json()


def sheet_inspect_workbook(path: str) -> str:
    """Inspect a local Excel workbook and recommend next tools."""
    return run_sheet_inspect_workbook(path).model_dump_json()


def sheet_read_workbook(path: str, max_rows_per_sheet: int = 100) -> str:
    """Read workbook sheets, rows, cells, formulas, and source refs as bounded JSON."""
    return run_sheet_read_workbook(path, max_rows_per_sheet=max_rows_per_sheet).model_dump_json()


def sheet_profile_data(path: str, max_rows_per_sheet: int = 100, include_source_refs: bool = False) -> str:
    """Profile workbook headers, data types, missing cells, formulas, and source coverage."""
    return run_sheet_profile_data(
        path,
        max_rows_per_sheet=max_rows_per_sheet,
        include_source_refs=include_source_refs,
    ).model_dump_json()


def sheet_extract_tables(path: str) -> str:
    """Extract workbook tables with sheet, row, column, and cell references."""
    return run_sheet_extract_tables(path).model_dump_json()


def sheet_write_workbook(data: dict[str, object], output_path: str) -> str:
    """Write an XLSX workbook from structured records with source refs."""
    return run_sheet_write_workbook(data, output_path).model_dump_json()


def sheet_create_evidence_workbook(data: dict[str, object], output_path: str) -> str:
    """Create an auditable XLSX evidence workbook from structured records with source refs."""
    return run_sheet_create_evidence_workbook(data, output_path).model_dump_json()


def sheet_validate_workbook(path: str) -> str:
    """Validate a local Excel workbook for agent-readable structure and safety markers."""
    return run_sheet_validate_workbook(path).model_dump_json()


def sheet_validate_formulas(path: str) -> str:
    """Validate workbook formulas for cached errors, broken refs, external refs, and volatile functions."""
    return run_sheet_validate_formulas(path).model_dump_json()


def sheet_validate_model_checks(path: str) -> str:
    """Perform structural model checks: circular references, empty input cells, and SUM range balance."""
    return run_sheet_validate_model_checks(path).model_dump_json()


def sheet_validate_external_links(path: str) -> str:
    """Audit external link targets in an XLSX workbook package."""
    return run_sheet_validate_external_links(path).model_dump_json()


def sheet_patch_cells(path: str, output_path: str, operations: list[dict[str, object]]) -> str:
    """Apply non-mutating cell value patches to an XLSX workbook and write a new output."""
    return run_patch_sheet_cells(path, output_path=output_path, operations=operations).model_dump_json()


def sheet_patch_table(path: str, output_path: str, operations: list[dict[str, object]]) -> str:
    """Apply non-mutating table range patches to an XLSX workbook and write a new output."""
    return run_patch_sheet_table(path, output_path=output_path, operations=operations).model_dump_json()


def sheet_patch_formulas(path: str, output_path: str, operations: list[dict[str, object]]) -> str:
    """Apply non-mutating formula replacement patches to an XLSX workbook and write a new output."""
    return run_patch_sheet_formulas(path, output_path=output_path, operations=operations).model_dump_json()


def sheet_patch_chart(path: str, output_path: str, operations: list[dict[str, object]]) -> str:
    """Apply non-mutating chart title patches to an XLSX workbook and write a new output."""
    return run_patch_sheet_chart(path, output_path=output_path, operations=operations).model_dump_json()


def sheet_review_model(path: str) -> str:
    """Review spreadsheet model quality: hardcoded literals, volatile functions, chain depth, and orphan inputs."""
    return run_review_sheet_model(path).model_dump_json()


def sheet_review_number_consistency(path: str) -> str:
    """Review number formatting consistency across sheets: hidden sheets, mixed format columns, percentage columns."""
    return run_review_sheet_number_consistency(path).model_dump_json()


def sheet_extract_formulas(path: str) -> str:
    """Extract all formulas with cell references, cached values, and precedents."""
    return run_sheet_extract_formulas(path).model_dump_json()


def sheet_extract_charts(path: str) -> str:
    """Extract chart inventory with sheet locators and types."""
    return run_sheet_extract_charts(path).model_dump_json()


def sheet_extract_named_ranges(path: str) -> str:
    """Extract defined names with scope and references."""
    return run_sheet_extract_named_ranges(path).model_dump_json()


def sheet_extract_comments(path: str) -> str:
    """Extract cell comments with author, text, and cell references."""
    return run_sheet_extract_comments(path).model_dump_json()


def sheet_extract_pivots(path: str) -> str:
    """Extract pivot table cache references."""
    return run_sheet_extract_pivots(path).model_dump_json()


def deck_inspect_presentation(path: str) -> str:
    """Inspect a local PowerPoint deck and recommend next tools."""
    return run_deck_inspect_presentation(path).model_dump_json()


def deck_extract_text(path: str) -> str:
    """Extract all slide text with slide-index locators."""
    return run_deck_extract_text(path).model_dump_json()


def deck_extract_notes(path: str) -> str:
    """Extract speaker notes with slide references."""
    return run_deck_extract_notes(path).model_dump_json()


def deck_extract_shapes(path: str) -> str:
    """Extract shape inventory with types, positions, and text."""
    return run_deck_extract_shapes(path).model_dump_json()


def deck_extract_media(path: str) -> str:
    """Extract embedded media references with MIME types."""
    return run_deck_extract_media(path).model_dump_json()


def deck_extract_charts(path: str) -> str:
    """Extract chart references with slide locators."""
    return run_deck_extract_charts(path).model_dump_json()


def deck_extract_theme(path: str) -> str:
    """Extract theme colors, fonts, and master layout metadata."""
    return run_deck_extract_theme(path).model_dump_json()


def deck_create_from_outline(outline: dict[str, object], output_path: str) -> str:
    """Create a local editable PPTX deck from a structured outline."""
    return run_deck_create_from_outline(outline, output_path).model_dump_json()


def deck_create_presentation(
    workbook_path: str | dict[str, object],
    output_path: str,
    title: str | None = None,
    profile: str = "board_review",
    style: dict[str, object] | None = None,
) -> str:
    """Create a styled, editable PowerPoint deck from a workbook, outline, or composition plan."""
    outline_or_plan = workbook_path if isinstance(workbook_path, dict) else None
    return run_deck_create_presentation(
        workbook_path=None if outline_or_plan is not None else workbook_path,
        output_path=output_path,
        title=title,
        profile=profile,
        style=style,
        outline_or_plan=outline_or_plan,
    ).model_dump_json()


def deck_patch_apply(input_path: str, output_path: str, operations: list[dict[str, object]]) -> str:
    """Apply a non-mutating PowerPoint patch transaction into a new PPTX output."""
    return run_deck_patch_apply(
        input_path=input_path,
        output_path=output_path,
        operations=operations,
    ).model_dump_json()


def deck_revise(input_path: str, output_path: str, operations: list[dict[str, object]]) -> str:
    """Apply revisions to a deck and re-run validation and taste QA."""
    from okoffice.office.deck_patch import revise_deck

    return revise_deck(
        input_path=input_path,
        output_path=output_path,
        operations=operations,
    ).model_dump_json()


def deck_validate_contact_sheet(path: str) -> str:
    """Validate PowerPoint contact-sheet preview readiness and render-worker status."""
    return run_deck_validate_contact_sheet(path).model_dump_json()


def deck_review_taste(path: str, html_preview_path: str | None = None) -> str:
    """Review a deck for taste and design quality, returning a scored report."""
    from okoffice.office.deck_taste_qa import review_deck_taste

    return review_deck_taste(path, html_preview_path=html_preview_path).model_dump_json()


def deck_review_story(path: str) -> str:
    """Review story rhythm and section balance of a deck."""
    return run_deck_review_story(path).model_dump_json()


def deck_review_claims(path: str) -> str:
    """Review verifiable claims in deck slides."""
    return run_deck_review_claims(path).model_dump_json()


def deck_validation_notes(path: str) -> str:
    """Validate speaker notes completeness and placeholder markers in a deck."""
    return run_deck_validate_notes(path).model_dump_json()


def deck_validation_placeholders(path: str) -> str:
    """Validate placeholder marker absence in deck slide text."""
    return run_deck_validate_placeholders(path).model_dump_json()


def deck_template_list() -> str:
    """List local template packs for agent-created PDFs."""
    return run_deck_template_list().model_dump_json()


def deck_template_preview(
    mood: str | None = None,
    tone: str | None = None,
    count: int = 3,
) -> str:
    """Generate and validate a local preview PDF for a creation template."""
    return run_deck_template_preview(mood=mood, tone=tone, count=count).model_dump_json()


def deck_create_from_template(
    template_id: str,
    slides: list[dict],
    output_path: str,
    theme: str | None = None,
    animation_recipe: str | None = None,
    background_effect: str | None = None,
) -> str:
    """Create a deck using a specific template ID."""
    return run_deck_create_from_template(
        template_id=template_id,
        slides=slides,
        output_path=output_path,
        theme=theme,
        animation_recipe=animation_recipe,
        background_effect=background_effect,
    ).model_dump_json()


def deck_spec_lock_create(outline: dict) -> str:
    """Create a spec lock from an outline to detect generation drift."""
    return run_deck_spec_lock_create(outline).model_dump_json()


def deck_spec_lock_check_drift(current_slides: list[dict], spec_lock: dict) -> str:
    """Check a deck against a spec lock to detect generation drift."""
    return run_deck_spec_lock_check_drift(current_slides, spec_lock).model_dump_json()


def deck_animation_apply(html: str, recipe: str, item_count: int = 4) -> str:
    """Apply a CSS animation recipe to HTML slide content."""
    return run_deck_animation_apply(html, recipe, item_count=item_count).model_dump_json()


def deck_compose_plan(
    workbook_path: str,
    output_path: str | None = None,
    title: str | None = None,
    style: str = "executive",
    max_rows_per_sheet: int = 100,
) -> str:
    """Compose a source-mapped deck plan from a local workbook without writing a PPTX."""
    return run_deck_compose_plan(
        workbook_path,
        output_path=output_path,
        title=title,
        style=style,
        max_rows_per_sheet=max_rows_per_sheet,
    ).model_dump_json()


def deck_render_html(plan_path: str, output_path: str, artifact_dir: str | None = None) -> str:
    """Render a deck composition plan or outline JSON into an offline HTML preview package."""
    return run_deck_render_html(plan_path, output_path, artifact_dir=artifact_dir).model_dump_json()


def deck_validation_html_preview(path: str) -> str:
    """Validate an offline HTML deck preview package before PPTX export."""
    return run_deck_validate_html_preview(path).model_dump_json()


def deck_export_pptx(html_path: str, output_path: str) -> str:
    """Export an HTML deck preview package into an editable PPTX deck."""
    return run_deck_export_pptx(html_path, output_path).model_dump_json()


def deck_validate_presentation(path: str) -> str:
    """Validate a local PowerPoint deck for structure, safety, and placeholder leakage."""
    quality = run_deck_validation_presentation(path)
    summary = quality.usage.get("summary", {})
    slide_count = int(summary.get("slide_count", 0)) if isinstance(summary, dict) else 0
    slides_without_notes = int(summary.get("slide_without_notes_count", 0)) if isinstance(summary, dict) else 0
    if slide_count and slides_without_notes < slide_count:
        return quality.model_dump_json()
    return run_deck_validate_presentation(path).model_dump_json()


def deck_validation_presentation(path: str) -> str:
    """Validate a local PowerPoint deck for structure, safety, and placeholder leakage (validation namespace alias)."""
    return deck_validate_presentation(path)


def pdf_inspect_pages(input_path: str, pages: str = "all", render_check: bool = False) -> str:
    """Inspect page-level facts for selected local PDF pages."""
    return run_inspect_pages(
        input_path,
        pages=pages,
        render_check=render_check,
    ).model_dump_json()


def pdf_inspect_health(input_path: str) -> str:
    """Inspect a local PDF for parseability, structural markers, and active-content risks."""
    return run_inspect_health(input_path).model_dump_json()


def pdf_workflow_plan(goal: str, input_path: str | None = None) -> str:
    """Plan a local-first agent PDF workflow."""
    return run_workflow_plan(goal=goal, input_path=input_path).model_dump_json()


def pdf_workflow_run(workflow: dict[str, object], dry_run: bool = False) -> str:
    """Run a local-first agent PDF workflow manifest."""
    return run_workflow_run(workflow=workflow, dry_run=dry_run).model_dump_json()


def pdf_workflow_report(workflow_run: dict[str, object], output_path: str | None = None) -> str:
    """Summarize a local workflow run with audit evidence."""
    return run_workflow_report(workflow_run=workflow_run, output_path=output_path).model_dump_json()


def pdf_workflow_createpdf(
    pdf_output_path: str,
    html_output_path: str | None = None,
    html: str | None = None,
    html_path: str | None = None,
    page_document: dict[str, object] | None = None,
    context_packet: dict[str, object] | None = None,
    context_packet_path: str | None = None,
    target_profile: dict[str, object] | str = "research_brief",
    style_pack: str | None = None,
    title: str | None = None,
    artifact_dir: str | None = None,
    bundle_output_path: str | None = None,
    expected_page_count: int | None = None,
    pages: str = "all",
    renderer_backend: str = "auto",
) -> str:
    """Create a validated PDF through the local HTML-first workflow."""
    return run_workflow_createpdf(
        pdf_output_path=pdf_output_path,
        html_output_path=html_output_path,
        html=html,
        html_path=html_path,
        page_document=page_document,
        context_packet=context_packet,
        context_packet_path=context_packet_path,
        target_profile=target_profile,
        style_pack=style_pack,
        title=title,
        artifact_dir=artifact_dir,
        bundle_output_path=bundle_output_path,
        expected_page_count=expected_page_count,
        pages=pages,
        renderer_backend=renderer_backend,
    ).model_dump_json()


def pdf_workflow_research_deck(
    brief: dict[str, object],
    evidence_cards: list[dict[str, object]] | None = None,
    html_output_path: str = "<deck.html>",
    pdf_output_path: str = "<deck.pdf>",
    artifact_dir: str | None = None,
    execute: bool = False,
) -> str:
    """Plan a local research-to-deck workflow."""
    return run_workflow_research_deck(
        brief=brief,
        evidence_cards=evidence_cards,
        html_output_path=html_output_path,
        pdf_output_path=pdf_output_path,
        artifact_dir=artifact_dir,
        execute=execute,
    ).model_dump_json()


def pdf_authoring_plan(brief: dict[str, object]) -> str:
    """Plan the best local authoring route before PDF creation."""
    return run_authoring_plan(brief).model_dump_json()


def pdf_storyboard_plan(
    brief: dict[str, object],
    authoring_plan: dict[str, object] | None = None,
    evidence_cards: list[dict[str, object]] | None = None,
) -> str:
    """Create a deterministic page-by-page storyboard."""
    return run_storyboard_plan(
        brief=brief,
        authoring_plan=authoring_plan,
        evidence_cards=evidence_cards,
    ).model_dump_json()


def pdf_pages_write(
    brief: dict[str, object],
    storyboard: dict[str, object],
    evidence_cards: list[dict[str, object]] | None = None,
    design_tokens: dict[str, object] | None = None,
) -> str:
    """Write page JSON from storyboard and evidence cards."""
    return run_pages_write(
        brief=brief,
        storyboard=storyboard,
        evidence_cards=evidence_cards,
        design_tokens=design_tokens,
    ).model_dump_json()


def pdf_research_plan(brief: dict[str, object]) -> str:
    """Plan local source gathering without fetching or using a model."""
    return run_research_plan(brief=brief).model_dump_json()


def pdf_research_source_cards(
    sources: list[dict[str, object]],
    brief: dict[str, object] | None = None,
) -> str:
    """Normalize agent-supplied sources into local source cards."""
    return run_research_source_cards(sources=sources, brief=brief).model_dump_json()


def pdf_research_evidence_cards(source_cards: list[dict[str, object]]) -> str:
    """Extract evidence cards from normalized source cards."""
    return run_research_evidence_cards(source_cards=source_cards).model_dump_json()


def pdf_design_tokens(
    theme: str = "business_tech",
    overrides: dict[str, object] | None = None,
) -> str:
    """Select safe local design tokens for authoring packages."""
    return run_design_tokens(theme=theme, overrides=overrides).model_dump_json()


def pdf_pages_revise(
    page_document: dict[str, object],
    revisions: list[dict[str, object]] | None = None,
    design_tokens: dict[str, object] | None = None,
) -> str:
    """Revise generated page JSON while preserving source refs by default."""
    return run_pages_revise(
        page_document=page_document,
        revisions=revisions,
        design_tokens=design_tokens,
    ).model_dump_json()


def pdf_create_html_package(
    page_document: dict[str, object] | None,
    html_output_path: str,
    title: str | None = None,
    html: str | None = None,
    html_path: str | None = None,
) -> str:
    """Write a local self-contained HTML/CSS source package."""
    return run_create_html_package(
        page_document=page_document,
        html_output_path=html_output_path,
        title=title,
        html=html,
        html_path=html_path,
    ).model_dump_json()


def pdf_qa_visual_report(
    input_path: str,
    expected_page_count: int | None = None,
    html_package_manifest_path: str | None = None,
    pages: str = "all",
) -> str:
    """Run visual QA checks over a generated PDF."""
    return run_qa_visual_report(
        input_path=input_path,
        expected_page_count=expected_page_count,
        html_package_manifest_path=html_package_manifest_path,
        pages=pages,
    ).model_dump_json()


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


def pdf_n_up(input_path: str, output_path: str, pages: str = "all", per_sheet: int = 2) -> str:
    """Place multiple source PDF pages on one output PDF page."""
    return run_n_up(
        input_path,
        output_path=output_path,
        pages=pages,
        per_sheet=per_sheet,
    ).model_dump_json()


def pdf_booklet(input_path: str, output_path: str, pages: str = "all") -> str:
    """Create a local booklet imposition PDF."""
    return run_booklet(input_path, output_path=output_path, pages=pages).model_dump_json()


def pdf_optimize_compress(input_path: str, output_path: str) -> str:
    """Compress local PDF content streams and write a new output PDF."""
    return run_compress(input_path, output_path=output_path).model_dump_json()


def pdf_optimize_repair(input_path: str, output_path: str) -> str:
    """Rewrite a parseable local PDF to rebuild output structure."""
    return run_repair(input_path, output_path=output_path).model_dump_json()


def pdf_optimize_remove_unused_objects(input_path: str, output_path: str) -> str:
    """Rewrite reachable objects from a local PDF into a new output PDF."""
    return run_remove_unused_objects(input_path, output_path=output_path).model_dump_json()


def pdf_optimize_subset_fonts(input_path: str, output_path: str) -> str:
    """Rewrite a local PDF and return font-subset audit evidence."""
    return run_subset_fonts(input_path, output_path=output_path).model_dump_json()


def pdf_optimize_to_pdfa(
    input_path: str,
    output_path: str,
    profile: str = "PDF/A-2B",
) -> str:
    """Create a best-effort local PDF/A-tagged copy."""
    return run_to_pdfa(input_path, output_path=output_path, profile=profile).model_dump_json()


def pdf_optimize_validate_pdfa(input_path: str) -> str:
    """Run local heuristic PDF/A validation checks."""
    return run_validate_pdfa(input_path).model_dump_json()


def pdf_image_to_pdf(image_paths: list[str], output_path: str) -> str:
    """Create a local PDF from image files."""
    return run_image_to_pdf(image_paths, output_path=output_path).model_dump_json()


def pdf_html_to_pdf(input_path: str, output_path: str) -> str:
    """Convert local HTML text to a PDF."""
    return run_html_to_pdf(input_path, output_path=output_path).model_dump_json()


def pdf_render_html_package(package_path: str, output_path: str, renderer_backend: str = "auto") -> str:
    """Validate and render an OKoffice HTML package to PDF."""
    return run_render_html_package(
        package_path,
        output_path=output_path,
        renderer_backend=renderer_backend,
    ).model_dump_json()


def pdf_url_to_pdf(
    url: str,
    output_path: str,
    allow_private_hosts: bool = False,
    allow_file_urls: bool = False,
) -> str:
    """Fetch a URL with safety checks and convert HTML text to PDF."""
    return run_url_to_pdf(
        url,
        output_path=output_path,
        allow_private_hosts=allow_private_hosts,
        allow_file_urls=allow_file_urls,
    ).model_dump_json()


def pdf_docx_to_pdf(input_path: str, output_path: str) -> str:
    """Convert DOCX text to a local PDF."""
    return run_docx_to_pdf(input_path, output_path=output_path).model_dump_json()


def pdf_pptx_to_pdf(input_path: str, output_path: str) -> str:
    """Convert PPTX slide text to a local PDF."""
    return run_pptx_to_pdf(input_path, output_path=output_path).model_dump_json()


def pdf_xlsx_to_pdf(input_path: str, output_path: str) -> str:
    """Convert XLSX rows to a local PDF."""
    return run_xlsx_to_pdf(input_path, output_path=output_path).model_dump_json()


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


def pdf_add_shape(
    input_path: str,
    output_path: str,
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
) -> str:
    """Add a vector shape overlay to a local PDF page."""
    return run_add_shape(
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
    ).model_dump_json()


def pdf_underline(
    input_path: str,
    output_path: str,
    page: int,
    bbox: list[float],
    color: str = "#2563eb",
    line_width: float = 1.0,
) -> str:
    """Underline a coordinate span in a local PDF."""
    return run_underline(
        input_path,
        output_path=output_path,
        page=page,
        bbox=bbox,
        color=color,
        line_width=line_width,
    ).model_dump_json()


def pdf_strikeout(
    input_path: str,
    output_path: str,
    page: int,
    bbox: list[float],
    color: str = "#dc2626",
    line_width: float = 1.0,
) -> str:
    """Strike out a coordinate span in a local PDF."""
    return run_strikeout(
        input_path,
        output_path=output_path,
        page=page,
        bbox=bbox,
        color=color,
        line_width=line_width,
    ).model_dump_json()


def pdf_freehand_draw(
    input_path: str,
    output_path: str,
    page: int,
    points: list[list[float]],
    stroke_color: str = "#2563eb",
    line_width: float = 1.5,
    opacity: float = 1.0,
) -> str:
    """Add a freehand drawing path to a local PDF."""
    return run_freehand_draw(
        input_path,
        output_path=output_path,
        page=page,
        points=points,
        stroke_color=stroke_color,
        line_width=line_width,
        opacity=opacity,
    ).model_dump_json()


def pdf_resize_pages(
    input_path: str,
    output_path: str,
    width: float,
    height: float,
    pages: str = "all",
) -> str:
    """Resize selected local PDF pages and scale content to fit."""
    return run_resize_pages(
        input_path,
        output_path=output_path,
        width=width,
        height=height,
        pages=pages,
    ).model_dump_json()


def pdf_add_margin(
    input_path: str,
    output_path: str,
    margin: float = 0,
    pages: str = "all",
    top: float | None = None,
    right: float | None = None,
    bottom: float | None = None,
    left: float | None = None,
) -> str:
    """Add margins around selected local PDF pages."""
    return run_add_margin(
        input_path,
        output_path=output_path,
        margin=margin,
        pages=pages,
        top=top,
        right=right,
        bottom=bottom,
        left=left,
    ).model_dump_json()


def pdf_underlay(
    input_path: str,
    output_path: str,
    text: str,
    pages: str = "all",
    font_size: int = 72,
    opacity: float = 0.12,
    angle: int = 45,
    color: str = "#64748b",
) -> str:
    """Add text below existing local PDF page content."""
    return run_underlay(
        input_path,
        output_path=output_path,
        text=text,
        pages=pages,
        font_size=font_size,
        opacity=opacity,
        angle=angle,
        color=color,
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
    output_path: str = ".okoffice-out/create-agent.pdf",
    plan_output_path: str | None = None,
    coverage_output_path: str | None = None,
    context_classification_output_path: str | None = None,
    context_report_output_path: str | None = None,
    context_report_json_output_path: str | None = None,
    bundle_output_path: str | None = None,
    preferred_template_id: str | None = None,
    preferred_color_scheme: str | None = None,
    title: str | None = None,
    prompt: str | None = None,
    style_pack: str | None = None,
    renderer: str = "markdown",
    html_output_path: str | None = None,
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
    renderer: str = "markdown",
    html_output_path: str | None = None,
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
        renderer=renderer,
        html_output_path=html_output_path,
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


def pdf_context_ingest(
    context_item: dict[str, object],
    output_path: str | None = None,
) -> str:
    """Normalize one local source into an agent context item."""
    return run_context_ingest(
        context_item,
        output_path=output_path,
    ).model_dump_json()


def pdf_context_packet(
    context_items: list[dict[str, object]],
    output_path: str,
    title: str | None = None,
    intent: str | None = None,
) -> str:
    """Build a reusable Context Packet from raw or pre-ingested context items."""
    return run_context_packet(
        context_items,
        output_path=output_path,
        title=title,
        intent=intent,
    ).model_dump_json()


def pdf_context_web_capture(
    url: str,
    output_path: str | None = None,
    label: str | None = None,
    role: str = "citation",
    context_item_id: str | None = None,
    max_bytes: int = 1_000_000,
    timeout_seconds: float = 10,
    allow_private_hosts: bool = False,
) -> str:
    """Capture a public web page into a local context item without model calls."""
    return run_context_web_capture(
        url=url,
        output_path=output_path,
        label=label,
        role=role,
        context_item_id=context_item_id,
        max_bytes=max_bytes,
        timeout_seconds=timeout_seconds,
        allow_private_hosts=allow_private_hosts,
    ).model_dump_json()


def pdf_context_classify(
    context_packet: dict[str, object] | str,
    target_profile: dict[str, object] | str | None = None,
    output_path: str | None = None,
) -> str:
    """Classify context items for agent routing into target PDF blocks and slots."""
    return run_context_classify(
        context_packet,
        target_profile=target_profile,
        output_path=output_path,
    ).model_dump_json()


def pdf_context_code_snapshot(
    path: str,
    output_path: str | None = None,
    label: str | None = None,
    role: str = "code_evidence",
    context_item_id: str | None = None,
    line_start: int | None = None,
    line_end: int | None = None,
    repository_root: str | None = None,
    include_dependencies: bool = False,
) -> str:
    """Create a code context item with local symbol, range, hash, and source refs."""
    return run_context_code_snapshot(
        path=path,
        output_path=output_path,
        label=label,
        role=role,
        context_item_id=context_item_id,
        line_start=line_start,
        line_end=line_end,
        repository_root=repository_root,
        include_dependencies=include_dependencies,
    ).model_dump_json()


def pdf_context_data_profile(
    path: str,
    output_path: str | None = None,
    label: str | None = None,
    role: str = "data_evidence",
    context_item_id: str | None = None,
    sheet: str | None = None,
    max_rows: int = 100,
) -> str:
    """Create a data context item with local table/profile evidence."""
    return run_context_data_profile(
        path=path,
        output_path=output_path,
        label=label,
        role=role,
        context_item_id=context_item_id,
        sheet=sheet,
        max_rows=max_rows,
    ).model_dump_json()


def pdf_context_image_analyze(
    input_path: str,
    languages: list[str] | None = None,
    run_ocr: bool = True,
    engine: str = "tesseract",
    psm: int = 6,
) -> str:
    """Analyze a local image with metadata and optional OCR text-region evidence."""
    return run_context_image_analyze(
        input_path,
        languages=languages,
        run_ocr=run_ocr,
        engine=engine,
        psm=psm,
    ).model_dump_json()


def pdf_compose_plan(
    context_packet: dict[str, object] | str,
    target_profile: dict[str, object] | str = "research_brief",
    output_path: str | None = None,
    style_pack: str | None = None,
    title: str | None = None,
) -> str:
    """Plan composition IR, source map, coverage, and render payload without writing a PDF."""
    return run_compose_plan(
        context_packet,
        target_profile=target_profile,
        output_path=output_path,
        style_pack=style_pack,
        title=title,
    ).model_dump_json()


def pdf_compose_render_ir(
    composition: dict[str, object] | str,
    output_path: str,
    style_pack: str | None = None,
    title: str | None = None,
) -> str:
    """Render a composition plan or IR payload into a validated PDF artifact."""
    return run_compose_render_ir(
        composition,
        output_path=output_path,
        style_pack=style_pack,
        title=title,
    ).model_dump_json()


def pdf_compose_from_context(
    context_packet: dict[str, object] | str,
    output_path: str,
    target_profile: dict[str, object] | str = "research_brief",
    style_pack: str | None = None,
    title: str | None = None,
    renderer: str = "markdown",
    html_output_path: str | None = None,
) -> str:
    """Compose a validated target PDF from a Context Packet and target profile."""
    return run_compose_from_context(
        context_packet,
        target_profile=target_profile,
        output_path=output_path,
        style_pack=style_pack,
        title=title,
        renderer=renderer,
        html_output_path=html_output_path,
    ).model_dump_json()


def pdf_compose_add_code_block(
    input_path: str,
    output_path: str,
    title: str,
    code: str,
    language: str = "text",
    source_refs: list[str] | None = None,
    block_id: str | None = None,
    target_slot: str | None = None,
    composition_path: str | None = None,
    layer_manifest_path: str | None = None,
    manifest_output_path: str | None = None,
) -> str:
    """Append a source-backed code block page to a new PDF artifact."""
    return run_compose_add_code_block(
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
    ).model_dump_json()


def pdf_compose_add_table(
    input_path: str,
    output_path: str,
    title: str,
    columns: list[str],
    rows: list[list[object]],
    source_refs: list[str] | None = None,
    block_id: str | None = None,
    target_slot: str | None = None,
    composition_path: str | None = None,
    layer_manifest_path: str | None = None,
    manifest_output_path: str | None = None,
) -> str:
    """Append a source-backed table page to a new PDF artifact."""
    return run_compose_add_table(
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
    ).model_dump_json()


def pdf_compose_add_figure(
    input_path: str,
    output_path: str,
    title: str,
    image_path: str,
    caption: str | None = None,
    source_refs: list[str] | None = None,
    block_id: str | None = None,
    target_slot: str | None = None,
    composition_path: str | None = None,
    layer_manifest_path: str | None = None,
    manifest_output_path: str | None = None,
) -> str:
    """Append a source-backed figure page to a new PDF artifact."""
    return run_compose_add_figure(
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
    ).model_dump_json()


def pdf_compose_add_appendix(
    input_path: str,
    output_path: str,
    title: str,
    markdown: str,
    source_refs: list[str] | None = None,
    block_id: str | None = None,
    target_slot: str | None = None,
    composition_path: str | None = None,
    layer_manifest_path: str | None = None,
    manifest_output_path: str | None = None,
) -> str:
    """Append a source-backed Markdown appendix to a new PDF artifact."""
    return run_compose_add_appendix(
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
    ).model_dump_json()


def pdf_compose_add_citation(
    input_path: str,
    output_path: str,
    title: str,
    source: str,
    quote: str | None = None,
    page: str | None = None,
    source_refs: list[str] | None = None,
    block_id: str | None = None,
    target_slot: str | None = None,
    composition_path: str | None = None,
    layer_manifest_path: str | None = None,
    manifest_output_path: str | None = None,
) -> str:
    """Append a source-backed citation page to a new PDF artifact."""
    return run_compose_add_citation(
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
    ).model_dump_json()


def pdf_compose_add_media_reference(
    input_path: str,
    output_path: str,
    title: str,
    media_path: str,
    media_kind: str = "media",
    transcript_excerpt: str | None = None,
    duration_seconds: float | None = None,
    chapter_count: int | None = None,
    keyframe_count: int | None = None,
    source_refs: list[str] | None = None,
    block_id: str | None = None,
    target_slot: str | None = None,
    composition_path: str | None = None,
    layer_manifest_path: str | None = None,
    manifest_output_path: str | None = None,
) -> str:
    """Append a source-backed media reference page to a new PDF artifact."""
    return run_compose_add_media_reference(
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
    ).model_dump_json()


def pdf_compose_add_slide(
    input_path: str,
    output_path: str,
    title: str,
    body: list[str] | None = None,
    subtitle: str | None = None,
    code: str | None = None,
    table: dict[str, object] | None = None,
    image_path: str | None = None,
    source_refs: list[str] | None = None,
    block_id: str | None = None,
    target_slot: str | None = None,
    composition_path: str | None = None,
    layer_manifest_path: str | None = None,
    manifest_output_path: str | None = None,
) -> str:
    """Append a source-backed slide-like page to a new PDF artifact."""
    return run_compose_add_slide(
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
    ).model_dump_json()


def pdf_target_profiles(output_path: str | None = None) -> str:
    """List built-in target PDF profiles with layout slots and accepted block types."""
    return run_target_profiles(output_path=output_path).model_dump_json()


def pdf_target_select_profile(
    goal: str = "",
    context_packet: dict[str, object] | str | None = None,
    preferred_profile: str | None = None,
    output_path: str | None = None,
) -> str:
    """Select a local target PDF profile from a goal and optional Context Packet."""
    return run_select_target_profile(
        goal=goal,
        context_packet=context_packet,
        preferred_profile=preferred_profile,
        output_path=output_path,
    ).model_dump_json()


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


def pdf_evidence_map_sources(
    composition: dict[str, object] | str | None = None,
    blocks: list[dict[str, object]] | None = None,
    claims: list[dict[str, object]] | None = None,
    context_packet: dict[str, object] | str | None = None,
    output_path: str | None = None,
) -> str:
    """Map generated blocks or claims back to Context Packet source refs."""
    return run_evidence_map_sources(
        composition=composition,
        blocks=blocks,
        claims=claims,
        context_packet=context_packet,
        output_path=output_path,
    ).model_dump_json()


def pdf_evidence_cite_claims(
    claims: list[dict[str, object]],
    composition: dict[str, object] | str | None = None,
    source_map: dict[str, object] | list[dict[str, object]] | str | None = None,
    context_packet: dict[str, object] | str | None = None,
    output_path: str | None = None,
) -> str:
    """Return local citations for claims using source refs and source-map evidence."""
    return run_evidence_cite_claims(
        claims=claims,
        composition=composition,
        source_map=source_map,
        context_packet=context_packet,
        output_path=output_path,
    ).model_dump_json()


def pdf_evidence_context_packet_report(
    context_packet: dict[str, object] | str,
    output_path: str,
    report_output_path: str | None = None,
    title: str | None = None,
    style_pack: str = "paper_ink",
) -> str:
    """Create a validated PDF/JSON report for a Context Packet and source graph."""
    return run_context_packet_report(
        context_packet=context_packet,
        output_path=output_path,
        report_output_path=report_output_path,
        title=title,
        style_pack=style_pack,
    ).model_dump_json()


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


def pdf_artifacts_manifest(
    artifact_paths: list[str],
    output_path: str | None = None,
    title: str | None = None,
    metadata: dict[str, object] | None = None,
) -> str:
    """Create a local artifact manifest with checksums, source refs, and HTML/context evidence."""
    return run_artifacts_manifest(
        artifact_paths=artifact_paths,
        output_path=output_path,
        title=title,
        metadata=metadata,
    ).model_dump_json()


def pdf_artifacts_graph(
    artifact_manifest_path: str | None = None,
    artifact_paths: list[str] | None = None,
    output_path: str | None = None,
    title: str | None = None,
) -> str:
    """Create a local artifact lineage graph with source-ref and HTML/context evidence."""
    return run_artifacts_graph(
        artifact_manifest_path=artifact_manifest_path,
        artifact_paths=artifact_paths or [],
        output_path=output_path,
        title=title,
    ).model_dump_json()


def pdf_artifacts_source_map(
    composition_path: str | None = None,
    source_map_path: str | None = None,
    context_packet_path: str | None = None,
    artifact_manifest_path: str | None = None,
    artifact_paths: list[str] | None = None,
    output_path: str | None = None,
    title: str | None = None,
) -> str:
    """Create an artifact-focused source map index for generated PDF blocks and sources."""
    return run_artifacts_source_map(
        composition_path=composition_path,
        source_map_path=source_map_path,
        context_packet_path=context_packet_path,
        artifact_manifest_path=artifact_manifest_path,
        artifact_paths=artifact_paths or [],
        output_path=output_path,
        title=title,
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
    artifact_graph_path: str | None = None,
    artifact_graph: str | None = None,
    reason: str | None = None,
) -> str:
    """Create a structured patch manifest without mutating the input PDF."""
    return run_patch_plan(
        input_path=input_path,
        operations=operations,
        output_path=output_path,
        composition_path=composition_path,
        layer_manifest_path=layer_manifest_path,
        artifact_graph_path=artifact_graph_path or artifact_graph,
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


def pdf_patch_composition_ir_plan(
    composition_path: str,
    operations: list[dict[str, object]],
    output_path: str,
) -> str:
    """Plan a patch on a Composition IR JSON artifact with 3-layer validation."""
    return run_composition_ir_patch_plan(
        composition_path, operations=operations, output_path=output_path,
    ).model_dump_json()


def pdf_patch_composition_ir_apply(
    patch_manifest: dict[str, object] | str,
    output_path: str,
) -> str:
    """Apply a composition IR patch and write a new composition JSON artifact."""
    return run_composition_ir_patch_apply(patch_manifest, output_path=output_path).model_dump_json()


def pdf_patch_composition_ir_verify(
    patch_manifest: dict[str, object] | str,
    patched_path: str,
) -> str:
    """Verify a patched composition IR artifact against the patch manifest."""
    return run_composition_ir_patch_verify(
        patch_manifest, patched_path=patched_path,
    ).model_dump_json()


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


def pdf_extract_fonts(input_path: str, pages: str = "all") -> str:
    """List fonts referenced by selected local PDF pages."""
    return run_extract_fonts(input_path, pages=pages).model_dump_json()


def pdf_pdf_to_json(input_path: str, output_path: str, pages: str = "all") -> str:
    """Export a local PDF to Document IR JSON."""
    return run_pdf_to_json(input_path, output_path=output_path, pages=pages).model_dump_json()


def pdf_pdf_to_markdown(input_path: str, output_path: str, pages: str = "all") -> str:
    """Export a local PDF to cited Markdown via Document IR."""
    return run_pdf_to_markdown(input_path, output_path=output_path, pages=pages).model_dump_json()


def pdf_pdf_to_html(input_path: str, output_path: str, pages: str = "all") -> str:
    """Export PDF text to a simple HTML document."""
    return run_pdf_to_html(input_path, output_path=output_path, pages=pages).model_dump_json()


def pdf_pdf_to_docx(input_path: str, output_path: str, pages: str = "all") -> str:
    """Export PDF text to a minimal DOCX package."""
    return run_pdf_to_docx(input_path, output_path=output_path, pages=pages).model_dump_json()


def pdf_pdf_to_pptx(input_path: str, output_path: str, pages: str = "all") -> str:
    """Export each PDF page as a simple text slide."""
    return run_pdf_to_pptx(input_path, output_path=output_path, pages=pages).model_dump_json()


def pdf_pdf_to_xlsx(input_path: str, output_path: str, pages: str = "all") -> str:
    """Export PDF page text rows to a minimal XLSX workbook."""
    return run_pdf_to_xlsx(input_path, output_path=output_path, pages=pages).model_dump_json()


def pdf_metadata_read(input_path: str) -> str:
    """Read local PDF document metadata."""
    return run_metadata_read(input_path).model_dump_json()


def pdf_metadata_page_info(input_path: str, pages: str = "all") -> str:
    """Return local PDF page size, rotation, text-layer, and image facts."""
    return run_metadata_page_info(input_path, pages=pages).model_dump_json()


def pdf_metadata_update(input_path: str, metadata: dict[str, object], output_path: str) -> str:
    """Update local PDF metadata and write a new PDF."""
    return run_metadata_update(input_path, metadata=metadata, output_path=output_path).model_dump_json()


def pdf_metadata_update_outline(
    input_path: str,
    outline: list[dict[str, object]],
    output_path: str,
) -> str:
    """Update local PDF outline/bookmarks and write a new PDF."""
    return run_metadata_update_outline(
        input_path,
        outline=outline,
        output_path=output_path,
    ).model_dump_json()


def pdf_metadata_remove(input_path: str, output_path: str) -> str:
    """Remove local PDF metadata and write a new PDF."""
    return run_metadata_remove(input_path, output_path=output_path).model_dump_json()


def pdf_security_remove_metadata(input_path: str, output_path: str) -> str:
    """Remove local PDF metadata under the security namespace and write a new PDF."""
    return run_security_remove_metadata(input_path, output_path=output_path).model_dump_json()


def pdf_security_protect(
    input_path: str,
    output_path: str,
    password: str,
    owner_password: str | None = None,
) -> str:
    """Protect a local PDF with password encryption."""
    return run_security_protect(
        input_path,
        output_path=output_path,
        password=password,
        owner_password=owner_password,
    ).model_dump_json()


def pdf_security_encrypt(
    input_path: str,
    output_path: str,
    password: str,
    owner_password: str | None = None,
) -> str:
    """Encrypt a local PDF with a password."""
    return run_security_encrypt(
        input_path,
        output_path=output_path,
        password=password,
        owner_password=owner_password,
    ).model_dump_json()


def pdf_security_unlock_authorized(input_path: str, output_path: str, password: str) -> str:
    """Unlock a local PDF only with an authorized password."""
    return run_security_unlock_authorized(
        input_path,
        output_path=output_path,
        password=password,
    ).model_dump_json()


def pdf_security_decrypt_authorized(input_path: str, output_path: str, password: str) -> str:
    """Decrypt a local PDF only with an authorized password."""
    return run_security_decrypt_authorized(
        input_path,
        output_path=output_path,
        password=password,
    ).model_dump_json()


def pdf_security_sign(input_path: str, output_path: str, secret: str | None = None) -> str:
    """Create a detached local integrity signature manifest."""
    return run_security_sign(input_path, output_path=output_path, secret=secret).model_dump_json()


def pdf_security_verify_signature(
    input_path: str,
    signature_path: str,
    secret: str | None = None,
) -> str:
    """Verify a detached local integrity signature manifest."""
    return run_security_verify_signature(
        input_path,
        signature_path=signature_path,
        secret=secret,
    ).model_dump_json()


def pdf_security_malware_scan(input_path: str) -> str:
    """Run a local static PDF risk marker scan."""
    return run_security_malware_scan(input_path).model_dump_json()


def pdf_security_sanitize(
    input_path: str,
    output_path: str,
    remove_metadata: bool = True,
) -> str:
    """Rewrite a local PDF while removing known active-content structures and metadata."""
    return run_security_sanitize(
        input_path,
        output_path=output_path,
        remove_metadata=remove_metadata,
    ).model_dump_json()


def pdf_security_redact(
    input_path: str,
    output_path: str,
    regions: list[dict[str, object]],
    fill_color: str = "#000000",
    render_scale: float = 2.0,
) -> str:
    """Redact explicit PDF-coordinate bbox regions into an image-only PDF."""
    return run_security_redact(
        input_path,
        output_path=output_path,
        regions=regions,
        fill_color=fill_color,
        render_scale=render_scale,
    ).model_dump_json()


def pdf_security_verify_redaction(
    input_path: str,
    search_terms: list[str] | None = None,
) -> str:
    """Verify supplied sensitive terms are absent after redaction."""
    return run_security_verify_redaction(input_path, search_terms=search_terms).model_dump_json()


def pdf_validate_output(path: str, expected_pages: int | None = None) -> str:
    """Validate generated local PDF output."""
    return run_validate_output(path, expected_pages=expected_pages).model_dump_json()


def pdf_page_count_check(path: str, expected_pages: int) -> str:
    """Compare a local PDF page count with an expected count."""
    return run_page_count_check(path, expected_pages=expected_pages).model_dump_json()


def pdf_render_check(path: str, pages: str = "all") -> str:
    """Render selected local PDF pages in memory to verify renderability."""
    return run_render_check(path, pages=pages).model_dump_json()


def pdf_blank_page_check(path: str, pages: str = "all") -> str:
    """Detect blank pages in a local PDF."""
    return run_blank_page_check(path, pages=pages).model_dump_json()


def pdf_validation_visual_diff(
    before_path: str,
    after_path: str,
    pages: str = "all",
    max_difference_ratio: float = 0.001,
    render_scale: float = 0.5,
) -> str:
    """Validate before/after PDFs with rendered visual diff evidence."""
    return run_validation_visual_diff(
        before_path,
        after_path,
        pages=pages,
        max_difference_ratio=max_difference_ratio,
        render_scale=render_scale,
    ).model_dump_json()


def pdf_validation_redaction_check(
    input_path: str,
    search_terms: list[str] | None = None,
) -> str:
    """Run validation-grade redaction leak checks for supplied terms."""
    return run_validation_redaction_check(input_path, search_terms=search_terms).model_dump_json()


def pdf_compare_semantic_diff(
    before_path: str,
    after_path: str,
    pages: str = "all",
) -> str:
    """Compare local PDF text layers with heuristic semantic evidence."""
    return run_compare_semantic_diff(
        before_path,
        after_path,
        pages=pages,
    ).model_dump_json()


def pdf_compare_visual_diff(
    before_path: str,
    after_path: str,
    pages: str = "all",
    max_difference_ratio: float = 0.001,
    render_scale: float = 0.5,
) -> str:
    """Compare rendered PDF pages and return local visual difference evidence."""
    return run_compare_visual_diff(
        before_path,
        after_path,
        pages=pages,
        max_difference_ratio=max_difference_ratio,
        render_scale=render_scale,
    ).model_dump_json()


def pdf_compare_version_report(
    before_path: str,
    after_path: str,
    output_path: str | None = None,
    pages: str = "all",
) -> str:
    """Create a Markdown version report from local PDF text-layer changes."""
    return run_compare_version_report(
        before_path,
        after_path,
        output_path=output_path,
        pages=pages,
    ).model_dump_json()


def pdf_ai_parse_lite(input_path: str, pages: str = "all") -> str:
    """Parse a local PDF text layer into Document IR."""
    return run_parse_lite(input_path, pages=pages).model_dump_json()


def pdf_ai_parse_figures(input_path: str, pages: str = "all") -> str:
    """Detect figure captions and page image hints from a local PDF."""
    return run_parse_figures(input_path, pages=pages).model_dump_json()


def pdf_ai_parse_formulas(input_path: str, pages: str = "all") -> str:
    """Detect formula-like text lines from a local PDF."""
    return run_parse_formulas(input_path, pages=pages).model_dump_json()


def pdf_ai_parse_charts(input_path: str, pages: str = "all") -> str:
    """Detect chart captions from a local PDF."""
    return run_parse_charts(input_path, pages=pages).model_dump_json()


def pdf_ai_parse_references(input_path: str, pages: str = "all") -> str:
    """Detect reference lines, DOIs, and URLs from a local PDF."""
    return run_parse_references(input_path, pages=pages).model_dump_json()


def pdf_forms_create(output_path: str, fields: list[dict[str, object]]) -> str:
    """Create a local PDF with text form fields."""
    return run_forms_create(output_path=output_path, fields=fields).model_dump_json()


def pdf_forms_import_data(
    input_path: str,
    data: dict[str, object],
    output_path: str,
) -> str:
    """Import local JSON field data into a PDF form."""
    return run_forms_import_data(input_path, data=data, output_path=output_path).model_dump_json()


def pdf_forms_validate(input_path: str, required_fields: list[str] | None = None) -> str:
    """Validate required PDF form fields."""
    return run_forms_validate(input_path, required_fields=required_fields).model_dump_json()


def pdf_ocr_scan_to_pdf(image_paths: list[str], output_path: str) -> str:
    """Create an image-only PDF from local scan images."""
    return run_ocr_scan_to_pdf(image_paths, output_path=output_path).model_dump_json()


def pdf_ocr(
    input_path: str,
    pages: str = "all",
    languages: list[str] | None = None,
    dpi: int = 200,
    engine: str = "tesseract",
    psm: int = 6,
) -> str:
    """Run local OCR and return text regions with bboxes."""
    return run_ocr(
        input_path,
        pages=pages,
        languages=languages,
        dpi=dpi,
        engine=engine,
        psm=psm,
    ).model_dump_json()


def pdf_ocr_searchable_pdf(
    input_path: str,
    output_path: str,
    pages: str = "all",
    languages: list[str] | None = None,
    dpi: int = 200,
    engine: str = "tesseract",
    psm: int = 6,
) -> str:
    """Add a local OCR text layer to a PDF."""
    return run_ocr_searchable_pdf(
        input_path,
        output_path=output_path,
        pages=pages,
        languages=languages,
        dpi=dpi,
        engine=engine,
        psm=psm,
    ).model_dump_json()


def pdf_ocr_despeckle(input_path: str, output_path: str) -> str:
    """Run local scan despeckle preparation."""
    return run_ocr_despeckle(input_path, output_path=output_path).model_dump_json()


def pdf_ocr_remove_existing_ocr(input_path: str, output_path: str) -> str:
    """Rewrite a PDF while removing existing OCR-layer metadata where possible."""
    return run_ocr_remove_existing(input_path, output_path=output_path).model_dump_json()


def pdf_ocr_multilingual_ocr(
    input_path: str,
    output_path: str,
    languages: list[str] | None = None,
) -> str:
    """Record a local multilingual OCR request and rewrite the PDF artifact."""
    return run_ocr_multilingual(input_path, output_path=output_path, languages=languages).model_dump_json()


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


def office_extract_claims(path: str) -> str:
    """Extract claim-like sentences from any Office document."""
    return run_extract_office_claims(path).model_dump_json()


def office_extract_entities(path: str) -> str:
    """Extract named entities heuristically from any Office document."""
    return run_extract_office_entities(path).model_dump_json()


def office_extract_obligations(path: str) -> str:
    """Extract obligation sentences from any Office document."""
    return run_extract_office_obligations(path).model_dump_json()


def office_inspect_batch(paths: list[str]) -> str:
    """Inspect multiple Office files and return aggregated per-file results."""
    return run_inspect_office_batch(paths).model_dump_json()


def office_evidence_map_sources(
    context_packet: dict[str, object],
    composition: dict[str, object] | None = None,
) -> str:
    """Map composition blocks back to context packet source refs."""
    return run_map_office_evidence_sources(context_packet, composition=composition).model_dump_json()


def office_evidence_coverage(composition: dict[str, object]) -> str:
    """Coverage report from a composition artifact."""
    return run_report_office_evidence_coverage(composition).model_dump_json()


def office_context_classify(
    context_packet: dict[str, object],
    target_profile: dict[str, object] | None = None,
) -> str:
    """Classify context items for agent routing into target blocks and slots."""
    return run_classify_office_context(context_packet, target_profile=target_profile).model_dump_json()


def office_evidence_verify_citations(
    claims: list[dict[str, object]],
    context_packet: dict[str, object],
    source_map: dict[str, object] | None = None,
) -> str:
    """Verify evidence citations against claims using context packet and source map."""
    return run_verify_office_evidence_citations(
        claims, context_packet, source_map=source_map,
    ).model_dump_json()


def office_bundle_report(bundle_path: str) -> str:
    """Report on an OKoffice bundle with manifest, artifact, and checksum evidence."""
    return run_report_office_bundle(bundle_path).model_dump_json()


def office_validate_output(path: str, expected_format: str | None = None) -> str:
    """Validate generated Office output before returning artifacts."""
    return run_validate_office_output(path, expected_format=expected_format).model_dump_json()


def office_patch_plan(path: str, operations: list[dict[str, object]]) -> str:
    """Plan patch operations for an Office document without applying them."""
    return run_plan_office_patch(path=path, operations=operations).model_dump_json()


def office_patch_preview(path: str, operations: list[dict[str, object]]) -> str:
    """Preview patch effects on an Office document without applying them."""
    return run_preview_office_patch(path=path, operations=operations).model_dump_json()


def office_patch_verify(input_path: str, output_path: str, patch_manifest: dict[str, object] | None = None) -> str:
    """Verify a patched Office file against the original."""
    return run_verify_office_patch(input_path=input_path, output_path=output_path,
                                   patch_manifest=patch_manifest).model_dump_json()


def office_workflow_review_and_patch(path: str, output_path: str, operations: list[dict[str, object]]) -> str:
    """Full workflow: inspect, plan, apply patch, and validate an Office document."""
    return run_review_and_patch_workflow(path=path, output_path=output_path,
                                         operations=operations).model_dump_json()


def office_workflow_redaction_packet(path: str, search_terms: list[str]) -> str:
    """Build a redaction-ready packet from cross-format text scanning."""
    return run_build_redaction_packet(path=path, search_terms=search_terms).model_dump_json()


def office_bundle_graph(artifact_paths: list[str]) -> str:
    """Create an artifact lineage graph from multi-format Office outputs."""
    return run_build_artifact_graph(artifact_paths=artifact_paths).model_dump_json()


# --- Phase 2: Alias handlers ---

def office_artifacts_bundle(artifact_paths: list[str], output_path: str,
                            title: str | None = None,
                            metadata: dict[str, object] | None = None) -> str:
    """Export local Office artifacts into a portable OKoffice bundle ZIP."""
    return run_office_artifacts_bundle(artifact_paths=artifact_paths,
                                       output_path=output_path,
                                       title=title,
                                       metadata=metadata).model_dump_json()


def word_extract_structure(path: str) -> str:
    """Extract a Word document outline, sections, references, and source-map anchors."""
    return run_word_extract_structure(path).model_dump_json()


def word_convert_to_pdf(input_path: str, output_path: str) -> str:
    """Convert DOCX to validated PDF through explicit local or configured renderer backends."""
    return run_word_convert_to_pdf(input_path, output_path).model_dump_json()


def word_convert_from_pdf(input_path: str, output_path: str) -> str:
    """Convert PDFs into editable DOCX drafts with layout warnings and source mapping."""
    return run_word_convert_from_pdf(input_path, output_path).model_dump_json()


def pdf_read_document(path: str, pages: str = "all", render_check: bool = False) -> str:
    """Read PDF document structure, pages, text, images, tables, metadata, and render facts."""
    return run_pdf_read_document(path, pages=pages, render_check=render_check).model_dump_json()


def pdf_convert_to_docx(input_path: str, output_path: str, pages: str = "all") -> str:
    """Convert PDF pages into DOCX drafts with source refs and layout-loss warnings."""
    return run_pdf_convert_to_docx(input_path, output_path, pages=pages).model_dump_json()


def pdf_convert_to_xlsx(input_path: str, output_path: str, pages: str = "all") -> str:
    """Convert PDF tables and selected fields into XLSX workbooks with provenance."""
    return run_pdf_convert_to_xlsx(input_path, output_path, pages=pages).model_dump_json()


def pdf_convert_to_pptx(input_path: str, output_path: str, pages: str = "all") -> str:
    """Convert PDF page evidence into PPTX drafts with page screenshots and editable notes."""
    return run_pdf_convert_to_pptx(input_path, output_path, pages=pages).model_dump_json()


# --- Phase 3: Workflow orchestrators ---

def office_workflow_source_to_deck(
    files: list[str | dict[str, object]],
    schema: dict[str, object] | str,
    output_path: str,
    title: str | None = None,
    intent: str | None = None,
    deck_title: str | None = None,
    max_rows_per_sheet: int = 100,
) -> str:
    """End-to-end: source documents -> evidence workbook -> deck with taste review."""
    return run_office_workflow_source_to_deck(
        files=files,
        schema=schema,
        output_path=output_path,
        title=title,
        intent=intent,
        deck_title=deck_title,
        max_rows_per_sheet=max_rows_per_sheet,
    ).model_dump_json()


def office_workflow_source_to_doc(
    files: list[str | dict[str, object]],
    schema: dict[str, object] | str,
    output_path: str,
    title: str | None = None,
    intent: str | None = None,
    profile: str = "executive_memo",
) -> str:
    """End-to-end: source documents -> evidence workbook -> Word report."""
    return run_office_workflow_source_to_doc(
        files=files,
        schema=schema,
        output_path=output_path,
        title=title,
        intent=intent,
        profile=profile,
    ).model_dump_json()


def deck_export_pdf_handler(input_path: str, output_path: str) -> str:
    """Export PPTX deck to PDF with slide render checks."""
    return run_deck_export_pdf(input_path, output_path).model_dump_json()


# --- Phase 4: New tool implementations ---

def office_workflow_multi_format_brief_handler(
    files: list[str],
    output_path: str | None = None,
    title: str | None = None,
    intent: str | None = None,
) -> str:
    """Build a structured brief from mixed-format source files."""
    return run_office_workflow_multi_format_brief(
        files=files, output_path=output_path, title=title, intent=intent,
    ).model_dump_json()


def word_comment_review_handler(
    input_path: str,
    output_path: str | None = None,
    resolve_ids: list[str] | None = None,
) -> str:
    """Review and optionally resolve Word document comments."""
    return run_word_comment_review(
        input_path=input_path, output_path=output_path, resolve_ids=resolve_ids,
    ).model_dump_json()


def sheet_visualize_chart_handler(
    input_path: str,
    output_path: str,
    sheet: str | None = None,
    chart_type: str = "bar",
    data_range: str | None = None,
    title: str | None = None,
    categories_range: str | None = None,
    series_ranges: list[str] | None = None,
) -> str:
    """Create a chart in an Excel workbook."""
    return run_sheet_visualize_chart(
        input_path=input_path, output_path=output_path, sheet=sheet,
        chart_type=chart_type, data_range=data_range, title=title,
        categories_range=categories_range, series_ranges=series_ranges,
    ).model_dump_json()


def deck_edit_apply_theme_handler(
    input_path: str,
    output_path: str,
    theme_name: str | None = None,
    colors: dict[str, str] | None = None,
) -> str:
    """Apply a color theme to a PPTX deck."""
    return run_deck_edit_apply_theme(
        input_path=input_path, output_path=output_path,
        theme_name=theme_name, colors=colors,
    ).model_dump_json()


def pdf_extract_tables_handler(
    input_path: str,
    pages: str = "all",
    output_path: str | None = None,
) -> str:
    """Detect and extract tables from PDF text layers."""
    return run_pdf_extract_tables(
        input_path=input_path, pages=pages, output_path=output_path,
    ).model_dump_json()


# Phase 5 alias handlers

def office_workflow_extract_to_sheet_handler(
    input_paths: list[str],
    output_path: str,
    context_packet_path: str | None = None,
) -> str:
    """Extract from multiple sources into a sheet (alias for docset_to_sheet)."""
    return run_office_workflow_extract_to_sheet(
        input_paths=input_paths, output_path=output_path,
        context_packet_path=context_packet_path,
    ).model_dump_json()


def office_workflow_source_to_board_pack_alias_handler(
    files: list[str],
    output_path: str,
    title: str | None = None,
) -> str:
    """Create a board pack from sources (alias for board_pack)."""
    return run_office_workflow_source_to_board_pack_alias(
        files=files, output_path=output_path, title=title,
    ).model_dump_json()


def word_read_document_handler(path: str) -> str:
    """Read a Word document (alias for inspect_document)."""
    return run_word_read_document(path=path).model_dump_json()


def word_write_document_handler(
    output_path: str,
    document_ir: dict[str, object],
) -> str:
    """Write a Word document (alias for create_document)."""
    return run_word_write_document(
        output_path=output_path, document_ir=document_ir,
    ).model_dump_json()


def sheet_edit_patch_handler(
    input_path: str,
    output_path: str,
    operations: list[dict[str, object]],
) -> str:
    """Edit a spreadsheet via patch operations (alias for patch_cells)."""
    return run_sheet_edit_patch(
        input_path=input_path, output_path=output_path, operations=operations,
    ).model_dump_json()


def word_edit_patch_handler(
    input_path: str,
    output_path: str,
    operations: list[dict[str, object]],
) -> str:
    """Edit a Word document via patch operations (alias for word_patch)."""
    return run_word_edit_patch(
        input_path=input_path, output_path=output_path, operations=operations,
    ).model_dump_json()


def run_mcp_server(transport: Literal["stdio", "sse", "streamable-http"] = "stdio") -> None:
    create_mcp_server().run(transport=transport)
