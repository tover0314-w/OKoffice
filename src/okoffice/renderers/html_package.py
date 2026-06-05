from __future__ import annotations

import hashlib
import html
import json
import mimetypes
import shutil
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

from okoffice.artifacts.store import build_artifact
from okoffice.conversion.local import html_to_pdf
from okoffice.renderers.browser import browser_chromium_html_to_pdf
from okoffice.renderers.html_contract import (
    HTML_LAYER_BBOX_PRECISION,
    SUPPORTED_RENDERER_BACKENDS,
    browser_chromium_backend,
    browser_chromium_backend_unavailable,
    document_render_profile,
    local_html_package_fallback_backend,
    renderer_constraints,
)
from okoffice.schemas.errors import OKofficeException
from okoffice.schemas.models import OKofficeError, ToolResult, ValidationCheck, ValidationReport
from okoffice.security.paths import resolve_input_path, resolve_output_path


SUPPORTED_RENDERER_CONTRACTS = {"html-package-v0", "authoring-html-package-v0"}


def write_composition_html_package(
    *,
    composition_ir: dict[str, Any],
    source_map: list[dict[str, Any]],
    target_profile: dict[str, Any],
    render_plan: dict[str, Any],
    html_output_path: str | Path,
    source_tool: str,
) -> dict[str, Any]:
    output = resolve_output_path(html_output_path)
    manifest_path = output.with_suffix(".html-manifest.json")
    assets_dir = output.with_suffix(".assets")
    blocks = _blocks(composition_ir)
    source_refs = _source_refs(blocks, source_map)
    assets = _package_assets(blocks, assets_dir=assets_dir, package_root=output.parent)
    assets_by_block = _assets_by_block(assets)
    layer_map = _layer_map(blocks)
    document = _html_document(
        composition_ir=composition_ir,
        source_map=source_map,
        target_profile=target_profile,
        render_plan=render_plan,
        blocks=blocks,
        assets_by_block=assets_by_block,
    )
    validation = _validate_html_package(assets)
    constraints = renderer_constraints()
    manifest = {
        "html_package_version": "0.1",
        "html_package_id": f"htmlpkg_{uuid4().hex[:16]}",
        "source_tool": source_tool,
        "renderer": "html_package",
        "renderer_contract": "html-package-v0",
        "html_path": str(output.resolve()),
        "manifest_path": str(manifest_path.resolve()),
        "composition_id": composition_ir.get("composition_id"),
        "context_packet_id": composition_ir.get("context_packet_id"),
        "target_profile_id": composition_ir.get("target_profile_id") or target_profile.get("profile_id"),
        "block_count": len(blocks),
        "layer_map_count": len(layer_map),
        "source_map_count": len(source_map),
        "source_ref_count": len(source_refs),
        "source_refs": source_refs,
        "javascript_enabled": False,
        "remote_assets_enabled": False,
        "render_profile": document_render_profile(),
        "renderer_constraints": constraints,
        "renderer_backend": local_html_package_fallback_backend(constraints),
        "assets_root": str(assets_dir.resolve()),
        "asset_count": len(assets),
        "assets": assets,
        "validation": validation.model_dump(mode="json"),
        "contract": {
            "body_attribute": "data-agentpdf-document",
            "block_selector": "[data-block-id]",
            "source_refs_attribute": "data-source-refs",
            "layer_id_attribute": "data-layer-id",
            "bbox_precision": HTML_LAYER_BBOX_PRECISION,
            "renderer_attribute": "data-agentpdf-renderer",
        },
        "layer_map": layer_map,
        "blocks": [
            {
                "block_id": str(block.get("block_id") or ""),
                "layer_id": _layer_id(str(block.get("block_id") or "")),
                "block_type": str(block.get("type") or "section"),
                "target_slot": block.get("target_slot"),
                "source_refs": [str(ref) for ref in block.get("source_refs", [])],
            }
            for block in blocks
        ],
    }
    output.write_text(document, encoding="utf-8")
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    html_artifact = build_artifact(output, source_tool=source_tool)
    manifest_artifact = build_artifact(manifest_path, source_tool=source_tool)
    return {
        "html_output_path": str(output.resolve()),
        "html_package_manifest_path": str(manifest_path.resolve()),
        "html_package_manifest": manifest,
        "html_package_validation": validation,
        "artifacts": [html_artifact, manifest_artifact],
    }


