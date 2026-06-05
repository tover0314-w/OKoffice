"""OKoffice target tool surface built on the current compatibility package."""

from agentpdf.office.context import build_office_context_packet
from agentpdf.office.bundle import export_office_bundle, verify_office_bundle
from agentpdf.office.deck import create_deck_from_outline, inspect_deck_presentation, validate_deck_presentation
from agentpdf.office.deck_plan import compose_deck_plan
from agentpdf.office.deck_patch import apply_deck_patch
from agentpdf.office.deck_validation import (
    validate_deck_contact_sheet,
    validate_deck_presentation as validate_deck_quality_presentation,
)
from agentpdf.office.deck_writer import create_deck_presentation
from agentpdf.office.extract import extract_schema
from agentpdf.office.inspect import inspect_office_file
from agentpdf.office.manifest import load_office_tool_manifest
from agentpdf.office.planner import plan_office_workflow
from agentpdf.office.sheet import (
    create_evidence_workbook,
    extract_sheet_tables,
    inspect_sheet_workbook,
    profile_sheet_data,
    read_sheet_workbook,
    validate_sheet_workbook,
    write_sheet_workbook,
)
from agentpdf.office.validation import validate_office_package, validate_sheet_formulas
from agentpdf.office.word import extract_word_tables, inspect_word_document
from agentpdf.office.word_patch import apply_word_patch, plan_word_patch
from agentpdf.office.word_report import create_word_report
from agentpdf.office.word_validation import validate_word_document
from agentpdf.office.workers import inspect_office_workers
from agentpdf.office.workflows import board_pack, docset_to_sheet, extract_to_sheet, sheet_to_deck, verify_board_pack

__all__ = [
    "build_office_context_packet",
    "board_pack",
    "docset_to_sheet",
    "extract_to_sheet",
    "sheet_to_deck",
    "verify_board_pack",
    "export_office_bundle",
    "verify_office_bundle",
    "apply_deck_patch",
    "apply_word_patch",
    "create_evidence_workbook",
    "create_deck_presentation",
    "create_word_report",
    "extract_sheet_tables",
    "extract_schema",
    "extract_word_tables",
    "compose_deck_plan",
    "create_deck_from_outline",
    "inspect_deck_presentation",
    "validate_deck_presentation",
    "validate_deck_quality_presentation",
    "validate_deck_contact_sheet",
    "inspect_office_file",
    "inspect_office_workers",
    "inspect_sheet_workbook",
    "inspect_word_document",
    "load_office_tool_manifest",
    "plan_office_workflow",
    "profile_sheet_data",
    "read_sheet_workbook",
    "plan_word_patch",
    "validate_sheet_formulas",
    "validate_sheet_workbook",
    "validate_office_package",
    "validate_word_document",
    "write_sheet_workbook",
]
