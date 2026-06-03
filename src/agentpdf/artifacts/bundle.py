from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4
from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile

from agentpdf.artifacts.store import build_artifact
from agentpdf.evidence.source_map import map_sources
from agentpdf.schemas.errors import AgentPDFException
from agentpdf.schemas.models import ToolResult, ValidationCheck, ValidationReport


def create_artifact_manifest(
    artifact_paths: list[str | Path],
    output_path: str | Path | None = None,
    title: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> ToolResult:
    tool = "pdf.artifacts.manifest"
    if not artifact_paths:
        raise AgentPDFException("invalid_input", "artifact_paths must include at least one file.")

    input_artifacts = [_input_artifact(path) for path in artifact_paths]
    manifest_entries: list[dict[str, Any]] = []
    evidence_links: dict[str, list[str]] = {}
    source_refs: set[str] = set()
    json_parse_warnings: list[str] = []

    for artifact in input_artifacts:
        path = artifact.path
        artifact_kind = _artifact_kind(path)
        entry = {
            **artifact.model_dump(mode="json"),
            "artifact_kind": artifact_kind,
            "retention_hint": artifact.retention_hint,
        }
        if artifact_kind != "file":
            evidence_links.setdefault(artifact_kind, []).append(path.as_posix())

        json_payload = _read_json_artifact(path, warnings=json_parse_warnings)
        if isinstance(json_payload, dict):
            entry["json_top_level_keys"] = sorted(str(key) for key in json_payload.keys())
            extracted_refs = sorted(_collect_source_refs(json_payload))
            entry["source_refs"] = extracted_refs
            source_refs.update(extracted_refs)
            if "validation" in json_payload:
                evidence_links.setdefault("validation", []).append(path.as_posix())
        manifest_entries.append(entry)

    sorted_source_refs = sorted(source_refs)
    artifact_manifest = {
        "manifest_version": "0.1",
        "manifest_id": f"artifact_manifest_{uuid4().hex[:16]}",
        "title": title or "AgentPDF Artifact Manifest",
        "created_at": datetime.now(UTC).isoformat(),
        "artifact_count": len(manifest_entries),
        "metadata": _json_safe_dict(metadata or {}),
        "artifacts": manifest_entries,
        "evidence_links": {key: sorted(paths) for key, paths in sorted(evidence_links.items())},
        "source_refs": sorted_source_refs,
        "source_ref_count": len(sorted_source_refs),
        "safety": {
            "contains_input_hashes": True,
            "mutates_inputs": False,
            "paths_are_resolved": True,
        },
    }

    artifacts = []
    if output_path is not None:
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(artifact_manifest, indent=2), encoding="utf-8")
        artifacts.append(build_artifact(destination, source_tool=tool))

    return ToolResult(
        job_id=f"job_{uuid4().hex[:16]}",
        status="succeeded",
        tool=tool,
        artifacts=artifacts,
        warnings=json_parse_warnings,
        usage={
            "artifact_manifest": artifact_manifest,
            "artifact_count": len(manifest_entries),
            "source_ref_count": len(sorted_source_refs),
            "evidence_link_count": sum(len(paths) for paths in evidence_links.values()),
            "total_input_bytes": sum(int(entry["size_bytes"]) for entry in manifest_entries),
        },
        next_recommended_tools=["pdf.artifacts.export_bundle", "pdf.artifacts.graph"],
    )


