"""OKoffice target tool surface built on the current compatibility package."""

from agentpdf.office.deck import inspect_deck_presentation
from agentpdf.office.manifest import load_office_tool_manifest
from agentpdf.office.inspect import inspect_office_file
from agentpdf.office.planner import plan_office_workflow
from agentpdf.office.sheet import (
    extract_sheet_tables,
    inspect_sheet_workbook,
    read_sheet_workbook,
    validate_sheet_workbook,
    write_sheet_workbook,
)
from agentpdf.office.word import extract_word_tables, inspect_word_document
from agentpdf.office.workflows import extract_to_sheet

__all__ = [
    "extract_to_sheet",
    "extract_sheet_tables",
    "extract_word_tables",
    "inspect_deck_presentation",
    "inspect_office_file",
    "inspect_sheet_workbook",
    "inspect_word_document",
    "load_office_tool_manifest",
    "plan_office_workflow",
    "read_sheet_workbook",
    "validate_sheet_workbook",
    "write_sheet_workbook",
]
