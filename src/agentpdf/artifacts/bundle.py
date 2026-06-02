from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4
from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile

from agentpdf.artifacts.store import build_artifact
from agentpdf.schemas.errors import AgentPDFException
from agentpdf.schemas.models import ToolResult, ValidationCheck, ValidationReport


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


def _input_artifact(path: str | Path):
    resolved = Path(path).resolve()
    if not resolved.exists():
        raise AgentPDFException("file_not_found", f"Bundle input file not found: {resolved}")
    if not resolved.is_file():
        raise AgentPDFException("invalid_input", f"Bundle input must be a file: {resolved}")
    return build_artifact(resolved, source_tool="pdf.artifacts.bundle_input")


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
