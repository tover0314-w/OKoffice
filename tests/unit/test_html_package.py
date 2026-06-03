import hashlib
import json
from pathlib import Path

import pytest
from PIL import Image

from agentpdf.renderers.html_package import write_composition_html_package
from agentpdf.schemas.errors import AgentPDFException


def test_html_package_copies_local_image_assets_and_records_validation(tmp_path: Path) -> None:
    image_path = tmp_path / "diagram.png"
    Image.new("RGB", (64, 32), color=(40, 80, 120)).save(image_path)
    html_path = tmp_path / "audit.html"

    package = write_composition_html_package(
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
        write_composition_html_package(
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
