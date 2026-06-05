import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator
from pypdf import PdfReader
from typer.testing import CliRunner

from agentpdf.artifacts import bundle as artifact_bundle
from agentpdf.api.app import create_app
from agentpdf.artifacts.bundle import export_artifact_bundle
from agentpdf.cli.main import app
from agentpdf.compose.context import compose_from_context
from agentpdf.context.packet import build_context_packet
from agentpdf.core.pdf import create_text_pdf
from agentpdf.mcp import server as mcp_server
from agentpdf.mcp.server import pdf_artifacts_export_bundle
from agentpdf.patch.transaction import apply_patch_transaction, plan_patch_transaction
from agentpdf.renderers.html_package import render_html_package
from agentpdf.tools.runner import run_create_html_package


runner = CliRunner()


def test_artifact_manifest_collects_metadata_source_refs_and_evidence_links(tmp_path: Path) -> None:
    pdf_path = tmp_path / "report.pdf"
    composition_path = tmp_path / "report.composition.json"
    coverage_path = tmp_path / "report.coverage.json"
    patch_path = tmp_path / "report.patch.json"
    output_path = tmp_path / "report.artifacts.json"
    create_text_pdf("Artifact manifests keep generated outputs auditable.", pdf_path)
    composition_path.write_text(
        json.dumps(
            {
                "composition_id": "cmp_report",
                "composition_ir": {
                    "blocks": [
                        {
                            "block_id": "blk_summary",
                            "type": "section",
                            "source_refs": ["ctx_text"],
                        }
                    ]
                },
                "source_map": [{"block_id": "blk_summary", "source_ref": "ctx_text"}],
            }
        ),
        encoding="utf-8",
    )
    coverage_path.write_text(
        json.dumps({"coverage": {"coverage_ratio": 1.0}, "source_refs": ["ctx_text"]}),
        encoding="utf-8",
    )
    patch_path.write_text(
        json.dumps(
            {
                "patch_id": "patch_report",
                "operations": [{"op": "append_markdown", "source_refs": ["ctx_patch"]}],
            }
        ),
        encoding="utf-8",
    )

    assert hasattr(artifact_bundle, "create_artifact_manifest")
    result = artifact_bundle.create_artifact_manifest(
        artifact_paths=[pdf_path, composition_path, coverage_path, patch_path],
        output_path=output_path,
        title="Report Artifact Manifest",
        metadata={"workflow": "context-packet-patch"},
    )

    assert result.status == "succeeded"
    assert result.tool == "pdf.artifacts.manifest"
    assert result.artifacts[0].mime_type == "application/json"
    manifest = result.usage["artifact_manifest"]
    assert manifest["manifest_version"] == "0.1"
    assert manifest["title"] == "Report Artifact Manifest"
    assert manifest["metadata"]["workflow"] == "context-packet-patch"
    assert manifest["artifact_count"] == 4
    assert manifest["source_refs"] == ["ctx_patch", "ctx_text"]
    assert manifest["source_ref_count"] == 2
    assert manifest["evidence_links"]["composition"] == [composition_path.resolve().as_posix()]
    assert manifest["evidence_links"]["coverage"] == [coverage_path.resolve().as_posix()]
    assert manifest["evidence_links"]["patch"] == [patch_path.resolve().as_posix()]
    assert manifest["artifacts"][0]["path"] == pdf_path.resolve().as_posix()
    assert manifest["artifacts"][0]["page_count"] == 1
    assert manifest["artifacts"][0]["sha256"]
    saved = json.loads(output_path.read_text(encoding="utf-8"))
    assert saved["manifest_id"].startswith("artifact_manifest_")
    assert saved["safety"]["mutates_inputs"] is False
    assert result.next_recommended_tools == ["pdf.artifacts.export_bundle", "pdf.artifacts.graph"]


def test_artifact_manifest_indexes_context_packet_evidence_for_audit_graph(tmp_path: Path) -> None:
    pdf_path = tmp_path / "report.pdf"
    composition_path = tmp_path / "report.composition.json"
    context_packet_path = tmp_path / "report.context.packet.json"
    manifest_path = tmp_path / "report.artifacts.json"
    graph_path = tmp_path / "report.artifact-graph.json"
    create_text_pdf("Context packet evidence should remain auditable through artifact manifests.", pdf_path)
    composition_path.write_text(
        json.dumps(
            {
                "composition_id": "cmp_context_audit",
                "composition_ir": {
                    "blocks": [
                        {"block_id": "blk_citation", "type": "section", "source_refs": ["ctx_web"]},
                        {"block_id": "blk_code", "type": "code", "source_refs": ["ctx_code"]},
                    ]
                },
                "source_map": [
                    {"block_id": "blk_citation", "source_ref": "ctx_web", "page_number": 1},
                    {"block_id": "blk_code", "source_ref": "ctx_code", "page_number": 1},
                ],
            }
        ),
        encoding="utf-8",
    )
    context_packet_path.write_text(
        json.dumps(
            {
                "context_packet_version": "0.1",
                "context_packet_id": "ctxpkt_audit",
                "items": [
                    {
                        "context_item_id": "ctx_001",
                        "source_ref": "ctx_web",
                        "type": "web_link",
                        "role": "citation",
                        "label": "Context Docs",
                        "uri": "https://okpdf.dev/docs/context",
                        "metadata": {
                            "citation_evidence": {
                                "normalized_url": "https://okpdf.dev/docs/context",
                                "domain": "okpdf.dev",
                                "fetch_status": "not_fetched",
                                "analysis_method": "local_url_metadata_v0",
                            }
                        },
                    },
                    {
                        "context_item_id": "ctx_002",
                        "source_ref": "ctx_code",
                        "type": "code",
                        "role": "code_evidence",
                        "label": "Renderer",
                        "metadata": {
                            "code_evidence": {
                                "language": "python",
                                "analysis_method": "local_code_symbol_scan_v0",
                            }
                        },
                    },
                ],
                "source_graph": {"source_graph_id": "srcgraph_audit", "nodes": [], "edges": []},
            }
        ),
        encoding="utf-8",
    )

    manifest_result = artifact_bundle.create_artifact_manifest(
        artifact_paths=[pdf_path, composition_path, context_packet_path],
        output_path=manifest_path,
        title="Context Audit Manifest",
    )

    manifest = manifest_result.usage["artifact_manifest"]
    assert manifest["context_packet_count"] == 1
    assert manifest["source_graph_ids"] == ["srcgraph_audit"]
    assert manifest["context_packet_refs"] == [
        {
            "context_packet_id": "ctxpkt_audit",
            "path": context_packet_path.resolve().as_posix(),
            "source_graph_id": "srcgraph_audit",
            "item_count": 2,
            "source_ref_count": 2,
        }
    ]
    assert manifest["context_evidence_index"]["ctx_web"]["context_item_type"] == "web_link"
    assert manifest["context_evidence_index"]["ctx_web"]["primary_evidence_kind"] == "citation_evidence"
    assert manifest["context_evidence_index"]["ctx_web"]["fetch_status"] == "not_fetched"
    assert manifest["context_evidence_index"]["ctx_code"]["context_item_type"] == "code"
    assert manifest["context_evidence_index"]["ctx_code"]["primary_evidence_kind"] == "code_evidence"

    graph_result = artifact_bundle.build_artifact_graph(
        artifact_manifest_path=manifest_path,
        output_path=graph_path,
        title="Context Audit Graph",
    )

    graph = graph_result.usage["artifact_graph"]
    assert graph["source_ref_index"]["ctx_web"]["context_packet_ids"] == ["ctxpkt_audit"]
    assert graph["source_ref_index"]["ctx_web"]["context_item_type"] == "web_link"
    assert graph["source_ref_index"]["ctx_web"]["primary_evidence_kind"] == "citation_evidence"
    assert graph["source_ref_index"]["ctx_code"]["context_item_type"] == "code"


