import json
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image
from pypdf import PdfReader
from typer.testing import CliRunner

from agentpdf.api.app import create_app
from agentpdf.cli.main import app
from agentpdf.compose.context import compose_from_context
from agentpdf.context.packet import build_context_packet
from agentpdf.core.pdf import inspect_pdf_pages
from agentpdf.evidence.coverage import create_coverage_report
from agentpdf.mcp.server import (
    pdf_evidence_coverage_report,
    pdf_patch_apply,
    pdf_patch_plan,
    pdf_patch_preview,
    pdf_patch_verify,
)
from agentpdf.patch.transaction import apply_patch_transaction, plan_patch_transaction, preview_patch_transaction, verify_patch_transaction


runner = CliRunner()


def test_evidence_coverage_report_reads_composition_artifact(tmp_path: Path) -> None:
    composition_path = _write_composed_pdf(tmp_path)[1]
    report_path = tmp_path / "coverage.json"

    result = create_coverage_report(composition_path, output_path=report_path)

    assert result.status == "succeeded"
    assert result.tool == "pdf.evidence.coverage_report"
    assert result.artifacts[0].mime_type == "application/json"
    assert result.usage["coverage"]["coverage_ratio"] == 1.0
    assert result.usage["covered_blocks"] >= 3
    assert result.usage["uncovered_blocks"] == []
    assert result.usage["source_ref_count"] == 2
    assert result.next_recommended_tools == ["pdf.patch.plan", "pdf.validation.validate_output"]
    saved = json.loads(report_path.read_text(encoding="utf-8"))
    assert saved["coverage"]["covered_context_items"] == 2
    assert saved["block_evidence"][0]["source_refs"]


def test_patch_transaction_appends_audited_markdown_without_mutating_input(tmp_path: Path) -> None:
    source_pdf, composition_path = _write_composed_pdf(tmp_path)
    original_pages = len(PdfReader(source_pdf).pages)
    manifest_path = tmp_path / "patch.json"
    preview_path = tmp_path / "patch-preview.json"
    patched_pdf = tmp_path / "patched.pdf"

    plan = plan_patch_transaction(
        input_path=source_pdf,
        operations=[
            {
                "op": "append_markdown",
                "title": "Reviewer Note",
                "markdown": "## Reviewer Note\n\nEvidence appendix added from local patch transaction.",
                "source_refs": ["ctx_001"],
            }
        ],
        output_path=manifest_path,
        composition_path=composition_path,
        reason="Add reviewer-facing evidence appendix.",
    )
    preview = preview_patch_transaction(manifest_path, output_path=preview_path)
    applied = apply_patch_transaction(manifest_path, output_path=patched_pdf)
    verified = verify_patch_transaction(manifest_path, patched_pdf)

    assert plan.status == "succeeded"
    assert plan.tool == "pdf.patch.plan"
    assert plan.usage["patch_manifest"]["operation_count"] == 1
    assert plan.usage["patch_manifest"]["composition_path"] == str(composition_path.resolve()).replace("\\", "/")
    assert manifest_path.exists()

    assert preview.status == "succeeded"
    assert preview.tool == "pdf.patch.preview"
    assert preview.usage["will_mutate_input"] is False
    assert preview.usage["operation_summary"][0]["op"] == "append_markdown"
    assert preview_path.exists()

    assert applied.status == "succeeded"
    assert applied.tool == "pdf.patch.apply"
    assert applied.validation is not None
    assert applied.validation.status == "passed"
    assert any(artifact.mime_type == "application/json" for artifact in applied.artifacts)
    assert len(PdfReader(source_pdf).pages) == original_pages
    assert len(PdfReader(patched_pdf).pages) > original_pages

    patched_text = "\n".join(page.extract_text() or "" for page in PdfReader(patched_pdf).pages)
    assert "Reviewer Note" in patched_text
    assert "Evidence appendix added" in patched_text

    assert verified.status == "succeeded"
    assert verified.tool == "pdf.patch.verify"
    assert verified.usage["verification"]["input_unchanged"] is True
    assert verified.usage["verification"]["page_count_delta"] > 0
    assert verified.validation is not None
    assert verified.validation.status == "passed"


