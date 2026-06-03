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
    pdf_authoring_plan,
    pdf_add_page_numbers,
    pdf_add_margin,
    pdf_add_shape,
    pdf_blank_page_check,
    pdf_context_image_analyze,
    pdf_create_html_package,
    pdf_create_markdown,
    pdf_create_text,
    pdf_design_tokens,
    pdf_extract_images,
    pdf_extract_fonts,
    pdf_extract_text,
    pdf_extract_pages,
    pdf_freehand_draw,
    pdf_image_to_pdf,
    pdf_inspect_document,
    pdf_inspect_pages,
    pdf_booklet,
    pdf_merge,
    pdf_n_up,
    pdf_evidence_cite_claims,
    pdf_evidence_map_sources,
    pdf_metadata_page_info,
    pdf_metadata_read,
    pdf_metadata_update_outline,
    pdf_ocr,
    pdf_ocr_searchable_pdf,
    pdf_pdf_to_markdown,
    pdf_pdf_to_json,
    pdf_insert_blank_pages,
    pdf_optimize_compress,
    pdf_optimize_remove_unused_objects,
    pdf_optimize_repair,
    pdf_optimize_validate_pdfa,
    pdf_page_count_check,
    pdf_render_pages,
    pdf_render_check,
    pdf_research_evidence_cards,
    pdf_research_plan,
    pdf_research_source_cards,
    pdf_pages_revise,
    pdf_reorder_pages,
    pdf_resize_pages,
    pdf_security_remove_metadata,
    pdf_strikeout,
    pdf_target_select_profile,
    pdf_underlay,
    pdf_underline,
    pdf_validate_output,
    pdf_watermark,
    pdf_workflow_plan,
    pdf_workflow_createpdf,
    pdf_workflow_research_deck,
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
    assert "pdf_optimize_remove_unused_objects" in tool_names
    assert "pdf_optimize_validate_pdfa" in tool_names
    assert "pdf_render_pages" in tool_names
    assert "pdf_extract_images" in tool_names
    assert "pdf_extract_fonts" in tool_names
    assert "pdf_extract_text" in tool_names
    assert "pdf_render_html_package" in tool_names
    assert "pdf_metadata_read" in tool_names
    assert "pdf_metadata_page_info" in tool_names
    assert "pdf_metadata_update" in tool_names
    assert "pdf_metadata_remove" in tool_names
    assert "pdf_security_remove_metadata" in tool_names
    assert "pdf_create_text" in tool_names
    assert "pdf_create_markdown" in tool_names
    assert "pdf_image_to_pdf" in tool_names
    assert "pdf_context_image_analyze" in tool_names
    assert "pdf_ocr" in tool_names
    assert "pdf_ocr_searchable_pdf" in tool_names
    assert "pdf_watermark" in tool_names
    assert "pdf_add_page_numbers" in tool_names
    assert "pdf_add_shape" in tool_names
    assert "pdf_underline" in tool_names
    assert "pdf_strikeout" in tool_names
    assert "pdf_freehand_draw" in tool_names
    assert "pdf_resize_pages" in tool_names
    assert "pdf_add_margin" in tool_names
    assert "pdf_underlay" in tool_names
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
    assert "pdf_workflow_createpdf" in tool_names
    assert "pdf_workflow_run" in tool_names
    assert "pdf_workflow_report" in tool_names
    assert "pdf_authoring_plan" in tool_names
    assert "pdf_storyboard_plan" in tool_names
    assert "pdf_pages_write" in tool_names
    assert "pdf_create_html_package" in tool_names
    assert "pdf_qa_visual_report" in tool_names
    assert "pdf_workflow_research_deck" in tool_names
    assert "pdf_artifacts_export_bundle" in tool_names
    assert "agentpdf_tool_manifest" in tool_names
    assert "pdf_target_select_profile" in tool_names
    assert "pdf_evidence_map_sources" in tool_names
    assert "pdf_evidence_cite_claims" in tool_names


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


