import json
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient


def test_word_patch_apply_is_non_mutating_and_runs_through_rest_and_mcp(tmp_path: Path) -> None:
    from agentpdf.api.app import create_app
    from agentpdf.mcp.server import word_patch_apply
    from agentpdf.office.word import inspect_word_document
    from agentpdf.office.word_patch import apply_word_patch, plan_word_patch

    input_path = tmp_path / "memo.docx"
    output_path = tmp_path / "memo.updated.docx"
    rest_output = tmp_path / "memo.rest.docx"
    mcp_output = tmp_path / "memo.mcp.docx"
    _write_docx(input_path, ["Vendor Renewal Memo", "Risk: High"])
    before_xml = _read_zip_text(input_path, "word/document.xml")
    operations = [
        {"op": "replace_paragraph", "paragraph_index": 1, "text": "Risk: Medium"},
        {"op": "append_paragraph", "text": "Next steps: approve renewal."},
    ]

    planned = plan_word_patch(input_path=input_path, operations=operations)

    assert planned.status == "succeeded"
    assert planned.tool == "word.patch.plan"
    assert planned.usage["summary"]["operation_count"] == 2
    assert planned.usage["preview"]["changes"][0]["previous_text"] == "Risk: High"
    assert planned.usage["patch_transaction"]["mutates_inputs"] is False

    applied = apply_word_patch(input_path=input_path, output_path=output_path, operations=operations)

    assert applied.status == "succeeded"
    assert applied.tool == "word.patch.apply"
    assert applied.validation is not None
    assert applied.validation.status == "passed"
    assert applied.usage["summary"]["output_paragraph_count"] == 3
    assert applied.usage["patch_transaction"]["input_path"] == input_path.resolve().as_posix()
    assert applied.usage["patch_transaction"]["output_path"] == output_path.resolve().as_posix()
    assert _read_zip_text(input_path, "word/document.xml") == before_xml
    inspected = inspect_word_document(output_path)
    assert [paragraph["text"] for paragraph in inspected.usage["paragraphs"]] == [
        "Vendor Renewal Memo",
        "Risk: Medium",
        "Next steps: approve renewal.",
    ]

    response = TestClient(create_app()).post(
        "/v1/tools/word.patch.apply/run",
        json={"input_path": str(input_path), "output_path": str(rest_output), "operations": operations},
    )
    assert response.status_code == 200
    assert response.json()["tool"] == "word.patch.apply"
    assert response.json()["usage"]["summary"]["operation_count"] == 2

    mcp_payload = json.loads(word_patch_apply(str(input_path), str(mcp_output), operations))
    assert mcp_payload["tool"] == response.json()["tool"]
    assert mcp_payload["usage"]["summary"] == response.json()["usage"]["summary"]


def test_generated_workbook_has_data_model_chart_plan_and_validation_bindings(tmp_path: Path) -> None:
    from agentpdf.office.sheet import inspect_sheet_workbook
    from agentpdf.office.validation import validate_sheet_formulas
    from agentpdf.office.workbook import write_sheet_workbook

    evidence_path = tmp_path / "evidence.json"
    output_path = tmp_path / "evidence.xlsx"
    evidence_path.write_text(json.dumps(_evidence()), encoding="utf-8")

    result = write_sheet_workbook(evidence_path=evidence_path, output_path=output_path)

    assert result.status == "succeeded"
    assert result.usage["summary"]["sheet_count"] == 4
    assert result.usage["summary"]["data_model_count"] == 4
    assert result.usage["summary"]["chart_plan_count"] == 2
    assert [sheet["name"] for sheet in result.usage["sheets"]] == [
        "Evidence",
        "SourceMap",
        "DataModel",
        "Charts",
    ]
    assert result.usage["data_model"]["fields"][2]["semantic_type"] == "number"
    assert result.usage["chart_plan"][0]["chart_type"] == "bar"
    assert result.validation is not None
    checks = {check.name: check.details for check in result.validation.checks}
    assert checks["data_model_written"]["field_count"] == 4
    assert checks["chart_plan_written"]["chart_plan_count"] == 2

    inspected = inspect_sheet_workbook(output_path)
    assert inspected.usage["summary"]["sheet_count"] == 4
    assert inspected.usage["summary"]["table_count"] == 4
    table_names = {table["name"] for table in inspected.usage["tables"]}
    assert {"DataModelTable", "ChartPlanTable"} <= table_names
    assert inspected.usage["data_model"]["field_count"] == 4
    assert inspected.usage["chart_plan"]["chart_plan_count"] == 2

    validated = validate_sheet_formulas(output_path)
    assert validated.status == "succeeded"
    assert validated.usage["summary"]["data_model_count"] == 4
    assert validated.usage["summary"]["chart_plan_count"] == 2
    assert validated.usage["bindings"]["data_model"]["field_count"] == 4
    assert validated.usage["bindings"]["chart_plan"]["chart_plan_count"] == 2