def test_artifact_manifest_and_graph_preserve_context_source_graph_sidecars(tmp_path: Path) -> None:
    audio_path = tmp_path / "meeting.mp3"
    audio_path.write_bytes(b"ID3 local audio fixture")
    transcript_path = tmp_path / "meeting.transcript.txt"
    transcript_path.write_text("00:00 Kickoff\n00:22 Decision evidence.", encoding="utf-8")
    packet_path = tmp_path / "media.context.packet.json"
    pdf_path = tmp_path / "media-audit.pdf"
    manifest_path = tmp_path / "media-audit.artifacts.json"
    graph_path = tmp_path / "media-audit.artifact-graph.json"

    packet = build_context_packet(
        [
            {
                "context_item_id": "ctx_audio",
                "path": str(audio_path),
                "role": "audio_context",
                "label": "Meeting Audio",
                "transcript_path": str(transcript_path),
            }
        ],
        output_path=packet_path,
        title="Media Sidecar Context",
    ).usage["context_packet"]

    compose_from_context(packet, target_profile="technical_audit", output_path=pdf_path)
    composition_path = pdf_path.with_suffix(".composition.json")

    manifest_result = artifact_bundle.create_artifact_manifest(
        artifact_paths=[pdf_path, composition_path, packet_path],
        output_path=manifest_path,
        title="Media Sidecar Manifest",
    )

    manifest = manifest_result.usage["artifact_manifest"]
    transcript_ref = next(ref for ref in manifest["source_graph_node_refs"] if ref["type"] == "transcript")
    assert manifest["source_graph_node_count"] == 2
    assert manifest["source_graph_edge_count"] == 1
    assert transcript_ref["source_graph_id"] == packet["source_graph"]["source_graph_id"]
    assert transcript_ref["source_ref"] == "ctx_audio#transcript"
    assert transcript_ref["uri"] == transcript_path.resolve().as_posix()
    assert transcript_ref["evidence"]["sha256"] == packet["items"][0]["metadata"]["transcript_sha256"]
    assert manifest["source_graph_edge_refs"] == [
        {
            "source_graph_id": packet["source_graph"]["source_graph_id"],
            "context_packet_id": packet["context_packet_id"],
            "from_node_id": transcript_ref["node_id"],
            "to_node_id": "src_001",
            "relation": "provides_transcript_for",
            "context_item_id": "ctx_audio",
            "source_ref": "ctx_audio",
            "sidecar_source_ref": "ctx_audio#transcript",
        }
    ]
    assert manifest["context_evidence_index"]["ctx_audio#transcript"]["context_item_type"] == "transcript"
    assert manifest["context_evidence_index"]["ctx_audio#transcript"]["primary_evidence_kind"] == "transcript_sidecar"

    graph = artifact_bundle.build_artifact_graph(
        artifact_manifest_path=manifest_path,
        output_path=graph_path,
        title="Media Sidecar Graph",
    ).usage["artifact_graph"]

    assert graph["source_graph_node_count"] == 2
    assert graph["source_graph_edge_count"] == 1
    assert graph["source_graph_node_index"][transcript_ref["graph_node_key"]]["source_ref"] == "ctx_audio#transcript"
    assert graph["source_ref_index"]["ctx_audio#transcript"]["context_item_type"] == "transcript"
    assert graph["source_ref_index"]["ctx_audio#transcript"]["primary_evidence_kind"] == "transcript_sidecar"
    assert any(edge["relation"] == "provides_transcript_for" for edge in graph["edges"])