def test_mcp_authoring_tools_are_exposed() -> None:
    server = create_mcp_server()
    tool_names = {tool.name for tool in asyncio.run(server.list_tools())}

    assert {
        "pdf_authoring_plan",
        "pdf_storyboard_plan",
        "pdf_pages_write",
        "pdf_create_html_package",
        "pdf_qa_visual_report",
        "pdf_workflow_research_deck",
        "pdf_research_plan",
        "pdf_research_source_cards",
        "pdf_research_evidence_cards",
        "pdf_design_tokens",
        "pdf_pages_revise",
    }.issubset(tool_names)


def test_mcp_authoring_plan_returns_route() -> None:
    payload = json.loads(pdf_authoring_plan(_authoring_brief()))

    assert payload["tool"] == "pdf.authoring.plan"
    assert payload["usage"]["authoring_plan"]["recommended_authoring_format"] == "html"
    assert payload["next_recommended_tools"] == ["pdf.storyboard.plan"]


def test_mcp_local_research_design_and_pages_revise() -> None:
    brief = _authoring_brief()
    source_payload = [
        {
            "title": "State of Mobile 2026",
            "source_type": "report",
            "summary": "Revenue growth continues while downloads flatten.",
            "key_points": ["Revenue growth continues while downloads flatten."],
        }
    ]
    research = json.loads(pdf_research_plan(brief))
    sources = json.loads(pdf_research_source_cards(brief=brief, sources=source_payload))
    evidence = json.loads(pdf_research_evidence_cards(source_cards=sources["usage"]["source_cards"]))
    design = json.loads(pdf_design_tokens(theme="consulting", overrides={"primary_color": "#123456"}))
    revised = json.loads(
        pdf_pages_revise(
            page_document={
                "page_document_id": "pages_test",
                "page_count": 1,
                "pages": [{"page_number": 1, "layout": "cover", "title": "Old title"}],
            },
            revisions=[{"page_number": 1, "title": "New title"}],
        )
    )

    assert research["tool"] == "pdf.research.plan"
    assert research["usage"]["research_plan"]["requires_network"] is False
    assert sources["tool"] == "pdf.research.source_cards"
    assert sources["usage"]["source_cards"][0]["fetch_status"] == "not_fetched"
    assert evidence["tool"] == "pdf.research.evidence_cards"
    assert evidence["usage"]["evidence_cards"][0]["source_title"] == "State of Mobile 2026"
    assert design["tool"] == "pdf.design.tokens"
    assert design["usage"]["design_tokens"]["primary_color"] == "#123456"
    assert revised["tool"] == "pdf.pages.revise"
    assert revised["usage"]["page_document"]["pages"][0]["title"] == "New title"


def test_mcp_workflow_research_deck_returns_steps() -> None:
    payload = json.loads(
        pdf_workflow_research_deck(
            _authoring_brief(),
            evidence_cards=_evidence_cards(),
            html_output_path="deck.html",
            pdf_output_path="deck.pdf",
        )
    )

    assert payload["tool"] == "pdf.workflow.research_deck"
    assert [step["tool"] for step in payload["usage"]["workflow"]["steps"]] == [
        "pdf.authoring.plan",
        "pdf.storyboard.plan",
        "pdf.pages.write",
        "pdf.create.html_package",
        "pdf.render.html_package",
        "pdf.qa.visual_report",
    ]


def test_mcp_workflow_createpdf_generates_audited_pdf(tmp_path: Path) -> None:
    pdf_output = tmp_path / "mcp-createpdf.pdf"
    payload = json.loads(
        pdf_workflow_createpdf(
            pdf_output_path=str(pdf_output),
            html_output_path=str(tmp_path / "mcp-createpdf.html"),
            html="<main><h1>CreatePDF</h1><p>MCP workflow creates audit artifacts.</p></main>",
            artifact_dir=str(tmp_path / "audit"),
        )
    )

    assert payload["tool"] == "pdf.workflow.createpdf"
    assert pdf_output.exists()
    assert Path(payload["usage"]["createpdf"]["qa_report_path"]).exists()


