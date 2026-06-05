import asyncio
import json
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image
from typer.testing import CliRunner

import okoffice.mcp.server as mcp_server
from okoffice.api.app import create_app
from okoffice.cli.main import app
from okoffice.tools.registry import get_tool


runner = CliRunner()


def test_forms_and_ocr_tools_are_registered() -> None:
    for tool_name in [
        "pdf.forms.create",
        "pdf.forms.import_data",
        "pdf.forms.validate",
        "pdf.ocr_scan.scan_to_pdf",
        "pdf.ocr_scan.despeckle",
        "pdf.ocr_scan.remove_existing_ocr",
        "pdf.ocr_scan.multilingual_ocr",
    ]:
        tool = get_tool(tool_name)

        assert tool.implemented is True
        assert tool.interfaces == ["cli", "mcp", "rest", "sdk"]


def test_forms_and_ocr_cli_commands(tmp_path: Path) -> None:
    image = tmp_path / "scan.png"
    form = tmp_path / "form.pdf"
    filled = tmp_path / "filled.pdf"
    scan = tmp_path / "scan.pdf"
    despeckled = tmp_path / "despeckled.pdf"
    no_ocr = tmp_path / "no-ocr.pdf"
    multilingual = tmp_path / "multi-ocr.pdf"
    Image.new("RGB", (80, 40), color=(245, 245, 245)).save(image)

    created = runner.invoke(
        app,
        [
            "forms",
            "create",
            "-o",
            str(form),
            "--field",
            '{"name":"name","label":"Name","required":true}',
            "--json",
        ],
    )
    imported = runner.invoke(
        app,
        [
            "forms",
            "import-data",
            str(form),
            "--data",
            '{"name":"Ada"}',
            "-o",
            str(filled),
            "--json",
        ],
    )
    validated = runner.invoke(
        app,
        ["forms", "validate", str(filled), "--required-field", "name", "--json"],
    )
    scanned = runner.invoke(app, ["ocr", "scan-to-pdf", str(image), "-o", str(scan), "--json"])
    despeckle = runner.invoke(app, ["ocr", "despeckle", str(scan), "-o", str(despeckled), "--json"])
    removed = runner.invoke(
        app,
        ["ocr", "remove-existing", str(scan), "-o", str(no_ocr), "--json"],
    )
    ocr = runner.invoke(
        app,
        [
            "ocr",
            "multilingual",
            str(scan),
            "-o",
            str(multilingual),
            "--language",
            "eng",
            "--language",
            "chi_sim",
            "--json",
        ],
    )

    assert created.exit_code == 0
    assert _tool(created.stdout) == "pdf.forms.create"
    assert imported.exit_code == 0
    assert _tool(imported.stdout) == "pdf.forms.import_data"
    assert validated.exit_code == 0
    assert _tool(validated.stdout) == "pdf.forms.validate"
    assert scanned.exit_code == 0
    assert _tool(scanned.stdout) == "pdf.ocr_scan.scan_to_pdf"
    assert despeckle.exit_code == 0
    assert _tool(despeckle.stdout) == "pdf.ocr_scan.despeckle"
    assert removed.exit_code == 0
    assert _tool(removed.stdout) == "pdf.ocr_scan.remove_existing_ocr"
    assert ocr.exit_code == 0
    assert _tool(ocr.stdout) == "pdf.ocr_scan.multilingual_ocr"
    assert form.exists()
    assert filled.exists()
    assert scan.exists()
    assert multilingual.exists()


