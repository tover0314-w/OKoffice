import hashlib
import json
from pathlib import Path

import pytest
from PIL import Image

from okoffice.renderers import html_package
from okoffice.schemas.errors import OKofficeException


def test_html_package_copies_local_image_assets_and_records_validation(tmp_path: Path) -> None:
    image_path = tmp_path / "diagram.png"
    Image.new("RGB", (64, 32), color=(40, 80, 120)).save(image_path)
    html_path = tmp_path / "audit.html"

    package = html_package.write_composition_html_package(
        composition_ir={
            "composition_id": "comp_html_assets",
            "context_packet_id": "ctxpkt_assets",
            "target_profile_id": "technical_audit",
            "blocks": [
                {
                    "block_id": "figure_1",
                    "type": "image",
                    "title": "Architecture Figure",
                    "target_slot": "evidence_figure",
                    "source_refs": ["ctx_image"],
                    "render_hints": {
                        "path": str(image_path),
                        "caption": "Local image evidence.",
                    },
                }
            ],
        },
        source_map=[
            {
                "block_id": "figure_1",
                "source_ref": "ctx_image",
                "type": "image",
            }
        ],
        target_profile={"profile_id": "technical_audit", "title": "Audit"},
        render_plan={"title": "Audit"},
        html_output_path=html_path,
        source_tool="pdf.compose.from_context",
    )

    manifest_path = html_path.with_suffix(".html-manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    asset = manifest["assets"][0]

    assert Path(asset["packaged_path"]).exists()
    assert asset["block_id"] == "figure_1"
    assert asset["source_path"] == str(image_path.resolve())
    assert asset["sha256"] == hashlib.sha256(image_path.read_bytes()).hexdigest()
    assert asset["relative_path"].startswith("audit.assets/")
    assert manifest["asset_count"] == 1
    assert manifest["render_profile"] == {
        "profile_id": "browser_print_a4_v0",
        "engine": "browser_print",
        "fallback_renderer": "local_html_package_fallback",
        "page_size": "A4",
        "prefer_css_page_size": True,
        "print_background": True,
        "scale": 1.0,
        "margin": {"top": "16mm", "right": "16mm", "bottom": "16mm", "left": "16mm"},
        "timeout_ms": 30000,
        "wait_until": "load",
        "javascript_enabled": False,
        "remote_assets_enabled": False,
        "allow_private_hosts": False,
        "allowed_origins": [],
    }
    assert manifest["renderer_constraints"] == {
        "network": "blocked",
        "javascript": "blocked",
        "file_urls": "blocked",
        "asset_policy": "local_packaged_assets_only",
        "bbox_precision": "estimated_dom_not_pdf_glyph_bbox",
    }
    assert manifest["layer_map_count"] == 1
    assert manifest["layer_map"][0]["layer_id"] == "html_layer_figure_1"
    assert manifest["layer_map"][0]["block_id"] == "figure_1"
    assert manifest["layer_map"][0]["anchor"]["bbox_precision"] == "estimated_dom_not_pdf_glyph_bbox"
    assert manifest["validation"]["status"] == "passed"
    assert [check["name"] for check in manifest["validation"]["checks"]] == [
        "html_package_manifest_valid",
        "all_assets_resolved",
        "html_layer_map_written",
        "render_profile_recorded",
        "no_remote_assets",
        "no_forbidden_asset_paths",
    ]

    html_text = html_path.read_text(encoding="utf-8")
    assert 'data-layer-id="html_layer_figure_1"' in html_text
    assert '<img src="./audit.assets/' in html_text
    assert 'data-asset-id="asset_figure_1_' in html_text
    assert package["html_package_manifest"]["assets"][0]["sha256"] == asset["sha256"]


def test_html_package_rejects_remote_image_assets(tmp_path: Path) -> None:
    with pytest.raises(OKofficeException) as exc_info:
        html_package.write_composition_html_package(
            composition_ir={
                "composition_id": "comp_remote_asset",
                "context_packet_id": "ctxpkt_assets",
                "target_profile_id": "technical_audit",
                "blocks": [
                    {
                        "block_id": "figure_1",
                        "type": "image",
                        "title": "Remote Figure",
                        "source_refs": ["ctx_image"],
                        "render_hints": {"path": "https://example.com/figure.png"},
                    }
                ],
            },
            source_map=[],
            target_profile={"profile_id": "technical_audit"},
            render_plan={"title": "Audit"},
            html_output_path=tmp_path / "audit.html",
            source_tool="pdf.compose.from_context",
        )

    assert exc_info.value.code == "unsafe_input_rejected"
    assert exc_info.value.details == {
        "html_package_error": "html_asset_blocked",
        "asset_ref": "https://example.com/figure.png",
    }


def test_render_html_package_validates_manifest_assets_and_outputs_pdf(tmp_path: Path) -> None:
    image_path = tmp_path / "diagram.png"
    Image.new("RGB", (64, 32), color=(40, 80, 120)).save(image_path)
    html_path = tmp_path / "audit.html"
    package = html_package.write_composition_html_package(
        composition_ir={
            "composition_id": "comp_render_package",
            "context_packet_id": "ctxpkt_render",
            "target_profile_id": "technical_audit",
            "blocks": [
                {
                    "block_id": "figure_1",
                    "type": "image",
                    "title": "Architecture Figure",
                    "source_refs": ["ctx_image"],
                    "render_hints": {"path": str(image_path), "caption": "Local image evidence."},
                }
            ],
        },
        source_map=[{"block_id": "figure_1", "source_ref": "ctx_image", "type": "image"}],
        target_profile={"profile_id": "technical_audit", "title": "Audit"},
        render_plan={"title": "Audit"},
        html_output_path=html_path,
        source_tool="pdf.compose.from_context",
    )
    output_pdf = tmp_path / "rendered.pdf"

    result = html_package.render_html_package(
        package["html_package_manifest_path"],
        output_pdf,
    )

    assert result.status == "succeeded"
    assert result.tool == "pdf.render.html_package"
    assert result.validation is not None
    assert result.validation.status == "passed"
    assert output_pdf.exists()
    assert result.usage["renderer"] == "local_html_package_fallback"
    assert result.usage["renderer_backend"] == {
        "backend_id": "local_html_package_fallback",
        "engine": "reportlab_text_fallback",
        "source": "okoffice.conversion.local.html_to_pdf",
        "is_browser_renderer": False,
        "fallback": True,
        "fallback_reason": "browser_renderer_worker_unavailable",
        "layout_fidelity": "text_layout_approximation",
        "network": "blocked",
        "javascript": "blocked",
        "file_urls": "blocked",
    }
    assert result.usage["render_profile"]["profile_id"] == "browser_print_a4_v0"
    assert result.usage["renderer_constraints"]["asset_policy"] == "local_packaged_assets_only"
    assert result.usage["html_package_manifest"]["asset_count"] == 1
    assert result.usage["html_package_validation"]["status"] == "passed"
    assert any(check.name == "html_package_manifest_valid" for check in result.validation.checks)
    assert any(check.name == "all_assets_resolved" for check in result.validation.checks)
    assert any(check.name == "render_profile_recorded" for check in result.validation.checks)
    assert any(check.name == "renderer_backend_declared" for check in result.validation.checks)
    assert any(str(artifact.path) == str(output_pdf.resolve()) for artifact in result.artifacts)
    assert "HTML/CSS layout is approximated" in result.warnings[0]


def test_render_html_package_reports_requested_browser_backend_when_unavailable(monkeypatch, tmp_path: Path) -> None:
    html_path = tmp_path / "browser-backend.html"
    package = html_package.write_composition_html_package(
        composition_ir={
            "composition_id": "comp_browser_backend",
            "context_packet_id": "ctxpkt_render",
            "target_profile_id": "technical_audit",
            "blocks": [{"block_id": "summary", "type": "section", "source_refs": ["ctx_001"]}],
        },
        source_map=[{"block_id": "summary", "source_ref": "ctx_001", "type": "section"}],
        target_profile={"profile_id": "technical_audit", "title": "Audit"},
        render_plan={"title": "Audit"},
        html_output_path=html_path,
        source_tool="pdf.compose.from_context",
    )
    output_pdf = tmp_path / "rendered.pdf"

    def missing_browser_render(**_kwargs: object):
        raise OKofficeException(
            "dependency_missing",
            "Chromium HTML rendering requires the optional Playwright dependency.",
        )

    monkeypatch.setattr(html_package, "browser_chromium_html_to_pdf", missing_browser_render)

    result = html_package.render_html_package(
        package["html_package_manifest_path"],
        output_pdf,
        renderer_backend="browser_chromium",
    )

    assert result.status == "failed"
    assert result.error is not None
    assert result.error.code == "dependency_missing"
    assert not output_pdf.exists()
    assert result.usage["requested_renderer_backend"] == "browser_chromium"
    assert result.usage["renderer"] == "browser_chromium"
    assert result.usage["render_skipped"] is True
    assert result.usage["render_skip_reason"] == "renderer_backend_unavailable"
    assert result.usage["renderer_backend"] == {
        "backend_id": "browser_chromium",
        "engine": "playwright_chromium",
        "source": "okoffice.renderers.browser_worker",
        "is_browser_renderer": True,
        "fallback": False,
        "available": False,
        "missing_optional_dependency": "playwright",
        "install_extra": "browser-renderer",
        "layout_fidelity": "browser_print_unavailable",
        "network": "blocked",
        "javascript": "blocked",
        "file_urls": "blocked",
    }
    assert result.usage["html_package_validation"]["status"] == "passed"
    failed_checks = {check.name for check in result.validation.checks if check.status == "failed"}
    assert failed_checks == {"renderer_backend_available"}
    assert any(
        check.name == "pdf_render_skipped_due_to_renderer_backend_unavailable" and check.status == "skipped"
        for check in result.validation.checks
    )


def test_render_html_package_uses_browser_backend_when_available(monkeypatch, tmp_path: Path) -> None:
    html_path = tmp_path / "browser-available.html"
    package = html_package.write_composition_html_package(
        composition_ir={
            "composition_id": "comp_browser_available",
            "context_packet_id": "ctxpkt_render",
            "target_profile_id": "technical_audit",
            "blocks": [{"block_id": "summary", "type": "section", "source_refs": ["ctx_001"]}],
        },
        source_map=[{"block_id": "summary", "source_ref": "ctx_001", "type": "section"}],
        target_profile={"profile_id": "technical_audit", "title": "Audit"},
        render_plan={"title": "Audit"},
        html_output_path=html_path,
        source_tool="pdf.compose.from_context",
    )
    output_pdf = tmp_path / "rendered.pdf"
    calls: list[dict[str, object]] = []

    def fake_browser_render(
        *,
        html_path: Path,
        manifest_path: Path,
        output_path: Path,
        render_profile: dict[str, object],
        renderer_constraints: dict[str, object],
    ):
        calls.append(
            {
                "html_path": html_path,
                "manifest_path": manifest_path,
                "output_path": output_path,
                "render_profile": render_profile,
                "renderer_constraints": renderer_constraints,
            }
        )
        return html_package.html_to_pdf(html_path, output_path)

    monkeypatch.setattr(html_package, "browser_chromium_html_to_pdf", fake_browser_render)

    result = html_package.render_html_package(
        package["html_package_manifest_path"],
        output_pdf,
        renderer_backend="browser_chromium",
    )

    assert result.status == "succeeded"
    assert output_pdf.exists()
    assert len(calls) == 1
    assert calls[0]["output_path"] == output_pdf.resolve()
    assert result.usage["requested_renderer_backend"] == "browser_chromium"
    assert result.usage["renderer"] == "browser_chromium"
    assert result.usage["renderer_backend"] == {
        "backend_id": "browser_chromium",
        "engine": "playwright_chromium",
        "source": "okoffice.renderers.browser_worker",
        "is_browser_renderer": True,
        "fallback": False,
        "available": True,
        "layout_fidelity": "browser_print",
        "network": "blocked",
        "javascript": "blocked",
        "file_urls": "blocked",
    }
    assert result.usage["render_skipped"] is False
    assert result.usage["render_skip_reason"] is None
    assert any(
        check.name == "renderer_backend_available" and check.status == "passed"
        for check in result.validation.checks
    )


def test_render_html_package_fails_when_render_profile_enables_unsafe_capabilities(tmp_path: Path) -> None:
    html_path = tmp_path / "unsafe-profile.html"
    package = html_package.write_composition_html_package(
        composition_ir={
            "composition_id": "comp_unsafe_profile",
            "context_packet_id": "ctxpkt_render",
            "target_profile_id": "technical_audit",
            "blocks": [{"block_id": "summary", "type": "section", "source_refs": ["ctx_001"]}],
        },
        source_map=[{"block_id": "summary", "source_ref": "ctx_001", "type": "section"}],
        target_profile={"profile_id": "technical_audit", "title": "Audit"},
        render_plan={"title": "Audit"},
        html_output_path=html_path,
        source_tool="pdf.compose.from_context",
    )
    manifest_path = Path(package["html_package_manifest_path"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["render_profile"]["javascript_enabled"] = True
    manifest["render_profile"]["remote_assets_enabled"] = True
    manifest["render_profile"]["allow_private_hosts"] = True
    manifest["render_profile"]["allowed_origins"] = ["https://example.com"]
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    output_pdf = tmp_path / "rendered.pdf"

    result = html_package.render_html_package(manifest_path, output_pdf)

    assert result.status == "failed"
    assert result.validation is not None
    assert not output_pdf.exists()
    assert result.usage["render_skipped"] is True
    assert result.usage["render_skip_reason"] == "html_package_validation_failed"
    failed_checks = {check.name for check in result.validation.checks if check.status == "failed"}
    assert {
        "render_profile_no_javascript",
        "render_profile_no_remote_assets",
        "render_profile_no_private_hosts",
        "render_profile_allowed_origins_empty",
    } <= failed_checks
    assert any(
        check.name == "pdf_render_skipped_due_to_html_package_validation" and check.status == "skipped"
        for check in result.validation.checks
    )
    assert result.usage["render_profile"]["javascript_enabled"] is True


def test_render_html_package_fails_when_manifest_asset_is_missing(tmp_path: Path) -> None:
    image_path = tmp_path / "diagram.png"
    Image.new("RGB", (64, 32), color=(40, 80, 120)).save(image_path)
    package = html_package.write_composition_html_package(
        composition_ir={
            "composition_id": "comp_missing_asset",
            "context_packet_id": "ctxpkt_render",
            "target_profile_id": "technical_audit",
            "blocks": [
                {
                    "block_id": "figure_1",
                    "type": "image",
                    "source_refs": ["ctx_image"],
                    "render_hints": {"path": str(image_path)},
                }
            ],
        },
        source_map=[],
        target_profile={"profile_id": "technical_audit"},
        render_plan={"title": "Audit"},
        html_output_path=tmp_path / "audit.html",
        source_tool="pdf.compose.from_context",
    )
    packaged_asset = Path(package["html_package_manifest"]["assets"][0]["packaged_path"])
    packaged_asset.unlink()

    with pytest.raises(OKofficeException) as exc_info:
        html_package.render_html_package(
            package["html_package_manifest_path"],
            tmp_path / "rendered.pdf",
        )

    assert exc_info.value.code == "html_asset_missing"
    assert exc_info.value.details["asset_id"] == package["html_package_manifest"]["assets"][0]["asset_id"]
