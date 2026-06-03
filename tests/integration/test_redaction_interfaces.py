import asyncio
import json
from pathlib import Path

from fastapi.testclient import TestClient
from pypdf import PdfReader
from reportlab.pdfgen import canvas
from typer.testing import CliRunner

import agentpdf.mcp.server as mcp_server
from agentpdf.api.app import create_app
from agentpdf.cli.main import app
from agentpdf.security.local import redact_pdf, verify_redaction_pdf
from agentpdf.tools.registry import get_tool


runner = CliRunner()
SECRET = "SECRET-CODE-123"


def test_redact_pdf_masks_region_and_removes_text_layer(tmp_path: Path) -> None:
    source = tmp_path / "secret.pdf"
    output = tmp_path / "redacted.pdf"
    _write_secret_pdf(source)

    result = redact_pdf(
        source,
        output,
        regions=[{"page": 1, "bbox": [60, 700, 280, 760], "label": "secret"}],
    )
    verified = verify_redaction_pdf(output, search_terms=[SECRET])

    assert result.status == "succeeded"
    assert result.tool == "pdf.security.redact"
    assert result.validation is not None
    assert result.validation.status == "passed"
    assert result.usage["redaction_strategy"] == "local_rasterize_and_mask_regions"
    assert result.usage["redaction_region_count"] == 1
    assert SECRET not in (PdfReader(output).pages[0].extract_text() or "")
    assert verified.tool == "pdf.security.verify_redaction"
    assert verified.validation is not None
    assert verified.validation.status == "passed"


def test_redaction_tools_are_registered() -> None:
    for tool_name in [
        "pdf.security.redact",
        "pdf.security.verify_redaction",
        "pdf.validation.redaction_check",
    ]:
        tool = get_tool(tool_name)

        assert tool.implemented is True
        assert tool.interfaces == ["cli", "mcp", "rest", "sdk"]


def test_redaction_cli_commands(tmp_path: Path) -> None:
    source = tmp_path / "secret.pdf"
    output = tmp_path / "redacted.pdf"
    _write_secret_pdf(source)
    region = '{"page":1,"bbox":[60,700,280,760],"label":"secret"}'

    redacted = runner.invoke(
        app,
        ["security", "redact", str(source), "-o", str(output), "--region", region, "--json"],
    )
    verified = runner.invoke(
        app,
        ["security", "verify-redaction", str(output), "--search-term", SECRET, "--json"],
    )
    checked = runner.invoke(
        app,
        ["redaction-check", str(output), "--search-term", SECRET, "--json"],
    )

    assert redacted.exit_code == 0
    assert json_payload(redacted.stdout)["tool"] == "pdf.security.redact"
    assert output.exists()
    assert verified.exit_code == 0
    assert json_payload(verified.stdout)["validation"]["status"] == "passed"
    assert checked.exit_code == 0
    assert json_payload(checked.stdout)["tool"] == "pdf.validation.redaction_check"


def test_redaction_api_routes(tmp_path: Path) -> None:
    client = TestClient(create_app())
    source = tmp_path / "secret.pdf"
    output = tmp_path / "redacted.pdf"
    _write_secret_pdf(source)

    redacted = client.post(
        "/v1/tools/pdf.security.redact/run",
        json={
            "input_path": str(source),
            "output_path": str(output),
            "regions": [{"page": 1, "bbox": [60, 700, 280, 760], "label": "secret"}],
        },
    )
    verified = client.post(
        "/v1/tools/pdf.security.verify_redaction/run",
        json={"input_path": str(output), "search_terms": [SECRET]},
    )
    checked = client.post(
        "/v1/tools/pdf.validation.redaction_check/run",
        json={"input_path": str(output), "search_terms": [SECRET]},
    )

    assert redacted.status_code == 200
    assert redacted.json()["tool"] == "pdf.security.redact"
    assert verified.status_code == 200
    assert verified.json()["validation"]["status"] == "passed"
    assert checked.status_code == 200
    assert checked.json()["tool"] == "pdf.validation.redaction_check"


def test_redaction_mcp_tools(tmp_path: Path) -> None:
    source = tmp_path / "secret.pdf"
    output = tmp_path / "redacted.pdf"
    _write_secret_pdf(source)
    tool_names = {tool.name for tool in asyncio.run(mcp_server.create_mcp_server().list_tools())}

    assert "pdf_security_redact" in tool_names
    assert "pdf_security_verify_redaction" in tool_names
    assert "pdf_validation_redaction_check" in tool_names

    redacted = json.loads(
        mcp_server.pdf_security_redact(
            str(source),
            str(output),
            regions=[{"page": 1, "bbox": [60, 700, 280, 760], "label": "secret"}],
        )
    )
    verified = json.loads(mcp_server.pdf_security_verify_redaction(str(output), search_terms=[SECRET]))
    checked = json.loads(mcp_server.pdf_validation_redaction_check(str(output), search_terms=[SECRET]))

    assert redacted["tool"] == "pdf.security.redact"
    assert verified["validation"]["status"] == "passed"
    assert checked["tool"] == "pdf.validation.redaction_check"


def _write_secret_pdf(path: Path) -> None:
    document = canvas.Canvas(str(path))
    document.drawString(72, 740, f"Customer token: {SECRET}")
    document.drawString(72, 700, "Public footer remains visible as raster content.")
    document.showPage()
    document.save()


def json_payload(raw: str) -> dict[str, object]:
    payload = json.loads(raw)
    assert isinstance(payload, dict)
    return payload
