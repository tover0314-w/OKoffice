import asyncio
from pathlib import Path

from PIL import Image
from fastapi.testclient import TestClient
from reportlab.pdfgen import canvas
from typer.testing import CliRunner

import okoffice.mcp.server as mcp_server
from okoffice.api.app import create_app
from okoffice.cli.main import app
from okoffice.compare.local import semantic_diff_pdf, version_report_pdf
from okoffice.ir.semantic import (
    parse_charts_pdf,
    parse_figures_pdf,
    parse_formulas_pdf,
    parse_references_pdf,
)
from okoffice.tools.registry import get_tool


runner = CliRunner()


def test_semantic_diff_pdf_returns_local_change_evidence(tmp_path: Path) -> None:
    before = tmp_path / "before.pdf"
    after = tmp_path / "after.pdf"
    _write_text_pdf(before, ["Revenue increased by 10%.", "Risk level is low."])
    _write_text_pdf(after, ["Revenue increased by 15%.", "Risk level is medium."])

    result = semantic_diff_pdf(before, after)

    assert result.status == "succeeded"
    assert result.tool == "pdf.compare.semantic_diff"
    assert result.usage["changed_page_count"] == 1
    assert result.usage["changes"][0]["page_number"] == 1
    assert result.usage["changes"][0]["similarity"] < 1
    assert "local_text_similarity" in result.usage["diff_strategy"]


def test_version_report_pdf_writes_markdown_artifact(tmp_path: Path) -> None:
    before = tmp_path / "before.pdf"
    after = tmp_path / "after.pdf"
    report = tmp_path / "version-report.md"
    _write_text_pdf(before, ["Original policy text."])
    _write_text_pdf(after, ["Updated policy text with a new control."])

    result = version_report_pdf(before, after, output_path=report)

    assert result.status == "succeeded"
    assert result.tool == "pdf.compare.version_report"
    assert result.artifacts[0].path == report.resolve()
    assert "Changed pages" in report.read_text(encoding="utf-8")
    assert result.usage["report"]["changed_page_count"] == 1


def test_local_parse_figures_formulas_charts_and_references(tmp_path: Path) -> None:
    source = tmp_path / "parse-source.pdf"
    image = tmp_path / "figure.png"
    Image.new("RGB", (24, 24), color=(80, 120, 160)).save(image)
    _write_parse_fixture(source, image)

    figures = parse_figures_pdf(source)
    formulas = parse_formulas_pdf(source)
    charts = parse_charts_pdf(source)
    references = parse_references_pdf(source)

    assert figures.status == "succeeded"
    assert figures.tool == "pdf.ai.parse.figures"
    assert figures.usage["figure_count"] >= 1
    assert "Figure 1" in figures.usage["figures"][0]["caption"]
    assert formulas.tool == "pdf.ai.parse.formulas"
    assert formulas.usage["formula_count"] >= 1
    assert any("E = mc^2" in item["text"] for item in formulas.usage["formulas"])
    assert charts.tool == "pdf.ai.parse.charts"
    assert charts.usage["chart_count"] >= 1
    assert "Chart 1" in charts.usage["charts"][0]["caption"]
    assert references.tool == "pdf.ai.parse.references"
    assert references.usage["reference_count"] >= 2


def test_compare_and_semantic_parse_tools_are_registered() -> None:
    for tool_name in [
        "pdf.compare.semantic_diff",
        "pdf.compare.version_report",
        "pdf.ai.parse.figures",
        "pdf.ai.parse.formulas",
        "pdf.ai.parse.charts",
        "pdf.ai.parse.references",
    ]:
        tool = get_tool(tool_name)

        assert tool.implemented is True
        assert tool.interfaces == ["cli", "mcp", "rest", "sdk"]


def test_compare_and_semantic_parse_cli_commands(tmp_path: Path) -> None:
    before = tmp_path / "before.pdf"
    after = tmp_path / "after.pdf"
    report = tmp_path / "version-report.md"
    source, _image = _write_parse_pdf_fixture(tmp_path)
    _write_text_pdf(before, ["Revenue increased by 10%."])
    _write_text_pdf(after, ["Revenue increased by 15%."])

    semantic_diff = runner.invoke(
        app,
        ["compare", "semantic-diff", str(before), str(after), "--pages", "1", "--json"],
    )
    version_report = runner.invoke(
        app,
        [
            "compare",
            "version-report",
            str(before),
            str(after),
            "-o",
            str(report),
            "--json",
        ],
    )
    figures = runner.invoke(app, ["parse-figures", str(source), "--json"])
    formulas = runner.invoke(app, ["parse-formulas", str(source), "--json"])
    charts = runner.invoke(app, ["parse-charts", str(source), "--json"])
    references = runner.invoke(app, ["parse-references", str(source), "--json"])

    assert semantic_diff.exit_code == 0
    assert json_tool(semantic_diff.stdout) == "pdf.compare.semantic_diff"
    assert version_report.exit_code == 0
    assert json_tool(version_report.stdout) == "pdf.compare.version_report"
    assert report.exists()
    assert figures.exit_code == 0
    assert json_tool(figures.stdout) == "pdf.ai.parse.figures"
    assert formulas.exit_code == 0
    assert json_tool(formulas.stdout) == "pdf.ai.parse.formulas"
    assert charts.exit_code == 0
    assert json_tool(charts.stdout) == "pdf.ai.parse.charts"
    assert references.exit_code == 0
    assert json_tool(references.stdout) == "pdf.ai.parse.references"


