import asyncio
import json
from pathlib import Path

from fastapi.testclient import TestClient
from pypdf import PdfReader, PdfWriter
from typer.testing import CliRunner

import okoffice.mcp.server as mcp_server
from okoffice.api.app import create_app
from okoffice.cli.main import app
from okoffice.security.local import inspect_health_pdf, sanitize_pdf
from okoffice.tools.registry import get_tool


runner = CliRunner()


def test_inspect_health_and_sanitize_pdf_remove_active_content(tmp_path: Path) -> None:
    source = tmp_path / "active.pdf"
    output = tmp_path / "sanitized.pdf"
    _write_active_pdf(source)

    health = inspect_health_pdf(source)
    sanitized = sanitize_pdf(source, output)
    post_health = inspect_health_pdf(output)

    assert health.tool == "pdf.inspect.health"
    assert health.validation is not None
    assert health.validation.status == "warning"
    assert health.usage["suspicious_count"] >= 1
    assert any(finding["risk"] == "javascript_action" for finding in health.usage["findings"])

    assert sanitized.status == "succeeded"
    assert sanitized.tool == "pdf.security.sanitize"
    assert output.exists()
    assert b"/JavaScript" in source.read_bytes()
    assert b"/JavaScript" not in output.read_bytes()
    assert PdfReader(output).metadata is None or "/Title" not in dict(PdfReader(output).metadata)
    assert sanitized.validation is not None
    assert sanitized.validation.status == "passed"
    assert sanitized.usage["removed_risk_count"] >= 1

    assert post_health.validation is not None
    assert post_health.validation.status == "passed"
    assert post_health.usage["suspicious_count"] == 0


def test_sanitize_and_health_tools_are_registered() -> None:
    for tool_name in ["pdf.inspect.health", "pdf.security.sanitize"]:
        tool = get_tool(tool_name)

        assert tool.implemented is True
        assert tool.interfaces == ["cli", "mcp", "rest", "sdk"]


def test_sanitize_and_health_cli_commands(tmp_path: Path) -> None:
    source = tmp_path / "active.pdf"
    output = tmp_path / "sanitized.pdf"
    _write_active_pdf(source)

    health = runner.invoke(app, ["inspect-health", str(source), "--json"])
    sanitized = runner.invoke(app, ["security", "sanitize", str(source), "-o", str(output), "--json"])
    post_health = runner.invoke(app, ["inspect-health", str(output), "--json"])

    assert health.exit_code == 0
    assert json_payload(health.stdout)["tool"] == "pdf.inspect.health"
    assert sanitized.exit_code == 0
    assert json_payload(sanitized.stdout)["tool"] == "pdf.security.sanitize"
    assert output.exists()
    assert post_health.exit_code == 0
    assert json_payload(post_health.stdout)["validation"]["status"] == "passed"


def test_sanitize_and_health_api_routes(tmp_path: Path) -> None:
    client = TestClient(create_app())
    source = tmp_path / "active.pdf"
    output = tmp_path / "sanitized.pdf"
    _write_active_pdf(source)

    health = client.post("/v1/tools/pdf.inspect.health/run", json={"input_path": str(source)})
    sanitized = client.post(
        "/v1/tools/pdf.security.sanitize/run",
        json={"input_path": str(source), "output_path": str(output)},
    )
    post_health = client.post("/v1/tools/pdf.inspect.health/run", json={"input_path": str(output)})

    assert health.status_code == 200
    assert health.json()["tool"] == "pdf.inspect.health"
    assert sanitized.status_code == 200
    assert sanitized.json()["tool"] == "pdf.security.sanitize"
    assert post_health.status_code == 200
    assert post_health.json()["validation"]["status"] == "passed"


def test_sanitize_and_health_mcp_tools(tmp_path: Path) -> None:
    source = tmp_path / "active.pdf"
    output = tmp_path / "sanitized.pdf"
    _write_active_pdf(source)
    tool_names = {tool.name for tool in asyncio.run(mcp_server.create_mcp_server().list_tools())}

    assert "pdf_inspect_health" in tool_names
    assert "pdf_security_sanitize" in tool_names

    health = json.loads(mcp_server.pdf_inspect_health(str(source)))
    sanitized = json.loads(mcp_server.pdf_security_sanitize(str(source), str(output)))
    post_health = json.loads(mcp_server.pdf_inspect_health(str(output)))

    assert health["tool"] == "pdf.inspect.health"
    assert sanitized["tool"] == "pdf.security.sanitize"
    assert post_health["validation"]["status"] == "passed"


def _write_active_pdf(path: Path) -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.add_metadata({"/Title": "Sensitive Metadata"})
    writer.add_js("app.alert('unsafe')")
    with path.open("wb") as handle:
        writer.write(handle)


def json_payload(raw: str) -> dict[str, object]:
    payload = json.loads(raw)
    assert isinstance(payload, dict)
    return payload
