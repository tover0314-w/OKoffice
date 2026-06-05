from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any

import typer

from agentpdf.office.bundle import export_office_bundle, verify_office_bundle
from agentpdf.office.context import build_office_context_packet
from agentpdf.office.deck import inspect_deck_presentation
from agentpdf.office.deck_validation import validate_deck_contact_sheet, validate_deck_presentation
from agentpdf.office.deck_writer import create_deck_presentation
from agentpdf.office.extract import extract_schema_from_context
from agentpdf.office.inspect import inspect_office_file
from agentpdf.office.planner import plan_office_workflow
from agentpdf.office.sheet import inspect_sheet_workbook
from agentpdf.office.validation import validate_office_package, validate_sheet_formulas
from agentpdf.office.word import inspect_word_document
from agentpdf.office.word_validation import validate_word_document
from agentpdf.office.word_report import create_word_report
from agentpdf.office.workbook import write_sheet_workbook
from agentpdf.office.workflows import board_pack, docset_to_sheet, sheet_to_deck
from agentpdf.schemas.models import ToolResult
from agentpdf.tools.runner import (
    run_agent_setup_claude_code,
    run_agent_setup_codex,
    run_agent_setup_kilo_code,
    run_agent_setup_openclaw,
    run_office_workers_status,
)
from okoffice import __version__
from okoffice.tools.registry import load_okoffice_manifest


app = typer.Typer(help="okoffice local-first agent-native Office CLI")
agent_app = typer.Typer(help="Generate local agent runtime configs.")
agent_setup_app = typer.Typer(help="Set up specific agent runtimes.")
tools_app = typer.Typer(help="Discover target okoffice tools and legacy compatibility tools.")
context_app = typer.Typer(help="Build reusable cross-format Office context packets.")
extract_app = typer.Typer(help="Extract cited structured evidence from Office context packets.")
word_app = typer.Typer(help="Inspect and transform Word documents.")
sheet_app = typer.Typer(help="Inspect and transform Excel workbooks.")
deck_app = typer.Typer(help="Inspect and transform PowerPoint presentations.")
workflow_app = typer.Typer(help="Run cross-format okoffice workflows.")
validation_app = typer.Typer(help="Run local Office artifact validation checks.")
workers_app = typer.Typer(help="Inspect optional okoffice worker contracts.")
bundle_app = typer.Typer(help="Export and verify portable okoffice artifact bundles.")
app.add_typer(agent_app, name="agent")
agent_app.add_typer(agent_setup_app, name="setup")
app.add_typer(tools_app, name="tools")
app.add_typer(context_app, name="context")
app.add_typer(extract_app, name="extract")
app.add_typer(word_app, name="word")
app.add_typer(sheet_app, name="sheet")
app.add_typer(deck_app, name="deck")
app.add_typer(workflow_app, name="workflow")
app.add_typer(validation_app, name="validation")
app.add_typer(workers_app, name="workers")
app.add_typer(bundle_app, name="bundle")


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
    """Serve local okoffice MCP or REST interfaces."""
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


@agent_setup_app.command("claude-code")
def agent_setup_claude_code(
    output_path: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Optional .mcp.json output path."),
    ] = None,
    safe_root: Annotated[
        str,
        typer.Option("--safe-root", help="Claude Code project safe root."),
    ] = "${CLAUDE_PROJECT_DIR:-.}",
    command: Annotated[
        str,
        typer.Option("--command", help="Executable used by Claude Code to start okoffice."),
    ] = "okoffice",
    args_prefix: Annotated[
        list[str] | None,
        typer.Option("--arg-prefix", help="Extra args before 'serve', e.g. -m okoffice.cli."),
    ] = None,
    server_name: Annotated[
        str,
        typer.Option("--server-name", help="MCP server name in Claude Code config."),
    ] = "okoffice",
    scope: Annotated[
        str,
        typer.Option("--scope", help="Claude Code MCP scope: project, local, or user."),
    ] = "project",
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Generate a Claude Code MCP config for local okoffice tools."""
    _emit_result(
        run_agent_setup_claude_code(
            output_path=output_path,
            safe_root=safe_root,
            command=command,
            args_prefix=args_prefix,
            server_name=server_name,
            scope=scope,
        ),
        json_output=json_output,
    )


@agent_setup_app.command("codex")
def agent_setup_codex(
    output_path: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Optional Codex MCP config output path."),
    ] = None,
    safe_root: Annotated[
        str,
        typer.Option("--safe-root", help="Codex workspace safe root."),
    ] = ".",
    command: Annotated[
        str,
        typer.Option("--command", help="Executable used by Codex to start okoffice."),
    ] = "okoffice",
    args_prefix: Annotated[
        list[str] | None,
        typer.Option("--arg-prefix", help="Extra args before 'serve', e.g. -m okoffice.cli."),
    ] = None,
    server_name: Annotated[
        str,
        typer.Option("--server-name", help="MCP server name in Codex config."),
    ] = "okoffice",
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Generate a Codex MCP config for local okoffice tools."""
    _emit_result(
        run_agent_setup_codex(
            output_path=output_path,
            safe_root=safe_root,
            command=command,
            args_prefix=args_prefix,
            server_name=server_name,
        ),
        json_output=json_output,
    )


