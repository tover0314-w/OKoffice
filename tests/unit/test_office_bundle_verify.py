import json
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient
from typer.testing import CliRunner


def test_verify_board_pack_checks_manifest_validation_and_artifact_hashes(tmp_path: Path) -> None:
    from okoffice.office.workflows import board_pack, verify_board_pack

    workbook_path, deck_path = _write_board_pack_inputs(tmp_path)
    bundle_path = tmp_path / "board-pack.zip"
    board_pack([workbook_path, deck_path], bundle_path, title="Q4 Board Pack")

    result = verify_board_pack(bundle_path)

    assert result.status == "succeeded"
    assert result.tool == "office.bundle.verify"
    assert result.artifacts[0].path == bundle_path
    assert result.artifacts[0].source_tool == "office.bundle.verify"
    assert result.validation is not None
    assert result.validation.status == "passed"
    assert result.usage["summary"]["manifest_file_count"] == 2
    assert result.usage["summary"]["verified_file_count"] == 2
    assert result.usage["summary"]["missing_file_count"] == 0
    assert result.usage["summary"]["hash_mismatch_count"] == 0
    assert result.usage["summary"]["size_mismatch_count"] == 0
    assert result.usage["manifest"]["workflow"] == "office.workflow.board_pack"
    assert [item["archive_path"] for item in result.usage["files"]] == [
        "artifacts/model.xlsx",
        "artifacts/board-review.pptx",
    ]
    assert "office.artifacts.source_map" in result.next_recommended_tools


def test_verify_board_pack_reports_hash_mismatch_without_mutating_bundle(tmp_path: Path) -> None:
    from okoffice.office.workflows import board_pack, verify_board_pack

    workbook_path, deck_path = _write_board_pack_inputs(tmp_path)
    bundle_path = tmp_path / "board-pack.zip"
    tampered_path = tmp_path / "tampered-board-pack.zip"
    board_pack([workbook_path, deck_path], bundle_path, title="Q4 Board Pack")
    _copy_bundle_with_tampered_member(
        bundle_path,
        tampered_path,
        member_name="artifacts/model.xlsx",
        replacement=b"not the workbook bytes in the manifest",
    )

    result = verify_board_pack(tampered_path)

    assert result.status == "succeeded"
    assert result.validation is not None
    assert result.validation.status == "failed"
    assert result.usage["summary"]["manifest_file_count"] == 2
    assert result.usage["summary"]["verified_file_count"] == 1
    assert result.usage["summary"]["hash_mismatch_count"] == 1
    assert result.usage["summary"]["size_mismatch_count"] == 1
    assert any("sha256 mismatch" in warning for warning in result.warnings)
    assert any(file["integrity_status"] == "failed" for file in result.usage["files"])

    original_result = verify_board_pack(bundle_path)
    assert original_result.validation is not None
    assert original_result.validation.status == "passed"


def test_bundle_verify_agent_interfaces(tmp_path: Path) -> None:
    from okoffice.api.app import create_app
    from okoffice.mcp.server import office_bundle_verify
    from okoffice.office.workflows import board_pack
    from okoffice.workflows.runner import run_workflow
    from okoffice.cli_okoffice.main import app

    workbook_path, deck_path = _write_board_pack_inputs(tmp_path)
    bundle_path = tmp_path / "board-pack.zip"
    board_pack([workbook_path, deck_path], bundle_path, title="Q4 Board Pack")

    runner = CliRunner()
    cli = runner.invoke(app, ["bundle", "verify", str(bundle_path), "--json"])
    response = TestClient(create_app()).post(
        "/v1/tools/office.bundle.verify/run",
        json={"bundle_path": str(bundle_path)},
    )
    mcp_payload = json.loads(office_bundle_verify(str(bundle_path)))
    workflow = run_workflow(
        {
            "steps": [
                {
                    "tool": "office.bundle.verify",
                    "input": {"bundle_path": str(bundle_path)},
                }
            ]
        }
    )

    assert cli.exit_code == 0
    assert json.loads(cli.stdout)["tool"] == "office.bundle.verify"
    assert response.status_code == 200
    assert response.json()["usage"]["summary"]["verified_file_count"] == 2
    assert mcp_payload["tool"] == "office.bundle.verify"
    assert mcp_payload["validation"]["status"] == "passed"
    assert workflow.status == "succeeded"
    assert workflow.usage["workflow_run"]["step_results"][0]["tool"] == "office.bundle.verify"


def test_bundle_verify_is_listed_in_manifests() -> None:
    from okoffice.tools.registry_okoffice import load_okoffice_manifest

    manifest = load_okoffice_manifest()
    target = {tool["name"]: tool for tool in manifest["target_tools"]}
    assert target["office.bundle.verify"]["status"] == "beta"
    assert target["office.bundle.verify"]["implemented"] is True

    catalog = json.loads(Path("schemas/mcp-tools.catalog.json").read_text(encoding="utf-8"))
    entries = {tool["name"]: tool for tool in catalog["tools"]}
    assert entries["office_bundle_verify"]["maps_to"] == "office.bundle.verify"


def _write_board_pack_inputs(tmp_path: Path) -> tuple[Path, Path]:
    from okoffice.office.deck import create_deck_from_outline
    from okoffice.office.xlsx import write_xlsx

    workbook_path = tmp_path / "model.xlsx"
    deck_path = tmp_path / "board-review.pptx"
    write_xlsx(
        workbook_path,
        [
            (
                "Model",
                [
                    ["Metric", "Value"],
                    ["Revenue", 120],
                    ["Margin", 0.32],
                ],
            ),
            (
                "SourceRefs",
                [
                    ["record_index", "source_path", "source_refs_json"],
                    [1, "source.docx", "[]"],
                    [2, "source.docx", "[]"],
                ],
            ),
        ],
    )
    create_deck_from_outline(
        {
            "slides": [
                {"title": "Board Review", "bullets": ["Revenue grew", "Margin held"]},
                {"title": "Next Steps", "bullets": ["Validate bundle"]},
            ]
        },
        deck_path,
    )
    return workbook_path, deck_path


def _copy_bundle_with_tampered_member(source: Path, target: Path, *, member_name: str, replacement: bytes) -> None:
    with zipfile.ZipFile(source, "r") as input_archive:
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as output_archive:
            for name in input_archive.namelist():
                data = replacement if name == member_name else input_archive.read(name)
                output_archive.writestr(name, data)
