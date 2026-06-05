from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from uuid import uuid4

from pypdf import PdfReader, PdfWriter
from pypdf.annotations import Highlight
from pypdf.generic import ArrayObject, FloatObject

from okoffice.artifacts.store import build_artifact
from okoffice.core.pdf import create_markdown_pdf
from okoffice.ir.lite import parse_lite_pdf
from okoffice.schemas.errors import OKofficeException
from okoffice.schemas.models import ToolResult
from okoffice.security.paths import resolve_input_path, resolve_output_path
from okoffice.validation.pdf import validate_pdf

TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "for",
    "from",
    "in",
    "is",
    "of",
    "on",
    "or",
    "the",
    "to",
    "what",
    "with",
}


def ingest_pdf(
    input_path: str | Path,
    index_path: str | Path,
    pages: str = "all",
    max_chars: int = 1200,
    overlap_chars: int = 120,
) -> ToolResult:
    tool = "pdf.ai.rag.ingest"
    parsed = parse_lite_pdf(input_path, pages=pages)
    document_ir = parsed.usage["document_ir"]
    output = _index_output_path(index_path)
    chunks = _chunks_from_ir(document_ir, max_chars=max_chars, overlap_chars=overlap_chars)
    index = {
        "index_version": "0.1",
        "index_id": f"idx_{uuid4().hex[:12]}",
        "source_path": document_ir["source"]["path"],
        "citation_mode": "page_bbox",
        "chunking": {
            "strategy": "page_text_blocks",
            "max_chars": max_chars,
            "overlap_chars": overlap_chars,
        },
        "chunks": chunks,
    }
    output.write_text(json.dumps(index, indent=2), encoding="utf-8")
    artifact = build_artifact(output, source_tool=tool)
    pages_indexed = sorted({chunk["page_number"] for chunk in chunks})
    return ToolResult(
        job_id=_job_id(),
        status="succeeded",
        tool=tool,
        artifacts=[artifact],
        warnings=parsed.warnings,
        usage={
            "index_id": index["index_id"],
            "index_path": str(output),
            "chunk_count": len(chunks),
            "pages_indexed": pages_indexed,
            "citation_mode": "page_bbox",
        },
        next_recommended_tools=["pdf.ai.rag.query", "pdf.ai.rag.search"],
    )


def query_index(index_path: str | Path, query: str, top_k: int = 5) -> ToolResult:
    tool = "pdf.ai.rag.query"
    resolved = _resolve_index_input_path(index_path)
    index = _load_index(resolved)
    scored = _rank_chunks(index.get("chunks", []), query)
    top_chunks = scored[: max(top_k, 1)]
    citations = [
        {
            "chunk_id": chunk["chunk_id"],
            "page_number": chunk["page_number"],
            "bbox": chunk["bbox"],
            "text": chunk["text"],
            "score": score,
        }
        for score, chunk in top_chunks
        if score > 0
    ]
    answer = "\n\n".join(citation["text"] for citation in citations)
    if not answer:
        answer = "No matching local chunks found."
    return ToolResult(
        job_id=_job_id(),
        status="succeeded",
        tool=tool,
        usage={
            "index_path": str(resolved),
            "query": query,
            "answer_mode": "extractive",
            "answer": answer,
            "citations": citations,
            "top_k": top_k,
        },
        next_recommended_tools=["pdf.ai.rag.cite_answer", "pdf.ai.rag.highlight_sources"],
    )


def search_index(index_path: str | Path, query: str, top_k: int = 5) -> ToolResult:
    tool = "pdf.ai.rag.search"
    resolved = _resolve_index_input_path(index_path)
    index = _load_index(resolved)
    scored = _rank_chunks(index.get("chunks", []), query)
    matches = [
        {
            "chunk_id": chunk["chunk_id"],
            "page_number": chunk["page_number"],
            "bbox": chunk["bbox"],
            "text": chunk["text"],
            "score": score,
        }
        for score, chunk in scored[: max(top_k, 1)]
        if score > 0
    ]
    return ToolResult(
        job_id=_job_id(),
        status="succeeded",
        tool=tool,
        usage={
            "index_path": str(resolved),
            "query": query,
            "matches": matches,
            "match_count": len(matches),
            "top_k": top_k,
        },
        next_recommended_tools=["pdf.ai.rag.query", "pdf.ai.rag.cite_answer"],
    )


