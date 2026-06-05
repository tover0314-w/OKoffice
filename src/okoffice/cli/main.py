import json
from pathlib import Path
from typing import Annotated, Any

import typer

from okoffice import __version__
from okoffice.office.manifest import load_office_tool_manifest
from okoffice.office.inspect import inspect_office_file
from okoffice.office.planner import plan_office_workflow
from okoffice.schemas.models import ToolResult
from okoffice.tools.registry import get_tool, load_tool_manifest
from okoffice.tools.runner import (
    run_add_margin,
    run_add_shape,
    run_underlay,
    run_agent_setup_claude_code,
    run_agent_setup_codex,
    run_agent_setup_kilo_code,
    run_agent_setup_openclaw,
    run_artifacts_export_bundle,
    run_artifacts_graph,
    run_artifacts_manifest,
    run_artifacts_source_map,
    run_artifacts_verify_bundle,
    run_authoring_plan,
    run_blank_page_check,
    run_booklet,
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
    run_compare_semantic_diff,
    run_compare_visual_diff,
    run_compare_version_report,
    run_create_markdown,
    run_create_text,
    run_create_agent,
    run_create_from_prompt,
    run_create_from_template_pack,
    run_create_html_package,
    run_plan_template_pack_creation,
    run_create_template_preview,
    run_create_template_packs,
    run_create_templates,
    run_context_packet_report,
    run_context_classify,
    run_context_code_snapshot,
    run_context_data_profile,
    run_context_web_capture,
    run_context_image_analyze,
    run_context_ingest,
    run_context_packet,
    run_validate_template_pack,
    run_evidence_cite_claims,
    run_evidence_coverage_report,
    run_evidence_map_sources,
    run_docx_to_pdf,
    run_extract_fonts,
    run_extract_images,
    run_extract_pages,
    run_extract_text,
    run_forms_create,
    run_forms_import_data,
    run_forms_validate,
    run_freehand_draw,
    run_html_to_pdf,
    run_image_to_pdf,
    run_inspect,
    run_inspect_health,
    run_inspect_pages,
    run_insert_blank_pages,
    run_metadata_read,
    run_metadata_page_info,
    run_metadata_remove,
    run_metadata_update,
    run_metadata_update_outline,
    run_merge,
    run_n_up,
    run_page_numbers,
    run_patch_apply,
    run_patch_plan,
    run_patch_preview,
    run_patch_verify,
    run_design_tokens,
    run_pages_write,
    run_pages_revise,
    run_parse_charts,
    run_parse_figures,
    run_parse_formulas,
    run_parse_lite,
    run_parse_references,
    run_pdf_to_docx,
    run_pdf_to_html,
    run_pdf_to_markdown,
    run_pdf_to_pptx,
    run_pdf_to_xlsx,
    run_pdf_to_json,
    run_pptx_to_pdf,
    run_rag_chat,
    run_rag_cite_answer,
    run_rag_export_report,
    run_rag_highlight_sources,
    run_rag_ingest,
    run_rag_query,
    run_rag_search,
    run_qa_visual_report,
    run_research_evidence_cards,
    run_research_plan,
    run_research_source_cards,
    run_remove_pages,
    run_render_html_package,
    run_remove_unused_objects,
    run_render,
    run_render_check,
    run_repair,
    run_reorder_pages,
    run_resize_pages,
    run_rotate_pages,
    run_page_count_check,
    run_ocr_despeckle,
    run_ocr,
    run_ocr_multilingual,
    run_ocr_remove_existing,
    run_ocr_scan_to_pdf,
    run_ocr_searchable_pdf,
    run_security_decrypt_authorized,
    run_security_encrypt,
    run_security_malware_scan,
    run_security_remove_metadata,
    run_security_protect,
    run_security_redact,
    run_security_sanitize,
    run_security_sign,
    run_security_unlock_authorized,
    run_security_verify_redaction,
    run_security_verify_signature,
    run_split,
    run_strikeout,
    run_storyboard_plan,
    run_subset_fonts,
    run_target_profiles,
    run_underline,
    run_validate_output,
    run_validate_pdfa,
    run_validate_target_profile,
    run_validation_redaction_check,
    run_validation_visual_diff,
    run_to_pdfa,
    run_url_to_pdf,
    run_watermark,
    run_workflow_plan,
    run_workflow_createpdf,
    run_workflow_research_deck,
    run_workflow_report,
    run_workflow_run,
    run_xlsx_to_pdf,
)

app = typer.Typer(help="OKoffice agent-native Office infra CLI")
office_app = typer.Typer(help="Plan OKoffice cross-format Word, Excel, PPT, and PDF workflows.")
agent_app = typer.Typer(help="Generate local agent runtime configs.")
agent_setup_app = typer.Typer(help="Set up specific agent runtimes.")
tools_app = typer.Typer(help="Discover compatibility PDF tools.")
metadata_app = typer.Typer(help="Read and write PDF metadata.")
security_app = typer.Typer(help="Run local PDF security and privacy tools.")
forms_app = typer.Typer(help="Create, import, and validate PDF forms.")
ocr_app = typer.Typer(help="Local scan and OCR preparation tools.")
create_app = typer.Typer(help="Create PDFs from local inputs.")
context_app = typer.Typer(help="Build agent context packets.")
compose_app = typer.Typer(help="Compose target PDFs from context packets.")
target_app = typer.Typer(help="List and validate target PDF profiles.")
evidence_app = typer.Typer(help="Audit source evidence and coverage.")
patch_app = typer.Typer(help="Plan, preview, apply, and verify PDF patch transactions.")
artifacts_app = typer.Typer(help="Export and inspect local artifact lineage.")
compare_app = typer.Typer(help="Compare local PDF versions.")
rag_app = typer.Typer(help="Local document retrieval tools.")
workflow_app = typer.Typer(help="Plan local agent PDF workflows.")
authoring_app = typer.Typer(help="Plan authoring routes before PDF creation.")
research_app = typer.Typer(help="Plan and normalize local authoring research inputs.")
design_app = typer.Typer(help="Resolve safe local authoring design tokens.")
storyboard_app = typer.Typer(help="Plan page-by-page deck and report structures.")
pages_app = typer.Typer(help="Write page JSON from storyboards and evidence.")
qa_app = typer.Typer(help="Run authoring and visual QA reports.")
app.add_typer(office_app, name="office")
app.add_typer(agent_app, name="agent")
agent_app.add_typer(agent_setup_app, name="setup")
app.add_typer(tools_app, name="tools")
app.add_typer(metadata_app, name="metadata")
app.add_typer(security_app, name="security")
app.add_typer(forms_app, name="forms")
app.add_typer(ocr_app, name="ocr")
app.add_typer(create_app, name="create")
app.add_typer(context_app, name="context")
app.add_typer(compose_app, name="compose")
app.add_typer(target_app, name="target")
app.add_typer(evidence_app, name="evidence")
app.add_typer(patch_app, name="patch")
app.add_typer(artifacts_app, name="artifacts")
app.add_typer(compare_app, name="compare")
app.add_typer(rag_app, name="rag")
app.add_typer(workflow_app, name="workflow")
app.add_typer(authoring_app, name="authoring")
app.add_typer(research_app, name="research")
app.add_typer(design_app, name="design")
app.add_typer(storyboard_app, name="storyboard")
app.add_typer(pages_app, name="pages")
app.add_typer(qa_app, name="qa")


@app.callback()
def main() -> None:
    """Local-first Office infrastructure for AI agents."""


@app.command()
def version() -> None:
    """Print the OKoffice compatibility package version."""
    typer.echo(f"okoffice {__version__} (compatibility package: agentpdf)")


