import json
from pathlib import Path

from fastapi.testclient import TestClient
from typer.testing import CliRunner


def test_extract_schema_matches_context_packet_sources(tmp_path: Path) -> None:
    from okoffice.office.extract import extract_schema

    output_path = tmp_path / "evidence.json"

    result = extract_schema(_context_packet(), _schema(), output_path=output_path)

    assert result.status == "succeeded"
    assert result.tool == "office.extract.schema"
    assert result.validation is not None
    assert result.validation.status == "passed"
    assert result.warnings == []
    assert result.artifacts[0].path == output_path.resolve()

    evidence = result.usage["evidence"]
    assert evidence["context_packet_id"] == "ctxpkt_test"
    assert evidence["source_graph_id"] == "srcgraph_test"
    assert evidence["missing_fields"] == []
    assert evidence["coverage"] == {"matched": 3, "total": 3, "ratio": 1.0}
    assert [record["field"] for record in evidence["records"]] == ["vendor", "renewal_date", "risk"]
    assert evidence["records"][0]["value"] == "Acme Corp"
    assert evidence["records"][0]["source_ref"] == "ctx_001:docx:paragraph:1"
    assert evidence["records"][2]["match_source"] == "source_graph.nodes[2].evidence_text"
    assert "sheet.create.evidence_workbook" in result.next_recommended_tools
    assert json.loads(output_path.read_text(encoding="utf-8")) == evidence


def test_extract_schema_loads_json_path_and_warns_for_missing_fields(tmp_path: Path) -> None:
    from okoffice.office.extract import extract_schema

    context_path = tmp_path / "context.json"
    context_path.write_text(json.dumps(_context_packet()), encoding="utf-8")
    schema = {"fields": [{"name": "vendor", "type": "string"}, {"name": "termination_fee", "type": "number"}]}

    result = extract_schema(context_path, schema)

    assert result.status == "succeeded"
    assert result.validation is not None
    assert result.validation.status == "warning"
    assert result.warnings == ["Missing evidence for fields: termination_fee."]
    assert result.usage["evidence"]["missing_fields"] == ["termination_fee"]
    assert result.usage["evidence"]["coverage"] == {"matched": 1, "total": 2, "ratio": 0.5}


def test_extract_schema_runs_through_agent_interfaces(tmp_path: Path) -> None:
    from okoffice.api.app import create_app
    from okoffice.mcp.server import office_extract_schema
    from okoffice.tools.runner import run_office_extract_schema
    from okoffice.workflows.runner import run_workflow
    from okoffice.cli_okoffice.main import app

    context_path = tmp_path / "context.json"
    schema_path = tmp_path / "schema.json"
    runner_output = tmp_path / "runner-evidence.json"
    api_output = tmp_path / "api-evidence.json"
    mcp_output = tmp_path / "mcp-evidence.json"
    workflow_output = tmp_path / "workflow-evidence.json"
    cli_output = tmp_path / "cli-evidence.json"
    context_path.write_text(json.dumps(_context_packet()), encoding="utf-8")
    schema_path.write_text(json.dumps(_schema()), encoding="utf-8")

    runner_result = run_office_extract_schema(context_path, _schema(), runner_output)
    response = TestClient(create_app()).post(
        "/v1/tools/office.extract.schema/run",
        json={"context_packet_path": str(context_path), "schema": _schema(), "output_path": str(api_output)},
    )
    mcp_payload = json.loads(office_extract_schema(str(context_path), _schema(), str(mcp_output)))
    workflow = run_workflow(
        {
            "steps": [
                {
                    "tool": "office.extract.schema",
                    "input": {
                        "context_packet_path": str(context_path),
                        "schema": _schema(),
                        "output_path": str(workflow_output),
                    },
                }
            ]
        }
    )
    cli_result = CliRunner().invoke(
        app,
        [
            "extract",
            "schema",
            str(context_path),
            "--schema",
            str(schema_path),
            "--output",
            str(cli_output),
            "--json",
        ],
    )

    assert runner_result.status == "succeeded"
    assert runner_output.exists()
    assert response.status_code == 200
    assert response.json()["status"] == "succeeded"
    assert api_output.exists()
    assert mcp_payload["status"] == "succeeded"
    assert mcp_output.exists()
    assert workflow.status == "succeeded"
    assert workflow_output.exists()
    assert cli_result.exit_code == 0
    assert json.loads(cli_result.stdout)["tool"] == "office.extract.schema"
    assert cli_output.exists()


def test_extract_schema_manifest_and_mcp_catalog_mark_tool_beta() -> None:
    from okoffice.tools.registry_okoffice import load_okoffice_manifest

    manifest = load_okoffice_manifest()
    target_tools = {tool["name"]: tool for tool in manifest["target_tools"]}
    assert target_tools["office.extract.schema"]["status"] == "beta"
    assert target_tools["office.extract.schema"]["implemented"] is True

    catalog = json.loads(Path("schemas/mcp-tools.catalog.json").read_text(encoding="utf-8"))
    catalog_tools = {tool["name"]: tool for tool in catalog["tools"]}
    assert catalog_tools["office_extract_schema"]["maps_to"] == "office.extract.schema"


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
                "source_ref": "ctx_001:file",
                "label": "memo.docx",
                "content": {"text": "Vendor: Acme Corp\nRenewal date: 2026-09-30"},
            }
        ],
        "source_graph": {
            "source_graph_id": "srcgraph_test",
            "nodes": [
                {
                    "node_id": "src_001_docx",
                    "type": "word.document",
                    "source_ref": "ctx_001:docx",
                    "label": "memo.docx",
                    "evidence": {"text": "Vendor: Acme Corp\nRenewal date: 2026-09-30"},
                    "locators": [{"kind": "word_document", "path": "memo.docx"}],
                },
                {
                    "node_id": "src_001_para_1",
                    "type": "word.paragraph",
                    "source_ref": "ctx_001:docx:paragraph:1",
                    "text": "Vendor: Acme Corp\nRenewal date: 2026-09-30",
                    "locators": [{"kind": "word_paragraph", "path": "memo.docx", "paragraph_index": 1}],
                },
                {
                    "node_id": "src_001_deck_slide_1",
                    "type": "deck.slide",
                    "source_ref": "ctx_002:pptx:slide:1",
                    "evidence_text": "Risk: High",
                    "locators": [{"kind": "deck_slide", "path": "deck.pptx", "slide_index": 1}],
                },
            ],
            "edges": [],
        },
    }