def test_forms_and_ocr_api_routes(tmp_path: Path) -> None:
    client = TestClient(create_app())
    image = tmp_path / "scan.png"
    form = tmp_path / "form.pdf"
    filled = tmp_path / "filled.pdf"
    scan = tmp_path / "scan.pdf"
    Image.new("RGB", (80, 40), color=(245, 245, 245)).save(image)

    created = client.post(
        "/v1/tools/pdf.forms.create/run",
        json={"output_path": str(form), "fields": [{"name": "name", "label": "Name", "required": True}]},
    )
    imported = client.post(
        "/v1/tools/pdf.forms.import_data/run",
        json={"input_path": str(form), "data": {"name": "Ada"}, "output_path": str(filled)},
    )
    validated = client.post(
        "/v1/tools/pdf.forms.validate/run",
        json={"input_path": str(filled), "required_fields": ["name"]},
    )
    scanned = client.post(
        "/v1/tools/pdf.ocr_scan.scan_to_pdf/run",
        json={"image_paths": [str(image)], "output_path": str(scan)},
    )
    despeckle = client.post(
        "/v1/tools/pdf.ocr_scan.despeckle/run",
        json={"input_path": str(scan), "output_path": str(tmp_path / "despeckled.pdf")},
    )
    removed = client.post(
        "/v1/tools/pdf.ocr_scan.remove_existing_ocr/run",
        json={"input_path": str(scan), "output_path": str(tmp_path / "no-ocr.pdf")},
    )
    multilingual = client.post(
        "/v1/tools/pdf.ocr_scan.multilingual_ocr/run",
        json={
            "input_path": str(scan),
            "output_path": str(tmp_path / "multi-ocr.pdf"),
            "languages": ["eng", "chi_sim"],
        },
    )

    assert created.status_code == 200
    assert created.json()["tool"] == "pdf.forms.create"
    assert imported.status_code == 200
    assert imported.json()["usage"]["applied_field_count"] == 1
    assert validated.status_code == 200
    assert validated.json()["usage"]["missing_required_fields"] == []
    assert scanned.status_code == 200
    assert scanned.json()["usage"]["page_count"] == 1
    assert despeckle.status_code == 200
    assert removed.status_code == 200
    assert multilingual.status_code == 200
    assert multilingual.json()["usage"]["languages"] == ["eng", "chi_sim"]


def test_forms_and_ocr_mcp_tools(tmp_path: Path) -> None:
    image = tmp_path / "scan.png"
    form = tmp_path / "form.pdf"
    filled = tmp_path / "filled.pdf"
    scan = tmp_path / "scan.pdf"
    Image.new("RGB", (80, 40), color=(245, 245, 245)).save(image)
    tool_names = {tool.name for tool in asyncio.run(mcp_server.create_mcp_server().list_tools())}

    assert "pdf_forms_create" in tool_names
    assert "pdf_forms_import_data" in tool_names
    assert "pdf_forms_validate" in tool_names
    assert "pdf_ocr_scan_to_pdf" in tool_names
    assert "pdf_ocr_despeckle" in tool_names
    assert "pdf_ocr_remove_existing_ocr" in tool_names
    assert "pdf_ocr_multilingual_ocr" in tool_names

    created = _json(
        mcp_server.pdf_forms_create(
            str(form),
            fields=[{"name": "name", "label": "Name", "required": True}],
        )
    )
    imported = _json(
        mcp_server.pdf_forms_import_data(
            str(form),
            data={"name": "Ada"},
            output_path=str(filled),
        )
    )
    validated = _json(mcp_server.pdf_forms_validate(str(filled), required_fields=["name"]))
    scanned = _json(mcp_server.pdf_ocr_scan_to_pdf([str(image)], str(scan)))
    despeckle = _json(mcp_server.pdf_ocr_despeckle(str(scan), str(tmp_path / "despeckled.pdf")))
    removed = _json(mcp_server.pdf_ocr_remove_existing_ocr(str(scan), str(tmp_path / "no-ocr.pdf")))
    multilingual = _json(
        mcp_server.pdf_ocr_multilingual_ocr(
            str(scan),
            str(tmp_path / "multi-ocr.pdf"),
            languages=["eng", "chi_sim"],
        )
    )

    assert created["tool"] == "pdf.forms.create"
    assert imported["tool"] == "pdf.forms.import_data"
    assert validated["usage"]["missing_required_fields"] == []
    assert scanned["tool"] == "pdf.ocr_scan.scan_to_pdf"
    assert despeckle["tool"] == "pdf.ocr_scan.despeckle"
    assert removed["tool"] == "pdf.ocr_scan.remove_existing_ocr"
    assert multilingual["usage"]["languages"] == ["eng", "chi_sim"]


def _json(raw: str) -> dict[str, object]:
    payload = json.loads(raw)
    assert isinstance(payload, dict)
    return payload


def _tool(raw: str) -> str:
    return str(_json(raw)["tool"])