def render_html_package(
    package_path: str | Path,
    output_path: str | Path,
    renderer_backend: str = "auto",
) -> ToolResult:
    tool = "pdf.render.html_package"
    manifest_path = _resolve_manifest_path(package_path)
    manifest = _load_html_package_manifest(manifest_path)
    html_path = _manifest_html_path(manifest)
    html_validation = _validate_existing_html_package_manifest(manifest, manifest_path=manifest_path, html_path=html_path)
    render_profile = _manifest_render_profile(manifest)
    renderer_constraints_value = _manifest_renderer_constraints(manifest)
    requested_renderer_backend = _normalize_renderer_backend(renderer_backend)
    renderer_backend_evidence = _renderer_backend_evidence(requested_renderer_backend, renderer_constraints_value)
    backend_validation = _renderer_backend_validation(renderer_backend_evidence)
    output = Path(output_path).expanduser().resolve()
    if html_validation.status == "failed":
        skipped_pdf_validation = _skipped_pdf_render_validation("html_package_validation_failed")
        validation = _merge_validation(_merge_validation(html_validation, backend_validation), skipped_pdf_validation)
        return ToolResult(
            job_id=f"job_{uuid4().hex[:16]}",
            status="failed",
            tool=tool,
            artifacts=[
                build_artifact(html_path, source_tool=tool),
                build_artifact(manifest_path, source_tool=tool),
            ],
            validation=validation,
            warnings=validation.warnings,
            usage={
                "renderer": str(renderer_backend_evidence["backend_id"]),
                "requested_renderer_backend": requested_renderer_backend,
                "renderer_backend": renderer_backend_evidence,
                "input": str(manifest_path),
                "html_path": str(html_path),
                "output": str(output),
                "render_skipped": True,
                "render_skip_reason": "html_package_validation_failed",
                "render_profile": render_profile,
                "renderer_constraints": renderer_constraints_value,
                "html_package_manifest": manifest,
                "html_package_validation": html_validation.model_dump(mode="json"),
            },
            next_recommended_tools=["pdf.create.html_package"],
        )
    if renderer_backend_evidence.get("available") is False:
        skipped_pdf_validation = _skipped_pdf_render_validation("renderer_backend_unavailable")
        validation = _merge_validation(_merge_validation(html_validation, backend_validation), skipped_pdf_validation)
        return ToolResult(
            job_id=f"job_{uuid4().hex[:16]}",
            status="failed",
            tool=tool,
            artifacts=[
                build_artifact(html_path, source_tool=tool),
                build_artifact(manifest_path, source_tool=tool),
            ],
            validation=validation,
            warnings=validation.warnings,
            usage={
                "renderer": str(renderer_backend_evidence["backend_id"]),
                "requested_renderer_backend": requested_renderer_backend,
                "renderer_backend": renderer_backend_evidence,
                "input": str(manifest_path),
                "html_path": str(html_path),
                "output": str(output),
                "render_skipped": True,
                "render_skip_reason": "renderer_backend_unavailable",
                "render_profile": render_profile,
                "renderer_constraints": renderer_constraints_value,
                "html_package_manifest": manifest,
                "html_package_validation": html_validation.model_dump(mode="json"),
            },
            next_recommended_tools=["pdf.render.html_package"],
            error=OKofficeError(
                code="dependency_missing",
                message="Requested browser renderer backend is not available in this local install.",
                retry_hint="Install the optional browser renderer worker or rerun with renderer_backend='auto'.",
                details={
                    "requested_renderer_backend": requested_renderer_backend,
                    "renderer_backend": renderer_backend_evidence,
                },
            ),
        )
    try:
        rendered = (
            browser_chromium_html_to_pdf(
                html_path=html_path,
                manifest_path=manifest_path,
                output_path=output,
                render_profile=render_profile,
                renderer_constraints=renderer_constraints_value,
            )
            if requested_renderer_backend == "browser_chromium"
            else html_to_pdf(html_path, output_path)
        )
    except OKofficeException as exc:
        if requested_renderer_backend == "browser_chromium" and exc.code == "dependency_missing":
            renderer_backend_evidence = browser_chromium_backend_unavailable(renderer_constraints_value)
            backend_validation = _renderer_backend_validation(renderer_backend_evidence)
            skipped_pdf_validation = _skipped_pdf_render_validation("renderer_backend_unavailable")
            validation = _merge_validation(_merge_validation(html_validation, backend_validation), skipped_pdf_validation)
            return ToolResult(
                job_id=f"job_{uuid4().hex[:16]}",
                status="failed",
                tool=tool,
                artifacts=[
                    build_artifact(html_path, source_tool=tool),
                    build_artifact(manifest_path, source_tool=tool),
                ],
                validation=validation,
                warnings=validation.warnings,
                usage={
                    "renderer": str(renderer_backend_evidence["backend_id"]),
                    "requested_renderer_backend": requested_renderer_backend,
                    "renderer_backend": renderer_backend_evidence,
                    "input": str(manifest_path),
                    "html_path": str(html_path),
                    "output": str(output),
                    "render_skipped": True,
                    "render_skip_reason": "renderer_backend_unavailable",
                    "render_profile": render_profile,
                    "renderer_constraints": renderer_constraints_value,
                    "html_package_manifest": manifest,
                    "html_package_validation": html_validation.model_dump(mode="json"),
                },
                next_recommended_tools=["pdf.render.html_package"],
                error=exc.to_error(),
            )
        raise
    pdf_validation = rendered.validation or ValidationReport(status="skipped", checks=[])
    validation = _merge_validation(_merge_validation(html_validation, backend_validation), pdf_validation)
    artifacts = [
        build_artifact(output, source_tool=tool),
        build_artifact(html_path, source_tool=tool),
        build_artifact(manifest_path, source_tool=tool),
    ]
    return ToolResult(
        job_id=f"job_{uuid4().hex[:16]}",
        status="succeeded" if validation.status == "passed" else "failed",
        tool=tool,
        artifacts=artifacts,
        validation=validation,
        warnings=[*rendered.warnings, *validation.warnings],
        usage={
            "renderer": str(renderer_backend_evidence["backend_id"]),
            "requested_renderer_backend": requested_renderer_backend,
            "renderer_backend": renderer_backend_evidence,
            "input": str(manifest_path),
            "html_path": str(html_path),
            "output": str(output),
            "render_skipped": False,
            "render_skip_reason": None,
            "render_profile": render_profile,
            "renderer_constraints": renderer_constraints_value,
            "html_package_manifest": manifest,
            "html_package_validation": html_validation.model_dump(mode="json"),
        },
        next_recommended_tools=[
            "pdf.validation.render_check",
            "pdf.validation.blank_page_check",
            "pdf.evidence.coverage_report",
        ],
    )


