from __future__ import annotations

import hashlib
import json
import mimetypes
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

from okoffice.artifacts.store import build_artifact
from okoffice.patch.transaction import (
    apply_patch_transaction,
    plan_patch_transaction,
    verify_patch_transaction,
)
from okoffice.schemas.errors import OKofficeException
from okoffice.schemas.models import ToolResult


def add_code_block_to_pdf(
    input_path: str | Path,
    output_path: str | Path,
    title: str,
    code: str,
    language: str = "text",
    source_refs: list[str] | None = None,
    block_id: str | None = None,
    target_slot: str | None = None,
    composition_path: str | Path | None = None,
    layer_manifest_path: str | Path | None = None,
    manifest_output_path: str | Path | None = None,
) -> ToolResult:
    operation = _base_operation(
        "append_code_block",
        title=title,
        source_refs=source_refs,
        block_id=block_id,
        target_slot=target_slot,
    )
    operation["code"] = code
    operation["language"] = language
    return _run_compose_block(
        tool="pdf.compose.add_code_block",
        block_type="code",
        input_path=input_path,
        output_path=output_path,
        operation=operation,
        composition_path=composition_path,
        layer_manifest_path=layer_manifest_path,
        manifest_output_path=manifest_output_path,
    )


def add_table_to_pdf(
    input_path: str | Path,
    output_path: str | Path,
    title: str,
    columns: list[str],
    rows: list[list[Any]],
    source_refs: list[str] | None = None,
    block_id: str | None = None,
    target_slot: str | None = None,
    composition_path: str | Path | None = None,
    layer_manifest_path: str | Path | None = None,
    manifest_output_path: str | Path | None = None,
) -> ToolResult:
    operation = _base_operation(
        "append_table",
        title=title,
        source_refs=source_refs,
        block_id=block_id,
        target_slot=target_slot,
    )
    operation["columns"] = columns
    operation["rows"] = rows
    return _run_compose_block(
        tool="pdf.compose.add_table",
        block_type="table",
        input_path=input_path,
        output_path=output_path,
        operation=operation,
        composition_path=composition_path,
        layer_manifest_path=layer_manifest_path,
        manifest_output_path=manifest_output_path,
    )


def add_figure_to_pdf(
    input_path: str | Path,
    output_path: str | Path,
    title: str,
    image_path: str | Path,
    caption: str | None = None,
    source_refs: list[str] | None = None,
    block_id: str | None = None,
    target_slot: str | None = None,
    composition_path: str | Path | None = None,
    layer_manifest_path: str | Path | None = None,
    manifest_output_path: str | Path | None = None,
) -> ToolResult:
    operation = _base_operation(
        "append_image",
        title=title,
        source_refs=source_refs,
        block_id=block_id,
        target_slot=target_slot,
    )
    operation["image_path"] = str(image_path)
    operation["caption"] = caption or ""
    return _run_compose_block(
        tool="pdf.compose.add_figure",
        block_type="image",
        input_path=input_path,
        output_path=output_path,
        operation=operation,
        composition_path=composition_path,
        layer_manifest_path=layer_manifest_path,
        manifest_output_path=manifest_output_path,
    )


def add_appendix_to_pdf(
    input_path: str | Path,
    output_path: str | Path,
    title: str,
    markdown: str,
    source_refs: list[str] | None = None,
    block_id: str | None = None,
    target_slot: str | None = None,
    composition_path: str | Path | None = None,
    layer_manifest_path: str | Path | None = None,
    manifest_output_path: str | Path | None = None,
) -> ToolResult:
    operation = _base_operation(
        "append_markdown",
        title=title,
        source_refs=source_refs,
        block_id=block_id,
        target_slot=target_slot,
    )
    operation["markdown"] = markdown
    return _run_compose_block(
        tool="pdf.compose.add_appendix",
        block_type="appendix",
        input_path=input_path,
        output_path=output_path,
        operation=operation,
        composition_path=composition_path,
        layer_manifest_path=layer_manifest_path,
        manifest_output_path=manifest_output_path,
    )


def add_citation_to_pdf(
    input_path: str | Path,
    output_path: str | Path,
    title: str,
    source: str,
    quote: str | None = None,
    page: str | None = None,
    source_refs: list[str] | None = None,
    block_id: str | None = None,
    target_slot: str | None = None,
    composition_path: str | Path | None = None,
    layer_manifest_path: str | Path | None = None,
    manifest_output_path: str | Path | None = None,
) -> ToolResult:
    operation = _base_operation(
        "append_citation",
        title=title,
        source_refs=source_refs,
        block_id=block_id,
        target_slot=target_slot,
    )
    operation["source"] = source
    operation["quote"] = quote or ""
    operation["page"] = page or ""
    operation["citation_evidence"] = _citation_evidence(source=source, title=title, quote=quote)
    return _run_compose_block(
        tool="pdf.compose.add_citation",
        block_type="citation",
        input_path=input_path,
        output_path=output_path,
        operation=operation,
        composition_path=composition_path,
        layer_manifest_path=layer_manifest_path,
        manifest_output_path=manifest_output_path,
    )


