"""OKoffice target tool surface built on the current compatibility package."""

from okoffice.office.context import build_office_context_packet
from okoffice.office.bundle import export_office_bundle, verify_office_bundle
from okoffice.office.deck import (
    create_deck_from_outline,
    export_deck_pptx,
    inspect_deck_presentation,
    render_deck_html,
    validate_deck_html_preview,
    validate_deck_presentation,
)
from okoffice.office.deck_plan import compose_deck_plan
from okoffice.office.deck_patch import apply_deck_patch, revise_deck
from okoffice.office.deck_validation import (
    validate_deck_contact_sheet,
    validate_deck_notes,
    validate_deck_placeholders,
    validate_deck_presentation as validate_deck_quality_presentation,
)
from okoffice.office.deck_taste_qa import review_deck_taste
from okoffice.office.deck_review import review_deck_claims, review_deck_story
from okoffice.office.deck_writer import create_deck_presentation
from okoffice.office.extract import extract_schema
from okoffice.office.inspect import inspect_office_file
from okoffice.office.manifest import load_office_tool_manifest
from okoffice.office.planner import plan_office_workflow
from okoffice.office.sheet import (
    create_evidence_workbook,
    extract_sheet_tables,
    inspect_sheet_workbook,
    profile_sheet_data,
    read_sheet_workbook,
    validate_sheet_workbook,
    write_sheet_workbook,
)
from okoffice.office.sheet_patch import (
    patch_sheet_cells,
    patch_sheet_chart,
    patch_sheet_formulas,
    patch_sheet_table,
)
from okoffice.office.sheet_review import (
    review_sheet_model,
    review_sheet_number_consistency,
)
from okoffice.office.sheet_extract import (
    extract_sheet_charts,
    extract_sheet_comments,
    extract_sheet_formulas,
    extract_sheet_named_ranges,
    extract_sheet_pivots,
)
from okoffice.office.deck_extract import (
    extract_deck_charts,
    extract_deck_media,
    extract_deck_notes,
    extract_deck_shapes,
    extract_deck_text,
    extract_deck_theme,
)
from okoffice.office.validation import validate_office_package, validate_sheet_formulas
from okoffice.office.word import extract_word_tables, inspect_word_document
from okoffice.office.word_create import create_word_document, create_word_memo
from okoffice.office.word_extract import (
    extract_word_comments,
    extract_word_fields,
    extract_word_outline,
    extract_word_revisions,
    extract_word_styles,
    extract_word_text,
)
from okoffice.office.word_patch import apply_word_patch, plan_word_patch
from okoffice.office.word_report import create_word_report
from okoffice.office.word_validation import validate_word_accessibility, validate_word_document, validate_word_metadata
from okoffice.office.word_review import review_word_style
from okoffice.office.workers import inspect_office_workers
from okoffice.office.evidence import (
    classify_office_context,
    map_office_evidence_sources,
    report_office_evidence_coverage,
)
from okoffice.office.office_batch import inspect_office_batch
from okoffice.office.office_extract import (
    extract_office_claims,
    extract_office_entities,
    extract_office_obligations,
)
from okoffice.office.bundle_report import report_office_bundle, validate_office_output
from okoffice.office.evidence_verify import verify_office_evidence_citations
from okoffice.office.workflows import board_pack, docset_to_sheet, extract_to_sheet, sheet_to_deck, source_to_board_pack, verify_board_pack
from okoffice.office.office_patch import plan_office_patch, preview_office_patch, verify_office_patch
from okoffice.office.workflows_extended import review_and_patch_workflow, build_redaction_packet, build_artifact_graph

__all__ = [
    "build_office_context_packet",
    "board_pack",
    "docset_to_sheet",
    "extract_to_sheet",
    "sheet_to_deck",
    "source_to_board_pack",
    "verify_board_pack",
    "export_office_bundle",
    "verify_office_bundle",
    "apply_deck_patch",
    "revise_deck",
    "apply_word_patch",
    "create_evidence_workbook",
    "create_deck_presentation",
    "create_word_document",
    "create_word_memo",
    "create_word_report",
    "extract_sheet_tables",
    "extract_sheet_charts",
    "extract_sheet_comments",
    "extract_sheet_formulas",
    "extract_sheet_named_ranges",
    "extract_sheet_pivots",
    "extract_deck_charts",
    "extract_deck_media",
    "extract_deck_notes",
    "extract_deck_shapes",
    "extract_deck_text",
    "extract_deck_theme",
    "classify_office_context",
    "extract_office_claims",
    "extract_office_entities",
    "extract_office_obligations",
    "extract_schema",
    "extract_word_comments",
    "extract_word_fields",
    "extract_word_outline",
    "extract_word_revisions",
    "extract_word_styles",
    "extract_word_tables",
    "extract_word_text",
    "compose_deck_plan",
    "create_deck_from_outline",
    "export_deck_pptx",
    "inspect_deck_presentation",
    "render_deck_html",
    "validate_deck_html_preview",
    "validate_deck_presentation",
    "validate_deck_quality_presentation",
    "validate_deck_contact_sheet",
    "validate_deck_notes",
    "validate_deck_placeholders",
    "review_deck_taste",
    "review_deck_story",
    "review_deck_claims",
    "inspect_office_batch",
    "inspect_office_file",
    "inspect_office_workers",
    "inspect_sheet_workbook",
    "inspect_word_document",
    "load_office_tool_manifest",
    "map_office_evidence_sources",
    "plan_office_workflow",
    "profile_sheet_data",
    "read_sheet_workbook",
    "plan_word_patch",
    "validate_sheet_formulas",
    "validate_sheet_workbook",
    "validate_office_package",
    "validate_word_document",
    "validate_word_metadata",
    "validate_word_accessibility",
    "review_word_style",
    "write_sheet_workbook",
    "patch_sheet_cells",
    "patch_sheet_table",
    "patch_sheet_formulas",
    "patch_sheet_chart",
    "review_sheet_model",
    "report_office_bundle",
    "validate_office_output",
    "verify_office_evidence_citations",
    "report_office_evidence_coverage",
    "review_sheet_number_consistency",
    "plan_office_patch",
    "preview_office_patch",
    "verify_office_patch",
    "review_and_patch_workflow",
    "build_redaction_packet",
    "build_artifact_graph",
]
