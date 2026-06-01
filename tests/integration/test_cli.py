import json
from pathlib import Path

from typer.testing import CliRunner

from agentpdf.cli.main import app


runner = CliRunner()


def test_tools_list_json_includes_complete_manifest() -> None:
    result = runner.invoke(app, ["tools", "list", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert len(payload["tools"]) >= 100
    assert any(tool["name"] == "pdf.organize.merge" for tool in payload["tools"])


def test_tools_show_json_returns_one_tool() -> None:
    result = runner.invoke(app, ["tools", "show", "pdf.inspect.document", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["name"] == "pdf.inspect.document"
    assert payload["implemented"] is True


def test_inspect_cli_returns_uniform_tool_result(simple_pdf: Path) -> None:
    result = runner.invoke(app, ["inspect", str(simple_pdf), "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "succeeded"
    assert payload["tool"] == "pdf.inspect.document"
    assert payload["usage"]["page_count"] == 1


def test_merge_cli_writes_output_and_returns_artifact(
    simple_pdf: Path, two_page_pdf: Path, tmp_path: Path
) -> None:
    output = tmp_path / "merged.pdf"

    result = runner.invoke(
        app,
        ["merge", str(simple_pdf), str(two_page_pdf), "-o", str(output), "--json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "succeeded"
    assert payload["artifacts"][0]["page_count"] == 3
    assert output.exists()


def test_split_cli_writes_selected_pages(two_page_pdf: Path, tmp_path: Path) -> None:
    output = tmp_path / "page-1.pdf"

    result = runner.invoke(
        app,
        ["split", str(two_page_pdf), "--pages", "1", "-o", str(output), "--json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "succeeded"
    assert payload["artifacts"][0]["page_count"] == 1
    assert output.exists()


def test_extract_remove_and_rotate_cli(two_page_pdf: Path, tmp_path: Path) -> None:
    extract_output = tmp_path / "extract.pdf"
    remove_output = tmp_path / "remove.pdf"
    rotate_output = tmp_path / "rotate.pdf"

    extract = runner.invoke(
        app,
        ["extract-pages", str(two_page_pdf), "--pages", "2", "-o", str(extract_output), "--json"],
    )
    remove = runner.invoke(
        app,
        ["remove-pages", str(two_page_pdf), "--pages", "1", "-o", str(remove_output), "--json"],
    )
    rotate = runner.invoke(
        app,
        [
            "rotate-pages",
            str(two_page_pdf),
            "--pages",
            "1",
            "--degrees",
            "90",
            "-o",
            str(rotate_output),
            "--json",
        ],
    )

    assert extract.exit_code == 0
    assert json.loads(extract.stdout)["tool"] == "pdf.organize.extract_pages"
    assert remove.exit_code == 0
    assert json.loads(remove.stdout)["tool"] == "pdf.organize.remove_pages"
    assert rotate.exit_code == 0
    assert json.loads(rotate.stdout)["tool"] == "pdf.organize.rotate_pages"


def test_render_cli_writes_png_output(simple_pdf: Path, tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "render",
            str(simple_pdf),
            "--pages",
            "1",
            "--format",
            "png",
            "--out-dir",
            str(tmp_path),
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "succeeded"
    assert payload["tool"] == "pdf.convert.pdf_to_images"
    assert payload["artifacts"][0]["mime_type"] == "image/png"
    assert len(list(tmp_path.iterdir())) == 1


def test_text_and_metadata_cli(text_pdf: Path, metadata_pdf: Path, tmp_path: Path) -> None:
    updated = tmp_path / "updated.pdf"
    cleaned = tmp_path / "cleaned.pdf"

    text = runner.invoke(app, ["extract-text", str(text_pdf), "--pages", "1", "--json"])
    read = runner.invoke(app, ["metadata", "read", str(metadata_pdf), "--json"])
    update = runner.invoke(
        app,
        [
            "metadata",
            "update",
            str(metadata_pdf),
            "--title",
            "CLI Title",
            "-o",
            str(updated),
            "--json",
        ],
    )
    remove = runner.invoke(
        app,
        ["metadata", "remove", str(metadata_pdf), "-o", str(cleaned), "--json"],
    )

    assert text.exit_code == 0
    assert "AgentPDF local text layer" in json.loads(text.stdout)["usage"]["text"]
    assert read.exit_code == 0
    assert json.loads(read.stdout)["usage"]["metadata"]["Title"] == "Original Title"
    assert update.exit_code == 0
    assert json.loads(update.stdout)["tool"] == "pdf.metadata.update"
    assert remove.exit_code == 0
    assert json.loads(remove.stdout)["tool"] == "pdf.metadata.remove"


def test_serve_api_invokes_local_rest_server(monkeypatch) -> None:
    called = {}

    def fake_run(app_path: str, **kwargs) -> None:
        called["app_path"] = app_path
        called["kwargs"] = kwargs

    monkeypatch.setattr("uvicorn.run", fake_run)

    result = runner.invoke(app, ["serve", "--api"])

    assert result.exit_code == 0
    assert called["app_path"] == "agentpdf.api.app:create_app"
    assert called["kwargs"]["factory"] is True
    assert called["kwargs"]["host"] == "127.0.0.1"
    assert called["kwargs"]["port"] == 7331
