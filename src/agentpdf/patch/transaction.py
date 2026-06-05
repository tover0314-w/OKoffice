from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any
from uuid import uuid4

from pypdf import PdfReader, PdfWriter

from agentpdf.artifacts.store import build_artifact
from agentpdf.core.pdf import create_markdown_pdf, create_slide_deck_pdf
from agentpdf.renderers.html_package import render_html_package
from agentpdf.schemas.errors import AgentPDFException
from agentpdf.schemas.models import ToolResult
from agentpdf.validation.pdf import validate_pdf


SUPPORTED_PATCH_OPERATIONS = [
    "append_markdown",
    "append_code_block",
    "append_table",
    "append_image",
    "append_slide",
    "append_citation",
    "append_media_reference",
    "regenerate_block",
]


def plan_patch_transaction(
    input_path: str | Path,
    operations: list[dict[str, Any]],
    output_path: str | Path,
    composition_path: str | Path | None = None,
    layer_manifest_path: str | Path | None = None,
    artifact_graph_path: str | Path | None = None,
    reason: str | None = None,
) -> ToolResult:
    tool = "pdf.patch.plan"
    source = Path(input_path).resolve()
    if not source.exists():
        raise AgentPDFException("file_not_found", f"Patch input PDF not found: {source}")
    if not operations:
        raise AgentPDFException("invalid_patch", "Patch operations must include at least one operation.")

    normalized_operations = [_normalize_operation(operation, index) for index, operation in enumerate(operations, start=1)]
    source_ref_validation = _validate_operation_source_refs(normalized_operations, composition_path)
    layer_ref_validation = _validate_operation_layer_refs(normalized_operations, layer_manifest_path)
    html_layer_ref_validation = _validate_operation_html_layer_refs(normalized_operations, artifact_graph_path)
    source_artifact = build_artifact(source, source_tool="pdf.patch.input")
    manifest = {
        "patch_manifest_version": "0.1",
        "patch_id": f"patch_{uuid4().hex[:16]}",
        "input_path": source.as_posix(),
        "input_artifact": source_artifact.model_dump(mode="json"),
        "composition_path": Path(composition_path).resolve().as_posix() if composition_path else None,
        "layer_manifest_path": Path(layer_manifest_path).resolve().as_posix() if layer_manifest_path else None,
        "artifact_graph_path": Path(artifact_graph_path).resolve().as_posix() if artifact_graph_path else None,
        "reason": reason or "",
        "operation_count": len(normalized_operations),
        "operations": normalized_operations,
        "source_ref_validation": source_ref_validation["summary"],
        "operation_source_map": source_ref_validation["operation_source_map"],
        "layer_ref_validation": layer_ref_validation["summary"],
        "operation_layer_map": layer_ref_validation["operation_layer_map"],
        "html_layer_ref_validation": html_layer_ref_validation["summary"],
        "operation_html_layer_map": html_layer_ref_validation["operation_html_layer_map"],
        "safety": {
            "mutates_input": False,
            "requires_new_output_path": True,
            "supported_operations": SUPPORTED_PATCH_OPERATIONS,
            "supports_layer_anchors": True,
            "supports_html_layer_anchors": True,
            "html_layer_bbox_precision": "estimated_dom_not_pdf_glyph_bbox",
            "claims_layout_preservation": False,
        },
        "validation_required": ["parseable_pdf", "page_count_delta"],
    }
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    artifact = build_artifact(destination, source_tool=tool)
    return ToolResult(
        job_id=f"job_{uuid4().hex[:16]}",
        status="succeeded",
        tool=tool,
        artifacts=[artifact],
        usage={"patch_manifest": manifest},
        next_recommended_tools=["pdf.patch.preview", "pdf.patch.apply"],
    )


def preview_patch_transaction(
    patch_manifest: dict[str, Any] | str | Path,
    output_path: str | Path | None = None,
) -> ToolResult:
    tool = "pdf.patch.preview"
    manifest = _load_manifest(patch_manifest)
    input_pages = len(PdfReader(manifest["input_path"]).pages)
    operation_summary = [
        {
            "operation_id": operation["operation_id"],
            "op": operation["op"],
            "title": operation.get("title"),
            "source_refs": operation.get("source_refs", []),
            "target_layer_refs": operation.get("target_layer_refs", {}),
            "target_html_layer_refs": operation.get("target_html_layer_refs", {}),
            "matched_layer_count": len(operation.get("layer_evidence", [])),
            "matched_html_layer_count": len(operation.get("html_layer_evidence", [])),
            "expected_effect": _operation_expected_effect(operation),
        }
        for operation in manifest["operations"]
    ]
    preview = {
        "patch_preview_version": "0.1",
        "patch_id": manifest["patch_id"],
        "input_path": manifest["input_path"],
        "input_pages": input_pages,
        "operation_summary": operation_summary,
        "will_mutate_input": False,
        "validation_required": manifest.get("validation_required", []),
    }
    artifacts = []
    if output_path is not None:
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(preview, indent=2), encoding="utf-8")
        artifacts.append(build_artifact(destination, source_tool=tool))
    return ToolResult(
        job_id=f"job_{uuid4().hex[:16]}",
        status="succeeded",
        tool=tool,
        artifacts=artifacts,
        usage=preview,
        next_recommended_tools=["pdf.patch.apply"],
    )


def apply_patch_transaction(
    patch_manifest: dict[str, Any] | str | Path,
    output_path: str | Path,
) -> ToolResult:
    tool = "pdf.patch.apply"
    manifest = _load_manifest(patch_manifest)
    input_path = Path(manifest["input_path"]).resolve()
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if _should_apply_html_layer_rerender(manifest):
        return _apply_html_layer_rerender(
            manifest=manifest,
            output_path=destination,
            input_path=input_path,
            tool=tool,
        )
    input_reader = PdfReader(input_path)
    writer = PdfWriter()
    for page in input_reader.pages:
        writer.add_page(page)

    appended_pages = 0
    temp_paths = []
    for operation in manifest["operations"]:
        temp_pdf = destination.with_name(f"{destination.stem}.{operation['operation_id']}.append.pdf")
        temp_paths.append(temp_pdf)
        if operation["op"] == "append_slide":
            create_slide_deck_pdf(
                [_operation_slide(operation, manifest)],
                output_path=temp_pdf,
                title=operation.get("title"),
                style_pack="paper_ink",
            )
        else:
            create_markdown_pdf(
                _operation_markdown(operation, manifest),
                output_path=temp_pdf,
                title=operation.get("title"),
                style_pack="paper_ink",
            )
        temp_reader = PdfReader(temp_pdf)
        appended_pages += len(temp_reader.pages)
        for page in temp_reader.pages:
            writer.add_page(page)

    with destination.open("wb") as handle:
        writer.write(handle)
    for temp_path in temp_paths:
        try:
            temp_path.unlink()
        except FileNotFoundError:
            pass

    validation = validate_pdf(destination)
    output_artifact = build_artifact(destination, source_tool=tool)
    applied_manifest = dict(manifest)
    applied_manifest["output_path"] = destination.resolve().as_posix()
    applied_manifest["output_artifact"] = output_artifact.model_dump(mode="json")
    applied_manifest["page_count_delta"] = appended_pages
    applied_path = destination.with_suffix(".patch-applied.json")
    applied_path.write_text(json.dumps(applied_manifest, indent=2), encoding="utf-8")
    rollback = {
        "rollback_manifest_version": "0.1",
        "patch_id": manifest["patch_id"],
        "restore_path": manifest["input_path"],
        "patched_path": destination.resolve().as_posix(),
        "input_artifact": manifest["input_artifact"],
    }
    rollback_path = destination.with_suffix(".rollback.json")
    rollback_path.write_text(json.dumps(rollback, indent=2), encoding="utf-8")
    return ToolResult(
        job_id=f"job_{uuid4().hex[:16]}",
        status="succeeded" if validation.status == "passed" else "failed",
        tool=tool,
        artifacts=[
            output_artifact,
            build_artifact(applied_path, source_tool=tool),
            build_artifact(rollback_path, source_tool="pdf.patch.rollback_manifest"),
        ],
        validation=validation,
        warnings=list(validation.warnings),
        usage={
            "patch_manifest": applied_manifest,
            "rollback_manifest": rollback,
            "page_count_delta": appended_pages,
            "input_unchanged": _sha256_matches(input_path, manifest["input_artifact"]["sha256"]),
        },
        next_recommended_tools=["pdf.patch.verify", "pdf.validation.render_check"],
    )


