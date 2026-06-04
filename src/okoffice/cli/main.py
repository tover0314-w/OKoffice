from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any

import typer

from agentpdf.office.inspect import inspect_office_file
from agentpdf.office.planner import plan_office_workflow
from okoffice import __version__
from okoffice.tools.registry import load_okoffice_manifest


app = typer.Typer(help="okoffice local-first agent-native Office CLI")
tools_app = typer.Typer(help="Discover target okoffice tools and legacy compatibility tools.")
app.add_typer(tools_app, name="tools")


@app.callback()
def main() -> None:
    """Agent-native Office infrastructure for local Word, Excel, PowerPoint, PDF, and bundle workflows."""


@app.command()
def version() -> None:
    """Print the okoffice version."""
    typer.echo(f"okoffice {__version__}")


@app.command("manifest")
def manifest(
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Print the okoffice manifest, including legacy pdf.* compatibility tools."""
    payload = load_okoffice_manifest()
    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False))
        return
    typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))


@app.command("plan")
def plan(
    goal: Annotated[str, typer.Option("--goal", "-g", help="Workflow goal for the office agent.")],
    input_paths: Annotated[
        list[Path] | None,
        typer.Option("--input", "-i", help="Input Word, Excel, PPT, PDF, or text source path."),
    ] = None,
    output_paths: Annotated[
        list[Path] | None,
        typer.Option("--output", "-o", help="Desired output document, workbook, deck, or PDF path."),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Plan a cross-format okoffice workflow without mutating files."""
    result = plan_office_workflow(
        goal=goal,
        input_paths=input_paths or [],
        output_paths=output_paths or [],
    )
    if json_output:
        typer.echo(result.model_dump_json())
        return
    typer.echo(result.model_dump_json(indent=2))


@app.command("inspect")
def inspect(
    path: Annotated[Path, typer.Argument(help="Office artifact path to inspect.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Inspect a local Office artifact without mutating it."""
    result = inspect_office_file(path)
    if json_output:
        typer.echo(result.model_dump_json())
    else:
        typer.echo(result.model_dump_json(indent=2))
    if result.status == "failed":
        raise typer.Exit(1)


@tools_app.command("list")
def tools_list(
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """List target okoffice tools plus legacy pdf.* compatibility tools."""
    manifest = load_okoffice_manifest()
    if json_output:
        typer.echo(json.dumps(manifest, ensure_ascii=False))
        return
    typer.echo("okoffice target tools")
    for tool in manifest["target_tools"]:
        implemented = "implemented" if tool.get("implemented") else str(tool.get("status", "planned"))
        typer.echo(f"{tool['name']}\t{implemented}\t{tool['description']}")
    typer.echo("")
    typer.echo("legacy compatibility tools")
    for tool in manifest["compatibility_tools"]:
        marker = "implemented" if tool.get("implemented") else str(tool.get("compatibility_status") or "legacy_compat")
        typer.echo(f"{tool['name']}\tlegacy_compat/{marker}\t{tool['description']}")


@tools_app.command("show")
def tools_show(
    name: Annotated[str, typer.Argument(help="Tool name, such as office.inspect.file or pdf.inspect.document.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Show one target or legacy compatibility tool."""
    tool = _find_tool(name)
    if json_output:
        typer.echo(json.dumps(tool, ensure_ascii=False))
        return
    typer.echo(f"{tool['name']}\nstatus: {tool['status']}\nimplemented: {tool.get('implemented', False)}")


def _find_tool(name: str) -> dict[str, Any]:
    manifest = load_okoffice_manifest()
    for tool in [*manifest["target_tools"], *manifest["compatibility_tools"]]:
        if tool["name"] == name:
            return dict(tool)
    raise typer.BadParameter(f"Unknown okoffice tool: {name}")
