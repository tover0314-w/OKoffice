"""OKoffice target tool surface built on the current compatibility package."""

from agentpdf.office.deck import inspect_deck_presentation
from agentpdf.office.manifest import load_office_tool_manifest
from agentpdf.office.inspect import inspect_office_file
from agentpdf.office.planner import plan_office_workflow
from agentpdf.office.sheet import inspect_sheet_workbook
from agentpdf.office.word import inspect_word_document

__all__ = [
    "inspect_deck_presentation",
    "inspect_office_file",
    "inspect_sheet_workbook",
    "inspect_word_document",
    "load_office_tool_manifest",
    "plan_office_workflow",
]
