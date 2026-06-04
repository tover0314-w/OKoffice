import json
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient
from typer.testing import CliRunner


def test_word_inspect_document_reports_structure(tmp_path: Path) -> None:
    from agentpdf.office.word import inspect_word_document

    path = tmp_path / "memo.docx"
    _write_docx(path)

    result = inspect_word_document(path)

    assert result.status == "succeeded"
    assert result.tool == "word.inspect.document"
    assert result.usage["document"]["format"] == "docx"
    assert result.usage["structure"]["paragraph_count"] == 2
    assert result.usage["structure"]["heading_count"] == 1
    assert result.usage["structure"]["table_count"] == 1
    assert result.usage["structure"]["section_count"] == 1
    assert result.usage["comments"]["comment_count"] == 1
    assert result.usage["styles"]["style_count"] == 2
    assert "word.extract.structure" in result.next_recommended_tools


def test_sheet_inspect_workbook_reports_sheets_and_formulas(tmp_path: Path) -> None:
    from agentpdf.office.sheet import inspect_sheet_workbook

    path = tmp_path / "model.xlsx"
    _write_xlsx(path)

    result = inspect_sheet_workbook(path)

    assert result.status == "succeeded"
    assert result.tool == "sheet.inspect.workbook"
    assert result.usage["workbook"]["format"] == "xlsx"
    assert result.usage["workbook"]["sheet_count"] == 2
    assert result.usage["sheets"][0]["name"] == "Summary"
    assert result.usage["sheets"][0]["dimension"] == "A1:B2"
    assert result.usage["formulas"]["formula_count"] == 1
    assert result.usage["tables"]["table_count"] == 1
    assert result.usage["charts"]["chart_count"] == 1
    assert result.usage["links"]["external_link_count"] == 1
    assert "sheet.extract.tables" in result.next_recommended_tools


def test_deck_inspect_presentation_reports_slide_assets(tmp_path: Path) -> None:
    from agentpdf.office.deck import inspect_deck_presentation

    path = tmp_path / "deck.pptx"
    _write_pptx(path)

    result = inspect_deck_presentation(path)

    assert result.status == "succeeded"
    assert result.tool == "deck.inspect.presentation"
    assert result.usage["presentation"]["format"] == "pptx"
    assert result.usage["presentation"]["slide_count"] == 2
    assert result.usage["notes"]["notes_slide_count"] == 1
    assert result.usage["layouts"]["layout_count"] == 1
    assert result.usage["theme"]["theme_count"] == 1
    assert result.usage["media"]["media_count"] == 1
    assert result.usage["charts"]["chart_count"] == 1
    assert "deck.edit.patch" in result.next_recommended_tools


def test_okoffice_domain_inspect_cli_commands_return_json(tmp_path: Path) -> None:
    from okoffice.cli.main import app

    docx_path = tmp_path / "memo.docx"
    xlsx_path = tmp_path / "model.xlsx"
    pptx_path = tmp_path / "deck.pptx"
    _write_docx(docx_path)
    _write_xlsx(xlsx_path)
    _write_pptx(pptx_path)

    runner = CliRunner()
    word = runner.invoke(app, ["word", "inspect", str(docx_path), "--json"])
    sheet = runner.invoke(app, ["sheet", "inspect", str(xlsx_path), "--json"])
    deck = runner.invoke(app, ["deck", "inspect", str(pptx_path), "--json"])

    assert word.exit_code == 0
    assert json.loads(word.stdout)["tool"] == "word.inspect.document"
    assert sheet.exit_code == 0
    assert json.loads(sheet.stdout)["tool"] == "sheet.inspect.workbook"
    assert deck.exit_code == 0
    assert json.loads(deck.stdout)["tool"] == "deck.inspect.presentation"


