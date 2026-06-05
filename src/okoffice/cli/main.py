from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any

import typer

from agentpdf.tools.runner import run_agent_setup_codex
from agentpdf.office.bundle import export_office_bundle, verify_office_bundle
from agentpdf.office.context import build_office_context_packet
from agentpdf.office.deck import (
    create_deck_from_outline,
    create_deck_presentation as create_deck_presentation_from_outline,
    export_deck_pptx,
    inspect_deck_presentation,
    render_deck_html,
    validate_deck_html_preview,
    validate_deck_presentation,
)
from agentpdf.office.deck_plan import compose_deck_plan
from agentpdf.office.deck_patch import apply_deck_patch
from agentpdf.office.deck_validation import (
    validate_deck_contact_sheet,
    validate_deck_presentation as validate_deck_quality_presentation,
)
from agentpdf.office.deck_writer import create_deck_presentation as create_deck_presentation_from_workbook
from agentpdf.office.extract import extract_schema
from agentpdf.office.inspect import inspect_office_file
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
from okoffice import __version__
from okoffice.tools.registry import load_okoffice_manifest


app = typer.Typer(help="okoffice local-first agent-native Office CLI")
agent_app = typer.Typer(help="Generate local agent integration config.")
agent_setup_app = typer.Typer(help="Generate MCP setup config for local agents.")
tools_app = typer.Typer(help="Discover target okoffice tools and legacy compatibility tools.")
word_app = typer.Typer(help="Inspect and transform Word documents.")
sheet_app = typer.Typer(help="Inspect and transform Excel workbooks.")
deck_app = typer.Typer(help="Inspect and transform PowerPoint decks.")
context_app = typer.Typer(help="Build local OKoffice context packets and source graphs.")
extract_app = typer.Typer(help="Extract structured evidence from OKoffice context.")
validate_app = typer.Typer(help="Validate Office artifacts and packages.")
workflow_app = typer.Typer(help="Run local cross-format OKoffice workflows.")
bundle_app = typer.Typer(help="Verify and export portable OKoffice artifact bundles.")
workers_app = typer.Typer(help="Inspect optional local Office worker contracts and feature flags.")


@app.callback()
def main() -> None:
    """Agent-native Office infrastructure for local Word, Excel, PowerPoint, PDF, and bundle workflows."""


@app.command()
def version() -> None:
    """Print the okoffice version."""
    typer.echo(f"okoffice {__version__}")


@app.command()
def serve(
    mcp: Annotated[bool, typer.Option("--mcp", help="Run the local MCP server.")] = False,
    api: Annotated[bool, typer.Option("--api", help="Run the local REST API.")] = False,
    host: Annotated[str, typer.Option("--host", help="REST API bind host.")] = "127.0.0.1",
    port: Annotated[int, typer.Option("--port", help="REST API bind port.")] = 7331,
    transport: Annotated[
        str,
        typer.Option("--transport", help="MCP transport: stdio, sse, or streamable-http."),
    ] = "stdio",
    safe_root: Annotated[
        Path | None,
        typer.Option("--safe-root", help="Reserved local safe root for agent configs."),
    ] = None,
) -> None:
    """Serve local okoffice interfaces."""
    if mcp:
        from agentpdf.mcp.server import run_mcp_server

        run_mcp_server(transport=transport)  # type: ignore[arg-type]
        return
    if api:
        import uvicorn

        uvicorn.run("agentpdf.api.app:create_app", factory=True, host=host, port=port)
        return
    typer.echo("Choose --mcp for the local MCP server or --api for the local REST server.")
    raise typer.Exit(1)