def add_media_reference_to_pdf(
    input_path: str | Path,
    output_path: str | Path,
    title: str,
    media_path: str | Path,
    media_kind: str = "media",
    transcript_excerpt: str | None = None,
    duration_seconds: float | int | None = None,
    chapter_count: int | None = None,
    keyframe_count: int | None = None,
    source_refs: list[str] | None = None,
    block_id: str | None = None,
    target_slot: str | None = None,
    composition_path: str | Path | None = None,
    layer_manifest_path: str | Path | None = None,
    manifest_output_path: str | Path | None = None,
) -> ToolResult:
    normalized_kind = _normalize_media_kind(media_kind)
    operation = _base_operation(
        "append_media_reference",
        title=title,
        source_refs=source_refs,
        block_id=block_id,
        target_slot=target_slot,
    )
    operation["media_path"] = str(media_path)
    operation["media_kind"] = normalized_kind
    if transcript_excerpt:
        operation["transcript_excerpt"] = transcript_excerpt
    if duration_seconds is not None:
        operation["duration_seconds"] = float(duration_seconds)
    if chapter_count is not None:
        operation["chapter_count"] = int(chapter_count)
    if keyframe_count is not None:
        operation["keyframe_count"] = int(keyframe_count)
    operation["media_evidence"] = _media_reference_evidence(media_path, normalized_kind)
    return _run_compose_block(
        tool="pdf.compose.add_media_reference",
        block_type=_media_reference_block_type(normalized_kind),
        input_path=input_path,
        output_path=output_path,
        operation=operation,
        composition_path=composition_path,
        layer_manifest_path=layer_manifest_path,
        manifest_output_path=manifest_output_path,
    )


def add_slide_to_pdf(
    input_path: str | Path,
    output_path: str | Path,
    title: str,
    body: list[str] | None = None,
    subtitle: str | None = None,
    code: str | None = None,
    table: dict[str, Any] | None = None,
    image_path: str | Path | None = None,
    source_refs: list[str] | None = None,
    block_id: str | None = None,
    target_slot: str | None = None,
    composition_path: str | Path | None = None,
    layer_manifest_path: str | Path | None = None,
    manifest_output_path: str | Path | None = None,
) -> ToolResult:
    operation = _base_operation(
        "append_slide",
        title=title,
        source_refs=source_refs,
        block_id=block_id,
        target_slot=target_slot,
    )
    operation["body"] = body or []
    if subtitle:
        operation["subtitle"] = subtitle
    if code:
        operation["code"] = code
    if table:
        operation["table"] = table
    if image_path:
        operation["image_path"] = str(image_path)
    return _run_compose_block(
        tool="pdf.compose.add_slide",
        block_type="slide",
        input_path=input_path,
        output_path=output_path,
        operation=operation,
        composition_path=composition_path,
        layer_manifest_path=layer_manifest_path,
        manifest_output_path=manifest_output_path,
    )


def _run_compose_block(
    tool: str,
    block_type: str,
    input_path: str | Path,
    output_path: str | Path,
    operation: dict[str, Any],
    composition_path: str | Path | None,
    layer_manifest_path: str | Path | None,
    manifest_output_path: str | Path | None,
) -> ToolResult:
    destination = Path(output_path)
    source_path = Path(input_path)
    if not source_path.exists():
        raise OKofficeException("file_not_found", f"Compose input PDF not found: {source_path}")
    block_manifest_path = Path(manifest_output_path) if manifest_output_path else destination.with_suffix(".compose-block.json")
    patch_manifest_path = block_manifest_path.with_suffix(".patch.json")

    input_hash_before = _sha256(source_path)
    plan_result = plan_patch_transaction(
        input_path=input_path,
        operations=[operation],
        output_path=patch_manifest_path,
        composition_path=composition_path,
        layer_manifest_path=layer_manifest_path,
        reason=f"{tool} append-only composition block",
    )
    apply_result = apply_patch_transaction(patch_manifest_path, output_path=destination)
    verify_result = verify_patch_transaction(patch_manifest_path, patched_path=destination)
    patch_manifest = plan_result.usage["patch_manifest"]
    normalized_operation = patch_manifest["operations"][0]
    input_unchanged = input_hash_before == _sha256(source_path)
    verification = verify_result.usage.get("verification", {})
    block_manifest = {
        "compose_block_manifest_version": "0.1",
        "compose_block_id": f"composeblk_{uuid4().hex[:16]}",
        "tool": tool,
        "block_type": block_type,
        "input_path": Path(input_path).resolve().as_posix(),
        "output_path": destination.resolve().as_posix(),
        "patch_manifest_path": patch_manifest_path.resolve().as_posix(),
        "patch_id": patch_manifest["patch_id"],
        "operation": normalized_operation,
        "source_refs": normalized_operation.get("source_refs", []),
        "target_layer_refs": normalized_operation.get("target_layer_refs", {}),
        "verification": verification,
        "safety": {
            "mutates_input": False,
            "input_unchanged": input_unchanged,
            "claims_layout_preservation": False,
            "operation_mode": "append_only",
        },
    }
    block_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    block_manifest_path.write_text(json.dumps(block_manifest, indent=2), encoding="utf-8")

    block_artifact = build_artifact(block_manifest_path, source_tool=tool)
    output_artifact = build_artifact(destination, source_tool=tool)
    artifacts = [
        output_artifact,
        block_artifact,
        *plan_result.artifacts,
        *apply_result.artifacts[1:],
    ]
    status = (
        "succeeded"
        if apply_result.status == "succeeded"
        and verify_result.status == "succeeded"
        and input_unchanged
        else "failed"
    )
    return ToolResult(
        job_id=f"job_{uuid4().hex[:16]}",
        status=status,
        tool=tool,
        artifacts=artifacts,
        validation=apply_result.validation,
        warnings=[*plan_result.warnings, *apply_result.warnings, *verify_result.warnings],
        usage={
            "compose_block": block_manifest,
            "patch_plan": patch_manifest,
            "patch_apply": apply_result.usage.get("patch_manifest", {}),
            "verification": verification,
            "input_unchanged": input_unchanged,
        },
        next_recommended_tools=[
            "pdf.validation.render_check",
            "pdf.evidence.coverage_report",
            "pdf.artifacts.export_bundle",
        ],
    )