def build_artifact_graph(
    artifact_manifest_path: str | Path | None = None,
    artifact_paths: list[str | Path] | None = None,
    output_path: str | Path | None = None,
    title: str | None = None,
) -> ToolResult:
    tool = "pdf.artifacts.graph"
    manifest, manifest_path = _load_graph_manifest(
        artifact_manifest_path=artifact_manifest_path,
        artifact_paths=artifact_paths or [],
    )
    artifact_entries = manifest.get("artifacts")
    if not isinstance(artifact_entries, list) or not artifact_entries:
        raise AgentPDFException("invalid_input", "Artifact graph input manifest must include at least one artifact.")

    manifest_id = str(manifest.get("manifest_id") or f"artifact_manifest_inline_{uuid4().hex[:8]}")
    graph_title = title or str(manifest.get("title") or "AgentPDF Artifact Graph")
    manifest_node_id = f"manifest:{manifest_id}"
    nodes: list[dict[str, Any]] = [
        {
            "id": manifest_node_id,
            "type": "manifest",
            "label": graph_title,
            "manifest_id": manifest_id,
            "path": manifest_path.as_posix() if manifest_path else None,
            "artifact_count": len(artifact_entries),
        }
    ]
    edges: list[dict[str, Any]] = []
    source_ref_index: dict[str, dict[str, Any]] = {}
    artifact_ids_by_kind: dict[str, list[str]] = {}
    artifact_node_ids_by_path: dict[str, str] = {}

    for index, entry in enumerate(artifact_entries, start=1):
        if not isinstance(entry, dict):
            continue
        artifact_id = _artifact_node_id(entry, index)
        path = str(entry.get("path") or entry.get("source_path") or "")
        artifact_kind = str(entry.get("artifact_kind") or _artifact_kind(Path(path)))
        artifact_node_ids_by_path[path] = artifact_id
        artifact_ids_by_kind.setdefault(artifact_kind, []).append(artifact_id)
        source_refs = _entry_source_refs(entry)
        nodes.append(
            {
                "id": artifact_id,
                "type": "artifact",
                "label": _artifact_label(path, index),
                "path": path,
                "artifact_kind": artifact_kind,
                "sha256": entry.get("sha256"),
                "size_bytes": entry.get("size_bytes"),
                "mime_type": entry.get("mime_type"),
                "page_count": entry.get("page_count"),
                "source_tool": entry.get("source_tool"),
                "retention_hint": entry.get("retention_hint"),
                "source_refs": source_refs,
            }
        )
        _add_edge(
            edges,
            manifest_node_id,
            artifact_id,
            "includes_artifact",
            evidence="artifact_manifest.artifacts",
            details={"artifact_kind": artifact_kind, "index": index},
        )
        for source_ref in source_refs:
            source_node_id = _source_ref_node_id(source_ref)
            indexed = source_ref_index.setdefault(
                source_ref,
                {
                    "node_id": source_node_id,
                    "artifact_ids": [],
                    "artifact_paths": [],
                    "artifact_count": 0,
                },
            )
            indexed["artifact_ids"].append(artifact_id)
            indexed["artifact_paths"].append(path)
            indexed["artifact_count"] = len(indexed["artifact_ids"])
            _add_edge(
                edges,
                artifact_id,
                source_node_id,
                "uses_source_ref",
                evidence="artifact_manifest.artifacts[].source_refs",
            )

    for source_ref, indexed in sorted(source_ref_index.items()):
        nodes.append(
            {
                "id": indexed["node_id"],
                "type": "source_ref",
                "label": source_ref,
                "source_ref": source_ref,
                "artifact_count": indexed["artifact_count"],
            }
        )

    _add_artifact_convention_edges(edges, artifact_ids_by_kind)
    evidence_link_index = _evidence_link_index(manifest, artifact_node_ids_by_path)
    warnings = []
    if not source_ref_index:
        warnings.append("Artifact graph contains no source refs; lineage is limited to artifact inclusion edges.")
    if not any(edge["relation"] != "includes_artifact" for edge in edges):
        warnings.append("Artifact graph contains no inferred lineage or source-ref edges.")

    artifact_graph = {
        "artifact_graph_version": "0.1",
        "artifact_graph_id": f"artifact_graph_{uuid4().hex[:16]}",
        "title": graph_title,
        "created_at": datetime.now(UTC).isoformat(),
        "manifest_id": manifest_id,
        "manifest_path": manifest_path.as_posix() if manifest_path else None,
        "artifact_count": len(artifact_entries),
        "source_ref_count": len(source_ref_index),
        "node_count": len(nodes),
        "edge_count": len(edges),
        "nodes": nodes,
        "edges": edges,
        "source_ref_index": source_ref_index,
        "evidence_link_index": evidence_link_index,
        "safety": {
            "mutates_inputs": False,
            "paths_are_resolved": True,
            "lineage_inference": "local_manifest_conventions",
            "inferred_edges_are_marked": True,
        },
    }

    artifacts = []
    if output_path is not None:
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(artifact_graph, indent=2), encoding="utf-8")
        artifacts.append(build_artifact(destination, source_tool=tool))

    validation = ValidationReport(
        status="passed",
        checks=[
            ValidationCheck(
                name="artifact_graph_has_artifacts",
                status="passed",
                details={"artifact_count": len(artifact_entries)},
            ),
            ValidationCheck(
                name="source_refs_indexed",
                status="passed",
                details={"source_ref_count": len(source_ref_index)},
            ),
            ValidationCheck(
                name="lineage_edges_present",
                status="passed",
                details={"edge_count": len(edges)},
            ),
        ],
        warnings=warnings,
    )
    return ToolResult(
        job_id=f"job_{uuid4().hex[:16]}",
        status="succeeded",
        tool=tool,
        artifacts=artifacts,
        validation=validation,
        warnings=warnings,
        usage={
            "artifact_graph": artifact_graph,
            "manifest_id": manifest_id,
            "artifact_count": len(artifact_entries),
            "source_ref_count": len(source_ref_index),
            "edge_count": len(edges),
        },
        next_recommended_tools=["pdf.artifacts.export_bundle", "pdf.workflow.report"],
    )


