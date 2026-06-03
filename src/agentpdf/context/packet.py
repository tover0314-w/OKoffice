from __future__ import annotations

import csv
import hashlib
import json
import mimetypes
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlunparse
from uuid import uuid4
from zipfile import BadZipFile, ZipFile

from PIL import Image, ImageStat
from pypdf import PdfReader

from agentpdf.artifacts.store import build_artifact
from agentpdf.schemas.errors import AgentPDFException
from agentpdf.schemas.models import ToolResult


CODE_EXTENSIONS = {
    ".c",
    ".cpp",
    ".cs",
    ".css",
    ".go",
    ".java",
    ".js",
    ".jsx",
    ".mjs",
    ".php",
    ".py",
    ".rs",
    ".sh",
    ".sql",
    ".ts",
    ".tsx",
}
DATA_EXTENSIONS = {".csv", ".json", ".jsonl", ".tsv", ".xlsx", ".xls"}
DOCUMENT_EXTENSIONS = {".doc", ".docx", ".html", ".md", ".ppt", ".pptx", ".rtf", ".txt"}
IMAGE_EXTENSIONS = {".bmp", ".gif", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".webp"}
AUDIO_EXTENSIONS = {".aac", ".flac", ".m4a", ".mp3", ".ogg", ".wav"}
VIDEO_EXTENSIONS = {".avi", ".mkv", ".mov", ".mp4", ".webm"}
MEDIA_EXTENSIONS = AUDIO_EXTENSIONS | VIDEO_EXTENSIONS


def build_context_packet(
    context_items: list[dict[str, Any]],
    output_path: str | Path | None = None,
    title: str | None = None,
    intent: str | None = None,
) -> ToolResult:
    return _build_context_packet(
        context_items=context_items,
        output_path=output_path,
        title=title,
        intent=intent,
        tool="pdf.context.build_packet",
    )


def build_reusable_context_packet(
    context_items: list[dict[str, Any]],
    output_path: str | Path | None = None,
    title: str | None = None,
    intent: str | None = None,
) -> ToolResult:
    return _build_context_packet(
        context_items=context_items,
        output_path=output_path,
        title=title,
        intent=intent,
        tool="pdf.context.packet",
    )


def ingest_context_item(
    context_item: dict[str, Any],
    output_path: str | Path | None = None,
) -> ToolResult:
    tool = "pdf.context.ingest"
    if not isinstance(context_item, dict) or not context_item:
        raise AgentPDFException("invalid_input", "context_item must be a non-empty JSON object.")

    item = _normalize_context_item(context_item, 1)
    source_graph = _build_source_graph([item])
    source_graph_node = source_graph["nodes"][0]
    payload = {
        "context_item_version": "0.1",
        "context_item": item,
        "source_graph_node": source_graph_node,
    }

    artifacts = []
    if output_path is not None:
        item_path = Path(output_path)
        item_path.parent.mkdir(parents=True, exist_ok=True)
        item_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        artifacts.append(build_artifact(item_path, source_tool=tool))

    return ToolResult(
        job_id=f"job_{uuid4().hex[:16]}",
        status="succeeded",
        tool=tool,
        artifacts=artifacts,
        warnings=_packet_warnings([item]),
        usage={
            "item_type": item["type"],
            "source_ref": item["source_ref"],
            "context_item": item,
            "source_graph_node": source_graph_node,
            "source_graph": {
                "source_graph_id": source_graph["source_graph_id"],
                "node_count": 1,
                "edge_count": 0,
                "nodes": source_graph["nodes"],
            },
        },
        next_recommended_tools=["pdf.context.packet", "pdf.context.build_packet", "pdf.compose.from_context"],
    )


def create_code_snapshot(
    path: str | Path,
    output_path: str | Path | None = None,
    label: str | None = None,
    role: str = "code_evidence",
    context_item_id: str | None = None,
    line_start: int | None = None,
    line_end: int | None = None,
    repository_root: str | Path | None = None,
    include_dependencies: bool = False,
) -> ToolResult:
    tool = "pdf.context.code_snapshot"
    source_path = Path(path).resolve()
    if not source_path.exists():
        raise AgentPDFException("file_not_found", f"Code snapshot path not found: {source_path}")
    if source_path.suffix.lower() not in CODE_EXTENSIONS:
        raise AgentPDFException("invalid_context_item", f"Code snapshot path is not a code file: {source_path}")

    item = _code_snapshot_context_item(
        source_path,
        label=label,
        role=role,
        context_item_id=context_item_id or "ctx_001",
        line_start=line_start,
        line_end=line_end,
        repository_root=Path(repository_root).resolve() if repository_root is not None else None,
        include_dependencies=include_dependencies,
    )
    return _context_item_result(
        tool=tool,
        item=item,
        output_path=output_path,
        next_recommended_tools=[
            "pdf.context.packet",
            "pdf.context.classify",
            "pdf.compose.add_code_block",
            "pdf.compose.from_context",
        ],
        extra_usage={"code_snapshot": item["metadata"].get("code_snapshot_evidence", {})},
    )


def profile_data_source(
    path: str | Path,
    output_path: str | Path | None = None,
    label: str | None = None,
    role: str = "data_evidence",
    context_item_id: str | None = None,
    sheet: str | None = None,
    max_rows: int = 100,
) -> ToolResult:
    tool = "pdf.context.data_profile"
    source_path = Path(path).resolve()
    if not source_path.exists():
        raise AgentPDFException("file_not_found", f"Data profile path not found: {source_path}")
    if source_path.suffix.lower() not in DATA_EXTENSIONS:
        raise AgentPDFException("invalid_context_item", f"Data profile path is not a data file: {source_path}")

    raw = {"sheet": sheet, "max_rows": max_rows}
    metadata = _file_metadata(source_path, "data", raw)
    content = _file_content_preview(source_path, "data", raw)
    item = {
        "context_item_id": context_item_id or "ctx_001",
        "type": "data",
        "role": role,
        "label": label or source_path.name,
        "source_ref": context_item_id or "ctx_001",
        "uri": source_path.as_posix(),
        "metadata": metadata,
        "content": content,
    }
    return _context_item_result(
        tool=tool,
        item=item,
        output_path=output_path,
        next_recommended_tools=[
            "pdf.context.packet",
            "pdf.context.classify",
            "pdf.compose.add_table",
            "pdf.compose.from_context",
        ],
        extra_usage={"data_profile": item["metadata"].get("data_profile_evidence", {})},
    )