def _should_apply_html_layer_rerender(manifest: dict[str, Any]) -> bool:
    operations = manifest.get("operations")
    if not isinstance(operations, list) or not operations:
        return False
    return all(
        isinstance(operation, dict)
        and operation.get("op") == "regenerate_block"
        and bool(operation.get("html_layer_evidence"))
        for operation in operations
    )


def _apply_html_layer_rerender(
    *,
    manifest: dict[str, Any],
    output_path: Path,
    input_path: Path,
    tool: str,
) -> ToolResult:
    html_context = _html_layer_patch_context(manifest)
    patched_html_path = output_path.with_suffix(".html")
    patched_manifest_path = patched_html_path.with_suffix(".html-manifest.json")
    patched_html = _apply_html_layer_replacements(
        html_context["html_path"].read_text(encoding="utf-8"),
        manifest["operations"],
    )
    patched_manifest = _patched_html_package_manifest(
        html_context["manifest"],
        html_output_path=patched_html_path,
        manifest_output_path=patched_manifest_path,
        patch_manifest=manifest,
    )
    patched_html_path.write_text(patched_html, encoding="utf-8")
    patched_manifest_path.write_text(json.dumps(patched_manifest, indent=2), encoding="utf-8")

    render_result = render_html_package(patched_manifest_path, output_path=output_path)
    validation = render_result.validation or validate_pdf(output_path)
    page_count_delta = len(PdfReader(output_path).pages) - len(PdfReader(input_path).pages)
    output_artifact = build_artifact(output_path, source_tool=tool)
    html_layer_patch = {
        "mode": "html_layer_rerender",
        "source_html_path": html_context["html_path"].as_posix(),
        "source_html_package_manifest_path": html_context["manifest_path"].as_posix(),
        "html_output_path": patched_html_path.resolve().as_posix(),
        "html_package_manifest_path": patched_manifest_path.resolve().as_posix(),
        "rewritten_layer_ids": _patched_html_layer_ids(manifest["operations"]),
        "bbox_precision": "estimated_dom_not_pdf_glyph_bbox",
        "mutates_input": False,
        "claims_layout_preservation": False,
    }
    applied_manifest = dict(manifest)
    applied_manifest["apply_mode"] = "html_layer_rerender"
    applied_manifest["output_path"] = output_path.resolve().as_posix()
    applied_manifest["output_artifact"] = output_artifact.model_dump(mode="json")
    applied_manifest["page_count_delta"] = page_count_delta
    applied_manifest["html_layer_patch"] = html_layer_patch
    applied_path = output_path.with_suffix(".patch-applied.json")
    applied_path.write_text(json.dumps(applied_manifest, indent=2), encoding="utf-8")
    rollback = {
        "rollback_manifest_version": "0.1",
        "patch_id": manifest["patch_id"],
        "restore_path": manifest["input_path"],
        "patched_path": output_path.resolve().as_posix(),
        "input_artifact": manifest["input_artifact"],
        "html_restore_path": html_context["html_path"].as_posix(),
    }
    rollback_path = output_path.with_suffix(".rollback.json")
    rollback_path.write_text(json.dumps(rollback, indent=2), encoding="utf-8")
    return ToolResult(
        job_id=f"job_{uuid4().hex[:16]}",
        status="succeeded" if validation.status == "passed" else "failed",
        tool=tool,
        artifacts=[
            output_artifact,
            build_artifact(patched_html_path, source_tool=tool),
            build_artifact(patched_manifest_path, source_tool=tool),
            build_artifact(applied_path, source_tool=tool),
            build_artifact(rollback_path, source_tool="pdf.patch.rollback_manifest"),
        ],
        validation=validation,
        warnings=[*render_result.warnings, *validation.warnings],
        usage={
            "patch_manifest": applied_manifest,
            "rollback_manifest": rollback,
            "html_layer_patch": html_layer_patch,
            "page_count_delta": page_count_delta,
            "input_unchanged": _sha256_matches(input_path, manifest["input_artifact"]["sha256"]),
        },
        next_recommended_tools=["pdf.patch.verify", "pdf.validation.render_check"],
    )


def _html_layer_patch_context(manifest: dict[str, Any]) -> dict[str, Any]:
    first_layer = _first_html_layer_evidence(manifest["operations"])
    if first_layer is None:
        raise AgentPDFException("invalid_patch", "HTML layer rerender requires html_layer_evidence.")
    manifest_path = Path(str(first_layer.get("path") or "")).expanduser().resolve()
    html_path = Path(str(first_layer.get("html_path") or "")).expanduser().resolve()
    if not manifest_path.exists():
        raise AgentPDFException("file_not_found", f"HTML package manifest not found: {manifest_path}")
    if not html_path.exists():
        raise AgentPDFException("file_not_found", f"HTML source not found: {html_path}")
    for operation in manifest["operations"]:
        for layer in operation.get("html_layer_evidence", []):
            if not isinstance(layer, dict):
                continue
            if Path(str(layer.get("path") or "")).expanduser().resolve() != manifest_path:
                raise AgentPDFException(
                    "invalid_patch",
                    "HTML layer rerender operations must target one HTML package manifest.",
                )
            if Path(str(layer.get("html_path") or "")).expanduser().resolve() != html_path:
                raise AgentPDFException(
                    "invalid_patch",
                    "HTML layer rerender operations must target one HTML source file.",
                )
    payload = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise AgentPDFException("html_invalid_package", "HTML package manifest must be a JSON object.")
    return {"manifest_path": manifest_path, "html_path": html_path, "manifest": payload}


def _first_html_layer_evidence(operations: list[dict[str, Any]]) -> dict[str, Any] | None:
    for operation in operations:
        for layer in operation.get("html_layer_evidence", []):
            if isinstance(layer, dict):
                return layer
    return None


def _apply_html_layer_replacements(html_text: str, operations: list[dict[str, Any]]) -> str:
    patched = html_text
    for operation in operations:
        for layer in operation.get("html_layer_evidence", []):
            if not isinstance(layer, dict):
                continue
            layer_id = str(layer.get("layer_id") or "").strip()
            if not layer_id:
                continue
            patched = _replace_html_layer_article(patched, layer_id=layer_id, operation=operation)
    return patched


def _replace_html_layer_article(html_text: str, *, layer_id: str, operation: dict[str, Any]) -> str:
    pattern = re.compile(
        rf'(<article\b[^>]*\bdata-layer-id="{re.escape(layer_id)}"[^>]*>)(.*?)(\n\s*</article>)',
        re.DOTALL,
    )
    replacement_html = _replacement_markdown_html(operation)
    patched, count = pattern.subn(
        lambda match: f"{match.group(1)}\n{replacement_html}{match.group(3)}",
        html_text,
        count=1,
    )
    if count != 1:
        raise AgentPDFException(
            "html_layer_ref_not_found",
            "HTML layer id was not found in the source HTML.",
            details={"html_layer_id": layer_id},
        )
    return patched