def cite_answer(index_path: str | Path, answer: str, top_k: int = 5) -> ToolResult:
    tool = "pdf.ai.rag.cite_answer"
    resolved = _resolve_index_input_path(index_path)
    index = _load_index(resolved)
    scored = _rank_chunks(index.get("chunks", []), answer)
    citations = [
        {
            "chunk_id": chunk["chunk_id"],
            "page_number": chunk["page_number"],
            "bbox": chunk["bbox"],
            "text": chunk["text"],
            "score": score,
            "source_block_id": chunk.get("source_block_id"),
        }
        for score, chunk in scored[: max(top_k, 1)]
        if score > 0
    ]
    warnings = [] if citations else ["No local chunks matched the supplied answer."]
    return ToolResult(
        job_id=_job_id(),
        status="succeeded",
        tool=tool,
        warnings=warnings,
        usage={
            "index_path": str(resolved),
            "answer": answer,
            "citation_mode": index.get("citation_mode", "page_bbox"),
            "citations": citations,
            "citation_count": len(citations),
            "top_k": top_k,
        },
        next_recommended_tools=["pdf.ai.rag.highlight_sources", "pdf.convert.pdf_to_markdown"],
    )


def highlight_sources(
    index_path: str | Path,
    output_path: str | Path,
    answer: str | None = None,
    query: str | None = None,
    top_k: int = 5,
    highlight_color: str = "fff59d",
) -> ToolResult:
    tool = "pdf.ai.rag.highlight_sources"
    resolved = _resolve_index_input_path(index_path)
    index = _load_index(resolved)
    source_path = resolve_input_path(index.get("source_path", ""))
    citations, warnings = _citations_for_highlight(
        index=index,
        index_path=resolved,
        answer=answer,
        query=query,
        top_k=top_k,
    )

    reader = PdfReader(source_path)
    if reader.is_encrypted:
        raise OKofficeException(
            "encrypted_pdf_requires_password",
            "Encrypted PDFs require an authorized password before processing.",
        )
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)

    highlighted_pages: set[int] = set()
    for citation in citations:
        page_number = int(citation.get("page_number", 0))
        if page_number < 1 or page_number > len(writer.pages):
            warnings.append(f"Citation references missing page: {page_number}.")
            continue
        page = writer.pages[page_number - 1]
        bbox = _clamped_bbox(citation.get("bbox", []), page_width=float(page.mediabox.width), page_height=float(page.mediabox.height))
        if bbox is None:
            warnings.append(f"Citation has invalid bbox on page {page_number}.")
            continue
        annotation = Highlight(
            rect=tuple(bbox),
            quad_points=_quad_points_from_bbox(bbox),
            highlight_color=highlight_color,
            printing=True,
        )
        writer.add_annotation(page_number - 1, annotation)
        highlighted_pages.add(page_number)

    output = resolve_output_path(output_path)
    with output.open("wb") as handle:
        writer.write(handle)
    artifact = build_artifact(output, source_tool=tool)
    validation = validate_pdf(output, expected_pages=len(reader.pages))
    return ToolResult(
        job_id=_job_id(),
        status="succeeded" if validation.status == "passed" else "failed",
        tool=tool,
        artifacts=[artifact],
        validation=validation,
        warnings=warnings,
        usage={
            "index_path": str(resolved),
            "source_path": str(source_path),
            "output_path": str(output),
            "answer": answer,
            "query": query,
            "citation_count": len(citations),
            "highlighted_pages": sorted(highlighted_pages),
            "highlight_color": highlight_color,
            "citations": citations,
        },
        next_recommended_tools=["pdf.validation.render_check", "pdf.workflow.report"],
    )