def _build_context_packet(
    context_items: list[dict[str, Any]],
    output_path: str | Path | None,
    title: str | None,
    intent: str | None,
    tool: str,
) -> ToolResult:
    if not context_items:
        raise AgentPDFException("invalid_input", "context_items must include at least one item.")

    items = [_normalize_context_item(raw, index) for index, raw in enumerate(context_items, start=1)]
    items, ref_warnings = _ensure_unique_context_refs(items)
    source_graph = _build_source_graph(items)
    packet = {
        "context_packet_version": "0.1",
        "context_packet_id": f"ctxpkt_{uuid4().hex[:16]}",
        "title": title or "AgentPDF Context Packet",
        "intent": intent or "",
        "items": items,
        "source_graph": source_graph,
    }

    artifacts = []
    if output_path is not None:
        packet_path = Path(output_path)
        packet_path.parent.mkdir(parents=True, exist_ok=True)
        packet_path.write_text(json.dumps(packet, indent=2), encoding="utf-8")
        artifacts.append(build_artifact(packet_path, source_tool=tool))

    kinds = sorted({item["type"] for item in items})
    warnings = [*_packet_warnings(items), *ref_warnings]
    return ToolResult(
        job_id=f"job_{uuid4().hex[:16]}",
        status="succeeded",
        tool=tool,
        artifacts=artifacts,
        warnings=warnings,
        usage={
            "context_packet_id": packet["context_packet_id"],
            "item_count": len(items),
            "item_types": kinds,
            "context_packet": packet,
            "source_graph": {
                "source_graph_id": source_graph["source_graph_id"],
                "node_count": len(source_graph["nodes"]),
                "edge_count": len(source_graph["edges"]),
                "nodes": source_graph["nodes"],
            },
        },
        next_recommended_tools=["pdf.compose.from_context"],
    )


def _context_item_result(
    tool: str,
    item: dict[str, Any],
    output_path: str | Path | None,
    next_recommended_tools: list[str],
    extra_usage: dict[str, Any] | None = None,
) -> ToolResult:
    source_graph = _build_source_graph([item])
    source_graph_node = source_graph["nodes"][0]
    payload = {
        "context_item_version": "0.1",
        "context_item": item,
        "source_graph_node": source_graph_node,
    }

    artifacts = []
    if output_path is not None:
        item_path = Path(output_path)
        item_path.parent.mkdir(parents=True, exist_ok=True)
        item_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        artifacts.append(build_artifact(item_path, source_tool=tool))

    usage = {
        "item_type": item["type"],
        "source_ref": item["source_ref"],
        "context_item": item,
        "source_graph_node": source_graph_node,
        "source_graph": {
            "source_graph_id": source_graph["source_graph_id"],
            "node_count": 1,
            "edge_count": 0,
            "nodes": source_graph["nodes"],
        },
    }
    if extra_usage:
        usage.update(extra_usage)

    return ToolResult(
        job_id=f"job_{uuid4().hex[:16]}",
        status="succeeded",
        tool=tool,
        artifacts=artifacts,
        warnings=_packet_warnings([item]),
        usage=usage,
        next_recommended_tools=next_recommended_tools,
    )


def _normalize_context_item(raw: dict[str, Any], index: int) -> dict[str, Any]:
    if isinstance(raw.get("context_item"), dict):
        return _normalize_context_item(raw["context_item"], index)
    if _looks_like_normalized_context_item(raw):
        return _normalize_preingested_context_item(raw, index)

    context_item_id = str(raw.get("context_item_id") or f"ctx_{index:03d}")
    label = str(raw.get("label") or raw.get("name") or f"Context item {index}")
    role = str(raw.get("role") or "source")

    if raw.get("text") is not None:
        text = str(raw.get("text") or "")
        return {
            "context_item_id": context_item_id,
            "type": "text",
            "role": role,
            "label": label,
            "source_ref": context_item_id,
            "content": {"text": text[:6000]},
            "metadata": {"char_count": len(text), "preview": text[:240]},
        }

    if raw.get("table") is not None:
        table = _normalize_inline_table(raw["table"])
        table_evidence = _table_evidence(table)
        table["table_evidence"] = table_evidence
        return {
            "context_item_id": context_item_id,
            "type": "data",
            "role": role,
            "label": label,
            "source_ref": context_item_id,
            "content": {"table": table, "text": _table_to_text(table)},
            "metadata": {
                "row_count": len(table["rows"]),
                "column_count": len(table["columns"]),
                "preview": _table_to_text(table)[:240],
                "table_evidence": table_evidence,
            },
        }

    uri = raw.get("uri") or raw.get("url")
    if uri:
        uri_text = str(uri)
        citation_evidence = _web_citation_evidence(uri_text, raw)
        return {
            "context_item_id": context_item_id,
            "type": "web_link",
            "role": role,
            "label": label,
            "source_ref": context_item_id,
            "uri": citation_evidence["normalized_url"],
            "metadata": {
                "scheme": citation_evidence["scheme"],
                "domain": citation_evidence["domain"],
                "citation_evidence": citation_evidence,
            },
            "content": {"citation": {"url": citation_evidence["normalized_url"], "citation_evidence": citation_evidence}},
        }

    if raw.get("path") is None:
        raise AgentPDFException("invalid_context_item", "Context item must include text, table, uri, url, or path.")

    path = Path(str(raw["path"])).resolve()
    if not path.exists():
        raise AgentPDFException("file_not_found", f"Context item path not found: {path}")

    item_type = _infer_file_type(path, raw.get("type"))
    metadata = _file_metadata(path, item_type, raw)
    content = _file_content_preview(path, item_type, raw)
    table = content.get("table") if isinstance(content.get("table"), dict) else None
    if table and isinstance(table.get("table_evidence"), dict):
        table_evidence = table["table_evidence"]
        metadata["table_evidence"] = table_evidence
        metadata["row_count"] = table_evidence["row_count"]
        metadata["column_count"] = table_evidence["column_count"]
    code = content.get("code") if isinstance(content.get("code"), dict) else None
    if code and isinstance(metadata.get("code_evidence"), dict):
        code["code_evidence"] = metadata["code_evidence"]
    return {
        "context_item_id": context_item_id,
        "type": item_type,
        "role": role,
        "label": raw.get("label") or path.name,
        "source_ref": context_item_id,
        "uri": path.as_posix(),
        "metadata": metadata,
        "content": content,
    }