def build_artifact_source_map(
    composition: dict[str, Any] | str | Path | None = None,
    composition_path: str | Path | None = None,
    source_map: dict[str, Any] | list[dict[str, Any]] | str | Path | None = None,
    source_map_path: str | Path | None = None,
    context_packet: dict[str, Any] | str | Path | None = None,
    context_packet_path: str | Path | None = None,
    artifact_manifest_path: str | Path | None = None,
    artifact_paths: list[str | Path] | None = None,
    output_path: str | Path | None = None,
    title: str | None = None,
) -> ToolResult:
    tool = "pdf.artifacts.source_map"
    composition_input = _source_map_composition_input(
        composition=composition,
        composition_path=composition_path,
        source_map=source_map,
        source_map_path=source_map_path,
    )
    context_input = context_packet if context_packet is not None else context_packet_path
    mapped = map_sources(composition=composition_input, context_packet=context_input)
    source_map_report = mapped.usage.get("source_map_report")
    if not isinstance(source_map_report, dict):
        raise AgentPDFException("invalid_input", "Could not build source map report.")
    source_entries = mapped.usage.get("source_map")
    if not isinstance(source_entries, list):
        source_entries = []

    composition_payload = _load_optional_json(composition_input, "Composition")
    composition_ir = _composition_payload_ir(composition_payload)
    blocks = _composition_blocks_for_artifact_source_map(composition_ir)
    block_index = _artifact_block_index(blocks=blocks, source_entries=source_entries)
    source_ref_index = _artifact_source_ref_index(source_entries)
    page_index = _artifact_page_index(source_entries)
    manifest, manifest_path = _optional_artifact_manifest(
        artifact_manifest_path=artifact_manifest_path,
        artifact_paths=artifact_paths or [],
    )
    generated_artifacts = _generated_artifacts_from_manifest(manifest)
    artifact_source_map = {
        "artifact_source_map_version": "0.1",
        "artifact_source_map_id": f"artifact_srcmap_{uuid4().hex[:16]}",
        "title": title or "AgentPDF Artifact Source Map",
        "created_at": datetime.now(UTC).isoformat(),
        "composition_id": source_map_report.get("composition_id") or composition_ir.get("composition_id"),
        "context_packet_id": source_map_report.get("context_packet_id"),
        "artifact_manifest_id": manifest.get("manifest_id") if manifest else None,
        "artifact_manifest_path": manifest_path.as_posix() if manifest_path else None,
        "generated_artifacts": generated_artifacts,
        "source_map": source_entries,
        "block_index": block_index,
        "source_ref_index": source_ref_index,
        "page_index": page_index,
        "coverage": mapped.usage.get("coverage", {}),
        "unmatched_source_refs": mapped.usage.get("unmatched_source_refs", []),
        "unmapped_targets": mapped.usage.get("unmapped_targets", []),
        "source_graph": source_map_report.get("source_graph"),
        "safety": {
            "mutates_inputs": False,
            "paths_are_resolved": True,
            "uses_local_source_map_only": True,
            "does_not_infer_missing_bboxes": True,
        },
    }

    artifacts = []
    if output_path is not None:
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(artifact_source_map, indent=2), encoding="utf-8")
        artifacts.append(build_artifact(destination, source_tool=tool))

    warnings = list(mapped.warnings)
    if not generated_artifacts:
        warnings.append("No generated PDF artifacts were provided through an artifact manifest.")
    validation = ValidationReport(
        status="passed",
        checks=[
            ValidationCheck(
                name="source_map_entries_present",
                status="passed" if source_entries else "warning",
                details={"entry_count": len(source_entries)},
                message=None if source_entries else "No source map entries were found.",
            ),
            ValidationCheck(
                name="block_index_built",
                status="passed",
                details={"block_count": len(block_index)},
            ),
            ValidationCheck(
                name="source_ref_index_built",
                status="passed",
                details={"source_ref_count": len(source_ref_index)},
            ),
        ],
        warnings=warnings,
    )
    return ToolResult(
        job_id=f"job_{uuid4().hex[:16]}",
        status="succeeded",
        tool=tool,
        artifacts=artifacts,
        validation=validation,
        warnings=warnings,
        usage={
            "artifact_source_map": artifact_source_map,
            "source_map": source_entries,
            "block_count": len(block_index),
            "source_ref_count": len(source_ref_index),
            "page_ref_count": sum(len(page["mappings"]) for page in page_index.values()),
            "generated_artifact_count": len(generated_artifacts),
        },
        next_recommended_tools=["pdf.artifacts.graph", "pdf.artifacts.export_bundle", "pdf.patch.plan"],
    )


