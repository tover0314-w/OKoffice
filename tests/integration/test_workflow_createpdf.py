import json
from pathlib import Path
from zipfile import ZipFile

from agentpdf.context.packet import build_context_packet
from agentpdf.tools.runner import run_workflow_createpdf


def test_workflow_createpdf_generates_validated_audited_html_first_pdf(tmp_path: Path) -> None:
    html_path = tmp_path / "createpdf.html"
    pdf_path = tmp_path / "createpdf.pdf"
    artifact_dir = tmp_path / "audit"

    result = run_workflow_createpdf(
        html="<main><h1>CreatePDF</h1><p>HTML-first workflow with audit evidence.</p></main>",
        html_output_path=html_path,
        pdf_output_path=pdf_path,
        title="CreatePDF",
        artifact_dir=artifact_dir,
        renderer_backend="local_html_package_fallback",
    )

    assert result.status == "succeeded"
    assert result.tool == "pdf.workflow.createpdf"
    assert pdf_path.exists()
    assert html_path.exists()

    usage = result.usage["createpdf"]
    assert usage["html_package_manifest_path"] == str(html_path.with_suffix(".html-manifest.json").resolve())
    assert usage["pdf_output_path"] == str(pdf_path.resolve())
    assert usage["qa_report_path"] == str((artifact_dir / "createpdf.qa.json").resolve())
    assert usage["artifact_manifest_path"] == str((artifact_dir / "createpdf.artifact-manifest.json").resolve())
    assert usage["artifact_graph_path"] == str((artifact_dir / "createpdf.artifact-graph.json").resolve())
    assert usage["html_render_profile_count"] == 1
    assert usage["html_render_profile_refs"][0]["render_profile_id"] == "browser_print_a4_v0"
    assert usage["html_render_profile_refs"][0]["page_size"] == "A4"
    assert usage["artifact_graph_summary"]["html_render_profile_count"] == 1
    assert usage["artifact_manifest_summary"]["renderer_backend_count"] == 1
    assert usage["artifact_graph_summary"]["renderer_backend_count"] == 1
    assert usage["requested_renderer_backend"] == "local_html_package_fallback"
    assert usage["renderer_backend"]["backend_id"] == "local_html_package_fallback"
    assert usage["renderer_backend"]["fallback_reason"] == "browser_renderer_worker_unavailable"
    assert usage["render_skipped"] is False
    assert [step["tool"] for step in usage["steps"]] == [
        "pdf.create.html_package",
        "pdf.render.html_package",
        "pdf.qa.visual_report",
        "pdf.artifacts.manifest",
        "pdf.artifacts.graph",
    ]
    assert usage["steps"][1]["renderer_backend_id"] == "local_html_package_fallback"
    assert usage["steps"][1]["render_skipped"] is False

    qa_report = json.loads(Path(usage["qa_report_path"]).read_text(encoding="utf-8"))
    artifact_manifest = json.loads(Path(usage["artifact_manifest_path"]).read_text(encoding="utf-8"))
    artifact_graph = json.loads(Path(usage["artifact_graph_path"]).read_text(encoding="utf-8"))

    assert qa_report["tool"] == "pdf.qa.visual_report"
    assert artifact_manifest["html_package_count"] == 1
    assert any(edge["relation"] == "renders_to_pdf" for edge in artifact_graph["edges"])


def test_workflow_createpdf_reports_requested_browser_backend_when_unavailable(tmp_path: Path) -> None:
    html_path = tmp_path / "browser-createpdf.html"
    pdf_path = tmp_path / "browser-createpdf.pdf"

    result = run_workflow_createpdf(
        html="<main><h1>CreatePDF Browser Backend</h1><p>Request browser renderer.</p></main>",
        html_output_path=html_path,
        pdf_output_path=pdf_path,
        title="Browser CreatePDF",
        artifact_dir=tmp_path / "audit",
        renderer_backend="browser_chromium",
    )

    assert result.status == "failed"
    assert result.error is not None
    assert result.error.code == "dependency_missing"
    assert html_path.exists()
    assert not pdf_path.exists()
    usage = result.usage["createpdf"]
    assert usage["failed_tool"] == "pdf.render.html_package"
    assert usage["requested_renderer_backend"] == "browser_chromium"
    assert usage["renderer_backend"]["backend_id"] == "browser_chromium"
    assert usage["renderer_backend"]["available"] is False
    assert usage["render_skipped"] is True
    assert usage["render_skip_reason"] == "renderer_backend_unavailable"
    assert [step["tool"] for step in usage["steps"]] == [
        "pdf.create.html_package",
        "pdf.render.html_package",
    ]
    assert usage["steps"][1]["renderer_backend_id"] == "browser_chromium"
    assert usage["steps"][1]["render_skipped"] is True