def _looks_like_normalized_context_item(raw: dict[str, Any]) -> bool:
    return bool(raw.get("type") and raw.get("source_ref") and (raw.get("content") is not None or raw.get("metadata") is not None))


def _normalize_preingested_context_item(raw: dict[str, Any], index: int) -> dict[str, Any]:
    context_item_id = str(raw.get("context_item_id") or f"ctx_{index:03d}")
    item = {
        "context_item_id": context_item_id,
        "type": str(raw.get("type") or "file"),
        "role": str(raw.get("role") or "source"),
        "label": str(raw.get("label") or raw.get("name") or f"Context item {index}"),
        "source_ref": str(raw.get("source_ref") or context_item_id),
        "metadata": raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {},
        "content": raw.get("content") if isinstance(raw.get("content"), dict) else {},
    }
    if raw.get("uri") is not None:
        item["uri"] = str(raw["uri"])
    return item


def _ensure_unique_context_refs(items: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    used_item_ids: set[str] = set()
    used_source_refs: set[str] = set()
    normalized: list[dict[str, Any]] = []
    warnings: list[str] = []
    for item in items:
        item_id = str(item["context_item_id"])
        source_ref = str(item["source_ref"])
        if item_id in used_item_ids or source_ref in used_source_refs:
            old_item_id = item_id
            old_source_ref = source_ref
            item = dict(item)
            metadata = dict(item.get("metadata", {}))
            new_ref = _next_context_ref(used_item_ids | used_source_refs)
            metadata["renamed_from_context_item_id"] = old_item_id
            metadata["renamed_from_source_ref"] = old_source_ref
            item["context_item_id"] = new_ref
            item["source_ref"] = new_ref
            item["metadata"] = metadata
            warnings.append(f"Duplicate context source ref {old_source_ref} was renamed to {new_ref}.")
            item_id = new_ref
            source_ref = new_ref
        used_item_ids.add(item_id)
        used_source_refs.add(source_ref)
        normalized.append(item)
    return normalized, warnings


def _next_context_ref(used_refs: set[str]) -> str:
    index = 1
    while True:
        candidate = f"ctx_{index:03d}"
        if candidate not in used_refs:
            return candidate
        index += 1


def _infer_file_type(path: Path, explicit_type: Any) -> str:
    if explicit_type and str(explicit_type) != "file":
        return str(explicit_type)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return "pdf"
    if suffix in IMAGE_EXTENSIONS:
        return "image"
    if suffix in AUDIO_EXTENSIONS:
        return "audio"
    if suffix in VIDEO_EXTENSIONS:
        return "video"
    if suffix in CODE_EXTENSIONS:
        return "code"
    if suffix in DATA_EXTENSIONS:
        return "data"
    if suffix in MEDIA_EXTENSIONS:
        return "media"
    if suffix in DOCUMENT_EXTENSIONS:
        return "document"
    return "file"


def _code_snapshot_context_item(
    path: Path,
    label: str | None,
    role: str,
    context_item_id: str,
    line_start: int | None,
    line_end: int | None,
    repository_root: Path | None,
    include_dependencies: bool,
) -> dict[str, Any]:
    full_text = _read_text(path)
    lines = full_text.splitlines()
    if not lines:
        lines = [""]
    start = line_start or 1
    end = line_end or len(lines)
    if start < 1 or end < start:
        raise AgentPDFException("invalid_context_item", "line_start and line_end must define a valid line range.")
    if start > len(lines):
        raise AgentPDFException("invalid_context_item", "line_start is beyond the end of the source file.")
    end = min(end, len(lines))
    selected_text = "\n".join(lines[start - 1 : end])
    language = _language_from_extension(path.suffix.lower())
    dependencies = _code_dependencies(full_text, language) if include_dependencies else []
    file_evidence = _code_evidence(path, full_text)
    selected_evidence = _code_evidence(path, selected_text)
    relative_path = _relative_path(path, repository_root) if repository_root else None
    snapshot_evidence = {
        "path": path.as_posix(),
        "repository_root": repository_root.as_posix() if repository_root else None,
        "repository_relative_path": relative_path,
        "line_start": start,
        "line_end": end,
        "selected_line_count": end - start + 1,
        "file_line_count": len(full_text.splitlines()),
        "selection_hash": hashlib.sha256(selected_text.encode("utf-8")).hexdigest(),
        "file_code_hash": file_evidence["code_hash"],
        "dependency_count": len(dependencies),
        "dependencies": dependencies,
        "analysis_method": "local_code_snapshot_v0",
    }
    data = path.read_bytes()
    metadata = {
        "path": path.as_posix(),
        "filename": path.name,
        "extension": path.suffix.lower(),
        "mime_type": mimetypes.guess_type(path.name)[0] or "text/plain",
        "size_bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "line_count": selected_evidence["line_count"],
        "char_count": selected_evidence["char_count"],
        "file_line_count": file_evidence["line_count"],
        "code_evidence": selected_evidence,
        "code_snapshot_evidence": snapshot_evidence,
    }
    preview_text = selected_text[:6000]
    return {
        "context_item_id": context_item_id,
        "type": "code",
        "role": role,
        "label": label or path.name,
        "source_ref": context_item_id,
        "uri": path.as_posix(),
        "metadata": metadata,
        "content": {
            "text": preview_text,
            "code": {
                "text": preview_text,
                "code_evidence": selected_evidence,
                "code_snapshot_evidence": snapshot_evidence,
            },
        },
    }


def _relative_path(path: Path, root: Path | None) -> str | None:
    if root is None:
        return None
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return None


def _code_dependencies(text: str, language: str) -> list[dict[str, Any]]:
    dependencies: list[dict[str, Any]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        value: str | None = None
        if language == "python":
            match = re.match(r"^(?:from\s+([A-Za-z0-9_.]+)\s+import|import\s+([A-Za-z0-9_.,\s]+))", stripped)
            if match:
                value = match.group(1) or match.group(2)
        elif language in {"javascript", "typescript"}:
            match = re.match(r"^(?:import\s+.*?\s+from\s+|import\s+|const\s+.*?=\s+require\()['\"]([^'\"]+)", stripped)
            if match:
                value = match.group(1)
        elif language == "rust":
            match = re.match(r"^use\s+([^;]+)", stripped)
            if match:
                value = match.group(1)
        if not value:
            continue
        for name in [part.strip() for part in value.split(",") if part.strip()]:
            dependencies.append({"name": name, "line": line_number})
    return dependencies[:100]


def _file_metadata(path: Path, item_type: str, raw: dict[str, Any] | None = None) -> dict[str, Any]:
    data = path.read_bytes()
    metadata: dict[str, Any] = {
        "path": path.as_posix(),
        "filename": path.name,
        "extension": path.suffix.lower(),
        "mime_type": mimetypes.guess_type(path.name)[0] or "application/octet-stream",
        "size_bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }
    if item_type in {"code", "data", "document"}:
        if item_type == "document":
            text = _document_text(path)
        elif item_type == "data":
            data_content = _data_content_preview(path, raw or {}, max_chars=12000)
            text = str(data_content.get("text") or "")
        else:
            text = _read_text_preview(path, max_chars=12000)
        metadata["line_count"] = len(text.splitlines())
        metadata["char_count"] = len(text)
        if item_type == "document":
            metadata["document_evidence"] = _document_evidence(path, text)
        if item_type == "data":
            table = data_content.get("table") if isinstance(data_content.get("table"), dict) else None
            profile = data_content.get("data_profile_evidence")
            if isinstance(table, dict) and isinstance(table.get("table_evidence"), dict):
                table_evidence = table["table_evidence"]
                metadata["table_evidence"] = table_evidence
                metadata["row_count"] = table_evidence["row_count"]
                metadata["column_count"] = table_evidence["column_count"]
            if isinstance(profile, dict):
                metadata["data_profile_evidence"] = profile
        if item_type == "code":
            full_text = _read_text(path)
            metadata["line_count"] = len(full_text.splitlines())
            metadata["char_count"] = len(full_text)
            metadata["code_evidence"] = _code_evidence(path, full_text)
    if item_type == "pdf":
        pdf_evidence = _pdf_text_evidence(path)
        metadata["page_count"] = pdf_evidence["page_count"]
        metadata["pdf_evidence"] = pdf_evidence
    if item_type == "image":
        with Image.open(path) as image:
            metadata["width"] = image.width
            metadata["height"] = image.height
            metadata["mode"] = image.mode
            metadata["visual_evidence"] = _image_visual_evidence(image)
    if item_type in {"audio", "video", "media"}:
        metadata["media_kind"] = item_type
        duration_seconds = _duration_seconds(raw or {})
        transcript = _transcript_text(raw or {})
        chapters = _normalize_timed_markers((raw or {}).get("chapters"))
        keyframes = _normalize_timed_markers((raw or {}).get("keyframes"))
        if duration_seconds is not None:
            metadata["duration_seconds"] = duration_seconds
        if transcript:
            metadata["transcript_char_count"] = len(transcript)
        if chapters:
            metadata["chapter_count"] = len(chapters)
        if keyframes:
            metadata["keyframe_count"] = len(keyframes)
    return metadata


def _file_content_preview(path: Path, item_type: str, raw: dict[str, Any] | None = None) -> dict[str, Any]:
    if item_type == "data":
        return _data_content_preview(path, raw or {}, max_chars=6000)
    if item_type in {"code", "document"}:
        text = _document_text(path)[:6000] if item_type == "document" else _read_text_preview(path, max_chars=6000)
        content: dict[str, Any] = {"text": text}
        if item_type == "code":
            content["code"] = {
                "text": text,
                "code_evidence": _code_evidence(path, text),
            }
        return content
    if item_type == "image":
        with Image.open(path) as image:
            visual_evidence = _image_visual_evidence(image)
            return {
                "image": {
                    "path": path.as_posix(),
                    "filename": path.name,
                    "width": image.width,
                    "height": image.height,
                    "mode": image.mode,
                    "visual_evidence": visual_evidence,
                }
            }
    if item_type == "pdf":
        pdf_evidence = _pdf_text_evidence(path)
        return {
            "pdf": {
                "path": path.as_posix(),
                "page_count": pdf_evidence["page_count"],
                "pdf_evidence": pdf_evidence,
            }
        }
    if item_type in {"audio", "video", "media"}:
        raw = raw or {}
        content: dict[str, Any] = {
            "media": {
                "path": path.as_posix(),
                "filename": path.name,
                "kind": item_type,
                "mime_type": mimetypes.guess_type(path.name)[0] or "application/octet-stream",
            }
        }
        transcript = _transcript_text(raw)
        chapters = _normalize_timed_markers(raw.get("chapters"))
        keyframes = _normalize_timed_markers(raw.get("keyframes"))
        if transcript:
            content["transcript"] = {
                "text": transcript[:6000],
                "char_count": len(transcript),
                "source": str(raw.get("transcript_source") or "provided"),
            }
        if chapters:
            content["chapters"] = chapters
        if keyframes:
            content["keyframes"] = keyframes
        return content
    return {}


def _duration_seconds(raw: dict[str, Any]) -> float | None:
    for key in ("duration_seconds", "duration", "duration_sec"):
        if raw.get(key) is None:
            continue
        try:
            return float(raw[key])
        except (TypeError, ValueError):
            return None
    return None


def _transcript_text(raw: dict[str, Any]) -> str:
    transcript = raw.get("transcript") or raw.get("transcript_text")
    if isinstance(transcript, dict):
        return str(transcript.get("text") or "").strip()
    if transcript is not None:
        return str(transcript).strip()
    transcript_path = raw.get("transcript_path")
    if transcript_path:
        path = Path(str(transcript_path)).resolve()
        if path.exists():
            return _read_text_preview(path, max_chars=12000).strip()
    return ""


def _normalize_timed_markers(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    markers: list[dict[str, Any]] = []
    for index, raw_marker in enumerate(value[:100], start=1):
        if isinstance(raw_marker, dict):
            marker = {
                key: raw_marker[key]
                for key in (
                    "start_seconds",
                    "end_seconds",
                    "timestamp_seconds",
                    "title",
                    "label",
                    "text",
                    "path",
                )
                if raw_marker.get(key) is not None
            }
        else:
            marker = {"title": str(raw_marker)}
        marker.setdefault("marker_id", f"marker_{index:03d}")
        markers.append({key: value for key, value in marker.items() if value not in {"", None}})
    return markers


def _data_content_preview(path: Path, raw: dict[str, Any], max_chars: int) -> dict[str, Any]:
    max_rows = _max_preview_rows(raw)
    table, profile_extras = _data_table_preview(path, raw, max_rows=max_rows)
    if table:
        text = _table_to_text(table)
    elif path.suffix.lower() in {".xlsx", ".xls"}:
        text = ""
    else:
        text = _read_text_preview(path, max_chars=max_chars)
    content: dict[str, Any] = {"text": text[:max_chars]}
    if table:
        content["table"] = table
    content["data_profile_evidence"] = _data_profile_evidence(path, text, table, profile_extras)
    return content


def _max_preview_rows(raw: dict[str, Any]) -> int:
    try:
        value = int(raw.get("max_rows", 100))
    except (TypeError, ValueError):
        value = 100
    return max(1, min(value, 500))


def _data_table_preview(
    path: Path,
    raw: dict[str, Any],
    max_rows: int,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix in {".csv", ".tsv"}:
        text = _read_text(path)
        return _delimited_table_preview(path, text, max_rows=max_rows), {
            "format": suffix.lstrip("."),
            "analysis_method": "local_delimited_table_profile_v0",
        }
    if suffix == ".json":
        text = _read_text(path)
        return _json_table_preview(text, max_rows=max_rows), {
            "format": "json",
            "analysis_method": "local_json_table_profile_v0",
        }
    if suffix == ".jsonl":
        text = _read_text(path)
        return _jsonl_table_preview(text, max_rows=max_rows), {
            "format": "jsonl",
            "analysis_method": "local_jsonl_table_profile_v0",
        }
    if suffix == ".xlsx":
        return _xlsx_table_preview(path, sheet=str(raw["sheet"]) if raw.get("sheet") else None, max_rows=max_rows)
    if suffix == ".xls":
        return None, {
            "format": "xls",
            "analysis_method": "local_data_profile_metadata_v0",
            "limitation": "legacy_xls_binary_not_parsed",
        }
    text = _read_text_preview(path, max_chars=12000)
    return _delimited_table_preview(path, text, max_rows=max_rows), {
        "format": suffix.lstrip(".") or "data",
        "analysis_method": "local_data_profile_metadata_v0",
    }


def _delimited_table_preview(path: Path, text: str, max_rows: int) -> dict[str, Any] | None:
    suffix = path.suffix.lower()
    if suffix not in {".csv", ".tsv"} or not text.strip():
        return None
    delimiter = "\t" if suffix == ".tsv" else ","
    rows = [[str(cell) for cell in row] for row in csv.reader(text.splitlines(), delimiter=delimiter)]
    return _rows_to_table(rows, max_rows=max_rows)


def _json_table_preview(text: str, max_rows: int) -> dict[str, Any] | None:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AgentPDFException("invalid_context_item", "JSON data source is not parseable.") from exc
    if isinstance(payload, list):
        return _records_to_table(payload, max_rows=max_rows)
    if isinstance(payload, dict):
        for value in payload.values():
            if isinstance(value, list):
                table = _records_to_table(value, max_rows=max_rows)
                if table:
                    return table
        scalar_rows = [[str(key), _json_scalar_preview(value)] for key, value in payload.items()]
        return _rows_to_table([["key", "value"], *scalar_rows], max_rows=max_rows)
    return None


def _jsonl_table_preview(text: str, max_rows: int) -> dict[str, Any] | None:
    records: list[Any] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise AgentPDFException(
                "invalid_context_item",
                f"JSONL data source is not parseable on line {line_number}.",
            ) from exc
    return _records_to_table(records, max_rows=max_rows)


def _records_to_table(records: list[Any], max_rows: int) -> dict[str, Any] | None:
    if not records:
        return None
    if all(isinstance(record, dict) for record in records):
        columns: list[str] = []
        for record in records[:max_rows]:
            for key in record.keys():
                column = str(key)
                if column not in columns:
                    columns.append(column)
        rows = [
            [_json_scalar_preview(record.get(column)) for column in columns]
            for record in records[:max_rows]
            if isinstance(record, dict)
        ]
        table = {"columns": columns, "rows": rows, "preview_row_count": len(records)}
        table["table_evidence"] = _table_evidence(table)
        return table
    if all(isinstance(record, list) for record in records):
        width = max((len(record) for record in records if isinstance(record, list)), default=0)
        rows = [
            [_json_scalar_preview(record[index]) if index < len(record) else "" for index in range(width)]
            for record in records[:max_rows]
            if isinstance(record, list)
        ]
        return _rows_to_table([[f"column_{index + 1}" for index in range(width)], *rows], max_rows=max_rows)
    return _rows_to_table([["value"], *[[_json_scalar_preview(record)] for record in records]], max_rows=max_rows)


def _json_scalar_preview(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)[:240]
    if value is None:
        return ""
    return str(value)


def _xlsx_table_preview(path: Path, sheet: str | None, max_rows: int) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    try:
        with ZipFile(path) as archive:
            shared_strings = _xlsx_shared_strings(archive)
            sheets = _xlsx_sheets(archive)
            if not sheets:
                return None, {
                    "format": "xlsx",
                    "analysis_method": "local_xlsx_sheet_profile_v0",
                    "sheet_count": 0,
                }
            selected_sheet = _select_xlsx_sheet(sheets, sheet)
            worksheet_xml = archive.read(selected_sheet["path"])
    except KeyError as exc:
        raise AgentPDFException("invalid_context_item", f"XLSX workbook is missing a required part: {path}") from exc
    except BadZipFile as exc:
        raise AgentPDFException("invalid_context_item", f"XLSX workbook is not a readable ZIP: {path}") from exc

    rows = _xlsx_rows(worksheet_xml, shared_strings)
    table = _rows_to_table(rows, max_rows=max_rows)
    return table, {
        "format": "xlsx",
        "analysis_method": "local_xlsx_sheet_profile_v0",
        "sheet_name": selected_sheet["name"],
        "sheet_count": len(sheets),
        "worksheet_path": selected_sheet["path"],
    }


def _xlsx_shared_strings(archive: ZipFile) -> list[str]:
    try:
        xml_data = archive.read("xl/sharedStrings.xml")
    except KeyError:
        return []
    root = ET.fromstring(xml_data)
    ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    strings: list[str] = []
    for item in root.findall(".//s:si", ns):
        parts = [node.text or "" for node in item.findall(".//s:t", ns)]
        strings.append("".join(parts))
    return strings


def _xlsx_sheets(archive: ZipFile) -> list[dict[str, str]]:
    workbook_root = ET.fromstring(archive.read("xl/workbook.xml"))
    rels_root = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    ns = {
        "s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
        "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
        "pr": "http://schemas.openxmlformats.org/package/2006/relationships",
    }
    rel_targets = {
        str(rel.attrib.get("Id")): str(rel.attrib.get("Target"))
        for rel in rels_root.findall(".//pr:Relationship", ns)
        if rel.attrib.get("Id") and rel.attrib.get("Target")
    }
    sheets: list[dict[str, str]] = []
    for sheet in workbook_root.findall(".//s:sheet", ns):
        rel_id = str(sheet.attrib.get(f"{{{ns['r']}}}id") or "")
        target = rel_targets.get(rel_id)
        if not target:
            continue
        path = target if target.startswith("xl/") else f"xl/{target.lstrip('/')}"
        sheets.append({"name": str(sheet.attrib.get("name") or rel_id), "path": path})
    return sheets


def _select_xlsx_sheet(sheets: list[dict[str, str]], requested: str | None) -> dict[str, str]:
    if requested:
        for sheet in sheets:
            if sheet["name"] == requested:
                return sheet
        raise AgentPDFException("invalid_context_item", f"XLSX sheet not found: {requested}")
    return sheets[0]


def _xlsx_rows(xml_data: bytes, shared_strings: list[str]) -> list[list[str]]:
    root = ET.fromstring(xml_data)
    ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    rows: list[list[str]] = []
    for row in root.findall(".//s:row", ns):
        values: list[str] = []
        for cell in row.findall("s:c", ns):
            column_index = _xlsx_column_index(str(cell.attrib.get("r") or "")) or len(values) + 1
            while len(values) < column_index - 1:
                values.append("")
            values.append(_xlsx_cell_value(cell, shared_strings, ns))
        if any(value != "" for value in values):
            rows.append(values)
    return rows


def _xlsx_cell_value(cell: ET.Element, shared_strings: list[str], ns: dict[str, str]) -> str:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        return "".join(node.text or "" for node in cell.findall(".//s:t", ns))
    value_node = cell.find("s:v", ns)
    value = value_node.text if value_node is not None and value_node.text is not None else ""
    if cell_type == "s" and value:
        try:
            return shared_strings[int(value)]
        except (IndexError, ValueError):
            return ""
    return value


def _xlsx_column_index(cell_ref: str) -> int | None:
    match = re.match(r"^([A-Z]+)", cell_ref.upper())
    if not match:
        return None
    index = 0
    for char in match.group(1):
        index = index * 26 + (ord(char) - 64)
    return index


def _rows_to_table(rows: list[list[str]], max_rows: int) -> dict[str, Any] | None:
    rows = [[str(cell) for cell in row] for row in rows if any(str(cell).strip() for cell in row)]
    if not rows:
        return None
    columns = [str(column) if str(column).strip() else f"column_{index + 1}" for index, column in enumerate(rows[0])]
    data_rows = []
    for row in rows[1 : max_rows + 1]:
        normalized = row + [""] * (len(columns) - len(row))
        data_rows.append([str(cell) for cell in normalized[: len(columns)]])
    table = {
        "columns": columns,
        "rows": data_rows,
        "preview_row_count": max(len(rows) - 1, 0),
    }
    table["table_evidence"] = _table_evidence(table)
    return table


def _data_profile_evidence(
    path: Path,
    text: str,
    table: dict[str, Any] | None,
    extras: dict[str, Any],
) -> dict[str, Any]:
    table_evidence = table.get("table_evidence") if isinstance(table, dict) else None
    evidence = {
        "format": extras.get("format") or path.suffix.lower().lstrip(".") or "data",
        "has_table": isinstance(table_evidence, dict),
        "row_count": table_evidence.get("row_count", 0) if isinstance(table_evidence, dict) else 0,
        "column_count": table_evidence.get("column_count", 0) if isinstance(table_evidence, dict) else 0,
        "preview_row_count": table_evidence.get("preview_row_count", 0) if isinstance(table_evidence, dict) else 0,
        "text_char_count": len(text),
        "analysis_method": extras.get("analysis_method") or "local_data_profile_metadata_v0",
    }
    for key in ("sheet_name", "sheet_count", "worksheet_path", "limitation"):
        if extras.get(key) is not None:
            evidence[key] = extras[key]
    if isinstance(table_evidence, dict):
        evidence["column_types"] = table_evidence["column_types"]
        evidence["table_hash"] = table_evidence["table_hash"]
    return evidence


def _table_preview(path: Path, text: str) -> dict[str, Any] | None:
    suffix = path.suffix.lower()
    if suffix not in {".csv", ".tsv"} or not text.strip():
        return None
    delimiter = "\t" if suffix == ".tsv" else ","
    rows = [[str(cell) for cell in row] for row in csv.reader(text.splitlines(), delimiter=delimiter)]
    if not rows:
        return None
    table = {
        "columns": rows[0],
        "rows": rows[1:11],
        "preview_row_count": max(len(rows) - 1, 0),
    }
    table["table_evidence"] = _table_evidence(table)
    return table


def _normalize_inline_table(raw_table: Any) -> dict[str, Any]:
    if not isinstance(raw_table, dict):
        raise AgentPDFException("invalid_context_item", "table context must be a JSON object.")
    raw_rows = raw_table.get("rows")
    if not isinstance(raw_rows, list):
        raise AgentPDFException("invalid_context_item", "table context must include rows.")
    raw_columns = raw_table.get("columns")
    if isinstance(raw_columns, list):
        columns = [str(column) for column in raw_columns]
    elif raw_rows and isinstance(raw_rows[0], dict):
        columns = [str(column) for column in raw_rows[0].keys()]
    else:
        columns = [f"column_{index + 1}" for index in range(len(raw_rows[0]) if raw_rows else 0)]
    rows: list[list[str]] = []
    for raw_row in raw_rows:
        if isinstance(raw_row, dict):
            rows.append([str(raw_row.get(column, "")) for column in columns])
        elif isinstance(raw_row, list):
            row = [str(cell) for cell in raw_row]
            rows.append(row + [""] * (len(columns) - len(row)))
        else:
            raise AgentPDFException("invalid_context_item", "table rows must be arrays or objects.")
    return {"columns": columns, "rows": rows[:100], "preview_row_count": len(rows)}


def _table_to_text(table: dict[str, Any]) -> str:
    columns = [str(column) for column in table.get("columns", [])]
    rows = [[str(cell) for cell in row] for row in table.get("rows", [])]
    if not columns:
        return ""
    return "\n".join([",".join(columns), *[",".join(row) for row in rows]])


def _table_evidence(table: dict[str, Any]) -> dict[str, Any]:
    columns = [str(column) for column in table.get("columns", [])]
    rows = [[str(cell) for cell in row] for row in table.get("rows", [])]
    row_count = int(table.get("preview_row_count") or len(rows))
    canonical = {"columns": columns, "rows": rows, "row_count": row_count}
    return {
        "row_count": row_count,
        "column_count": len(columns),
        "preview_row_count": len(rows),
        "column_types": _infer_table_column_types(columns, rows),
        "table_hash": hashlib.sha256(json.dumps(canonical, sort_keys=True).encode("utf-8")).hexdigest(),
        "analysis_method": "local_table_schema_hash_v0",
    }


def _infer_table_column_types(columns: list[str], rows: list[list[str]]) -> dict[str, str]:
    types: dict[str, str] = {}
    for index, column in enumerate(columns):
        values = [row[index].strip() for row in rows if index < len(row) and row[index].strip()]
        types[column] = _infer_scalar_type(values)
    return types


def _infer_scalar_type(values: list[str]) -> str:
    if not values:
        return "empty"
    lowered = [value.lower() for value in values]
    if all(value in {"true", "false", "yes", "no"} for value in lowered):
        return "boolean"
    if all(_is_number(value) for value in values):
        return "number"
    return "string"


def _is_number(value: str) -> bool:
    try:
        float(value.replace(",", ""))
    except ValueError:
        return False
    return True


def _code_evidence(path: Path, text: str) -> dict[str, Any]:
    language = _language_from_extension(path.suffix.lower())
    symbols = _code_symbols(text, language)
    return {
        "language": language,
        "line_count": len(text.splitlines()),
        "char_count": len(text),
        "code_hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "symbol_count": len(symbols),
        "symbols": symbols,
        "analysis_method": "local_code_symbol_scan_v0",
    }


def _code_symbols(text: str, language: str) -> list[dict[str, Any]]:
    symbols: list[dict[str, Any]] = []
    for index, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        symbol: dict[str, Any] | None = None
        if language == "python":
            match = re.match(r"^(class|def)\s+([A-Za-z_][A-Za-z0-9_]*)", stripped)
            if match:
                symbol = {
                    "name": match.group(2),
                    "kind": "class" if match.group(1) == "class" else "function",
                    "line": index,
                }
        elif language in {"javascript", "typescript"}:
            match = re.match(r"^(?:export\s+)?(?:async\s+)?(function|class)\s+([A-Za-z_$][A-Za-z0-9_$]*)", stripped)
            if match:
                symbol = {
                    "name": match.group(2),
                    "kind": "class" if match.group(1) == "class" else "function",
                    "line": index,
                }
            else:
                assignment = re.match(r"^(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*=", stripped)
                if assignment:
                    symbol = {"name": assignment.group(1), "kind": "binding", "line": index}
        else:
            match = re.match(r"^(?:function\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*\(", stripped)
            if match:
                symbol = {"name": match.group(1), "kind": "function", "line": index}
        if symbol is not None:
            symbols.append(symbol)
    return symbols[:100]


def _language_from_extension(extension: str) -> str:
    return {
        ".js": "javascript",
        ".jsx": "javascript",
        ".mjs": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".py": "python",
        ".rs": "rust",
        ".go": "go",
        ".sql": "sql",
        ".java": "java",
        ".cs": "csharp",
        ".css": "css",
        ".sh": "shell",
    }.get(extension, extension.lstrip(".") or "text")


def _read_text_preview(path: Path, max_chars: int) -> str:
    return _read_text(path)[:max_chars]


def _document_text(path: Path) -> str:
    if path.suffix.lower() == ".docx":
        return _read_docx_text(path)
    return _read_text_preview(path, max_chars=12000)


def _document_evidence(path: Path, text: str) -> dict[str, Any]:
    extension = path.suffix.lower()
    if extension == ".docx":
        paragraphs = [line for line in text.splitlines() if line.strip()]
        return {
            "format": "docx",
            "paragraph_count": len(paragraphs),
            "text_char_count": len(text),
            "has_text": bool(text.strip()),
            "analysis_method": "local_docx_xml_text_v0",
        }
    return {
        "format": extension.lstrip(".") or "text",
        "line_count": len(text.splitlines()),
        "text_char_count": len(text),
        "has_text": bool(text.strip()),
        "analysis_method": "local_plaintext_preview_v0",
    }


def _read_docx_text(path: Path) -> str:
    try:
        with ZipFile(path) as archive:
            try:
                document_xml = archive.read("word/document.xml")
            except KeyError as exc:
                raise AgentPDFException(
                    "invalid_context_item",
                    f"DOCX document is missing word/document.xml: {path}",
                ) from exc
    except BadZipFile as exc:
        raise AgentPDFException("invalid_context_item", f"DOCX document is not a readable ZIP: {path}") from exc

    try:
        root = ET.fromstring(document_xml)
    except ET.ParseError as exc:
        raise AgentPDFException("invalid_context_item", f"DOCX document XML is not parseable: {path}") from exc

    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs: list[str] = []
    for paragraph in root.findall(".//w:p", ns):
        parts: list[str] = []
        for node in paragraph.iter():
            tag = node.tag.rsplit("}", 1)[-1] if "}" in node.tag else node.tag
            if tag == "t" and node.text:
                parts.append(node.text)
            elif tag == "tab":
                parts.append("\t")
            elif tag in {"br", "cr"}:
                parts.append("\n")
        text = "".join(parts).strip()
        if text:
            paragraphs.append(text)
    return "\n".join(paragraphs)


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")


def _build_source_graph(items: list[dict[str, Any]]) -> dict[str, Any]:
    nodes = []
    for item in items:
        metadata = item.get("metadata", {})
        nodes.append(
            {
                "node_id": f"src_{len(nodes) + 1:03d}",
                "context_item_id": item["context_item_id"],
                "source_ref": item["source_ref"],
                "type": item["type"],
                "role": item["role"],
                "label": item["label"],
                "uri": item.get("uri"),
                "evidence": {
                    key: value
                    for key, value in metadata.items()
                    if key
                    in {
                        "path",
                        "sha256",
                        "page_count",
                        "pdf_evidence",
                        "domain",
                        "citation_evidence",
                        "code_evidence",
                        "code_snapshot_evidence",
                        "line_count",
                        "width",
                        "height",
                        "visual_evidence",
                        "document_evidence",
                        "size_bytes",
                        "row_count",
                        "column_count",
                        "table_evidence",
                        "data_profile_evidence",
                        "duration_seconds",
                        "transcript_char_count",
                        "chapter_count",
                        "keyframe_count",
                        "media_kind",
                    }
                },
            }
        )
    return {
        "source_graph_version": "0.1",
        "source_graph_id": f"srcgraph_{uuid4().hex[:16]}",
        "nodes": nodes,
        "edges": [],
    }


def _packet_warnings(items: list[dict[str, Any]]) -> list[str]:
    warnings = []
    media_count = sum(1 for item in items if item["type"] in {"audio", "video", "media"})
    if media_count:
        warnings.append("Media context uses provided transcript")
    web_count = sum(1 for item in items if item["type"] == "web_link")
    if web_count:
        warnings.append("Web links are recorded as source refs; local fetching is not enabled by default.")
    return warnings


def _image_visual_evidence(image: Image.Image) -> dict[str, Any]:
    rgb = image.convert("RGB")
    width, height = rgb.size
    sample = rgb.copy()
    if width * height > 262_144:
        sample.thumbnail((512, 512))
    raw = sample.tobytes()
    pixel_count = max(len(raw) // 3, 1)
    non_white_count = sum(
        1
        for offset in range(0, len(raw), 3)
        if raw[offset] < 250 or raw[offset + 1] < 250 or raw[offset + 2] < 250
    )
    non_white_ratio = round(non_white_count / pixel_count, 4)
    average_color = [int(round(value)) for value in ImageStat.Stat(sample).mean[:3]]
    return {
        "width": int(width),
        "height": int(height),
        "aspect_ratio": round(width / height, 4) if height else None,
        "mode": image.mode,
        "average_color_rgb": average_color,
        "non_white_ratio": non_white_ratio,
        "is_blank": non_white_ratio <= 0.001,
        "perceptual_hash": _average_image_hash(rgb),
        "analysis_method": "local_pillow_average_hash_v0",
    }


def _average_image_hash(image: Image.Image) -> str:
    resampling = getattr(Image, "Resampling", Image).LANCZOS
    grayscale = image.convert("L").resize((8, 8), resampling)
    values = list(grayscale.tobytes())
    average = sum(values) / max(len(values), 1)
    bits = "".join("1" if value >= average else "0" for value in values)
    return f"{int(bits, 2):016x}"


def _pdf_text_evidence(path: Path, max_pages: int = 5, max_chars_per_page: int = 1200) -> dict[str, Any]:
    reader = PdfReader(path)
    pages: list[dict[str, Any]] = []
    total_text_chars = 0
    for index, page in enumerate(reader.pages[:max_pages], start=1):
        text = page.extract_text() or ""
        normalized_text = " ".join(text.split())
        total_text_chars += len(text)
        mediabox = page.mediabox
        bbox = [
            float(mediabox.left),
            float(mediabox.bottom),
            float(mediabox.right),
            float(mediabox.top),
        ]
        pages.append(
            {
                "page_number": index,
                "bbox": bbox,
                "width": round(float(mediabox.width), 4),
                "height": round(float(mediabox.height), 4),
                "char_count": len(text),
                "text_preview": normalized_text[:max_chars_per_page],
            }
        )
    return {
        "page_count": len(reader.pages),
        "extracted_page_count": len(pages),
        "text_char_count": total_text_chars,
        "has_text_layer": total_text_chars > 0,
        "pages": pages,
        "analysis_method": "local_pypdf_text_preview_v0",
    }


def _web_citation_evidence(uri: str, raw: dict[str, Any]) -> dict[str, Any]:
    original_url = uri.strip()
    if not original_url:
        raise AgentPDFException("invalid_context_item", "Web context link cannot be empty.")

    parsed = urlparse(original_url)
    if not parsed.scheme:
        parsed = urlparse(f"https://{original_url}")
    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https"}:
        raise AgentPDFException("unsafe_input_rejected", "Web context links must use http:// or https:// URLs.")
    if parsed.username or parsed.password:
        raise AgentPDFException("unsafe_input_rejected", "Web context links must not include credentials.")

    domain = (parsed.hostname or "").lower()
    if not domain:
        raise AgentPDFException("unsafe_input_rejected", "Web context link must include a host.")
    try:
        port = parsed.port
    except ValueError as exc:
        raise AgentPDFException("unsafe_input_rejected", "Web context link has an invalid port.") from exc

    netloc = f"[{domain}]" if ":" in domain and not domain.startswith("[") else domain
    if port is not None:
        netloc = f"{netloc}:{port}"
    path = parsed.path or "/"
    normalized_url = urlunparse((scheme, netloc, path, "", parsed.query, parsed.fragment))
    title = str(raw.get("title") or raw.get("label") or raw.get("name") or normalized_url)
    snippet = str(raw.get("snippet") or raw.get("description") or raw.get("summary") or "").strip()
    evidence: dict[str, Any] = {
        "url": original_url,
        "normalized_url": normalized_url,
        "scheme": scheme,
        "domain": domain,
        "path": path,
        "query": parsed.query,
        "fragment": parsed.fragment,
        "title": title[:300],
        "snippet": snippet[:1000],
        "fetch_status": "not_fetched",
        "analysis_method": "local_url_metadata_v0",
    }
    for key in ("author", "published_at", "accessed_at", "source_type"):
        if raw.get(key) is not None:
            evidence[key] = str(raw[key])
    return {key: value for key, value in evidence.items() if value not in {"", None}}
