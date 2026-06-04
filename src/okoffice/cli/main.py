from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any

import typer

from agentpdf.office.deck import create_deck_from_outline, inspect_deck_presentation, validate_deck_presentation
from agentpdf.office.inspect import inspect_office_file
from agentpdf.office.planner import plan_office_workflow
from agentpdf.office.sheet import (
    extract_sheet_tables,
    inspect_sheet_workbook,
    profile_sheet_data,
    read_sheet_workbook,
    validate_sheet_workbook,
    write_sheet_workbook,
)
from agentpdf.office.word import extract_word_tables, inspect_word_document
from agentpdf.office.workflows import board_pack, extract_to_sheet, sheet_to_deck
from okoffice import __version__
from okoffice.tools.registry import load_okoffice_manifest


app = typer.Typer(help="okoffice local-first agent-native Office CLI")
tools_app = typer.Typer(help="Discover target okoffice tools and legacy compatibility tools.")
word_app = typer.Typer(help="Inspect and transform Word documents.")
sheet_app = typer.Typer(help="Inspect and transform Excel workbooks.")
deck_app = typer.Typer(help="Inspect and transform PowerPoint decks.")
workflow_app = typer.Typer(help="Run local cross-format OKoffice workflows.")


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


@word_app.command("inspect")
def word_inspect(
    path: Annotated[Path, typer.Argument(help="DOCX artifact path to inspect.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Inspect a local Word document without mutating it."""
    _emit_result(inspect_word_document(path), json_output=json_output)


@word_app.command("extract-tables")
def word_extract_tables(
    path: Annotated[Path, typer.Argument(help="DOCX artifact path to extract tables from.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Extract Word tables into normalized agent-readable records."""
    _emit_result(extract_word_tables(path), json_output=json_output)


@sheet_app.command("inspect")
def sheet_inspect(
    path: Annotated[Path, typer.Argument(help="XLSX artifact path to inspect.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Inspect a local Excel workbook without mutating it."""
    _emit_result(inspect_sheet_workbook(path), json_output=json_output)


@sheet_app.command("extract-tables")
def sheet_extract_tables(
    path: Annotated[Path, typer.Argument(help="XLSX artifact path to extract tables from.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Extract workbook tables with sheet, row, column, and cell references."""
    _emit_result(extract_sheet_tables(path), json_output=json_output)


@sheet_app.command("read")
def sheet_read(
    path: Annotated[Path, typer.Argument(help="XLSX artifact path to read.")],
    max_rows_per_sheet: Annotated[int, typer.Option("--max-rows", help="Maximum non-empty rows returned per sheet.")] = 100,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Read workbook rows, cells, formulas, and source refs as bounded JSON."""
    _emit_result(read_sheet_workbook(path, max_rows_per_sheet=max_rows_per_sheet), json_output=json_output)


@sheet_app.command("profile")
def sheet_profile(
    path: Annotated[Path, typer.Argument(help="XLSX artifact path to profile.")],
    max_rows_per_sheet: Annotated[int, typer.Option("--max-rows", help="Maximum non-empty rows read per sheet.")] = 100,
    include_source_refs: Annotated[
        bool,
        typer.Option("--include-source-refs", help="Profile the SourceRefs provenance sheet too."),
    ] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Profile workbook headers, data types, missing cells, formulas, and source coverage."""
    _emit_result(
        profile_sheet_data(
            path,
            max_rows_per_sheet=max_rows_per_sheet,
            include_source_refs=include_source_refs,
        ),
        json_output=json_output,
    )


@sheet_app.command("write-workbook")
def sheet_write_workbook(
    data_path: Annotated[Path, typer.Argument(help="JSON records or ToolResult path to write as XLSX.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output XLSX workbook path.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Write an XLSX workbook from structured records with source refs."""
    payload = json.loads(data_path.read_text(encoding="utf-8"))
    _emit_result(write_sheet_workbook(payload, output_path), json_output=json_output)


@sheet_app.command("validate")
def sheet_validate(
    path: Annotated[Path, typer.Argument(help="XLSX artifact path to validate.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Validate workbook structure, safety markers, and source-map readiness."""
    _emit_result(validate_sheet_workbook(path), json_output=json_output)


@deck_app.command("inspect")
def deck_inspect(
    path: Annotated[Path, typer.Argument(help="PPTX artifact path to inspect.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Inspect a local PowerPoint deck without mutating it."""
    _emit_result(inspect_deck_presentation(path), json_output=json_output)


@deck_app.command("validate")
def deck_validate(
    path: Annotated[Path, typer.Argument(help="PPTX artifact path to validate.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Validate a local PowerPoint deck for structure, safety, and placeholder leakage."""
    _emit_result(validate_deck_presentation(path), json_output=json_output)


@deck_app.command("create-from-outline")
def deck_create_from_outline(
    outline_path: Annotated[Path, typer.Argument(help="JSON deck outline path.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output PPTX deck path.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Create a local editable PPTX deck from a structured outline."""
    outline = json.loads(outline_path.read_text(encoding="utf-8"))
    _emit_result(
        create_deck_from_outline(outline if isinstance(outline, dict) else {}, output_path),
        json_output=json_output,
    )


@workflow_app.command("extract-to-sheet")
def workflow_extract_to_sheet(
    input_paths: Annotated[
        list[Path],
        typer.Argument(help="Input DOCX/XLSX sources to extract into an evidence workbook."),
    ],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output XLSX evidence workbook path.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Extract source tables into a source-mapped evidence workbook."""
    _emit_result(extract_to_sheet(input_paths, output_path), json_output=json_output)


@workflow_app.command("sheet-to-deck")
def workflow_sheet_to_deck(
    workbook_path: Annotated[Path, typer.Argument(help="Input XLSX workbook to profile and turn into a deck.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output PPTX deck path.")],
    title: Annotated[str | None, typer.Option("--title", help="Deck title. Defaults to the workbook stem.")] = None,
    max_rows_per_sheet: Annotated[int, typer.Option("--max-rows", help="Maximum non-empty rows read per sheet.")] = 100,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Turn an evidence workbook into an editable PowerPoint deck."""
    _emit_result(
        sheet_to_deck(
            workbook_path,
            output_path,
            title=title,
            max_rows_per_sheet=max_rows_per_sheet,
        ),
        json_output=json_output,
    )


@workflow_app.command("board-pack")
def workflow_board_pack(
    files: Annotated[
        list[Path],
        typer.Argument(help="Input Office artifacts to include in the board pack."),
    ],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output board pack ZIP path.")],
    title: Annotated[str | None, typer.Option("--title", help="Board pack title.")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Create a local board pack ZIP with artifacts, manifest, and validation report."""
    _emit_result(board_pack(files, output_path, title=title), json_output=json_output)


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


app.add_typer(tools_app, name="tools")
app.add_typer(word_app, name="word")
app.add_typer(sheet_app, name="sheet")
app.add_typer(deck_app, name="deck")
app.add_typer(workflow_app, name="workflow")


def _find_tool(name: str) -> dict[str, Any]:
    manifest = load_okoffice_manifest()
    for tool in [*manifest["target_tools"], *manifest["compatibility_tools"]]:
        if tool["name"] == name:
            return dict(tool)
    raise typer.BadParameter(f"Unknown okoffice tool: {name}")


def _emit_result(result: object, json_output: bool) -> None:
    if json_output:
        typer.echo(result.model_dump_json())
    else:
        typer.echo(result.model_dump_json(indent=2))
    if result.status == "failed":
        raise typer.Exit(1)
