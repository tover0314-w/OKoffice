import json
import zipfile
from pathlib import Path

from typer.testing import CliRunner


def test_source_to_board_pack_chains_full_pipeline(tmp_path: Path) -> None:
    from okoffice.office.workflows import source_to_board_pack

    source = tmp_path / "memo.docx"
    output = tmp_path / "board-pack.zip"
    _write_labeled_docx(source)

    result = source_to_board_pack(
        files=[source],
        schema=_schema(),
        output_path=output,
        title="E2E Board Pack",
        deck_title="Quarterly Review",
    )

    assert result.status == "succeeded"
    assert result.tool == "office.workflow.source_to_board_pack"
    assert output.exists()

    xlsx_path = tmp_path / "board-pack.xlsx"
    pptx_path = tmp_path / "board-pack.pptx"
    assert xlsx_path.exists(), f"Evidence workbook missing: {xlsx_path}"
    assert pptx_path.exists(), f"Deck presentation missing: {pptx_path}"

    assert result.validation is not None
    assert result.validation.status in ("passed", "warning")
    check_names = [c.name for c in result.validation.checks]
    assert "docset_to_sheet" in check_names
    assert "sheet_to_deck" in check_names
    assert "board_pack" in check_names
    assert "end_to_end_pipeline" in check_names

    assert result.usage["pipeline"] == "office.workflow.source_to_board_pack"
    assert result.usage["steps_completed"] == 3
    assert result.usage["source_count"] == 1

    with zipfile.ZipFile(output) as archive:
        names = set(archive.namelist())
        assert "okoffice-manifest.json" in names
        assert "okoffice-validation.json" in names
        manifest = json.loads(archive.read("okoffice-manifest.json"))
        assert manifest["product"] == "okoffice"
        assert manifest["title"] == "E2E Board Pack"


def test_source_to_board_pack_fails_when_docset_step_fails(tmp_path: Path) -> None:
    from okoffice.office.workflows import source_to_board_pack

    output = tmp_path / "fail.zip"
    result = source_to_board_pack(
        files=[tmp_path / "nonexistent.docx"],
        schema=_schema(),
        output_path=output,
    )

    assert result.status == "failed"


def test_source_to_board_pack_runs_through_mcp(tmp_path: Path) -> None:
    from okoffice.mcp.server import office_workflow_source_to_board_pack

    source = tmp_path / "memo.docx"
    output = tmp_path / "mcp-board-pack.zip"
    _write_labeled_docx(source)

    payload = json.loads(
        office_workflow_source_to_board_pack(
            files=[str(source)],
            schema=_schema(),
            output_path=str(output),
            title="MCP E2E",
        )
    )

    assert payload["tool"] == "office.workflow.source_to_board_pack"
    assert payload["status"] == "succeeded"
    assert payload["usage"]["steps_completed"] == 3


def test_source_to_board_pack_runs_through_cli(tmp_path: Path) -> None:
    from okoffice.cli_okoffice.main import app

    source = tmp_path / "memo.docx"
    output = tmp_path / "cli-board-pack.zip"
    _write_labeled_docx(source)

    schema_path = tmp_path / "schema.json"
    schema_path.write_text(json.dumps(_schema()), encoding="utf-8")

    runner = CliRunner()
    cli_result = runner.invoke(
        app,
        [
            "workflow",
            "source-to-board-pack",
            str(source),
            "--schema",
            str(schema_path),
            "-o",
            str(output),
            "--title",
            "CLI E2E",
        ],
    )

    assert cli_result.exit_code == 0, f"CLI failed: {cli_result.output}"
    assert output.exists()


def test_source_to_board_pack_runs_through_generic_workflow_runner(tmp_path: Path) -> None:
    from okoffice.workflows.runner import run_workflow

    source = tmp_path / "memo.docx"
    output = tmp_path / "runner-board-pack.zip"
    _write_labeled_docx(source)

    result = run_workflow(
        {
            "steps": [
                {
                    "tool": "office.workflow.source_to_board_pack",
                    "input": {
                        "files": [str(source)],
                        "schema": _schema(),
                        "output_path": str(output),
                        "title": "Runner E2E",
                    },
                }
            ]
        }
    )

    assert result.status == "succeeded"
    step = result.usage["workflow_run"]["step_results"][0]
    assert step["tool"] == "office.workflow.source_to_board_pack"
    assert step["validation"]["status"] in ("passed", "warning")


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
