import hashlib
import json
from pathlib import Path

import pytest
from PIL import Image

from agentpdf.renderers import html_package
from agentpdf.schemas.errors import AgentPDFException


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
    assert manifest["validation"]["status"] == "passed"
    assert [check["name"] for check in manifest["validation"]["checks"]] == [
        "html_package_manifest_valid",
        "all_assets_resolved",
        "no_remote_assets",
        "no_forbidden_asset_paths",
    ]

    html_text = html_path.read_text(encoding="utf-8")
    assert '<img src="./audit.assets/' in html_text
    assert 'data-asset-id="asset_figure_1_' in html_text
    assert package["html_package_manifest"]["assets"][0]["sha256"] == asset["sha256"]


def test_html_package_rejects_remote_image_assets(tmp_path: Path) -> None:
    with pytest.raises(AgentPDFException) as exc_info:
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
    assert result.usage["html_package_manifest"]["asset_count"] == 1
    assert result.usage["html_package_validation"]["status"] == "passed"
    assert any(check.name == "html_package_manifest_valid" for check in result.validation.checks)
    assert any(check.name == "all_assets_resolved" for check in result.validation.checks)
    assert any(str(artifact.path) == str(output_pdf.resolve()) for artifact in result.artifacts)
    assert "HTML/CSS layout is approximated" in result.warnings[0]


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

    with pytest.raises(AgentPDFException) as exc_info:
        html_package.render_html_package(
            package["html_package_manifest_path"],
            tmp_path / "rendered.pdf",
        )

    assert exc_info.value.code == "html_asset_missing"
    assert exc_info.value.details["asset_id"] == package["html_package_manifest"]["assets"][0]["asset_id"]