def _html_document(
    *,
    composition_ir: dict[str, Any],
    source_map: list[dict[str, Any]],
    target_profile: dict[str, Any],
    render_plan: dict[str, Any],
    blocks: list[dict[str, Any]],
    assets_by_block: dict[str, dict[str, Any]],
) -> str:
    title = str(render_plan.get("title") or target_profile.get("title") or target_profile.get("name") or "OKoffice")
    profile_id = str(composition_ir.get("target_profile_id") or target_profile.get("profile_id") or "custom")
    markdown = str(render_plan.get("markdown") or render_plan.get("markdown_outline") or "")
    block_html = "\n".join(_block_html(block, assets_by_block.get(str(block.get("block_id") or ""))) for block in blocks)
    source_map_html = "\n".join(_source_map_row(mapping) for mapping in source_map)
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="en">',
            "<head>",
            '  <meta charset="utf-8" />',
            '  <meta http-equiv="Content-Security-Policy" content="default-src \'none\'; img-src \'self\' data:; style-src \'unsafe-inline\'; font-src \'self\' data:; script-src \'none\';" />',
            f"  <title>{html.escape(title)}</title>",
            '  <meta name="agentpdf:renderer" content="html-package-v0" />',
            f'  <meta name="agentpdf:composition_id" content="{_attr(composition_ir.get("composition_id"))}" />',
            f'  <meta name="agentpdf:target_profile" content="{_attr(profile_id)}" />',
            "  <style>",
            _stylesheet(),
            "  </style>",
            "</head>",
            f'<body data-agentpdf-document data-agentpdf-renderer="html-package-v0" data-composition-id="{_attr(composition_ir.get("composition_id"))}" data-target-profile="{_attr(profile_id)}">',
            '  <section class="page page-cover" data-page-kind="cover" data-slot="cover">',
            f"    <p class=\"eyebrow\">{html.escape(profile_id)}</p>",
            f"    <h1>{html.escape(title)}</h1>",
            f"    <p>Composition ID: <code>{html.escape(str(composition_ir.get('composition_id') or ''))}</code></p>",
            "  </section>",
            '  <section class="page page-body" data-page-kind="body" data-slot="body">',
            block_html,
            "  </section>",
            '  <section class="page page-source-map" data-page-kind="source_map" data-slot="source_map">',
            "    <h2>Source Map</h2>",
            "    <table>",
            "      <thead><tr><th>Block</th><th>Source</th><th>Type</th></tr></thead>",
            "      <tbody>",
            source_map_html,
            "      </tbody>",
            "    </table>",
            "  </section>",
            '  <section class="page page-render-plan" data-page-kind="appendix" data-slot="render_plan">',
            "    <h2>Render Plan Markdown</h2>",
            f"    <pre>{html.escape(markdown)}</pre>",
            "  </section>",
            "</body>",
            "</html>",
        ]
    )