@office_app.command("manifest")
def office_manifest(
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Print the target OKoffice tool manifest."""
    manifest = load_office_tool_manifest()
    if json_output:
        typer.echo(manifest.model_dump_json())
        return
    typer.echo(manifest.model_dump_json(indent=2))


@office_app.command("plan")
def office_plan(
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
    """Plan a cross-format OKoffice workflow without mutating files."""
    _emit_result(
        plan_office_workflow(
            goal=goal,
            input_paths=input_paths or [],
            output_paths=output_paths or [],
        ),
        json_output=json_output,
    )


@office_app.command("inspect")
def office_inspect(
    path: Annotated[Path, typer.Argument(help="Office artifact path to inspect.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Inspect a local Office artifact without mutating it."""
    _emit_result(inspect_office_file(path), json_output=json_output)


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
    """Generate an OpenClaw-style MCP config for local okoffice tools."""
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


@tools_app.command("list")
def tools_list(
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """List the public OKoffice tool manifest."""
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


@app.command("inspect-health")
def inspect_health(
    input_path: Annotated[Path, typer.Argument(help="PDF file to inspect for health and active-content risks.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Inspect PDF parseability, trailer markers, page geometry, and static risk markers."""
    _emit_result(run_inspect_health(input_path), json_output=json_output)


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


@app.command("n-up")
def n_up(
    input_path: Annotated[Path, typer.Argument(help="Input PDF file.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output PDF path.")],
    pages: Annotated[str, typer.Option("--pages", help="Page range such as all or 1-4.")] = "all",
    per_sheet: Annotated[int, typer.Option("--per-sheet", help="Pages per output sheet: 2 or 4.")] = 2,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Place multiple source pages on one output PDF page."""
    _emit_result(
        run_n_up(input_path, output_path=output_path, pages=pages, per_sheet=per_sheet),
        json_output=json_output,
    )


@app.command("booklet")
def booklet(
    input_path: Annotated[Path, typer.Argument(help="Input PDF file.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output PDF path.")],
    pages: Annotated[str, typer.Option("--pages", help="Page range such as all or 1-8.")] = "all",
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Create a local booklet imposition PDF."""
    _emit_result(run_booklet(input_path, output_path=output_path, pages=pages), json_output=json_output)


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


@app.command("remove-unused-objects")
def remove_unused_objects(
    input_path: Annotated[Path, typer.Argument(help="Input PDF file.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output PDF path.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Rewrite the reachable page tree into a new optimized PDF."""
    _emit_result(
        run_remove_unused_objects(input_path, output_path=output_path),
        json_output=json_output,
    )


@app.command("validate-pdfa")
def validate_pdfa(
    input_path: Annotated[Path, typer.Argument(help="Input PDF file.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Run local heuristic PDF/A validation checks."""
    _emit_result(run_validate_pdfa(input_path), json_output=json_output)


@app.command("subset-fonts")
def subset_fonts(
    input_path: Annotated[Path, typer.Argument(help="Input PDF file.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output PDF path.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Rewrite a PDF and return local font-subset audit evidence."""
    _emit_result(run_subset_fonts(input_path, output_path=output_path), json_output=json_output)


@app.command("to-pdfa")
def to_pdfa(
    input_path: Annotated[Path, typer.Argument(help="Input PDF file.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output PDF path.")],
    profile: Annotated[str, typer.Option("--profile", help="Requested PDF/A profile.")] = "PDF/A-2B",
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Create a best-effort local PDF/A-tagged copy and validation report."""
    _emit_result(
        run_to_pdfa(input_path, output_path=output_path, profile=profile),
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


@app.command("html-to-pdf")
def html_to_pdf_cmd(
    input_path: Annotated[Path, typer.Argument(help="Input HTML file.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output PDF path.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Convert a local HTML file to a text-approximated PDF."""
    _emit_result(run_html_to_pdf(input_path, output_path=output_path), json_output=json_output)


@app.command("render-html-package")
def render_html_package_cmd(
    package_path: Annotated[Path, typer.Argument(help="HTML package manifest or HTML file.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output PDF path.")],
    renderer_backend: Annotated[
        str,
        typer.Option(
            "--renderer-backend",
            "--backend",
            help="Renderer backend: auto, local_html_package_fallback, or browser_chromium.",
        ),
    ] = "auto",
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Validate and render an OKoffice HTML package to PDF."""
    _emit_result(
        run_render_html_package(
            package_path,
            output_path=output_path,
            renderer_backend=renderer_backend,
        ),
        json_output=json_output,
    )


@app.command("url-to-pdf")
def url_to_pdf_cmd(
    url: Annotated[str, typer.Argument(help="HTTP(S) URL to convert.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output PDF path.")],
    allow_private_hosts: Annotated[
        bool,
        typer.Option("--allow-private-hosts", help="Allow private/loopback hosts."),
    ] = False,
    allow_file_urls: Annotated[bool, typer.Option("--allow-file-urls", help="Allow file:// URLs.")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Fetch a URL with safety checks and convert HTML text to PDF."""
    _emit_result(
        run_url_to_pdf(
            url,
            output_path=output_path,
            allow_private_hosts=allow_private_hosts,
            allow_file_urls=allow_file_urls,
        ),
        json_output=json_output,
    )


@app.command("docx-to-pdf")
def docx_to_pdf_cmd(
    input_path: Annotated[Path, typer.Argument(help="Input DOCX file.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output PDF path.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Convert DOCX text to a local PDF."""
    _emit_result(run_docx_to_pdf(input_path, output_path=output_path), json_output=json_output)


@app.command("pptx-to-pdf")
def pptx_to_pdf_cmd(
    input_path: Annotated[Path, typer.Argument(help="Input PPTX file.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output PDF path.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Convert PPTX slide text to a local PDF."""
    _emit_result(run_pptx_to_pdf(input_path, output_path=output_path), json_output=json_output)


@app.command("xlsx-to-pdf")
def xlsx_to_pdf_cmd(
    input_path: Annotated[Path, typer.Argument(help="Input XLSX file.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output PDF path.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Convert the first XLSX sheet to a local PDF."""
    _emit_result(run_xlsx_to_pdf(input_path, output_path=output_path), json_output=json_output)


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


@app.command("add-shape")
def add_shape(
    input_path: Annotated[Path, typer.Argument(help="Input PDF file.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output PDF path.")],
    shape: Annotated[str, typer.Option("--shape", help="rectangle, line, circle, or ellipse.")],
    page: Annotated[int, typer.Option("--page", help="1-based page number.")],
    x: Annotated[float, typer.Option("--x", help="Lower-left x coordinate.")],
    y: Annotated[float, typer.Option("--y", help="Lower-left y coordinate.")],
    width: Annotated[float, typer.Option("--width", help="Shape width or line delta x.")],
    height: Annotated[float, typer.Option("--height", help="Shape height or line delta y.")],
    stroke_color: Annotated[str, typer.Option("--stroke-color", help="Stroke color hex.")] = "#2563eb",
    fill_color: Annotated[str | None, typer.Option("--fill-color", help="Optional fill color hex.")] = None,
    line_width: Annotated[float, typer.Option("--line-width", help="Stroke width.")] = 1.5,
    opacity: Annotated[float, typer.Option("--opacity", help="Opacity from 0 to 1.")] = 1.0,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Add a vector shape overlay to a PDF page."""
    _emit_result(
        run_add_shape(
            input_path,
            output_path=output_path,
            shape=shape,
            page=page,
            x=x,
            y=y,
            width=width,
            height=height,
            stroke_color=stroke_color,
            fill_color=fill_color,
            line_width=line_width,
            opacity=opacity,
        ),
        json_output=json_output,
    )


@app.command("underline")
def underline(
    input_path: Annotated[Path, typer.Argument(help="Input PDF file.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output PDF path.")],
    page: Annotated[int, typer.Option("--page", help="1-based page number.")],
    bbox: Annotated[str, typer.Option("--bbox", help="x0,y0,x1,y1 coordinates.")],
    color: Annotated[str, typer.Option("--color", help="Line color hex.")] = "#2563eb",
    line_width: Annotated[float, typer.Option("--line-width", help="Line width.")] = 1.0,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Underline a coordinate span."""
    _emit_result(
        run_underline(
            input_path,
            output_path=output_path,
            page=page,
            bbox=_parse_float_list(bbox, expected=4, label="bbox"),
            color=color,
            line_width=line_width,
        ),
        json_output=json_output,
    )


@app.command("strikeout")
def strikeout(
    input_path: Annotated[Path, typer.Argument(help="Input PDF file.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output PDF path.")],
    page: Annotated[int, typer.Option("--page", help="1-based page number.")],
    bbox: Annotated[str, typer.Option("--bbox", help="x0,y0,x1,y1 coordinates.")],
    color: Annotated[str, typer.Option("--color", help="Line color hex.")] = "#dc2626",
    line_width: Annotated[float, typer.Option("--line-width", help="Line width.")] = 1.0,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Strike out a coordinate span."""
    _emit_result(
        run_strikeout(
            input_path,
            output_path=output_path,
            page=page,
            bbox=_parse_float_list(bbox, expected=4, label="bbox"),
            color=color,
            line_width=line_width,
        ),
        json_output=json_output,
    )


@app.command("freehand-draw")
def freehand_draw(
    input_path: Annotated[Path, typer.Argument(help="Input PDF file.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output PDF path.")],
    page: Annotated[int, typer.Option("--page", help="1-based page number.")],
    points: Annotated[str, typer.Option("--points", help="JSON array like [[72,680],[120,700]].")],
    stroke_color: Annotated[str, typer.Option("--stroke-color", help="Stroke color hex.")] = "#2563eb",
    line_width: Annotated[float, typer.Option("--line-width", help="Line width.")] = 1.5,
    opacity: Annotated[float, typer.Option("--opacity", help="Opacity from 0 to 1.")] = 1.0,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Add a freehand drawing path to a PDF page."""
    _emit_result(
        run_freehand_draw(
            input_path,
            output_path=output_path,
            page=page,
            points=_parse_points_json(points),
            stroke_color=stroke_color,
            line_width=line_width,
            opacity=opacity,
        ),
        json_output=json_output,
    )


@app.command("resize-pages")
def resize_pages(
    input_path: Annotated[Path, typer.Argument(help="Input PDF file.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output PDF path.")],
    width: Annotated[float, typer.Option("--width", help="Target page width in points.")],
    height: Annotated[float, typer.Option("--height", help="Target page height in points.")],
    pages: Annotated[str, typer.Option("--pages", help="Page range such as all or 1-3.")] = "all",
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Resize selected pages and scale content to fit."""
    _emit_result(
        run_resize_pages(input_path, output_path=output_path, width=width, height=height, pages=pages),
        json_output=json_output,
    )


@app.command("add-margin")
def add_margin(
    input_path: Annotated[Path, typer.Argument(help="Input PDF file.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output PDF path.")],
    margin: Annotated[float, typer.Option("--margin", help="Default margin in points.")] = 0,
    pages: Annotated[str, typer.Option("--pages", help="Page range such as all or 1-3.")] = "all",
    top: Annotated[float | None, typer.Option("--top", help="Top margin override.")] = None,
    right: Annotated[float | None, typer.Option("--right", help="Right margin override.")] = None,
    bottom: Annotated[float | None, typer.Option("--bottom", help="Bottom margin override.")] = None,
    left: Annotated[float | None, typer.Option("--left", help="Left margin override.")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Add page margins by placing content on larger pages."""
    _emit_result(
        run_add_margin(
            input_path,
            output_path=output_path,
            margin=margin,
            pages=pages,
            top=top,
            right=right,
            bottom=bottom,
            left=left,
        ),
        json_output=json_output,
    )


@app.command("underlay")
def underlay(
    input_path: Annotated[Path, typer.Argument(help="Input PDF file.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output PDF path.")],
    text: Annotated[str, typer.Option("--text", help="Underlay text.")],
    pages: Annotated[str, typer.Option("--pages", help="Page range such as all or 1-3.")] = "all",
    font_size: Annotated[int, typer.Option("--font-size", help="Underlay font size.")] = 72,
    opacity: Annotated[float, typer.Option("--opacity", help="Opacity from 0 to 1.")] = 0.12,
    angle: Annotated[int, typer.Option("--angle", help="Rotation angle.")] = 45,
    color: Annotated[str, typer.Option("--color", help="Text color hex.")] = "#64748b",
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Add text below existing page content."""
    _emit_result(
        run_underlay(
            input_path,
            output_path=output_path,
            text=text,
            pages=pages,
            font_size=font_size,
            opacity=opacity,
            angle=angle,
            color=color,
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
    renderer: Annotated[str, typer.Option("--renderer", help="Renderer mode: markdown or html.")] = "markdown",
    html_output_path: Annotated[
        Path | None,
        typer.Option("--html-output", help="Optional HTML package output path when --renderer html is used."),
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
            renderer=renderer,
            html_output_path=html_output_path,
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
    renderer: Annotated[str, typer.Option("--renderer", help="Renderer mode: markdown or html.")] = "markdown",
    html_output_path: Annotated[
        Path | None,
        typer.Option("--html-output", help="Optional HTML package output path when --renderer html is used."),
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
            renderer=renderer,
            html_output_path=html_output_path,
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
    transcript_path: Annotated[
        Path | None,
        typer.Option("--transcript-path", help="Provided audio/video transcript sidecar file."),
    ] = None,
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
                transcript_path=transcript_path,
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


@context_app.command("web-capture")
def context_web_capture(
    url: Annotated[str, typer.Argument(help="HTTP or HTTPS URL to fetch as web context.")],
    output_path: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Optional output context item JSON path."),
    ] = None,
    label: Annotated[str | None, typer.Option("--label", help="Context item label.")] = None,
    role: Annotated[str, typer.Option("--role", help="Context item role.")] = "citation",
    context_item_id: Annotated[
        str | None,
        typer.Option("--context-item-id", help="Stable context item/source ref id."),
    ] = None,
    max_bytes: Annotated[int, typer.Option("--max-bytes", help="Maximum response bytes to keep.")] = 1_000_000,
    timeout_seconds: Annotated[
        float,
        typer.Option("--timeout-seconds", help="HTTP request timeout in seconds."),
    ] = 10,
    allow_private_hosts: Annotated[
        bool,
        typer.Option("--allow-private-hosts", help="Allow local/private hosts. Disabled by default."),
    ] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Fetch a web page into a context item with SSRF-safe local evidence."""
    _emit_result(
        run_context_web_capture(
            url=url,
            output_path=output_path,
            label=label,
            role=role,
            context_item_id=context_item_id,
            max_bytes=max_bytes,
            timeout_seconds=timeout_seconds,
            allow_private_hosts=allow_private_hosts,
        ),
        json_output=json_output,
    )


@context_app.command("image-analyze")
def context_image_analyze(
    input_path: Annotated[Path, typer.Argument(help="Local image file to analyze.")],
    languages: Annotated[
        list[str] | None,
        typer.Option("--language", help="OCR language code. Can be repeated."),
    ] = None,
    run_ocr: Annotated[
        bool,
        typer.Option("--run-ocr/--skip-ocr", help="Run local OCR when available."),
    ] = True,
    engine: Annotated[str, typer.Option("--engine", help="Local OCR engine executable.")] = "tesseract",
    psm: Annotated[int, typer.Option("--psm", help="Tesseract page segmentation mode.")] = 6,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Analyze a local image with metadata and optional OCR evidence."""
    _emit_result(
        run_context_image_analyze(
            input_path,
            languages=languages,
            run_ocr=run_ocr,
            engine=engine,
            psm=psm,
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
    renderer: Annotated[str, typer.Option("--renderer", help="Renderer mode: markdown or html.")] = "markdown",
    html_output_path: Annotated[
        Path | None,
        typer.Option("--html-output", help="Optional HTML package output path when renderer=html."),
    ] = None,
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
            renderer=renderer,
            html_output_path=html_output_path,
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


@evidence_app.command("cite-claims")
def evidence_cite_claims(
    claims_path: Annotated[Path, typer.Argument(help="Claims JSON array path.")],
    composition_path: Annotated[
        Path | None,
        typer.Option("--composition", help="Optional composition JSON artifact path."),
    ] = None,
    source_map_path: Annotated[
        Path | None,
        typer.Option("--source-map", help="Optional source-map report or source_map JSON path."),
    ] = None,
    context_packet_path: Annotated[
        Path | None,
        typer.Option("--context-packet", help="Optional Context Packet JSON for source evidence enrichment."),
    ] = None,
    output_path: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Optional output citation report JSON path."),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Return local citations for claims using source refs and source-map evidence."""
    _emit_result(
        run_evidence_cite_claims(
            claims=_read_json_object_list(claims_path, "claims"),
            composition=composition_path,
            source_map=source_map_path,
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
    artifact_graph_path: Annotated[
        Path | None,
        typer.Option("--artifact-graph", help="Optional artifact graph JSON artifact for HTML layer refs."),
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
            artifact_graph_path=artifact_graph_path,
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


@artifacts_app.command("manifest")
def artifacts_manifest(
    artifact_paths: Annotated[
        list[Path] | None,
        typer.Option("--file", help="Artifact file to include in the manifest."),
    ] = None,
    output_path: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Optional artifact manifest JSON output path."),
    ] = None,
    title: Annotated[str | None, typer.Option("--title", help="Optional manifest title.")] = None,
    metadata_items: Annotated[
        list[str] | None,
        typer.Option("--metadata", help="Metadata key=value pair to include."),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Create a local artifact manifest with checksums, source refs, and HTML/context evidence."""
    _emit_result(
        run_artifacts_manifest(
            artifact_paths=artifact_paths or [],
            output_path=output_path,
            title=title,
            metadata=_parse_key_value_items(metadata_items or []),
        ),
        json_output=json_output,
    )


@artifacts_app.command("graph")
def artifacts_graph(
    artifact_manifest_path: Annotated[
        Path | None,
        typer.Option("--manifest", help="Artifact manifest JSON path to turn into a lineage graph."),
    ] = None,
    artifact_paths: Annotated[
        list[Path] | None,
        typer.Option("--file", help="Artifact file to include when building a manifest inline."),
    ] = None,
    output_path: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Optional artifact graph JSON output path."),
    ] = None,
    title: Annotated[str | None, typer.Option("--title", help="Optional graph title.")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Create a local artifact lineage graph with source-ref and HTML/context evidence."""
    _emit_result(
        run_artifacts_graph(
            artifact_manifest_path=artifact_manifest_path,
            artifact_paths=artifact_paths or [],
            output_path=output_path,
            title=title,
        ),
        json_output=json_output,
    )


@artifacts_app.command("source-map")
def artifacts_source_map(
    composition_path: Annotated[
        Path | None,
        typer.Option("--composition", help="Composition JSON path containing composition_ir and source_map."),
    ] = None,
    source_map_path: Annotated[
        Path | None,
        typer.Option("--source-map", help="Existing source-map JSON path to normalize."),
    ] = None,
    context_packet_path: Annotated[
        Path | None,
        typer.Option("--context-packet", help="Optional Context Packet JSON path for source-ref enrichment."),
    ] = None,
    artifact_manifest_path: Annotated[
        Path | None,
        typer.Option("--manifest", help="Optional artifact manifest JSON path for generated PDF artifacts."),
    ] = None,
    artifact_paths: Annotated[
        list[Path] | None,
        typer.Option("--file", help="Artifact file to include when building a manifest inline."),
    ] = None,
    output_path: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Optional artifact source-map JSON output path."),
    ] = None,
    title: Annotated[str | None, typer.Option("--title", help="Optional source-map title.")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Create an artifact-focused source map index for generated PDF blocks and sources."""
    _emit_result(
        run_artifacts_source_map(
            composition_path=composition_path,
            source_map_path=source_map_path,
            context_packet_path=context_packet_path,
            artifact_manifest_path=artifact_manifest_path,
            artifact_paths=artifact_paths or [],
            output_path=output_path,
            title=title,
        ),
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
    bundle_path: Annotated[Path, typer.Argument(help="Input okoffice-bundle.zip path.")],
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


@app.command("extract-fonts")
def extract_fonts(
    input_path: Annotated[Path, typer.Argument(help="Input PDF file.")],
    pages: Annotated[str, typer.Option("--pages", help="Page range such as all or 1-3.")] = "all",
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """List fonts referenced by selected PDF pages."""
    _emit_result(run_extract_fonts(input_path, pages=pages), json_output=json_output)


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


@app.command("pdf-to-html")
def pdf_to_html_cmd(
    input_path: Annotated[Path, typer.Argument(help="Input PDF file.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output HTML path.")],
    pages: Annotated[str, typer.Option("--pages", help="Page range such as all or 1-3.")] = "all",
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Export PDF text to a simple HTML document."""
    _emit_result(run_pdf_to_html(input_path, output_path=output_path, pages=pages), json_output=json_output)


@app.command("pdf-to-docx")
def pdf_to_docx_cmd(
    input_path: Annotated[Path, typer.Argument(help="Input PDF file.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output DOCX path.")],
    pages: Annotated[str, typer.Option("--pages", help="Page range such as all or 1-3.")] = "all",
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Export PDF text to a minimal DOCX package."""
    _emit_result(run_pdf_to_docx(input_path, output_path=output_path, pages=pages), json_output=json_output)


@app.command("pdf-to-pptx")
def pdf_to_pptx_cmd(
    input_path: Annotated[Path, typer.Argument(help="Input PDF file.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output PPTX path.")],
    pages: Annotated[str, typer.Option("--pages", help="Page range such as all or 1-3.")] = "all",
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Export each PDF page as a simple text slide."""
    _emit_result(run_pdf_to_pptx(input_path, output_path=output_path, pages=pages), json_output=json_output)


@app.command("pdf-to-xlsx")
def pdf_to_xlsx_cmd(
    input_path: Annotated[Path, typer.Argument(help="Input PDF file.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output XLSX path.")],
    pages: Annotated[str, typer.Option("--pages", help="Page range such as all or 1-3.")] = "all",
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Export PDF page text rows to a minimal XLSX workbook."""
    _emit_result(run_pdf_to_xlsx(input_path, output_path=output_path, pages=pages), json_output=json_output)


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


@metadata_app.command("update-outline")
def metadata_update_outline(
    input_path: Annotated[Path, typer.Argument(help="Input PDF file.")],
    outline_path: Annotated[Path, typer.Argument(help="Outline JSON array path.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output PDF path.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Write PDF outline/bookmarks from a JSON array."""
    _emit_result(
        run_metadata_update_outline(
            input_path,
            outline=_read_json_object_list(outline_path, "outline"),
            output_path=output_path,
        ),
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


@security_app.command("protect")
def security_protect(
    input_path: Annotated[Path, typer.Argument(help="Input PDF file.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output encrypted PDF path.")],
    password: Annotated[str, typer.Option("--password", help="User password.")],
    owner_password: Annotated[str | None, typer.Option("--owner-password", help="Owner password.")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Protect a PDF with password encryption."""
    _emit_result(
        run_security_protect(
            input_path,
            output_path=output_path,
            password=password,
            owner_password=owner_password,
        ),
        json_output=json_output,
    )


@security_app.command("encrypt")
def security_encrypt(
    input_path: Annotated[Path, typer.Argument(help="Input PDF file.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output encrypted PDF path.")],
    password: Annotated[str, typer.Option("--password", help="User password.")],
    owner_password: Annotated[str | None, typer.Option("--owner-password", help="Owner password.")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Encrypt a PDF with a password."""
    _emit_result(
        run_security_encrypt(
            input_path,
            output_path=output_path,
            password=password,
            owner_password=owner_password,
        ),
        json_output=json_output,
    )


@security_app.command("unlock-authorized")
def security_unlock_authorized(
    input_path: Annotated[Path, typer.Argument(help="Input encrypted PDF file.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output unlocked PDF path.")],
    password: Annotated[str, typer.Option("--password", help="Authorized password.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Unlock a PDF only with a supplied authorized password."""
    _emit_result(
        run_security_unlock_authorized(input_path, output_path=output_path, password=password),
        json_output=json_output,
    )


@security_app.command("decrypt-authorized")
def security_decrypt_authorized(
    input_path: Annotated[Path, typer.Argument(help="Input encrypted PDF file.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output decrypted PDF path.")],
    password: Annotated[str, typer.Option("--password", help="Authorized password.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Decrypt a PDF only with a supplied authorized password."""
    _emit_result(
        run_security_decrypt_authorized(input_path, output_path=output_path, password=password),
        json_output=json_output,
    )


@security_app.command("sign")
def security_sign(
    input_path: Annotated[Path, typer.Argument(help="Input PDF file.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output signature JSON path.")],
    secret: Annotated[str | None, typer.Option("--secret", help="Optional HMAC secret.")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Create a detached local integrity signature manifest."""
    _emit_result(
        run_security_sign(input_path, output_path=output_path, secret=secret),
        json_output=json_output,
    )


@security_app.command("verify-signature")
def security_verify_signature(
    input_path: Annotated[Path, typer.Argument(help="Input PDF file.")],
    signature_path: Annotated[Path, typer.Argument(help="Detached signature JSON path.")],
    secret: Annotated[str | None, typer.Option("--secret", help="Optional HMAC secret.")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Verify a detached local integrity signature manifest."""
    _emit_result(
        run_security_verify_signature(input_path, signature_path=signature_path, secret=secret),
        json_output=json_output,
    )


@security_app.command("malware-scan")
def security_malware_scan(
    input_path: Annotated[Path, typer.Argument(help="Input PDF file.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Run a local static PDF risk marker scan."""
    _emit_result(run_security_malware_scan(input_path), json_output=json_output)


@security_app.command("sanitize")
def security_sanitize(
    input_path: Annotated[Path, typer.Argument(help="Input PDF file.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output sanitized PDF path.")],
    remove_metadata: Annotated[
        bool,
        typer.Option("--remove-metadata/--keep-metadata", help="Remove document metadata while rewriting."),
    ] = True,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Rewrite a PDF while removing known active-content structures and metadata."""
    _emit_result(
        run_security_sanitize(input_path, output_path=output_path, remove_metadata=remove_metadata),
        json_output=json_output,
    )


@security_app.command("redact")
def security_redact(
    input_path: Annotated[Path, typer.Argument(help="Input PDF file.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output redacted PDF path.")],
    regions: Annotated[
        list[str],
        typer.Option("--region", help="Redaction region JSON object. Can be repeated."),
    ],
    fill_color: Annotated[str, typer.Option("--fill-color", help="Mask fill color.")] = "#000000",
    render_scale: Annotated[float, typer.Option("--render-scale", help="Raster render scale.")] = 2.0,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Redact explicit bbox regions by creating an image-only PDF."""
    _emit_result(
        run_security_redact(
            input_path,
            output_path=output_path,
            regions=[_parse_json_object_value(region, "--region") for region in regions],
            fill_color=fill_color,
            render_scale=render_scale,
        ),
        json_output=json_output,
    )


@security_app.command("verify-redaction")
def security_verify_redaction(
    input_path: Annotated[Path, typer.Argument(help="Input redacted PDF file.")],
    search_terms: Annotated[
        list[str] | None,
        typer.Option("--search-term", help="Sensitive term that must be absent. Can be repeated."),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Verify supplied sensitive terms are absent after redaction."""
    _emit_result(
        run_security_verify_redaction(input_path, search_terms=search_terms),
        json_output=json_output,
    )


@forms_app.command("create")
def forms_create(
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output form PDF path.")],
    fields: Annotated[
        list[str],
        typer.Option("--field", help="Form field JSON object or path. Can be repeated."),
    ],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Create a local PDF with text form fields."""
    _emit_result(
        run_forms_create(
            output_path=output_path,
            fields=[_parse_json_object_value(field, "--field") for field in fields],
        ),
        json_output=json_output,
    )


@forms_app.command("import-data")
def forms_import_data(
    input_path: Annotated[Path, typer.Argument(help="Input form PDF.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output filled PDF path.")],
    data: Annotated[str, typer.Option("--data", help="Field data JSON object or path.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Import local JSON form data into a PDF form."""
    _emit_result(
        run_forms_import_data(
            input_path,
            data=_parse_json_object_value(data, "--data"),
            output_path=output_path,
        ),
        json_output=json_output,
    )


@forms_app.command("validate")
def forms_validate(
    input_path: Annotated[Path, typer.Argument(help="Input form PDF.")],
    required_fields: Annotated[
        list[str] | None,
        typer.Option("--required-field", help="Required field name. Can be repeated."),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Validate required PDF form fields."""
    _emit_result(
        run_forms_validate(input_path, required_fields=required_fields),
        json_output=json_output,
    )


@ocr_app.command("scan-to-pdf")
def ocr_scan_to_pdf(
    image_paths: Annotated[list[Path], typer.Argument(help="Input scan image files.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output PDF path.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Create an image-only PDF from local scan images."""
    _emit_result(run_ocr_scan_to_pdf(image_paths, output_path=output_path), json_output=json_output)


@ocr_app.command("ocr")
def ocr_extract(
    input_path: Annotated[Path, typer.Argument(help="Input PDF or image file.")],
    pages: Annotated[str, typer.Option("--pages", help="Page range for PDF input.")] = "all",
    languages: Annotated[
        list[str] | None,
        typer.Option("--language", help="OCR language code. Can be repeated."),
    ] = None,
    dpi: Annotated[int, typer.Option("--dpi", help="PDF render DPI before OCR.")] = 200,
    engine: Annotated[str, typer.Option("--engine", help="Local OCR engine executable.")] = "tesseract",
    psm: Annotated[int, typer.Option("--psm", help="Tesseract page segmentation mode.")] = 6,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Run local OCR and return text regions with bboxes."""
    _emit_result(
        run_ocr(
            input_path,
            pages=pages,
            languages=languages,
            dpi=dpi,
            engine=engine,
            psm=psm,
        ),
        json_output=json_output,
    )


@ocr_app.command("searchable-pdf")
def ocr_searchable_pdf(
    input_path: Annotated[Path, typer.Argument(help="Input PDF file.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output searchable PDF path.")],
    pages: Annotated[str, typer.Option("--pages", help="Page range for OCR.")] = "all",
    languages: Annotated[
        list[str] | None,
        typer.Option("--language", help="OCR language code. Can be repeated."),
    ] = None,
    dpi: Annotated[int, typer.Option("--dpi", help="PDF render DPI before OCR.")] = 200,
    engine: Annotated[str, typer.Option("--engine", help="Local OCR engine executable.")] = "tesseract",
    psm: Annotated[int, typer.Option("--psm", help="Tesseract page segmentation mode.")] = 6,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Add a local OCR text layer to a PDF."""
    _emit_result(
        run_ocr_searchable_pdf(
            input_path,
            output_path=output_path,
            pages=pages,
            languages=languages,
            dpi=dpi,
            engine=engine,
            psm=psm,
        ),
        json_output=json_output,
    )


@ocr_app.command("despeckle")
def ocr_despeckle(
    input_path: Annotated[Path, typer.Argument(help="Input PDF file.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output PDF path.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Run local scan despeckle preparation."""
    _emit_result(run_ocr_despeckle(input_path, output_path=output_path), json_output=json_output)


@ocr_app.command("remove-existing")
def ocr_remove_existing(
    input_path: Annotated[Path, typer.Argument(help="Input PDF file.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output PDF path.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Rewrite a PDF while removing existing OCR-layer metadata where possible."""
    _emit_result(run_ocr_remove_existing(input_path, output_path=output_path), json_output=json_output)


@ocr_app.command("multilingual")
def ocr_multilingual(
    input_path: Annotated[Path, typer.Argument(help="Input PDF file.")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output PDF path.")],
    languages: Annotated[
        list[str] | None,
        typer.Option("--language", help="OCR language code. Can be repeated."),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Record a local multilingual OCR request and rewrite the PDF artifact."""
    _emit_result(
        run_ocr_multilingual(input_path, output_path=output_path, languages=languages),
        json_output=json_output,
    )


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


@app.command("visual-diff")
def validation_visual_diff(
    before_path: Annotated[Path, typer.Argument(help="Earlier PDF file.")],
    after_path: Annotated[Path, typer.Argument(help="Later PDF file.")],
    pages: Annotated[str, typer.Option("--pages", help="Page range such as all or 1-3.")] = "all",
    max_difference_ratio: Annotated[
        float,
        typer.Option("--max-difference-ratio", help="Maximum allowed changed pixel ratio per page."),
    ] = 0.001,
    render_scale: Annotated[
        float,
        typer.Option("--render-scale", help="PDF render scale used for local pixel comparison."),
    ] = 0.5,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Validate before/after PDFs with rendered page visual diff evidence."""
    _emit_result(
        run_validation_visual_diff(
            before_path,
            after_path,
            pages=pages,
            max_difference_ratio=max_difference_ratio,
            render_scale=render_scale,
        ),
        json_output=json_output,
    )


@app.command("redaction-check")
def validation_redaction_check(
    input_path: Annotated[Path, typer.Argument(help="Input redacted PDF file.")],
    search_terms: Annotated[
        list[str] | None,
        typer.Option("--search-term", help="Sensitive term that must be absent. Can be repeated."),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Run validation-grade redaction leak checks for supplied terms."""
    _emit_result(
        run_validation_redaction_check(input_path, search_terms=search_terms),
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


@compare_app.command("semantic-diff")
def semantic_diff(
    before_path: Annotated[Path, typer.Argument(help="Earlier PDF file.")],
    after_path: Annotated[Path, typer.Argument(help="Later PDF file.")],
    pages: Annotated[str, typer.Option("--pages", help="Page range such as all or 1-3.")] = "all",
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Compare local PDF text layers with heuristic semantic evidence."""
    _emit_result(
        run_compare_semantic_diff(before_path, after_path, pages=pages),
        json_output=json_output,
    )


@compare_app.command("visual-diff")
def compare_visual_diff(
    before_path: Annotated[Path, typer.Argument(help="Earlier PDF file.")],
    after_path: Annotated[Path, typer.Argument(help="Later PDF file.")],
    pages: Annotated[str, typer.Option("--pages", help="Page range such as all or 1-3.")] = "all",
    max_difference_ratio: Annotated[
        float,
        typer.Option("--max-difference-ratio", help="Difference ratio threshold for changed pages."),
    ] = 0.001,
    render_scale: Annotated[
        float,
        typer.Option("--render-scale", help="PDF render scale used for local pixel comparison."),
    ] = 0.5,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Compare rendered PDF pages and report local visual difference evidence."""
    _emit_result(
        run_compare_visual_diff(
            before_path,
            after_path,
            pages=pages,
            max_difference_ratio=max_difference_ratio,
            render_scale=render_scale,
        ),
        json_output=json_output,
    )


@compare_app.command("version-report")
def version_report(
    before_path: Annotated[Path, typer.Argument(help="Earlier PDF file.")],
    after_path: Annotated[Path, typer.Argument(help="Later PDF file.")],
    output_path: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Optional Markdown report output path."),
    ] = None,
    pages: Annotated[str, typer.Option("--pages", help="Page range such as all or 1-3.")] = "all",
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Create a local Markdown version report from PDF text-layer changes."""
    _emit_result(
        run_compare_version_report(
            before_path,
            after_path,
            output_path=output_path,
            pages=pages,
        ),
        json_output=json_output,
    )


@app.command("parse-figures")
def parse_figures(
    input_path: Annotated[Path, typer.Argument(help="Input PDF file.")],
    pages: Annotated[str, typer.Option("--pages", help="Page range such as all or 1-3.")] = "all",
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Detect figure captions and page image hints from a local PDF."""
    _emit_result(run_parse_figures(input_path, pages=pages), json_output=json_output)


@app.command("parse-formulas")
def parse_formulas(
    input_path: Annotated[Path, typer.Argument(help="Input PDF file.")],
    pages: Annotated[str, typer.Option("--pages", help="Page range such as all or 1-3.")] = "all",
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Detect formula-like text lines from a local PDF."""
    _emit_result(run_parse_formulas(input_path, pages=pages), json_output=json_output)


@app.command("parse-charts")
def parse_charts(
    input_path: Annotated[Path, typer.Argument(help="Input PDF file.")],
    pages: Annotated[str, typer.Option("--pages", help="Page range such as all or 1-3.")] = "all",
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Detect chart captions from a local PDF."""
    _emit_result(run_parse_charts(input_path, pages=pages), json_output=json_output)


@app.command("parse-references")
def parse_references(
    input_path: Annotated[Path, typer.Argument(help="Input PDF file.")],
    pages: Annotated[str, typer.Option("--pages", help="Page range such as all or 1-3.")] = "all",
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Detect reference lines, DOIs, and URLs from a local PDF."""
    _emit_result(run_parse_references(input_path, pages=pages), json_output=json_output)


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


@authoring_app.command("plan")
def authoring_plan(
    brief_path: Annotated[Path, typer.Argument(help="Authoring brief JSON path.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Plan the best local authoring route before PDF creation."""
    _emit_result(run_authoring_plan(_read_json_object(brief_path)), json_output=json_output)


@research_app.command("plan")
def research_plan(
    brief_path: Annotated[Path, typer.Argument(help="Authoring brief JSON path.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Plan local source gathering without fetching or using a model."""
    _emit_result(run_research_plan(_read_json_object(brief_path)), json_output=json_output)


@research_app.command("source-cards")
def research_source_cards(
    sources_path: Annotated[Path, typer.Option("--sources", help="Source list JSON array path.")],
    brief_path: Annotated[Path | None, typer.Option("--brief", help="Optional authoring brief JSON path.")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Normalize agent-supplied sources into source cards."""
    _emit_result(
        run_research_source_cards(
            sources=_read_json_object_list(sources_path, "--sources"),
            brief=_read_json_object(brief_path) if brief_path is not None else None,
        ),
        json_output=json_output,
    )


@research_app.command("evidence-cards")
def research_evidence_cards(
    source_cards_path: Annotated[Path, typer.Option("--source-cards", help="Source cards JSON array path.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Extract evidence cards from normalized source cards."""
    _emit_result(
        run_research_evidence_cards(_read_json_object_list(source_cards_path, "--source-cards")),
        json_output=json_output,
    )


@design_app.command("tokens")
def design_tokens(
    theme: Annotated[str, typer.Option("--theme", help="Built-in local design theme.")] = "business_tech",
    color_overrides: Annotated[
        list[str] | None,
        typer.Option("--color", help="Design token override such as primary_color=#123456."),
    ] = None,
    overrides_path: Annotated[Path | None, typer.Option("--overrides", help="Design token overrides JSON path.")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Select safe local design tokens for authoring source packages."""
    overrides = _read_json_object(overrides_path) if overrides_path is not None else {}
    overrides.update(_parse_color_overrides(color_overrides or []))
    _emit_result(run_design_tokens(theme=theme, overrides=overrides), json_output=json_output)


@storyboard_app.command("plan")
def storyboard_plan(
    brief_path: Annotated[Path, typer.Argument(help="Authoring brief JSON path.")],
    evidence_cards_path: Annotated[
        Path | None,
        typer.Option("--evidence", "--evidence-cards", help="Evidence cards JSON array path."),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Create a deterministic page-by-page storyboard."""
    _emit_result(
        run_storyboard_plan(
            brief=_read_json_object(brief_path),
            evidence_cards=_read_json_object_list(evidence_cards_path, "--evidence")
            if evidence_cards_path
            else None,
        ),
        json_output=json_output,
    )


@pages_app.command("write")
def pages_write(
    brief_path: Annotated[Path, typer.Argument(help="Authoring brief JSON path.")],
    storyboard_path: Annotated[Path, typer.Argument(help="Storyboard JSON path.")],
    evidence_cards_path: Annotated[
        Path | None,
        typer.Option("--evidence", "--evidence-cards", help="Evidence cards JSON array path."),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Write page JSON from storyboard and evidence cards."""
    _emit_result(
        run_pages_write(
            brief=_read_json_object(brief_path),
            storyboard=_read_json_object(storyboard_path),
            evidence_cards=_read_json_object_list(evidence_cards_path, "--evidence")
            if evidence_cards_path
            else None,
        ),
        json_output=json_output,
    )


@pages_app.command("revise")
def pages_revise(
    page_document_path: Annotated[Path, typer.Argument(help="Page document JSON path.")],
    revision_items: Annotated[
        list[str] | None,
        typer.Option("--revision", help="Revision JSON object or path. Can be repeated."),
    ] = None,
    revisions_path: Annotated[Path | None, typer.Option("--revisions", help="Revision JSON array path.")] = None,
    design_tokens_path: Annotated[
        Path | None,
        typer.Option("--design-tokens", help="Optional design tokens JSON path."),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Revise generated page JSON while preserving source refs by default."""
    revisions: list[dict[str, object]] = []
    if revisions_path is not None:
        revisions.extend(_read_json_object_list(revisions_path, "--revisions"))
    for item in revision_items or []:
        revisions.append(_parse_json_object_value(item, "--revision"))
    _emit_result(
        run_pages_revise(
            page_document=_read_json_object(page_document_path),
            revisions=revisions,
            design_tokens=_read_json_object(design_tokens_path) if design_tokens_path is not None else None,
        ),
        json_output=json_output,
    )


@create_app.command("html-package")
def create_html_package(
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output HTML path.")],
    page_document_path: Annotated[Path | None, typer.Argument(help="Optional page document JSON path.")] = None,
    title: Annotated[str | None, typer.Option("--title", help="Optional document title.")] = None,
    html_source: Annotated[str | None, typer.Option("--html", help="Raw HTML string to package.")] = None,
    html_input_path: Annotated[
        Path | None,
        typer.Option("--html-file", "--html-path", help="Raw HTML file to package."),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Write a local self-contained HTML/CSS source package."""
    _emit_result(
        run_create_html_package(
            page_document=_read_json_object(page_document_path) if page_document_path is not None else None,
            html_output_path=output_path,
            title=title,
            html=html_source,
            html_path=html_input_path,
        ),
        json_output=json_output,
    )


@qa_app.command("visual-report")
def qa_visual_report(
    input_path: Annotated[Path, typer.Argument(help="Input generated PDF path.")],
    expected_page_count: Annotated[
        int | None,
        typer.Option("--expected-page-count", help="Expected PDF page count."),
    ] = None,
    html_package_manifest_path: Annotated[
        Path | None,
        typer.Option("--html-package-manifest", help="HTML package manifest path."),
    ] = None,
    pages: Annotated[str, typer.Option("--pages", help="Pages to render/check.")] = "all",
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Run visual QA checks over a generated PDF."""
    _emit_result(
        run_qa_visual_report(
            input_path=input_path,
            expected_page_count=expected_page_count,
            html_package_manifest_path=html_package_manifest_path,
            pages=pages,
        ),
        json_output=json_output,
    )


@workflow_app.command("research-deck")
def workflow_research_deck(
    brief_path: Annotated[Path, typer.Argument(help="Authoring brief JSON path.")],
    evidence_cards_path: Annotated[
        Path | None,
        typer.Option("--evidence", "--evidence-cards", help="Evidence cards JSON array path."),
    ] = None,
    html_output_path: Annotated[Path, typer.Option("--html-output", help="Output HTML package path.")] = Path(
        "deck.html"
    ),
    pdf_output_path: Annotated[Path, typer.Option("--pdf-output", help="Output PDF path.")] = Path("deck.pdf"),
    artifact_dir: Annotated[
        Path | None,
        typer.Option("--artifact-dir", help="Directory for auto-generated workflow artifacts when executing."),
    ] = None,
    execute: Annotated[bool, typer.Option("--execute", help="Run the workflow immediately.")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Plan a local research-to-deck workflow."""
    _emit_result(
        run_workflow_research_deck(
            brief=_read_json_object(brief_path),
            evidence_cards=_read_json_object_list(evidence_cards_path, "--evidence")
            if evidence_cards_path
            else None,
            html_output_path=str(html_output_path),
            pdf_output_path=str(pdf_output_path),
            artifact_dir=artifact_dir,
            execute=execute,
        ),
        json_output=json_output,
    )


@app.command("createpdf")
@workflow_app.command("createpdf")
def workflow_createpdf(
    pdf_output_path: Annotated[Path, typer.Option("--pdf-output", "-o", help="Output PDF path.")],
    html_output_path: Annotated[
        Path | None,
        typer.Option("--html-output", help="Output HTML package path. Defaults next to the PDF."),
    ] = None,
    page_document_path: Annotated[
        Path | None,
        typer.Option("--page-document", help="Optional page document JSON path."),
    ] = None,
    context_packet_path: Annotated[
        Path | None,
        typer.Option("--context-packet", help="Optional Context Packet JSON path."),
    ] = None,
    target_profile_name: Annotated[
        str,
        typer.Option("--profile", "--target-profile", help="Target PDF profile id."),
    ] = "research_brief",
    target_profile_path: Annotated[
        Path | None,
        typer.Option("--profile-json", help="Optional target profile JSON path."),
    ] = None,
    style_pack: Annotated[str | None, typer.Option("--style-pack", help="Optional style pack.")] = None,
    title: Annotated[str | None, typer.Option("--title", help="Optional document title.")] = None,
    html_source: Annotated[str | None, typer.Option("--html", help="Raw HTML string to package.")] = None,
    html_input_path: Annotated[
        Path | None,
        typer.Option("--html-file", "--html-path", help="Raw HTML file to package."),
    ] = None,
    artifact_dir: Annotated[
        Path | None,
        typer.Option("--artifact-dir", help="Directory for QA and artifact reports."),
    ] = None,
    bundle_output_path: Annotated[
        Path | None,
        typer.Option("--bundle-output", help="Optional portable audit bundle ZIP output path."),
    ] = None,
    expected_page_count: Annotated[
        int | None,
        typer.Option("--expected-page-count", help="Expected generated PDF page count."),
    ] = None,
    pages: Annotated[str, typer.Option("--pages", help="Pages to render/check during QA.")] = "all",
    renderer_backend: Annotated[
        str,
        typer.Option(
            "--renderer-backend",
            "--backend",
            help="Renderer backend: auto, local_html_package_fallback, or browser_chromium.",
        ),
    ] = "auto",
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Create a validated PDF through the local HTML-first workflow."""
    _emit_result(
        run_workflow_createpdf(
            pdf_output_path=pdf_output_path,
            html_output_path=html_output_path,
            html=html_source,
            html_path=html_input_path,
            page_document=_read_json_object(page_document_path) if page_document_path is not None else None,
            context_packet_path=context_packet_path,
            target_profile=_read_json_object(target_profile_path)
            if target_profile_path is not None
            else target_profile_name,
            style_pack=style_pack,
            title=title,
            artifact_dir=artifact_dir,
            bundle_output_path=bundle_output_path,
            expected_page_count=expected_page_count,
            pages=pages,
            renderer_backend=renderer_backend,
        ),
        json_output=json_output,
    )


@app.command("createpdf")
def createpdf(
    pdf_output_path: Annotated[Path, typer.Option("--pdf-output", "-o", help="Output PDF path.")],
    html_output_path: Annotated[
        Path | None,
        typer.Option("--html-output", help="Output HTML package path. Defaults next to the PDF."),
    ] = None,
    page_document_path: Annotated[
        Path | None,
        typer.Option("--page-document", help="Optional page document JSON path."),
    ] = None,
    context_packet_path: Annotated[
        Path | None,
        typer.Option("--context-packet", help="Optional Context Packet JSON path."),
    ] = None,
    target_profile_name: Annotated[
        str,
        typer.Option("--profile", "--target-profile", help="Target PDF profile id."),
    ] = "research_brief",
    target_profile_path: Annotated[
        Path | None,
        typer.Option("--profile-json", help="Optional target profile JSON path."),
    ] = None,
    style_pack: Annotated[str | None, typer.Option("--style-pack", help="Optional style pack.")] = None,
    title: Annotated[str | None, typer.Option("--title", help="Optional document title.")] = None,
    html_source: Annotated[str | None, typer.Option("--html", help="Raw HTML string to package.")] = None,
    html_input_path: Annotated[
        Path | None,
        typer.Option("--html-file", "--html-path", help="Raw HTML file to package."),
    ] = None,
    artifact_dir: Annotated[
        Path | None,
        typer.Option("--artifact-dir", help="Directory for QA and artifact reports."),
    ] = None,
    bundle_output_path: Annotated[
        Path | None,
        typer.Option("--bundle-output", help="Optional portable audit bundle ZIP output path."),
    ] = None,
    expected_page_count: Annotated[
        int | None,
        typer.Option("--expected-page-count", help="Expected generated PDF page count."),
    ] = None,
    pages: Annotated[str, typer.Option("--pages", help="Pages to render/check during QA.")] = "all",
    renderer_backend: Annotated[
        str,
        typer.Option(
            "--renderer-backend",
            "--backend",
            help="Renderer backend: auto, local_html_package_fallback, or browser_chromium.",
        ),
    ] = "auto",
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Create a validated PDF through the local HTML-first workflow."""
    _emit_result(
        run_workflow_createpdf(
            pdf_output_path=pdf_output_path,
            html_output_path=html_output_path,
            html=html_source,
            html_path=html_input_path,
            page_document=_read_json_object(page_document_path) if page_document_path is not None else None,
            context_packet_path=context_packet_path,
            target_profile=_read_json_object(target_profile_path)
            if target_profile_path is not None
            else target_profile_name,
            style_pack=style_pack,
            title=title,
            artifact_dir=artifact_dir,
            bundle_output_path=bundle_output_path,
            expected_page_count=expected_page_count,
            pages=pages,
            renderer_backend=renderer_backend,
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


def _parse_float_list(value: str, expected: int, label: str) -> list[float]:
    parts = [item.strip() for item in value.split(",") if item.strip()]
    if len(parts) != expected:
        raise typer.BadParameter(f"{label} must contain {expected} comma-separated numbers.")
    try:
        return [float(item) for item in parts]
    except ValueError as exc:
        raise typer.BadParameter(f"{label} must contain only numbers.") from exc


def _parse_points_json(value: str) -> list[list[float]]:
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as exc:
        raise typer.BadParameter("--points must be a JSON array of [x, y] pairs.") from exc
    if not isinstance(payload, list):
        raise typer.BadParameter("--points must be a JSON array of [x, y] pairs.")
    points: list[list[float]] = []
    for point in payload:
        if not isinstance(point, list) or len(point) != 2:
            raise typer.BadParameter("--points entries must be [x, y] arrays.")
        try:
            points.append([float(point[0]), float(point[1])])
        except (TypeError, ValueError) as exc:
            raise typer.BadParameter("--points entries must contain numeric x/y values.") from exc
    return points


def _read_json_object(path: Path) -> dict[str, object]:
    payload = _read_json_value(path)
    if not isinstance(payload, dict):
        raise typer.BadParameter("--data must point to a JSON object.")
    return payload


def _read_json_object_list(path: Path, option_name: str) -> list[dict[str, object]]:
    payload = _read_json_value(path)
    if isinstance(payload, dict) and isinstance(payload.get("evidence_cards"), list):
        payload = payload["evidence_cards"]
    if not isinstance(payload, list) or not all(isinstance(item, dict) for item in payload):
        raise typer.BadParameter(f"{option_name} must point to a JSON array of objects.")
    return list(payload)


def _read_json_value(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _parse_json_object_value(value: str, option_name: str) -> dict[str, object]:
    raw_value = value.strip()
    candidate_path = Path(raw_value)
    if candidate_path.exists():
        raw_value = candidate_path.read_text(encoding="utf-8-sig")
    try:
        payload = json.loads(raw_value)
    except json.JSONDecodeError as exc:
        raise typer.BadParameter(f"{option_name} must be a JSON object or path to one.") from exc
    if not isinstance(payload, dict):
        raise typer.BadParameter(f"{option_name} must decode to a JSON object.")
    return payload


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
    transcript_path: Path | None,
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
    if transcript_path is not None:
        item["transcript_path"] = transcript_path.as_posix()
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
    """Serve local OKoffice interfaces."""
    if mcp:
        from okoffice.mcp.server import run_mcp_server

        run_mcp_server(transport=transport)  # type: ignore[arg-type]
        return
    if api:
        import uvicorn

        uvicorn.run("okoffice.api.app:create_app", factory=True, host=host, port=port)
        return
    typer.echo("Choose --mcp for the local MCP server or --api for the future REST server.")
    raise typer.Exit(1)


if __name__ == "__main__":
    app()