def export_report(
    index_path: str | Path,
    output_path: str | Path,
    question: str,
    answer: str | None = None,
    top_k: int = 5,
    include_citations: bool = True,
    title: str | None = None,
    style_pack: str = "plain_report",
) -> ToolResult:
    tool = "pdf.ai.rag.export_report"
    resolved = _resolve_index_input_path(index_path)
    index = _load_index(resolved)
    warnings: list[str] = []

    if answer is None:
        query_result = query_index(resolved, query=question, top_k=top_k)
        answer_text = str(query_result.usage.get("answer", ""))
        citations = list(query_result.usage.get("citations", [])) if include_citations else []
        warnings.extend(query_result.warnings)
    else:
        answer_text = answer
        cite_result = cite_answer(resolved, answer=answer, top_k=top_k)
        citations = list(cite_result.usage.get("citations", [])) if include_citations else []
        warnings.extend(cite_result.warnings)

    pages_cited = sorted(
        {
            int(citation["page_number"])
            for citation in citations
            if str(citation.get("page_number", "")).isdigit()
        }
    )
    markdown = _rag_report_markdown(
        index=index,
        index_path=resolved,
        question=question,
        answer=answer_text,
        citations=citations,
        title=title or "okoffice RAG Answer Report",
        include_citations=include_citations,
    )
    created = create_markdown_pdf(
        markdown,
        output_path=output_path,
        title=title or "okoffice RAG Answer Report",
        style_pack=style_pack,
    )
    output = Path(created.artifacts[0].path) if created.artifacts else resolve_output_path(output_path)
    artifact = build_artifact(output, source_tool=tool)
    return ToolResult(
        job_id=_job_id(),
        status=created.status,
        tool=tool,
        artifacts=[artifact],
        validation=created.validation,
        warnings=warnings + created.warnings,
        usage={
            "index_path": str(resolved),
            "source_path": index.get("source_path"),
            "output_path": str(output),
            "question": question,
            "answer": answer_text,
            "answer_mode": "extractive" if answer is None else "provided_answer_with_local_citations",
            "citation_mode": index.get("citation_mode", "page_bbox"),
            "citation_count": len(citations),
            "pages_cited": pages_cited,
            "citations": citations,
            "report_markdown_length": len(markdown),
            "style_pack": created.usage.get("style_pack", style_pack),
            "style_pack_name": created.usage.get("style_pack_name"),
            "colors": created.usage.get("colors", {}),
        },
        next_recommended_tools=["pdf.ai.rag.highlight_sources", "pdf.workflow.report"],
    )


def chat_pdf(
    input_path: str | Path,
    question: str,
    index_path: str | Path | None = None,
    report_output_path: str | Path | None = None,
    highlight_output_path: str | Path | None = None,
    pages: str = "all",
    top_k: int = 5,
    max_chars: int = 1200,
    overlap_chars: int = 120,
    style_pack: str = "plain_report",
    highlight_color: str = "fff59d",
) -> ToolResult:
    tool = "pdf.ai.rag.chat"
    job_id = _job_id()
    output_paths = _chat_output_paths(
        job_id=job_id,
        index_path=index_path,
        report_output_path=report_output_path,
        highlight_output_path=highlight_output_path,
    )

    ingest = ingest_pdf(
        input_path,
        index_path=output_paths["index_path"],
        pages=pages,
        max_chars=max_chars,
        overlap_chars=overlap_chars,
    )
    query = query_index(output_paths["index_path"], query=question, top_k=top_k)
    answer = str(query.usage.get("answer", ""))
    citations = list(query.usage.get("citations", []))
    report = export_report(
        output_paths["index_path"],
        output_path=output_paths["report_output_path"],
        question=question,
        answer=answer,
        top_k=top_k,
        style_pack=style_pack,
    )
    highlighted = highlight_sources(
        output_paths["index_path"],
        output_path=output_paths["highlight_output_path"],
        answer=answer,
        top_k=top_k,
        highlight_color=highlight_color,
    )

    artifacts = [*ingest.artifacts, *report.artifacts, *highlighted.artifacts]
    warnings = [*ingest.warnings, *query.warnings, *report.warnings, *highlighted.warnings]
    pages_cited = sorted(
        {
            int(citation["page_number"])
            for citation in citations
            if str(citation.get("page_number", "")).isdigit()
        }
    )
    status = "succeeded"
    if any(result.status == "failed" for result in [ingest, query, report, highlighted]):
        status = "failed"
    return ToolResult(
        job_id=job_id,
        status=status,
        tool=tool,
        artifacts=artifacts,
        validation=highlighted.validation or report.validation,
        warnings=warnings,
        usage={
            "input_path": str(resolve_input_path(input_path)),
            "index_path": ingest.usage.get("index_path"),
            "question": question,
            "answer": answer,
            "answer_mode": query.usage.get("answer_mode", "extractive"),
            "citation_mode": ingest.usage.get("citation_mode", "page_bbox"),
            "citations": citations,
            "citation_count": len(citations),
            "pages_cited": pages_cited,
            "report_path": report.usage.get("output_path"),
            "highlighted_path": highlighted.usage.get("output_path"),
            "highlighted_pages": highlighted.usage.get("highlighted_pages", []),
            "style_pack": report.usage.get("style_pack"),
            "step_results": [
                _chat_step_summary("ingest", ingest),
                _chat_step_summary("query", query),
                _chat_step_summary("export_report", report),
                _chat_step_summary("highlight_sources", highlighted),
            ],
        },
        next_recommended_tools=["pdf.workflow.report", "pdf.validation.render_check"],
    )