def _block_html(block: dict[str, Any], asset: dict[str, Any] | None = None) -> str:
    block_id = str(block.get("block_id") or "")
    layer_id = _layer_id(block_id)
    block_type = str(block.get("type") or "section")
    title = str(block.get("title") or block_type)
    target_slot = str(block.get("target_slot") or "body")
    source_refs = [str(ref) for ref in block.get("source_refs", [])]
    hints = block.get("render_hints") if isinstance(block.get("render_hints"), dict) else {}
    data = block.get("data") if isinstance(block.get("data"), dict) else {}
    if data and block_type == "image":
        hints = {**data, **hints}
    return "\n".join(
        [
            f'    <article class="agentpdf-block block-{_class_token(block_type)}" data-block-id="{_attr(block_id)}" data-layer-id="{_attr(layer_id)}" data-block-type="{_attr(block_type)}" data-slot="{_attr(target_slot)}" data-source-refs="{_attr(" ".join(source_refs))}">',
            f"      <h2>{html.escape(title)}</h2>",
            f"      <p><strong>Type:</strong> {html.escape(block_type)}</p>",
            _render_hints_html(hints, asset),
            "    </article>",
        ]
    )


def _render_hints_html(hints: dict[str, Any], asset: dict[str, Any] | None = None) -> str:
    if asset is not None:
        caption = str(hints.get("caption") or hints.get("alt") or asset.get("source_name") or "Image evidence")
        return "\n".join(
            [
                f'      <figure data-asset-id="{_attr(asset["asset_id"])}">',
                f'        <img src="./{_attr(asset["relative_path"])}" alt="{_attr(caption)}" data-asset-id="{_attr(asset["asset_id"])}" />',
                f"        <figcaption>{html.escape(caption)}</figcaption>",
                "      </figure>",
            ]
        )
    if not hints:
        return "      <p>No render hints supplied.</p>"
    if isinstance(hints.get("columns"), list):
        columns = [str(column) for column in hints.get("columns", [])]
        rows = "".join(f"<th>{html.escape(column)}</th>" for column in columns)
        return "\n".join(
            [
                "      <table>",
                f"        <thead><tr>{rows}</tr></thead>",
                "      </table>",
                f"      <p>Preview rows: {html.escape(str(hints.get('preview_rows', 0)))}</p>",
            ]
        )
    if hints.get("path"):
        return f"      <p>Path: <code>{html.escape(str(hints['path']))}</code></p>"
    if hints.get("language"):
        return f"      <p>Language: <code>{html.escape(str(hints['language']))}</code></p>"
    return f"      <pre>{html.escape(json.dumps(hints, indent=2, default=str))}</pre>"