def _replacement_markdown_html(operation: dict[str, Any]) -> str:
    markdown = str(operation.get("replacement_markdown") or "").strip()
    lines = []
    for line in markdown.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("## "):
            lines.append(f"      <h2>{html.escape(stripped[3:].strip())}</h2>")
        elif stripped.startswith("# "):
            lines.append(f"      <h2>{html.escape(stripped[2:].strip())}</h2>")
        elif stripped.startswith("- "):
            lines.append(f"      <p>&bull; {html.escape(stripped[2:].strip())}</p>")
        else:
            lines.append(f"      <p>{html.escape(stripped)}</p>")
    lines.extend(
        [
            '      <p class="agentpdf-patch-note"><strong>Patch operation:</strong> '
            f"{html.escape(str(operation.get('operation_id') or 'unknown'))}</p>",
            '      <p class="agentpdf-patch-note"><strong>Patch mode:</strong> '
            "html_layer_rerender</p>",
        ]
    )
    return "\n".join(lines)


def _patched_html_package_manifest(
    manifest: dict[str, Any],
    *,
    html_output_path: Path,
    manifest_output_path: Path,
    patch_manifest: dict[str, Any],
) -> dict[str, Any]:
    patched = dict(manifest)
    patched["html_package_id"] = f"htmlpkg_patch_{uuid4().hex[:12]}"
    patched["source_tool"] = "pdf.patch.apply"
    patched["html_path"] = html_output_path.resolve().as_posix()
    patched["manifest_path"] = manifest_output_path.resolve().as_posix()
    patched["patched_from_html_package_id"] = manifest.get("html_package_id")
    patched["patch_id"] = patch_manifest.get("patch_id")
    patched["patch_mode"] = "html_layer_rerender"
    patched["patched_layer_ids"] = _patched_html_layer_ids(patch_manifest["operations"])
    return patched


def _patched_html_layer_ids(operations: list[dict[str, Any]]) -> list[str]:
    layer_ids = []
    for operation in operations:
        for layer in operation.get("html_layer_evidence", []):
            if not isinstance(layer, dict):
                continue
            layer_id = str(layer.get("layer_id") or "").strip()
            if layer_id and layer_id not in layer_ids:
                layer_ids.append(layer_id)
    return layer_ids


def verify_patch_transaction(
    patch_manifest: dict[str, Any] | str | Path,
    patched_path: str | Path,
) -> ToolResult:
    tool = "pdf.patch.verify"
    manifest = _load_manifest(patch_manifest)
    input_path = Path(manifest["input_path"]).resolve()
    patched = Path(patched_path).resolve()
    if not patched.exists():
        raise AgentPDFException("file_not_found", f"Patched PDF not found: {patched}")
    input_pages = len(PdfReader(input_path).pages)
    patched_pages = len(PdfReader(patched).pages)
    validation = validate_pdf(patched)
    verification = {
        "patch_id": manifest["patch_id"],
        "input_unchanged": _sha256_matches(input_path, manifest["input_artifact"]["sha256"]),
        "input_pages": input_pages,
        "patched_pages": patched_pages,
        "page_count_delta": patched_pages - input_pages,
        "operation_count": len(manifest["operations"]),
        "source_ref_validation_status": manifest.get("source_ref_validation", {}).get("status", "unknown"),
        "layer_ref_validation_status": manifest.get("layer_ref_validation", {}).get("status", "unknown"),
        "html_layer_ref_validation_status": manifest.get("html_layer_ref_validation", {}).get("status", "unknown"),
        "matched_source_count": _manifest_matched_source_count(manifest),
        "matched_layer_count": _manifest_matched_layer_count(manifest),
        "matched_html_layer_count": _manifest_matched_html_layer_count(manifest),
        "source_ref_validation": manifest.get("source_ref_validation", {}),
        "layer_ref_validation": manifest.get("layer_ref_validation", {}),
        "html_layer_ref_validation": manifest.get("html_layer_ref_validation", {}),
        "operation_source_map": manifest.get("operation_source_map", []),
        "operation_layer_map": manifest.get("operation_layer_map", []),
        "operation_html_layer_map": manifest.get("operation_html_layer_map", []),
    }
    status = "succeeded" if validation.status == "passed" and verification["page_count_delta"] >= 0 else "failed"
    return ToolResult(
        job_id=f"job_{uuid4().hex[:16]}",
        status=status,
        tool=tool,
        validation=validation,
        warnings=list(validation.warnings),
        usage={"verification": verification},
        next_recommended_tools=["pdf.evidence.coverage_report"],
    )


def _normalize_operation(operation: dict[str, Any], index: int) -> dict[str, Any]:
    op = str(operation.get("op") or "")
    if op not in SUPPORTED_PATCH_OPERATIONS:
        raise AgentPDFException("unsupported_patch_operation", f"Unsupported patch operation: {op}")
    normalized: dict[str, Any] = {
        "operation_id": str(operation.get("operation_id") or f"op_{index:03d}"),
        "op": op,
        "title": str(operation.get("title") or f"Patch Operation {index}"),
        "source_refs": _source_refs(operation),
    }
    target_layer_refs = _target_layer_refs(operation)
    if any(target_layer_refs.values()):
        normalized["target_layer_refs"] = target_layer_refs
    target_html_layer_refs = _target_html_layer_refs(operation)
    if any(target_html_layer_refs.values()):
        normalized["target_html_layer_refs"] = target_html_layer_refs
    if op == "append_markdown":
        markdown = str(operation.get("markdown") or "").strip()
        if not markdown:
            raise AgentPDFException("invalid_patch", "append_markdown operation requires markdown.")
        normalized["markdown"] = markdown
    elif op == "append_code_block":
        code = str(operation.get("code") or "").rstrip()
        if not code:
            raise AgentPDFException("invalid_patch", "append_code_block operation requires code.")
        normalized["code"] = code
        normalized["language"] = str(operation.get("language") or "text")
    elif op == "append_table":
        columns = _string_list(operation.get("columns"))
        rows = operation.get("rows")
        if not columns:
            raise AgentPDFException("invalid_patch", "append_table operation requires columns.")
        if not isinstance(rows, list) or not rows:
            raise AgentPDFException("invalid_patch", "append_table operation requires one or more rows.")
        normalized["columns"] = columns
        normalized["rows"] = [_string_list(row) for row in rows]
    elif op == "append_image":
        raw_path = str(operation.get("path") or operation.get("image_path") or "").strip()
        if not raw_path:
            raise AgentPDFException("invalid_patch", "append_image operation requires path.")
        image_path = Path(raw_path).resolve()
        if not image_path.exists():
            raise AgentPDFException("file_not_found", f"Patch image not found: {image_path}")
        normalized["path"] = image_path.as_posix()
        normalized["caption"] = str(operation.get("caption") or "")
    elif op == "append_slide":
        body = operation.get("body")
        normalized["body"] = _string_list(body) if isinstance(body, list) else [str(body)] if body else []
        if operation.get("subtitle"):
            normalized["subtitle"] = str(operation["subtitle"])
        if operation.get("code"):
            normalized["code"] = str(operation["code"])
        if operation.get("table"):
            normalized["table"] = _normalize_table(operation["table"])
        raw_image_path = str(operation.get("image_path") or operation.get("path") or "").strip()
        if raw_image_path:
            image_path = Path(raw_image_path).resolve()
            if not image_path.exists():
                raise AgentPDFException("file_not_found", f"Patch slide image not found: {image_path}")
            normalized["image_path"] = image_path.as_posix()
    elif op == "append_citation":
        source = str(operation.get("source") or "").strip()
        if not source:
            raise AgentPDFException("invalid_patch", "append_citation operation requires source.")
        normalized["source"] = source
        normalized["quote"] = str(operation.get("quote") or "").strip()
        normalized["page"] = str(operation.get("page") or "").strip()
        citation_evidence = operation.get("citation_evidence")
        normalized["citation_evidence"] = citation_evidence if isinstance(citation_evidence, dict) else {}
    elif op == "append_media_reference":
        media_path = str(operation.get("media_path") or operation.get("path") or operation.get("media") or "").strip()
        if not media_path:
            raise AgentPDFException("invalid_patch", "append_media_reference operation requires media_path.")
        normalized["media_path"] = media_path
        normalized["media_kind"] = _normalize_media_kind(operation.get("media_kind"))
        transcript_excerpt = str(operation.get("transcript_excerpt") or "").strip()
        if transcript_excerpt:
            normalized["transcript_excerpt"] = transcript_excerpt
        duration_seconds = _optional_nonnegative_float(operation.get("duration_seconds"), "duration_seconds")
        if duration_seconds is not None:
            normalized["duration_seconds"] = duration_seconds
        chapter_count = _optional_nonnegative_int(operation.get("chapter_count"), "chapter_count")
        if chapter_count is not None:
            normalized["chapter_count"] = chapter_count
        keyframe_count = _optional_nonnegative_int(operation.get("keyframe_count"), "keyframe_count")
        if keyframe_count is not None:
            normalized["keyframe_count"] = keyframe_count
        media_evidence = operation.get("media_evidence")
        normalized["media_evidence"] = media_evidence if isinstance(media_evidence, dict) else {}
    elif op == "regenerate_block":
        replacement_markdown = str(
            operation.get("replacement_markdown") or operation.get("markdown") or ""
        ).strip()
        if not replacement_markdown:
            raise AgentPDFException(
                "invalid_patch",
                "regenerate_block operation requires replacement_markdown.",
            )
        if not any(target_layer_refs.values()) and not any(target_html_layer_refs.values()):
            raise AgentPDFException(
                "invalid_patch",
                "regenerate_block operation requires layer_id, block_id, target_slot, or html_layer_id.",
            )
        if not normalized["source_refs"]:
            raise AgentPDFException(
                "invalid_patch",
                "regenerate_block operation requires source_refs for audit evidence.",
            )
        normalized["replacement_markdown"] = replacement_markdown
        has_html_layer_target = any(target_html_layer_refs.values())
        regeneration_policy = {
            "requested_effect": "regenerate_html_layer" if has_html_layer_target else "regenerate_template_block",
            "actual_effect": (
                "html_layer_rerender"
                if has_html_layer_target
                else "append_regenerated_block_appendix"
            ),
            "mutates_original_block": False,
            "requires_new_output_path": True,
            "claims_layout_preservation": False,
            "requires_layer_evidence": True,
        }
        if has_html_layer_target:
            regeneration_policy["requires_html_layer_evidence"] = True
        normalized["regeneration_policy"] = regeneration_policy
    return normalized


