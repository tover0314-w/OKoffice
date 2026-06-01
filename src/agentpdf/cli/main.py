import json
from pathlib import Path
from typing import Annotated

import typer

from agentpdf import __version__
from agentpdf.schemas.models import ToolResult
from agentpdf.tools.registry import get_tool, load_tool_manifest
from agentpdf.tools.runner import (
    run_blank_page_check,
    run_compress,
    run_create_markdown,
    run_create_text,
    run_extract_images,
    run_extract_pages,
    run_extract_text,
    run_image_to_pdf,
    run_inspect,
    run_inspect_pages,
    run_insert_blank_pages,
    run_metadata_read,
    run_metadata_remove,
    run_metadata_update,
    run_merge,
    run_page_numbers,
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
    run_split,
    run_validate_output,
    run_watermark,
    run_workflow_plan,
    run_workflow_report,
    run_workflow_run,
)

app = typer.Typer(help="AgentPDF Infra CLI")
tools_app = typer.Typer(help="Discover AgentPDF tools.")
metadata_app = typer.Typer(help="Read and write PDF metadata.")
create_app = typer.Typer(help="Create PDFs from local inputs.")
rag_app = typer.Typer(help="Local document retrieval tools.")
workflow_app = typer.Typer(help="Plan local agent PDF workflows.")
app.add_typer(tools_app, name="tools")
app.add_typer(metadata_app, name="metadata")
app.add_typer(create_app, name="create")
app.add_typer(rag_app, name="rag")
app.add_typer(workflow_app, name="workflow")


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
