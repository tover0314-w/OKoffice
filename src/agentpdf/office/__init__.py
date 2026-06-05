"""OKoffice target tool surface built on the current compatibility package."""

from agentpdf.office.context import build_office_context_packet
from agentpdf.office.deck import (
    create_deck_from_outline,
    create_deck_presentation,
    inspect_deck_presentation,
    validate_deck_presentation,
)
from agentpdf.office.deck_plan import compose_deck_plan
from agentpdf.office.extract import extract_schema
from agentpdf.office.manifest import load_office_tool_manifest
from agentpdf.office.inspect import inspect_office_file
from agentpdf.office.planner import plan_office_workflow
from agentpdf.office.sheet import (
    create_evidence_workbook,
    extract_sheet_tables,
    inspect_sheet_workbook,
    profile_sheet_data,
    read_sheet_workbook,
    validate_sheet_formulas,
    validate_sheet_workbook,
    write_sheet_workbook,
)
from agentpdf.office.validation import validate_office_package
from agentpdf.office.word import extract_word_tables, inspect_word_document
from agentpdf.office.workflows import board_pack, extract_to_sheet, sheet_to_deck, verify_board_pack

__all__ = [
    "build_office_context_packet",
    "board_pack",
    "extract_to_sheet",
    "sheet_to_deck",
    "verify_board_pack",
    "create_evidence_workbook",
    "extract_sheet_tables",
    "extract_schema",
    "extract_word_tables",
    "compose_deck_plan",
    "create_deck_from_outline",
    "create_deck_presentation",
    "inspect_deck_presentation",
    "validate_deck_presentation",
    "inspect_office_file",
    "inspect_sheet_workbook",
    "inspect_word_document",
    "load_office_tool_manifest",
    "plan_office_workflow",
    "profile_sheet_data",
    "read_sheet_workbook",
    "validate_sheet_formulas",
    "validate_sheet_workbook",
    "validate_office_package",
    "write_sheet_workbook",
]