def _load_manifest(patch_manifest: dict[str, Any] | str | Path) -> dict[str, Any]:
    if isinstance(patch_manifest, dict):
        manifest = patch_manifest
    else:
        path = Path(patch_manifest)
        if not path.exists():
            raise AgentPDFException("file_not_found", f"Patch manifest not found: {path}")
        manifest = json.loads(path.read_text(encoding="utf-8-sig"))
    if "patch_id" not in manifest or "operations" not in manifest:
        raise AgentPDFException("invalid_patch", "Patch manifest must include patch_id and operations.")
    _validate_loaded_patch_manifest(manifest)
    return manifest


def _validate_loaded_patch_manifest(manifest: dict[str, Any]) -> None:
    operations = manifest.get("operations")
    if not isinstance(operations, list) or not operations:
        raise AgentPDFException("invalid_patch", "Patch manifest operations must be a non-empty array.")
    for operation in operations:
        if not isinstance(operation, dict):
            raise AgentPDFException("invalid_patch", "Patch manifest operations must be objects.")
        op = str(operation.get("op") or "")
        if op not in SUPPORTED_PATCH_OPERATIONS:
            raise AgentPDFException("unsupported_patch_operation", f"Unsupported patch operation: {op}")
    layer_policy_maps = []
    for item in manifest.get("operation_layer_map", []):
        if isinstance(item, dict):
            layer_policy_maps.append(item)
    for operation in operations:
        if not isinstance(operation, dict) or not operation.get("layer_evidence"):
            continue
        target_layer_refs = operation.get("target_layer_refs") if isinstance(operation.get("target_layer_refs"), dict) else {}
        layer_policy_maps.append(
            {
                "operation_id": operation.get("operation_id"),
                "op": operation.get("op"),
                "title": operation.get("title"),
                "layer_ids": _string_list(target_layer_refs.get("layer_ids")),
                "block_ids": _string_list(target_layer_refs.get("block_ids")),
                "target_slots": _string_list(target_layer_refs.get("target_slots")),
                "matched_layer_count": len(operation.get("layer_evidence", [])),
                "matched_layers": operation.get("layer_evidence", []),
            }
        )
    _validate_operation_layer_policies(layer_policy_maps)


def _validate_operation_source_refs(
    operations: list[dict[str, Any]],
    composition_path: str | Path | None,
) -> dict[str, Any]:
    if composition_path is None:
        operation_source_map = [_operation_source_map(operation, {}) for operation in operations]
        return {
            "summary": {
                "status": "skipped",
                "reason": "composition_path_not_provided",
                "known_source_ref_count": 0,
                "known_source_refs": [],
                "requested_source_refs": sorted(_requested_source_refs(operations)),
                "missing_source_refs": [],
                "operation_count": len(operations),
            },
            "operation_source_map": operation_source_map,
        }

    payload = _load_composition_payload(composition_path)
    source_map_by_ref = _source_map_by_ref(payload.get("source_map", []))
    requested_refs = _requested_source_refs(operations)
    known_refs = set(source_map_by_ref)
    missing_refs = sorted(requested_refs - known_refs)
    operation_source_map = [_operation_source_map(operation, source_map_by_ref) for operation in operations]
    if missing_refs:
        raise AgentPDFException(
            "source_ref_not_found",
            "Patch operation source_refs were not found in the composition source map.",
            retry_hint="Run pdf.evidence.coverage_report on the composition artifact, then retry with listed source_refs.",
            details={
                "composition_path": Path(composition_path).resolve().as_posix(),
                "missing_source_refs": missing_refs,
                "known_source_refs": sorted(known_refs),
            },
        )
    return {
        "summary": {
            "status": "passed",
            "composition_path": Path(composition_path).resolve().as_posix(),
            "known_source_ref_count": len(known_refs),
            "known_source_refs": sorted(known_refs),
            "requested_source_refs": sorted(requested_refs),
            "missing_source_refs": [],
            "operation_count": len(operations),
        },
        "operation_source_map": operation_source_map,
    }