@agent_setup_app.command("kilo-code")
def agent_setup_kilo_code(
    output_path: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Optional Kilo Code MCP config output path."),
    ] = None,
    safe_root: Annotated[
        str,
        typer.Option("--safe-root", help="Kilo Code project safe root."),
    ] = ".",
    command: Annotated[
        str,
        typer.Option("--command", help="Executable used by Kilo Code to start okoffice."),
    ] = "okoffice",
    args_prefix: Annotated[
        list[str] | None,
        typer.Option("--arg-prefix", help="Extra args before 'serve', e.g. -m okoffice.cli."),
    ] = None,
    server_name: Annotated[
        str,
        typer.Option("--server-name", help="MCP server name in Kilo Code config."),
    ] = "okoffice",
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Generate a Kilo Code MCP config for local okoffice tools."""
    _emit_result(
        run_agent_setup_kilo_code(
            output_path=output_path,
            safe_root=safe_root,
            command=command,
            args_prefix=args_prefix,
            server_name=server_name,
        ),
        json_output=json_output,
    )


@agent_setup_app.command("openclaw")
def agent_setup_openclaw(
    output_path: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Optional OpenClaw MCP config output path."),
    ] = None,
    safe_root: Annotated[
        str,
        typer.Option("--safe-root", help="OpenClaw project safe root."),
    ] = ".",
    command: Annotated[
        str,
        typer.Option("--command", help="Executable used by OpenClaw to start okoffice."),
    ] = "okoffice",
    args_prefix: Annotated[
        list[str] | None,
        typer.Option("--arg-prefix", help="Extra args before 'serve', e.g. -m okoffice.cli."),
    ] = None,
    server_name: Annotated[
        str,
        typer.Option("--server-name", help="MCP server name in OpenClaw config."),
    ] = "okoffice",
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Generate an OpenClaw MCP config for local okoffice tools."""
    _emit_result(
        run_agent_setup_openclaw(
            output_path=output_path,
            safe_root=safe_root,
            command=command,
            args_prefix=args_prefix,
            server_name=server_name,
        ),
        json_output=json_output,
    )