@agent_setup_app.command("codex")
def agent_setup_codex(
    output_path: Annotated[Path | None, typer.Option("--output", "-o", help="Output Codex MCP JSON path.")] = None,
    safe_root: Annotated[str, typer.Option("--safe-root", help="Safe root passed to okoffice serve.")] = ".",
    command: Annotated[str, typer.Option("--command", help="Command used by Codex to start okoffice.")] = "okoffice",
    server_name: Annotated[str, typer.Option("--server-name", help="MCP server name.")] = "okoffice",
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Generate a Codex MCP config for local okoffice tools."""
    _emit_result(
        run_agent_setup_codex(
            output_path=output_path,
            safe_root=safe_root,
            command=command,
            server_name=server_name,
        ),
        json_output=json_output,
    )


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


@word_app.command("validate-document")
def word_validate_document_command(
    path: Annotated[Path, typer.Argument(help="DOCX artifact path to validate.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Validate a Word document for structure, safety, comments, and render-preview readiness."""
    _emit_result(validate_word_document(path), json_output=json_output)


@word_app.command("create-report")
def word_create_report_command(
    workbook_path: Annotated[Path, typer.Option("--from-workbook", help="Evidence workbook path.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output DOCX report path.")],
    title: Annotated[str | None, typer.Option("--title", help="Report title.")] = None,
    profile: Annotated[str, typer.Option("--profile", help="Report profile.")] = "executive_memo",
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Create an editable Word report from an evidence workbook."""
    _emit_result(
        create_word_report(workbook_path=workbook_path, output_path=output_path, title=title, profile=profile),
        json_output=json_output,
    )


@word_app.command("patch-plan")
def word_patch_plan_command(
    input_path: Annotated[Path, typer.Argument(help="Input DOCX artifact path.")],
    operations_path: Annotated[Path, typer.Option("--operations", help="JSON patch operations path.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Preview a non-mutating Word patch transaction."""
    operations = json.loads(operations_path.read_text(encoding="utf-8"))
    _emit_result(plan_word_patch(input_path=input_path, operations=_operations(operations)), json_output=json_output)


@word_app.command("patch-apply")
def word_patch_apply_command(
    input_path: Annotated[Path, typer.Argument(help="Input DOCX artifact path.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output DOCX artifact path.")],
    operations_path: Annotated[Path, typer.Option("--operations", help="JSON patch operations path.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Apply a non-mutating Word patch transaction into a new DOCX output."""
    operations = json.loads(operations_path.read_text(encoding="utf-8"))
    _emit_result(
        apply_word_patch(input_path=input_path, output_path=output_path, operations=_operations(operations)),
        json_output=json_output,
    )


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


@sheet_app.command("create-evidence-workbook")
def sheet_create_evidence_workbook(
    data_path: Annotated[Path, typer.Argument(help="JSON records or ToolResult path to write as an evidence XLSX.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output evidence XLSX workbook path.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Create an auditable XLSX evidence workbook from structured records with source refs."""
    payload = json.loads(data_path.read_text(encoding="utf-8"))
    _emit_result(create_evidence_workbook(payload, output_path), json_output=json_output)


@sheet_app.command("validate")
def sheet_validate(
    path: Annotated[Path, typer.Argument(help="XLSX artifact path to validate.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Validate workbook structure, safety markers, and source-map readiness."""
    _emit_result(validate_sheet_workbook(path), json_output=json_output)


@sheet_app.command("validate-formulas")
def sheet_validate_formulas(
    path: Annotated[Path, typer.Argument(help="XLSX artifact path to validate formulas in.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Validate workbook formulas for cached errors, broken refs, external refs, and volatile functions."""
    _emit_result(validate_sheet_formulas(path), json_output=json_output)


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


@deck_app.command("validate-contact-sheet")
def deck_validate_contact_sheet_command(
    path: Annotated[Path, typer.Argument(help="PPTX artifact path to validate.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Validate contact-sheet preview readiness and render-worker status."""
    _emit_result(validate_deck_contact_sheet(path), json_output=json_output)


@deck_app.command("validate-presentation")
def deck_validate_presentation_command(
    path: Annotated[Path, typer.Argument(help="PPTX artifact path to validate.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Validate presentation structure, speaker notes, theme metadata, and render evidence state."""
    _emit_result(validate_deck_quality_presentation(path), json_output=json_output)


@deck_app.command("create")
def deck_create_command(
    workbook_path: Annotated[Path, typer.Option("--from-workbook", help="Evidence workbook path.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output PPTX deck path.")],
    title: Annotated[str | None, typer.Option("--title", help="Deck title.")] = None,
    profile: Annotated[str, typer.Option("--profile", help="Deck profile.")] = "board_review",
    style_path: Annotated[Path | None, typer.Option("--style", help="Optional JSON style override path.")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Create an editable PowerPoint deck from an evidence workbook."""
    style = json.loads(style_path.read_text(encoding="utf-8")) if style_path else None
    _emit_result(
        create_deck_presentation_from_workbook(
            workbook_path=workbook_path,
            output_path=output_path,
            title=title,
            profile=profile,
            style=style if isinstance(style, dict) else None,
        ),
        json_output=json_output,
    )


@deck_app.command("patch-apply")
def deck_patch_apply_command(
    input_path: Annotated[Path, typer.Argument(help="Input PPTX artifact path.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output PPTX artifact path.")],
    operations_path: Annotated[Path, typer.Option("--operations", help="JSON patch operations path.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Apply a non-mutating PowerPoint patch transaction into a new PPTX output."""
    operations = json.loads(operations_path.read_text(encoding="utf-8"))
    _emit_result(
        apply_deck_patch(input_path=input_path, output_path=output_path, operations=_operations(operations)),
        json_output=json_output,
    )


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


@deck_app.command("create-presentation")
def deck_create_presentation(
    outline_path: Annotated[Path, typer.Argument(help="JSON deck outline or composition plan path.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output PPTX deck path.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Create a local editable PPTX deck from an outline or composition plan."""
    outline_or_plan = json.loads(outline_path.read_text(encoding="utf-8"))
    _emit_result(
        create_deck_presentation_from_outline(outline_or_plan if isinstance(outline_or_plan, dict) else {}, output_path),
        json_output=json_output,
    )


@deck_app.command("render-html")
def deck_render_html(
    plan_path: Annotated[Path, typer.Argument(help="JSON deck outline or composition plan path.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output HTML deck preview path.")],
    artifact_dir: Annotated[
        Path | None,
        typer.Option("--artifact-dir", help="Optional directory for the HTML package manifest."),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Render a source-mapped deck plan into an offline HTML preview package."""
    _emit_result(render_deck_html(plan_path, output_path, artifact_dir=artifact_dir), json_output=json_output)


@deck_app.command("validate-html")
@deck_app.command("validate-html-preview")
def deck_validate_html(
    path: Annotated[Path, typer.Argument(help="HTML deck preview path to validate.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Validate an offline HTML deck preview package before PPTX export."""
    _emit_result(validate_deck_html_preview(path), json_output=json_output)


@deck_app.command("export-pptx")
def deck_export_pptx(
    html_path: Annotated[Path, typer.Argument(help="HTML deck preview path to export.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output editable PPTX deck path.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Export a validated HTML deck package into an editable PPTX deck."""
    _emit_result(export_deck_pptx(html_path, output_path), json_output=json_output)


@deck_app.command("compose-plan")
def deck_compose_plan(
    workbook_path: Annotated[Path, typer.Argument(help="Input XLSX workbook to turn into a deck Composition IR.")],
    output_path: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Optional output JSON composition plan path."),
    ] = None,
    title: Annotated[str | None, typer.Option("--title", help="Deck title. Defaults to the workbook stem.")] = None,
    style: Annotated[str, typer.Option("--style", help="Deck style label for the Composition IR.")] = "executive",
    max_rows_per_sheet: Annotated[int, typer.Option("--max-rows", help="Maximum non-empty rows read per sheet.")] = 100,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Compose a source-mapped deck plan without writing a PPTX."""
    _emit_result(
        compose_deck_plan(
            workbook_path,
            output_path=output_path,
            title=title,
            style=style,
            max_rows_per_sheet=max_rows_per_sheet,
        ),
        json_output=json_output,
    )


@context_app.command("build")
def context_build(
    files: Annotated[
        list[Path] | None,
        typer.Option("--file", "-f", help="Input Office artifact path to include in the context packet."),
    ] = None,
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output context packet JSON path.")] = Path(
        ".okoffice-out/context.packet.json"
    ),
    title: Annotated[str | None, typer.Option("--title", help="Context packet title.")] = None,
    intent: Annotated[str | None, typer.Option("--intent", help="User or agent intent for this packet.")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Build a local context packet and source graph from Office-compatible files."""
    _emit_result(
        build_office_context_packet(files or [], output_path, title=title, intent=intent),
        json_output=json_output,
    )


@extract_app.command("schema")
def extract_schema_command(
    context_packet_path: Annotated[Path, typer.Argument(help="OKoffice context packet JSON path.")],
    schema_path: Annotated[Path, typer.Option("--schema", help="Schema JSON path.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output JSON evidence path.")] = Path(
        ".okoffice-out/evidence.json"
    ),
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Extract schema-shaped evidence from a context packet."""
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    _emit_result(extract_schema(context_packet_path, schema if isinstance(schema, dict) else {}, output_path), json_output=json_output)


@validate_app.command("package")
def validate_package(
    path: Annotated[Path, typer.Argument(help="Office artifact path to validate.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Validate Office package structure and safety markers."""
    _emit_result(validate_office_package(path), json_output=json_output)


@workflow_app.command("extract-to-sheet")
def workflow_extract_to_sheet(
    input_paths: Annotated[
        list[Path] | None,
        typer.Argument(help="Input DOCX/XLSX sources to extract into an evidence workbook."),
    ] = None,
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output XLSX evidence workbook path.")] = Path(
        ".okoffice-out/evidence.xlsx"
    ),
    context_packet_path: Annotated[
        Path | None,
        typer.Option("--context-packet", help="Context packet JSON to use as the source graph input."),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Extract source tables into a source-mapped evidence workbook."""
    _emit_result(
        extract_to_sheet(input_paths or [], output_path, context_packet_path=context_packet_path),
        json_output=json_output,
    )


@workflow_app.command("docset-to-sheet")
def workflow_docset_to_sheet(
    schema_path: Annotated[Path, typer.Option("--schema", help="Schema JSON path.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output XLSX evidence workbook path.")],
    files: Annotated[
        list[Path] | None,
        typer.Option("--file", "-f", help="Input Office artifact path to include in the context packet."),
    ] = None,
    title: Annotated[str | None, typer.Option("--title", help="Context/workbook title.")] = None,
    intent: Annotated[str | None, typer.Option("--intent", help="User or agent intent for this packet.")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Build a context packet, extract schema evidence, write a workbook, and validate formulas."""
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    _emit_result(
        docset_to_sheet(
            files=files or [],
            schema=schema if isinstance(schema, dict) else {},
            output_path=output_path,
            title=title,
            intent=intent,
        ),
        json_output=json_output,
    )


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


@bundle_app.command("verify")
def bundle_verify(
    bundle_path: Annotated[Path, typer.Argument(help="OKoffice board pack ZIP path to verify.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Verify a local board pack ZIP manifest, validation report, members, and checksums."""
    result = verify_office_bundle(bundle_path)
    if result.status == "failed":
        result = verify_board_pack(bundle_path)
    _emit_result(result, json_output=json_output)


@bundle_app.command("export")
def bundle_export(
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output OKoffice bundle ZIP path.")],
    files: Annotated[
        list[Path] | None,
        typer.Option("--file", "-f", help="Office artifact path to include in the bundle."),
    ] = None,
    title: Annotated[str | None, typer.Option("--title", help="Bundle title.")] = None,
    metadata_path: Annotated[Path | None, typer.Option("--metadata", help="Optional JSON metadata path.")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Export local Office artifacts into a portable OKoffice bundle."""
    metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path else None
    _emit_result(
        export_office_bundle(
            artifact_paths=files or [],
            output_path=output_path,
            title=title,
            metadata=metadata if isinstance(metadata, dict) else None,
        ),
        json_output=json_output,
    )


@workers_app.command("status")
def workers_status(
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Inspect optional Office worker contracts, flags, dependency status, and license boundaries."""
    _emit_result(inspect_office_workers(), json_output=json_output)


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


agent_app.add_typer(agent_setup_app, name="setup")
app.add_typer(agent_app, name="agent")
app.add_typer(tools_app, name="tools")
app.add_typer(word_app, name="word")
app.add_typer(sheet_app, name="sheet")
app.add_typer(deck_app, name="deck")
app.add_typer(context_app, name="context")
app.add_typer(extract_app, name="extract")
app.add_typer(validate_app, name="validate")
app.add_typer(workflow_app, name="workflow")
app.add_typer(bundle_app, name="bundle")
app.add_typer(workers_app, name="workers")


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


def _operations(payload: object) -> list[dict[str, Any]]:
    if isinstance(payload, list) and all(isinstance(item, dict) for item in payload):
        return payload
    raise typer.BadParameter("--operations must decode to a JSON array of objects.")