def test_artifact_manifest_tracks_html_first_package_lineage(tmp_path: Path) -> None:
    html_path = tmp_path / "html-first.html"
    pdf_path = tmp_path / "html-first.pdf"
    manifest_path = tmp_path / "html-first.artifacts.json"
    graph_path = tmp_path / "html-first.artifact-graph.json"

    html_package = run_create_html_package(
        page_document=None,
        html="<main><h1>HTML First</h1><p>Auditable HTML source before PDF.</p></main>",
        html_output_path=html_path,
        title="HTML First",
    )
    html_package_manifest_path = Path(html_package.usage["html_package_manifest_path"])
    rendered = render_html_package(html_package_manifest_path, pdf_path)

    result = artifact_bundle.create_artifact_manifest(
        artifact_paths=[html_path, html_package_manifest_path, pdf_path],
        output_path=manifest_path,
        title="HTML First Artifact Manifest",
        metadata={"workflow": "html-first-createpdf"},
    )

    manifest = result.usage["artifact_manifest"]
    assert rendered.status == "succeeded"
    assert manifest["html_package_count"] == 1
    assert manifest["evidence_links"]["html"] == [html_path.resolve().as_posix()]
    assert manifest["evidence_links"]["html_package"] == [html_package_manifest_path.resolve().as_posix()]
    assert manifest["html_package_refs"] == [
        {
            "html_package_id": html_package.usage["html_package_manifest"]["html_package_id"],
            "path": html_package_manifest_path.resolve().as_posix(),
            "html_path": html_path.resolve().as_posix(),
            "renderer_contract": "html-package-v0",
            "source_format": "raw_html",
            "asset_count": 0,
            "validation_status": "passed",
        }
    ]
    assert manifest["html_render_profile_count"] == 1
    assert manifest["html_render_profile_refs"] == [
        {
            "html_package_id": html_package.usage["html_package_manifest"]["html_package_id"],
            "path": html_package_manifest_path.resolve().as_posix(),
            "html_path": html_path.resolve().as_posix(),
            "renderer_contract": "html-package-v0",
            "render_profile_id": "browser_print_a4_v0",
            "render_profile": html_package.usage["html_package_manifest"]["render_profile"],
            "renderer_constraints": html_package.usage["html_package_manifest"]["renderer_constraints"],
            "page_size": "A4",
            "prefer_css_page_size": True,
            "print_background": True,
            "javascript_enabled": False,
            "remote_assets_enabled": False,
        }
    ]
    assert manifest["renderer_backend_count"] == 1
    assert manifest["renderer_backend_refs"] == [
        {
            "html_package_id": html_package.usage["html_package_manifest"]["html_package_id"],
            "path": html_package_manifest_path.resolve().as_posix(),
            "html_path": html_path.resolve().as_posix(),
            "renderer_contract": "html-package-v0",
            "backend_id": "local_html_package_fallback",
            "renderer_backend": rendered.usage["renderer_backend"],
            "engine": "reportlab_text_fallback",
            "source": "agentpdf.conversion.local.html_to_pdf",
            "is_browser_renderer": False,
            "fallback": True,
            "fallback_reason": "browser_renderer_worker_unavailable",
            "layout_fidelity": "text_layout_approximation",
            "network": "blocked",
            "javascript": "blocked",
            "file_urls": "blocked",
        }
    ]
    html_package_entry = next(entry for entry in manifest["artifacts"] if entry["artifact_kind"] == "html_package")
    assert html_package_entry["renderer_contract"] == "html-package-v0"
    assert html_package_entry["source_format"] == "raw_html"
    assert html_package_entry["validation_status"] == "passed"
    assert html_package_entry["render_profile_id"] == "browser_print_a4_v0"
    assert html_package_entry["renderer_backend_id"] == "local_html_package_fallback"

    graph_result = artifact_bundle.build_artifact_graph(
        artifact_manifest_path=manifest_path,
        output_path=graph_path,
        title="HTML First Artifact Graph",
    )

    graph = graph_result.usage["artifact_graph"]
    assert graph["html_package_refs"] == manifest["html_package_refs"]
    assert graph["html_render_profile_refs"] == manifest["html_render_profile_refs"]
    assert graph["renderer_backend_refs"] == manifest["renderer_backend_refs"]
    assert graph["html_render_profile_count"] == 1
    assert graph["renderer_backend_count"] == 1
    assert graph["html_render_profile_index"]["browser_print_a4_v0"]["page_size"] == "A4"
    assert graph["html_render_profile_index"]["browser_print_a4_v0"]["html_package_ids"] == [
        html_package.usage["html_package_manifest"]["html_package_id"]
    ]
    assert graph["renderer_backend_index"]["local_html_package_fallback"]["fallback"] is True
    assert graph["renderer_backend_index"]["local_html_package_fallback"]["html_package_ids"] == [
        html_package.usage["html_package_manifest"]["html_package_id"]
    ]
    assert any(
        node["type"] == "renderer_backend" and node["backend_id"] == "local_html_package_fallback"
        for node in graph["nodes"]
    )
    relations = {edge["relation"] for edge in graph["edges"]}
    assert {
        "describes_html_source",
        "renders_to_pdf",
        "html_package_uses_render_profile",
        "html_package_uses_renderer_backend",
    } <= relations


def test_artifact_manifest_and_graph_index_html_layer_map(tmp_path: Path) -> None:
    csv_path = tmp_path / "metrics.csv"
    csv_path.write_text("metric,value\nlatency_ms,42\n", encoding="utf-8")
    packet = build_context_packet(
        [
            {"text": "Create a technical audit PDF with traceable HTML layers.", "role": "brief"},
            {"path": str(csv_path), "role": "data_evidence", "label": "Runtime Metrics"},
        ],
        output_path=tmp_path / "context.packet.json",
        title="Layer Audit Context",
    ).usage["context_packet"]
    pdf_path = tmp_path / "layer-audit.pdf"
    html_path = tmp_path / "layer-audit.html"
    manifest_path = tmp_path / "layer-audit.artifacts.json"
    graph_path = tmp_path / "layer-audit.artifact-graph.json"

    composed = compose_from_context(
        packet,
        target_profile="technical_audit",
        output_path=pdf_path,
        renderer="html",
        html_output_path=html_path,
        title="Layer Audit",
    )
    html_manifest_path = Path(composed.usage["html_package_manifest_path"])
    composition_path = pdf_path.with_suffix(".composition.json")

    manifest_result = artifact_bundle.create_artifact_manifest(
        artifact_paths=[html_path, html_manifest_path, pdf_path, composition_path],
        output_path=manifest_path,
        title="Layer Audit Manifest",
    )

    manifest = manifest_result.usage["artifact_manifest"]
    table_layer = next(layer for layer in manifest["html_layer_refs"] if layer["block_id"] == "item_ctx_002")
    assert manifest["html_layer_count"] == composed.usage["html_package_manifest"]["layer_map_count"]
    assert table_layer["layer_id"] == "html_layer_item_ctx_002"
    assert table_layer["html_package_id"] == composed.usage["html_package_manifest"]["html_package_id"]
    assert table_layer["block_type"] == "table"
    assert table_layer["source_refs"] == ["ctx_002"]
    assert table_layer["anchor"]["bbox_precision"] == "estimated_dom_not_pdf_glyph_bbox"
    html_package_entry = next(entry for entry in manifest["artifacts"] if entry["artifact_kind"] == "html_package")
    assert html_package_entry["html_layer_count"] == manifest["html_layer_count"]

    graph_result = artifact_bundle.build_artifact_graph(
        artifact_manifest_path=manifest_path,
        output_path=graph_path,
        title="Layer Audit Graph",
    )

    graph = graph_result.usage["artifact_graph"]
    assert graph["html_layer_count"] == manifest["html_layer_count"]
    assert graph["html_layer_index"][table_layer["layer_id"]]["block_id"] == "item_ctx_002"
    assert graph["html_layer_index"][table_layer["layer_id"]]["source_refs"] == ["ctx_002"]
    layer_node = next(
        node for node in graph["nodes"] if node["type"] == "html_layer" and node["layer_id"] == table_layer["layer_id"]
    )
    assert layer_node["anchor"]["dom_selector"] == f'[data-layer-id="{table_layer["layer_id"]}"]'
    relations = {edge["relation"] for edge in graph["edges"]}
    assert {"defines_html_layer", "layer_uses_source_ref"} <= relations


