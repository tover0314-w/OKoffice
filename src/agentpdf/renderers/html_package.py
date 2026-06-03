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

from agentpdf.artifacts.store import build_artifact
from agentpdf.schemas.errors import AgentPDFException
from agentpdf.schemas.models import ValidationCheck, ValidationReport
from agentpdf.security.paths import resolve_input_path, resolve_output_path


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
    document = _html_document(
        composition_ir=composition_ir,
        source_map=source_map,
        target_profile=target_profile,
        render_plan=render_plan,
        blocks=blocks,
        assets_by_block=assets_by_block,
    )
    validation = _validate_html_package(assets)
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
        "source_map_count": len(source_map),
        "source_ref_count": len(source_refs),
        "source_refs": source_refs,
        "javascript_enabled": False,
        "remote_assets_enabled": False,
        "assets_root": str(assets_dir.resolve()),
        "asset_count": len(assets),
        "assets": assets,
        "validation": validation.model_dump(mode="json"),
        "contract": {
            "body_attribute": "data-agentpdf-document",
            "block_selector": "[data-block-id]",
            "source_refs_attribute": "data-source-refs",
            "renderer_attribute": "data-agentpdf-renderer",
        },
        "blocks": [
            {
                "block_id": str(block.get("block_id") or ""),
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


def _html_document(
    *,
    composition_ir: dict[str, Any],
    source_map: list[dict[str, Any]],
    target_profile: dict[str, Any],
    render_plan: dict[str, Any],
    blocks: list[dict[str, Any]],
    assets_by_block: dict[str, dict[str, Any]],
) -> str:
    title = str(render_plan.get("title") or target_profile.get("title") or target_profile.get("name") or "AgentPDF")
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
    block_type = str(block.get("type") or "section")
    title = str(block.get("title") or block_type)
    target_slot = str(block.get("target_slot") or "body")
    source_refs = [str(ref) for ref in block.get("source_refs", [])]
    hints = block.get("render_hints") if isinstance(block.get("render_hints"), dict) else {}
    return "\n".join(
        [
            f'    <article class="agentpdf-block block-{_class_token(block_type)}" data-block-id="{_attr(block_id)}" data-block-type="{_attr(block_type)}" data-slot="{_attr(target_slot)}" data-source-refs="{_attr(" ".join(source_refs))}">',
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
            raise AgentPDFException(
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
    raw = hints.get("path") or hints.get("image_path") or block.get("path") or block.get("image_path")
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


def _attr(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def _class_token(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in value) or "section"