@context_app.command("build")
def context_build(
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output context packet JSON path.")],
    files: Annotated[
        list[Path] | None,
        typer.Option("--file", help="Local Word, Excel, PowerPoint, PDF, text, or data source. Can be repeated."),
    ] = None,
    title: Annotated[str | None, typer.Option("--title", help="Context packet title.")] = None,
    intent: Annotated[str | None, typer.Option("--intent", help="User or agent intent for the packet.")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Build an OKoffice context packet with source graph metadata."""
    result = build_office_context_packet(
        files=files or [],
        output_path=output_path,
        title=title,
        intent=intent,
    )
    if json_output:
        typer.echo(result.model_dump_json())
    else:
        typer.echo(result.model_dump_json(indent=2))
    if result.status == "failed":
        raise typer.Exit(1)


@extract_app.command("schema")
def extract_schema(
    context_packet_path: Annotated[Path, typer.Argument(help="OKoffice context packet JSON path.")],
    schema_path: Annotated[Path, typer.Option("--schema", help="Schema JSON path.")],
    output_path: Annotated[Path | None, typer.Option("--output", "-o", help="Output evidence JSON path.")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Extract schema-shaped rows with source refs."""
    schema = _read_json_object(schema_path)
    result = extract_schema_from_context(
        context_packet_path=context_packet_path,
        schema=schema,
        output_path=output_path,
    )
    if json_output:
        typer.echo(result.model_dump_json())
    else:
        typer.echo(result.model_dump_json(indent=2))
    if result.status == "failed":
        raise typer.Exit(1)


@word_app.command("inspect")
def word_inspect(
    path: Annotated[Path, typer.Argument(help="DOCX/DOCM path to inspect.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Inspect a Word document without mutating it."""
    result = inspect_word_document(path)
    if json_output:
        typer.echo(result.model_dump_json())
    else:
        typer.echo(result.model_dump_json(indent=2))
    if result.status == "failed":
        raise typer.Exit(1)


@word_app.command("create-report")
def word_create_report(
    workbook_path: Annotated[Path, typer.Option("--from-workbook", help="Evidence workbook XLSX path.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output DOCX report path.")],
    title: Annotated[str | None, typer.Option("--title", help="Report title.")] = None,
    profile: Annotated[str, typer.Option("--profile", help="Report profile or style key.")] = "executive_memo",
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Create an editable Word report from an evidence workbook."""
    result = create_word_report(
        workbook_path=workbook_path,
        output_path=output_path,
        title=title,
        profile=profile,
    )
    if json_output:
        typer.echo(result.model_dump_json())
    else:
        typer.echo(result.model_dump_json(indent=2))
    if result.status == "failed":
        raise typer.Exit(1)


@word_app.command("validate-document")
def word_validate_document(
    path: Annotated[Path, typer.Argument(help="DOCX/DOCM path to validate structurally.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Validate a Word document with local structural QA checks."""
    result = validate_word_document(path)
    if json_output:
        typer.echo(result.model_dump_json())
    else:
        typer.echo(result.model_dump_json(indent=2))
    if result.status == "failed":
        raise typer.Exit(1)


@sheet_app.command("inspect")
def sheet_inspect(
    path: Annotated[Path, typer.Argument(help="XLSX/XLSM path to inspect.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Inspect an Excel workbook without mutating it."""
    result = inspect_sheet_workbook(path)
    if json_output:
        typer.echo(result.model_dump_json())
    else:
        typer.echo(result.model_dump_json(indent=2))
    if result.status == "failed":
        raise typer.Exit(1)


@sheet_app.command("write-workbook")
def sheet_write_workbook(
    evidence_path: Annotated[Path, typer.Argument(help="Evidence JSON path from office.extract.schema.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output XLSX evidence workbook path.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Write an evidence XLSX workbook without mutating source files."""
    result = write_sheet_workbook(evidence_path=evidence_path, output_path=output_path)
    if json_output:
        typer.echo(result.model_dump_json())
    else:
        typer.echo(result.model_dump_json(indent=2))
    if result.status == "failed":
        raise typer.Exit(1)


@sheet_app.command("validate-formulas")
def sheet_validate_formulas(
    path: Annotated[Path, typer.Argument(help="XLSX/XLSM path to validate structurally.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Validate workbook formulas with local structural checks."""
    result = validate_sheet_formulas(path)
    if json_output:
        typer.echo(result.model_dump_json())
    else:
        typer.echo(result.model_dump_json(indent=2))
    if result.status == "failed":
        raise typer.Exit(1)


@deck_app.command("inspect")
def deck_inspect(
    path: Annotated[Path, typer.Argument(help="PPTX/PPTM path to inspect.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Inspect a PowerPoint presentation without mutating it."""
    result = inspect_deck_presentation(path)
    if json_output:
        typer.echo(result.model_dump_json())
    else:
        typer.echo(result.model_dump_json(indent=2))
    if result.status == "failed":
        raise typer.Exit(1)


@deck_app.command("create")
def deck_create(
    workbook_path: Annotated[Path, typer.Option("--from-workbook", help="Evidence workbook XLSX path.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output PPTX presentation path.")],
    title: Annotated[str | None, typer.Option("--title", help="Presentation title.")] = None,
    profile: Annotated[str, typer.Option("--profile", help="Presentation profile or style pack key.")] = "board_review",
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Create an editable PowerPoint presentation from an evidence workbook."""
    result = create_deck_presentation(
        workbook_path=workbook_path,
        output_path=output_path,
        title=title,
        profile=profile,
    )
    if json_output:
        typer.echo(result.model_dump_json())
    else:
        typer.echo(result.model_dump_json(indent=2))
    if result.status == "failed":
        raise typer.Exit(1)


@deck_app.command("validate-contact-sheet")
def deck_validate_contact_sheet(
    path: Annotated[Path, typer.Argument(help="PPTX/PPTM path to validate for contact-sheet preview readiness.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Validate contact-sheet preview availability for a presentation."""
    result = validate_deck_contact_sheet(path)
    if json_output:
        typer.echo(result.model_dump_json())
    else:
        typer.echo(result.model_dump_json(indent=2))
    if result.status == "failed":
        raise typer.Exit(1)


@deck_app.command("validate-presentation")
def deck_validate_presentation(
    path: Annotated[Path, typer.Argument(help="PPTX/PPTM path to validate structurally.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Validate a presentation with local structural deck QA checks."""
    result = validate_deck_presentation(path)
    if json_output:
        typer.echo(result.model_dump_json())
    else:
        typer.echo(result.model_dump_json(indent=2))
    if result.status == "failed":
        raise typer.Exit(1)


@validation_app.command("package")
def validation_package(
    path: Annotated[Path, typer.Argument(help="Office artifact package path.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Validate Office/PDF package structure and safety markers."""
    result = validate_office_package(path)
    if json_output:
        typer.echo(result.model_dump_json())
    else:
        typer.echo(result.model_dump_json(indent=2))
    if result.status == "failed":
        raise typer.Exit(1)


@workflow_app.command("docset-to-sheet")
def workflow_docset_to_sheet(
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output evidence workbook XLSX path.")],
    schema_path: Annotated[Path, typer.Option("--schema", help="Schema JSON path.")],
    files: Annotated[
        list[Path] | None,
        typer.Option("--file", help="Local Word, PDF, Excel, PowerPoint, text, or data source. Can be repeated."),
    ] = None,
    title: Annotated[str | None, typer.Option("--title", help="Context packet title.")] = None,
    intent: Annotated[str | None, typer.Option("--intent", help="User or agent intent for the workflow.")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Build an evidence workbook from a source document set."""
    schema = _read_json_object(schema_path)
    result = docset_to_sheet(
        files=files or [],
        schema=schema,
        output_path=output_path,
        title=title,
        intent=intent,
    )
    if json_output:
        typer.echo(result.model_dump_json())
    else:
        typer.echo(result.model_dump_json(indent=2))
    if result.status == "failed":
        raise typer.Exit(1)


@workflow_app.command("sheet-to-deck")
def workflow_sheet_to_deck(
    workbook_path: Annotated[Path, typer.Option("--workbook", help="Evidence workbook XLSX path.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output PPTX presentation path.")],
    title: Annotated[str | None, typer.Option("--title", help="Presentation title.")] = None,
    profile: Annotated[str, typer.Option("--profile", help="Presentation profile or style pack key.")] = "board_review",
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Create a validated presentation from an evidence workbook."""
    result = sheet_to_deck(
        workbook_path=workbook_path,
        output_path=output_path,
        title=title,
        profile=profile,
    )
    if json_output:
        typer.echo(result.model_dump_json())
    else:
        typer.echo(result.model_dump_json(indent=2))
    if result.status == "failed":
        raise typer.Exit(1)


@workflow_app.command("board-pack")
def workflow_board_pack(
    out_dir: Annotated[Path, typer.Option("--out-dir", help="Output directory for board-pack artifacts.")],
    schema_path: Annotated[Path, typer.Option("--schema", help="Schema JSON path.")],
    files: Annotated[
        list[Path] | None,
        typer.Option("--file", help="Local Word, PDF, Excel, PowerPoint, text, or data source. Can be repeated."),
    ] = None,
    title: Annotated[str | None, typer.Option("--title", help="Board-pack title.")] = None,
    profile: Annotated[str, typer.Option("--profile", help="Deck/report profile key.")] = "board_review",
    intent: Annotated[str | None, typer.Option("--intent", help="User or agent intent for the workflow.")] = None,
    include_pdf_handout: Annotated[
        bool,
        typer.Option("--include-pdf-handout", help="Generate a local HTML-first PDF handout and include it in the bundle."),
    ] = False,
    pdf_renderer_backend: Annotated[
        str,
        typer.Option("--pdf-renderer-backend", help="Renderer backend for the optional PDF handout."),
    ] = "auto",
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Create a workbook, memo, deck, optional PDF handout, and verified okoffice bundle."""
    schema = _read_json_object(schema_path)
    result = board_pack(
        files=files or [],
        schema=schema,
        out_dir=out_dir,
        title=title,
        profile=profile,
        intent=intent,
        include_pdf_handout=include_pdf_handout,
        pdf_renderer_backend=pdf_renderer_backend,
    )
    if json_output:
        typer.echo(result.model_dump_json())
    else:
        typer.echo(result.model_dump_json(indent=2))
    if result.status == "failed":
        raise typer.Exit(1)


@workers_app.command("status")
def workers_status(
    enabled_workers: Annotated[
        list[str] | None,
        typer.Option("--enable", help="Worker id to enable for availability probing. Can be repeated."),
    ] = None,
    commands: Annotated[
        list[str] | None,
        typer.Option("--command", help="Worker command override as worker_id=command. Can be repeated."),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Report optional okoffice worker contracts and availability."""
    result = run_office_workers_status(
        feature_flags={worker_id: True for worker_id in (enabled_workers or [])},
        command_paths=_worker_command_dict(commands or []),
    )
    if json_output:
        typer.echo(result.model_dump_json())
    else:
        typer.echo(result.model_dump_json(indent=2))
    if result.status == "failed":
        raise typer.Exit(1)


@bundle_app.command("export")
def bundle_export(
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output .okoffice.zip bundle path.")],
    files: Annotated[
        list[Path] | None,
        typer.Option("--file", help="Artifact file to include. Can be repeated."),
    ] = None,
    title: Annotated[str | None, typer.Option("--title", help="Human-readable bundle title.")] = None,
    metadata: Annotated[
        list[str] | None,
        typer.Option("--metadata", help="Bundle metadata key=value. Can be repeated."),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Export local artifacts into a portable okoffice audit bundle."""
    result = export_office_bundle(
        artifact_paths=files or [],
        output_path=output_path,
        title=title,
        metadata=_metadata_dict(metadata or []),
    )
    if json_output:
        typer.echo(result.model_dump_json())
    else:
        typer.echo(result.model_dump_json(indent=2))
    if result.status == "failed":
        raise typer.Exit(1)


@bundle_app.command("verify")
def bundle_verify(
    bundle_path: Annotated[Path, typer.Argument(help="Input .okoffice.zip bundle path.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Verify an okoffice audit bundle manifest and checksums."""
    result = verify_office_bundle(bundle_path)
    if json_output:
        typer.echo(result.model_dump_json())
    else:
        typer.echo(result.model_dump_json(indent=2))
    if result.status == "failed":
        raise typer.Exit(1)


def _emit_result(result: ToolResult, json_output: bool) -> None:
    if json_output:
        typer.echo(result.model_dump_json())
    else:
        typer.echo(result.model_dump_json(indent=2))
    if result.status == "failed":
        raise typer.Exit(1)


def _find_tool(name: str) -> dict[str, Any]:
    manifest = load_okoffice_manifest()
    for tool in [*manifest["target_tools"], *manifest["compatibility_tools"]]:
        if tool["name"] == name:
            return dict(tool)
    raise typer.BadParameter(f"Unknown okoffice tool: {name}")


def _read_json_object(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise typer.BadParameter(f"JSON file must contain an object: {path}")
    return data


def _metadata_dict(items: list[str]) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for item in items:
        if "=" not in item:
            raise typer.BadParameter(f"Metadata must use key=value format: {item}")
        key, value = item.split("=", maxsplit=1)
        parsed[key.strip()] = value.strip()
    return parsed


def _worker_command_dict(items: list[str]) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for item in items:
        if "=" not in item:
            raise typer.BadParameter(f"Worker command must use worker_id=command format: {item}")
        key, value = item.split("=", maxsplit=1)
        parsed[key.strip()] = value.strip()
    return parsed