def test_workflow_createpdf_accepts_context_packet_and_target_profile(tmp_path: Path) -> None:
    code_path = tmp_path / "service.py"
    code_path.write_text("def risky_total(items):\n    return sum(items)\n", encoding="utf-8")
    data_path = tmp_path / "metrics.csv"
    data_path.write_text("metric,value\nlatency_ms,42\n", encoding="utf-8")
    packet_path = tmp_path / "context.packet.json"
    packet = build_context_packet(
        [
            {"text": "Create a technical audit from local context.", "role": "brief"},
            {"path": str(code_path), "role": "code_evidence", "label": "Service Code"},
            {"path": str(data_path), "role": "data_evidence", "label": "Runtime Metrics"},
            {"uri": "https://example.com/source", "role": "source", "label": "External Source"},
        ],
        output_path=packet_path,
        title="CreatePDF Context",
    ).usage["context_packet"]
    html_path = tmp_path / "context-createpdf.html"
    pdf_path = tmp_path / "context-createpdf.pdf"
    artifact_dir = tmp_path / "context-audit"

    result = run_workflow_createpdf(
        context_packet_path=packet_path,
        target_profile="technical_audit",
        html_output_path=html_path,
        pdf_output_path=pdf_path,
        title="Context CreatePDF",
        artifact_dir=artifact_dir,
        renderer_backend="local_html_package_fallback",
    )

    assert result.status == "succeeded"
    assert pdf_path.exists()
    assert html_path.exists()
    usage = result.usage["createpdf"]
    assert usage["source_format"] == "context_packet"
    assert usage["context_packet_id"] == packet["context_packet_id"]
    assert usage["target_profile"]["profile_id"] == "technical_audit"
    assert usage["composition_path"] == str(pdf_path.with_suffix(".composition.json").resolve())
    assert usage["html_render_profile_count"] == 1
    assert usage["html_render_profile_refs"][0]["render_profile_id"] == "browser_print_a4_v0"
    assert usage["artifact_graph_summary"]["html_render_profile_count"] == 1
    assert usage["requested_renderer_backend"] == "local_html_package_fallback"
    assert usage["renderer_backend"]["backend_id"] == "local_html_package_fallback"
    assert usage["renderer_backend"]["fallback"] is True
    assert usage["render_skipped"] is False
    assert [step["tool"] for step in usage["steps"]] == [
        "pdf.compose.from_context",
        "pdf.qa.visual_report",
        "pdf.artifacts.manifest",
        "pdf.artifacts.graph",
    ]
    assert usage["steps"][0]["renderer_backend_id"] == "local_html_package_fallback"

    artifact_manifest = json.loads(Path(usage["artifact_manifest_path"]).read_text(encoding="utf-8"))
    artifact_graph = json.loads(Path(usage["artifact_graph_path"]).read_text(encoding="utf-8"))
    assert artifact_manifest["context_packet_count"] == 1
    assert artifact_manifest["html_package_count"] == 1
    assert {"ctx_001", "ctx_002", "ctx_003", "ctx_004"} <= set(artifact_manifest["source_refs"])
    relations = {edge["relation"] for edge in artifact_graph["edges"]}
    assert {"renders_to_pdf", "uses_source_ref"} <= relations


def test_workflow_createpdf_materializes_inline_context_packet_for_audit(tmp_path: Path) -> None:
    packet = build_context_packet(
        [
            {
                "text": "Create an audited PDF from an inline packet.",
                "role": "brief",
                "label": "Inline Brief",
            },
            {
                "table": {
                    "columns": ["risk", "status"],
                    "rows": [["lineage", "required"]],
                },
                "role": "data_evidence",
                "label": "Audit Matrix",
            },
        ],
        title="Inline CreatePDF Context",
    ).usage["context_packet"]
    html_path = tmp_path / "inline-createpdf.html"
    pdf_path = tmp_path / "inline-createpdf.pdf"
    artifact_dir = tmp_path / "inline-audit"

    result = run_workflow_createpdf(
        context_packet=packet,
        target_profile="technical_audit",
        html_output_path=html_path,
        pdf_output_path=pdf_path,
        title="Inline Context CreatePDF",
        artifact_dir=artifact_dir,
    )

    assert result.status == "succeeded"
    usage = result.usage["createpdf"]
    context_packet_path = Path(usage["context_packet_path"])
    assert context_packet_path == (artifact_dir / "inline-createpdf.context.packet.json").resolve()
    assert context_packet_path.exists()
    materialized_packet = json.loads(context_packet_path.read_text(encoding="utf-8"))
    assert materialized_packet["context_packet_id"] == packet["context_packet_id"]
    assert materialized_packet["items"][1]["metadata"]["table_evidence"]["row_count"] == 1

    artifact_manifest = json.loads(Path(usage["artifact_manifest_path"]).read_text(encoding="utf-8"))
    artifact_graph = json.loads(Path(usage["artifact_graph_path"]).read_text(encoding="utf-8"))

    assert artifact_manifest["context_packet_refs"] == [
        {
            "context_packet_id": packet["context_packet_id"],
            "path": context_packet_path.as_posix(),
            "source_graph_id": packet["source_graph"]["source_graph_id"],
            "item_count": 2,
            "source_ref_count": 2,
        }
    ]
    assert artifact_manifest["context_evidence_index"]["ctx_002"]["primary_evidence_kind"] == "table_evidence"
    assert artifact_graph["context_packet_refs"] == artifact_manifest["context_packet_refs"]
    assert artifact_graph["source_ref_index"]["ctx_002"]["context_packet_ids"] == [packet["context_packet_id"]]


