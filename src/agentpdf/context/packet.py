from __future__ import annotations

import csv
import hashlib
import json
import mimetypes
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlunparse
from uuid import uuid4

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
    tool = "pdf.context.build_packet"
    if not context_items:
        raise AgentPDFException("invalid_input", "context_items must include at least one item.")

    items = [_normalize_context_item(raw, index) for index, raw in enumerate(context_items, start=1)]
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
    warnings = _packet_warnings(items)
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


def _normalize_context_item(raw: dict[str, Any], index: int) -> dict[str, Any]:
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
        text = _read_text_preview(path, max_chars=12000)
        metadata["line_count"] = len(text.splitlines())
        metadata["char_count"] = len(text)
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
    if item_type in {"code", "data", "document"}:
        text = _read_text_preview(path, max_chars=6000)
        content: dict[str, Any] = {"text": text}
        if item_type == "code":
            content["code"] = {
                "text": text,
                "code_evidence": _code_evidence(path, text),
            }
        table = _table_preview(path, text)
        if table:
            content["table"] = table
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
                        "line_count",
                        "width",
                        "height",
                        "visual_evidence",
                        "size_bytes",
                        "row_count",
                        "column_count",
                        "table_evidence",
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
    parsed = urlparse(uri.strip())
    scheme = (parsed.scheme or "https").lower()
    netloc = parsed.netloc.lower()
    path = parsed.path or ("/" if netloc else "")
    normalized_url = urlunparse((scheme, netloc, path, "", parsed.query, parsed.fragment))
    title = str(raw.get("title") or raw.get("label") or raw.get("name") or normalized_url)
    snippet = str(raw.get("snippet") or raw.get("description") or raw.get("summary") or "").strip()
    evidence: dict[str, Any] = {
        "url": uri.strip(),
        "normalized_url": normalized_url,
        "scheme": scheme,
        "domain": netloc,
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