def test_patch_transaction_appends_structured_blocks_without_mutating_input(tmp_path: Path) -> None:
    source_pdf, composition_path = _write_composed_pdf(tmp_path)
    original_pages = len(PdfReader(source_pdf).pages)
    image_path = tmp_path / "architecture.png"
    Image.new("RGB", (120, 80), color=(20, 100, 90)).save(image_path)
    manifest_path = tmp_path / "structured.patch.json"
    patched_pdf = tmp_path / "structured-patched.pdf"

    operations = [
        {
            "op": "append_code_block",
            "title": "Risky Function",
            "language": "python",
            "code": "def risky_total(items):\n    return sum(items)\n",
            "source_refs": ["ctx_001"],
        },
        {
            "op": "append_table",
            "title": "Runtime Metrics",
            "columns": ["metric", "value"],
            "rows": [["latency_ms", "42"], ["error_rate", "0.01"]],
            "source_refs": ["ctx_001"],
        },
        {
            "op": "append_image",
            "title": "Architecture Figure",
            "path": str(image_path),
            "caption": "Local visual evidence.",
            "source_refs": ["ctx_001"],
        },
        {
            "op": "append_slide",
            "title": "Slide Appendix",
            "body": ["Patch transactions can append slide-like pages."],
            "source_refs": ["ctx_001"],
        },
    ]

    plan = plan_patch_transaction(
        input_path=source_pdf,
        operations=operations,
        output_path=manifest_path,
        composition_path=composition_path,
        reason="Append structured evidence blocks.",
    )
    preview = preview_patch_transaction(manifest_path)
    applied = apply_patch_transaction(manifest_path, output_path=patched_pdf)
    verified = verify_patch_transaction(manifest_path, patched_pdf)

    manifest = plan.usage["patch_manifest"]
    assert manifest["operation_count"] == 4
    assert manifest["safety"]["supported_operations"] == [
        "append_markdown",
        "append_code_block",
        "append_table",
        "append_image",
        "append_slide",
    ]
    assert [item["op"] for item in preview.usage["operation_summary"]] == [
        "append_code_block",
        "append_table",
        "append_image",
        "append_slide",
    ]

    assert applied.status == "succeeded"
    assert applied.validation is not None
    assert applied.validation.status == "passed"
    assert len(PdfReader(source_pdf).pages) == original_pages
    assert len(PdfReader(patched_pdf).pages) > original_pages
    assert verified.usage["verification"]["input_unchanged"] is True
    assert verified.usage["verification"]["page_count_delta"] > 0

    patched_text = "\n".join(page.extract_text() or "" for page in PdfReader(patched_pdf).pages)
    assert "Risky Function" in patched_text
    assert "Runtime Metrics" in patched_text
    assert "latency_ms" in patched_text
    assert "Architecture Figure" in patched_text
    assert "Slide Appendix" in patched_text
    assert "Patch Evidence" in patched_text
    page_report = inspect_pdf_pages(patched_pdf, pages="all")
    assert sum(page["image_count"] for page in page_report["pages"]) >= 1