def test_workflow_createpdf_exports_and_verifies_audit_bundle(tmp_path: Path) -> None:
    html_path = tmp_path / "bundle-createpdf.html"
    pdf_path = tmp_path / "bundle-createpdf.pdf"
    artifact_dir = tmp_path / "bundle-audit"
    bundle_path = tmp_path / "bundle-createpdf.agentpdf-bundle.zip"

    result = run_workflow_createpdf(
        html="<main><h1>Bundled CreatePDF</h1><p>Export and verify audit bundle.</p></main>",
        html_output_path=html_path,
        pdf_output_path=pdf_path,
        title="Bundled CreatePDF",
        artifact_dir=artifact_dir,
        bundle_output_path=bundle_path,
    )

    assert result.status == "succeeded"
    assert bundle_path.exists()
    usage = result.usage["createpdf"]
    assert usage["bundle_path"] == str(bundle_path.resolve())
    assert usage["bundle_export"]["tool"] == "pdf.artifacts.export_bundle"
    assert usage["bundle_verification"]["tool"] == "pdf.artifacts.verify_bundle"
    assert usage["bundle_verification"]["validation"]["status"] == "passed"
    assert [step["tool"] for step in usage["steps"]][-2:] == [
        "pdf.artifacts.export_bundle",
        "pdf.artifacts.verify_bundle",
    ]

    with ZipFile(bundle_path) as archive:
        names = set(archive.namelist())

    assert "agentpdf-bundle-manifest.json" in names
    assert "checksums.sha256" in names
    assert "artifacts/bundle-createpdf.pdf" in names
    assert "artifacts/bundle-createpdf.artifact-manifest.json" in names
    assert "artifacts/bundle-createpdf.artifact-graph.json" in names


def test_workflow_createpdf_bundle_includes_materialized_context_packet(tmp_path: Path) -> None:
    audio_path = tmp_path / "meeting.mp3"
    audio_path.write_bytes(b"ID3 local audio fixture")
    transcript_path = tmp_path / "meeting.transcript.txt"
    transcript_path.write_text("00:00 Kickoff\n00:22 Decision evidence.", encoding="utf-8")
    packet = build_context_packet(
        [
            {
                "path": str(audio_path),
                "role": "audio_context",
                "label": "Meeting Audio",
                "transcript_path": str(transcript_path),
            }
        ],
        title="Bundled Context Packet",
    ).usage["context_packet"]
    html_path = tmp_path / "context-bundle.html"
    pdf_path = tmp_path / "context-bundle.pdf"
    artifact_dir = tmp_path / "context-bundle-audit"
    bundle_path = tmp_path / "context-bundle.agentpdf-bundle.zip"

    result = run_workflow_createpdf(
        context_packet=packet,
        target_profile="technical_audit",
        html_output_path=html_path,
        pdf_output_path=pdf_path,
        title="Bundled Context CreatePDF",
        artifact_dir=artifact_dir,
        bundle_output_path=bundle_path,
    )

    assert result.status == "succeeded"
    usage = result.usage["createpdf"]
    materialized_packet_path = Path(usage["context_packet_path"])
    assert materialized_packet_path == (artifact_dir / "context-bundle.context.packet.json").resolve()

    with ZipFile(bundle_path) as archive:
        names = set(archive.namelist())
        archived_packet = json.loads(archive.read("artifacts/context-bundle.context.packet.json"))

    assert "artifacts/context-bundle.context.packet.json" in names
    assert archived_packet["context_packet_id"] == packet["context_packet_id"]
    assert archived_packet["source_graph"]["edges"][0]["relation"] == "provides_transcript_for"
