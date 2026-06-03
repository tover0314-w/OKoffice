import json
from pathlib import Path
from typing import Annotated, Any

import typer

from agentpdf import __version__
from agentpdf.schemas.models import ToolResult
from agentpdf.tools.registry import get_tool, load_tool_manifest
from agentpdf.tools.runner import (
    run_agent_setup_claude_code,
    run_agent_setup_codex,
    run_artifacts_export_bundle,
    run_artifacts_verify_bundle,
    run_blank_page_check,
    run_build_context_packet,
    run_compose_add_appendix,
    run_compose_add_citation,
    run_compose_add_code_block,
    run_compose_add_figure,
    run_compose_add_media_reference,
    run_compose_add_slide,
    run_compose_add_table,
    run_compose_from_context,
    run_compose_plan,
    run_compose_render_ir,
    run_compress,
    run_create_markdown,
    run_create_text,
    run_create_agent,
    run_create_from_prompt,
    run_create_from_template_pack,
    run_plan_template_pack_creation,
    run_create_template_preview,
    run_create_template_packs,
    run_create_templates,
    run_context_packet_report,
    run_context_classify,
    run_context_code_snapshot,
    run_context_data_profile,
    run_context_ingest,
    run_context_packet,
    run_validate_template_pack,
    run_evidence_coverage_report,
    run_evidence_map_sources,
    run_extract_images,
    run_extract_pages,
    run_extract_text,
    run_image_to_pdf,
    run_inspect,
    run_inspect_pages,
    run_insert_blank_pages,
    run_metadata_read,
    run_metadata_page_info,
    run_metadata_remove,
    run_metadata_update,
    run_merge,
    run_page_numbers,
    run_patch_apply,
    run_patch_plan,
    run_patch_preview,
    run_patch_verify,
    run_parse_lite,
    run_pdf_to_markdown,
    run_pdf_to_json,
    run_rag_chat,
    run_rag_cite_answer,
    run_rag_export_report,
    run_rag_highlight_sources,
    run_rag_ingest,
    run_rag_query,
    run_rag_search,
    run_remove_pages,
    run_render,
    run_render_check,
    run_repair,
    run_reorder_pages,
    run_rotate_pages,
    run_page_count_check,
    run_security_remove_metadata,
    run_split,
    run_target_profiles,
    run_validate_output,
    run_validate_target_profile,
    run_watermark,
    run_workflow_plan,
    run_workflow_report,
    run_workflow_run,
)

app = typer.Typer(help="AgentPDF Infra CLI")
agent_app = typer.Typer(help="Generate local agent runtime configs.")
agent_setup_app = typer.Typer(help="Set up specific agent runtimes.")
tools_app = typer.Typer(help="Discover AgentPDF tools.")
metadata_app = typer.Typer(help="Read and write PDF metadata.")
security_app = typer.Typer(help="Run local PDF security and privacy tools.")
create_app = typer.Typer(help="Create PDFs from local inputs.")
context_app = typer.Typer(help="Build agent context packets.")
compose_app = typer.Typer(help="Compose target PDFs from context packets.")
target_app = typer.Typer(help="List and validate target PDF profiles.")
evidence_app = typer.Typer(help="Audit source evidence and coverage.")
patch_app = typer.Typer(help="Plan, preview, apply, and verify PDF patch transactions.")
artifacts_app = typer.Typer(help="Export and inspect local artifact lineage.")
rag_app = typer.Typer(help="Local document retrieval tools.")
workflow_app = typer.Typer(help="Plan local agent PDF workflows.")
app.add_typer(agent_app, name="agent")
agent_app.add_typer(agent_setup_app, name="setup")
app.add_typer(tools_app, name="tools")
app.add_typer(metadata_app, name="metadata")
app.add_typer(security_app, name="security")
app.add_typer(create_app, name="create")
app.add_typer(context_app, name="context")
app.add_typer(compose_app, name="compose")
app.add_typer(target_app, name="target")
app.add_typer(evidence_app, name="evidence")
app.add_typer(patch_app, name="patch")
app.add_typer(artifacts_app, name="artifacts")
app.add_typer(rag_app, name="rag")
app.add_typer(workflow_app, name="workflow")


@app.callback()
def main() -> None:
    """Open-source PDF infrastructure for AI agents."""


@app.command()
def version() -> None:
    """Print the AgentPDF version."""
    typer.echo(f"agentpdf {__version__}")


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
        typer.Option("--command", help="Executable used by Claude Code to start okpdf."),
    ] = "okpdf",
    args_prefix: Annotated[
        list[str] | None,
        typer.Option("--arg-prefix", help="Extra args before 'serve', e.g. -m agentpdf.cli."),
    ] = None,
    server_name: Annotated[
        str,
        typer.Option("--server-name", help="MCP server name in Claude Code config."),
    ] = "agentpdf",
    scope: Annotated[
        str,
        typer.Option("--scope", help="Claude Code MCP scope: project, local, or user."),
    ] = "project",
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Generate a Claude Code MCP config for local okpdf tools."""
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
        typer.Option("--command", help="Executable used by Codex to start okpdf."),
    ] = "okpdf",
    args_prefix: Annotated[
        list[str] | None,
        typer.Option("--arg-prefix", help="Extra args before 'serve', e.g. -m agentpdf.cli."),
    ] = None,
    server_name: Annotated[
        str,
        typer.Option("--server-name", help="MCP server name in Codex config."),
    ] = "agentpdf",
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Generate a Codex MCP config for local okpdf tools."""
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


