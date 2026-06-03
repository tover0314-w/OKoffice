import json
import asyncio
from pathlib import Path

from PIL import Image

from agentpdf.mcp.server import (
    create_mcp_server,
    pdf_ai_parse_lite,
    pdf_ai_create_from_prompt,
    pdf_ai_create_template_preview,
    pdf_ai_create_templates,
    pdf_ai_rag_cite_answer,
    pdf_ai_rag_chat,
    pdf_ai_rag_export_report,
    pdf_ai_rag_highlight_sources,
    pdf_ai_rag_ingest,
    pdf_ai_rag_query,
    pdf_ai_rag_search,
    pdf_add_page_numbers,
    pdf_blank_page_check,
    pdf_create_markdown,
    pdf_create_text,
    pdf_extract_images,
    pdf_extract_text,
    pdf_extract_pages,
    pdf_image_to_pdf,
    pdf_inspect_document,
    pdf_inspect_pages,
    pdf_merge,
    pdf_evidence_map_sources,
    pdf_metadata_page_info,
    pdf_metadata_read,
    pdf_pdf_to_markdown,
    pdf_pdf_to_json,
    pdf_insert_blank_pages,
    pdf_optimize_compress,
    pdf_optimize_repair,
    pdf_page_count_check,
    pdf_render_pages,
    pdf_render_check,
    pdf_reorder_pages,
    pdf_security_remove_metadata,
    pdf_target_select_profile,
    pdf_validate_output,
    pdf_watermark,
    pdf_workflow_plan,
    pdf_workflow_report,
    pdf_workflow_run,
)


def test_mcp_server_exposes_local_pdf_tools() -> None:
    server = create_mcp_server()
    tool_names = {tool.name for tool in asyncio.run(server.list_tools())}

    assert "pdf_inspect_document" in tool_names
    assert "pdf_inspect_pages" in tool_names
    assert "pdf_merge" in tool_names
    assert "pdf_split" in tool_names
    assert "pdf_extract_pages" in tool_names
    assert "pdf_remove_pages" in tool_names
    assert "pdf_rotate_pages" in tool_names
    assert "pdf_reorder_pages" in tool_names
    assert "pdf_insert_blank_pages" in tool_names
    assert "pdf_optimize_compress" in tool_names
    assert "pdf_optimize_repair" in tool_names
    assert "pdf_render_pages" in tool_names
    assert "pdf_extract_images" in tool_names
    assert "pdf_extract_text" in tool_names
    assert "pdf_metadata_read" in tool_names
    assert "pdf_metadata_page_info" in tool_names
    assert "pdf_metadata_update" in tool_names
    assert "pdf_metadata_remove" in tool_names
    assert "pdf_security_remove_metadata" in tool_names
    assert "pdf_create_text" in tool_names
    assert "pdf_create_markdown" in tool_names
    assert "pdf_image_to_pdf" in tool_names
    assert "pdf_watermark" in tool_names
    assert "pdf_add_page_numbers" in tool_names
    assert "pdf_validate_output" in tool_names
    assert "pdf_page_count_check" in tool_names
    assert "pdf_render_check" in tool_names
    assert "pdf_blank_page_check" in tool_names
    assert "pdf_ai_parse_lite" in tool_names
    assert "pdf_ai_create_from_prompt" in tool_names
    assert "pdf_ai_create_template_preview" in tool_names
    assert "pdf_ai_create_templates" in tool_names
    assert "pdf_ai_create_template_packs" in tool_names
    assert "pdf_ai_create_validate_template_pack" in tool_names
    assert "pdf_ai_create_from_template_pack" in tool_names
    assert "pdf_ai_rag_ingest" in tool_names
    assert "pdf_ai_rag_cite_answer" in tool_names
    assert "pdf_ai_rag_chat" in tool_names
    assert "pdf_ai_rag_export_report" in tool_names
    assert "pdf_ai_rag_highlight_sources" in tool_names
    assert "pdf_ai_rag_query" in tool_names
    assert "pdf_ai_rag_search" in tool_names
    assert "agent_setup_claude_code" in tool_names
    assert "pdf_pdf_to_json" in tool_names
    assert "pdf_pdf_to_markdown" in tool_names
    assert "pdf_workflow_plan" in tool_names
    assert "pdf_workflow_run" in tool_names
    assert "pdf_workflow_report" in tool_names
    assert "pdf_artifacts_export_bundle" in tool_names
    assert "agentpdf_tool_manifest" in tool_names
    assert "pdf_target_select_profile" in tool_names
    assert "pdf_evidence_map_sources" in tool_names