def test_mcp_create_html_package_accepts_raw_html(tmp_path: Path) -> None:
    output = tmp_path / "raw.html"

    payload = json.loads(
        pdf_create_html_package(
            page_document=None,
            html_output_path=str(output),
            title="Raw HTML",
            html="<main><h1>Raw HTML</h1><p>MCP creation keeps the source package.</p></main>",
        )
    )

    assert payload["tool"] == "pdf.create.html_package"
    assert payload["usage"]["source_format"] == "raw_html"
    assert output.exists()


def test_mcp_workflow_research_deck_execute_mode(tmp_path: Path) -> None:
    payload = json.loads(
        pdf_workflow_research_deck(
            _authoring_brief(),
            evidence_cards=_evidence_cards(),
            html_output_path=str(tmp_path / "deck.html"),
            pdf_output_path=str(tmp_path / "deck.pdf"),
            artifact_dir=str(tmp_path / "workflow-artifacts"),
            execute=True,
        )
    )

    run = payload["usage"]["workflow_run"]
    assert payload["tool"] == "pdf.workflow.research_deck"
    assert run["executed_steps"] == 6
    assert Path(run["bindings"]["<final.pdf>"]).exists()


def test_mcp_authoring_plan_and_research_deck_workflow() -> None:
    brief = {
        "topic": "Independent developers going global",
        "goal": "Create a concise strategy deck",
        "audience": "founders",
        "page_count": 4,
        "deliverable": "deck",
    }

    plan_payload = json.loads(pdf_authoring_plan(brief))
    workflow_payload = json.loads(
        pdf_workflow_research_deck(
            brief,
            evidence_cards=[
                {
                    "id": "ev_market",
                    "claim": "Mobile monetization remains strong.",
                    "evidence": "Revenue growth continues while downloads flatten.",
                    "source_title": "State of Mobile 2026",
                }
            ],
            html_output_path="deck.html",
            pdf_output_path="deck.pdf",
        )
    )

    assert plan_payload["tool"] == "pdf.authoring.plan"
    assert plan_payload["usage"]["authoring_plan"]["recommended_authoring_format"] == "html"
    assert workflow_payload["tool"] == "pdf.workflow.research_deck"
    assert workflow_payload["usage"]["workflow"]["steps"][0]["tool"] == "pdf.authoring.plan"


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


def test_mcp_n_up_and_booklet_return_artifacts(two_page_pdf: Path, tmp_path: Path) -> None:
    n_up = json.loads(pdf_n_up(str(two_page_pdf), str(tmp_path / "n-up.pdf"), per_sheet=2))
    booklet = json.loads(pdf_booklet(str(two_page_pdf), str(tmp_path / "booklet.pdf")))

    assert n_up["tool"] == "pdf.organize.n_up"
    assert n_up["artifacts"][0]["page_count"] == 1
    assert booklet["tool"] == "pdf.organize.booklet"
    assert booklet["usage"]["padded_page_count"] == 4


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


def test_mcp_ocr_returns_regions(monkeypatch, tmp_path: Path) -> None:
    image = tmp_path / "scan.png"
    output = tmp_path / "searchable.pdf"
    image_pdf = tmp_path / "scan.pdf"
    Image.new("RGB", (160, 80), color=(255, 255, 255)).save(image)
    _write_image_pdf(image_pdf, image)
    monkeypatch.setattr("agentpdf.ocr_scan.local._run_tesseract_tsv", _fake_tesseract_tsv)

    ocr_payload = json.loads(pdf_ocr(str(image), languages=["eng"]))
    searchable_payload = json.loads(
        pdf_ocr_searchable_pdf(str(image_pdf), str(output), languages=["eng"])
    )

    assert ocr_payload["tool"] == "pdf.ocr_scan.ocr"
    assert ocr_payload["usage"]["text"] == "Hello OCR"
    assert searchable_payload["tool"] == "pdf.ocr_scan.searchable_pdf"
    assert searchable_payload["status"] == "succeeded"
    assert output.exists()