@tools_app.command("list")
def tools_list(
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """List the public AgentPDF tool manifest."""
    manifest = load_tool_manifest()
    if json_output:
        typer.echo(manifest.model_dump_json())
        return
    for tool in manifest.tools:
        marker = "implemented" if tool.implemented else tool.status
        typer.echo(f"{tool.name}\t{marker}\t{tool.description}")


@tools_app.command("show")
def tools_show(
    name: Annotated[str, typer.Argument(help="Tool name, such as pdf.inspect.document.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Show one tool specification."""
    tool = get_tool(name)
    if json_output:
        typer.echo(tool.model_dump_json())
        return
    typer.echo(f"{tool.name}\nstatus: {tool.status}\nimplemented: {tool.implemented}")


@app.command()
def inspect(
    path: Annotated[Path, typer.Argument(help="PDF file to inspect.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Inspect a PDF document."""
    _emit_result(run_inspect(path), json_output=json_output)


@app.command("inspect-pages")
def inspect_pages(
    input_path: Annotated[Path, typer.Argument(help="PDF file to inspect page by page.")],
    pages: Annotated[str, typer.Option("--pages", help="Page range such as all or 1-3.")] = "all",
    render_check: Annotated[bool, typer.Option("--render-check", help="Render selected pages in memory.")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Inspect page-level text, image, geometry, and optional render facts."""
    _emit_result(
        run_inspect_pages(input_path, pages=pages, render_check=render_check),
        json_output=json_output,
    )


@app.command()
def merge(
    input_paths: Annotated[list[Path], typer.Argument(help="Input PDF files.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output PDF path.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Merge multiple PDFs."""
    _emit_result(run_merge(input_paths, output_path), json_output=json_output)


@app.command()
def split(
    input_path: Annotated[Path, typer.Argument(help="Input PDF file.")],
    pages: Annotated[str, typer.Option("--pages", help="Page range such as 1-3,7.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output PDF path.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Extract selected pages into a new PDF."""
    _emit_result(run_split(input_path, pages=pages, output_path=output_path), json_output=json_output)


@app.command("extract-pages")
def extract_pages(
    input_path: Annotated[Path, typer.Argument(help="Input PDF file.")],
    pages: Annotated[str, typer.Option("--pages", help="Page range such as 1-3,7.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output PDF path.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Extract selected pages into a new PDF."""
    _emit_result(
        run_extract_pages(input_path, pages=pages, output_path=output_path),
        json_output=json_output,
    )


@app.command("remove-pages")
def remove_pages(
    input_path: Annotated[Path, typer.Argument(help="Input PDF file.")],
    pages: Annotated[str, typer.Option("--pages", help="Page range such as 1-3,7.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output PDF path.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Remove selected pages and write a new PDF."""
    _emit_result(
        run_remove_pages(input_path, pages=pages, output_path=output_path),
        json_output=json_output,
    )


@app.command("rotate-pages")
def rotate_pages(
    input_path: Annotated[Path, typer.Argument(help="Input PDF file.")],
    pages: Annotated[str, typer.Option("--pages", help="Page range such as 1-3,7.")],
    degrees: Annotated[int, typer.Option("--degrees", help="Rotation degrees, multiple of 90.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output PDF path.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Rotate selected pages and write a new PDF."""
    _emit_result(
        run_rotate_pages(input_path, pages=pages, degrees=degrees, output_path=output_path),
        json_output=json_output,
    )


@app.command("reorder-pages")
def reorder_pages(
    input_path: Annotated[Path, typer.Argument(help="Input PDF file.")],
    order: Annotated[str, typer.Option("--order", help="New page order such as 3,1,2.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output PDF path.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Reorder pages and write a new PDF."""
    _emit_result(
        run_reorder_pages(input_path, order=order, output_path=output_path),
        json_output=json_output,
    )


@app.command("insert-blank-pages")
def insert_blank_pages(
    input_path: Annotated[Path, typer.Argument(help="Input PDF file.")],
    after_page: Annotated[int, typer.Option("--after-page", help="Insert after this 1-based page; use 0 for start.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output PDF path.")],
    count: Annotated[int, typer.Option("--count", help="Number of blank pages to insert.")] = 1,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Insert blank pages and write a new PDF."""
    _emit_result(
        run_insert_blank_pages(
            input_path,
            after_page=after_page,
            count=count,
            output_path=output_path,
        ),
        json_output=json_output,
    )


@app.command("compress")
def compress(
    input_path: Annotated[Path, typer.Argument(help="Input PDF file.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output PDF path.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Compress PDF content streams and write a new PDF."""
    _emit_result(
        run_compress(input_path, output_path=output_path),
        json_output=json_output,
    )


@app.command("repair")
def repair(
    input_path: Annotated[Path, typer.Argument(help="Input PDF file.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output PDF path.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Rewrite a parseable PDF to rebuild output structure."""
    _emit_result(
        run_repair(input_path, output_path=output_path),
        json_output=json_output,
    )


@app.command("image-to-pdf")
def image_to_pdf(
    image_paths: Annotated[list[Path], typer.Argument(help="Input image files.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output PDF path.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Create a PDF from one or more local images."""
    _emit_result(run_image_to_pdf(image_paths, output_path=output_path), json_output=json_output)


@app.command()
def watermark(
    input_path: Annotated[Path, typer.Argument(help="Input PDF file.")],
    text: Annotated[str, typer.Option("--text", help="Watermark text.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output PDF path.")],
    pages: Annotated[str, typer.Option("--pages", help="Page range such as all or 1-3.")] = "all",
    font_size: Annotated[int, typer.Option("--font-size", help="Watermark font size.")] = 48,
    opacity: Annotated[float, typer.Option("--opacity", help="Watermark opacity from 0 to 1.")] = 0.18,
    angle: Annotated[int, typer.Option("--angle", help="Watermark rotation angle.")] = 45,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Add a text watermark overlay to a PDF."""
    _emit_result(
        run_watermark(
            input_path,
            text=text,
            output_path=output_path,
            pages=pages,
            font_size=font_size,
            opacity=opacity,
            angle=angle,
        ),
        json_output=json_output,
    )


@app.command("page-numbers")
def page_numbers(
    input_path: Annotated[Path, typer.Argument(help="Input PDF file.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output PDF path.")],
    pages: Annotated[str, typer.Option("--pages", help="Page range such as all or 1-3.")] = "all",
    template: Annotated[
        str,
        typer.Option("--template", help="Template using {page} and {total}."),
    ] = "{page}",
    font_size: Annotated[int, typer.Option("--font-size", help="Page number font size.")] = 10,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Add page number overlays to a PDF."""
    _emit_result(
        run_page_numbers(
            input_path,
            output_path=output_path,
            pages=pages,
            template=template,
            font_size=font_size,
        ),
        json_output=json_output,
    )


@create_app.command("text")
def create_text(
    text: Annotated[str, typer.Argument(help="Text content to write into a new PDF.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output PDF path.")],
    title: Annotated[str | None, typer.Option("--title", help="Document title.")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Create a PDF from plain text."""
    _emit_result(run_create_text(text, output_path=output_path, title=title), json_output=json_output)


@create_app.command("markdown")
def create_markdown(
    markdown_path: Annotated[Path, typer.Argument(help="Markdown file to convert.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output PDF path.")],
    title: Annotated[str | None, typer.Option("--title", help="Document title.")] = None,
    style_pack: Annotated[
        str,
        typer.Option("--style-pack", help="Local style pack name."),
    ] = "plain_report",
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Create a PDF from a local Markdown file."""
    markdown = markdown_path.read_text(encoding="utf-8")
    _emit_result(
        run_create_markdown(
            markdown,
            output_path=output_path,
            title=title,
            style_pack=style_pack,
        ),
        json_output=json_output,
    )


@create_app.command("from-prompt")
def create_from_prompt(
    prompt: Annotated[str, typer.Argument(help="Creation brief or prompt for the local PDF agent.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output PDF path.")],
    template: Annotated[
        str | None,
        typer.Option("--template", help="Template id such as research_brief, proposal, or worksheet."),
    ] = None,
    style_pack: Annotated[
        str | None,
        typer.Option("--style-pack", help="Style pack id or local JSON style pack path."),
    ] = None,
    data_path: Annotated[
        Path | None,
        typer.Option("--data", help="Optional JSON data file for template fields."),
    ] = None,
    colors: Annotated[
        list[str] | None,
        typer.Option("--color", help="Theme color override such as primary=#4f46e5."),
    ] = None,
    title: Annotated[str | None, typer.Option("--title", help="Optional document title.")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Create a validated local PDF from a prompt, template, and optional JSON data."""
    data = _read_json_object(data_path) if data_path is not None else None
    _emit_result(
        run_create_from_prompt(
            prompt,
            output_path=output_path,
            template=template,
            style_pack=style_pack,
            data=data,
            title=title,
            colors=_parse_color_overrides(colors or []),
        ),
        json_output=json_output,
    )


@create_app.command("templates")
def create_templates(
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """List local PDF creation templates, style packs, and color keys."""
    _emit_result(run_create_templates(), json_output=json_output)


@create_app.command("template-packs")
def create_template_packs(
    output_path: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Optional output catalog JSON path."),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """List local template packs for agent-created PDFs."""
    _emit_result(run_create_template_packs(output_path=output_path), json_output=json_output)


@create_app.command("validate-template-pack")
def create_validate_template_pack(
    template_pack: Annotated[Path, typer.Argument(help="Template pack JSON file.")],
    output_path: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Optional validation JSON output path."),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Validate a local template pack contract."""
    _emit_result(
        run_validate_template_pack(template_pack, output_path=output_path),
        json_output=json_output,
    )


@create_app.command("plan-template-pack")
def create_plan_template_pack(
    template_pack: Annotated[Path, typer.Argument(help="Template pack JSON file or built-in pack id.")],
    target_profile: Annotated[
        str | None,
        typer.Option("--target-profile", "--profile", help="Target PDF Profile id or inline profile JSON."),
    ] = None,
    target_profile_path: Annotated[
        Path | None,
        typer.Option("--target-profile-file", help="Optional Target PDF Profile JSON file."),
    ] = None,
    context_packet_path: Annotated[
        Path | None,
        typer.Option("--context-packet", help="Optional Context Packet JSON path for planning."),
    ] = None,
    planned_output_path: Annotated[
        Path | None,
        typer.Option("--planned-output", help="Recommended PDF output path to include in the create payload."),
    ] = None,
    output_path: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Optional plan JSON output path."),
    ] = None,
    preferred_template_id: Annotated[
        str | None,
        typer.Option("--preferred-template", help="Preferred template id to bias selection."),
    ] = None,
    preferred_color_scheme: Annotated[
        str | None,
        typer.Option("--preferred-color-scheme", help="Preferred color scheme id to use if available."),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Plan a local template-pack PDF creation call from target and context evidence."""
    resolved_target_profile: dict[str, object] | str | None
    if target_profile_path is not None:
        resolved_target_profile = _read_json_object(target_profile_path)
    elif target_profile is not None and target_profile.strip().startswith("{"):
        payload = json.loads(target_profile)
        resolved_target_profile = payload if isinstance(payload, dict) else target_profile
    else:
        resolved_target_profile = target_profile
    _emit_result(
        run_plan_template_pack_creation(
            template_pack,
            target_profile=resolved_target_profile,
            context_packet_path=context_packet_path,
            planned_output_path=planned_output_path,
            output_path=output_path,
            preferred_template_id=preferred_template_id,
            preferred_color_scheme=preferred_color_scheme,
        ),
        json_output=json_output,
    )


@create_app.command("agent")
def create_agent(
    template_pack: Annotated[Path, typer.Argument(help="Template pack JSON file or built-in pack id.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output PDF path.")],
    target_profile: Annotated[
        str | None,
        typer.Option("--target-profile", "--profile", help="Target PDF Profile id or inline profile JSON."),
    ] = None,
    target_profile_path: Annotated[
        Path | None,
        typer.Option("--target-profile-file", help="Optional Target PDF Profile JSON file."),
    ] = None,
    context_packet_path: Annotated[
        Path | None,
        typer.Option("--context-packet", help="Context Packet JSON path for planning and creation."),
    ] = None,
    plan_output_path: Annotated[
        Path | None,
        typer.Option("--plan-output", help="Optional plan JSON output path."),
    ] = None,
    coverage_output_path: Annotated[
        Path | None,
        typer.Option("--coverage-output", help="Optional evidence coverage JSON output path."),
    ] = None,
    context_classification_output_path: Annotated[
        Path | None,
        typer.Option("--context-classification-output", help="Optional Context Packet classification JSON output path."),
    ] = None,
    context_report_output_path: Annotated[
        Path | None,
        typer.Option("--context-report-output", help="Optional Context Packet PDF audit report output path."),
    ] = None,
    context_report_json_output_path: Annotated[
        Path | None,
        typer.Option("--context-report-json-output", help="Optional Context Packet JSON audit report output path."),
    ] = None,
    bundle_output_path: Annotated[
        Path | None,
        typer.Option("--bundle-output", help="Optional portable audit bundle ZIP output path."),
    ] = None,
    preferred_template_id: Annotated[
        str | None,
        typer.Option("--preferred-template", help="Preferred template id to bias selection."),
    ] = None,
    preferred_color_scheme: Annotated[
        str | None,
        typer.Option("--preferred-color-scheme", help="Preferred color scheme id to use if available."),
    ] = None,
    title: Annotated[str | None, typer.Option("--title", help="Optional document title.")] = None,
    prompt: Annotated[str | None, typer.Option("--prompt", help="Optional creation prompt.")] = None,
    style_pack: Annotated[
        str | None,
        typer.Option("--style-pack", help="Optional style pack override."),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Run the local create agent: plan, create, render-check, blank-check, and coverage."""
    resolved_target_profile: dict[str, object] | str | None
    if target_profile_path is not None:
        resolved_target_profile = _read_json_object(target_profile_path)
    elif target_profile is not None and target_profile.strip().startswith("{"):
        payload = json.loads(target_profile)
        resolved_target_profile = payload if isinstance(payload, dict) else target_profile
    else:
        resolved_target_profile = target_profile
    _emit_result(
        run_create_agent(
            template_pack,
            target_profile=resolved_target_profile,
            context_packet_path=context_packet_path,
            output_path=output_path,
            plan_output_path=plan_output_path,
            coverage_output_path=coverage_output_path,
            context_classification_output_path=context_classification_output_path,
            context_report_output_path=context_report_output_path,
            context_report_json_output_path=context_report_json_output_path,
            bundle_output_path=bundle_output_path,
            preferred_template_id=preferred_template_id,
            preferred_color_scheme=preferred_color_scheme,
            title=title,
            prompt=prompt,
            style_pack=style_pack,
        ),
        json_output=json_output,
    )


@create_app.command("from-template-pack")
def create_from_template_pack(
    template_pack: Annotated[Path, typer.Argument(help="Template pack JSON file or built-in pack id.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output PDF path.")],
    template_id: Annotated[str, typer.Option("--template", help="Template id inside the pack.")],
    color_scheme: Annotated[
        str | None,
        typer.Option("--color-scheme", help="Template pack color scheme id."),
    ] = None,
    data_path: Annotated[
        Path | None,
        typer.Option("--data", help="Optional JSON data file for template fields."),
    ] = None,
    context_packet_path: Annotated[
        Path | None,
        typer.Option("--context-packet", help="Optional Context Packet JSON path to auto-build agent blocks."),
    ] = None,
    title: Annotated[str | None, typer.Option("--title", help="Optional document title.")] = None,
    prompt: Annotated[str | None, typer.Option("--prompt", help="Optional creation prompt.")] = None,
    style_pack: Annotated[
        str | None,
        typer.Option("--style-pack", help="Optional style pack override."),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Create a validated PDF from a local template pack."""
    data = _read_json_object(data_path) if data_path is not None else None
    _emit_result(
        run_create_from_template_pack(
            template_pack,
            template_id=template_id,
            output_path=output_path,
            color_scheme=color_scheme,
            data=data,
            context_packet_path=context_packet_path,
            title=title,
            prompt=prompt,
            style_pack=style_pack,
        ),
        json_output=json_output,
    )


@create_app.command("preview")
def create_preview(
    template: Annotated[str, typer.Argument(help="Template id to preview, such as invoice or worksheet.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output preview PDF path.")],
    style_pack: Annotated[
        str | None,
        typer.Option("--style-pack", help="Optional style pack override."),
    ] = None,
    data_path: Annotated[
        Path | None,
        typer.Option("--data", help="Optional JSON data file instead of built-in sample data."),
    ] = None,
    colors: Annotated[
        list[str] | None,
        typer.Option("--color", help="Theme color override such as primary=#4f46e5."),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Generate and validate a local preview PDF for a creation template."""
    data = _read_json_object(data_path) if data_path is not None else None
    _emit_result(
        run_create_template_preview(
            template,
            output_path=output_path,
            style_pack=style_pack,
            data=data,
            colors=_parse_color_overrides(colors or []),
        ),
        json_output=json_output,
    )


@context_app.command("build")
def context_build(
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output context packet JSON path.")],
    files: Annotated[
        list[Path] | None,
        typer.Option("--file", help="Local context file. Can be repeated."),
    ] = None,
    texts: Annotated[
        list[str] | None,
        typer.Option("--text", help="Inline text context. Can be repeated."),
    ] = None,
    links: Annotated[
        list[str] | None,
        typer.Option("--link", help="Web/link context URI. Can be repeated."),
    ] = None,
    item_json: Annotated[
        list[str] | None,
        typer.Option("--item-json", help="Structured context item JSON object or JSON file. Can be repeated."),
    ] = None,
    title: Annotated[str | None, typer.Option("--title", help="Context packet title.")] = None,
    intent: Annotated[str | None, typer.Option("--intent", help="User or agent intent for this context packet.")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Build a local Context Packet with source graph metadata."""
    _emit_result(
        run_build_context_packet(
            _context_items_from_cli(files or [], texts or [], links or [], item_json or []),
            output_path=output_path,
            title=title,
            intent=intent,
        ),
        json_output=json_output,
    )


@context_app.command("ingest")
def context_ingest(
    output_path: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Optional output context item JSON path."),
    ] = None,
    file: Annotated[Path | None, typer.Option("--file", help="Local context file.")] = None,
    text: Annotated[str | None, typer.Option("--text", help="Inline text context.")] = None,
    link: Annotated[str | None, typer.Option("--link", help="Web/link context URI.")] = None,
    item_json: Annotated[
        str | None,
        typer.Option("--item-json", help="Structured context item JSON object or JSON file."),
    ] = None,
    role: Annotated[str | None, typer.Option("--role", help="Context item role override.")] = None,
    label: Annotated[str | None, typer.Option("--label", help="Context item label override.")] = None,
    item_type: Annotated[str | None, typer.Option("--type", help="Explicit context item type override.")] = None,
    transcript: Annotated[str | None, typer.Option("--transcript", help="Provided audio/video transcript.")] = None,
    duration_seconds: Annotated[
        float | None,
        typer.Option("--duration-seconds", help="Provided media duration in seconds."),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Normalize one local source into an agent context item."""
    _emit_result(
        run_context_ingest(
            _single_context_item_from_cli(
                file=file,
                text=text,
                link=link,
                item_json=item_json,
                role=role,
                label=label,
                item_type=item_type,
                transcript=transcript,
                duration_seconds=duration_seconds,
            ),
            output_path=output_path,
        ),
        json_output=json_output,
    )


@context_app.command("packet")
def context_packet(
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output context packet JSON path.")],
    files: Annotated[
        list[Path] | None,
        typer.Option("--file", help="Local context file. Can be repeated."),
    ] = None,
    texts: Annotated[
        list[str] | None,
        typer.Option("--text", help="Inline text context. Can be repeated."),
    ] = None,
    links: Annotated[
        list[str] | None,
        typer.Option("--link", help="Web/link context URI. Can be repeated."),
    ] = None,
    item_json: Annotated[
        list[str] | None,
        typer.Option("--item-json", help="Structured context item JSON object or JSON file. Can be repeated."),
    ] = None,
    title: Annotated[str | None, typer.Option("--title", help="Context packet title.")] = None,
    intent: Annotated[str | None, typer.Option("--intent", help="User or agent intent for this context packet.")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Build a reusable Context Packet from raw or pre-ingested context items."""
    _emit_result(
        run_context_packet(
            _context_items_from_cli(files or [], texts or [], links or [], item_json or []),
            output_path=output_path,
            title=title,
            intent=intent,
        ),
        json_output=json_output,
    )


@context_app.command("classify")
def context_classify(
    context_packet_path: Annotated[Path, typer.Argument(help="Context packet JSON path.")],
    output_path: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Optional output classification JSON path."),
    ] = None,
    profile: Annotated[str | None, typer.Option("--profile", help="Target PDF profile id.")] = None,
    profile_path: Annotated[
        Path | None,
        typer.Option("--profile-json", help="Optional target profile JSON file."),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Classify context items for agent routing into target PDF blocks and slots."""
    target_profile: dict[str, object] | str | None = _read_json_object(profile_path) if profile_path else profile
    _emit_result(
        run_context_classify(
            context_packet_path,
            target_profile=target_profile,
            output_path=output_path,
        ),
        json_output=json_output,
    )


@context_app.command("code-snapshot")
def context_code_snapshot(
    path: Annotated[Path, typer.Argument(help="Local code file to snapshot.")],
    output_path: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Optional output context item JSON path."),
    ] = None,
    label: Annotated[str | None, typer.Option("--label", help="Context item label.")] = None,
    role: Annotated[str, typer.Option("--role", help="Context item role.")] = "code_evidence",
    context_item_id: Annotated[
        str | None,
        typer.Option("--context-item-id", help="Stable context item/source ref id."),
    ] = None,
    line_start: Annotated[int | None, typer.Option("--line-start", help="1-based first line to include.")] = None,
    line_end: Annotated[int | None, typer.Option("--line-end", help="1-based final line to include.")] = None,
    repository_root: Annotated[
        Path | None,
        typer.Option("--repository-root", help="Optional repo root for relative path evidence."),
    ] = None,
    include_dependencies: Annotated[
        bool,
        typer.Option("--include-dependencies", help="Include static import/dependency hints."),
    ] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Create a code context item with local symbol, range, hash, and source refs."""
    _emit_result(
        run_context_code_snapshot(
            path=path,
            output_path=output_path,
            label=label,
            role=role,
            context_item_id=context_item_id,
            line_start=line_start,
            line_end=line_end,
            repository_root=repository_root,
            include_dependencies=include_dependencies,
        ),
        json_output=json_output,
    )


@context_app.command("data-profile")
def context_data_profile(
    path: Annotated[Path, typer.Argument(help="Local CSV/TSV/JSON/JSONL/XLSX data file to profile.")],
    output_path: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Optional output context item JSON path."),
    ] = None,
    label: Annotated[str | None, typer.Option("--label", help="Context item label.")] = None,
    role: Annotated[str, typer.Option("--role", help="Context item role.")] = "data_evidence",
    context_item_id: Annotated[
        str | None,
        typer.Option("--context-item-id", help="Stable context item/source ref id."),
    ] = None,
    sheet: Annotated[str | None, typer.Option("--sheet", help="Optional XLSX sheet name.")] = None,
    max_rows: Annotated[int, typer.Option("--max-rows", help="Maximum preview rows to keep.")] = 100,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Create a data context item with local table/profile evidence."""
    _emit_result(
        run_context_data_profile(
            path=path,
            output_path=output_path,
            label=label,
            role=role,
            context_item_id=context_item_id,
            sheet=sheet,
            max_rows=max_rows,
        ),
        json_output=json_output,
    )


@compose_app.command("plan")
def compose_plan_command(
    context_packet_path: Annotated[Path, typer.Argument(help="Context packet JSON path.")],
    output_path: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Optional output composition plan JSON path."),
    ] = None,
    profile: Annotated[str, typer.Option("--profile", help="Target PDF profile id.")] = "research_brief",
    profile_path: Annotated[
        Path | None,
        typer.Option("--profile-json", help="Optional target profile JSON file."),
    ] = None,
    style_pack: Annotated[str | None, typer.Option("--style-pack", help="Optional style pack override.")] = None,
    title: Annotated[str | None, typer.Option("--title", help="Optional planned PDF title.")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Plan composition IR, source map, coverage, and render payload without writing a PDF."""
    target_profile: dict[str, object] | str = _read_json_object(profile_path) if profile_path else profile
    _emit_result(
        run_compose_plan(
            context_packet_path,
            target_profile=target_profile,
            output_path=output_path,
            style_pack=style_pack,
            title=title,
        ),
        json_output=json_output,
    )


@compose_app.command("render-ir")
def compose_render_ir_command(
    composition_path: Annotated[Path, typer.Argument(help="Composition plan/IR JSON path.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output rendered PDF path.")],
    style_pack: Annotated[str | None, typer.Option("--style-pack", help="Optional style pack override.")] = None,
    title: Annotated[str | None, typer.Option("--title", help="Optional rendered PDF title.")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Render a composition plan or IR payload into a validated PDF artifact."""
    _emit_result(
        run_compose_render_ir(
            composition_path,
            output_path=output_path,
            style_pack=style_pack,
            title=title,
        ),
        json_output=json_output,
    )


@compose_app.command("from-context")
def compose_from_context_command(
    context_packet_path: Annotated[Path, typer.Argument(help="Context packet JSON path.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output composed PDF path.")],
    profile: Annotated[str, typer.Option("--profile", help="Target PDF profile id.")] = "research_brief",
    profile_path: Annotated[
        Path | None,
        typer.Option("--profile-json", help="Optional target profile JSON file."),
    ] = None,
    style_pack: Annotated[str | None, typer.Option("--style-pack", help="Optional style pack override.")] = None,
    title: Annotated[str | None, typer.Option("--title", help="Optional composed PDF title.")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Compose a validated target PDF from a Context Packet and target profile."""
    target_profile: dict[str, object] | str = _read_json_object(profile_path) if profile_path else profile
    _emit_result(
        run_compose_from_context(
            context_packet_path,
            target_profile=target_profile,
            output_path=output_path,
            style_pack=style_pack,
            title=title,
        ),
        json_output=json_output,
    )


@compose_app.command("add-code-block")
def compose_add_code_block(
    input_path: Annotated[Path, typer.Argument(help="Input PDF path.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output composed PDF path.")],
    title: Annotated[str, typer.Option("--title", help="Code block title.")] = "Code Block",
    code: Annotated[str, typer.Option("--code", help="Code content to append.")] = "",
    language: Annotated[str, typer.Option("--language", help="Code language label.")] = "text",
    source_refs: Annotated[
        list[str] | None,
        typer.Option("--source-ref", help="Source ref for this block; may be repeated."),
    ] = None,
    block_id: Annotated[str | None, typer.Option("--block-id", help="Optional target block id.")] = None,
    target_slot: Annotated[str | None, typer.Option("--target-slot", help="Optional target slot.")] = None,
    composition_path: Annotated[Path | None, typer.Option("--composition", help="Composition JSON for source-ref validation.")] = None,
    layer_manifest_path: Annotated[Path | None, typer.Option("--layers", help="Layer manifest for edit-policy validation.")] = None,
    manifest_output_path: Annotated[Path | None, typer.Option("--manifest-output", help="Output compose block manifest JSON path.")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Append a source-backed code block page to a new PDF artifact."""
    _emit_result(
        run_compose_add_code_block(
            input_path=input_path,
            output_path=output_path,
            title=title,
            code=code,
            language=language,
            source_refs=source_refs,
            block_id=block_id,
            target_slot=target_slot,
            composition_path=composition_path,
            layer_manifest_path=layer_manifest_path,
            manifest_output_path=manifest_output_path,
        ),
        json_output=json_output,
    )


@compose_app.command("add-table")
def compose_add_table(
    input_path: Annotated[Path, typer.Argument(help="Input PDF path.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output composed PDF path.")],
    title: Annotated[str, typer.Option("--title", help="Table title.")] = "Table",
    columns_raw: Annotated[str, typer.Option("--columns", help="Comma-separated column names.")] = "",
    rows_raw: Annotated[
        list[str] | None,
        typer.Option("--row", help="Comma-separated row values; may be repeated."),
    ] = None,
    source_refs: Annotated[
        list[str] | None,
        typer.Option("--source-ref", help="Source ref for this block; may be repeated."),
    ] = None,
    block_id: Annotated[str | None, typer.Option("--block-id", help="Optional target block id.")] = None,
    target_slot: Annotated[str | None, typer.Option("--target-slot", help="Optional target slot.")] = None,
    composition_path: Annotated[Path | None, typer.Option("--composition", help="Composition JSON for source-ref validation.")] = None,
    layer_manifest_path: Annotated[Path | None, typer.Option("--layers", help="Layer manifest for edit-policy validation.")] = None,
    manifest_output_path: Annotated[Path | None, typer.Option("--manifest-output", help="Output compose block manifest JSON path.")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Append a source-backed table page to a new PDF artifact."""
    _emit_result(
        run_compose_add_table(
            input_path=input_path,
            output_path=output_path,
            title=title,
            columns=_parse_csv_values(columns_raw),
            rows=[_parse_csv_values(row) for row in rows_raw or []],
            source_refs=source_refs,
            block_id=block_id,
            target_slot=target_slot,
            composition_path=composition_path,
            layer_manifest_path=layer_manifest_path,
            manifest_output_path=manifest_output_path,
        ),
        json_output=json_output,
    )


@compose_app.command("add-figure")
def compose_add_figure(
    input_path: Annotated[Path, typer.Argument(help="Input PDF path.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output composed PDF path.")],
    image_path: Annotated[Path, typer.Option("--image", help="Local image path to append.")],
    title: Annotated[str, typer.Option("--title", help="Figure title.")] = "Figure",
    caption: Annotated[str | None, typer.Option("--caption", help="Optional figure caption.")] = None,
    source_refs: Annotated[
        list[str] | None,
        typer.Option("--source-ref", help="Source ref for this block; may be repeated."),
    ] = None,
    block_id: Annotated[str | None, typer.Option("--block-id", help="Optional target block id.")] = None,
    target_slot: Annotated[str | None, typer.Option("--target-slot", help="Optional target slot.")] = None,
    composition_path: Annotated[Path | None, typer.Option("--composition", help="Composition JSON for source-ref validation.")] = None,
    layer_manifest_path: Annotated[Path | None, typer.Option("--layers", help="Layer manifest for edit-policy validation.")] = None,
    manifest_output_path: Annotated[Path | None, typer.Option("--manifest-output", help="Output compose block manifest JSON path.")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Append a source-backed figure page to a new PDF artifact."""
    _emit_result(
        run_compose_add_figure(
            input_path=input_path,
            output_path=output_path,
            title=title,
            image_path=image_path,
            caption=caption,
            source_refs=source_refs,
            block_id=block_id,
            target_slot=target_slot,
            composition_path=composition_path,
            layer_manifest_path=layer_manifest_path,
            manifest_output_path=manifest_output_path,
        ),
        json_output=json_output,
    )


@compose_app.command("add-appendix")
def compose_add_appendix(
    input_path: Annotated[Path, typer.Argument(help="Input PDF path.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output composed PDF path.")],
    title: Annotated[str, typer.Option("--title", help="Appendix title.")] = "Appendix",
    markdown: Annotated[str, typer.Option("--markdown", help="Markdown appendix body.")] = "",
    source_refs: Annotated[
        list[str] | None,
        typer.Option("--source-ref", help="Source ref for this block; may be repeated."),
    ] = None,
    block_id: Annotated[str | None, typer.Option("--block-id", help="Optional target block id.")] = None,
    target_slot: Annotated[str | None, typer.Option("--target-slot", help="Optional target slot.")] = None,
    composition_path: Annotated[Path | None, typer.Option("--composition", help="Composition JSON for source-ref validation.")] = None,
    layer_manifest_path: Annotated[Path | None, typer.Option("--layers", help="Layer manifest for edit-policy validation.")] = None,
    manifest_output_path: Annotated[Path | None, typer.Option("--manifest-output", help="Output compose block manifest JSON path.")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Append a source-backed Markdown appendix to a new PDF artifact."""
    _emit_result(
        run_compose_add_appendix(
            input_path=input_path,
            output_path=output_path,
            title=title,
            markdown=markdown,
            source_refs=source_refs,
            block_id=block_id,
            target_slot=target_slot,
            composition_path=composition_path,
            layer_manifest_path=layer_manifest_path,
            manifest_output_path=manifest_output_path,
        ),
        json_output=json_output,
    )


@compose_app.command("add-citation")
def compose_add_citation(
    input_path: Annotated[Path, typer.Argument(help="Input PDF path.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output composed PDF path.")],
    source: Annotated[str, typer.Option("--source", help="Citation source URL, file, or reference.")],
    title: Annotated[str, typer.Option("--title", help="Citation title.")] = "Citation",
    quote: Annotated[str | None, typer.Option("--quote", help="Optional quoted or cited claim text.")] = None,
    page: Annotated[str | None, typer.Option("--page", help="Optional page, section, or timestamp label.")] = None,
    source_refs: Annotated[
        list[str] | None,
        typer.Option("--source-ref", help="Source ref for this block; may be repeated."),
    ] = None,
    block_id: Annotated[str | None, typer.Option("--block-id", help="Optional target block id.")] = None,
    target_slot: Annotated[str | None, typer.Option("--target-slot", help="Optional target slot.")] = None,
    composition_path: Annotated[Path | None, typer.Option("--composition", help="Composition JSON for source-ref validation.")] = None,
    layer_manifest_path: Annotated[Path | None, typer.Option("--layers", help="Layer manifest for edit-policy validation.")] = None,
    manifest_output_path: Annotated[Path | None, typer.Option("--manifest-output", help="Output compose block manifest JSON path.")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Append a source-backed citation page to a new PDF artifact."""
    _emit_result(
        run_compose_add_citation(
            input_path=input_path,
            output_path=output_path,
            title=title,
            source=source,
            quote=quote,
            page=page,
            source_refs=source_refs,
            block_id=block_id,
            target_slot=target_slot,
            composition_path=composition_path,
            layer_manifest_path=layer_manifest_path,
            manifest_output_path=manifest_output_path,
        ),
        json_output=json_output,
    )


@compose_app.command("add-media-reference")
def compose_add_media_reference(
    input_path: Annotated[Path, typer.Argument(help="Input PDF path.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output composed PDF path.")],
    media_path: Annotated[Path, typer.Option("--media", help="Local audio/video/media file or reference path.")],
    title: Annotated[str, typer.Option("--title", help="Media reference title.")] = "Media Reference",
    media_kind: Annotated[str, typer.Option("--media-kind", help="Media kind: audio, video, or media.")] = "media",
    transcript_excerpt: Annotated[
        str | None,
        typer.Option("--transcript-excerpt", help="Optional user/agent-provided transcript excerpt."),
    ] = None,
    duration_seconds: Annotated[
        float | None,
        typer.Option("--duration-seconds", help="Optional media duration in seconds."),
    ] = None,
    chapter_count: Annotated[int | None, typer.Option("--chapter-count", help="Optional chapter count.")] = None,
    keyframe_count: Annotated[int | None, typer.Option("--keyframe-count", help="Optional keyframe count.")] = None,
    source_refs: Annotated[
        list[str] | None,
        typer.Option("--source-ref", help="Source ref for this block; may be repeated."),
    ] = None,
    block_id: Annotated[str | None, typer.Option("--block-id", help="Optional target block id.")] = None,
    target_slot: Annotated[str | None, typer.Option("--target-slot", help="Optional target slot.")] = None,
    composition_path: Annotated[Path | None, typer.Option("--composition", help="Composition JSON for source-ref validation.")] = None,
    layer_manifest_path: Annotated[Path | None, typer.Option("--layers", help="Layer manifest for edit-policy validation.")] = None,
    manifest_output_path: Annotated[Path | None, typer.Option("--manifest-output", help="Output compose block manifest JSON path.")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Append a source-backed media reference page to a new PDF artifact."""
    _emit_result(
        run_compose_add_media_reference(
            input_path=input_path,
            output_path=output_path,
            title=title,
            media_path=media_path,
            media_kind=media_kind,
            transcript_excerpt=transcript_excerpt,
            duration_seconds=duration_seconds,
            chapter_count=chapter_count,
            keyframe_count=keyframe_count,
            source_refs=source_refs,
            block_id=block_id,
            target_slot=target_slot,
            composition_path=composition_path,
            layer_manifest_path=layer_manifest_path,
            manifest_output_path=manifest_output_path,
        ),
        json_output=json_output,
    )


@compose_app.command("add-slide")
def compose_add_slide(
    input_path: Annotated[Path, typer.Argument(help="Input PDF path.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output composed PDF path.")],
    title: Annotated[str, typer.Option("--title", help="Slide title.")] = "Slide",
    subtitle: Annotated[str | None, typer.Option("--subtitle", help="Optional slide subtitle.")] = None,
    body: Annotated[
        list[str] | None,
        typer.Option("--body", help="Slide body line; may be repeated."),
    ] = None,
    code: Annotated[str | None, typer.Option("--code", help="Optional code block to include on the slide.")] = None,
    image_path: Annotated[Path | None, typer.Option("--image", help="Optional local image path for the slide.")] = None,
    source_refs: Annotated[
        list[str] | None,
        typer.Option("--source-ref", help="Source ref for this block; may be repeated."),
    ] = None,
    block_id: Annotated[str | None, typer.Option("--block-id", help="Optional target block id.")] = None,
    target_slot: Annotated[str | None, typer.Option("--target-slot", help="Optional target slot.")] = None,
    composition_path: Annotated[Path | None, typer.Option("--composition", help="Composition JSON for source-ref validation.")] = None,
    layer_manifest_path: Annotated[Path | None, typer.Option("--layers", help="Layer manifest for edit-policy validation.")] = None,
    manifest_output_path: Annotated[Path | None, typer.Option("--manifest-output", help="Output compose block manifest JSON path.")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Append a source-backed slide-like page to a new PDF artifact."""
    _emit_result(
        run_compose_add_slide(
            input_path=input_path,
            output_path=output_path,
            title=title,
            subtitle=subtitle,
            body=body,
            code=code,
            image_path=image_path,
            source_refs=source_refs,
            block_id=block_id,
            target_slot=target_slot,
            composition_path=composition_path,
            layer_manifest_path=layer_manifest_path,
            manifest_output_path=manifest_output_path,
        ),
        json_output=json_output,
    )


@target_app.command("profiles")
def target_profiles(
    output_path: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Optional output target profile catalog JSON path."),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """List built-in target PDF profiles with layout slots and accepted block types."""
    _emit_result(run_target_profiles(output_path=output_path), json_output=json_output)


@target_app.command("validate")
def target_validate(
    profile: Annotated[str, typer.Option("--profile", help="Built-in target profile id.")] = "research_brief",
    profile_path: Annotated[
        Path | None,
        typer.Option("--profile-json", help="Target profile JSON file to validate."),
    ] = None,
    output_path: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Optional output target profile validation JSON path."),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Validate a built-in or custom target PDF profile."""
    target_profile: dict[str, object] | str = _read_json_object(profile_path) if profile_path else profile
    _emit_result(
        run_validate_target_profile(target_profile, output_path=output_path),
        json_output=json_output,
    )


@evidence_app.command("coverage-report")
def evidence_coverage_report(
    composition_path: Annotated[Path, typer.Argument(help="Composition JSON artifact path.")],
    output_path: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Optional output coverage JSON path."),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Create an evidence coverage report from a composition artifact."""
    _emit_result(
        run_evidence_coverage_report(composition_path, output_path=output_path),
        json_output=json_output,
    )


@evidence_app.command("map-sources")
def evidence_map_sources(
    composition_path: Annotated[
        Path | None,
        typer.Argument(help="Optional composition JSON artifact path."),
    ] = None,
    context_packet_path: Annotated[
        Path | None,
        typer.Option("--context-packet", help="Optional Context Packet JSON for source evidence enrichment."),
    ] = None,
    blocks_path: Annotated[
        Path | None,
        typer.Option("--blocks", help="Optional JSON array of generated blocks."),
    ] = None,
    claims_path: Annotated[
        Path | None,
        typer.Option("--claims", help="Optional JSON array of extracted claims."),
    ] = None,
    output_path: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Optional output source-map report JSON path."),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Map generated blocks or claims back to Context Packet source refs."""
    _emit_result(
        run_evidence_map_sources(
            composition=composition_path,
            blocks=_read_json_object_list(blocks_path, "--blocks") if blocks_path else None,
            claims=_read_json_object_list(claims_path, "--claims") if claims_path else None,
            context_packet=context_packet_path,
            output_path=output_path,
        ),
        json_output=json_output,
    )


@evidence_app.command("context-packet-report")
def evidence_context_packet_report(
    context_packet_path: Annotated[Path, typer.Argument(help="Context packet JSON artifact path.")],
    output_path: Annotated[
        Path,
        typer.Option("--output", "-o", help="Output PDF report path."),
    ],
    report_output_path: Annotated[
        Path | None,
        typer.Option("--report-output", help="Optional output JSON report path."),
    ] = None,
    title: Annotated[str | None, typer.Option("--title", help="Optional PDF report title.")] = None,
    style_pack: Annotated[str, typer.Option("--style-pack", help="Markdown PDF style pack name.")] = "paper_ink",
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Create a validated PDF/JSON report for a Context Packet and source graph."""
    _emit_result(
        run_context_packet_report(
            context_packet_path,
            output_path=output_path,
            report_output_path=report_output_path,
            title=title,
            style_pack=style_pack,
        ),
        json_output=json_output,
    )


@patch_app.command("plan")
def patch_plan(
    input_path: Annotated[Path, typer.Argument(help="Input PDF path to patch.")],
    operations_path: Annotated[Path, typer.Option("--operations", help="Patch operations JSON file.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output patch manifest JSON path.")],
    composition_path: Annotated[
        Path | None,
        typer.Option("--composition", help="Optional composition JSON artifact for source refs."),
    ] = None,
    layer_manifest_path: Annotated[
        Path | None,
        typer.Option("--layers", help="Optional template layer manifest JSON artifact for layer/block/slot refs."),
    ] = None,
    reason: Annotated[str | None, typer.Option("--reason", help="Reason for this patch transaction.")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Create a structured patch manifest without mutating the input PDF."""
    operations_raw = _read_json_value(operations_path)
    operations = _parse_patch_operations(operations_raw)
    _emit_result(
        run_patch_plan(
            input_path=input_path,
            operations=operations,
            output_path=output_path,
            composition_path=composition_path,
            layer_manifest_path=layer_manifest_path,
            reason=reason,
        ),
        json_output=json_output,
    )


@patch_app.command("preview")
def patch_preview(
    patch_manifest_path: Annotated[Path, typer.Argument(help="Patch manifest JSON path.")],
    output_path: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Optional output preview JSON path."),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Preview patch effects and validation requirements."""
    _emit_result(
        run_patch_preview(patch_manifest_path, output_path=output_path),
        json_output=json_output,
    )


@patch_app.command("apply")
def patch_apply(
    patch_manifest_path: Annotated[Path, typer.Argument(help="Patch manifest JSON path.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output patched PDF path.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Apply a patch transaction to a new output PDF artifact."""
    _emit_result(
        run_patch_apply(patch_manifest_path, output_path=output_path),
        json_output=json_output,
    )


@patch_app.command("verify")
def patch_verify(
    patch_manifest_path: Annotated[Path, typer.Argument(help="Patch manifest JSON path.")],
    patched_path: Annotated[Path, typer.Argument(help="Patched PDF path.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Verify a patched PDF against a patch manifest."""
    _emit_result(
        run_patch_verify(patch_manifest_path, patched_path=patched_path),
        json_output=json_output,
    )


@artifacts_app.command("export-bundle")
def artifacts_export_bundle(
    artifact_paths: Annotated[
        list[Path],
        typer.Option("--file", help="Artifact file to include; repeat for PDF, manifests, coverage, reports."),
    ],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output .zip bundle path.")],
    title: Annotated[str | None, typer.Option("--title", help="Human-readable bundle title.")] = None,
    metadata: Annotated[
        list[str] | None,
        typer.Option("--metadata", help="Bundle metadata as KEY=VALUE; repeat as needed."),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Export local artifacts into a portable audit bundle."""
    _emit_result(
        run_artifacts_export_bundle(
            artifact_paths=artifact_paths,
            output_path=output_path,
            title=title,
            metadata=_parse_key_value_items(metadata or []),
        ),
        json_output=json_output,
    )


@artifacts_app.command("verify-bundle")
def artifacts_verify_bundle(
    bundle_path: Annotated[Path, typer.Argument(help="Input .agentpdf-bundle.zip path.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Verify a portable audit bundle manifest and checksums."""
    _emit_result(
        run_artifacts_verify_bundle(bundle_path=bundle_path),
        json_output=json_output,
    )


@app.command()
def render(
    input_path: Annotated[Path, typer.Argument(help="Input PDF file.")],
    pages: Annotated[str, typer.Option("--pages", help="Page range such as 1 or 1-3.")],
    image_format: Annotated[str, typer.Option("--format", help="Image format.")] = "png",
    out_dir: Annotated[Path, typer.Option("--out-dir", help="Output render directory.")] = Path(
        "renders"
    ),
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Render PDF pages to images when an optional renderer is configured."""
    _emit_result(
        run_render(input_path, pages=pages, image_format=image_format, out_dir=out_dir),
        json_output=json_output,
    )


@app.command("extract-images")
def extract_images(
    input_path: Annotated[Path, typer.Argument(help="Input PDF file.")],
    pages: Annotated[str, typer.Option("--pages", help="Page range such as all or 1-3.")] = "all",
    out_dir: Annotated[Path, typer.Option("--out-dir", help="Directory for extracted images.")] = Path(
        "extracted-images"
    ),
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Extract embedded images from selected PDF pages."""
    _emit_result(
        run_extract_images(input_path=input_path, pages=pages, out_dir=out_dir),
        json_output=json_output,
    )


@app.command("extract-text")
def extract_text(
    input_path: Annotated[Path, typer.Argument(help="Input PDF file.")],
    pages: Annotated[str, typer.Option("--pages", help="Page range such as all or 1-3.")] = "all",
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Extract text from PDF pages."""
    _emit_result(run_extract_text(input_path, pages=pages), json_output=json_output)


@app.command("pdf-to-json")
def pdf_to_json(
    input_path: Annotated[Path, typer.Argument(help="Input PDF file.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output JSON path.")],
    pages: Annotated[str, typer.Option("--pages", help="Page range such as all or 1-3.")] = "all",
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Export a local PDF to Document IR JSON."""
    _emit_result(
        run_pdf_to_json(input_path, output_path=output_path, pages=pages),
        json_output=json_output,
    )


@app.command("pdf-to-markdown")
def pdf_to_markdown(
    input_path: Annotated[Path, typer.Argument(help="Input PDF file.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output Markdown path.")],
    pages: Annotated[str, typer.Option("--pages", help="Page range such as all or 1-3.")] = "all",
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Export a local PDF to cited Markdown via Document IR."""
    _emit_result(
        run_pdf_to_markdown(input_path, output_path=output_path, pages=pages),
        json_output=json_output,
    )


@metadata_app.command("read")
def metadata_read(
    input_path: Annotated[Path, typer.Argument(help="Input PDF file.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Read PDF metadata."""
    _emit_result(run_metadata_read(input_path), json_output=json_output)


@metadata_app.command("page-info")
def metadata_page_info(
    input_path: Annotated[Path, typer.Argument(help="Input PDF file.")],
    pages: Annotated[str, typer.Option("--pages", help="Page range such as all or 1-3.")] = "all",
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Return page size, rotation, text-layer, and image facts."""
    _emit_result(run_metadata_page_info(input_path, pages=pages), json_output=json_output)


@metadata_app.command("update")
def metadata_update(
    input_path: Annotated[Path, typer.Argument(help="Input PDF file.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output PDF path.")],
    title: Annotated[str | None, typer.Option("--title", help="Document title.")] = None,
    author: Annotated[str | None, typer.Option("--author", help="Document author.")] = None,
    subject: Annotated[str | None, typer.Option("--subject", help="Document subject.")] = None,
    keywords: Annotated[str | None, typer.Option("--keywords", help="Document keywords.")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Update PDF metadata and write a new PDF."""
    metadata = {
        key: value
        for key, value in {
            "Title": title,
            "Author": author,
            "Subject": subject,
            "Keywords": keywords,
        }.items()
        if value is not None
    }
    _emit_result(
        run_metadata_update(input_path, metadata=metadata, output_path=output_path),
        json_output=json_output,
    )


@metadata_app.command("remove")
def metadata_remove(
    input_path: Annotated[Path, typer.Argument(help="Input PDF file.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output PDF path.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Remove PDF metadata and write a new PDF."""
    _emit_result(run_metadata_remove(input_path, output_path=output_path), json_output=json_output)


@security_app.command("remove-metadata")
def security_remove_metadata(
    input_path: Annotated[Path, typer.Argument(help="Input PDF file.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output PDF path.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Remove document metadata under the security namespace."""
    _emit_result(run_security_remove_metadata(input_path, output_path=output_path), json_output=json_output)


@app.command()
def validate(
    path: Annotated[Path, typer.Argument(help="PDF file to validate.")],
    expected_pages: Annotated[
        int | None,
        typer.Option("--expected-pages", help="Expected page count."),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Validate generated PDF output."""
    _emit_result(
        run_validate_output(path, expected_pages=expected_pages),
        json_output=json_output,
    )


@app.command("page-count-check")
def page_count_check(
    path: Annotated[Path, typer.Argument(help="PDF file to check.")],
    expected_pages: Annotated[int, typer.Option("--expected-pages", help="Expected page count.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Compare the PDF page count with an expected value."""
    _emit_result(run_page_count_check(path, expected_pages=expected_pages), json_output=json_output)


@app.command("render-check")
def render_check(
    path: Annotated[Path, typer.Argument(help="PDF file to render-check.")],
    pages: Annotated[str, typer.Option("--pages", help="Page range such as all or 1-3.")] = "all",
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Render selected pages in memory to verify output renderability."""
    _emit_result(
        run_render_check(path, pages=pages),
        json_output=json_output,
    )


@app.command("blank-page-check")
def blank_page_check(
    path: Annotated[Path, typer.Argument(help="PDF file to scan for blank pages.")],
    pages: Annotated[str, typer.Option("--pages", help="Page range such as all or 1-3.")] = "all",
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Detect blank pages with text-layer and render evidence."""
    _emit_result(
        run_blank_page_check(path, pages=pages),
        json_output=json_output,
    )


@app.command("parse-lite")
def parse_lite(
    input_path: Annotated[Path, typer.Argument(help="Input PDF file.")],
    pages: Annotated[str, typer.Option("--pages", help="Page range such as all or 1-3.")] = "all",
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Parse a local PDF text layer into Document IR."""
    _emit_result(run_parse_lite(input_path, pages=pages), json_output=json_output)


@rag_app.command("ingest")
def rag_ingest(
    input_path: Annotated[Path, typer.Argument(help="Input PDF file.")],
    index_path: Annotated[Path, typer.Option("--index", help="Output local JSON index path.")],
    pages: Annotated[str, typer.Option("--pages", help="Page range such as all or 1-3.")] = "all",
    max_chars: Annotated[int, typer.Option("--max-chars", help="Maximum characters per chunk.")] = 1200,
    overlap_chars: Annotated[
        int,
        typer.Option("--overlap-chars", help="Overlapping characters between chunks."),
    ] = 120,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Build a local cited keyword index for a PDF."""
    _emit_result(
        run_rag_ingest(
            input_path,
            index_path=index_path,
            pages=pages,
            max_chars=max_chars,
            overlap_chars=overlap_chars,
        ),
        json_output=json_output,
    )


@rag_app.command("query")
def rag_query(
    index_path: Annotated[Path, typer.Argument(help="Local JSON index path or directory.")],
    query: Annotated[str, typer.Option("--query", help="Question or search query.")],
    top_k: Annotated[int, typer.Option("--top-k", help="Number of chunks to return.")] = 5,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Query a local PDF index and return extractive citations."""
    _emit_result(run_rag_query(index_path, query=query, top_k=top_k), json_output=json_output)


@rag_app.command("chat")
def rag_chat(
    input_path: Annotated[Path, typer.Argument(help="Input PDF file.")],
    question: Annotated[str, typer.Option("--question", help="Question to ask the PDF.")],
    index_path: Annotated[
        Path | None,
        typer.Option("--index", help="Optional output local JSON index path."),
    ] = None,
    report_output_path: Annotated[
        Path | None,
        typer.Option("--report-output", help="Optional output cited PDF report path."),
    ] = None,
    highlight_output_path: Annotated[
        Path | None,
        typer.Option("--highlight-output", help="Optional output highlighted source PDF path."),
    ] = None,
    pages: Annotated[str, typer.Option("--pages", help="Page range such as all or 1-3.")] = "all",
    top_k: Annotated[int, typer.Option("--top-k", help="Number of supporting chunks.")] = 5,
    max_chars: Annotated[int, typer.Option("--max-chars", help="Maximum characters per chunk.")] = 1200,
    overlap_chars: Annotated[
        int,
        typer.Option("--overlap-chars", help="Overlapping characters between chunks."),
    ] = 120,
    style_pack: Annotated[str, typer.Option("--style-pack", help="Answer report style pack.")] = "plain_report",
    highlight_color: Annotated[str, typer.Option("--highlight-color", help="Hex RGB highlight color.")] = "fff59d",
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Ask a local PDF and return answer, citations, report, and highlights."""
    _emit_result(
        run_rag_chat(
            input_path,
            question=question,
            index_path=index_path,
            report_output_path=report_output_path,
            highlight_output_path=highlight_output_path,
            pages=pages,
            top_k=top_k,
            max_chars=max_chars,
            overlap_chars=overlap_chars,
            style_pack=style_pack,
            highlight_color=highlight_color,
        ),
        json_output=json_output,
    )


@rag_app.command("search")
def rag_search(
    index_path: Annotated[Path, typer.Argument(help="Local JSON index path or directory.")],
    query: Annotated[str, typer.Option("--query", help="Search query.")],
    top_k: Annotated[int, typer.Option("--top-k", help="Number of chunks to return.")] = 5,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Search a local PDF index and return cited chunks."""
    _emit_result(run_rag_search(index_path, query=query, top_k=top_k), json_output=json_output)


@rag_app.command("cite-answer")
def rag_cite_answer(
    index_path: Annotated[Path, typer.Argument(help="Local JSON index path or directory.")],
    answer: Annotated[str, typer.Option("--answer", help="Answer text to cite from the local index.")],
    top_k: Annotated[int, typer.Option("--top-k", help="Number of supporting chunks.")] = 5,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Find page/bbox citations that support an answer."""
    _emit_result(
        run_rag_cite_answer(index_path, answer=answer, top_k=top_k),
        json_output=json_output,
    )


@rag_app.command("highlight-sources")
def rag_highlight_sources(
    index_path: Annotated[Path, typer.Argument(help="Local JSON index path or directory.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output highlighted PDF path.")],
    answer: Annotated[
        str | None,
        typer.Option("--answer", help="Answer text to cite and highlight from the local index."),
    ] = None,
    query: Annotated[str | None, typer.Option("--query", help="Search query to highlight.")] = None,
    top_k: Annotated[int, typer.Option("--top-k", help="Number of supporting chunks.")] = 5,
    highlight_color: Annotated[str, typer.Option("--highlight-color", help="Hex RGB highlight color.")] = "fff59d",
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Create a highlighted copy of the source PDF from local citations."""
    _emit_result(
        run_rag_highlight_sources(
            index_path,
            output_path=output_path,
            answer=answer,
            query=query,
            top_k=top_k,
            highlight_color=highlight_color,
        ),
        json_output=json_output,
    )


@rag_app.command("export-report")
def rag_export_report(
    index_path: Annotated[Path, typer.Argument(help="Local JSON index path or directory.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output cited PDF report path.")],
    question: Annotated[str, typer.Option("--question", help="Question answered by this report.")],
    answer: Annotated[
        str | None,
        typer.Option("--answer", help="Optional answer text to cite from the local index."),
    ] = None,
    top_k: Annotated[int, typer.Option("--top-k", help="Number of supporting chunks.")] = 5,
    include_citations: Annotated[
        bool,
        typer.Option("--include-citations/--no-citations", help="Include cited snippets in the report."),
    ] = True,
    title: Annotated[str | None, typer.Option("--title", help="Optional PDF report title.")] = None,
    style_pack: Annotated[str, typer.Option("--style-pack", help="Markdown PDF style pack name.")] = "plain_report",
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Create a cited local PDF report from a RAG answer."""
    _emit_result(
        run_rag_export_report(
            index_path,
            output_path=output_path,
            question=question,
            answer=answer,
            top_k=top_k,
            include_citations=include_citations,
            title=title,
            style_pack=style_pack,
        ),
        json_output=json_output,
    )


@workflow_app.command("plan")
def workflow_plan(
    goal: Annotated[str, typer.Option("--goal", help="Workflow goal to plan.")],
    input_path: Annotated[str | None, typer.Option("--input-path", help="Optional input PDF path.")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Plan a local-first agent PDF workflow."""
    _emit_result(
        run_workflow_plan(goal=goal, input_path=input_path),
        json_output=json_output,
    )


@workflow_app.command("run")
def workflow_run(
    workflow_path: Annotated[Path, typer.Argument(help="Workflow JSON file to execute.")],
    artifact_dir: Annotated[
        Path | None,
        typer.Option("--artifact-dir", help="Directory for auto-generated workflow artifacts."),
    ] = None,
    bindings: Annotated[
        list[str] | None,
        typer.Option("--binding", help="Runtime binding such as '<question>=What is this?'"),
    ] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Validate steps without executing.")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Run a local-first agent PDF workflow manifest."""
    workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
    if artifact_dir is not None:
        workflow["artifact_dir"] = str(artifact_dir)
    if bindings:
        workflow.setdefault("bindings", {}).update(_parse_bindings(bindings))
    _emit_result(
        run_workflow_run(workflow=workflow, dry_run=dry_run),
        json_output=json_output,
    )


@workflow_app.command("report")
def workflow_report(
    workflow_run_path: Annotated[Path, typer.Argument(help="Workflow run ToolResult JSON file.")],
    output_path: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Optional Markdown report path."),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Summarize a workflow run as structured JSON and optional Markdown."""
    workflow_run = json.loads(workflow_run_path.read_text(encoding="utf-8"))
    _emit_result(
        run_workflow_report(workflow_run=workflow_run, output_path=output_path),
        json_output=json_output,
    )


def _parse_bindings(bindings: list[str]) -> dict[str, str]:
    parsed = {}
    for item in bindings:
        key, separator, value = item.partition("=")
        if not separator or not key:
            raise typer.BadParameter("Bindings must use KEY=VALUE syntax.")
        parsed[key] = value
    return parsed


def _parse_csv_values(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _read_json_object(path: Path) -> dict[str, object]:
    payload = _read_json_value(path)
    if not isinstance(payload, dict):
        raise typer.BadParameter("--data must point to a JSON object.")
    return payload


def _read_json_object_list(path: Path, option_name: str) -> list[dict[str, object]]:
    payload = _read_json_value(path)
    if not isinstance(payload, list) or not all(isinstance(item, dict) for item in payload):
        raise typer.BadParameter(f"{option_name} must point to a JSON array of objects.")
    return list(payload)


def _read_json_value(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _parse_patch_operations(value: object) -> list[dict[str, Any]]:
    operations: object
    if isinstance(value, list):
        operations = value
    elif isinstance(value, dict) and isinstance(value.get("operations"), list):
        operations = value["operations"]
    elif isinstance(value, dict):
        operations = [value]
    else:
        raise typer.BadParameter("--operations must be a JSON array, a single operation object, or {'operations': [...]}.")
    if not all(isinstance(operation, dict) for operation in operations):
        raise typer.BadParameter("--operations entries must be JSON objects.")
    return list(operations)


def _parse_color_overrides(items: list[str]) -> dict[str, str]:
    colors = {}
    for item in items:
        key, separator, value = item.partition("=")
        if not separator or not key:
            raise typer.BadParameter("--color must use KEY=#RRGGBB syntax.")
        colors[key] = value
    return colors


def _parse_key_value_items(items: list[str]) -> dict[str, str]:
    values = {}
    for item in items:
        key, separator, value = item.partition("=")
        if not separator or not key:
            raise typer.BadParameter("metadata must use KEY=VALUE syntax.")
        values[key] = value
    return values


def _context_items_from_cli(
    files: list[Path],
    texts: list[str],
    links: list[str],
    item_json: list[str],
) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for text in texts:
        items.append({"text": text, "role": "brief"})
    for path in files:
        items.append({"path": str(path), "role": "source"})
    for link in links:
        items.append({"uri": link, "role": "link"})
    for value in item_json:
        items.extend(_parse_context_item_json(value))
    return items


def _single_context_item_from_cli(
    file: Path | None,
    text: str | None,
    link: str | None,
    item_json: str | None,
    role: str | None,
    label: str | None,
    item_type: str | None,
    transcript: str | None,
    duration_seconds: float | None,
) -> dict[str, object]:
    items = _context_items_from_cli(
        [file] if file is not None else [],
        [text] if text is not None else [],
        [link] if link is not None else [],
        [item_json] if item_json is not None else [],
    )
    if len(items) != 1:
        raise typer.BadParameter("context ingest requires exactly one of --file, --text, --link, or --item-json.")
    item = dict(items[0])
    if role is not None:
        item["role"] = role
    if label is not None:
        item["label"] = label
    if item_type is not None:
        item["type"] = item_type
    if transcript is not None:
        item["transcript"] = transcript
    if duration_seconds is not None:
        item["duration_seconds"] = duration_seconds
    return item


def _parse_context_item_json(value: str) -> list[dict[str, object]]:
    raw_value = value.strip()
    candidate_path = Path(raw_value)
    if candidate_path.exists():
        raw_value = candidate_path.read_text(encoding="utf-8")
    try:
        payload = json.loads(raw_value)
    except json.JSONDecodeError as exc:
        raise typer.BadParameter("--item-json must be a JSON object, JSON array, or path to one.") from exc
    if isinstance(payload, dict):
        return [payload]
    if isinstance(payload, list) and all(isinstance(item, dict) for item in payload):
        return payload
    raise typer.BadParameter("--item-json must decode to a JSON object or array of objects.")


def _emit_result(result: ToolResult, json_output: bool) -> None:
    if json_output:
        typer.echo(result.model_dump_json())
    else:
        typer.echo(result.model_dump_json(indent=2))
    if result.status == "failed":
        raise typer.Exit(1)


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
    """Serve local AgentPDF interfaces."""
    if mcp:
        from agentpdf.mcp.server import run_mcp_server

        run_mcp_server(transport=transport)  # type: ignore[arg-type]
        return
    if api:
        import uvicorn

        uvicorn.run("agentpdf.api.app:create_app", factory=True, host=host, port=port)
        return
    typer.echo("Choose --mcp for the local MCP server or --api for the future REST server.")
    raise typer.Exit(1)


if __name__ == "__main__":
    app()