def test_static_mcp_catalog_matches_server_tools() -> None:
    server = create_mcp_server()
    server_tool_names = {tool.name for tool in asyncio.run(server.list_tools())}
    catalog_path = Path(__file__).resolve().parents[2] / "schemas" / "mcp-tools.catalog.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    catalog_tool_names = {tool["name"] for tool in catalog["tools"]}

    assert sorted(server_tool_names - catalog_tool_names) == []
    assert sorted(catalog_tool_names - server_tool_names) == []


def test_mcp_workflow_plan_returns_agent_steps() -> None:
    payload = json.loads(
        pdf_workflow_plan("Chat with this PDF and cite the answer.", input_path="report.pdf")
    )

    assert payload["tool"] == "pdf.workflow.plan"
    assert payload["usage"]["workflow"]["steps"][0]["tool"] == "pdf.inspect.document"


def test_mcp_workflow_run_returns_step_evidence(text_pdf: Path) -> None:
    payload = json.loads(
        pdf_workflow_run(
            {
                "steps": [
                    {
                        "step_id": "inspect",
                        "tool": "pdf.inspect.document",
                        "input": {"path": str(text_pdf)},
                    }
                ]
            }
        )
    )

    assert payload["tool"] == "pdf.workflow.run"
    assert payload["usage"]["workflow_run"]["executed_steps"] == 1
    assert payload["usage"]["workflow_run"]["step_results"][0]["tool"] == "pdf.inspect.document"


def test_mcp_workflow_report_returns_audit_summary(text_pdf: Path) -> None:
    run_payload = json.loads(
        pdf_workflow_run(
            {
                "steps": [
                    {
                        "step_id": "inspect",
                        "tool": "pdf.inspect.document",
                        "input": {"path": str(text_pdf)},
                    }
                ]
            }
        )
    )

    payload = json.loads(pdf_workflow_report(run_payload))

    assert payload["tool"] == "pdf.workflow.report"
    assert payload["usage"]["workflow_report"]["executed_steps"] == 1
    assert "pdf.inspect.document" in payload["usage"]["workflow_report"]["markdown"]


def test_mcp_inspect_returns_same_tool_result_contract(simple_pdf: Path) -> None:
    payload = json.loads(pdf_inspect_document(str(simple_pdf)))

    assert payload["status"] == "succeeded"
    assert payload["tool"] == "pdf.inspect.document"
    assert payload["usage"]["page_count"] == 1


def test_mcp_inspect_pages_returns_page_facts(text_pdf: Path) -> None:
    payload = json.loads(pdf_inspect_pages(str(text_pdf), pages="1", render_check=True))

    assert payload["status"] == "succeeded"
    assert payload["tool"] == "pdf.inspect.pages"
    assert payload["usage"]["selected_pages"] == [1]
    assert payload["usage"]["pages"][0]["render"]["status"] == "passed"


def test_mcp_merge_returns_artifact(simple_pdf: Path, two_page_pdf: Path, tmp_path: Path) -> None:
    output = tmp_path / "merged.pdf"

    payload = json.loads(pdf_merge([str(simple_pdf), str(two_page_pdf)], str(output)))

    assert payload["status"] == "succeeded"
    assert payload["artifacts"][0]["page_count"] == 3


