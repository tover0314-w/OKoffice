import json
import zipfile
from pathlib import Path

from typer.testing import CliRunner


def test_board_pack_workflow_creates_workbook_memo_deck_and_verified_bundle(tmp_path: Path) -> None:
    from agentpdf.office.workflows import board_pack

    source = tmp_path / "memo.docx"
    out_dir = tmp_path / "board-pack"
    _write_labeled_docx(source)

    result = board_pack(
        files=[source],
        schema=_schema(),
        out_dir=out_dir,
        title="Vendor Renewal Review",
        profile="board_review",
    )

    assert result.status == "succeeded"
    assert result.tool == "office.workflow.board_pack"
    assert result.validation is not None
    assert result.validation.status == "warning"
    assert (out_dir / "evidence.xlsx").exists()
    assert (out_dir / "evidence.context.json").exists()
    assert (out_dir / "evidence.evidence.json").exists()
    assert (out_dir / "memo.docx").exists()
    assert (out_dir / "board-deck.pptx").exists()
    assert (out_dir / "board-pack.okoffice.zip").exists()

    assert result.usage["summary"] == {
        "file_count": 1,
        "artifact_count": 6,
        "workbook_rows": 1,
        "memo_paragraphs": 6,
        "deck_slides": 2,
        "bundle_validation_status": "passed",
        "contact_sheet_status": "skipped",
    }
    assert [step["tool"] for step in result.usage["steps"]] == [
        "office.workflow.docset_to_sheet",
        "word.create.report",
        "office.workflow.sheet_to_deck",
        "office.bundle.export",
        "office.bundle.verify",
    ]
    assert "office.bundle.verify" in result.next_recommended_tools

    with zipfile.ZipFile(out_dir / "board-pack.okoffice.zip") as archive:
        names = set(archive.namelist())
        assert "checksums.sha256" in names
        assert "artifacts/evidence.xlsx" in names
        assert "artifacts/memo.docx" in names
        assert "artifacts/board-deck.pptx" in names


def test_board_pack_workflow_can_add_pdf_handout_to_verified_bundle(tmp_path: Path) -> None:
    from agentpdf.office.workflows import board_pack

    source = tmp_path / "memo.docx"
    out_dir = tmp_path / "board-pack"
    _write_labeled_docx(source)

    result = board_pack(
        files=[source],
        schema=_schema(),
        out_dir=out_dir,
        title="Vendor Renewal Review",
        profile="board_review",
        include_pdf_handout=True,
    )

    assert result.status == "succeeded"
    assert (out_dir / "handout.html").exists()
    assert (out_dir / "handout.pdf").exists()
    assert (out_dir / "handout.qa.json").exists()
    assert (out_dir / "handout.artifact-manifest.json").exists()
    assert (out_dir / "handout.artifact-graph.json").exists()
    assert result.usage["summary"]["pdf_handout_status"] == "passed"
    assert result.usage["workflow"]["paths"]["handout_pdf"] == (out_dir / "handout.pdf").resolve().as_posix()
    assert "pdf.workflow.createpdf" in [step["tool"] for step in result.usage["steps"]]

    with zipfile.ZipFile(out_dir / "board-pack.okoffice.zip") as archive:
        names = set(archive.namelist())
        assert "artifacts/handout.pdf" in names
        assert "artifacts/handout.html" in names
        assert "artifacts/handout.qa.json" in names


def test_okoffice_board_pack_cli_returns_tool_result_json(tmp_path: Path) -> None:
    from okoffice.cli.main import app

    source = tmp_path / "memo.docx"
    schema_path = tmp_path / "schema.json"
    out_dir = tmp_path / "board-pack"
    _write_labeled_docx(source)
    schema_path.write_text(json.dumps(_schema()), encoding="utf-8")

    result = CliRunner().invoke(
        app,
        [
            "workflow",
            "board-pack",
            "--file",
            str(source),
            "--schema",
            str(schema_path),
            "--out-dir",
            str(out_dir),
            "--title",
            "Vendor Renewal Review",
            "--include-pdf-handout",
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["tool"] == "office.workflow.board_pack"
    assert payload["usage"]["summary"]["bundle_validation_status"] == "passed"
    assert payload["usage"]["summary"]["pdf_handout_status"] == "passed"
    assert (out_dir / "handout.pdf").exists()


def test_board_pack_workflow_runs_through_rest_api(tmp_path: Path) -> None:
    from fastapi.testclient import TestClient

    from agentpdf.api.app import create_app

    source = tmp_path / "memo.docx"
    out_dir = tmp_path / "board-pack"
    _write_labeled_docx(source)

    response = TestClient(create_app()).post(
        "/v1/tools/office.workflow.board_pack/run",
        json={
            "files": [str(source)],
            "schema": _schema(),
            "out_dir": str(out_dir),
            "title": "Vendor Renewal Review",
            "include_pdf_handout": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["tool"] == "office.workflow.board_pack"
    assert payload["usage"]["summary"]["pdf_handout_status"] == "passed"
    assert (out_dir / "handout.pdf").exists()


def test_board_pack_workflow_runs_through_mcp_function(tmp_path: Path) -> None:
    from agentpdf.mcp.server import office_workflow_board_pack

    source = tmp_path / "memo.docx"
    out_dir = tmp_path / "board-pack"
    _write_labeled_docx(source)

    payload = json.loads(
        office_workflow_board_pack(
            [str(source)],
            _schema(),
            str(out_dir),
            title="Vendor Renewal Review",
            include_pdf_handout=True,
        )
    )

    assert payload["tool"] == "office.workflow.board_pack"
    assert payload["status"] == "succeeded"
    assert payload["usage"]["summary"]["workbook_rows"] == 1
    assert payload["usage"]["summary"]["pdf_handout_status"] == "passed"


def test_board_pack_workflow_runs_through_generic_workflow_runner(tmp_path: Path) -> None:
    from agentpdf.workflows.runner import run_workflow

    source = tmp_path / "memo.docx"
    out_dir = tmp_path / "board-pack"
    _write_labeled_docx(source)

    result = run_workflow(
        {
            "steps": [
                {
                    "tool": "office.workflow.board_pack",
                    "input": {
                        "files": [str(source)],
                        "schema": _schema(),
                        "out_dir": str(out_dir),
                        "title": "Vendor Renewal Review",
                        "include_pdf_handout": True,
                    },
                }
            ]
        }
    )

    assert result.status == "succeeded"
    step = result.usage["workflow_run"]["step_results"][0]
    assert step["tool"] == "office.workflow.board_pack"
    assert step["validation"]["status"] == "warning"
    assert (out_dir / "handout.pdf").exists()


def _schema() -> dict[str, object]:
    return {
        "name": "vendor_renewal",
        "fields": [
            {"name": "vendor", "type": "string", "aliases": ["Vendor"]},
            {"name": "renewal_date", "type": "date", "aliases": ["Renewal date"]},
            {"name": "annual_amount", "type": "number", "aliases": ["Annual amount"]},
            {"name": "risk", "type": "string", "aliases": ["Risk"]},
        ],
    }


def _write_labeled_docx(path: Path) -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr(
            "word/document.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>Vendor: Acme Corp</w:t></w:r></w:p>
    <w:p><w:r><w:t>Renewal date: 2026-09-30</w:t></w:r></w:p>
    <w:p><w:r><w:t>Annual amount: $120,000</w:t></w:r></w:p>
    <w:p><w:r><w:t>Risk: High</w:t></w:r></w:p>
  </w:body>
</w:document>
""",
        )
