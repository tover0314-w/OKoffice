import json
import tomllib
from pathlib import Path

from typer.testing import CliRunner

from agentpdf.cli.main import app
from okoffice.cli.main import app as okoffice_app


REPO_ROOT = Path(__file__).resolve().parents[2]
runner = CliRunner()


def test_pyproject_exposes_okoffice_console_script() -> None:
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["scripts"]["okoffice"] == "okoffice.cli.main:app"


def test_office_manifest_command_returns_target_tool_map() -> None:
    result = runner.invoke(app, ["office", "manifest", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    tool_names = {tool["name"] for tool in payload["tools"]}

    assert payload["product"] == "okoffice"
    assert payload["compatibility_package"] == "agentpdf"
    assert "office.workflow.extract_to_sheet" in tool_names
    assert "word.read.document" in tool_names
    assert "sheet.write.workbook" in tool_names
    assert "deck.create.presentation" in tool_names
    assert "deck.create.from_outline" in tool_names


def test_public_okoffice_cli_lists_target_and_legacy_tools() -> None:
    result = runner.invoke(okoffice_app, ["tools", "list", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    target_names = {tool["name"] for tool in payload["target_tools"]}
    legacy_names = {tool["name"] for tool in payload["compatibility_tools"]}

    assert "office.inspect.file" in target_names
    assert "office.workflow.docset_to_sheet" in target_names
    assert "office.validation.package" in target_names
    assert "office.workflow.sheet_to_deck" in target_names
    assert "office.workflow.board_pack" in target_names
    assert "office.workers.status" in target_names
    assert "office.workflow.extract_to_sheet" in target_names
    assert "word.create.report" in target_names
    assert "word.validation.document" in target_names
    assert "sheet.validation.formulas" in target_names
    assert "deck.create.presentation" in target_names
    assert "deck.validation.contact_sheet" in target_names
    assert "deck.validation.presentation" in target_names
    assert "office.bundle.export" in target_names
    assert "office.bundle.verify" in target_names
    assert "pdf.inspect.document" in legacy_names


def test_public_okoffice_cli_exposes_serve_command() -> None:
    result = runner.invoke(okoffice_app, ["serve", "--help"])

    assert result.exit_code == 0
    assert "--mcp" in result.stdout
    assert "--api" in result.stdout


def test_office_plan_command_returns_structured_agent_result() -> None:
    result = runner.invoke(
        app,
        [
            "office",
            "plan",
            "--goal",
            "Extract financial facts from Word and PDF files, build Excel tables, then create a deck.",
            "--input",
            "memo.docx",
            "--input",
            "filing.pdf",
            "--output",
            "model.xlsx",
            "--output",
            "board-deck.pptx",
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    plan = payload["usage"]["plan"]

    assert payload["tool"] == "office.workflow.plan"
    assert payload["status"] == "succeeded"
    assert payload["validation"]["status"] == "passed"
    assert plan["input_formats"] == ["docx", "pdf"]
    assert plan["output_formats"] == ["xlsx", "pptx"]
    assert plan["recommended_pipeline"][0]["tool"] == "office.context.ingest"
    assert "office.workflow.extract_to_sheet" in payload["next_recommended_tools"]


def test_public_okoffice_plan_returns_structured_agent_result() -> None:
    result = runner.invoke(
        okoffice_app,
        [
            "plan",
            "--goal",
            "Extract financial facts from Word and PDF files, build Excel tables, then create a deck.",
            "--input",
            "memo.docx",
            "--input",
            "filing.pdf",
            "--output",
            "model.xlsx",
            "--output",
            "board-deck.pptx",
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)

    assert payload["tool"] == "office.workflow.plan"
    assert payload["usage"]["plan"]["output_formats"] == ["xlsx", "pptx"]
