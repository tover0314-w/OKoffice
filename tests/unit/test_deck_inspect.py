import json
import zipfile
from pathlib import Path

from typer.testing import CliRunner


def test_deck_inspect_presentation_reports_pptx_structure(tmp_path: Path) -> None:
    from okoffice.office.deck import inspect_deck_presentation

    path = tmp_path / "board.pptx"
    _write_pptx_fixture(path)

    result = inspect_deck_presentation(path)

    assert result.status == "succeeded"
    assert result.tool == "deck.inspect.presentation"
    assert result.validation is not None
    assert result.validation.status == "warning"

    summary = result.usage["summary"]
    assert summary["slide_count"] == 2
    assert summary["slide_with_notes_count"] == 1
    assert summary["shape_count"] == 3
    assert summary["text_run_count"] == 3
    assert summary["chart_count"] == 1
    assert summary["media_count"] == 1
    assert summary["theme_count"] == 1
    assert summary["external_link_count"] == 1

    assert result.usage["package"]["has_external_relationships"] is True
    assert result.usage["package"]["macro_enabled"] is False
    assert result.usage["layout"]["rendered_layout_claimed"] is False
    assert "External presentation relationship targets were detected." in result.warnings

    first_slide = result.usage["slides"][0]
    assert first_slide["slide_number"] == 1
    assert first_slide["title"] == "Q2 Results"
    assert first_slide["part"] == "ppt/slides/slide1.xml"
    assert first_slide["has_notes"] is True
    assert first_slide["shape_count"] == 2
    assert first_slide["chart_count"] == 1
    assert first_slide["media_count"] == 1
    assert first_slide["locator"] == {"kind": "deck", "slide": 1, "slide_id": "256"}

    second_slide = result.usage["slides"][1]
    assert second_slide["title"] == "Appendix"
    assert second_slide["has_notes"] is False

    title_shape = result.usage["shapes"][0]
    assert title_shape["text"] == "Q2 Results"
    assert title_shape["placeholder"] == "title"
    assert title_shape["locator"] == {
        "kind": "deck",
        "slide": 1,
        "slide_id": "256",
        "shape_id": "2",
        "placeholder": "title",
    }

    notes = result.usage["notes"][0]
    assert notes["slide_number"] == 1
    assert notes["text"] == "Discuss risk drivers."
    assert notes["locator"] == {"kind": "deck", "slide": 1, "slide_id": "256", "notes": True}

    chart = result.usage["charts"][0]
    assert chart["slide_number"] == 1
    assert chart["chart_id"] == "chart1"
    assert chart["locator"] == {"kind": "deck", "slide": 1, "slide_id": "256", "shape_id": "chart1"}

    media = result.usage["media"][0]
    assert media["slide_number"] == 1
    assert media["kind"] == "image"
    assert media["part"] == "ppt/media/image1.png"

    theme = result.usage["themes"][0]
    assert theme["name"] == "Quarterly Theme"


def test_deck_inspect_presentation_rejects_non_pptx_zip(tmp_path: Path) -> None:
    from okoffice.office.deck import inspect_deck_presentation

    path = tmp_path / "bad.pptx"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")

    result = inspect_deck_presentation(path)

    assert result.status == "failed"
    assert result.error is not None
    assert result.error.code == "unsupported_file_type"


