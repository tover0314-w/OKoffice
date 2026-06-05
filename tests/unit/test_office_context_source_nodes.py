import json
import zipfile
from pathlib import Path


def test_context_packet_adds_native_source_nodes_for_word_sheet_and_deck(tmp_path: Path) -> None:
    from okoffice.office.context import build_office_context_packet

    docx_path = tmp_path / "memo.docx"
    xlsx_path = tmp_path / "model.xlsx"
    pptx_path = tmp_path / "deck.pptx"
    _write_docx_with_table(docx_path)
    _write_xlsx_with_table_and_formula(xlsx_path)
    _write_pptx_with_slides(pptx_path)

    result = build_office_context_packet(
        [docx_path, xlsx_path, pptx_path],
        tmp_path / "context.packet.json",
        title="Native Source Graph",
    )

    assert result.status == "succeeded"
    packet = result.usage["context_packet"]
    nodes = packet["source_graph"]["nodes"]
    node_types = {node["type"] for node in nodes}

    assert "word.table" in node_types
    assert "sheet.sheet" in node_types
    assert "sheet.table" in node_types
    assert "sheet.formula_summary" in node_types
    assert "deck.slide" in node_types
    assert result.usage["summary"]["source_node_count"] >= 12
    assert result.usage["summary"]["native_node_count"] >= 6

    word_table = _first_node(nodes, "word.table")
    assert word_table["locators"][0] == {
        "kind": "word_table",
        "path": docx_path.as_posix(),
        "table_index": 1,
    }
    assert word_table["evidence"]["row_count"] == 2
    assert word_table["evidence"]["cell_count"] == 4

    sheet_table = _first_node(nodes, "sheet.table")
    assert sheet_table["locators"][0]["kind"] == "sheet_range"
    assert sheet_table["locators"][0]["sheet_name"] == "Summary"
    assert sheet_table["locators"][0]["range_ref"] == "A1:B3"
    assert sheet_table["evidence"]["row_count"] == 3
    assert sheet_table["evidence"]["cell_count"] == 6

    formula_summary = _first_node(nodes, "sheet.formula_summary")
    assert formula_summary["evidence"]["formula_count"] == 1
    assert formula_summary["locators"][0]["kind"] == "workbook_formulas"

    deck_slides = [node for node in nodes if node["type"] == "deck.slide"]
    assert [slide["locators"][0]["slide_index"] for slide in deck_slides] == [1, 2]
    assert deck_slides[0]["evidence"]["package_part"] == "ppt/slides/slide1.xml"

    edges = packet["source_graph"]["edges"]
    relationships = {edge["relationship"] for edge in edges}
    assert "contains_source_node" in relationships

    written = json.loads((tmp_path / "context.packet.json").read_text(encoding="utf-8"))
    assert len(written["source_graph"]["nodes"]) == len(nodes)


def _first_node(nodes: list[dict[str, object]], node_type: str) -> dict[str, object]:
    return next(node for node in nodes if node["type"] == node_type)


def _write_docx_with_table(path: Path) -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr(
            "word/document.xml",
            """
            <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
              <w:body>
                <w:tbl>
                  <w:tr>
                    <w:tc><w:p><w:r><w:t>Name</w:t></w:r></w:p></w:tc>
                    <w:tc><w:p><w:r><w:t>Value</w:t></w:r></w:p></w:tc>
                  </w:tr>
                  <w:tr>
                    <w:tc><w:p><w:r><w:t>Alpha</w:t></w:r></w:p></w:tc>
                    <w:tc><w:p><w:r><w:t>42</w:t></w:r></w:p></w:tc>
                  </w:tr>
                </w:tbl>
              </w:body>
            </w:document>
            """,
        )


def _write_xlsx_with_table_and_formula(path: Path) -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr(
            "xl/workbook.xml",
            """
            <workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
              xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
              <sheets><sheet name="Summary" sheetId="1" r:id="rId1"/></sheets>
            </workbook>
            """,
        )
        archive.writestr(
            "xl/worksheets/sheet1.xml",
            """
            <worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
              <dimension ref="A1:B3"/>
              <sheetData>
                <row r="1">
                  <c r="A1" t="inlineStr"><is><t>Name</t></is></c>
                  <c r="B1" t="inlineStr"><is><t>Value</t></is></c>
                </row>
                <row r="2">
                  <c r="A2" t="inlineStr"><is><t>Alpha</t></is></c>
                  <c r="B2"><v>42</v></c>
                </row>
                <row r="3">
                  <c r="A3" t="inlineStr"><is><t>Total</t></is></c>
                  <c r="B3"><f>SUM(B2:B2)</f><v>42</v></c>
                </row>
              </sheetData>
            </worksheet>
            """,
        )


def _write_pptx_with_slides(path: Path) -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("ppt/presentation.xml", "<p:presentation xmlns:p='x'/>")
        archive.writestr("ppt/slides/slide1.xml", "<p:sld xmlns:p='x'><a:t xmlns:a='y'>One</a:t></p:sld>")
        archive.writestr("ppt/slides/slide2.xml", "<p:sld xmlns:p='x'><a:t xmlns:a='y'>Two</a:t></p:sld>")