def _package_assets(
    blocks: list[dict[str, Any]],
    *,
    assets_dir: Path,
    package_root: Path,
) -> list[dict[str, Any]]:
    assets: list[dict[str, Any]] = []
    for block in blocks:
        asset_ref = _image_asset_ref(block)
        if asset_ref is None:
            continue
        if _is_blocked_asset_ref(asset_ref):
            raise OKofficeException(
                "unsafe_input_rejected",
                "HTML package image assets must be local file paths.",
                details={"html_package_error": "html_asset_blocked", "asset_ref": asset_ref},
            )
        source = resolve_input_path(asset_ref)
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        block_id = str(block.get("block_id") or "asset")
        asset_id = f"asset_{_class_token(block_id)}_{digest[:12]}"
        suffix = source.suffix.lower() or ".bin"
        assets_dir.mkdir(parents=True, exist_ok=True)
        packaged = assets_dir / f"{asset_id}{suffix}"
        if source.resolve() != packaged.resolve():
            shutil.copyfile(source, packaged)
        relative_path = packaged.relative_to(package_root).as_posix()
        assets.append(
            {
                "asset_id": asset_id,
                "block_id": block_id,
                "source_path": str(source.resolve()),
                "source_name": source.name,
                "packaged_path": str(packaged.resolve()),
                "relative_path": relative_path,
                "mime_type": mimetypes.guess_type(source.name)[0] or "application/octet-stream",
                "size_bytes": packaged.stat().st_size,
                "sha256": digest,
            }
        )
    return assets


def _image_asset_ref(block: dict[str, Any]) -> str | None:
    if str(block.get("type") or "") != "image":
        return None
    hints = block.get("render_hints") if isinstance(block.get("render_hints"), dict) else {}
    data = block.get("data") if isinstance(block.get("data"), dict) else {}
    raw = (
        hints.get("path")
        or hints.get("image_path")
        or block.get("path")
        or block.get("image_path")
        or data.get("path")
        or data.get("image_path")
    )
    if raw is None:
        return None
    value = str(raw).strip()
    return value or None


def _is_blocked_asset_ref(asset_ref: str) -> bool:
    parsed = urlparse(asset_ref)
    return parsed.scheme in {"http", "https", "file", "ftp", "data"}


def _assets_by_block(assets: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(asset["block_id"]): asset for asset in assets}


def _validate_html_package(assets: list[dict[str, Any]]) -> ValidationReport:
    checks = [
        ValidationCheck(
            name="html_package_manifest_valid",
            status="passed",
            details={"manifest_version": "0.1"},
        ),
        ValidationCheck(
            name="all_assets_resolved",
            status="passed",
            details={"asset_count": len(assets)},
        ),
        ValidationCheck(
            name="html_layer_map_written",
            status="passed",
            details={"bbox_precision": HTML_LAYER_BBOX_PRECISION},
        ),
        ValidationCheck(
            name="render_profile_recorded",
            status="passed",
            details={"render_profile": document_render_profile()},
        ),
        ValidationCheck(
            name="no_remote_assets",
            status="passed",
            details={"remote_assets_enabled": False},
        ),
        ValidationCheck(
            name="no_forbidden_asset_paths",
            status="passed",
            details={"checked_assets": len(assets)},
        ),
    ]
    return ValidationReport(status="passed", checks=checks)


def _resolve_manifest_path(package_path: str | Path) -> Path:
    resolved = resolve_input_path(package_path)
    if resolved.suffix.lower() in {".html", ".htm"}:
        return resolve_input_path(resolved.with_suffix(".html-manifest.json"))
    return resolved


