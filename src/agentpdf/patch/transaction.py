from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from pypdf import PdfReader, PdfWriter

from agentpdf.artifacts.store import build_artifact
from agentpdf.core.pdf import create_markdown_pdf, create_slide_deck_pdf
from agentpdf.schemas.errors import AgentPDFException
from agentpdf.schemas.models import ToolResult
from agentpdf.validation.pdf import validate_pdf


SUPPORTED_PATCH_OPERATIONS = [
    "append_markdown",
    "append_code_block",
    "append_table",
    "append_image",
    "append_slide",
]


def plan_patch_transaction(
    input_path: str | Path,
    operations: list[dict[str, Any]],
    output_path: str | Path,
    composition_path: str | Path | None = None,
    layer_manifest_path: str | Path | None = None,
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
    source_artifact = build_artifact(source, source_tool="pdf.patch.input")
    manifest = {
        "patch_manifest_version": "0.1",
        "patch_id": f"patch_{uuid4().hex[:16]}",
        "input_path": source.as_posix(),
        "input_artifact": source_artifact.model_dump(mode="json"),
        "composition_path": Path(composition_path).resolve().as_posix() if composition_path else None,
        "layer_manifest_path": Path(layer_manifest_path).resolve().as_posix() if layer_manifest_path else None,
        "reason": reason or "",
        "operation_count": len(normalized_operations),
        "operations": normalized_operations,
        "source_ref_validation": source_ref_validation["summary"],
        "operation_source_map": source_ref_validation["operation_source_map"],
        "layer_ref_validation": layer_ref_validation["summary"],
        "operation_layer_map": layer_ref_validation["operation_layer_map"],
        "safety": {
            "mutates_input": False,
            "requires_new_output_path": True,
            "supported_operations": SUPPORTED_PATCH_OPERATIONS,
            "supports_layer_anchors": True,
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
            "matched_layer_count": len(operation.get("layer_evidence", [])),
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
        "matched_source_count": _manifest_matched_source_count(manifest),
        "matched_layer_count": _manifest_matched_layer_count(manifest),
        "source_ref_validation": manifest.get("source_ref_validation", {}),
        "layer_ref_validation": manifest.get("layer_ref_validation", {}),
        "operation_source_map": manifest.get("operation_source_map", []),
        "operation_layer_map": manifest.get("operation_layer_map", []),
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
    return normalized


def _load_manifest(patch_manifest: dict[str, Any] | str | Path) -> dict[str, Any]:
    if isinstance(patch_manifest, dict):
        manifest = patch_manifest
    else:
        path = Path(patch_manifest)
        if not path.exists():
            raise AgentPDFException("file_not_found", f"Patch manifest not found: {path}")
        manifest = json.loads(path.read_text(encoding="utf-8"))
    if "patch_id" not in manifest or "operations" not in manifest:
        raise AgentPDFException("invalid_patch", "Patch manifest must include patch_id and operations.")
    return manifest


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


def _load_composition_payload(composition_path: str | Path) -> dict[str, Any]:
    path = Path(composition_path)
    if not path.exists():
        raise AgentPDFException("file_not_found", f"Composition artifact not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or "composition_ir" not in payload:
        raise AgentPDFException("invalid_composition_ir", "Composition payload must include composition_ir.")
    return payload


def _load_layer_manifest(layer_manifest_path: str | Path) -> dict[str, Any]:
    path = Path(layer_manifest_path)
    if not path.exists():
        raise AgentPDFException("file_not_found", f"Template layer manifest not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or "template_layer_manifest_id" not in payload:
        raise AgentPDFException("invalid_layer_manifest", "Layer manifest must include template_layer_manifest_id.")
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
    return (
        "## Patch Evidence\n\n"
        f"- Patch id: `{manifest['patch_id']}`\n"
        f"- Operation id: `{operation['operation_id']}`\n"
        f"- Source refs: {refs}\n"
        "- Input PDF was not mutated; this page was appended to a new output artifact.\n"
        f"{source_map_evidence}"
        f"{layer_evidence}"
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


def _operation_expected_effect(operation: dict[str, Any]) -> str:
    return {
        "append_markdown": "append one or more audited markdown pages",
        "append_code_block": "append one or more audited code appendix pages",
        "append_table": "append one or more audited table appendix pages",
        "append_image": "append one or more audited image appendix pages",
        "append_slide": "append one audited landscape slide page",
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


def _escape_markdown_table_cell(value: str) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def _sha256_matches(path: Path, expected: str) -> bool:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest() == expected