def test_mcp_image_analyze_returns_ocr_evidence(monkeypatch, tmp_path: Path) -> None:
    image = tmp_path / "scan.png"
    Image.new("RGB", (160, 80), color=(255, 255, 255)).save(image)
    monkeypatch.setattr("agentpdf.ocr_scan.local._run_tesseract_tsv", _fake_tesseract_tsv)

    payload = json.loads(pdf_context_image_analyze(str(image), languages=["eng"]))

    assert payload["tool"] == "pdf.context.image_analyze"
    assert payload["usage"]["image"]["height"] == 80
    assert payload["usage"]["ocr"]["text"] == "Hello OCR"


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
    optimized = tmp_path / "optimized.pdf"

    compress = json.loads(pdf_optimize_compress(str(two_page_pdf), output_path=str(compressed)))
    repair = json.loads(pdf_optimize_repair(str(two_page_pdf), output_path=str(repaired)))
    remove_unused = json.loads(
        pdf_optimize_remove_unused_objects(str(two_page_pdf), output_path=str(optimized))
    )
    validate_pdfa = json.loads(pdf_optimize_validate_pdfa(str(two_page_pdf)))

    assert compress["tool"] == "pdf.optimize.compress"
    assert repair["tool"] == "pdf.optimize.repair"
    assert remove_unused["tool"] == "pdf.optimize.remove_unused_objects"
    assert validate_pdfa["tool"] == "pdf.optimize.validate_pdfa"
    assert compressed.exists()
    assert repaired.exists()
    assert optimized.exists()


