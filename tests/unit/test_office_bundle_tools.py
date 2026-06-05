import json
from pathlib import Path
from zipfile import ZipFile

from typer.testing import CliRunner


def test_office_bundle_export_and_verify_wrap_existing_bundle_engine(tmp_path: Path) -> None:
    from okoffice.office.bundle import export_office_bundle, verify_office_bundle

    artifact = tmp_path / "evidence.txt"
    bundle = tmp_path / "board-pack.okoffice.zip"
    artifact.write_text("local evidence", encoding="utf-8")

    exported = export_office_bundle(
        artifact_paths=[artifact],
        output_path=bundle,
        title="Vendor Board Pack",
        metadata={"workflow": "board_pack"},
    )

    assert exported.status == "succeeded"
    assert exported.tool == "office.bundle.export"
    assert exported.artifacts[0].path == bundle.resolve()
    assert exported.usage["bundle_manifest"]["title"] == "Vendor Board Pack"
    assert exported.usage["bundle_manifest"]["metadata"]["product"] == "okoffice"
    assert "office.bundle.verify" in exported.next_recommended_tools

    with ZipFile(bundle) as archive:
        names = set(archive.namelist())
        assert "okoffice-bundle-manifest.json" in names
        assert "checksums.sha256" in names
        assert "artifacts/evidence.txt" in names

    verified = verify_office_bundle(bundle)

    assert verified.status == "succeeded"
    assert verified.tool == "office.bundle.verify"
    assert verified.validation is not None
    assert verified.validation.status == "passed"
    assert verified.usage["bundle_verification"]["verified_artifact_count"] == 1


def test_okoffice_bundle_cli_exports_and_verifies(tmp_path: Path) -> None:
    from okoffice.cli_okoffice.main import app

    artifact = tmp_path / "evidence.txt"
    bundle = tmp_path / "board-pack.okoffice.zip"
    artifact.write_text("local evidence", encoding="utf-8")

    exported = CliRunner().invoke(
        app,
        ["bundle", "export", "--file", str(artifact), "-o", str(bundle), "--title", "Vendor Board Pack", "--json"],
    )

    assert exported.exit_code == 0
    exported_payload = json.loads(exported.stdout)
    assert exported_payload["tool"] == "office.bundle.export"
    assert bundle.exists()

    verified = CliRunner().invoke(app, ["bundle", "verify", str(bundle), "--json"])

    assert verified.exit_code == 0
    verified_payload = json.loads(verified.stdout)
    assert verified_payload["tool"] == "office.bundle.verify"
    assert verified_payload["validation"]["status"] == "passed"


def test_office_bundle_tools_run_through_rest_api(tmp_path: Path) -> None:
    from fastapi.testclient import TestClient

    from okoffice.api.app import create_app

    artifact = tmp_path / "evidence.txt"
    bundle = tmp_path / "board-pack.okoffice.zip"
    artifact.write_text("local evidence", encoding="utf-8")
    client = TestClient(create_app())

    exported = client.post(
        "/v1/tools/office.bundle.export/run",
        json={"artifact_paths": [str(artifact)], "output_path": str(bundle), "title": "Vendor Board Pack"},
    )

    assert exported.status_code == 200
    assert exported.json()["tool"] == "office.bundle.export"

    verified = client.post("/v1/tools/office.bundle.verify/run", json={"bundle_path": str(bundle)})

    assert verified.status_code == 200
    assert verified.json()["tool"] == "office.bundle.verify"
    assert verified.json()["validation"]["status"] == "passed"


def test_office_bundle_tools_run_through_mcp_functions(tmp_path: Path) -> None:
    from okoffice.mcp.server import office_bundle_export, office_bundle_verify

    artifact = tmp_path / "evidence.txt"
    bundle = tmp_path / "board-pack.okoffice.zip"
    artifact.write_text("local evidence", encoding="utf-8")

    exported = json.loads(office_bundle_export([str(artifact)], str(bundle), title="Vendor Board Pack"))

    assert exported["tool"] == "office.bundle.export"
    assert bundle.exists()

    verified = json.loads(office_bundle_verify(str(bundle)))

    assert verified["tool"] == "office.bundle.verify"
    assert verified["validation"]["status"] == "passed"


def test_office_bundle_tools_run_through_workflow_runner(tmp_path: Path) -> None:
    from okoffice.workflows.runner import run_workflow

    artifact = tmp_path / "evidence.txt"
    bundle = tmp_path / "board-pack.okoffice.zip"
    artifact.write_text("local evidence", encoding="utf-8")

    result = run_workflow(
        {
            "steps": [
                {
                    "tool": "office.bundle.export",
                    "input": {"artifact_paths": [str(artifact)], "output_path": str(bundle), "title": "Vendor Board Pack"},
                },
                {
                    "tool": "office.bundle.verify",
                    "input": {"bundle_path": str(bundle)},
                },
            ]
        }
    )

    assert result.status == "succeeded"
    steps = result.usage["workflow_run"]["step_results"]
    assert [step["tool"] for step in steps] == ["office.bundle.export", "office.bundle.verify"]
    assert steps[1]["validation"]["status"] == "passed"