def test_patch_plan_uses_artifact_graph_html_layer_evidence(tmp_path: Path) -> None:
    csv_path = tmp_path / "metrics.csv"
    csv_path.write_text("metric,value\nlatency_ms,42\n", encoding="utf-8")
    packet = build_context_packet(
        [
            {"text": "Create a technical audit PDF with patchable HTML layers.", "role": "brief"},
            {"path": str(csv_path), "role": "data_evidence", "label": "Runtime Metrics"},
        ],
        output_path=tmp_path / "context.packet.json",
        title="Patchable Layer Context",
    ).usage["context_packet"]
    pdf_path = tmp_path / "patchable-layer.pdf"
    html_path = tmp_path / "patchable-layer.html"
    manifest_path = tmp_path / "patchable-layer.artifacts.json"
    graph_path = tmp_path / "patchable-layer.artifact-graph.json"
    patch_path = tmp_path / "patchable-layer.patch.json"

    composed = compose_from_context(
        packet,
        target_profile="technical_audit",
        output_path=pdf_path,
        renderer="html",
        html_output_path=html_path,
        title="Patchable Layer",
    )
    html_manifest_path = Path(composed.usage["html_package_manifest_path"])
    composition_path = pdf_path.with_suffix(".composition.json")
    artifact_manifest = artifact_bundle.create_artifact_manifest(
        artifact_paths=[html_path, html_manifest_path, pdf_path, composition_path],
        output_path=manifest_path,
        title="Patchable Layer Manifest",
    ).usage["artifact_manifest"]
    table_layer = next(layer for layer in artifact_manifest["html_layer_refs"] if layer["block_id"] == "item_ctx_002")
    artifact_bundle.build_artifact_graph(
        artifact_manifest_path=manifest_path,
        output_path=graph_path,
        title="Patchable Layer Graph",
    )

    result = plan_patch_transaction(
        input_path=pdf_path,
        operations=[
            {
                "op": "regenerate_block",
                "title": "Refresh Runtime Metrics",
                "replacement_markdown": "## Runtime Metrics\n\nLatency evidence was refreshed from the source table.",
                "source_refs": ["ctx_002"],
                "html_layer_id": table_layer["layer_id"],
            }
        ],
        output_path=patch_path,
        composition_path=composition_path,
        artifact_graph_path=graph_path,
    )

    manifest = result.usage["patch_manifest"]
    operation = manifest["operations"][0]
    html_layer_evidence = operation["html_layer_evidence"][0]
    html_layer_map = manifest["operation_html_layer_map"][0]
    assert result.status == "succeeded"
    assert manifest["artifact_graph_path"] == graph_path.resolve().as_posix()
    assert manifest["html_layer_ref_validation"]["status"] == "passed"
    assert manifest["html_layer_ref_validation"]["requested_html_layer_ids"] == [table_layer["layer_id"]]
    assert operation["target_html_layer_refs"] == {"html_layer_ids": [table_layer["layer_id"]]}
    assert html_layer_evidence["layer_id"] == table_layer["layer_id"]
    assert html_layer_evidence["block_id"] == "item_ctx_002"
    assert html_layer_evidence["source_refs"] == ["ctx_002"]
    assert html_layer_evidence["anchor"]["bbox_precision"] == "estimated_dom_not_pdf_glyph_bbox"
    assert html_layer_map["matched_html_layer_count"] == 1
    assert html_layer_map["matched_html_layers"][0]["layer_id"] == table_layer["layer_id"]


def test_patch_apply_rerenders_html_source_for_html_layer_regeneration(tmp_path: Path) -> None:
    csv_path = tmp_path / "metrics.csv"
    csv_path.write_text("metric,value\nlatency_ms,42\n", encoding="utf-8")
    packet = build_context_packet(
        [
            {"text": "Create a technical audit PDF with HTML source patching.", "role": "brief"},
            {"path": str(csv_path), "role": "data_evidence", "label": "Runtime Metrics"},
        ],
        output_path=tmp_path / "context.packet.json",
        title="HTML Apply Context",
    ).usage["context_packet"]
    pdf_path = tmp_path / "html-apply.pdf"
    html_path = tmp_path / "html-apply.html"
    manifest_path = tmp_path / "html-apply.artifacts.json"
    graph_path = tmp_path / "html-apply.artifact-graph.json"
    patch_path = tmp_path / "html-apply.patch.json"
    patched_pdf_path = tmp_path / "html-apply-patched.pdf"
    replacement = "HTML layer replacement rendered from ctx_002."

    composed = compose_from_context(
        packet,
        target_profile="technical_audit",
        output_path=pdf_path,
        renderer="html",
        html_output_path=html_path,
        title="HTML Apply",
    )
    html_manifest_path = Path(composed.usage["html_package_manifest_path"])
    composition_path = pdf_path.with_suffix(".composition.json")
    artifact_manifest = artifact_bundle.create_artifact_manifest(
        artifact_paths=[html_path, html_manifest_path, pdf_path, composition_path],
        output_path=manifest_path,
        title="HTML Apply Manifest",
    ).usage["artifact_manifest"]
    table_layer = next(layer for layer in artifact_manifest["html_layer_refs"] if layer["block_id"] == "item_ctx_002")
    artifact_bundle.build_artifact_graph(
        artifact_manifest_path=manifest_path,
        output_path=graph_path,
        title="HTML Apply Graph",
    )
    plan_patch_transaction(
        input_path=pdf_path,
        operations=[
            {
                "op": "regenerate_block",
                "title": "Refresh Runtime Metrics",
                "replacement_markdown": f"## Runtime Metrics\n\n{replacement}",
                "source_refs": ["ctx_002"],
                "html_layer_id": table_layer["layer_id"],
            }
        ],
        output_path=patch_path,
        composition_path=composition_path,
        artifact_graph_path=graph_path,
    )

    result = apply_patch_transaction(patch_path, output_path=patched_pdf_path)

    html_layer_patch = result.usage["html_layer_patch"]
    patched_html_path = Path(html_layer_patch["html_output_path"])
    patched_manifest_path = Path(html_layer_patch["html_package_manifest_path"])
    patched_text = "\n".join(page.extract_text() or "" for page in PdfReader(patched_pdf_path).pages)
    assert result.status == "succeeded"
    assert result.usage["patch_manifest"]["apply_mode"] == "html_layer_rerender"
    assert result.usage["patch_manifest"]["operations"][0]["regeneration_policy"]["actual_effect"] == "html_layer_rerender"
    assert html_layer_patch["rewritten_layer_ids"] == [table_layer["layer_id"]]
    assert patched_html_path.exists()
    assert patched_manifest_path.exists()
    assert replacement in patched_html_path.read_text(encoding="utf-8")
    assert replacement not in html_path.read_text(encoding="utf-8")
    assert replacement in patched_text
    assert result.usage["input_unchanged"] is True


