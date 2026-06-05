import json
from pathlib import Path


def test_extract_schema_matches_context_packet_sources(tmp_path: Path) -> None:
    from agentpdf.office.extract import extract_schema

    output_path = tmp_path / "evidence.json"

    result = extract_schema(
        _context_packet(),
        _schema(),
        output_path=output_path,
    )

    assert result.status == "succeeded"
    assert result.tool == "office.extract.schema"
    assert result.validation is not None
    assert result.validation.status == "passed"
    assert result.warnings == []
    assert result.artifacts[0].path == output_path.resolve()

    evidence = result.usage["evidence"]
    assert evidence["context_packet_id"] == "ctxpkt_test"
    assert evidence["source_graph_id"] == "srcgraph_test"
    assert evidence["fields"] == _schema()["fields"]
    assert evidence["missing_fields"] == []
    assert evidence["coverage"] == {"matched": 3, "total": 3, "ratio": 1.0}
    assert evidence["records"] == [
        {
            "field": "vendor",
            "type": "string",
            "value": "Acme Corp",
            "source_ref": "ctx_001#p1",
            "source_id": "src_002",
            "locator": {"kind": "word", "paragraph_id": "p_0001", "paragraph_index": 0},
            "matched_text": "Vendor: Acme Corp",
            "match_source": "source_graph.nodes[1].text",
            "confidence": 0.9,
        },
        {
            "field": "renewal_date",
            "type": "date",
            "value": "2026-09-30",
            "source_ref": "ctx_001#p1",
            "source_id": "src_002",
            "locator": {"kind": "word", "paragraph_id": "p_0001", "paragraph_index": 0},
            "matched_text": "Renewal date: 2026-09-30",
            "match_source": "source_graph.nodes[1].text",
            "confidence": 0.9,
        },
        {
            "field": "risk",
            "type": "string",
            "value": "High",
            "source_ref": "ctx_002#s1",
            "source_id": "src_004",
            "locator": {"kind": "deck", "slide": 1, "slide_id": "256"},
            "matched_text": "Risk: High",
            "match_source": "source_graph.nodes[3].evidence_text",
            "confidence": 0.9,
        },
    ]

    assert json.loads(output_path.read_text(encoding="utf-8")) == evidence


def test_extract_schema_loads_json_path_and_warns_for_missing_fields(tmp_path: Path) -> None:
    from agentpdf.office.extract import extract_schema

    context_path = tmp_path / "context.json"
    context_path.write_text(json.dumps(_context_packet()), encoding="utf-8")
    schema = {"fields": [{"name": "vendor", "type": "string"}, {"name": "termination_fee", "type": "number"}]}

    result = extract_schema(context_path, schema)

    assert result.status == "succeeded"
    assert result.validation is not None
    assert result.validation.status == "warning"
    assert result.warnings == ["Missing evidence for fields: termination_fee."]

    evidence = result.usage["evidence"]
    assert evidence["context_packet_id"] == "ctxpkt_test"
    assert evidence["source_graph_id"] == "srcgraph_test"
    assert evidence["records"][0]["field"] == "vendor"
    assert evidence["missing_fields"] == ["termination_fee"]
    assert evidence["coverage"] == {"matched": 1, "total": 2, "ratio": 0.5}


def _schema() -> dict[str, object]:
    return {
        "fields": [
            {"name": "vendor", "type": "string"},
            {"name": "renewal_date", "type": "date"},
            {"name": "risk", "type": "string"},
        ],
    }


def _context_packet() -> dict[str, object]:
    return {
        "context_packet_id": "ctxpkt_test",
        "items": [
            {
                "context_item_id": "ctx_001",
                "source_ref": "ctx_001",
                "label": "memo.docx",
                "file_name": "memo.docx",
            },
            {
                "context_item_id": "ctx_002",
                "source_ref": "ctx_002",
                "label": "board-risk-review.pptx",
                "file_name": "board-risk-review.pptx",
            },
        ],
        "source_graph": {
            "source_graph_id": "srcgraph_test",
            "nodes": [
                {
                    "source_id": "src_001",
                    "source_type": "word_document",
                    "source_ref": "ctx_001",
                    "label": "memo.docx",
                },
                {
                    "source_id": "src_002",
                    "parent_source_id": "src_001",
                    "source_type": "word_paragraph",
                    "source_ref": "ctx_001#p1",
                    "text": "Vendor: Acme Corp\nRenewal date: 2026-09-30\nAnnual amount: $120,000",
                    "locator": {"kind": "word", "paragraph_id": "p_0001", "paragraph_index": 0},
                },
                {
                    "source_id": "src_003",
                    "source_type": "deck",
                    "source_ref": "ctx_002",
                    "label": "board-risk-review.pptx",
                },
                {
                    "source_id": "src_004",
                    "parent_source_id": "src_003",
                    "source_type": "slide",
                    "source_ref": "ctx_002#s1",
                    "evidence_text": "Risk: High",
                    "locator": {"kind": "deck", "slide": 1, "slide_id": "256"},
                },
            ],
            "edges": [],
        },
    }