def _validate_operation_layer_refs(
    operations: list[dict[str, Any]],
    layer_manifest_path: str | Path | None,
) -> dict[str, Any]:
    if layer_manifest_path is None:
        operation_layer_map = [_operation_layer_map(operation, {}) for operation in operations]
        return {
            "summary": {
                "status": "skipped",
                "reason": "layer_manifest_path_not_provided",
                "known_layer_count": 0,
                "known_layer_ids": [],
                "requested_layer_ids": sorted(_requested_layer_ids(operations)),
                "requested_block_ids": sorted(_requested_block_ids(operations)),
                "requested_target_slots": sorted(_requested_target_slots(operations)),
                "missing_layer_refs": [],
                "operation_count": len(operations),
            },
            "operation_layer_map": operation_layer_map,
        }

    manifest = _load_layer_manifest(layer_manifest_path)
    layers = manifest.get("layers", [])
    if not isinstance(layers, list):
        raise AgentPDFException("invalid_layer_manifest", "Template layer manifest layers must be an array.")
    layer_indexes = _layer_indexes(layers)
    requested_layer_ids = _requested_layer_ids(operations)
    requested_block_ids = _requested_block_ids(operations)
    requested_target_slots = _requested_target_slots(operations)
    missing_layer_refs = [
        *[f"layer_id:{layer_id}" for layer_id in sorted(requested_layer_ids - set(layer_indexes["by_layer_id"]))],
        *[f"block_id:{block_id}" for block_id in sorted(requested_block_ids - set(layer_indexes["by_block_id"]))],
        *[f"target_slot:{slot}" for slot in sorted(requested_target_slots - set(layer_indexes["by_target_slot"]))],
    ]
    operation_layer_map = [_operation_layer_map(operation, layer_indexes) for operation in operations]
    unmatched_operations = [
        item["operation_id"]
        for item in operation_layer_map
        if (
            item["layer_ids"]
            or item["block_ids"]
            or item["target_slots"]
        )
        and item["matched_layer_count"] == 0
    ]
    if unmatched_operations:
        missing_layer_refs.extend([f"operation:{operation_id}" for operation_id in unmatched_operations])
    if missing_layer_refs:
        raise AgentPDFException(
            "layer_ref_not_found",
            "Patch operation layer references were not found in the template layer manifest.",
            retry_hint="Inspect the .layers.json artifact and retry with layer_id, block_id, or target_slot values from it.",
            details={
                "layer_manifest_path": Path(layer_manifest_path).resolve().as_posix(),
                "missing_layer_refs": missing_layer_refs,
                "known_layer_ids": sorted(layer_indexes["by_layer_id"]),
                "known_block_ids": sorted(layer_indexes["by_block_id"]),
                "known_target_slots": sorted(layer_indexes["by_target_slot"]),
            },
        )
    _validate_operation_layer_policies(operation_layer_map)
    return {
        "summary": {
            "status": "passed",
            "layer_manifest_path": Path(layer_manifest_path).resolve().as_posix(),
            "template_layer_manifest_id": manifest.get("template_layer_manifest_id"),
            "known_layer_count": len(layer_indexes["by_layer_id"]),
            "known_layer_ids": sorted(layer_indexes["by_layer_id"]),
            "requested_layer_ids": sorted(requested_layer_ids),
            "requested_block_ids": sorted(requested_block_ids),
            "requested_target_slots": sorted(requested_target_slots),
            "missing_layer_refs": [],
            "operation_count": len(operations),
        },
        "operation_layer_map": operation_layer_map,
    }


def _validate_operation_html_layer_refs(
    operations: list[dict[str, Any]],
    artifact_graph_path: str | Path | None,
) -> dict[str, Any]:
    if artifact_graph_path is None:
        operation_html_layer_map = [_operation_html_layer_map(operation, {}) for operation in operations]
        return {
            "summary": {
                "status": "skipped",
                "reason": "artifact_graph_path_not_provided",
                "known_html_layer_count": 0,
                "known_html_layer_ids": [],
                "requested_html_layer_ids": sorted(_requested_html_layer_ids(operations)),
                "missing_html_layer_refs": [],
                "operation_count": len(operations),
            },
            "operation_html_layer_map": operation_html_layer_map,
        }

    graph = _load_artifact_graph(artifact_graph_path)
    html_layer_index = graph.get("html_layer_index")
    if not isinstance(html_layer_index, dict):
        raise AgentPDFException("invalid_artifact_graph", "Artifact graph html_layer_index must be an object.")
    requested_html_layer_ids = _requested_html_layer_ids(operations)
    known_html_layer_ids = {str(layer_id) for layer_id in html_layer_index if layer_id}
    missing_html_layer_refs = [
        f"html_layer_id:{layer_id}"
        for layer_id in sorted(requested_html_layer_ids - known_html_layer_ids)
    ]
    operation_html_layer_map = [_operation_html_layer_map(operation, html_layer_index) for operation in operations]
    unmatched_operations = [
        item["operation_id"]
        for item in operation_html_layer_map
        if item["html_layer_ids"] and item["matched_html_layer_count"] == 0
    ]
    if unmatched_operations:
        missing_html_layer_refs.extend([f"operation:{operation_id}" for operation_id in unmatched_operations])
    if missing_html_layer_refs:
        raise AgentPDFException(
            "html_layer_ref_not_found",
            "Patch operation HTML layer references were not found in the artifact graph.",
            retry_hint="Inspect the .artifact-graph.json artifact and retry with html_layer_id values from html_layer_index.",
            details={
                "artifact_graph_path": Path(artifact_graph_path).resolve().as_posix(),
                "missing_html_layer_refs": missing_html_layer_refs,
                "known_html_layer_ids": sorted(known_html_layer_ids),
            },
        )
    return {
        "summary": {
            "status": "passed",
            "artifact_graph_path": Path(artifact_graph_path).resolve().as_posix(),
            "artifact_graph_id": graph.get("artifact_graph_id"),
            "known_html_layer_count": len(known_html_layer_ids),
            "known_html_layer_ids": sorted(known_html_layer_ids),
            "requested_html_layer_ids": sorted(requested_html_layer_ids),
            "missing_html_layer_refs": [],
            "operation_count": len(operations),
            "bbox_precision": "estimated_dom_not_pdf_glyph_bbox",
        },
        "operation_html_layer_map": operation_html_layer_map,
    }


def _validate_operation_layer_policies(operation_layer_map: list[dict[str, Any]]) -> None:
    for item in operation_layer_map:
        op = str(item.get("op") or "")
        allowed_policy_names = _policy_names_for_patch_operation(op)
        for layer in item.get("matched_layers", []):
            if not isinstance(layer, dict):
                continue
            edit_policy = layer.get("edit_policy") if isinstance(layer.get("edit_policy"), dict) else {}
            editable = bool(edit_policy.get("editable", False))
            allowed_operations = _string_list(edit_policy.get("allowed_operations"))
            if editable and any(policy_name in allowed_operations for policy_name in allowed_policy_names):
                continue
            raise AgentPDFException(
                "layer_operation_not_allowed",
                "Patch operation is not allowed by the matched template layer edit policy.",
                retry_hint="Inspect the .layers.json edit_policy.allowed_operations and retry with an allowed operation.",
                details={
                    "operation_id": str(item.get("operation_id") or ""),
                    "op": op,
                    "layer_id": str(layer.get("layer_id") or ""),
                    "block_id": str(layer.get("block_id") or ""),
                    "target_slot": str(layer.get("target_slot") or ""),
                    "editable": editable,
                    "allowed_operations": allowed_operations,
                },
            )


def _policy_names_for_patch_operation(op: str) -> list[str]:
    if op == "append_markdown":
        return ["append_to_slot", "annotate"]
    if op in {
        "append_code_block",
        "append_table",
        "append_image",
        "append_slide",
        "append_citation",
        "append_media_reference",
    }:
        return ["append_to_slot"]
    return [op]


