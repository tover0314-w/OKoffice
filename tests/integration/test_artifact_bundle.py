import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator
from typer.testing import CliRunner

from agentpdf.artifacts import bundle as artifact_bundle
from agentpdf.api.app import create_app
from agentpdf.artifacts.bundle import export_artifact_bundle
from agentpdf.cli.main import app
from agentpdf.core.pdf import create_text_pdf
from agentpdf.mcp import server as mcp_server
from agentpdf.mcp.server import pdf_artifacts_export_bundle


runner = CliRunner()


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