def test_mcp_text_and_metadata_tools(text_pdf: Path, metadata_pdf: Path) -> None:
    text = json.loads(pdf_extract_text(str(text_pdf), pages="1"))
    fonts = json.loads(pdf_extract_fonts(str(text_pdf), pages="1"))
    metadata = json.loads(pdf_metadata_read(str(metadata_pdf)))
    page_info = json.loads(pdf_metadata_page_info(str(text_pdf), pages="1"))
    outlined = json.loads(
        pdf_metadata_update_outline(
            str(metadata_pdf),
            outline=[{"title": "Page One", "page": 1}],
            output_path=str(metadata_pdf.parent / "mcp-outlined.pdf"),
        )
    )

    assert text["tool"] == "pdf.convert.pdf_to_text"
    assert "AgentPDF local text layer" in text["usage"]["text"]
    assert fonts["tool"] == "pdf.convert.extract_fonts"
    assert metadata["usage"]["metadata"]["Title"] == "Original Title"
    assert page_info["tool"] == "pdf.metadata.page_info"
    assert page_info["usage"]["selected_pages"] == [1]
    assert outlined["tool"] == "pdf.metadata.update_outline"


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
    cited = json.loads(
        pdf_evidence_cite_claims(
            claims=[
                {
                    "claim_id": "claim_mcp",
                    "text": "MCP source note is cited.",
                    "source_refs": ["ctx_001"],
                }
            ],
            source_map=mapped["usage"]["source_map"],
        )
    )
    page_count = json.loads(pdf_page_count_check(str(metadata_pdf), expected_pages=1))
    cleaned = tmp_path / "security-clean.pdf"
    security = json.loads(pdf_security_remove_metadata(str(metadata_pdf), str(cleaned)))

    assert selected["tool"] == "pdf.target.select_profile"
    assert selected["usage"]["selected_profile_id"] == "slide_deck"
    assert mapped["tool"] == "pdf.evidence.map_sources"
    assert mapped["usage"]["source_map"][0]["source_match_status"] == "matched"
    assert cited["tool"] == "pdf.evidence.cite_claims"
    assert cited["usage"]["citations"][0]["source_ref"] == "ctx_001"
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
    shaped = tmp_path / "shaped.pdf"
    underlined = tmp_path / "underlined.pdf"
    struck = tmp_path / "struck.pdf"
    drawn = tmp_path / "drawn.pdf"
    resized = tmp_path / "resized.pdf"
    margined = tmp_path / "margined.pdf"
    underlaid = tmp_path / "underlaid.pdf"
    Image.new("RGB", (120, 80), color=(120, 40, 80)).save(image)

    image_result = json.loads(pdf_image_to_pdf([str(image)], str(image_pdf)))
    watermark = json.loads(pdf_watermark(str(image_pdf), "CONFIDENTIAL", str(watermarked)))
    page_numbers = json.loads(pdf_add_page_numbers(str(watermarked), str(numbered)))
    shape = json.loads(
        pdf_add_shape(
            str(numbered),
            str(shaped),
            shape="rectangle",
            page=1,
            x=12,
            y=12,
            width=48,
            height=32,
        )
    )
    underline = json.loads(
        pdf_underline(str(shaped), str(underlined), page=1, bbox=[10, 10, 80, 24])
    )
    strikeout = json.loads(
        pdf_strikeout(str(underlined), str(struck), page=1, bbox=[10, 10, 80, 24])
    )
    draw = json.loads(
        pdf_freehand_draw(
            str(struck),
            str(drawn),
            page=1,
            points=[[10, 10], [30, 40], [60, 20]],
        )
    )
    resize = json.loads(pdf_resize_pages(str(drawn), str(resized), width=200, height=200))
    margin = json.loads(pdf_add_margin(str(resized), str(margined), margin=12))
    underlay = json.loads(pdf_underlay(str(margined), str(underlaid), text="DRAFT"))
    validate = json.loads(pdf_validate_output(str(underlaid), expected_pages=1))
    render_check = json.loads(pdf_render_check(str(underlaid), pages="1"))
    blank_check = json.loads(pdf_blank_page_check(str(underlaid), pages="1"))

    assert image_result["tool"] == "pdf.convert.image_to_pdf"
    assert watermark["tool"] == "pdf.edit.watermark"
    assert page_numbers["tool"] == "pdf.edit.page_numbers"
    assert shape["tool"] == "pdf.edit.add_shape"
    assert underline["tool"] == "pdf.edit.underline"
    assert strikeout["tool"] == "pdf.edit.strikeout"
    assert draw["tool"] == "pdf.edit.freehand_draw"
    assert resize["tool"] == "pdf.edit.resize_pages"
    assert margin["tool"] == "pdf.edit.add_margin"
    assert underlay["tool"] == "pdf.edit.underlay"
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


def _authoring_brief() -> dict[str, object]:
    return {
        "topic": "Independent developers going global",
        "goal": "Create a concise strategy deck",
        "audience": "founders",
        "page_count": 4,
        "deliverable": "deck",
    }


def _evidence_cards() -> list[dict[str, object]]:
    return [
        {
            "id": "ev_market",
            "claim": "Mobile monetization remains strong.",
            "evidence": "Revenue growth continues while downloads flatten.",
            "source_title": "State of Mobile 2026",
        }
    ]


def _fake_tesseract_tsv(
    image_path: Path,
    languages: list[str],
    engine: str,
    psm: int,
) -> str:
    assert image_path.exists()
    assert languages == ["eng"]
    assert engine == "tesseract"
    assert psm == 6
    return (
        "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
        "5\t1\t1\t1\t1\t1\t10\t20\t40\t12\t96\tHello\n"
        "5\t1\t1\t1\t1\t2\t56\t20\t28\t12\t91\tOCR\n"
    )