def test_mcp_render_pages_returns_image_artifact(simple_pdf: Path, tmp_path: Path) -> None:
    payload = json.loads(pdf_render_pages(str(simple_pdf), pages="1", image_format="png", out_dir=str(tmp_path)))

    assert payload["status"] == "succeeded"
    assert payload["artifacts"][0]["mime_type"] == "image/png"


def test_mcp_extract_images_returns_artifacts(tmp_path: Path) -> None:
    image = tmp_path / "source.png"
    source = tmp_path / "source.pdf"
    Image.new("RGB", (32, 24), color=(40, 120, 80)).save(image)
    _write_image_pdf(source, image)

    payload = json.loads(pdf_extract_images(str(source), pages="1", out_dir=str(tmp_path / "images")))

    assert payload["tool"] == "pdf.convert.extract_images"
    assert payload["usage"]["image_count"] == 1
    assert payload["artifacts"][0]["mime_type"] == "image/png"


def test_mcp_extract_pages_returns_artifact(two_page_pdf: Path, tmp_path: Path) -> None:
    output = tmp_path / "extract.pdf"

    payload = json.loads(pdf_extract_pages(str(two_page_pdf), pages="1", output_path=str(output)))

    assert payload["status"] == "succeeded"
    assert payload["tool"] == "pdf.organize.extract_pages"


def test_mcp_reorder_and_insert_blank_pages(two_page_pdf: Path, tmp_path: Path) -> None:
    reordered = tmp_path / "reordered.pdf"
    with_blank = tmp_path / "with-blank.pdf"

    reorder = json.loads(pdf_reorder_pages(str(two_page_pdf), order="2,1", output_path=str(reordered)))
    insert_blank = json.loads(
        pdf_insert_blank_pages(str(reordered), after_page=1, count=1, output_path=str(with_blank))
    )

    assert reorder["tool"] == "pdf.organize.reorder_pages"
    assert insert_blank["tool"] == "pdf.organize.insert_blank_pages"
    assert insert_blank["artifacts"][0]["page_count"] == 3


def test_mcp_optimize_compress_and_repair(two_page_pdf: Path, tmp_path: Path) -> None:
    compressed = tmp_path / "compressed.pdf"
    repaired = tmp_path / "repaired.pdf"

    compress = json.loads(pdf_optimize_compress(str(two_page_pdf), output_path=str(compressed)))
    repair = json.loads(pdf_optimize_repair(str(two_page_pdf), output_path=str(repaired)))

    assert compress["tool"] == "pdf.optimize.compress"
    assert repair["tool"] == "pdf.optimize.repair"
    assert compressed.exists()
    assert repaired.exists()


def test_mcp_text_and_metadata_tools(text_pdf: Path, metadata_pdf: Path) -> None:
    text = json.loads(pdf_extract_text(str(text_pdf), pages="1"))
    metadata = json.loads(pdf_metadata_read(str(metadata_pdf)))
    page_info = json.loads(pdf_metadata_page_info(str(text_pdf), pages="1"))

    assert text["tool"] == "pdf.convert.pdf_to_text"
    assert "AgentPDF local text layer" in text["usage"]["text"]
    assert metadata["usage"]["metadata"]["Title"] == "Original Title"
    assert page_info["tool"] == "pdf.metadata.page_info"
    assert page_info["usage"]["selected_pages"] == [1]


