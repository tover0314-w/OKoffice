from pathlib import Path

from reportlab.pdfgen import canvas

from okoffice.workflows.planner import plan_workflow
from okoffice.workflows.runner import run_workflow


def test_workflow_run_executes_local_agent_steps_with_evidence(tmp_path: Path) -> None:
    source = tmp_path / "agent.pdf"
    index = tmp_path / "agent.index.json"
    _write_text_pdf(source, "Local workflow run gives agents cited document evidence.")
    workflow = {
        "steps": [
            {
                "step_id": "inspect",
                "tool": "pdf.inspect.document",
                "input": {"path": str(source)},
            },
            {
                "step_id": "parse",
                "tool": "pdf.ai.parse.lite",
                "input": {"input_path": str(source)},
            },
            {
                "step_id": "index",
                "tool": "pdf.ai.rag.ingest",
                "input": {"input_path": str(source), "index_path": str(index), "max_chars": 80},
            },
            {
                "step_id": "query",
                "tool": "pdf.ai.rag.query",
                "input": {"index_path": str(index), "query": "What gives cited evidence?"},
            },
            {
                "step_id": "cite",
                "tool": "pdf.ai.rag.cite_answer",
                "input": {
                    "index_path": str(index),
                    "answer": "Local workflow run gives agents cited document evidence.",
                },
            },
        ]
    }

    result = run_workflow(workflow)

    assert result.status == "succeeded"
    assert result.tool == "pdf.workflow.run"
    run = result.usage["workflow_run"]
    assert run["run_id"].startswith("wfrun_")
    assert run["status"] == "succeeded"
    assert run["executed_steps"] == 5
    assert run["failed_steps"] == 0
    assert [step["tool"] for step in run["step_results"]] == [
        "pdf.inspect.document",
        "pdf.ai.parse.lite",
        "pdf.ai.rag.ingest",
        "pdf.ai.rag.query",
        "pdf.ai.rag.cite_answer",
    ]
    assert all(step["status"] == "succeeded" for step in run["step_results"])
    assert run["step_results"][2]["artifact_ids"]
    assert index.exists()


def test_workflow_run_executes_planner_output_with_runtime_bindings(tmp_path: Path) -> None:
    source = tmp_path / "planned.pdf"
    _write_text_pdf(source, "Planner workflow gives agents cited document evidence.")
    planned = plan_workflow(
        goal="Chat with this PDF and cite the answer.",
        input_path=str(source),
    )
    workflow = planned.usage["workflow"]
    workflow["artifact_dir"] = str(tmp_path / "workflow-artifacts")
    workflow["bindings"] = {
        "<question>": "What gives cited evidence?",
        "<answer>": "Planner workflow gives agents cited document evidence.",
    }

    result = run_workflow(workflow)

    assert result.status == "succeeded"
    run = result.usage["workflow_run"]
    assert run["executed_steps"] == len(workflow["steps"])
    assert run["failed_steps"] == 0
    assert Path(run["bindings"]["<final.pdf>"]).exists()
    assert run["bindings"]["<final.pdf>"] != str(source)
    assert Path(run["bindings"]["<output.index.json>"]).exists()
    assert Path(run["bindings"]["<highlighted.pdf>"]).exists()
    index_step = next(step for step in run["step_results"] if step["step_id"] == "index")
    query_step = next(step for step in run["step_results"] if step["step_id"] == "answer")
    assert index_step["input"]["index_path"] == run["bindings"]["<output.index.json>"]
    assert query_step["input"]["query"] == "What gives cited evidence?"
    assert all("<" not in str(step["input"]) for step in run["step_results"])


def test_workflow_run_rejects_unresolved_placeholders_before_execution() -> None:
    result = run_workflow(
        {
            "steps": [
                {
                    "step_id": "validate",
                    "tool": "pdf.validation.validate_output",
                    "input": {"path": "<final.pdf>"},
                }
            ]
        }
    )

    assert result.status == "failed"
    assert result.tool == "pdf.workflow.run"
    assert result.error is not None
    assert result.error.code == "unsafe_input_rejected"
    run = result.usage["workflow_run"]
    assert run["executed_steps"] == 0
    assert run["failed_steps"] == 1
    assert run["step_results"][0]["status"] == "failed"


def test_workflow_run_rejects_bad_authoring_qa_expected_page_count() -> None:
    result = run_workflow(
        {
            "steps": [
                {
                    "step_id": "visual_qa",
                    "tool": "pdf.qa.visual_report",
                    "input": {
                        "input_path": "deck.pdf",
                        "expected_page_count": "abc",
                    },
                }
            ]
        }
    )

    assert result.status == "failed"
    assert result.tool == "pdf.workflow.run"
    assert result.error is not None
    assert result.error.code == "unsafe_input_rejected"
    run = result.usage["workflow_run"]
    assert run["executed_steps"] == 1
    assert run["failed_steps"] == 1
    assert run["step_results"][0]["error"]["code"] == "unsafe_input_rejected"


def test_workflow_run_dry_run_reports_supported_steps_without_running_files() -> None:
    result = run_workflow(
        {
            "steps": [
                {
                    "step_id": "inspect",
                    "tool": "pdf.inspect.document",
                    "input": {"path": "<input.pdf>"},
                }
            ]
        },
        dry_run=True,
    )

    assert result.status == "succeeded"
    run = result.usage["workflow_run"]
    assert run["dry_run"] is True
    assert run["executed_steps"] == 0
    assert run["planned_steps"] == 1
    assert run["step_results"][0]["status"] == "planned"


def _write_text_pdf(path: Path, text: str) -> None:
    document = canvas.Canvas(str(path))
    document.drawString(72, 720, text)
    document.save()