def test_compare_and_semantic_parse_api_routes(tmp_path: Path) -> None:
    client = TestClient(create_app())
    before = tmp_path / "before.pdf"
    after = tmp_path / "after.pdf"
    report = tmp_path / "version-report.md"
    source, _image = _write_parse_pdf_fixture(tmp_path)
    _write_text_pdf(before, ["Original policy text."])
    _write_text_pdf(after, ["Updated policy text."])

    semantic_diff = client.post(
        "/v1/tools/pdf.compare.semantic_diff/run",
        json={"before_path": str(before), "after_path": str(after), "pages": "1"},
    )
    version_report = client.post(
        "/v1/tools/pdf.compare.version_report/run",
        json={"before_path": str(before), "after_path": str(after), "output_path": str(report)},
    )
    figures = client.post("/v1/tools/pdf.ai.parse.figures/run", json={"input_path": str(source)})
    formulas = client.post("/v1/tools/pdf.ai.parse.formulas/run", json={"input_path": str(source)})
    charts = client.post("/v1/tools/pdf.ai.parse.charts/run", json={"input_path": str(source)})
    references = client.post("/v1/tools/pdf.ai.parse.references/run", json={"input_path": str(source)})

    assert semantic_diff.status_code == 200
    assert semantic_diff.json()["tool"] == "pdf.compare.semantic_diff"
    assert version_report.status_code == 200
    assert version_report.json()["tool"] == "pdf.compare.version_report"
    assert report.exists()
    assert figures.status_code == 200
    assert figures.json()["usage"]["figure_count"] >= 1
    assert formulas.status_code == 200
    assert formulas.json()["usage"]["formula_count"] >= 1
    assert charts.status_code == 200
    assert charts.json()["usage"]["chart_count"] >= 1
    assert references.status_code == 200
    assert references.json()["usage"]["reference_count"] >= 2


def test_compare_and_semantic_parse_mcp_tools(tmp_path: Path) -> None:
    before = tmp_path / "before.pdf"
    after = tmp_path / "after.pdf"
    report = tmp_path / "version-report.md"
    source, _image = _write_parse_pdf_fixture(tmp_path)
    _write_text_pdf(before, ["Risk level is low."])
    _write_text_pdf(after, ["Risk level is medium."])
    tool_names = {tool.name for tool in asyncio.run(mcp_server.create_mcp_server().list_tools())}

    assert "pdf_compare_semantic_diff" in tool_names
    assert "pdf_compare_version_report" in tool_names
    assert "pdf_ai_parse_figures" in tool_names
    assert "pdf_ai_parse_formulas" in tool_names
    assert "pdf_ai_parse_charts" in tool_names
    assert "pdf_ai_parse_references" in tool_names

    semantic_diff = json_loads(mcp_server.pdf_compare_semantic_diff(str(before), str(after), pages="1"))
    version_report = json_loads(
        mcp_server.pdf_compare_version_report(str(before), str(after), output_path=str(report))
    )
    figures = json_loads(mcp_server.pdf_ai_parse_figures(str(source)))
    formulas = json_loads(mcp_server.pdf_ai_parse_formulas(str(source)))
    charts = json_loads(mcp_server.pdf_ai_parse_charts(str(source)))
    references = json_loads(mcp_server.pdf_ai_parse_references(str(source)))

    assert semantic_diff["tool"] == "pdf.compare.semantic_diff"
    assert version_report["tool"] == "pdf.compare.version_report"
    assert figures["usage"]["figure_count"] >= 1
    assert formulas["usage"]["formula_count"] >= 1
    assert charts["usage"]["chart_count"] >= 1
    assert references["usage"]["reference_count"] >= 2


def _write_text_pdf(path: Path, lines: list[str]) -> None:
    document = canvas.Canvas(str(path))
    y = 740
    for line in lines:
        document.drawString(72, y, line)
        y -= 20
    document.showPage()
    document.save()


def _write_parse_fixture(path: Path, image_path: Path) -> None:
    document = canvas.Canvas(str(path))
    document.drawString(72, 740, "Figure 1: System architecture")
    document.drawImage(str(image_path), 72, 690, width=24, height=24)
    document.drawString(72, 650, "E = mc^2")
    document.drawString(72, 620, "Chart 1: Revenue by month")
    document.drawString(72, 590, "[1] Doe, Agent PDF Systems, 2026.")
    document.drawString(72, 560, "https://example.com/reference")
    document.showPage()
    document.save()


def _write_parse_pdf_fixture(tmp_path: Path) -> tuple[Path, Path]:
    source = tmp_path / "parse-source.pdf"
    image = tmp_path / "figure.png"
    Image.new("RGB", (24, 24), color=(80, 120, 160)).save(image)
    _write_parse_fixture(source, image)
    return source, image


def json_loads(raw: str) -> dict[str, object]:
    import json

    payload = json.loads(raw)
    assert isinstance(payload, dict)
    return payload


def json_tool(raw: str) -> str:
    payload = json_loads(raw)
    return str(payload["tool"])