def test_deck_create_accepts_style_overrides_and_deck_patch_edits_theme(tmp_path: Path) -> None:
    from agentpdf.office.deck_patch import apply_deck_patch
    from agentpdf.office.deck_writer import create_deck_presentation
    from agentpdf.office.workbook import write_sheet_workbook

    evidence_path = tmp_path / "evidence.json"
    workbook_path = tmp_path / "evidence.xlsx"
    deck_path = tmp_path / "board.pptx"
    patched_path = tmp_path / "board.styled.pptx"
    evidence_path.write_text(json.dumps(_evidence()), encoding="utf-8")
    assert write_sheet_workbook(evidence_path=evidence_path, output_path=workbook_path).status == "succeeded"

    created = create_deck_presentation(
        workbook_path=workbook_path,
        output_path=deck_path,
        title="Vendor Renewal Review",
        profile="board_review",
        style={"theme_name": "Executive Green", "primary_color": "123456", "accent_color": "2BA84A"},
    )

    assert created.status == "succeeded"
    assert created.usage["style"]["theme_name"] == "Executive Green"
    assert created.usage["presentation_manifest"]["style"]["accent_color"] == "2BA84A"
    theme_xml = _read_zip_text(deck_path, "ppt/theme/theme1.xml")
    assert 'name="Executive Green"' in theme_xml
    assert 'val="123456"' in theme_xml
    assert 'val="2BA84A"' in theme_xml

    patched = apply_deck_patch(
        input_path=deck_path,
        output_path=patched_path,
        operations=[
            {"op": "replace_text", "find": "Risk: High", "replace": "Risk: Medium"},
            {"op": "update_theme", "theme_name": "Executive Blue", "primary_color": "0B3D91", "accent_color": "D1495B"},
        ],
    )

    assert patched.status == "succeeded"
    assert patched.tool == "deck.patch.apply"
    assert patched.usage["summary"]["operation_count"] == 2
    assert patched.usage["summary"]["text_replacement_count"] == 1
    assert patched.usage["patch_transaction"]["mutates_inputs"] is False
    patched_theme_xml = _read_zip_text(patched_path, "ppt/theme/theme1.xml")
    patched_slide_xml = _read_zip_text(patched_path, "ppt/slides/slide2.xml")
    assert 'name="Executive Blue"' in patched_theme_xml
    assert 'val="0B3D91"' in patched_theme_xml
    assert "Risk: Medium" in patched_slide_xml
    assert "Risk: High" in _read_zip_text(deck_path, "ppt/slides/slide2.xml")


def test_source_graph_includes_tables_formulas_charts_shapes_and_notes(tmp_path: Path) -> None:
    from agentpdf.office.context import build_office_context_packet
    from agentpdf.office.deck_writer import create_deck_presentation
    from agentpdf.office.workbook import write_sheet_workbook

    evidence_path = tmp_path / "evidence.json"
    workbook_path = tmp_path / "evidence.xlsx"
    deck_path = tmp_path / "board.pptx"
    context_path = tmp_path / "context.json"
    evidence_path.write_text(json.dumps(_evidence()), encoding="utf-8")
    assert write_sheet_workbook(evidence_path=evidence_path, output_path=workbook_path).status == "succeeded"
    assert create_deck_presentation(
        workbook_path=workbook_path,
        output_path=deck_path,
        title="Vendor Renewal Review",
    ).status == "succeeded"

    result = build_office_context_packet(
        files=[workbook_path, deck_path],
        output_path=context_path,
        title="Board packet",
        intent="Build a sourced board review.",
    )

    assert result.status == "succeeded"
    source_graph = result.usage["source_graph"]
    source_types = {node["source_type"] for node in source_graph["nodes"]}
    assert {"workbook", "sheet", "table", "chart", "deck", "slide", "shape", "speaker_note"} <= source_types
    assert any(edge["relation"] == "contains" for edge in source_graph["edges"])
    chart_node = next(node for node in source_graph["nodes"] if node["source_type"] == "chart")
    assert chart_node["locator"]["kind"] == "sheet"
    note_node = next(node for node in source_graph["nodes"] if node["source_type"] == "speaker_note")
    assert "Sources:" in note_node["text"]
    written = json.loads(context_path.read_text(encoding="utf-8"))
    assert written["source_graph"]["node_count"] == len(source_graph["nodes"])


