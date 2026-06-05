import json
from pathlib import Path


def test_native_locators_round_trip_with_discriminated_kinds() -> None:
    from agentpdf.office.ir import (
        DeckLocator,
        PdfLocator,
        SheetLocator,
        SourceGraph,
        SourceGraphNode,
        WordLocator,
    )

    graph = SourceGraph(
        source_graph_id="sg_demo",
        nodes=[
            SourceGraphNode(
                source_id="src_docx_001_p_012",
                source_type="word_paragraph",
                parent_source_id="src_docx_001",
                locator=WordLocator(section=1, paragraph_id="p_0012", paragraph_index=12, run_index=2),
                text="Renewal risk is concentrated in enterprise accounts.",
                confidence=0.93,
            ),
            SourceGraphNode(
                source_id="src_xlsx_001_range_revenue",
                source_type="sheet_range",
                parent_source_id="src_xlsx_001",
                locator=SheetLocator(sheet="Revenue", range="B4:F18", row=8, column="D"),
                confidence=1.0,
            ),
            SourceGraphNode(
                source_id="src_pptx_001_shape_12",
                source_type="shape",
                parent_source_id="src_pptx_001_slide_007",
                locator=DeckLocator(slide=7, shape_id="shape_12", bbox=[1.5, 4.0, 14.2, 6.8], unit="cm"),
            ),
            SourceGraphNode(
                source_id="src_pdf_001_page_005_bbox",
                source_type="pdf_block",
                parent_source_id="src_pdf_001_page_005",
                locator=PdfLocator(page=5, bbox=[72, 144, 520, 210]),
                confidence=0.88,
            ),
        ],
    )

    payload = graph.model_dump(mode="json")
    assert payload["nodes"][0]["locator"]["kind"] == "word"
    assert payload["nodes"][1]["locator"]["kind"] == "sheet"
    assert payload["nodes"][2]["locator"]["kind"] == "deck"
    assert payload["nodes"][3]["locator"]["kind"] == "pdf"

    restored = SourceGraph.model_validate_json(graph.model_dump_json())
    assert restored.nodes[0].locator.kind == "word"
    assert restored.nodes[1].locator.kind == "sheet"
    assert restored.nodes[2].locator.kind == "deck"
    assert restored.nodes[3].locator.kind == "pdf"


def test_office_ir_serializes_source_refs_for_workbook_formula() -> None:
    from agentpdf.office.ir import OfficeIR, SheetLocator, SourceRef

    ir = OfficeIR(
        ir_version="0.3",
        document_id="doc_metrics",
        artifact_kind="workbook",
        source={"source_id": "src_xlsx_001", "filename": "metrics.xlsx", "sha256": "abc123"},
        metadata={"title": "Q1 Metrics", "sheet_count": 1, "has_macros": False},
        sheets=[
            {
                "name": "Revenue",
                "used_range": "A1:F40",
                "formulas": [
                    {
                        "cell": "F12",
                        "formula": "SUM(B12:E12)",
                        "cached_value": 1250000,
                        "source_ref": SourceRef(
                            source_id="src_xlsx_001",
                            locator=SheetLocator(sheet="Revenue", cell="F12", formula="SUM(B12:E12)"),
                        ),
                    }
                ],
            }
        ],
    )

    payload = ir.model_dump(mode="json")
    assert payload["artifact_kind"] == "workbook"
    assert payload["sheets"][0]["formulas"][0]["source_ref"]["locator"]["kind"] == "sheet"
    assert payload["sheets"][0]["formulas"][0]["source_ref"]["locator"]["cell"] == "F12"


def test_source_graph_and_office_ir_examples_validate() -> None:
    from agentpdf.office.ir import OfficeIR, SourceGraph

    source_graph = json.loads(Path("examples/ir/okoffice-source-graph.json").read_text(encoding="utf-8"))
    workbook_ir = json.loads(Path("examples/ir/workbook-office-ir.json").read_text(encoding="utf-8"))

    assert SourceGraph.model_validate(source_graph).source_graph_id == "sg_okoffice_demo"
    assert OfficeIR.model_validate(workbook_ir).artifact_kind == "workbook"