def test_artifact_graph_links_html_layer_rerender_patch_outputs(tmp_path: Path) -> None:
    csv_path = tmp_path / "metrics.csv"
    csv_path.write_text("metric,value\nlatency_ms,42\n", encoding="utf-8")
    packet = build_context_packet(
        [
            {"text": "Create a technical audit PDF with HTML rerender lineage.", "role": "brief"},
            {"path": str(csv_path), "role": "data_evidence", "label": "Runtime Metrics"},
        ],
        output_path=tmp_path / "context.packet.json",
        title="HTML Lineage Context",
    ).usage["context_packet"]
    pdf_path = tmp_path / "html-lineage.pdf"
    html_path = tmp_path / "html-lineage.html"
    source_manifest_path = tmp_path / "html-lineage.artifacts.json"
    source_graph_path = tmp_path / "html-lineage.artifact-graph.json"
    patch_path = tmp_path / "html-lineage.patch.json"
    patched_pdf_path = tmp_path / "html-lineage-patched.pdf"
    output_manifest_path = tmp_path / "html-lineage-patched.artifacts.json"
    output_graph_path = tmp_path / "html-lineage-patched.artifact-graph.json"

    composed = compose_from_context(
        packet,
        target_profile="technical_audit",
        output_path=pdf_path,
        renderer="html",
        html_output_path=html_path,
        title="HTML Lineage",
    )
    html_manifest_path = Path(composed.usage["html_package_manifest_path"])
    composition_path = pdf_path.with_suffix(".composition.json")
    source_manifest = artifact_bundle.create_artifact_manifest(
        artifact_paths=[html_path, html_manifest_path, pdf_path, composition_path],
        output_path=source_manifest_path,
        title="HTML Lineage Source Manifest",
    ).usage["artifact_manifest"]
    table_layer = next(layer for layer in source_manifest["html_layer_refs"] if layer["block_id"] == "item_ctx_002")
    artifact_bundle.build_artifact_graph(
        artifact_manifest_path=source_manifest_path,
        output_path=source_graph_path,
        title="HTML Lineage Source Graph",
    )
    plan_patch_transaction(
        input_path=pdf_path,
        operations=[
            {
                "op": "regenerate_block",
                "title": "Refresh Runtime Metrics",
                "replacement_markdown": "## Runtime Metrics\n\nLineage evidence for patched HTML.",
                "source_refs": ["ctx_002"],
                "html_layer_id": table_layer["layer_id"],
            }
        ],
        output_path=patch_path,
        composition_path=composition_path,
        artifact_graph_path=source_graph_path,
    )
    apply_patch_transaction(patch_path, output_path=patched_pdf_path)
    patch_applied_path = patched_pdf_path.with_suffix(".patch-applied.json")
    patched_html_path = patched_pdf_path.with_suffix(".html")
    patched_html_manifest_path = patched_html_path.with_suffix(".html-manifest.json")

    manifest = artifact_bundle.create_artifact_manifest(
        artifact_paths=[
            pdf_path,
            html_path,
            html_manifest_path,
            patch_path,
            patched_pdf_path,
            patched_html_path,
            patched_html_manifest_path,
            patch_applied_path,
        ],
        output_path=output_manifest_path,
        title="HTML Lineage Patched Manifest",
    ).usage["artifact_manifest"]
    graph = artifact_bundle.build_artifact_graph(
        artifact_manifest_path=output_manifest_path,
        output_path=output_graph_path,
        title="HTML Lineage Patched Graph",
    ).usage["artifact_graph"]

    patch_ref = manifest["html_layer_patch_refs"][0]
    assert manifest["html_layer_patch_count"] == 1
    assert patch_ref["patch_applied_path"] == patch_applied_path.resolve().as_posix()
    assert patch_ref["output_path"] == patched_pdf_path.resolve().as_posix()
    assert patch_ref["html_output_path"] == patched_html_path.resolve().as_posix()
    assert patch_ref["html_package_manifest_path"] == patched_html_manifest_path.resolve().as_posix()
    assert patch_ref["rewritten_layer_ids"] == [table_layer["layer_id"]]
    assert graph["html_layer_patch_count"] == 1
    relations = {edge["relation"] for edge in graph["edges"]}
    assert {
        "patch_rerenders_pdf",
        "patch_writes_html_source",
        "patch_writes_html_package",
        "patch_rewrites_html_layer",
    } <= relations
    assert graph["html_layer_patch_refs"][0]["patch_id"].startswith("patch_")


def test_artifact_manifest_cli_api_and_mcp_are_exposed(tmp_path: Path) -> None:
    pdf_path = tmp_path / "report.pdf"
    composition_path = tmp_path / "report.composition.json"
    create_text_pdf("Artifact manifest interfaces.", pdf_path)
    composition_path.write_text(
        json.dumps({"source_map": [{"source_ref": "ctx_cli"}]}),
        encoding="utf-8",
    )

    cli_output = tmp_path / "cli-artifacts.json"
    cli = runner.invoke(
        app,
        [
            "artifacts",
            "manifest",
            "--file",
            str(pdf_path),
            "--file",
            str(composition_path),
            "-o",
            str(cli_output),
            "--title",
            "CLI Artifact Manifest",
            "--metadata",
            "agent=codex",
            "--json",
        ],
    )

    assert cli.exit_code == 0
    cli_payload = json.loads(cli.stdout)
    assert cli_payload["tool"] == "pdf.artifacts.manifest"
    assert cli_payload["usage"]["artifact_manifest"]["metadata"]["agent"] == "codex"
    assert cli_payload["usage"]["artifact_manifest"]["source_refs"] == ["ctx_cli"]
    assert cli_output.exists()

    api_output = tmp_path / "api-artifacts.json"
    api = TestClient(create_app())
    api_result = api.post(
        "/v1/tools/pdf.artifacts.manifest/run",
        json={
            "artifact_paths": [str(pdf_path), str(composition_path)],
            "output_path": str(api_output),
            "title": "API Artifact Manifest",
            "metadata": {"agent": "rest"},
        },
    )

    assert api_result.status_code == 200
    assert api_result.json()["tool"] == "pdf.artifacts.manifest"
    assert api_result.json()["usage"]["artifact_manifest"]["metadata"]["agent"] == "rest"
    assert api_output.exists()

    assert hasattr(mcp_server, "pdf_artifacts_manifest")
    mcp_output = tmp_path / "mcp-artifacts.json"
    mcp = json.loads(
        mcp_server.pdf_artifacts_manifest(
            [str(pdf_path), str(composition_path)],
            output_path=str(mcp_output),
            title="MCP Artifact Manifest",
            metadata={"agent": "mcp"},
        )
    )

    assert mcp["tool"] == "pdf.artifacts.manifest"
    assert mcp["usage"]["artifact_manifest"]["title"] == "MCP Artifact Manifest"
    assert mcp_output.exists()