def test_domain_inspect_tools_run_through_agent_interfaces(tmp_path: Path) -> None:
    from agentpdf.api.app import create_app
    from agentpdf.mcp.server import sheet_inspect_workbook
    from agentpdf.workflows.runner import run_workflow

    docx_path = tmp_path / "memo.docx"
    xlsx_path = tmp_path / "model.xlsx"
    pptx_path = tmp_path / "deck.pptx"
    _write_docx(docx_path)
    _write_xlsx(xlsx_path)
    _write_pptx(pptx_path)

    response = TestClient(create_app()).post(
        "/v1/tools/word.inspect.document/run",
        json={"path": str(docx_path)},
    )
    sheet_payload = json.loads(sheet_inspect_workbook(str(xlsx_path)))
    workflow = run_workflow(
        {
            "steps": [
                {
                    "tool": "deck.inspect.presentation",
                    "input": {"path": str(pptx_path)},
                }
            ]
        }
    )

    assert response.status_code == 200
    assert response.json()["tool"] == "word.inspect.document"
    assert sheet_payload["tool"] == "sheet.inspect.workbook"
    assert workflow.status == "succeeded"
    assert workflow.usage["workflow_run"]["step_results"][0]["tool"] == "deck.inspect.presentation"


def _write_docx(path: Path) -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr(
            "word/document.xml",
            """
            <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
              <w:body>
                <w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Board memo</w:t></w:r></w:p>
                <w:p><w:r><w:t>Revenue grew.</w:t></w:r></w:p>
                <w:tbl><w:tr><w:tc><w:p><w:r><w:t>A</w:t></w:r></w:p></w:tc></w:tr></w:tbl>
                <w:sectPr/>
              </w:body>
            </w:document>
            """,
        )
        archive.writestr(
            "word/comments.xml",
            """
            <w:comments xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
              <w:comment w:id="1" w:author="Analyst"/>
            </w:comments>
            """,
        )
        archive.writestr(
            "word/styles.xml",
            """
            <w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
              <w:style w:styleId="Normal"/><w:style w:styleId="Heading1"/>
            </w:styles>
            """,
        )


def _write_xlsx(path: Path) -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr(
            "xl/workbook.xml",
            """
            <workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
              xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
              <sheets>
                <sheet name="Summary" sheetId="1" r:id="rId1"/>
                <sheet name="Details" sheetId="2" r:id="rId2"/>
              </sheets>
            </workbook>
            """,
        )
        archive.writestr(
            "xl/worksheets/sheet1.xml",
            """
            <worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
              <dimension ref="A1:B2"/>
              <sheetData><row r="1"><c r="B1"><f>SUM(A1:A2)</f><v>3</v></c></row></sheetData>
            </worksheet>
            """,
        )
        archive.writestr(
            "xl/worksheets/sheet2.xml",
            """
            <worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
              <dimension ref="C3:C3"/>
            </worksheet>
            """,
        )
        archive.writestr("xl/tables/table1.xml", "<table/>")
        archive.writestr("xl/charts/chart1.xml", "<chart/>")
        archive.writestr("xl/externalLinks/externalLink1.xml", "<externalLink/>")


def _write_pptx(path: Path) -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr(
            "ppt/presentation.xml",
            """
            <p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
              <p:sldIdLst><p:sldId id="256"/><p:sldId id="257"/></p:sldIdLst>
            </p:presentation>
            """,
        )
        archive.writestr(
            "ppt/slides/slide1.xml",
            """
            <p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
              xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:t>Title</a:t></p:sld>
            """,
        )
        archive.writestr("ppt/slides/slide2.xml", "<p:sld xmlns:p='http://schemas.openxmlformats.org/presentationml/2006/main'/>")
        archive.writestr("ppt/notesSlides/notesSlide1.xml", "<notes/>")
        archive.writestr("ppt/slideLayouts/slideLayout1.xml", "<layout/>")
        archive.writestr("ppt/theme/theme1.xml", "<theme/>")
        archive.writestr("ppt/media/image1.png", b"png")
        archive.writestr("ppt/charts/chart1.xml", "<chart/>")
