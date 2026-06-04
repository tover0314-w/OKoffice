"""OKoffice target tool surface built on the current compatibility package."""

from agentpdf.office.manifest import load_office_tool_manifest
from agentpdf.office.inspect import inspect_office_file
from agentpdf.office.planner import plan_office_workflow

__all__ = ["inspect_office_file", "load_office_tool_manifest", "plan_office_workflow"]