def test_artifact_graph_builds_lineage_from_manifest(tmp_path: Path) -> None:
    pdf_path = tmp_path / "report-patched.pdf"
    composition_path = tmp_path / "report.composition.json"
    source_map_path = tmp_path / "report.source-map.json"
    citations_path = tmp_path / "report.citations.json"
    patch_path = tmp_path / "report.patch.json"
    manifest_path = tmp_path / "report.artifacts.json"
    graph_path = tmp_path / "report.artifact-graph.json"
    create_text_pdf("Artifact graphs make evidence lineage traversable.", pdf_path)
    composition_path.write_text(
        json.dumps(
            {
                "composition_id": "cmp_report",
                "blocks": [{"block_id": "blk_summary", "source_refs": ["ctx_text"]}],
            }
        ),
        encoding="utf-8",
    )
    source_map_path.write_text(
        json.dumps({"source_map": [{"block_id": "blk_summary", "source_ref": "ctx_text"}]}),
        encoding="utf-8",
    )
    citations_path.write_text(
        json.dumps({"citations": [{"claim_id": "claim_1", "source_refs": ["ctx_text"]}]}),
        encoding="utf-8",
    )
    patch_path.write_text(
        json.dumps({"patch_id": "patch_report", "operations": [{"op": "append_markdown", "source_refs": ["ctx_patch"]}]}),
        encoding="utf-8",
    )
    manifest = artifact_bundle.create_artifact_manifest(
        artifact_paths=[pdf_path, composition_path, source_map_path, citations_path, patch_path],
        output_path=manifest_path,
        title="Report Artifact Manifest",
        metadata={"workflow": "context-packet-patch"},
    ).usage["artifact_manifest"]

    assert hasattr(artifact_bundle, "build_artifact_graph")
    result = artifact_bundle.build_artifact_graph(
        artifact_manifest_path=manifest_path,
        output_path=graph_path,
        title="Report Artifact Graph",
    )

    assert result.status == "succeeded"
    assert result.tool == "pdf.artifacts.graph"
    assert result.artifacts[0].mime_type == "application/json"
    graph = result.usage["artifact_graph"]
    assert graph["artifact_graph_version"] == "0.1"
    assert graph["title"] == "Report Artifact Graph"
    assert graph["manifest_id"] == manifest["manifest_id"]
    assert graph["artifact_count"] == 5
    assert graph["source_ref_count"] == 2
    assert graph["node_count"] == len(graph["nodes"])
    assert graph["edge_count"] == len(graph["edges"])
    assert graph["source_ref_index"]["ctx_text"]["artifact_count"] == 3
    assert graph["source_ref_index"]["ctx_patch"]["artifact_count"] == 1
    relations = {edge["relation"] for edge in graph["edges"]}
    assert {"includes_artifact", "uses_source_ref", "derived_from_composition", "produces_pdf"} <= relations
    assert graph["safety"]["mutates_inputs"] is False
    assert graph["safety"]["lineage_inference"] == "local_manifest_conventions"
    saved = json.loads(graph_path.read_text(encoding="utf-8"))
    assert saved["artifact_graph_id"].startswith("artifact_graph_")
    assert result.next_recommended_tools == ["pdf.artifacts.export_bundle", "pdf.workflow.report"]


def test_artifact_graph_cli_api_and_mcp_are_exposed(tmp_path: Path) -> None:
    pdf_path = tmp_path / "report.pdf"
    composition_path = tmp_path / "report.composition.json"
    manifest_path = tmp_path / "report.artifacts.json"
    create_text_pdf("Artifact graph interfaces.", pdf_path)
    composition_path.write_text(
        json.dumps({"source_map": [{"source_ref": "ctx_cli"}]}),
        encoding="utf-8",
    )
    artifact_bundle.create_artifact_manifest(
        artifact_paths=[pdf_path, composition_path],
        output_path=manifest_path,
        title="Interface Artifact Manifest",
    )

    cli_output = tmp_path / "cli-artifact-graph.json"
    cli = runner.invoke(
        app,
        [
            "artifacts",
            "graph",
            "--manifest",
            str(manifest_path),
            "-o",
            str(cli_output),
            "--title",
            "CLI Artifact Graph",
            "--json",
        ],
    )

    assert cli.exit_code == 0
    cli_payload = json.loads(cli.stdout)
    assert cli_payload["tool"] == "pdf.artifacts.graph"
    assert cli_payload["usage"]["artifact_graph"]["title"] == "CLI Artifact Graph"
    assert cli_payload["usage"]["artifact_graph"]["source_ref_index"]["ctx_cli"]["artifact_count"] == 1
    assert cli_output.exists()

    api_output = tmp_path / "api-artifact-graph.json"
    api = TestClient(create_app())
    api_result = api.post(
        "/v1/tools/pdf.artifacts.graph/run",
        json={
            "artifact_manifest_path": str(manifest_path),
            "output_path": str(api_output),
            "title": "API Artifact Graph",
        },
    )

    assert api_result.status_code == 200
    assert api_result.json()["tool"] == "pdf.artifacts.graph"
    assert api_result.json()["usage"]["artifact_graph"]["title"] == "API Artifact Graph"
    assert api_output.exists()

    assert hasattr(mcp_server, "pdf_artifacts_graph")
    mcp_output = tmp_path / "mcp-artifact-graph.json"
    mcp = json.loads(
        mcp_server.pdf_artifacts_graph(
            artifact_manifest_path=str(manifest_path),
            output_path=str(mcp_output),
            title="MCP Artifact Graph",
        )
    )

    assert mcp["tool"] == "pdf.artifacts.graph"
    assert mcp["usage"]["artifact_graph"]["title"] == "MCP Artifact Graph"
    assert mcp_output.exists()