def test_mcp_target_page_count_and_security_helpers(metadata_pdf: Path, tmp_path: Path) -> None:
    selected = json.loads(pdf_target_select_profile("Create a slide deck from source notes."))
    mapped = json.loads(
        pdf_evidence_map_sources(
            blocks=[{"block_id": "blk_001", "type": "section", "source_refs": ["ctx_001"]}],
            context_packet={
                "context_packet_id": "ctxpkt_mcp",
                "items": [
                    {
                        "context_item_id": "ctx_001",
                        "source_ref": "ctx_001",
                        "type": "text",
                        "role": "source",
                        "label": "Source note",
                        "metadata": {"preview": "MCP source note"},
                        "content": {"text": "MCP source note"},
                    }
                ],
            },
        )
    )
    page_count = json.loads(pdf_page_count_check(str(metadata_pdf), expected_pages=1))
    cleaned = tmp_path / "security-clean.pdf"
    security = json.loads(pdf_security_remove_metadata(str(metadata_pdf), str(cleaned)))

    assert selected["tool"] == "pdf.target.select_profile"
    assert selected["usage"]["selected_profile_id"] == "slide_deck"
    assert mapped["tool"] == "pdf.evidence.map_sources"
    assert mapped["usage"]["source_map"][0]["source_match_status"] == "matched"
    assert page_count["tool"] == "pdf.validation.page_count_check"
    assert page_count["usage"]["actual_pages"] == 1
    assert security["tool"] == "pdf.security.remove_metadata"
    assert cleaned.exists()


def test_mcp_create_text_and_markdown(tmp_path: Path) -> None:
    text_output = tmp_path / "text.pdf"
    markdown_output = tmp_path / "markdown.pdf"

    text = json.loads(pdf_create_text("MCP created text", str(text_output)))
    markdown = json.loads(pdf_create_markdown("# MCP Report", str(markdown_output)))

    assert text["status"] == "succeeded"
    assert text["tool"] == "pdf.convert.text_to_pdf"
    assert markdown["status"] == "succeeded"
    assert markdown["tool"] == "pdf.convert.markdown_to_pdf"


def test_mcp_create_from_prompt_returns_validated_pdf(tmp_path: Path) -> None:
    output = tmp_path / "mcp-brief.pdf"

    payload = json.loads(
        pdf_ai_create_from_prompt(
            "Create a worksheet about validating generated PDFs.",
            str(output),
            template="worksheet",
            style_pack="paper_ink",
            colors={"primary": "#4f46e5"},
            data={
                "audience": "agent builders",
                "sections": [
                    {
                        "heading": "Check the output",
                        "body": "Renderability and page count should be inspected.",
                    }
                ],
            },
        )
    )

    assert payload["status"] == "succeeded"
    assert payload["tool"] == "pdf.ai.create.from_prompt"
    assert payload["usage"]["template_id"] == "worksheet"
    assert payload["usage"]["colors"]["primary"] == "#4f46e5"
    assert payload["validation"]["status"] == "passed"
    assert output.exists()


def test_mcp_create_templates_returns_catalog() -> None:
    payload = json.loads(pdf_ai_create_templates())

    assert payload["tool"] == "pdf.ai.create.templates"
    assert "worksheet" in payload["usage"]["templates"]
    assert "paper_ink" in payload["usage"]["style_packs"]
    assert payload["usage"]["templates"]["invoice"]["preview_tool"] == "pdf.ai.create.template_preview"


def test_mcp_create_template_preview_generates_pdf(tmp_path: Path) -> None:
    output = tmp_path / "mcp-preview.pdf"

    payload = json.loads(pdf_ai_create_template_preview("invoice", str(output)))

    assert payload["tool"] == "pdf.ai.create.template_preview"
    assert payload["usage"]["template_id"] == "invoice"
    assert payload["usage"]["data_source"] == "template_sample_data"
    assert payload["validation"]["status"] == "passed"
    assert output.exists()


def test_mcp_image_watermark_page_numbers_and_validate(tmp_path: Path) -> None:
    image = tmp_path / "cover.png"
    image_pdf = tmp_path / "cover.pdf"
    watermarked = tmp_path / "watermarked.pdf"
    numbered = tmp_path / "numbered.pdf"
    Image.new("RGB", (120, 80), color=(120, 40, 80)).save(image)

    image_result = json.loads(pdf_image_to_pdf([str(image)], str(image_pdf)))
    watermark = json.loads(pdf_watermark(str(image_pdf), "CONFIDENTIAL", str(watermarked)))
    page_numbers = json.loads(pdf_add_page_numbers(str(watermarked), str(numbered)))
    validate = json.loads(pdf_validate_output(str(numbered), expected_pages=1))
    render_check = json.loads(pdf_render_check(str(numbered), pages="1"))
    blank_check = json.loads(pdf_blank_page_check(str(numbered), pages="1"))

    assert image_result["tool"] == "pdf.convert.image_to_pdf"
    assert watermark["tool"] == "pdf.edit.watermark"
    assert page_numbers["tool"] == "pdf.edit.page_numbers"
    assert validate["status"] == "succeeded"
    assert render_check["tool"] == "pdf.validation.render_check"
    assert blank_check["tool"] == "pdf.validation.blank_page_check"