def export_artifact_bundle(
    artifact_paths: list[str | Path],
    output_path: str | Path,
    title: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> ToolResult:
    tool = "pdf.artifacts.export_bundle"
    if not artifact_paths:
        raise AgentPDFException("invalid_input", "artifact_paths must include at least one file.")

    input_artifacts = [_input_artifact(path) for path in artifact_paths]
    bundle_entries = _bundle_entries(input_artifacts)
    bundle_manifest = {
        "bundle_version": "0.1",
        "bundle_id": f"bundle_{uuid4().hex[:16]}",
        "title": title or "AgentPDF Artifact Bundle",
        "created_at": datetime.now(UTC).isoformat(),
        "artifact_count": len(bundle_entries),
        "metadata": _json_safe_dict(metadata or {}),
        "artifacts": bundle_entries,
        "safety": {
            "contains_input_hashes": True,
            "mutates_inputs": False,
            "zip_paths_are_sanitized": True,
        },
    }
    checksums = "\n".join(f"{entry['sha256']}  {entry['bundle_path']}" for entry in bundle_entries) + "\n"

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(destination, mode="w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("agentpdf-bundle-manifest.json", json.dumps(bundle_manifest, indent=2))
        archive.writestr("checksums.sha256", checksums)
        for source, entry in zip(input_artifacts, bundle_entries, strict=True):
            archive.write(source.path, entry["bundle_path"])

    artifact = build_artifact(destination, source_tool=tool)
    return ToolResult(
        job_id=f"job_{uuid4().hex[:16]}",
        status="succeeded",
        tool=tool,
        artifacts=[artifact],
        usage={
            "bundle_manifest": bundle_manifest,
            "file_count": len(bundle_entries),
            "bundle_entries": [entry["bundle_path"] for entry in bundle_entries],
            "checksums": checksums.strip().splitlines(),
            "total_input_bytes": sum(int(entry["size_bytes"]) for entry in bundle_entries),
        },
        next_recommended_tools=["pdf.workflow.report", "pdf.validation.validate_output"],
    )


def verify_artifact_bundle(bundle_path: str | Path) -> ToolResult:
    tool = "pdf.artifacts.verify_bundle"
    resolved = Path(bundle_path).resolve()
    if not resolved.exists():
        raise AgentPDFException("file_not_found", f"Bundle file not found: {resolved}")
    if not resolved.is_file():
        raise AgentPDFException("invalid_input", f"Bundle path must be a file: {resolved}")

    checks: list[ValidationCheck] = []
    warnings: list[str] = []
    manifest: dict[str, Any] = {}
    artifact_count = 0
    verified_artifact_count = 0
    missing_artifacts: list[str] = []
    checksum_mismatches: list[str] = []
    duplicate_bundle_paths: list[str] = []
    checksum_file_entries: dict[str, str] = {}

    try:
        with ZipFile(resolved) as archive:
            names = archive.namelist()
            name_counts = {name: names.count(name) for name in set(names)}
            duplicate_bundle_paths = sorted(name for name, count in name_counts.items() if count > 1)
            if duplicate_bundle_paths:
                warnings.extend(f"Duplicate ZIP entry: {name}" for name in duplicate_bundle_paths)

            if "agentpdf-bundle-manifest.json" not in names:
                checks.append(
                    ValidationCheck(
                        name="manifest_present",
                        status="failed",
                        message="Bundle is missing agentpdf-bundle-manifest.json.",
                    )
                )
            else:
                checks.append(ValidationCheck(name="manifest_present", status="passed"))
                try:
                    manifest = json.loads(archive.read("agentpdf-bundle-manifest.json"))
                    if not isinstance(manifest, dict):
                        raise ValueError("manifest JSON must be an object")
                    checks.append(ValidationCheck(name="manifest_parseable", status="passed"))
                except (json.JSONDecodeError, ValueError) as exc:
                    checks.append(
                        ValidationCheck(
                            name="manifest_parseable",
                            status="failed",
                            message=f"Bundle manifest is not valid JSON: {exc}",
                        )
                    )

            if "checksums.sha256" in names:
                checksum_file_entries = _read_checksum_file(archive.read("checksums.sha256").decode("utf-8"))
                checks.append(
                    ValidationCheck(
                        name="checksums_file_present",
                        status="passed",
                        details={"entry_count": len(checksum_file_entries)},
                    )
                )
            else:
                checks.append(
                    ValidationCheck(
                        name="checksums_file_present",
                        status="failed",
                        message="Bundle is missing checksums.sha256.",
                    )
                )

            artifact_entries = manifest.get("artifacts", []) if manifest else []
            if not isinstance(artifact_entries, list):
                artifact_entries = []
                checks.append(
                    ValidationCheck(
                        name="manifest_artifacts_list",
                        status="failed",
                        message="Bundle manifest artifacts must be a list.",
                    )
                )
            else:
                checks.append(ValidationCheck(name="manifest_artifacts_list", status="passed"))

            artifact_count = len(artifact_entries)
            declared_count = manifest.get("artifact_count") if manifest else None
            count_matches = declared_count == artifact_count
            checks.append(
                ValidationCheck(
                    name="artifact_count_matches_manifest",
                    status="passed" if count_matches else "failed",
                    details={"declared": declared_count, "actual": artifact_count},
                    message=None if count_matches else "artifact_count does not match artifacts length.",
                )
            )

            for entry in artifact_entries:
                if not isinstance(entry, dict):
                    checks.append(
                        ValidationCheck(
                            name="artifact_entry_shape",
                            status="failed",
                            message="Artifact manifest entry must be an object.",
                        )
                    )
                    continue
                bundle_entry_path = str(entry.get("bundle_path") or "")
                expected_sha = str(entry.get("sha256") or "")
                if not bundle_entry_path.startswith("artifacts/") or "/" in bundle_entry_path.removeprefix("artifacts/"):
                    checks.append(
                        ValidationCheck(
                            name="artifact_path_sanitized",
                            status="failed",
                            details={"bundle_path": bundle_entry_path},
                            message="Artifact bundle_path must be a sanitized artifacts/<filename> path.",
                        )
                    )
                    continue
                if bundle_entry_path not in names:
                    missing_artifacts.append(bundle_entry_path)
                    checks.append(
                        ValidationCheck(
                            name="artifact_present",
                            status="failed",
                            details={"bundle_path": bundle_entry_path},
                            message=f"Missing artifact entry: {bundle_entry_path}",
                        )
                    )
                    continue

                actual_sha = hashlib.sha256(archive.read(bundle_entry_path)).hexdigest()
                checksum_line_sha = checksum_file_entries.get(bundle_entry_path)
                checksum_matches = actual_sha == expected_sha and (
                    checksum_line_sha is None or checksum_line_sha == expected_sha
                )
                if checksum_matches:
                    verified_artifact_count += 1
                else:
                    checksum_mismatches.append(bundle_entry_path)
                    warnings.append(f"Checksum mismatch for {bundle_entry_path}.")
                checks.append(
                    ValidationCheck(
                        name="artifact_checksum",
                        status="passed" if checksum_matches else "failed",
                        details={
                            "bundle_path": bundle_entry_path,
                            "expected_sha256": expected_sha,
                            "actual_sha256": actual_sha,
                            "checksums_file_sha256": checksum_line_sha,
                        },
                        message=None if checksum_matches else f"Checksum mismatch for {bundle_entry_path}.",
                    )
                )
    except BadZipFile as exc:
        raise AgentPDFException("invalid_input", f"Bundle is not a readable ZIP file: {resolved}") from exc

    if missing_artifacts:
        warnings.extend(f"Missing artifact entry: {path}" for path in missing_artifacts)

    validation_status = "failed" if any(check.status == "failed" for check in checks) else "passed"
    validation = ValidationReport(status=validation_status, checks=checks, warnings=warnings)
    return ToolResult(
        job_id=f"job_{uuid4().hex[:16]}",
        status="succeeded" if validation_status == "passed" else "failed",
        tool=tool,
        validation=validation,
        warnings=warnings,
        usage={
            "bundle_verification": {
                "bundle_path": resolved.as_posix(),
                "manifest": manifest,
                "artifact_count": artifact_count,
                "verified_artifact_count": verified_artifact_count,
                "missing_artifacts": missing_artifacts,
                "checksum_mismatches": checksum_mismatches,
                "duplicate_bundle_paths": duplicate_bundle_paths,
                "checksum_file_entry_count": len(checksum_file_entries),
            }
        },
        next_recommended_tools=["pdf.workflow.report", "pdf.inspect.document"],
    )


def _source_map_composition_input(
    composition: dict[str, Any] | str | Path | None,
    composition_path: str | Path | None,
    source_map: dict[str, Any] | list[dict[str, Any]] | str | Path | None,
    source_map_path: str | Path | None,
) -> dict[str, Any] | str | Path:
    if composition_path is not None:
        return composition_path
    if composition is not None:
        return composition
    source_value = source_map if source_map is not None else source_map_path
    if source_value is None:
        raise AgentPDFException("invalid_input", "Provide composition_path, composition, source_map_path, or source_map.")
    payload = _load_optional_json(source_value, "Source map")
    if isinstance(payload.get("source_map"), list):
        return payload
    if isinstance(payload.get("source_map_report"), dict):
        return {"source_map": payload["source_map_report"].get("source_map", [])}
    if isinstance(source_value, list):
        return {"source_map": source_value}
    raise AgentPDFException("invalid_input", "Source map input must be an array or object containing source_map.")


def _load_optional_json(value: Any, label: str) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, list):
        return {"source_map": value}
    resolved = Path(value).resolve()
    if not resolved.exists():
        raise AgentPDFException("file_not_found", f"{label} JSON not found: {resolved}")
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AgentPDFException("invalid_input", f"{label} JSON is not valid JSON: {resolved}") from exc
    if isinstance(payload, list):
        return {"source_map": payload}
    if not isinstance(payload, dict):
        raise AgentPDFException("invalid_input", f"{label} JSON must be an object or array.")
    return payload


def _composition_payload_ir(payload: dict[str, Any]) -> dict[str, Any]:
    if isinstance(payload.get("composition_ir"), dict):
        return payload["composition_ir"]
    usage = payload.get("usage")
    if isinstance(usage, dict) and isinstance(usage.get("composition_ir"), dict):
        return usage["composition_ir"]
    if isinstance(payload.get("blocks"), list):
        return payload
    return {}


def _composition_blocks_for_artifact_source_map(composition_ir: dict[str, Any]) -> list[dict[str, Any]]:
    blocks = composition_ir.get("blocks", [])
    if not isinstance(blocks, list):
        return []
    return [block for block in blocks if isinstance(block, dict)]


def _artifact_block_index(
    blocks: list[dict[str, Any]],
    source_entries: list[Any],
) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for block in blocks:
        block_id = str(block.get("block_id") or "").strip()
        if not block_id:
            continue
        index[block_id] = {
            "block_id": block_id,
            "block_type": block.get("type"),
            "title": block.get("title"),
            "target_slot": block.get("target_slot"),
            "source_refs": _sorted_strings(block.get("source_refs")),
            "page_refs": [],
            "mapping_count": 0,
        }
    for entry in source_entries:
        if not isinstance(entry, dict):
            continue
        block_id = str(entry.get("block_id") or "").strip()
        if not block_id:
            continue
        block_record = index.setdefault(
            block_id,
            {
                "block_id": block_id,
                "block_type": entry.get("block_type"),
                "title": None,
                "target_slot": entry.get("target_slot"),
                "source_refs": [],
                "page_refs": [],
                "mapping_count": 0,
            },
        )
        source_ref = str(entry.get("source_ref") or "").strip()
        if source_ref and source_ref not in block_record["source_refs"]:
            block_record["source_refs"].append(source_ref)
            block_record["source_refs"].sort()
        page_ref = _page_ref_from_source_entry(entry)
        if page_ref:
            block_record["page_refs"].append(page_ref)
        block_record["mapping_count"] += 1
    for block_record in index.values():
        block_record["page_refs"] = _sorted_page_refs(block_record["page_refs"])
    return dict(sorted(index.items()))


def _artifact_source_ref_index(source_entries: list[Any]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for entry in source_entries:
        if not isinstance(entry, dict):
            continue
        source_ref = str(entry.get("source_ref") or "").strip()
        if not source_ref:
            continue
        record = index.setdefault(
            source_ref,
            {
                "source_ref": source_ref,
                "mapping_count": 0,
                "block_ids": [],
                "target_slots": [],
                "page_refs": [],
                "evidence_kinds": [],
                "source_match_status": "unmatched",
            },
        )
        record["mapping_count"] += 1
        _append_unique(record["block_ids"], entry.get("block_id"))
        _append_unique(record["target_slots"], entry.get("target_slot"))
        _append_unique(record["evidence_kinds"], entry.get("evidence_kind"))
        page_ref = _page_ref_from_source_entry(entry)
        if page_ref:
            record["page_refs"].append(page_ref)
        statuses = set(record.get("_statuses", []))
        statuses.add(str(entry.get("source_match_status") or "unmatched"))
        record["_statuses"] = sorted(statuses)
    for record in index.values():
        statuses = set(record.pop("_statuses", []))
        if statuses == {"matched"}:
            record["source_match_status"] = "matched"
        elif len(statuses) > 1:
            record["source_match_status"] = "mixed"
        record["block_ids"].sort()
        record["target_slots"].sort()
        record["evidence_kinds"].sort()
        record["page_refs"] = _sorted_page_refs(record["page_refs"])
    return dict(sorted(index.items()))


def _artifact_page_index(source_entries: list[Any]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for entry in source_entries:
        if not isinstance(entry, dict) or entry.get("page_number") is None:
            continue
        page_number = int(entry["page_number"])
        key = str(page_number)
        record = index.setdefault(
            key,
            {
                "page_number": page_number,
                "block_ids": [],
                "source_refs": [],
                "mappings": [],
            },
        )
        _append_unique(record["block_ids"], entry.get("block_id"))
        _append_unique(record["source_refs"], entry.get("source_ref"))
        record["mappings"].append(
            {
                "mapping_id": entry.get("mapping_id"),
                "block_id": entry.get("block_id"),
                "source_ref": entry.get("source_ref"),
                "bbox": entry.get("bbox"),
            }
        )
    for record in index.values():
        record["block_ids"].sort()
        record["source_refs"].sort()
        record["mappings"] = sorted(
            record["mappings"],
            key=lambda item: (str(item.get("block_id") or ""), str(item.get("source_ref") or "")),
        )
    return dict(sorted(index.items(), key=lambda item: int(item[0])))


def _page_ref_from_source_entry(entry: dict[str, Any]) -> dict[str, Any] | None:
    if entry.get("page_number") is None:
        return None
    page_ref: dict[str, Any] = {
        "page_number": int(entry["page_number"]),
        "block_id": entry.get("block_id"),
        "source_ref": entry.get("source_ref"),
        "mapping_id": entry.get("mapping_id"),
    }
    if entry.get("bbox") is not None:
        page_ref["bbox"] = entry["bbox"]
    return {key: value for key, value in page_ref.items() if value is not None}


def _sorted_page_refs(page_refs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        page_refs,
        key=lambda item: (
            int(item.get("page_number") or 0),
            str(item.get("block_id") or ""),
            str(item.get("source_ref") or ""),
        ),
    )


def _optional_artifact_manifest(
    artifact_manifest_path: str | Path | None,
    artifact_paths: list[str | Path],
) -> tuple[dict[str, Any], Path | None]:
    if artifact_manifest_path is None and not artifact_paths:
        return {}, None
    return _load_graph_manifest(artifact_manifest_path=artifact_manifest_path, artifact_paths=artifact_paths)


def _generated_artifacts_from_manifest(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    entries = manifest.get("artifacts")
    if not isinstance(entries, list):
        return []
    generated = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        artifact_kind = str(entry.get("artifact_kind") or "")
        mime_type = str(entry.get("mime_type") or "")
        if artifact_kind != "pdf" and mime_type != "application/pdf":
            continue
        generated.append(
            {
                "path": entry.get("path"),
                "artifact_kind": artifact_kind or "pdf",
                "mime_type": mime_type,
                "sha256": entry.get("sha256"),
                "page_count": entry.get("page_count"),
                "size_bytes": entry.get("size_bytes"),
            }
        )
    return generated


def _sorted_strings(value: Any) -> list[str]:
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    if isinstance(value, list):
        return sorted({str(item).strip() for item in value if str(item).strip()})
    return []


def _append_unique(items: list[Any], value: Any) -> None:
    if value is None:
        return
    text = str(value).strip()
    if text and text not in items:
        items.append(text)


def _load_graph_manifest(
    artifact_manifest_path: str | Path | None,
    artifact_paths: list[str | Path],
) -> tuple[dict[str, Any], Path | None]:
    if artifact_manifest_path is not None:
        resolved = Path(artifact_manifest_path).resolve()
        if not resolved.exists():
            raise AgentPDFException("file_not_found", f"Artifact manifest file not found: {resolved}")
        if not resolved.is_file():
            raise AgentPDFException("invalid_input", f"Artifact manifest path must be a file: {resolved}")
        try:
            payload = json.loads(resolved.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise AgentPDFException("invalid_input", f"Artifact manifest is not valid JSON: {resolved}") from exc
        if not isinstance(payload, dict):
            raise AgentPDFException("invalid_input", "Artifact manifest JSON must be an object.")
        return payload, resolved
    if artifact_paths:
        result = create_artifact_manifest(artifact_paths=artifact_paths)
        manifest = result.usage.get("artifact_manifest")
        if not isinstance(manifest, dict):
            raise AgentPDFException("invalid_input", "Could not build artifact manifest from artifact_paths.")
        return manifest, None
    raise AgentPDFException("invalid_input", "Provide artifact_manifest_path or at least one artifact_path.")


def _artifact_node_id(entry: dict[str, Any], index: int) -> str:
    sha256 = str(entry.get("sha256") or "")
    if sha256:
        return f"artifact:{sha256[:16]}"
    path = str(entry.get("path") or entry.get("source_path") or "")
    digest = hashlib.sha256(path.encode("utf-8")).hexdigest()[:16] if path else f"{index:04d}"
    return f"artifact:{digest}"


def _source_ref_node_id(source_ref: str) -> str:
    return f"source_ref:{source_ref}"


def _artifact_label(path: str, index: int) -> str:
    if path:
        return Path(path).name
    return f"artifact-{index:03d}"


def _entry_source_refs(entry: dict[str, Any]) -> list[str]:
    value = entry.get("source_refs")
    if isinstance(value, str) and value:
        return [value]
    if isinstance(value, list):
        return sorted({str(item) for item in value if item})
    return []


def _add_edge(
    edges: list[dict[str, Any]],
    from_node: str,
    to_node: str,
    relation: str,
    *,
    evidence: str,
    details: dict[str, Any] | None = None,
    inferred: bool = False,
) -> None:
    edges.append(
        {
            "id": f"edge_{len(edges) + 1:04d}",
            "from": from_node,
            "to": to_node,
            "relation": relation,
            "evidence": evidence,
            "inferred": inferred,
            "details": details or {},
        }
    )


def _add_artifact_convention_edges(edges: list[dict[str, Any]], artifact_ids_by_kind: dict[str, list[str]]) -> None:
    _add_kind_edges(
        edges,
        artifact_ids_by_kind,
        parent_kind="composition",
        child_kind="coverage",
        relation="derived_from_composition",
    )
    _add_kind_edges(
        edges,
        artifact_ids_by_kind,
        parent_kind="composition",
        child_kind="source_map",
        relation="derived_from_composition",
    )
    _add_kind_edges(
        edges,
        artifact_ids_by_kind,
        parent_kind="composition",
        child_kind="patch",
        relation="derived_from_composition",
    )
    _add_kind_edges(
        edges,
        artifact_ids_by_kind,
        parent_kind="source_map",
        child_kind="citations",
        relation="derived_from_source_map",
    )
    _add_kind_edges(
        edges,
        artifact_ids_by_kind,
        parent_kind="patch",
        child_kind="pdf",
        relation="produces_pdf",
    )


def _add_kind_edges(
    edges: list[dict[str, Any]],
    artifact_ids_by_kind: dict[str, list[str]],
    *,
    parent_kind: str,
    child_kind: str,
    relation: str,
) -> None:
    for parent_id in artifact_ids_by_kind.get(parent_kind, []):
        for child_id in artifact_ids_by_kind.get(child_kind, []):
            _add_edge(
                edges,
                parent_id,
                child_id,
                relation,
                evidence=f"artifact_kind_convention:{parent_kind}->{child_kind}",
                details={"parent_kind": parent_kind, "child_kind": child_kind},
                inferred=True,
            )


def _evidence_link_index(
    manifest: dict[str, Any],
    artifact_node_ids_by_path: dict[str, str],
) -> dict[str, list[dict[str, str]]]:
    evidence_links = manifest.get("evidence_links")
    if not isinstance(evidence_links, dict):
        return {}
    index: dict[str, list[dict[str, str]]] = {}
    for kind, paths in evidence_links.items():
        if not isinstance(paths, list):
            continue
        index[str(kind)] = [
            {
                "path": str(path),
                "artifact_node_id": artifact_node_ids_by_path.get(str(path), ""),
            }
            for path in paths
        ]
    return index


def _input_artifact(path: str | Path):
    resolved = Path(path).resolve()
    if not resolved.exists():
        raise AgentPDFException("file_not_found", f"Bundle input file not found: {resolved}")
    if not resolved.is_file():
        raise AgentPDFException("invalid_input", f"Bundle input must be a file: {resolved}")
    return build_artifact(resolved, source_tool="pdf.artifacts.bundle_input")


def _artifact_kind(path: Path) -> str:
    name = path.name.lower()
    if name.endswith(".composition.json"):
        return "composition"
    if name.endswith(".coverage.json"):
        return "coverage"
    if name.endswith(".source-map.json"):
        return "source_map"
    if name.endswith(".citations.json"):
        return "citations"
    if name.endswith(".patch.json"):
        return "patch"
    if name.endswith(".layers.json"):
        return "layers"
    if name.endswith(".context.packet.json") or name.endswith(".context-item.json"):
        return "context"
    if path.suffix.lower() == ".pdf":
        return "pdf"
    return "file"


def _read_json_artifact(path: Path, warnings: list[str]) -> dict[str, Any] | list[Any] | None:
    if path.suffix.lower() != ".json":
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        warnings.append(f"JSON artifact could not be parsed: {path.as_posix()} ({exc})")
        return None
    if isinstance(payload, (dict, list)):
        return payload
    warnings.append(f"JSON artifact is not an object or array: {path.as_posix()}")
    return None


def _collect_source_refs(value: Any) -> set[str]:
    refs: set[str] = set()
    if isinstance(value, dict):
        source_ref = value.get("source_ref")
        source_refs = value.get("source_refs")
        if isinstance(source_ref, str) and source_ref:
            refs.add(source_ref)
        if isinstance(source_refs, str) and source_refs:
            refs.add(source_refs)
        elif isinstance(source_refs, list):
            refs.update(str(item) for item in source_refs if item)
        for nested in value.values():
            refs.update(_collect_source_refs(nested))
    elif isinstance(value, list):
        for item in value:
            refs.update(_collect_source_refs(item))
    return refs


def _bundle_entries(input_artifacts: list[Any]) -> list[dict[str, Any]]:
    seen_names: set[str] = set()
    entries = []
    for artifact in input_artifacts:
        safe_name = _safe_bundle_filename(artifact.path.name, seen_names)
        seen_names.add(safe_name)
        payload = artifact.model_dump(mode="json")
        entries.append(
            {
                **payload,
                "source_path": payload["path"],
                "bundle_path": f"artifacts/{safe_name}",
            }
        )
    return entries


def _safe_bundle_filename(name: str, seen_names: set[str]) -> str:
    candidate = Path(name).name.strip().replace("\\", "_").replace("/", "_")
    if not candidate or candidate in {".", ".."}:
        raise AgentPDFException("unsafe_input_rejected", f"Unsafe bundle filename: {name!r}")
    if ".." in Path(candidate).parts:
        raise AgentPDFException("unsafe_input_rejected", f"Unsafe bundle filename: {name!r}")
    if candidate not in seen_names:
        return candidate
    stem = Path(candidate).stem or "artifact"
    suffix = Path(candidate).suffix
    index = 2
    while f"{stem}-{index}{suffix}" in seen_names:
        index += 1
    return f"{stem}-{index}{suffix}"


def _json_safe_dict(value: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(value, default=str))


def _read_checksum_file(text: str) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        parts = stripped.split(maxsplit=1)
        if len(parts) != 2:
            continue
        checksum, bundle_path = parts
        entries[bundle_path.strip()] = checksum.strip().lower()
    return entries