def test_artifact_source_map_indexes_blocks_pages_sources_and_artifacts(tmp_path: Path) -> None:
    pdf_path = tmp_path / "report.pdf"
    composition_path = tmp_path / "report.composition.json"
    context_packet_path = tmp_path / "context.packet.json"
    manifest_path = tmp_path / "report.artifacts.json"
    output_path = tmp_path / "report.artifact-source-map.json"
    create_text_pdf("Artifact source maps preserve block-to-source evidence.", pdf_path)
    composition_path.write_text(
        json.dumps(
            {
                "composition_ir": {
                    "composition_id": "cmp_report",
                    "blocks": [
                        {
                            "block_id": "blk_summary",
                            "type": "section",
                            "title": "Summary",
                            "target_slot": "executive_summary",
                            "source_refs": ["ctx_text"],
                        },
                        {
                            "block_id": "blk_metrics",
                            "type": "table",
                            "title": "Metrics",
                            "target_slot": "findings",
                            "source_refs": ["ctx_table"],
                        },
                    ],
                },
                "source_map": [
                    {
                        "block_id": "blk_summary",
                        "block_type": "section",
                        "target_slot": "executive_summary",
                        "source_ref": "ctx_text",
                        "page_number": 1,
                        "bbox": [72, 640, 520, 720],
                    },
                    {
                        "block_id": "blk_metrics",
                        "block_type": "table",
                        "target_slot": "findings",
                        "source_ref": "ctx_table",
                        "page_number": 1,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    context_packet_path.write_text(
        json.dumps(
            {
                "context_packet_version": "0.1",
                "context_packet_id": "ctxpkt_report",
                "items": [
                    {
                        "context_item_id": "ctx_001",
                        "source_ref": "ctx_text",
                        "type": "text",
                        "role": "brief",
                        "label": "Audit Brief",
                        "metadata": {"preview": "Audit brief evidence."},
                    },
                    {
                        "context_item_id": "ctx_002",
                        "source_ref": "ctx_table",
                        "type": "data",
                        "role": "data_evidence",
                        "label": "Runtime Metrics",
                        "metadata": {"preview": "Runtime metrics.", "row_count": 2, "column_count": 2},
                    },
                ],
                "source_graph": {"source_graph_id": "srcgraph_report", "nodes": [], "edges": []},
            }
        ),
        encoding="utf-8",
    )
    manifest = artifact_bundle.create_artifact_manifest(
        artifact_paths=[pdf_path, composition_path],
        output_path=manifest_path,
        title="Report Artifacts",
    ).usage["artifact_manifest"]

    assert hasattr(artifact_bundle, "build_artifact_source_map")
    result = artifact_bundle.build_artifact_source_map(
        composition_path=composition_path,
        context_packet_path=context_packet_path,
        artifact_manifest_path=manifest_path,
        output_path=output_path,
        title="Report Artifact Source Map",
    )

    assert result.status == "succeeded"
    assert result.tool == "pdf.artifacts.source_map"
    assert result.artifacts[0].mime_type == "application/json"
    report = result.usage["artifact_source_map"]
    assert report["artifact_source_map_version"] == "0.1"
    assert report["title"] == "Report Artifact Source Map"
    assert report["composition_id"] == "cmp_report"
    assert report["context_packet_id"] == "ctxpkt_report"
    assert report["artifact_manifest_id"] == manifest["manifest_id"]
    assert report["generated_artifacts"][0]["path"] == pdf_path.resolve().as_posix()
    assert report["block_index"]["blk_summary"]["source_refs"] == ["ctx_text"]
    assert report["block_index"]["blk_summary"]["page_refs"][0]["bbox"] == [72, 640, 520, 720]
    assert report["source_ref_index"]["ctx_text"]["mapping_count"] == 1
    assert report["source_ref_index"]["ctx_text"]["source_match_status"] == "matched"
    assert report["page_index"]["1"]["block_ids"] == ["blk_metrics", "blk_summary"]
    assert report["coverage"]["source_ref_match_ratio"] == 1.0
    assert report["safety"]["mutates_inputs"] is False
    saved = json.loads(output_path.read_text(encoding="utf-8"))
    assert saved["artifact_source_map_id"].startswith("artifact_srcmap_")
    assert result.next_recommended_tools == ["pdf.artifacts.graph", "pdf.artifacts.export_bundle", "pdf.patch.plan"]


def test_artifact_source_map_cli_api_and_mcp_are_exposed(tmp_path: Path) -> None:
    composition_path = tmp_path / "report.composition.json"
    context_packet_path = tmp_path / "context.packet.json"
    composition_path.write_text(
        json.dumps(
            {
                "composition_ir": {
                    "composition_id": "cmp_cli",
                    "blocks": [{"block_id": "blk_cli", "type": "section", "source_refs": ["ctx_cli"]}],
                },
                "source_map": [{"block_id": "blk_cli", "source_ref": "ctx_cli", "page_number": 1}],
            }
        ),
        encoding="utf-8",
    )
    context_packet_path.write_text(
        json.dumps(
            {
                "context_packet_id": "ctxpkt_cli",
                "items": [{"context_item_id": "ctx_001", "source_ref": "ctx_cli", "type": "text"}],
            }
        ),
        encoding="utf-8",
    )

    cli_output = tmp_path / "cli-artifact-source-map.json"
    cli = runner.invoke(
        app,
        [
            "artifacts",
            "source-map",
            "--composition",
            str(composition_path),
            "--context-packet",
            str(context_packet_path),
            "-o",
            str(cli_output),
            "--title",
            "CLI Artifact Source Map",
            "--json",
        ],
    )

    assert cli.exit_code == 0
    cli_payload = json.loads(cli.stdout)
    assert cli_payload["tool"] == "pdf.artifacts.source_map"
    assert cli_payload["usage"]["artifact_source_map"]["title"] == "CLI Artifact Source Map"
    assert cli_payload["usage"]["artifact_source_map"]["source_ref_index"]["ctx_cli"]["mapping_count"] == 1
    assert cli_output.exists()

    api_output = tmp_path / "api-artifact-source-map.json"
    api = TestClient(create_app())
    api_result = api.post(
        "/v1/tools/pdf.artifacts.source_map/run",
        json={
            "composition_path": str(composition_path),
            "context_packet_path": str(context_packet_path),
            "output_path": str(api_output),
            "title": "API Artifact Source Map",
        },
    )

    assert api_result.status_code == 200
    assert api_result.json()["tool"] == "pdf.artifacts.source_map"
    assert api_result.json()["usage"]["artifact_source_map"]["title"] == "API Artifact Source Map"
    assert api_output.exists()

    assert hasattr(mcp_server, "pdf_artifacts_source_map")
    mcp_output = tmp_path / "mcp-artifact-source-map.json"
    mcp = json.loads(
        mcp_server.pdf_artifacts_source_map(
            composition_path=str(composition_path),
            context_packet_path=str(context_packet_path),
            output_path=str(mcp_output),
            title="MCP Artifact Source Map",
        )
    )

    assert mcp["tool"] == "pdf.artifacts.source_map"
    assert mcp["usage"]["artifact_source_map"]["title"] == "MCP Artifact Source Map"
    assert mcp_output.exists()


def test_export_artifact_bundle_writes_zip_manifest_and_checksums(tmp_path: Path) -> None:
    pdf_path = tmp_path / "report.pdf"
    composition_path = tmp_path / "report.composition.json"
    coverage_path = tmp_path / "report.coverage.json"
    output_path = tmp_path / "report.agentpdf-bundle.zip"
    create_text_pdf("AgentPDF bundle evidence.", pdf_path)
    composition_path.write_text(json.dumps({"composition_ir": {"blocks": []}, "source_map": []}), encoding="utf-8")
    coverage_path.write_text(json.dumps({"coverage": {"coverage_ratio": 1.0}}), encoding="utf-8")

    result = export_artifact_bundle(
        artifact_paths=[pdf_path, composition_path, coverage_path],
        output_path=output_path,
        title="Report Audit Bundle",
        metadata={"workflow": "template-pack-to-patch"},
    )

    assert result.status == "succeeded"
    assert result.tool == "pdf.artifacts.export_bundle"
    assert result.artifacts[0].path == output_path.resolve()
    assert result.usage["bundle_manifest"]["title"] == "Report Audit Bundle"
    assert result.usage["bundle_manifest"]["metadata"]["workflow"] == "template-pack-to-patch"
    assert result.usage["file_count"] == 3
    assert output_path.exists()

    with ZipFile(output_path) as archive:
        names = set(archive.namelist())
        assert "agentpdf-bundle-manifest.json" in names
        assert "checksums.sha256" in names
        assert "artifacts/report.pdf" in names
        assert "artifacts/report.composition.json" in names
        manifest = json.loads(archive.read("agentpdf-bundle-manifest.json"))
        checksums = archive.read("checksums.sha256").decode("utf-8")

    assert manifest["bundle_version"] == "0.1"
    assert manifest["artifact_count"] == 3
    assert manifest["artifacts"][0]["bundle_path"] == "artifacts/report.pdf"
    assert "report.composition.json" in checksums
    schema = json.loads(Path("schemas/artifact-bundle-manifest.schema.json").read_text(encoding="utf-8"))
    assert list(Draft202012Validator(schema).iter_errors(manifest)) == []
    assert result.next_recommended_tools == ["pdf.workflow.report", "pdf.validation.validate_output"]


def test_verify_artifact_bundle_reports_manifest_and_checksum_status(tmp_path: Path) -> None:
    pdf_path = tmp_path / "report.pdf"
    composition_path = tmp_path / "report.composition.json"
    bundle_path = tmp_path / "report.agentpdf-bundle.zip"
    create_text_pdf("AgentPDF bundle verification.", pdf_path)
    composition_path.write_text(json.dumps({"composition_id": "cmp_demo", "blocks": []}), encoding="utf-8")
    export_artifact_bundle(
        artifact_paths=[pdf_path, composition_path],
        output_path=bundle_path,
        title="Verified Bundle",
        metadata={"workflow": "create-agent"},
    )

    assert hasattr(artifact_bundle, "verify_artifact_bundle")
    result = artifact_bundle.verify_artifact_bundle(bundle_path)

    assert result.status == "succeeded"
    assert result.tool == "pdf.artifacts.verify_bundle"
    assert result.validation is not None
    assert result.validation.status == "passed"
    assert result.usage["bundle_verification"]["manifest"]["title"] == "Verified Bundle"
    assert result.usage["bundle_verification"]["artifact_count"] == 2
    assert result.usage["bundle_verification"]["verified_artifact_count"] == 2
    assert result.usage["bundle_verification"]["checksum_mismatches"] == []
    assert result.next_recommended_tools == ["pdf.workflow.report", "pdf.inspect.document"]

    tampered_path = tmp_path / "report.tampered.agentpdf-bundle.zip"
    with ZipFile(bundle_path) as source, ZipFile(tampered_path, mode="w", compression=ZIP_DEFLATED) as target:
        for entry in source.infolist():
            payload = source.read(entry.filename)
            if entry.filename == "artifacts/report.composition.json":
                payload = json.dumps({"tampered": True}).encode("utf-8")
            target.writestr(entry, payload)

    tampered = artifact_bundle.verify_artifact_bundle(tampered_path)

    assert tampered.status == "failed"
    assert tampered.validation is not None
    assert tampered.validation.status == "failed"
    assert tampered.usage["bundle_verification"]["checksum_mismatches"] == [
        "artifacts/report.composition.json"
    ]
    assert "artifacts/report.composition.json" in tampered.warnings[0]


def test_export_artifact_bundle_cli_api_and_mcp_are_exposed(tmp_path: Path) -> None:
    pdf_path = tmp_path / "report.pdf"
    manifest_path = tmp_path / "patch.json"
    create_text_pdf("Bundle interfaces.", pdf_path)
    manifest_path.write_text(json.dumps({"patch_id": "patch_demo", "operations": []}), encoding="utf-8")

    cli_output = tmp_path / "cli-bundle.zip"
    cli = runner.invoke(
        app,
        [
            "artifacts",
            "export-bundle",
            "--file",
            str(pdf_path),
            "--file",
            str(manifest_path),
            "-o",
            str(cli_output),
            "--title",
            "CLI Bundle",
            "--metadata",
            "agent=codex",
            "--json",
        ],
    )

    assert cli.exit_code == 0
    cli_payload = json.loads(cli.stdout)
    assert cli_payload["tool"] == "pdf.artifacts.export_bundle"
    assert cli_payload["usage"]["bundle_manifest"]["metadata"]["agent"] == "codex"
    assert cli_output.exists()

    api_output = tmp_path / "api-bundle.zip"
    api = TestClient(create_app())
    api_result = api.post(
        "/v1/tools/pdf.artifacts.export_bundle/run",
        json={
            "artifact_paths": [str(pdf_path), str(manifest_path)],
            "output_path": str(api_output),
            "title": "API Bundle",
            "metadata": {"agent": "rest"},
        },
    )

    assert api_result.status_code == 200
    assert api_result.json()["tool"] == "pdf.artifacts.export_bundle"
    assert api_result.json()["usage"]["bundle_manifest"]["metadata"]["agent"] == "rest"
    assert api_output.exists()

    mcp_output = tmp_path / "mcp-bundle.zip"
    mcp = json.loads(
        pdf_artifacts_export_bundle(
            [str(pdf_path), str(manifest_path)],
            str(mcp_output),
            title="MCP Bundle",
            metadata={"agent": "claude-code"},
        )
    )

    assert mcp["tool"] == "pdf.artifacts.export_bundle"
    assert mcp["usage"]["bundle_manifest"]["title"] == "MCP Bundle"
    assert mcp_output.exists()

    cli_verify = runner.invoke(
        app,
        [
            "artifacts",
            "verify-bundle",
            str(cli_output),
            "--json",
        ],
    )

    assert cli_verify.exit_code == 0
    cli_verify_payload = json.loads(cli_verify.stdout)
    assert cli_verify_payload["tool"] == "pdf.artifacts.verify_bundle"
    assert cli_verify_payload["validation"]["status"] == "passed"

    api_verify = api.post(
        "/v1/tools/pdf.artifacts.verify_bundle/run",
        json={"bundle_path": str(api_output)},
    )

    assert api_verify.status_code == 200
    assert api_verify.json()["tool"] == "pdf.artifacts.verify_bundle"
    assert api_verify.json()["validation"]["status"] == "passed"

    assert hasattr(mcp_server, "pdf_artifacts_verify_bundle")
    mcp_verify = json.loads(mcp_server.pdf_artifacts_verify_bundle(str(mcp_output)))

    assert mcp_verify["tool"] == "pdf.artifacts.verify_bundle"
    assert mcp_verify["validation"]["status"] == "passed"