def test_evidence_and_patch_cli_api_mcp_are_exposed(tmp_path: Path) -> None:
    source_pdf, composition_path = _write_composed_pdf(tmp_path)
    operations_path = tmp_path / "operations.json"
    single_operation_path = tmp_path / "single-operation.json"
    operations = [
        {
            "op": "append_markdown",
            "title": "CLI Patch Note",
            "markdown": "## CLI Patch Note\n\nPatch applied through exposed agent interfaces.",
            "source_refs": ["ctx_001"],
        }
    ]
    operations_path.write_text(json.dumps(operations), encoding="utf-8")
    single_operation_path.write_text(json.dumps(operations[0]), encoding="utf-8")
    coverage_path = tmp_path / "coverage.json"
    patch_path = tmp_path / "patch.json"
    single_patch_path = tmp_path / "single-patch.json"
    preview_path = tmp_path / "patch-preview.json"
    patched_pdf = tmp_path / "patched.pdf"

    coverage_cli = runner.invoke(
        app,
        ["evidence", "coverage-report", str(composition_path), "-o", str(coverage_path), "--json"],
    )
    plan_cli = runner.invoke(
        app,
        [
            "patch",
            "plan",
            str(source_pdf),
            "--operations",
            str(operations_path),
            "-o",
            str(patch_path),
            "--composition",
            str(composition_path),
            "--json",
        ],
    )
    single_plan_cli = runner.invoke(
        app,
        [
            "patch",
            "plan",
            str(source_pdf),
            "--operations",
            str(single_operation_path),
            "-o",
            str(single_patch_path),
            "--composition",
            str(composition_path),
            "--json",
        ],
    )
    preview_cli = runner.invoke(app, ["patch", "preview", str(patch_path), "-o", str(preview_path), "--json"])
    apply_cli = runner.invoke(app, ["patch", "apply", str(patch_path), "-o", str(patched_pdf), "--json"])
    verify_cli = runner.invoke(app, ["patch", "verify", str(patch_path), str(patched_pdf), "--json"])

    assert coverage_cli.exit_code == 0
    assert json.loads(coverage_cli.stdout)["tool"] == "pdf.evidence.coverage_report"
    assert plan_cli.exit_code == 0
    assert json.loads(plan_cli.stdout)["tool"] == "pdf.patch.plan"
    assert single_plan_cli.exit_code == 0
    assert json.loads(single_plan_cli.stdout)["usage"]["patch_manifest"]["operation_count"] == 1
    assert preview_cli.exit_code == 0
    assert json.loads(preview_cli.stdout)["tool"] == "pdf.patch.preview"
    assert apply_cli.exit_code == 0
    assert json.loads(apply_cli.stdout)["validation"]["status"] == "passed"
    assert verify_cli.exit_code == 0
    assert json.loads(verify_cli.stdout)["usage"]["verification"]["input_unchanged"] is True

    client = TestClient(create_app())
    api_coverage = client.post(
        "/v1/tools/pdf.evidence.coverage_report/run",
        json={"composition_path": str(composition_path), "output_path": str(tmp_path / "api-coverage.json")},
    )
    api_plan = client.post(
        "/v1/tools/pdf.patch.plan/run",
        json={
            "input_path": str(source_pdf),
            "operations": operations,
            "output_path": str(tmp_path / "api-patch.json"),
            "composition_path": str(composition_path),
        },
    )

    assert api_coverage.status_code == 200
    assert api_coverage.json()["tool"] == "pdf.evidence.coverage_report"
    assert api_plan.status_code == 200
    assert api_plan.json()["tool"] == "pdf.patch.plan"

    mcp_coverage = json.loads(pdf_evidence_coverage_report(str(composition_path), str(tmp_path / "mcp-coverage.json")))
    mcp_plan = json.loads(pdf_patch_plan(str(source_pdf), operations, str(tmp_path / "mcp-patch.json")))
    mcp_preview = json.loads(pdf_patch_preview(str(tmp_path / "mcp-patch.json")))
    mcp_apply = json.loads(pdf_patch_apply(str(tmp_path / "mcp-patch.json"), str(tmp_path / "mcp-patched.pdf")))
    mcp_verify = json.loads(pdf_patch_verify(str(tmp_path / "mcp-patch.json"), str(tmp_path / "mcp-patched.pdf")))

    assert mcp_coverage["tool"] == "pdf.evidence.coverage_report"
    assert mcp_plan["tool"] == "pdf.patch.plan"
    assert mcp_preview["tool"] == "pdf.patch.preview"
    assert mcp_apply["validation"]["status"] == "passed"
    assert mcp_verify["tool"] == "pdf.patch.verify"


def _write_composed_pdf(tmp_path: Path) -> tuple[Path, Path]:
    note = tmp_path / "note.md"
    note.write_text("# Audit Note\n\nMargin pressure needs evidence.\n", encoding="utf-8")
    packet = build_context_packet(
        [
            {"text": "Create an audit PDF with a reviewer appendix.", "role": "brief"},
            {"path": str(note), "role": "source_document"},
        ],
        output_path=tmp_path / "context.packet.json",
        title="Audit Context",
    ).usage["context_packet"]
    output_pdf = tmp_path / "audit.pdf"
    result = compose_from_context(packet, target_profile="technical_audit", output_path=output_pdf)
    assert result.status == "succeeded"
    return output_pdf, tmp_path / "audit.composition.json"