def _load_composition_payload(composition_path: str | Path) -> dict[str, Any]:
    path = Path(composition_path)
    if not path.exists():
        raise AgentPDFException("file_not_found", f"Composition artifact not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict) or "composition_ir" not in payload:
        raise AgentPDFException("invalid_composition_ir", "Composition payload must include composition_ir.")
    return payload


def _load_layer_manifest(layer_manifest_path: str | Path) -> dict[str, Any]:
    path = Path(layer_manifest_path)
    if not path.exists():
        raise AgentPDFException("file_not_found", f"Template layer manifest not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict) or "template_layer_manifest_id" not in payload:
        raise AgentPDFException("invalid_layer_manifest", "Layer manifest must include template_layer_manifest_id.")
    return payload


def _load_artifact_graph(artifact_graph_path: str | Path) -> dict[str, Any]:
    path = Path(artifact_graph_path)
    if not path.exists():
        raise AgentPDFException("file_not_found", f"Artifact graph not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict) or "artifact_graph_version" not in payload:
        raise AgentPDFException("invalid_artifact_graph", "Artifact graph must include artifact_graph_version.")
    return payload


def _source_map_by_ref(source_map: Any) -> dict[str, list[dict[str, Any]]]:
    if not isinstance(source_map, list):
        raise AgentPDFException("invalid_composition_ir", "Composition source_map must be an array.")
    by_ref: dict[str, list[dict[str, Any]]] = {}
    for mapping in source_map:
        if not isinstance(mapping, dict):
            continue
        source_ref = str(mapping.get("source_ref") or "").strip()
        if not source_ref:
            continue
        by_ref.setdefault(source_ref, []).append(dict(mapping))
    return by_ref


def _layer_indexes(layers: list[Any]) -> dict[str, dict[str, Any] | dict[str, list[dict[str, Any]]]]:
    by_layer_id: dict[str, dict[str, Any]] = {}
    by_block_id: dict[str, list[dict[str, Any]]] = {}
    by_target_slot: dict[str, list[dict[str, Any]]] = {}
    for raw_layer in layers:
        if not isinstance(raw_layer, dict):
            continue
        layer = dict(raw_layer)
        layer_id = str(layer.get("layer_id") or "").strip()
        block_id = str(layer.get("block_id") or "").strip()
        target_slot = str(layer.get("target_slot") or "").strip()
        if layer_id:
            by_layer_id[layer_id] = layer
        if block_id:
            by_block_id.setdefault(block_id, []).append(layer)
        if target_slot:
            by_target_slot.setdefault(target_slot, []).append(layer)
    return {
        "by_layer_id": by_layer_id,
        "by_block_id": by_block_id,
        "by_target_slot": by_target_slot,
    }


def _requested_source_refs(operations: list[dict[str, Any]]) -> set[str]:
    return {
        source_ref
        for operation in operations
        for source_ref in operation.get("source_refs", [])
        if source_ref
    }


def _requested_layer_ids(operations: list[dict[str, Any]]) -> set[str]:
    return {
        layer_id
        for operation in operations
        for layer_id in operation.get("target_layer_refs", {}).get("layer_ids", [])
        if layer_id
    }


def _requested_block_ids(operations: list[dict[str, Any]]) -> set[str]:
    return {
        block_id
        for operation in operations
        for block_id in operation.get("target_layer_refs", {}).get("block_ids", [])
        if block_id
    }


def _requested_target_slots(operations: list[dict[str, Any]]) -> set[str]:
    return {
        target_slot
        for operation in operations
        for target_slot in operation.get("target_layer_refs", {}).get("target_slots", [])
        if target_slot
    }


def _requested_html_layer_ids(operations: list[dict[str, Any]]) -> set[str]:
    return {
        html_layer_id
        for operation in operations
        for html_layer_id in operation.get("target_html_layer_refs", {}).get("html_layer_ids", [])
        if html_layer_id
    }


def _operation_source_map(
    operation: dict[str, Any],
    source_map_by_ref: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    matched_sources = [
        mapping
        for source_ref in operation.get("source_refs", [])
        for mapping in source_map_by_ref.get(source_ref, [])
    ]
    operation["source_map_evidence"] = matched_sources
    return {
        "operation_id": operation["operation_id"],
        "op": operation["op"],
        "title": operation.get("title"),
        "source_refs": operation.get("source_refs", []),
        "matched_source_count": len(matched_sources),
        "matched_sources": matched_sources,
    }


def _operation_layer_map(
    operation: dict[str, Any],
    layer_indexes: dict[str, Any],
) -> dict[str, Any]:
    target_layer_refs = operation.get("target_layer_refs", {})
    layer_ids = _string_list(target_layer_refs.get("layer_ids"))
    block_ids = _string_list(target_layer_refs.get("block_ids"))
    target_slots = _string_list(target_layer_refs.get("target_slots"))
    matched_layers = _matched_layers(
        layer_ids=layer_ids,
        block_ids=block_ids,
        target_slots=target_slots,
        layer_indexes=layer_indexes,
    )
    operation["layer_evidence"] = matched_layers
    return {
        "operation_id": operation["operation_id"],
        "op": operation["op"],
        "title": operation.get("title"),
        "layer_ids": layer_ids,
        "block_ids": block_ids,
        "target_slots": target_slots,
        "matched_layer_count": len(matched_layers),
        "matched_layers": matched_layers,
    }


def _operation_html_layer_map(
    operation: dict[str, Any],
    html_layer_index: dict[str, Any],
) -> dict[str, Any]:
    target_html_layer_refs = operation.get("target_html_layer_refs", {})
    html_layer_ids = _string_list(target_html_layer_refs.get("html_layer_ids"))
    matched_html_layers = _matched_html_layers(html_layer_ids, html_layer_index)
    operation["html_layer_evidence"] = matched_html_layers
    return {
        "operation_id": operation["operation_id"],
        "op": operation["op"],
        "title": operation.get("title"),
        "html_layer_ids": html_layer_ids,
        "matched_html_layer_count": len(matched_html_layers),
        "matched_html_layers": matched_html_layers,
    }


def _matched_html_layers(
    html_layer_ids: list[str],
    html_layer_index: dict[str, Any],
) -> list[dict[str, Any]]:
    if not html_layer_index:
        return []
    matched_layers = []
    seen = set()
    for html_layer_id in html_layer_ids:
        if html_layer_id in seen:
            continue
        raw_layer = html_layer_index.get(html_layer_id)
        if not isinstance(raw_layer, dict):
            continue
        seen.add(html_layer_id)
        matched_layers.append(_html_layer_evidence(raw_layer, fallback_layer_id=html_layer_id))
    return matched_layers


def _html_layer_evidence(raw_layer: dict[str, Any], *, fallback_layer_id: str) -> dict[str, Any]:
    layer_id = str(raw_layer.get("layer_id") or fallback_layer_id)
    return _drop_empty_values(
        {
            "layer_id": layer_id,
            "graph_node_id": raw_layer.get("node_id"),
            "html_package_id": raw_layer.get("html_package_id"),
            "path": raw_layer.get("path"),
            "html_path": raw_layer.get("html_path"),
            "block_id": raw_layer.get("block_id"),
            "block_type": raw_layer.get("block_type"),
            "target_slot": raw_layer.get("target_slot"),
            "source_refs": _string_list(raw_layer.get("source_refs")),
            "anchor": raw_layer.get("anchor") if isinstance(raw_layer.get("anchor"), dict) else {},
            "bbox_precision": raw_layer.get("bbox_precision") or "estimated_dom_not_pdf_glyph_bbox",
        }
    )


def _matched_layers(
    layer_ids: list[str],
    block_ids: list[str],
    target_slots: list[str],
    layer_indexes: dict[str, Any],
) -> list[dict[str, Any]]:
    if not layer_indexes:
        return []
    by_layer_id = layer_indexes.get("by_layer_id", {})
    by_block_id = layer_indexes.get("by_block_id", {})
    by_target_slot = layer_indexes.get("by_target_slot", {})
    candidates: list[dict[str, Any]] | None = None
    if layer_ids:
        candidates = [
            by_layer_id[layer_id]
            for layer_id in layer_ids
            if layer_id in by_layer_id
        ]
    if block_ids:
        block_matches = [
            layer
            for block_id in block_ids
            for layer in by_block_id.get(block_id, [])
        ]
        candidates = _intersect_layers(candidates, block_matches) if candidates is not None else block_matches
    if target_slots:
        slot_matches = [
            layer
            for target_slot in target_slots
            for layer in by_target_slot.get(target_slot, [])
        ]
        candidates = _intersect_layers(candidates, slot_matches) if candidates is not None else slot_matches
    return _unique_layers(candidates or [])


def _intersect_layers(
    left: list[dict[str, Any]] | None,
    right: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if left is None:
        return right
    right_ids = {str(layer.get("layer_id") or "") for layer in right}
    return [
        layer
        for layer in left
        if str(layer.get("layer_id") or "") in right_ids
    ]


def _unique_layers(layers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    unique = []
    for layer in layers:
        layer_id = str(layer.get("layer_id") or "")
        if not layer_id or layer_id in seen:
            continue
        seen.add(layer_id)
        unique.append(layer)
    return unique


def _operation_markdown(operation: dict[str, Any], manifest: dict[str, Any]) -> str:
    body = _operation_markdown_body(operation)
    return f"# {operation.get('title')}\n\n{body}\n\n{_patch_evidence_markdown(operation, manifest)}"


def _operation_markdown_body(operation: dict[str, Any]) -> str:
    op = operation["op"]
    title = str(operation.get("title") or "Patch Operation")
    if op == "append_markdown":
        return str(operation["markdown"])
    if op == "append_code_block":
        language = str(operation.get("language") or "text")
        return f"## {title}\n\n```{language}\n{operation['code']}\n```"
    if op == "append_table":
        return f"## {title}\n\n{_format_markdown_table(operation['columns'], operation['rows'])}"
    if op == "append_image":
        caption = str(operation.get("caption") or "")
        image_path = str(operation["path"])
        caption_block = f"{caption}\n\n" if caption else ""
        return f"## {title}\n\n{caption_block}![{title}](<{image_path}>)"
    if op == "append_slide":
        body = "\n".join(f"- {item}" for item in operation.get("body", []))
        return f"## {title}\n\n{body}"
    if op == "append_citation":
        quote = str(operation.get("quote") or "")
        source = str(operation.get("source") or "")
        page = str(operation.get("page") or "")
        evidence = operation.get("citation_evidence") if isinstance(operation.get("citation_evidence"), dict) else {}
        lines = [f"## {title}", ""]
        if quote:
            lines.extend([f"> {quote}", ""])
        lines.append(f"Source: {source}")
        if page:
            lines.append(f"Page: {page}")
        if evidence:
            lines.extend(["", "### Citation Evidence", ""])
            for key in ("normalized_url", "domain", "path", "query", "fragment", "fetch_status", "analysis_method"):
                if evidence.get(key) is not None:
                    lines.append(f"- {key}: `{evidence[key]}`")
        return "\n".join(lines)
    if op == "append_media_reference":
        media_path = str(operation.get("media_path") or "")
        media_kind = str(operation.get("media_kind") or "media")
        transcript_excerpt = str(operation.get("transcript_excerpt") or "")
        evidence = operation.get("media_evidence") if isinstance(operation.get("media_evidence"), dict) else {}
        lines = [
            f"## {title}",
            "",
            f"Media kind: `{media_kind}`",
            f"Media reference: `{media_path}`",
        ]
        if operation.get("duration_seconds") is not None:
            lines.append(f"Duration seconds: `{operation['duration_seconds']}`")
        if operation.get("chapter_count") is not None:
            lines.append(f"Chapter count: `{operation['chapter_count']}`")
        if operation.get("keyframe_count") is not None:
            lines.append(f"Keyframe count: `{operation['keyframe_count']}`")
        if transcript_excerpt:
            lines.extend(["", "### Transcript Excerpt", "", transcript_excerpt])
        if evidence:
            lines.extend(["", "### Local Media Evidence", ""])
            for key in (
                "reference_type",
                "filename",
                "mime_type",
                "size_bytes",
                "sha256",
                "exists",
                "fetch_status",
                "analysis_method",
                "normalized_url",
                "domain",
            ):
                if evidence.get(key) is not None:
                    lines.append(f"- {key}: `{evidence[key]}`")
        return "\n".join(lines)
    if op == "regenerate_block":
        replacement = str(operation["replacement_markdown"])
        return (
            f"## {title}\n\n"
            f"{replacement}\n\n"
            "## Regeneration Policy\n\n"
            "- Requested effect: regenerate template block\n"
            "- Actual effect: append regenerated block appendix\n"
            "- Original template block was not mutated\n"
            "- Layout preservation is not claimed\n"
        )
    raise AgentPDFException("unsupported_patch_operation", f"Unsupported patch operation: {op}")


def _operation_slide(operation: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    source_refs = operation.get("source_refs") or []
    refs = ", ".join(str(ref) for ref in source_refs) if source_refs else "none"
    body = list(operation.get("body", []))
    body.extend(
        [
            "Patch Evidence",
            f"Patch id: {manifest['patch_id']}",
            f"Operation id: {operation['operation_id']}",
            f"Source refs: {refs}",
            "Input PDF was not mutated; this slide was appended to a new output artifact.",
        ]
    )
    source_map_lines = _source_map_evidence_lines(operation)
    if source_map_lines:
        body.extend(["Matched Source Map Evidence", *source_map_lines])
    layer_lines = _layer_evidence_lines(operation)
    if layer_lines:
        body.extend(["Matched Template Layer Evidence", *layer_lines])
    html_layer_lines = _html_layer_evidence_lines(operation)
    if html_layer_lines:
        body.extend(["Matched HTML Layer Evidence", *html_layer_lines])
    slide = {
        "title": operation.get("title") or "Patch Slide",
        "subtitle": operation.get("subtitle") or "Patch transaction appendix",
        "body": body,
        "source_refs": source_refs,
    }
    for key in ("code", "table", "image_path"):
        if operation.get(key):
            slide[key] = operation[key]
    return slide


def _patch_evidence_markdown(operation: dict[str, Any], manifest: dict[str, Any]) -> str:
    source_refs = operation.get("source_refs") or []
    refs = ", ".join(f"`{ref}`" for ref in source_refs) if source_refs else "none"
    source_map_evidence = _source_map_evidence_markdown(operation)
    layer_evidence = _layer_evidence_markdown(operation)
    html_layer_evidence = _html_layer_evidence_markdown(operation)
    return (
        "## Patch Evidence\n\n"
        f"- Patch id: `{manifest['patch_id']}`\n"
        f"- Operation id: `{operation['operation_id']}`\n"
        f"- Source refs: {refs}\n"
        "- Input PDF was not mutated; this page was appended to a new output artifact.\n"
        f"{source_map_evidence}"
        f"{layer_evidence}"
        f"{html_layer_evidence}"
    )


def _format_markdown_table(columns: list[str], rows: list[list[str]]) -> str:
    header = "| " + " | ".join(_escape_markdown_table_cell(column) for column in columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"
    body = []
    for row in rows:
        padded = row[: len(columns)] + [""] * max(len(columns) - len(row), 0)
        body.append("| " + " | ".join(_escape_markdown_table_cell(cell) for cell in padded) + " |")
    return "\n".join([header, separator, *body])


def _normalize_table(table: Any) -> dict[str, list[Any]]:
    if not isinstance(table, dict):
        raise AgentPDFException("invalid_patch", "append_slide table must be an object with columns and rows.")
    columns = _string_list(table.get("columns"))
    rows = table.get("rows")
    if not columns or not isinstance(rows, list):
        raise AgentPDFException("invalid_patch", "append_slide table requires columns and rows.")
    return {"columns": columns, "rows": [_string_list(row) for row in rows]}


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, tuple):
        return [str(item) for item in value]
    if value is None:
        return []
    return [str(value)]


def _normalize_media_kind(value: Any) -> str:
    media_kind = str(value or "media").strip().lower().replace("-", "_")
    if media_kind in {"audio", "audio_reference", "sound"}:
        return "audio"
    if media_kind in {"video", "video_reference", "movie"}:
        return "video"
    return "media"


def _optional_nonnegative_float(value: Any, field_name: str) -> float | None:
    if value is None or value == "":
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise AgentPDFException("invalid_patch", f"{field_name} must be a number.") from exc
    if parsed < 0:
        raise AgentPDFException("invalid_patch", f"{field_name} must be non-negative.")
    return parsed


def _optional_nonnegative_int(value: Any, field_name: str) -> int | None:
    if value is None or value == "":
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise AgentPDFException("invalid_patch", f"{field_name} must be an integer.") from exc
    if parsed < 0:
        raise AgentPDFException("invalid_patch", f"{field_name} must be non-negative.")
    return parsed


def _source_refs(operation: dict[str, Any]) -> list[str]:
    source_refs = operation.get("source_refs", [])
    if isinstance(source_refs, str):
        return [source_refs]
    if isinstance(source_refs, list):
        return [str(ref) for ref in source_refs]
    return []


def _target_layer_refs(operation: dict[str, Any]) -> dict[str, list[str]]:
    return {
        "layer_ids": _string_list(operation.get("layer_ids") or operation.get("layer_id")),
        "block_ids": _string_list(operation.get("block_ids") or operation.get("block_id")),
        "target_slots": _string_list(operation.get("target_slots") or operation.get("target_slot")),
    }


def _target_html_layer_refs(operation: dict[str, Any]) -> dict[str, list[str]]:
    target_html_layer_refs = (
        operation.get("target_html_layer_refs")
        if isinstance(operation.get("target_html_layer_refs"), dict)
        else {}
    )
    return {
        "html_layer_ids": _string_list(
            operation.get("html_layer_ids")
            or operation.get("html_layer_id")
            or target_html_layer_refs.get("html_layer_ids")
            or target_html_layer_refs.get("html_layer_id")
        ),
    }


def _operation_expected_effect(operation: dict[str, Any]) -> str:
    if operation["op"] == "regenerate_block" and operation.get("target_html_layer_refs"):
        return (
            "write a patched HTML source package and rerender a new PDF; original PDF and "
            "HTML source remain unchanged"
        )
    return {
        "append_markdown": "append one or more audited markdown pages",
        "append_code_block": "append one or more audited code appendix pages",
        "append_table": "append one or more audited table appendix pages",
        "append_image": "append one or more audited image appendix pages",
        "append_slide": "append one audited landscape slide page",
        "append_citation": "append one audited citation evidence page",
        "append_media_reference": "append one audited media reference evidence page",
        "regenerate_block": (
            "append an audited regenerated block appendix; original template block remains unchanged"
        ),
    }.get(operation["op"], "append one or more pages")


def _source_map_evidence_markdown(operation: dict[str, Any]) -> str:
    lines = _source_map_evidence_lines(operation)
    if not lines:
        return ""
    return "\n### Matched Source Map Evidence\n\n" + "\n".join(f"- {line}" for line in lines) + "\n"


def _layer_evidence_markdown(operation: dict[str, Any]) -> str:
    lines = _layer_evidence_lines(operation)
    if not lines:
        return ""
    return "\n### Matched Template Layer Evidence\n\n" + "\n".join(f"- {line}" for line in lines) + "\n"


def _html_layer_evidence_markdown(operation: dict[str, Any]) -> str:
    lines = _html_layer_evidence_lines(operation)
    if not lines:
        return ""
    return "\n### Matched HTML Layer Evidence\n\n" + "\n".join(f"- {line}" for line in lines) + "\n"


def _source_map_evidence_lines(operation: dict[str, Any]) -> list[str]:
    lines = []
    for mapping in operation.get("source_map_evidence", []):
        if not isinstance(mapping, dict):
            continue
        source_ref = str(mapping.get("source_ref") or "unknown")
        block_id = str(mapping.get("block_id") or "unknown_block")
        source_kind = str(mapping.get("source_kind") or "unknown_kind")
        target_slot = str(mapping.get("target_slot") or "unknown_slot")
        template_id = str(mapping.get("template_id") or "")
        suffix = f", template: `{template_id}`" if template_id else ""
        lines.append(
            f"`{block_id}` from `{source_ref}` ({source_kind}, slot: `{target_slot}`{suffix})"
        )
    return lines


def _layer_evidence_lines(operation: dict[str, Any]) -> list[str]:
    lines = []
    for layer in operation.get("layer_evidence", []):
        if not isinstance(layer, dict):
            continue
        layer_id = str(layer.get("layer_id") or "unknown_layer")
        block_id = str(layer.get("block_id") or "unknown_block")
        target_slot = str(layer.get("target_slot") or "unknown_slot")
        anchor = layer.get("anchor") if isinstance(layer.get("anchor"), dict) else {}
        anchor_kind = str(anchor.get("anchor_kind") or "unknown_anchor")
        edit_policy = layer.get("edit_policy") if isinstance(layer.get("edit_policy"), dict) else {}
        editable = edit_policy.get("editable", False)
        lines.append(
            f"`{layer_id}` for block `{block_id}` (slot: `{target_slot}`, anchor: `{anchor_kind}`, editable: `{editable}`)"
        )
    return lines


def _html_layer_evidence_lines(operation: dict[str, Any]) -> list[str]:
    lines = []
    for layer in operation.get("html_layer_evidence", []):
        if not isinstance(layer, dict):
            continue
        layer_id = str(layer.get("layer_id") or "unknown_html_layer")
        block_id = str(layer.get("block_id") or "unknown_block")
        block_type = str(layer.get("block_type") or "unknown_type")
        target_slot = str(layer.get("target_slot") or "unknown_slot")
        anchor = layer.get("anchor") if isinstance(layer.get("anchor"), dict) else {}
        selector = str(anchor.get("dom_selector") or "unknown_selector")
        bbox_precision = str(layer.get("bbox_precision") or anchor.get("bbox_precision") or "unknown_precision")
        lines.append(
            f"`{layer_id}` for block `{block_id}` ({block_type}, slot: `{target_slot}`, "
            f"selector: `{selector}`, bbox: `{bbox_precision}`)"
        )
    return lines


def _manifest_matched_source_count(manifest: dict[str, Any]) -> int:
    return sum(
        int(operation_map.get("matched_source_count") or 0)
        for operation_map in manifest.get("operation_source_map", [])
        if isinstance(operation_map, dict)
    )


def _manifest_matched_layer_count(manifest: dict[str, Any]) -> int:
    return sum(
        int(operation_map.get("matched_layer_count") or 0)
        for operation_map in manifest.get("operation_layer_map", [])
        if isinstance(operation_map, dict)
    )


def _manifest_matched_html_layer_count(manifest: dict[str, Any]) -> int:
    return sum(
        int(operation_map.get("matched_html_layer_count") or 0)
        for operation_map in manifest.get("operation_html_layer_map", [])
        if isinstance(operation_map, dict)
    )


def _drop_empty_values(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if value not in (None, "", [], {})}


def _escape_markdown_table_cell(value: str) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def _sha256_matches(path: Path, expected: str) -> bool:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest() == expected