def _base_operation(
    op: str,
    title: str,
    source_refs: list[str] | None,
    block_id: str | None,
    target_slot: str | None,
) -> dict[str, Any]:
    operation: dict[str, Any] = {
        "operation_id": f"op_{uuid4().hex[:8]}",
        "op": op,
        "title": title,
        "source_refs": source_refs or [],
    }
    if block_id:
        operation["block_id"] = block_id
    if target_slot:
        operation["target_slot"] = target_slot
    return operation


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _citation_evidence(source: str, title: str, quote: str | None) -> dict[str, Any]:
    parsed = urlparse(str(source).strip())
    evidence: dict[str, Any] = {
        "source": str(source).strip(),
        "title": title,
        "quote_char_count": len(quote or ""),
        "fetch_status": "not_fetched",
        "analysis_method": "local_citation_metadata_v0",
    }
    if parsed.scheme:
        evidence["scheme"] = parsed.scheme.lower()
    if parsed.netloc:
        evidence["domain"] = parsed.netloc.lower()
    if parsed.path:
        evidence["path"] = parsed.path
    if parsed.query:
        evidence["query"] = parsed.query
    if parsed.fragment:
        evidence["fragment"] = parsed.fragment
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        evidence["normalized_url"] = parsed.geturl()
    return {key: value for key, value in evidence.items() if value not in {"", None}}


def _normalize_media_kind(media_kind: str) -> str:
    value = str(media_kind or "media").strip().lower().replace("-", "_")
    if value in {"audio", "audio_reference", "sound"}:
        return "audio"
    if value in {"video", "video_reference", "movie"}:
        return "video"
    return "media"


def _media_reference_block_type(media_kind: str) -> str:
    if media_kind == "audio":
        return "audio_reference"
    if media_kind == "video":
        return "video_reference"
    return "media_reference"


def _media_reference_evidence(media_path: str | Path, media_kind: str) -> dict[str, Any]:
    raw_path = str(media_path).strip()
    if not raw_path:
        raise OKofficeException("invalid_patch", "append_media_reference operation requires media_path.")

    parsed = urlparse(raw_path)
    guessed_mime, _encoding = mimetypes.guess_type(raw_path)
    evidence: dict[str, Any] = {
        "media_kind": media_kind,
        "source": raw_path,
        "exists": False,
        "fetch_status": "not_fetched",
        "mime_type": guessed_mime or "application/octet-stream",
        "analysis_method": "local_media_reference_metadata_v0",
    }

    if parsed.scheme and parsed.netloc:
        evidence["reference_type"] = "url"
        evidence["scheme"] = parsed.scheme.lower()
        evidence["domain"] = parsed.netloc.lower()
        if parsed.path:
            evidence["path"] = parsed.path
            evidence["filename"] = Path(parsed.path).name
        if parsed.query:
            evidence["query"] = parsed.query
        if parsed.fragment:
            evidence["fragment"] = parsed.fragment
        if parsed.scheme in {"http", "https"}:
            evidence["normalized_url"] = parsed.geturl()
        return {key: value for key, value in evidence.items() if value not in {"", None}}

    path = Path(raw_path)
    evidence["reference_type"] = "local_file"
    evidence["filename"] = path.name
    if path.suffix:
        evidence["extension"] = path.suffix.lower()
    if path.exists():
        resolved = path.resolve()
        evidence["path"] = resolved.as_posix()
        evidence["exists"] = True
        evidence["size_bytes"] = resolved.stat().st_size
        evidence["sha256"] = _sha256(resolved)
    else:
        evidence["path"] = path.as_posix()
    return {key: value for key, value in evidence.items() if value not in {"", None}}
