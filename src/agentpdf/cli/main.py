from pathlib import Path
from typing import Annotated

import typer

from agentpdf import __version__
from agentpdf.schemas.models import ToolResult
from agentpdf.tools.registry import get_tool, load_tool_manifest
from agentpdf.tools.runner import (
    run_create_markdown,
    run_create_text,
    run_extract_pages,
    run_extract_text,
    run_inspect,
    run_metadata_read,
    run_metadata_remove,
    run_metadata_update,
    run_merge,
    run_remove_pages,
    run_render,
    run_rotate_pages,
    run_split,
)

app = typer.Typer(help="AgentPDF Infra CLI")
tools_app = typer.Typer(help="Discover AgentPDF tools.")
metadata_app = typer.Typer(help="Read and write PDF metadata.")
create_app = typer.Typer(help="Create PDFs from local inputs.")
app.add_typer(tools_app, name="tools")
app.add_typer(metadata_app, name="metadata")
app.add_typer(create_app, name="create")


@app.callback()
def main() -> None:
    """Open-source PDF infrastructure for AI agents."""


@app.command()
def version() -> None:
    """Print the AgentPDF version."""
    typer.echo(f"agentpdf {__version__}")


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


@app.command("extract-text")
def extract_text(
    input_path: Annotated[Path, typer.Argument(help="Input PDF file.")],
    pages: Annotated[str, typer.Option("--pages", help="Page range such as all or 1-3.")] = "all",
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Extract text from PDF pages."""
    _emit_result(run_extract_text(input_path, pages=pages), json_output=json_output)


@metadata_app.command("read")
def metadata_read(
    input_path: Annotated[Path, typer.Argument(help="Input PDF file.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
) -> None:
    """Read PDF metadata."""
    _emit_result(run_metadata_read(input_path), json_output=json_output)


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

        uvicorn.run("agentpdf.api.app:create_app", factory=True, host="127.0.0.1", port=7331)
        return
    typer.echo("Choose --mcp for the local MCP server or --api for the future REST server.")
    raise typer.Exit(1)


if __name__ == "__main__":
    app()
