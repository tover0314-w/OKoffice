"""OKoffice target tool surface built on the current compatibility package."""

from agentpdf.office.manifest import load_office_tool_manifest
from agentpdf.office.bundle import export_office_bundle, verify_office_bundle
from agentpdf.office.context import build_office_context_packet
from agentpdf.office.deck import inspect_deck_presentation
from agentpdf.office.deck_patch import apply_deck_patch
from agentpdf.office.deck_validation import validate_deck_contact_sheet, validate_deck_presentation
from agentpdf.office.deck_writer import create_deck_presentation
from agentpdf.office.extract import extract_schema, extract_schema_from_context
from agentpdf.office.inspect import inspect_office_file
from agentpdf.office.ir import (
    DeckLocator,
    OfficeIR,
    PdfLocator,
    SheetLocator,
    SourceGraph,
    SourceGraphEdge,
    SourceGraphNode,
    SourceRef,
    WordLocator,
)
from agentpdf.office.planner import plan_office_workflow
from agentpdf.office.sheet import inspect_sheet_workbook
from agentpdf.office.validation import validate_office_package, validate_sheet_formulas
from agentpdf.office.word import inspect_word_document
from agentpdf.office.word_patch import apply_word_patch, plan_word_patch
from agentpdf.office.word_validation import validate_word_document
from agentpdf.office.word_report import create_word_report
from agentpdf.office.workbook import write_sheet_workbook
from agentpdf.office.workers import inspect_office_workers
from agentpdf.office.workflows import board_pack, docset_to_sheet, sheet_to_deck

__all__ = [
    "DeckLocator",
    "OfficeIR",
    "PdfLocator",
    "SheetLocator",
    "SourceGraph",
    "SourceGraphEdge",
    "SourceGraphNode",
    "SourceRef",
    "WordLocator",
    "build_office_context_packet",
    "apply_deck_patch",
    "apply_word_patch",
    "board_pack",
    "create_word_report",
    "docset_to_sheet",
    "export_office_bundle",
    "extract_schema",
    "extract_schema_from_context",
    "create_deck_presentation",
    "inspect_deck_presentation",
    "inspect_office_file",
    "inspect_office_workers",
    "inspect_sheet_workbook",
    "inspect_word_document",
    "load_office_tool_manifest",
    "plan_office_workflow",
    "plan_word_patch",
    "sheet_to_deck",
    "validate_deck_contact_sheet",
    "validate_deck_presentation",
    "validate_office_package",
    "validate_sheet_formulas",
    "validate_word_document",
    "verify_office_bundle",
    "write_sheet_workbook",
]
