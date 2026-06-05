import json
import zipfile
from pathlib import Path

from typer.testing import CliRunner


def test_office_context_build_packet_summarizes_mixed_office_sources(tmp_path: Path) -> None:
    from agentpdf.office.context import build_office_context_packet

    memo = tmp_path / "memo.docx"
    model = tmp_path / "model.xlsx"
    deck = tmp_path / "board.pptx"
    output_path = tmp_path / "context.json"
    _write_docx(memo)
    _write_xlsx(model)
    _write_pptx(deck)

    result = build_office_context_packet(
        files=[memo, model, deck],
        output_path=output_path,
        title="Renewal packet",
        intent="Build board-ready renewal evidence.",
    )

    assert result.status == "succeeded"
    assert result.tool == "office.context.build_packet"
    assert result.validation is not None
    assert result.validation.status == "passed"
    assert output_path.exists()
    assert result.artifacts[0].path == output_path

    usage = result.usage
    assert usage["item_count"] == 3
    assert usage["domains"] == ["deck", "sheet", "word"]
    assert usage["inspection_tools"] == [
        "word.inspect.document",
        "sheet.inspect.workbook",
        "deck.inspect.presentation",
    ]
    assert "office.extract.schema" in result.next_recommended_tools

    packet = usage["context_packet"]
    assert packet["product"] == "okoffice"
    assert packet["title"] == "Renewal packet"
    assert packet["intent"] == "Build board-ready renewal evidence."
    assert packet["items"][0]["domain"] == "word"
    assert packet["items"][0]["inspection"]["summary"]["paragraph_count"] == 1
    assert packet["items"][1]["domain"] == "sheet"
    assert packet["items"][1]["inspection"]["summary"]["sheet_count"] == 1
    assert packet["items"][2]["domain"] == "deck"
    assert packet["items"][2]["inspection"]["summary"]["slide_count"] == 1

    source_graph = packet["source_graph"]
    source_types = {node["source_type"] for node in source_graph["nodes"]}
    assert {"word_document", "word_paragraph", "workbook", "sheet", "deck", "slide"} <= source_types
    assert source_graph["node_count"] == len(source_graph["nodes"])
    assert source_graph["edge_count"] == len(source_graph["edges"])

    written = json.loads(output_path.read_text(encoding="utf-8"))
    assert written["context_packet_id"] == packet["context_packet_id"]


def test_okoffice_context_build_cli_returns_tool_result_json(tmp_path: Path) -> None:
    from okoffice.cli.main import app

    memo = tmp_path / "memo.docx"
    model = tmp_path / "model.xlsx"
    output_path = tmp_path / "context.json"
    _write_docx(memo)
    _write_xlsx(model)

    result = CliRunner().invoke(
        app,
        [
            "context",
            "build",
            "--file",
            str(memo),
            "--file",
            str(model),
            "-o",
            str(output_path),
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["tool"] == "office.context.build_packet"
    assert payload["usage"]["item_count"] == 2
    assert payload["usage"]["domains"] == ["sheet", "word"]


def test_office_context_build_packet_runs_through_rest_api(tmp_path: Path) -> None:
    from fastapi.testclient import TestClient

    from agentpdf.api.app import create_app

    memo = tmp_path / "memo.docx"
    deck = tmp_path / "board.pptx"
    output_path = tmp_path / "context.json"
    _write_docx(memo)
    _write_pptx(deck)

    response = TestClient(create_app()).post(
        "/v1/tools/office.context.build_packet/run",
        json={
            "files": [
                {"kind": "local_path", "path": str(memo)},
                {"path": str(deck)},
            ],
            "output_path": str(output_path),
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["tool"] == "office.context.build_packet"
    assert payload["usage"]["domains"] == ["deck", "word"]


def test_office_context_build_packet_runs_through_mcp_function(tmp_path: Path) -> None:
    from agentpdf.mcp.server import office_context_build_packet

    model = tmp_path / "model.xlsx"
    output_path = tmp_path / "context.json"
    _write_xlsx(model)

    payload = json.loads(office_context_build_packet(files=[str(model)], output_path=str(output_path)))

    assert payload["tool"] == "office.context.build_packet"
    assert payload["status"] == "succeeded"
    assert payload["usage"]["inspection_tools"] == ["sheet.inspect.workbook"]


def test_office_context_build_packet_runs_through_workflow_runner(tmp_path: Path) -> None:
    from agentpdf.workflows.runner import run_workflow

    memo = tmp_path / "memo.docx"
    output_path = tmp_path / "context.json"
    _write_docx(memo)

    result = run_workflow(
        {
            "steps": [
                {
                    "tool": "office.context.build_packet",
                    "input": {"files": [str(memo)], "output_path": str(output_path)},
                }
            ]
        }
    )

    assert result.status == "succeeded"
    step = result.usage["workflow_run"]["step_results"][0]
    assert step["tool"] == "office.context.build_packet"
    assert step["status"] == "succeeded"
    assert "office.extract.schema" in step["next_recommended_tools"]


def _write_docx(path: Path) -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr(
            "word/document.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body><w:p><w:r><w:t>Renewal memo evidence.</w:t></w:r></w:p></w:body>
</w:document>
""",
        )


def _write_xlsx(path: Path) -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr(
            "xl/workbook.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets><sheet name="Summary" sheetId="1" r:id="rId1"/></sheets>
</workbook>
""",
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>
""",
        )
        archive.writestr(
            "xl/worksheets/sheet1.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <dimension ref="A1:A1"/><sheetData><row r="1"><c r="A1"><v>1</v></c></row></sheetData>
</worksheet>
""",
        )


def _write_pptx(path: Path) -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr(
            "ppt/presentation.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <p:sldIdLst><p:sldId id="256" r:id="rId1"/></p:sldIdLst>
</p:presentation>
""",
        )
        archive.writestr(
            "ppt/_rels/presentation.xml.rels",
            """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide1.xml"/>
</Relationships>
""",
        )
        archive.writestr(
            "ppt/slides/slide1.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
  <p:cSld><p:spTree><p:sp><p:nvSpPr><p:cNvPr id="2" name="Title 1"/><p:nvPr><p:ph type="title"/></p:nvPr></p:nvSpPr><p:txBody><a:p><a:r><a:t>Board update</a:t></a:r></a:p></p:txBody></p:sp></p:spTree></p:cSld>
</p:sld>
""",
        )