def test_mcp_parse_lite_and_local_rag(tmp_path: Path) -> None:
    source = tmp_path / "rag.pdf"
    index = tmp_path / "rag.index.json"
    ir_json = tmp_path / "rag.ir.json"
    ir_markdown = tmp_path / "rag.md"
    pdf_create_markdown("# AgentPDF\n\nLocal RAG gives agents cited document evidence.", str(source))

    parsed = json.loads(pdf_ai_parse_lite(str(source)))
    exported = json.loads(pdf_pdf_to_json(str(source), str(ir_json)))
    markdown = json.loads(pdf_pdf_to_markdown(str(source), str(ir_markdown)))
    ingest = json.loads(pdf_ai_rag_ingest(str(source), str(index), max_chars=80))
    query = json.loads(pdf_ai_rag_query(str(index), "What gives cited evidence?"))
    search = json.loads(pdf_ai_rag_search(str(index), "cited evidence"))
    cite = json.loads(pdf_ai_rag_cite_answer(str(index), "Local RAG gives cited document evidence."))
    highlighted = tmp_path / "rag-highlighted.pdf"
    report = tmp_path / "rag-report.pdf"
    chat_report = tmp_path / "rag-chat-report.pdf"
    chat_highlighted = tmp_path / "rag-chat-highlighted.pdf"
    highlight = json.loads(
        pdf_ai_rag_highlight_sources(
            str(index),
            output_path=str(highlighted),
            answer="Local RAG gives cited document evidence.",
        )
    )
    exported_report = json.loads(
        pdf_ai_rag_export_report(
            str(index),
            output_path=str(report),
            question="What gives cited evidence?",
            answer="Local RAG gives cited document evidence.",
        )
    )
    chat = json.loads(
        pdf_ai_rag_chat(
            str(source),
            question="What gives cited evidence?",
            index_path=str(tmp_path / "rag-chat.index.json"),
            report_output_path=str(chat_report),
            highlight_output_path=str(chat_highlighted),
        )
    )

    assert parsed["tool"] == "pdf.ai.parse.lite"
    assert exported["tool"] == "pdf.convert.pdf_to_json"
    assert markdown["tool"] == "pdf.convert.pdf_to_markdown"
    assert ingest["tool"] == "pdf.ai.rag.ingest"
    assert query["tool"] == "pdf.ai.rag.query"
    assert cite["tool"] == "pdf.ai.rag.cite_answer"
    assert chat["tool"] == "pdf.ai.rag.chat"
    assert chat["usage"]["citation_count"] >= 1
    assert exported_report["tool"] == "pdf.ai.rag.export_report"
    assert highlight["tool"] == "pdf.ai.rag.highlight_sources"
    assert highlighted.exists()
    assert report.exists()
    assert chat_report.exists()
    assert chat_highlighted.exists()
    assert query["usage"]["citations"][0]["page_number"] == 1
    assert cite["usage"]["citations"][0]["page_number"] == 1
    assert search["usage"]["matches"][0]["page_number"] == 1


def _write_image_pdf(path: Path, image_path: Path) -> None:
    from reportlab.pdfgen import canvas

    document = canvas.Canvas(str(path), pagesize=(200, 200))
    document.drawImage(str(image_path), 24, 120, width=32, height=24)
    document.showPage()
    document.save()