def test_okoffice_deck_inspect_cli_returns_tool_result_json(tmp_path: Path) -> None:
    from okoffice.cli_okoffice.main import app

    path = tmp_path / "board.pptx"
    _write_pptx_fixture(path)

    result = CliRunner().invoke(app, ["deck", "inspect", str(path), "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["tool"] == "deck.inspect.presentation"
    assert payload["usage"]["summary"]["slide_count"] == 2
    assert payload["usage"]["slides"][0]["locator"]["kind"] == "deck"


def test_deck_inspect_presentation_runs_through_rest_api(tmp_path: Path) -> None:
    from fastapi.testclient import TestClient

    from okoffice.api.app import create_app

    path = tmp_path / "board.pptx"
    _write_pptx_fixture(path)

    response = TestClient(create_app()).post(
        "/v1/tools/deck.inspect.presentation/run",
        json={"path": str(path)},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["tool"] == "deck.inspect.presentation"
    assert payload["usage"]["summary"]["chart_count"] == 1


def test_deck_inspect_presentation_runs_through_mcp_function(tmp_path: Path) -> None:
    from okoffice.mcp.server import deck_inspect_presentation

    path = tmp_path / "board.pptx"
    _write_pptx_fixture(path)

    payload = json.loads(deck_inspect_presentation(str(path)))

    assert payload["tool"] == "deck.inspect.presentation"
    assert payload["status"] == "succeeded"
    assert payload["usage"]["summary"]["theme_count"] == 1


def test_deck_inspect_presentation_runs_through_workflow_runner(tmp_path: Path) -> None:
    from okoffice.workflows.runner import run_workflow

    path = tmp_path / "board.pptx"
    _write_pptx_fixture(path)

    result = run_workflow(
        {
            "steps": [
                {
                    "tool": "deck.inspect.presentation",
                    "input": {"path": str(path)},
                }
            ]
        }
    )

    assert result.status == "succeeded"
    step = result.usage["workflow_run"]["step_results"][0]
    assert step["tool"] == "deck.inspect.presentation"
    assert step["status"] == "succeeded"
    assert "deck.validation.presentation" in step["next_recommended_tools"]


def _write_pptx_fixture(path: Path) -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("ppt/presentation.xml", _presentation_xml())
        archive.writestr("ppt/_rels/presentation.xml.rels", _presentation_rels_xml())
        archive.writestr("ppt/slides/slide1.xml", _slide1_xml())
        archive.writestr("ppt/slides/slide2.xml", _slide2_xml())
        archive.writestr("ppt/slides/_rels/slide1.xml.rels", _slide1_rels_xml())
        archive.writestr("ppt/notesSlides/notesSlide1.xml", _notes_xml())
        archive.writestr("ppt/charts/chart1.xml", "<c:chartSpace xmlns:c='http://schemas.openxmlformats.org/drawingml/2006/chart'/>")
        archive.writestr("ppt/theme/theme1.xml", _theme_xml())
        archive.writestr("ppt/media/image1.png", b"\x89PNG\r\n\x1a\n")
        archive.writestr("docProps/core.xml", _core_xml())


def _presentation_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <p:sldIdLst>
    <p:sldId id="256" r:id="rId1"/>
    <p:sldId id="257" r:id="rId2"/>
  </p:sldIdLst>
</p:presentation>
"""


def _presentation_rels_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide2.xml"/>
  <Relationship Id="rIdTheme" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="theme/theme1.xml"/>
  <Relationship Id="rIdExternal" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" Target="https://example.com/board" TargetMode="External"/>
</Relationships>
"""


def _slide1_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <p:cSld>
    <p:spTree>
      <p:sp>
        <p:nvSpPr><p:cNvPr id="2" name="Title 1"/><p:nvPr><p:ph type="title"/></p:nvPr></p:nvSpPr>
        <p:txBody><a:p><a:r><a:t>Q2 Results</a:t></a:r></a:p></p:txBody>
      </p:sp>
      <p:sp>
        <p:nvSpPr><p:cNvPr id="3" name="Body 1"/><p:nvPr><p:ph type="body"/></p:nvPr></p:nvSpPr>
        <p:txBody><a:p><a:r><a:t>Revenue grew</a:t></a:r></a:p></p:txBody>
      </p:sp>
      <p:graphicFrame>
        <p:nvGraphicFramePr><p:cNvPr id="4" name="Chart 1"/></p:nvGraphicFramePr>
        <a:graphic><a:graphicData><c:chart r:id="rIdChart1"/></a:graphicData></a:graphic>
      </p:graphicFrame>
      <p:pic>
        <p:nvPicPr><p:cNvPr id="5" name="Logo"/></p:nvPicPr>
        <p:blipFill><a:blip r:embed="rIdImage1"/></p:blipFill>
      </p:pic>
    </p:spTree>
  </p:cSld>
</p:sld>
"""


def _slide2_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
  <p:cSld>
    <p:spTree>
      <p:sp>
        <p:nvSpPr><p:cNvPr id="2" name="Title 1"/><p:nvPr><p:ph type="title"/></p:nvPr></p:nvSpPr>
        <p:txBody><a:p><a:r><a:t>Appendix</a:t></a:r></a:p></p:txBody>
      </p:sp>
    </p:spTree>
  </p:cSld>
</p:sld>
"""


def _slide1_rels_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rIdNotes" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/notesSlide" Target="../notesSlides/notesSlide1.xml"/>
  <Relationship Id="rIdChart1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/chart" Target="../charts/chart1.xml"/>
  <Relationship Id="rIdImage1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="../media/image1.png"/>
</Relationships>
"""


def _notes_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<p:notes xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
  <p:cSld><p:spTree><p:sp><p:txBody><a:p><a:r><a:t>Discuss risk drivers.</a:t></a:r></a:p></p:txBody></p:sp></p:spTree></p:cSld>
</p:notes>
"""


def _theme_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="Quarterly Theme"/>
"""


def _core_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/">
  <dc:title>Board Deck</dc:title>
  <dc:creator>okoffice tests</dc:creator>
</cp:coreProperties>
"""