def test_okoffice_compatibility_manifest_keeps_pdf_layer_slim() -> None:
    from okoffice.tools.registry import load_okoffice_manifest

    manifest = load_okoffice_manifest()
    compatibility_tool = next(tool for tool in manifest["compatibility_tools"] if tool["name"] == "pdf.inspect.document")

    assert manifest["compatibility_manifest"]["role"] == "legacy_compat"
    assert manifest["compatibility_manifest"]["surface"] == "slim_summary"
    assert compatibility_tool["status"] == "legacy_compat"
    assert compatibility_tool["compatibility_boundary"] == "pdf.*"
    assert "input_schema" not in compatibility_tool
    assert "output_schema" not in compatibility_tool


def _write_docx(path: Path, paragraphs: list[str]) -> None:
    body = "".join(f"<w:p><w:r><w:t>{paragraph}</w:t></w:r></w:p>" for paragraph in paragraphs)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr(
            "word/document.xml",
            (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                f"<w:body>{body}<w:sectPr/></w:body></w:document>"
            ),
        )


def _evidence() -> dict[str, object]:
    return {
        "extraction_id": "extract_test",
        "schema_name": "vendor_renewal",
        "fields": [
            {"name": "vendor", "type": "string", "aliases": ["Vendor"], "required": True},
            {"name": "renewal_date", "type": "date", "aliases": ["Renewal date"], "required": True},
            {"name": "annual_amount", "type": "number", "aliases": ["Annual amount"], "required": True},
            {"name": "risk", "type": "string", "aliases": ["Risk"], "required": False},
        ],
        "rows": [
            {
                "row_id": "row_001",
                "values": {
                    "vendor": "Acme Corp",
                    "renewal_date": "2026-09-30",
                    "annual_amount": "120000",
                    "risk": "High",
                },
                "field_evidence": {
                    "vendor": {
                        "source_ref": "ctx_001#p1",
                        "source_type": "word_paragraph",
                        "locator": {"kind": "word", "paragraph_id": "p_0001", "paragraph_index": 0},
                        "excerpt": "Vendor: Acme Corp",
                        "confidence": 0.95,
                    },
                    "renewal_date": {
                        "source_ref": "ctx_001#p1",
                        "source_type": "word_paragraph",
                        "locator": {"kind": "word", "paragraph_id": "p_0001", "paragraph_index": 0},
                        "excerpt": "Renewal date: 2026-09-30",
                        "confidence": 0.95,
                    },
                    "annual_amount": {
                        "source_ref": "ctx_001#p1",
                        "source_type": "word_paragraph",
                        "locator": {"kind": "word", "paragraph_id": "p_0001", "paragraph_index": 0},
                        "excerpt": "Annual amount: $120,000",
                        "confidence": 0.95,
                    },
                    "risk": {
                        "source_ref": "ctx_002#s1",
                        "source_type": "slide",
                        "locator": {"kind": "deck", "slide": 1, "slide_id": "256"},
                        "excerpt": "Risk: High",
                        "confidence": 0.95,
                    },
                },
            }
        ],
        "source_refs": [
            {"source_ref": "ctx_001#p1", "source_type": "word_paragraph"},
            {"source_ref": "ctx_002#s1", "source_type": "slide"},
        ],
        "method": "local_label_value_match_v0",
    }


def _read_zip_text(path: Path, member: str) -> str:
    with zipfile.ZipFile(path) as archive:
        return archive.read(member).decode("utf-8")