def _load_html_package_manifest(manifest_path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise OKofficeException(
            "html_invalid_package",
            "HTML package manifest is not valid JSON.",
            details={"manifest_path": str(manifest_path)},
        ) from exc
    if not isinstance(payload, dict):
        raise OKofficeException(
            "html_invalid_package",
            "HTML package manifest must be a JSON object.",
            details={"manifest_path": str(manifest_path)},
        )
    if payload.get("renderer_contract") not in SUPPORTED_RENDERER_CONTRACTS:
        raise OKofficeException(
            "html_invalid_package",
            "HTML package manifest has an unsupported renderer contract.",
            details={"manifest_path": str(manifest_path), "renderer_contract": payload.get("renderer_contract")},
        )
    return payload


def _manifest_html_path(manifest: dict[str, Any]) -> Path:
    raw_path = manifest.get("html_path")
    if not raw_path:
        raise OKofficeException("html_invalid_package", "HTML package manifest is missing html_path.")
    return resolve_input_path(str(raw_path))


def _validate_existing_html_package_manifest(
    manifest: dict[str, Any],
    *,
    manifest_path: Path,
    html_path: Path,
) -> ValidationReport:
    assets = manifest.get("assets", [])
    if not isinstance(assets, list):
        raise OKofficeException(
            "html_invalid_package",
            "HTML package manifest assets must be an array.",
            details={"manifest_path": str(manifest_path)},
        )
    for asset in assets:
        if not isinstance(asset, dict):
            raise OKofficeException(
                "html_invalid_package",
                "HTML package manifest asset entries must be objects.",
                details={"manifest_path": str(manifest_path)},
            )
        _validate_manifest_asset(asset, manifest_path=manifest_path)
    remote_assets_enabled = bool(manifest.get("remote_assets_enabled", False))
    javascript_enabled = bool(manifest.get("javascript_enabled", False))
    render_profile = _manifest_render_profile(manifest)
    checks = [
        ValidationCheck(
            name="html_package_manifest_valid",
            status="passed",
            details={
                "manifest_path": str(manifest_path),
                "html_path": str(html_path),
                "renderer_contract": manifest.get("renderer_contract"),
            },
        ),
        ValidationCheck(
            name="all_assets_resolved",
            status="passed",
            details={"asset_count": len(assets)},
        ),
        ValidationCheck(
            name="no_remote_assets",
            status="failed" if remote_assets_enabled else "passed",
            details={"remote_assets_enabled": remote_assets_enabled},
            message="HTML packages must not rely on remote assets." if remote_assets_enabled else None,
        ),
        ValidationCheck(
            name="no_javascript",
            status="failed" if javascript_enabled else "passed",
            details={"javascript_enabled": javascript_enabled},
            message="HTML package rendering disables JavaScript." if javascript_enabled else None,
        ),
        ValidationCheck(
            name="render_profile_recorded",
            status="passed" if manifest.get("render_profile") else "warning",
            details={"render_profile": render_profile},
            message="HTML package manifest did not include a render_profile; using local defaults."
            if not manifest.get("render_profile")
            else None,
        ),
        *_render_profile_safety_checks(render_profile),
        ValidationCheck(
            name="no_forbidden_asset_paths",
            status="passed",
            details={"checked_assets": len(assets)},
        ),
    ]
    return ValidationReport(
        status="failed" if any(check.status == "failed" for check in checks) else "passed",
        checks=checks,
    )


def _manifest_render_profile(manifest: dict[str, Any]) -> dict[str, Any]:
    render_profile = manifest.get("render_profile")
    return render_profile if isinstance(render_profile, dict) else document_render_profile()


def _manifest_renderer_constraints(manifest: dict[str, Any]) -> dict[str, Any]:
    constraints = manifest.get("renderer_constraints")
    return constraints if isinstance(constraints, dict) else renderer_constraints()


def _normalize_renderer_backend(renderer_backend: str) -> str:
    normalized = str(renderer_backend or "auto").strip()
    if normalized not in SUPPORTED_RENDERER_BACKENDS:
        raise OKofficeException(
            "html_render_failed",
            "Unsupported HTML package renderer backend.",
            details={
                "renderer_backend": normalized,
                "supported_renderer_backends": sorted(SUPPORTED_RENDERER_BACKENDS),
            },
        )
    return normalized


def _renderer_backend_evidence(renderer_backend: str, constraints: dict[str, Any]) -> dict[str, Any]:
    if renderer_backend == "browser_chromium":
        return browser_chromium_backend(constraints)
    return local_html_package_fallback_backend(constraints)


def _renderer_backend_validation(renderer_backend: dict[str, Any]) -> ValidationReport:
    available = renderer_backend.get("available", True) is not False
    checks = [
        ValidationCheck(
            name="renderer_backend_declared",
            status="passed",
            details=renderer_backend,
        ),
        ValidationCheck(
            name="renderer_backend_available",
            status="passed" if available else "failed",
            details=renderer_backend,
            message="Requested renderer backend is not available." if not available else None,
        ),
    ]
    return ValidationReport(
        status="passed" if available else "failed",
        checks=checks,
    )


def _skipped_pdf_render_validation(reason: str) -> ValidationReport:
    if reason == "renderer_backend_unavailable":
        message = "PDF render skipped because the requested renderer backend is unavailable."
        check_name = "pdf_render_skipped_due_to_renderer_backend_unavailable"
    else:
        message = "PDF render skipped because the HTML package failed validation."
        check_name = "pdf_render_skipped_due_to_html_package_validation"
    return ValidationReport(
        status="skipped",
        checks=[
            ValidationCheck(
                name=check_name,
                status="skipped",
                details={"reason": reason},
                message=message,
            )
        ],
        warnings=[message],
    )


def _render_profile_safety_checks(render_profile: dict[str, Any]) -> list[ValidationCheck]:
    javascript_enabled = _any_profile_flag(render_profile, "javascript_enabled", "allow_javascript")
    remote_assets_enabled = _any_profile_flag(render_profile, "remote_assets_enabled", "allow_remote_assets")
    allow_private_hosts = bool(render_profile.get("allow_private_hosts", False))
    allow_file_urls = bool(render_profile.get("allow_file_urls", False))
    allowed_origins = render_profile.get("allowed_origins")
    allowed_origin_count = len(allowed_origins) if isinstance(allowed_origins, list) else 0
    return [
        ValidationCheck(
            name="render_profile_no_javascript",
            status="failed" if javascript_enabled else "passed",
            details={
                "javascript_enabled": bool(render_profile.get("javascript_enabled", False)),
                "allow_javascript": bool(render_profile.get("allow_javascript", False)),
            },
            message="HTML package render profiles must keep JavaScript disabled." if javascript_enabled else None,
        ),
        ValidationCheck(
            name="render_profile_no_remote_assets",
            status="failed" if remote_assets_enabled else "passed",
            details={
                "remote_assets_enabled": bool(render_profile.get("remote_assets_enabled", False)),
                "allow_remote_assets": bool(render_profile.get("allow_remote_assets", False)),
            },
            message="HTML package render profiles must block remote assets." if remote_assets_enabled else None,
        ),
        ValidationCheck(
            name="render_profile_no_private_hosts",
            status="failed" if allow_private_hosts else "passed",
            details={"allow_private_hosts": allow_private_hosts},
            message="HTML package render profiles must not allow private hosts." if allow_private_hosts else None,
        ),
        ValidationCheck(
            name="render_profile_no_file_urls",
            status="failed" if allow_file_urls else "passed",
            details={"allow_file_urls": allow_file_urls},
            message="HTML package render profiles must not allow file URLs." if allow_file_urls else None,
        ),
        ValidationCheck(
            name="render_profile_allowed_origins_empty",
            status="failed" if allowed_origin_count else "passed",
            details={"allowed_origin_count": allowed_origin_count},
            message="HTML package render profiles must not whitelist remote origins." if allowed_origin_count else None,
        ),
    ]


def _any_profile_flag(render_profile: dict[str, Any], *keys: str) -> bool:
    return any(bool(render_profile.get(key, False)) for key in keys)


def _validate_manifest_asset(asset: dict[str, Any], *, manifest_path: Path) -> None:
    raw_path = str(asset.get("packaged_path") or "")
    if not raw_path:
        raise OKofficeException(
            "html_invalid_package",
            "HTML package asset is missing packaged_path.",
            details={"manifest_path": str(manifest_path), "asset_id": asset.get("asset_id")},
        )
    if _is_blocked_asset_ref(raw_path):
        raise OKofficeException(
            "html_invalid_package",
            "HTML package asset path must be local.",
            details={"manifest_path": str(manifest_path), "asset_id": asset.get("asset_id"), "asset_ref": raw_path},
        )
    path = Path(raw_path).expanduser().resolve()
    if not path.exists() or not path.is_file():
        raise OKofficeException(
            "html_asset_missing",
            "HTML package asset is missing.",
            details={
                "manifest_path": str(manifest_path),
                "asset_id": asset.get("asset_id"),
                "packaged_path": str(path),
            },
        )
    expected_sha = asset.get("sha256")
    if expected_sha and hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha:
        raise OKofficeException(
            "html_invalid_package",
            "HTML package asset hash does not match the manifest.",
            details={"manifest_path": str(manifest_path), "asset_id": asset.get("asset_id"), "packaged_path": str(path)},
        )


def _merge_validation(first: ValidationReport, second: ValidationReport) -> ValidationReport:
    checks = [*first.checks, *second.checks]
    status = "passed"
    if any(check.status == "failed" for check in checks):
        status = "failed"
    elif any(check.status == "warning" for check in checks):
        status = "warning"
    elif checks and all(check.status == "skipped" for check in checks):
        status = "skipped"
    return ValidationReport(
        status=status,
        checks=checks,
        page_count=second.page_count,
        warnings=[*first.warnings, *second.warnings],
    )


def _source_map_row(mapping: dict[str, Any]) -> str:
    return (
        "        <tr>"
        f"<td><code>{html.escape(str(mapping.get('block_id') or ''))}</code></td>"
        f"<td><code>{html.escape(str(mapping.get('source_ref') or ''))}</code></td>"
        f"<td>{html.escape(str(mapping.get('type') or mapping.get('block_type') or ''))}</td>"
        "</tr>"
    )


def _stylesheet() -> str:
    return """
    @page { size: A4; margin: 16mm; }
    body { font-family: Arial, Helvetica, sans-serif; color: #172033; line-height: 1.45; }
    .page { break-after: page; min-height: 240mm; }
    .eyebrow { text-transform: uppercase; letter-spacing: .08em; color: #52627a; }
    h1 { font-size: 34px; margin: 0 0 24px; }
    h2 { font-size: 20px; margin: 0 0 10px; }
    .agentpdf-block { border-top: 2px solid #d8dee9; padding: 14px 0 18px; }
    table { width: 100%; border-collapse: collapse; margin: 12px 0; }
    th, td { border: 1px solid #d8dee9; padding: 6px 8px; text-align: left; vertical-align: top; }
    pre { white-space: pre-wrap; background: #f7f8fb; border: 1px solid #d8dee9; padding: 12px; }
    code { font-family: Consolas, Menlo, monospace; }
    """


def _blocks(composition_ir: dict[str, Any]) -> list[dict[str, Any]]:
    blocks = composition_ir.get("blocks")
    return [block for block in blocks if isinstance(block, dict)] if isinstance(blocks, list) else []


def _source_refs(blocks: list[dict[str, Any]], source_map: list[dict[str, Any]]) -> list[str]:
    refs = {
        str(ref)
        for block in blocks
        for ref in block.get("source_refs", [])
        if str(ref).strip()
    }
    refs.update(str(mapping["source_ref"]) for mapping in source_map if mapping.get("source_ref"))
    return sorted(refs)


def _layer_map(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [_layer_entry(block, index=index) for index, block in enumerate(blocks)]


def _layer_entry(block: dict[str, Any], *, index: int) -> dict[str, Any]:
    block_id = str(block.get("block_id") or "")
    layer_id = _layer_id(block_id)
    block_type = str(block.get("type") or "section")
    source_refs = [str(ref) for ref in block.get("source_refs", []) if str(ref).strip()]
    return {
        "layer_id": layer_id,
        "block_id": block_id,
        "block_type": block_type,
        "target_slot": block.get("target_slot"),
        "source_refs": source_refs,
        "anchor": _estimated_layer_anchor(layer_id, index=index),
        "edit_policy": {
            "editable": True,
            "allowed_operations": ["append_note", "append_citation", "regenerate_block"],
        },
    }


def _estimated_layer_anchor(layer_id: str, *, index: int) -> dict[str, Any]:
    page_estimate = 2 + index // 4
    row = index % 4
    x = 64
    y = 96 + (row * 180)
    width = 672
    height = 150
    page_width = 800
    page_height = 1120
    normalized_bbox = [
        round(x / page_width, 4),
        round(y / page_height, 4),
        round((x + width) / page_width, 4),
        round((y + height) / page_height, 4),
    ]
    return {
        "anchor_kind": "estimated_dom_anchor",
        "page_estimate": page_estimate,
        "dom_selector": f'[data-layer-id="{layer_id}"]',
        "dom_bbox_px": {
            "x": x,
            "y": y,
            "width": width,
            "height": height,
        },
        "normalized_bbox": normalized_bbox,
        "bbox_precision": HTML_LAYER_BBOX_PRECISION,
    }


def _layer_id(block_id: str) -> str:
    return f"html_layer_{_class_token(block_id or 'block')}"


def _attr(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def _class_token(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in value) or "section"
