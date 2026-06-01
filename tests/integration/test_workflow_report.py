from pathlib import Path

from reportlab.pdfgen import canvas

from agentpdf.workflows.reporter import create_workflow_report
from agentpdf.workflows.runner import run_workflow


def test_workflow_report_summarizes_run_result_and_writes_markdown(
    tmp_path: Path,
) -> None:
    source = tmp_path / "report-source.pdf"
    index = tmp_path / "report.index.json"
    output = tmp_path / "workflow-report.md"
    _write_text_pdf(source, "Workflow report gives agents audit evidence.")
    run_result = run_workflow(
        {
            "steps": [
                {
                    "step_id": "inspect",
                    "tool": "pdf.inspect.document",
                    "input": {"path": str(source)},
                },
                {
                    "step_id": "index",
                    "tool": "pdf.ai.rag.ingest",
                    "input": {"input_path": str(source), "index_path": str(index)},
                },
            ]
        }
    )

    result = create_workflow_report(
        run_result.model_dump(mode="json"),
        output_path=output,
    )

    assert result.status == "succeeded"
    assert result.tool == "pdf.workflow.report"
    assert output.exists()
    assert result.artifacts[0].path == output.resolve()
    report = result.usage["workflow_report"]
    assert report["run_id"] == run_result.usage["workflow_run"]["run_id"]
    assert report["run_status"] == "succeeded"
    assert report["planned_steps"] == 2
    assert report["executed_steps"] == 2
    assert report["failed_steps"] == 0
    assert report["artifact_count"] == 1
    assert report["tools"] == ["pdf.inspect.document", "pdf.ai.rag.ingest"]
    assert report["markdown"].startswith("# AgentPDF Workflow Report")
    assert "pdf.ai.rag.ingest" in report["markdown"]
    assert "output.index.json" not in report["markdown"]


def test_workflow_report_accepts_raw_workflow_run_payload() -> None:
    result = create_workflow_report(
        {
            "run_id": "wfrun_raw",
            "status": "failed",
            "planned_steps": 2,
            "executed_steps": 1,
            "failed_steps": 1,
            "bindings": {"<final.pdf>": "input.pdf"},
            "step_results": [
                {
                    "step_id": "inspect",
                    "tool": "pdf.inspect.document",
                    "status": "succeeded",
                    "warnings": [],
                    "artifact_ids": [],
                },
                {
                    "step_id": "validate",
                    "tool": "pdf.validation.validate_output",
                    "status": "failed",
                    "warnings": ["Output was not parseable."],
                    "artifact_ids": [],
                },
            ],
        }
    )

    report = result.usage["workflow_report"]
    assert result.status == "succeeded"
    assert report["run_status"] == "failed"
    assert report["failed_step_ids"] == ["validate"]
    assert report["warnings"] == ["Output was not parseable."]
    assert "validate" in report["markdown"]


def _write_text_pdf(path: Path, text: str) -> None:
    document = canvas.Canvas(str(path))
    document.drawString(72, 720, text)
    document.save()