def _chat_output_paths(
    job_id: str,
    index_path: str | Path | None,
    report_output_path: str | Path | None,
    highlight_output_path: str | Path | None,
) -> dict[str, Path]:
    base_dir = Path(".okoffice-out") / "rag-chat" / job_id.removeprefix("job_")
    return {
        "index_path": Path(index_path) if index_path is not None else base_dir / "index.json",
        "report_output_path": Path(report_output_path)
        if report_output_path is not None
        else base_dir / "answer-report.pdf",
        "highlight_output_path": Path(highlight_output_path)
        if highlight_output_path is not None
        else base_dir / "highlighted-source.pdf",
    }


def _chat_step_summary(step_id: str, result: ToolResult) -> dict[str, Any]:
    return {
        "step_id": step_id,
        "tool": result.tool,
        "status": result.status,
        "job_id": result.job_id,
        "artifact_ids": [artifact.artifact_id for artifact in result.artifacts],
        "warnings": result.warnings,
    }


def _citations_for_highlight(
    index: dict[str, Any],
    index_path: Path,
    answer: str | None,
    query: str | None,
    top_k: int,
) -> tuple[list[dict[str, Any]], list[str]]:
    if answer:
        result = cite_answer(index_path, answer=answer, top_k=top_k)
        return list(result.usage.get("citations", [])), list(result.warnings)
    if query:
        result = search_index(index_path, query=query, top_k=top_k)
        return list(result.usage.get("matches", [])), list(result.warnings)
    chunks = index.get("chunks", [])
    citations = [
        {
            "chunk_id": chunk.get("chunk_id"),
            "page_number": chunk.get("page_number"),
            "bbox": chunk.get("bbox"),
            "text": chunk.get("text"),
            "source_block_id": chunk.get("source_block_id"),
            "score": None,
        }
        for chunk in chunks[: max(top_k, 1)]
    ]
    warnings = ["No answer or query supplied; highlighted the first indexed chunks."] if citations else [
        "No local chunks were available to highlight."
    ]
    return citations, warnings


def _rag_report_markdown(
    index: dict[str, Any],
    index_path: Path,
    question: str,
    answer: str,
    citations: list[dict[str, Any]],
    title: str,
    include_citations: bool,
) -> str:
    lines = [
        f"# {title}",
        "",
        "## Question",
        question.strip() or "(empty question)",
        "",
        "## Answer",
        answer.strip() or "No answer was produced from the local index.",
        "",
        "## Source",
        f"- Index: {index_path}",
        f"- Source PDF: {index.get('source_path', 'unknown')}",
        f"- Index ID: {index.get('index_id', 'unknown')}",
        f"- Citation mode: {index.get('citation_mode', 'page_bbox')}",
        "",
    ]
    if include_citations:
        lines.extend(["## Citations", ""])
        if citations:
            for position, citation in enumerate(citations, start=1):
                page_number = citation.get("page_number", "unknown")
                bbox = citation.get("bbox", [])
                score = citation.get("score")
                lines.append(f"### Citation {position} - Page {page_number}")
                lines.append(f"- Chunk: {citation.get('chunk_id', 'unknown')}")
                lines.append(f"- BBox: {bbox}")
                if score is not None:
                    lines.append(f"- Score: {score}")
                lines.append("")
                lines.append(_truncate_text(str(citation.get("text", "")), limit=900))
                lines.append("")
        else:
            lines.extend(["No local citations matched this answer.", ""])
    else:
        lines.extend(["## Citations", "Citation export was disabled for this report.", ""])
    lines.extend(
        [
            "## Limitations",
            "- This local report uses the current lightweight text-layer index.",
            "- OCR, formulas, charts, and image reasoning should be routed to explicit future workers or cloud features.",
            "- Always validate generated PDFs before using them in production workflows.",
        ]
    )
    return "\n".join(lines)


