import json
from pathlib import Path

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
    assert [step["tool"] for step in usage["steps"]] == [
        "pdf.create.html_package",
        "pdf.render.html_package",
        "pdf.qa.visual_report",
        "pdf.artifacts.manifest",
        "pdf.artifacts.graph",
    ]

    qa_report = json.loads(Path(usage["qa_report_path"]).read_text(encoding="utf-8"))
    artifact_manifest = json.loads(Path(usage["artifact_manifest_path"]).read_text(encoding="utf-8"))
    artifact_graph = json.loads(Path(usage["artifact_graph_path"]).read_text(encoding="utf-8"))

    assert qa_report["tool"] == "pdf.qa.visual_report"
    assert artifact_manifest["html_package_count"] == 1
    assert any(edge["relation"] == "renders_to_pdf" for edge in artifact_graph["edges"])
