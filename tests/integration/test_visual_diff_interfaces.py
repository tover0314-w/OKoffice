import asyncio
import json
from pathlib import Path

from fastapi.testclient import TestClient
from reportlab.pdfgen import canvas
from typer.testing import CliRunner

import agentpdf.compare.local as compare_local
import agentpdf.mcp.server as mcp_server
from agentpdf.api.app import create_app
from agentpdf.cli.main import app
from agentpdf.tools.registry import get_tool


runner = CliRunner()


def test_visual_diff_pdf_returns_rendered_page_evidence(tmp_path: Path) -> None:
    before = tmp_path / "before.pdf"
    after = tmp_path / "after.pdf"
    _write_visual_pdf(before, "Risk: low", fill_color=(0.8, 0.9, 1.0))
    _write_visual_pdf(after, "Risk: high", fill_color=(1.0, 0.8, 0.8))

    visual_diff_pdf = getattr(compare_local, "visual_diff_pdf", None)
    assert callable(visual_diff_pdf)
    result = visual_diff_pdf(before, after, pages="1", max_difference_ratio=0.0)

    assert result.status == "succeeded"
    assert result.tool == "pdf.compare.visual_diff"
    assert result.validation is not None
    assert result.validation.status == "warning"
    assert result.usage["changed_page_count"] == 1
    assert result.usage["changes"][0]["page_number"] == 1
    assert result.usage["changes"][0]["difference_ratio"] > 0
    assert result.usage["diff_strategy"] == "local_render_pixel_difference"


def test_visual_diff_tools_are_registered() -> None:
    for tool_name in ["pdf.compare.visual_diff", "pdf.validation.visual_diff"]:
        tool = get_tool(tool_name)

        assert tool.implemented is True
        assert tool.interfaces == ["cli", "mcp", "rest", "sdk"]


def test_visual_diff_cli_commands(tmp_path: Path) -> None:
    before = tmp_path / "before.pdf"
    after = tmp_path / "after.pdf"
    _write_visual_pdf(before, "Before", fill_color=(0.8, 0.9, 1.0))
    _write_visual_pdf(after, "After", fill_color=(1.0, 0.8, 0.8))

    compare = runner.invoke(
        app,
        ["compare", "visual-diff", str(before), str(after), "--pages", "1", "--json"],
    )
    validation = runner.invoke(
        app,
        [
            "visual-diff",
            str(before),
            str(after),
            "--pages",
            "1",
            "--max-difference-ratio",
            "0",
            "--json",
        ],
    )

    assert compare.exit_code == 0
    assert json_payload(compare.stdout)["tool"] == "pdf.compare.visual_diff"
    assert validation.exit_code == 0
    validation_payload = json_payload(validation.stdout)
    assert validation_payload["tool"] == "pdf.validation.visual_diff"
    assert validation_payload["validation"]["status"] == "warning"


def test_visual_diff_api_routes(tmp_path: Path) -> None:
    client = TestClient(create_app())
    before = tmp_path / "before.pdf"
    after = tmp_path / "after.pdf"
    _write_visual_pdf(before, "Before", fill_color=(0.8, 0.9, 1.0))
    _write_visual_pdf(after, "After", fill_color=(1.0, 0.8, 0.8))

    compare = client.post(
        "/v1/tools/pdf.compare.visual_diff/run",
        json={"before_path": str(before), "after_path": str(after), "pages": "1"},
    )
    validation = client.post(
        "/v1/tools/pdf.validation.visual_diff/run",
        json={
            "before_path": str(before),
            "after_path": str(after),
            "pages": "1",
            "max_difference_ratio": 0,
        },
    )

    assert compare.status_code == 200
    assert compare.json()["tool"] == "pdf.compare.visual_diff"
    assert compare.json()["usage"]["changed_page_count"] == 1
    assert validation.status_code == 200
    assert validation.json()["tool"] == "pdf.validation.visual_diff"
    assert validation.json()["validation"]["status"] == "warning"


def test_visual_diff_mcp_tools(tmp_path: Path) -> None:
    before = tmp_path / "before.pdf"
    after = tmp_path / "after.pdf"
    _write_visual_pdf(before, "Before", fill_color=(0.8, 0.9, 1.0))
    _write_visual_pdf(after, "After", fill_color=(1.0, 0.8, 0.8))
    tool_names = {tool.name for tool in asyncio.run(mcp_server.create_mcp_server().list_tools())}

    assert "pdf_compare_visual_diff" in tool_names
    assert "pdf_validation_visual_diff" in tool_names

    compare = json.loads(mcp_server.pdf_compare_visual_diff(str(before), str(after), pages="1"))
    validation = json.loads(
        mcp_server.pdf_validation_visual_diff(
            str(before),
            str(after),
            pages="1",
            max_difference_ratio=0,
        )
    )

    assert compare["tool"] == "pdf.compare.visual_diff"
    assert compare["usage"]["changed_page_count"] == 1
    assert validation["tool"] == "pdf.validation.visual_diff"
    assert validation["validation"]["status"] == "warning"


def _write_visual_pdf(path: Path, label: str, fill_color: tuple[float, float, float]) -> None:
    document = canvas.Canvas(str(path))
    document.setFillColorRGB(*fill_color)
    document.rect(72, 620, 180, 80, fill=1, stroke=0)
    document.setFillColorRGB(0, 0, 0)
    document.drawString(72, 740, label)
    document.showPage()
    document.save()


def json_payload(raw: str) -> dict[str, object]:
    payload = json.loads(raw)
    assert isinstance(payload, dict)
    return payload