def _truncate_text(text: str, limit: int) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[: max(limit - 3, 0)].rstrip()}..."


def _clamped_bbox(value: Any, page_width: float, page_height: float) -> list[float] | None:
    if not isinstance(value, list | tuple) or len(value) != 4:
        return None
    try:
        x0, y0, x1, y1 = [float(item) for item in value]
    except (TypeError, ValueError):
        return None
    left = max(0.0, min(x0, x1, page_width))
    right = max(0.0, min(max(x0, x1), page_width))
    bottom = max(0.0, min(y0, y1, page_height))
    top = max(0.0, min(max(y0, y1), page_height))
    if right <= left or top <= bottom:
        return None
    return [left, bottom, right, top]


def _quad_points_from_bbox(bbox: list[float]) -> ArrayObject:
    left, bottom, right, top = bbox
    return ArrayObject(
        [
            FloatObject(left),
            FloatObject(top),
            FloatObject(right),
            FloatObject(top),
            FloatObject(left),
            FloatObject(bottom),
            FloatObject(right),
            FloatObject(bottom),
        ]
    )


def _chunks_from_ir(
    document_ir: dict[str, Any],
    max_chars: int,
    overlap_chars: int,
) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    chunk_index = 1
    size = max(max_chars, 1)
    overlap = min(max(overlap_chars, 0), max(size - 1, 0))
    for page in document_ir["pages"]:
        for block in page["blocks"]:
            text = block.get("text", "").strip()
            if not text:
                continue
            for chunk_text in _text_chunks(text, size=size, overlap=overlap):
                chunks.append(
                    {
                        "chunk_id": f"chunk_{chunk_index:06d}",
                        "page_number": page["page_number"],
                        "bbox": block.get("bbox", [0, 0, page["width"], page["height"]]),
                        "text": chunk_text,
                        "source_block_id": block["id"],
                        "tokens": sorted(_tokens(chunk_text)),
                    }
                )
                chunk_index += 1
    return chunks


def _text_chunks(text: str, size: int, overlap: int) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    current_length = 0
    for unit in [part.strip() for part in text.splitlines() if part.strip()]:
        if len(unit) > size:
            if current:
                chunks.append("\n".join(current))
                current = []
                current_length = 0
            chunks.extend(_fixed_chunks(unit, size=size, overlap=overlap))
            continue
        next_length = current_length + len(unit) + (1 if current else 0)
        if current and next_length > size:
            chunks.append("\n".join(current))
            current = [unit]
            current_length = len(unit)
        else:
            current.append(unit)
            current_length = next_length
    if current:
        chunks.append("\n".join(current))
    return chunks


def _fixed_chunks(text: str, size: int, overlap: int) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        chunk_text = text[start:end].strip()
        if chunk_text:
            chunks.append(chunk_text)
        if end == len(text):
            break
        start = end - overlap
    return chunks


def _rank_chunks(chunks: list[dict[str, Any]], query: str) -> list[tuple[float, dict[str, Any]]]:
    query_tokens = _tokens(query)
    scored = []
    for chunk in chunks:
        chunk_tokens = set(chunk.get("tokens") or _tokens(chunk.get("text", "")))
        overlap = query_tokens & chunk_tokens
        score = len(overlap) / max(len(query_tokens), 1)
        scored.append((round(score, 6), chunk))
    return sorted(scored, key=lambda item: (-item[0], item[1]["chunk_id"]))


def _tokens(text: str) -> set[str]:
    return {token.lower() for token in TOKEN_RE.findall(text) if token.lower() not in STOPWORDS}


def _index_output_path(index_path: str | Path) -> Path:
    candidate = Path(index_path)
    if candidate.suffix.lower() != ".json":
        candidate = candidate / "index.json"
    return resolve_output_path(candidate)


def _resolve_index_input_path(index_path: str | Path) -> Path:
    candidate = Path(index_path)
    if candidate.suffix.lower() != ".json":
        candidate = candidate / "index.json"
    return resolve_input_path(candidate)


def _load_index(resolved: Path) -> dict[str, Any]:
    try:
        return json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise OKofficeException(
            "pdf_parse_failed",
            f"Unable to parse local RAG index JSON: {resolved}",
        ) from exc


def _job_id() -> str:
    return f"job_{uuid4().hex[:16]}"
