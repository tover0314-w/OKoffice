import json
from pathlib import Path

from PIL import Image
from typer.testing import CliRunner

from agentpdf.cli.main import app
from agentpdf.tools.registry import load_tool_manifest


runner = CliRunner()


def test_tools_list_json_includes_complete_manifest() -> None:
    result = runner.invoke(app, ["tools", "list", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert len(payload["tools"]) == len(load_tool_manifest().tools)
    assert any(tool["name"] == "pdf.organize.merge" for tool in payload["tools"])


def test_tools_show_json_returns_one_tool() -> None:
    result = runner.invoke(app, ["tools", "show", "pdf.inspect.document", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["name"] == "pdf.inspect.document"
    assert payload["implemented"] is True


def test_workflow_plan_cli_returns_agent_steps() -> None:
    result = runner.invoke(
        app,
        [
            "workflow",
            "plan",
            "--goal",
            "Chat with this PDF and cite the answer.",
            "--input-path",
            "report.pdf",
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["tool"] == "pdf.workflow.plan"
    assert payload["usage"]["workflow"]["steps"][0]["tool"] == "pdf.inspect.document"
    assert "pdf.ai.rag.cite_answer" in [
        step["tool"] for step in payload["usage"]["workflow"]["steps"]
    ]


def test_authoring_plan_cli_from_brief_json(tmp_path: Path) -> None:
    brief_path = tmp_path / "brief.json"
    brief_path.write_text(
        json.dumps(
            {
                "topic": "Independent developers going global",
                "goal": "Create a concise strategy deck",
                "audience": "founders",
                "page_count": 4,
                "deliverable": "deck",
            }
        ),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["authoring", "plan", str(brief_path), "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["tool"] == "pdf.authoring.plan"
    assert payload["usage"]["authoring_plan"]["recommended_authoring_format"] == "html"


def test_cli_authoring_plan_from_brief_json(tmp_path: Path) -> None:
    brief_path = _write_authoring_brief(tmp_path)

    result = runner.invoke(app, ["authoring", "plan", str(brief_path), "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["tool"] == "pdf.authoring.plan"
    assert payload["usage"]["authoring_plan"]["recommended_authoring_format"] == "html"


def test_cli_storyboard_plan_from_brief_json(tmp_path: Path) -> None:
    brief_path = _write_authoring_brief(tmp_path)
    evidence_path = _write_evidence_cards(tmp_path)

    result = runner.invoke(
        app,
        ["storyboard", "plan", str(brief_path), "--evidence", str(evidence_path), "--json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["tool"] == "pdf.storyboard.plan"
    assert payload["usage"]["storyboard"]["page_count"] == 4


def test_cli_local_research_design_and_pages_revise(tmp_path: Path) -> None:
    brief_path = _write_authoring_brief(tmp_path)
    sources_path = tmp_path / "sources.json"
    page_doc_path = tmp_path / "pages.json"
    sources_path.write_text(
        json.dumps(
            [
                {
                    "title": "State of Mobile 2026",
                    "source_type": "report",
                    "summary": "Revenue growth continues while downloads flatten.",
                    "key_points": ["Revenue growth continues while downloads flatten."],
                }
            ]
        ),
        encoding="utf-8",
    )
    page_doc_path.write_text(
        json.dumps(
            {
                "page_document_id": "pages_test",
                "page_count": 1,
                "pages": [
                    {
                        "page_number": 1,
                        "layout": "cover",
                        "title": "Old title",
                        "blocks": [],
                        "evidence_refs": ["ev_1"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    plan = runner.invoke(app, ["research", "plan", str(brief_path), "--json"])
    source_cards = runner.invoke(
        app,
        ["research", "source-cards", "--brief", str(brief_path), "--sources", str(sources_path), "--json"],
    )
    source_payload = json.loads(source_cards.stdout)
    source_cards_path = tmp_path / "source-cards.json"
    source_cards_path.write_text(json.dumps(source_payload["usage"]["source_cards"]), encoding="utf-8")
    evidence_cards = runner.invoke(
        app,
        ["research", "evidence-cards", "--source-cards", str(source_cards_path), "--json"],
    )
    design = runner.invoke(
        app,
        ["design", "tokens", "--theme", "consulting", "--color", "primary_color=#123456", "--json"],
    )
    revise = runner.invoke(
        app,
        [
            "pages",
            "revise",
            str(page_doc_path),
            "--revision",
            '{"page_number":1,"title":"New title"}',
            "--json",
        ],
    )

    assert plan.exit_code == 0
    assert json.loads(plan.stdout)["tool"] == "pdf.research.plan"
    assert source_cards.exit_code == 0
    assert source_payload["usage"]["source_cards"][0]["fetch_status"] == "not_fetched"
    assert evidence_cards.exit_code == 0
    assert json.loads(evidence_cards.stdout)["tool"] == "pdf.research.evidence_cards"
    assert design.exit_code == 0
    assert json.loads(design.stdout)["usage"]["design_tokens"]["primary_color"] == "#123456"
    assert revise.exit_code == 0
    assert json.loads(revise.stdout)["usage"]["page_document"]["pages"][0]["title"] == "New title"


def test_cli_workflow_research_deck(tmp_path: Path) -> None:
    brief_path = _write_authoring_brief(tmp_path)
    evidence_path = _write_evidence_cards(tmp_path)

    result = runner.invoke(
        app,
        [
            "workflow",
            "research-deck",
            str(brief_path),
            "--evidence",
            str(evidence_path),
            "--html-output",
            str(tmp_path / "deck.html"),
            "--pdf-output",
            str(tmp_path / "deck.pdf"),
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["tool"] == "pdf.workflow.research_deck"
    assert payload["usage"]["workflow"]["steps"][0]["tool"] == "pdf.authoring.plan"
    assert payload["usage"]["workflow"]["steps"][-1]["tool"] == "pdf.qa.visual_report"


def test_cli_createpdf_html_first_workflow(tmp_path: Path) -> None:
    html_output = tmp_path / "createpdf.html"
    pdf_output = tmp_path / "createpdf.pdf"

    result = runner.invoke(
        app,
        [
            "createpdf",
            "--html",
            "<main><h1>CreatePDF</h1><p>CLI wraps HTML package, render, QA, and audit.</p></main>",
            "--html-output",
            str(html_output),
            "--pdf-output",
            str(pdf_output),
            "--artifact-dir",
            str(tmp_path / "audit"),
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["tool"] == "pdf.workflow.createpdf"
    assert pdf_output.exists()
    assert Path(payload["usage"]["createpdf"]["qa_report_path"]).exists()


def test_cli_create_html_package_accepts_raw_html(tmp_path: Path) -> None:
    html_output = tmp_path / "raw.html"

    result = runner.invoke(
        app,
        [
            "create",
            "html-package",
            "--html",
            "<main><h1>Raw HTML</h1><p>HTML-first PDF creation.</p></main>",
            "-o",
            str(html_output),
            "--title",
            "Raw HTML",
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["tool"] == "pdf.create.html_package"
    assert payload["usage"]["source_format"] == "raw_html"
    assert html_output.exists()
    assert html_output.with_suffix(".html-manifest.json").exists()


def test_cli_html_first_create_render_and_qa(tmp_path: Path) -> None:
    html_output = tmp_path / "raw.html"
    pdf_output = tmp_path / "raw.pdf"

    create_result = runner.invoke(
        app,
        [
            "create",
            "html-package",
            "--html",
            "<main><h1>Raw HTML</h1><p>HTML-first PDF creation.</p></main>",
            "-o",
            str(html_output),
            "--title",
            "Raw HTML",
            "--json",
        ],
    )
    render_result = runner.invoke(
        app,
        [
            "render-html-package",
            str(html_output.with_suffix(".html-manifest.json")),
            "-o",
            str(pdf_output),
            "--json",
        ],
    )
    qa_result = runner.invoke(
        app,
        [
            "qa",
            "visual-report",
            str(pdf_output),
            "--html-package-manifest",
            str(html_output.with_suffix(".html-manifest.json")),
            "--pages",
            "1",
            "--json",
        ],
    )

    assert create_result.exit_code == 0
    assert render_result.exit_code == 0
    assert qa_result.exit_code == 0
    qa_payload = json.loads(qa_result.stdout)
    assert qa_payload["tool"] == "pdf.qa.visual_report"
    assert qa_payload["status"] == "succeeded"
    assert qa_payload["usage"]["visual_qa"]["checks"]["html_package_manifest"] == "passed"
    assert qa_payload["usage"]["visual_qa"]["html_package_manifest"]["renderer_contract"] == "html-package-v0"


def test_workflow_research_deck_cli_returns_authoring_steps(tmp_path: Path) -> None:
    brief_path = tmp_path / "brief.json"
    evidence_path = tmp_path / "evidence.json"
    brief_path.write_text(
        json.dumps(
            {
                "topic": "Independent developers going global",
                "goal": "Create a concise strategy deck",
                "audience": "founders",
                "page_count": 4,
                "deliverable": "deck",
            }
        ),
        encoding="utf-8",
    )
    evidence_path.write_text(
        json.dumps(
            [
                {
                    "id": "ev_market",
                    "claim": "Mobile monetization remains strong.",
                    "evidence": "Revenue growth continues while downloads flatten.",
                    "source_title": "State of Mobile 2026",
                }
            ]
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "workflow",
            "research-deck",
            str(brief_path),
            "--evidence-cards",
            str(evidence_path),
            "--html-output",
            str(tmp_path / "deck.html"),
            "--pdf-output",
            str(tmp_path / "deck.pdf"),
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["tool"] == "pdf.workflow.research_deck"
    assert payload["usage"]["workflow"]["steps"][0]["tool"] == "pdf.authoring.plan"
    assert payload["usage"]["workflow"]["steps"][-1]["tool"] == "pdf.qa.visual_report"


def test_workflow_research_deck_cli_can_execute_to_pdf(tmp_path: Path) -> None:
    brief_path = _write_authoring_brief(tmp_path)
    evidence_path = _write_evidence_cards(tmp_path)

    result = runner.invoke(
        app,
        [
            "workflow",
            "research-deck",
            str(brief_path),
            "--evidence-cards",
            str(evidence_path),
            "--html-output",
            str(tmp_path / "deck.html"),
            "--pdf-output",
            str(tmp_path / "deck.pdf"),
            "--artifact-dir",
            str(tmp_path / "workflow-artifacts"),
            "--execute",
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    run = payload["usage"]["workflow_run"]
    assert payload["tool"] == "pdf.workflow.research_deck"
    assert run["executed_steps"] == 6
    assert Path(run["bindings"]["<final.pdf>"]).exists()


def test_workflow_run_cli_executes_workflow_file(text_pdf: Path, tmp_path: Path) -> None:
    workflow_path = tmp_path / "workflow.json"
    workflow_path.write_text(
        json.dumps(
            {
                "steps": [
                    {
                        "step_id": "inspect",
                        "tool": "pdf.inspect.document",
                        "input": {"path": str(text_pdf)},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["workflow", "run", str(workflow_path), "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["tool"] == "pdf.workflow.run"
    assert payload["usage"]["workflow_run"]["executed_steps"] == 1
    assert payload["usage"]["workflow_run"]["step_results"][0]["tool"] == "pdf.inspect.document"


def test_workflow_run_cli_accepts_plan_output_with_bindings(
    text_pdf: Path, tmp_path: Path
) -> None:
    plan = runner.invoke(
        app,
        [
            "workflow",
            "plan",
            "--goal",
            "Chat with this PDF and cite the answer.",
            "--input-path",
            str(text_pdf),
            "--json",
        ],
    )
    plan_path = tmp_path / "plan-result.json"
    plan_path.write_text(plan.stdout, encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "workflow",
            "run",
            str(plan_path),
            "--artifact-dir",
            str(tmp_path / "workflow-artifacts"),
            "--binding",
            "<question>=What is the local text layer?",
            "--binding",
            "<answer>=AgentPDF local text layer",
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    run = payload["usage"]["workflow_run"]
    assert payload["tool"] == "pdf.workflow.run"
    assert run["executed_steps"] == 9
    assert run["failed_steps"] == 0
    assert Path(run["bindings"]["<output.index.json>"]).exists()
    assert Path(run["bindings"]["<highlighted.pdf>"]).exists()


def test_workflow_report_cli_writes_markdown_report(text_pdf: Path, tmp_path: Path) -> None:
    workflow_path = tmp_path / "workflow.json"
    run_path = tmp_path / "run-result.json"
    report_path = tmp_path / "workflow-report.md"
    workflow_path.write_text(
        json.dumps(
            {
                "steps": [
                    {
                        "step_id": "inspect",
                        "tool": "pdf.inspect.document",
                        "input": {"path": str(text_pdf)},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    run_result = runner.invoke(app, ["workflow", "run", str(workflow_path), "--json"])
    run_path.write_text(run_result.stdout, encoding="utf-8")

    result = runner.invoke(
        app,
        ["workflow", "report", str(run_path), "-o", str(report_path), "--json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["tool"] == "pdf.workflow.report"
    assert payload["usage"]["workflow_report"]["executed_steps"] == 1
    assert report_path.exists()


def test_inspect_cli_returns_uniform_tool_result(simple_pdf: Path) -> None:
    result = runner.invoke(app, ["inspect", str(simple_pdf), "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "succeeded"
    assert payload["tool"] == "pdf.inspect.document"
    assert payload["usage"]["page_count"] == 1


def test_inspect_pages_cli_returns_page_facts_and_render_evidence(text_pdf: Path) -> None:
    result = runner.invoke(
        app,
        ["inspect-pages", str(text_pdf), "--pages", "1", "--render-check", "--json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["tool"] == "pdf.inspect.pages"
    assert payload["usage"]["selected_pages"] == [1]
    assert payload["usage"]["pages"][0]["has_text_layer"] is True
    assert payload["usage"]["pages"][0]["render"]["status"] == "passed"


def test_merge_cli_writes_output_and_returns_artifact(
    simple_pdf: Path, two_page_pdf: Path, tmp_path: Path
) -> None:
    output = tmp_path / "merged.pdf"

    result = runner.invoke(
        app,
        ["merge", str(simple_pdf), str(two_page_pdf), "-o", str(output), "--json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "succeeded"
    assert payload["artifacts"][0]["page_count"] == 3
    assert output.exists()


def test_split_cli_writes_selected_pages(two_page_pdf: Path, tmp_path: Path) -> None:
    output = tmp_path / "page-1.pdf"

    result = runner.invoke(
        app,
        ["split", str(two_page_pdf), "--pages", "1", "-o", str(output), "--json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "succeeded"
    assert payload["artifacts"][0]["page_count"] == 1
    assert output.exists()


def test_extract_remove_and_rotate_cli(two_page_pdf: Path, tmp_path: Path) -> None:
    extract_output = tmp_path / "extract.pdf"
    remove_output = tmp_path / "remove.pdf"
    rotate_output = tmp_path / "rotate.pdf"

    extract = runner.invoke(
        app,
        ["extract-pages", str(two_page_pdf), "--pages", "2", "-o", str(extract_output), "--json"],
    )
    remove = runner.invoke(
        app,
        ["remove-pages", str(two_page_pdf), "--pages", "1", "-o", str(remove_output), "--json"],
    )
    rotate = runner.invoke(
        app,
        [
            "rotate-pages",
            str(two_page_pdf),
            "--pages",
            "1",
            "--degrees",
            "90",
            "-o",
            str(rotate_output),
            "--json",
        ],
    )

    assert extract.exit_code == 0
    assert json.loads(extract.stdout)["tool"] == "pdf.organize.extract_pages"
    assert remove.exit_code == 0
    assert json.loads(remove.stdout)["tool"] == "pdf.organize.remove_pages"
    assert rotate.exit_code == 0
    assert json.loads(rotate.stdout)["tool"] == "pdf.organize.rotate_pages"


def test_reorder_and_insert_blank_pages_cli(two_page_pdf: Path, tmp_path: Path) -> None:
    reordered = tmp_path / "reordered.pdf"
    with_blank = tmp_path / "with-blank.pdf"
    n_up = tmp_path / "n-up.pdf"
    booklet = tmp_path / "booklet.pdf"

    reorder = runner.invoke(
        app,
        ["reorder-pages", str(two_page_pdf), "--order", "2,1", "-o", str(reordered), "--json"],
    )
    insert_blank = runner.invoke(
        app,
        [
            "insert-blank-pages",
            str(reordered),
            "--after-page",
            "1",
            "--count",
            "1",
            "-o",
            str(with_blank),
            "--json",
        ],
    )
    n_up_result = runner.invoke(
        app,
        ["n-up", str(with_blank), "--per-sheet", "2", "-o", str(n_up), "--json"],
    )
    booklet_result = runner.invoke(
        app,
        ["booklet", str(with_blank), "-o", str(booklet), "--json"],
    )

    assert reorder.exit_code == 0
    assert json.loads(reorder.stdout)["tool"] == "pdf.organize.reorder_pages"
    assert insert_blank.exit_code == 0
    assert n_up_result.exit_code == 0
    assert json.loads(n_up_result.stdout)["tool"] == "pdf.organize.n_up"
    assert booklet_result.exit_code == 0
    assert json.loads(booklet_result.stdout)["tool"] == "pdf.organize.booklet"
    payload = json.loads(insert_blank.stdout)
    assert payload["tool"] == "pdf.organize.insert_blank_pages"
    assert payload["artifacts"][0]["page_count"] == 3


def test_optimize_compress_and_repair_cli(two_page_pdf: Path, tmp_path: Path) -> None:
    compressed = tmp_path / "compressed.pdf"
    repaired = tmp_path / "repaired.pdf"
    optimized = tmp_path / "optimized.pdf"

    compress = runner.invoke(
        app,
        ["compress", str(two_page_pdf), "-o", str(compressed), "--json"],
    )
    repair = runner.invoke(
        app,
        ["repair", str(two_page_pdf), "-o", str(repaired), "--json"],
    )
    remove_unused = runner.invoke(
        app,
        ["remove-unused-objects", str(two_page_pdf), "-o", str(optimized), "--json"],
    )
    validate_pdfa = runner.invoke(app, ["validate-pdfa", str(two_page_pdf), "--json"])

    assert compress.exit_code == 0
    assert json.loads(compress.stdout)["tool"] == "pdf.optimize.compress"
    assert compressed.exists()
    assert repair.exit_code == 0
    assert json.loads(repair.stdout)["tool"] == "pdf.optimize.repair"
    assert repaired.exists()
    assert remove_unused.exit_code == 0
    assert json.loads(remove_unused.stdout)["tool"] == "pdf.optimize.remove_unused_objects"
    assert optimized.exists()
    assert validate_pdfa.exit_code == 0
    assert json.loads(validate_pdfa.stdout)["tool"] == "pdf.optimize.validate_pdfa"


def test_render_cli_writes_png_output(simple_pdf: Path, tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "render",
            str(simple_pdf),
            "--pages",
            "1",
            "--format",
            "png",
            "--out-dir",
            str(tmp_path),
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "succeeded"
    assert payload["tool"] == "pdf.convert.pdf_to_images"
    assert payload["artifacts"][0]["mime_type"] == "image/png"
    assert len(list(tmp_path.iterdir())) == 1


def test_extract_images_cli_writes_image_artifacts(tmp_path: Path) -> None:
    image = tmp_path / "source.png"
    source = tmp_path / "source.pdf"
    out_dir = tmp_path / "images"
    Image.new("RGB", (32, 24), color=(40, 120, 80)).save(image)
    _write_image_pdf(source, image)

    result = runner.invoke(
        app,
        ["extract-images", str(source), "--pages", "1", "--out-dir", str(out_dir), "--json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["tool"] == "pdf.convert.extract_images"
    assert payload["usage"]["image_count"] == 1
    assert payload["artifacts"][0]["mime_type"] == "image/png"


def test_text_and_metadata_cli(text_pdf: Path, metadata_pdf: Path, tmp_path: Path) -> None:
    updated = tmp_path / "updated.pdf"
    cleaned = tmp_path / "cleaned.pdf"
    outlined = tmp_path / "outlined.pdf"
    outline_path = tmp_path / "outline.json"
    outline_path.write_text(json.dumps([{"title": "Page One", "page": 1}]), encoding="utf-8")

    text = runner.invoke(app, ["extract-text", str(text_pdf), "--pages", "1", "--json"])
    fonts = runner.invoke(app, ["extract-fonts", str(text_pdf), "--pages", "1", "--json"])
    read = runner.invoke(app, ["metadata", "read", str(metadata_pdf), "--json"])
    page_info = runner.invoke(app, ["metadata", "page-info", str(text_pdf), "--pages", "1", "--json"])
    update = runner.invoke(
        app,
        [
            "metadata",
            "update",
            str(metadata_pdf),
            "--title",
            "CLI Title",
            "-o",
            str(updated),
            "--json",
        ],
    )
    remove = runner.invoke(
        app,
        ["metadata", "remove", str(metadata_pdf), "-o", str(cleaned), "--json"],
    )
    outline = runner.invoke(
        app,
        ["metadata", "update-outline", str(metadata_pdf), str(outline_path), "-o", str(outlined), "--json"],
    )
    security_cleaned = tmp_path / "security-cleaned.pdf"
    security_remove = runner.invoke(
        app,
        ["security", "remove-metadata", str(metadata_pdf), "-o", str(security_cleaned), "--json"],
    )

    assert text.exit_code == 0
    assert "AgentPDF local text layer" in json.loads(text.stdout)["usage"]["text"]
    assert fonts.exit_code == 0
    assert json.loads(fonts.stdout)["tool"] == "pdf.convert.extract_fonts"
    assert read.exit_code == 0
    assert json.loads(read.stdout)["usage"]["metadata"]["Title"] == "Original Title"
    assert page_info.exit_code == 0
    assert json.loads(page_info.stdout)["tool"] == "pdf.metadata.page_info"
    assert update.exit_code == 0
    assert json.loads(update.stdout)["tool"] == "pdf.metadata.update"
    assert outline.exit_code == 0
    assert json.loads(outline.stdout)["tool"] == "pdf.metadata.update_outline"
    assert remove.exit_code == 0
    assert json.loads(remove.stdout)["tool"] == "pdf.metadata.remove"
    assert security_remove.exit_code == 0
    assert json.loads(security_remove.stdout)["tool"] == "pdf.security.remove_metadata"


def test_create_text_and_markdown_cli(tmp_path: Path) -> None:
    text_output = tmp_path / "text.pdf"
    markdown_source = tmp_path / "report.md"
    markdown_output = tmp_path / "report.pdf"
    markdown_source.write_text("# CLI Report\n\n- Created locally\n", encoding="utf-8")

    text = runner.invoke(
        app,
        ["create", "text", "Hello CLI creation", "-o", str(text_output), "--json"],
    )
    markdown = runner.invoke(
        app,
        ["create", "markdown", str(markdown_source), "-o", str(markdown_output), "--json"],
    )

    assert text.exit_code == 0
    assert json.loads(text.stdout)["tool"] == "pdf.convert.text_to_pdf"
    assert text_output.exists()
    assert markdown.exit_code == 0
    assert json.loads(markdown.stdout)["tool"] == "pdf.convert.markdown_to_pdf"
    assert markdown_output.exists()


def test_create_from_prompt_cli_uses_template_and_style_pack(tmp_path: Path) -> None:
    output = tmp_path / "agent-brief.pdf"
    data = tmp_path / "brief-data.json"
    data.write_text(
        json.dumps(
            {
                "audience": "local agents",
                "sections": [
                    {
                        "heading": "Template Engine",
                        "body": "The local create agent turns prompts into validated PDFs.",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "create",
            "from-prompt",
            "Create a research brief for okpdf template creation.",
            "-o",
            str(output),
            "--template",
            "research_brief",
            "--style-pack",
            "paper_ink",
            "--data",
            str(data),
            "--color",
            "primary=#4f46e5",
            "--color",
            "accent=#f59e0b",
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["tool"] == "pdf.ai.create.from_prompt"
    assert payload["usage"]["template_id"] == "research_brief"
    assert payload["usage"]["style_pack"] == "paper_ink"
    assert payload["usage"]["colors"]["primary"] == "#4f46e5"
    assert payload["usage"]["colors"]["accent"] == "#f59e0b"
    assert "Template Engine" in payload["usage"]["generated_markdown"]
    assert output.exists()


def test_create_templates_cli_lists_catalog() -> None:
    result = runner.invoke(app, ["create", "templates", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["tool"] == "pdf.ai.create.templates"
    assert "research_brief" in payload["usage"]["templates"]
    assert "paper_ink" in payload["usage"]["style_packs"]
    assert payload["usage"]["templates"]["invoice"]["preview_tool"] == "pdf.ai.create.template_preview"


def test_create_template_preview_cli_generates_valid_pdf(tmp_path: Path) -> None:
    output = tmp_path / "invoice-preview.pdf"

    result = runner.invoke(
        app,
        [
            "create",
            "preview",
            "invoice",
            "-o",
            str(output),
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["tool"] == "pdf.ai.create.template_preview"
    assert payload["usage"]["template_id"] == "invoice"
    assert payload["usage"]["data_source"] == "template_sample_data"
    assert payload["validation"]["status"] == "passed"
    assert output.exists()


def test_image_watermark_page_numbers_and_validate_cli(tmp_path: Path) -> None:
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
    Image.new("RGB", (160, 90), color=(40, 80, 120)).save(image)

    image_result = runner.invoke(app, ["image-to-pdf", str(image), "-o", str(image_pdf), "--json"])
    watermark_result = runner.invoke(
        app,
        ["watermark", str(image_pdf), "--text", "CONFIDENTIAL", "-o", str(watermarked), "--json"],
    )
    page_numbers_result = runner.invoke(
        app,
        ["page-numbers", str(watermarked), "-o", str(numbered), "--json"],
    )
    shape_result = runner.invoke(
        app,
        [
            "add-shape",
            str(numbered),
            "-o",
            str(shaped),
            "--shape",
            "rectangle",
            "--page",
            "1",
            "--x",
            "12",
            "--y",
            "12",
            "--width",
            "48",
            "--height",
            "32",
            "--json",
        ],
    )
    underline_result = runner.invoke(
        app,
        ["underline", str(shaped), "-o", str(underlined), "--page", "1", "--bbox", "10,10,80,24", "--json"],
    )
    strikeout_result = runner.invoke(
        app,
        ["strikeout", str(underlined), "-o", str(struck), "--page", "1", "--bbox", "10,10,80,24", "--json"],
    )
    draw_result = runner.invoke(
        app,
        [
            "freehand-draw",
            str(struck),
            "-o",
            str(drawn),
            "--page",
            "1",
            "--points",
            "[[10,10],[30,40],[60,20]]",
            "--json",
        ],
    )
    resize_result = runner.invoke(
        app,
        ["resize-pages", str(drawn), "-o", str(resized), "--width", "200", "--height", "200", "--json"],
    )
    margin_result = runner.invoke(
        app,
        ["add-margin", str(resized), "-o", str(margined), "--margin", "12", "--json"],
    )
    underlay_result = runner.invoke(
        app,
        ["underlay", str(margined), "-o", str(underlaid), "--text", "DRAFT", "--json"],
    )
    validate_result = runner.invoke(app, ["validate", str(underlaid), "--json"])
    page_count = runner.invoke(app, ["page-count-check", str(underlaid), "--expected-pages", "1", "--json"])
    render_check = runner.invoke(app, ["render-check", str(underlaid), "--pages", "1", "--json"])
    blank_check = runner.invoke(app, ["blank-page-check", str(underlaid), "--pages", "1", "--json"])

    assert image_result.exit_code == 0
    assert json.loads(image_result.stdout)["tool"] == "pdf.convert.image_to_pdf"
    assert watermark_result.exit_code == 0
    assert json.loads(watermark_result.stdout)["tool"] == "pdf.edit.watermark"
    assert page_numbers_result.exit_code == 0
    assert json.loads(page_numbers_result.stdout)["tool"] == "pdf.edit.page_numbers"
    assert shape_result.exit_code == 0
    assert json.loads(shape_result.stdout)["tool"] == "pdf.edit.add_shape"
    assert underline_result.exit_code == 0
    assert json.loads(underline_result.stdout)["tool"] == "pdf.edit.underline"
    assert strikeout_result.exit_code == 0
    assert json.loads(strikeout_result.stdout)["tool"] == "pdf.edit.strikeout"
    assert draw_result.exit_code == 0
    assert json.loads(draw_result.stdout)["tool"] == "pdf.edit.freehand_draw"
    assert resize_result.exit_code == 0
    assert json.loads(resize_result.stdout)["tool"] == "pdf.edit.resize_pages"
    assert margin_result.exit_code == 0
    assert json.loads(margin_result.stdout)["tool"] == "pdf.edit.add_margin"
    assert underlay_result.exit_code == 0
    assert json.loads(underlay_result.stdout)["tool"] == "pdf.edit.underlay"
    assert validate_result.exit_code == 0
    assert json.loads(validate_result.stdout)["tool"] == "pdf.validation.validate_output"
    assert page_count.exit_code == 0
    assert json.loads(page_count.stdout)["tool"] == "pdf.validation.page_count_check"
    assert render_check.exit_code == 0
    assert json.loads(render_check.stdout)["tool"] == "pdf.validation.render_check"
    assert blank_check.exit_code == 0
    assert json.loads(blank_check.stdout)["tool"] == "pdf.validation.blank_page_check"


def test_parse_lite_and_rag_cli(tmp_path: Path) -> None:
    source = tmp_path / "rag.pdf"
    markdown = tmp_path / "rag.md"
    index = tmp_path / "rag.index.json"
    ir_json = tmp_path / "rag.ir.json"
    markdown.write_text(
        "# AgentPDF\n\nLocal RAG gives agents cited document evidence.\n",
        encoding="utf-8",
    )
    create_result = runner.invoke(
        app,
        ["create", "markdown", str(markdown), "-o", str(source), "--json"],
    )

    parse = runner.invoke(app, ["parse-lite", str(source), "--json"])
    pdf_json = runner.invoke(app, ["pdf-to-json", str(source), "-o", str(ir_json), "--json"])
    markdown_output = tmp_path / "rag.md.out"
    pdf_markdown = runner.invoke(
        app,
        ["pdf-to-markdown", str(source), "-o", str(markdown_output), "--json"],
    )
    ingest = runner.invoke(app, ["rag", "ingest", str(source), "--index", str(index), "--json"])
    query = runner.invoke(
        app,
        ["rag", "query", str(index), "--query", "What gives cited evidence?", "--json"],
    )
    search = runner.invoke(
        app,
        ["rag", "search", str(index), "--query", "cited evidence", "--json"],
    )
    highlighted = tmp_path / "rag-highlighted.pdf"
    report = tmp_path / "rag-report.pdf"
    chat_report = tmp_path / "rag-chat-report.pdf"
    chat_highlighted = tmp_path / "rag-chat-highlighted.pdf"
    highlight = runner.invoke(
        app,
        [
            "rag",
            "highlight-sources",
            str(index),
            "--answer",
            "Local RAG gives cited document evidence.",
            "-o",
            str(highlighted),
            "--json",
        ],
    )
    export_report = runner.invoke(
        app,
        [
            "rag",
            "export-report",
            str(index),
            "--question",
            "What gives cited evidence?",
            "--answer",
            "Local RAG gives cited document evidence.",
            "-o",
            str(report),
            "--json",
        ],
    )
    chat = runner.invoke(
        app,
        [
            "rag",
            "chat",
            str(source),
            "--question",
            "What gives cited evidence?",
            "--index",
            str(tmp_path / "rag-chat.index.json"),
            "--report-output",
            str(chat_report),
            "--highlight-output",
            str(chat_highlighted),
            "--json",
        ],
    )
    cite = runner.invoke(
        app,
        [
            "rag",
            "cite-answer",
            str(index),
            "--answer",
            "Local RAG gives cited document evidence.",
            "--json",
        ],
    )

    assert create_result.exit_code == 0
    assert parse.exit_code == 0
    assert json.loads(parse.stdout)["tool"] == "pdf.ai.parse.lite"
    assert pdf_json.exit_code == 0
    assert json.loads(pdf_json.stdout)["tool"] == "pdf.convert.pdf_to_json"
    assert pdf_markdown.exit_code == 0
    assert json.loads(pdf_markdown.stdout)["tool"] == "pdf.convert.pdf_to_markdown"
    assert markdown_output.exists()
    assert ingest.exit_code == 0
    assert json.loads(ingest.stdout)["tool"] == "pdf.ai.rag.ingest"
    assert query.exit_code == 0
    payload = json.loads(query.stdout)
    assert payload["tool"] == "pdf.ai.rag.query"
    assert payload["usage"]["citations"][0]["page_number"] == 1
    assert search.exit_code == 0
    assert json.loads(search.stdout)["tool"] == "pdf.ai.rag.search"
    assert highlight.exit_code == 0
    assert json.loads(highlight.stdout)["tool"] == "pdf.ai.rag.highlight_sources"
    assert highlighted.exists()
    assert export_report.exit_code == 0
    assert json.loads(export_report.stdout)["tool"] == "pdf.ai.rag.export_report"
    assert report.exists()
    assert chat.exit_code == 0
    chat_payload = json.loads(chat.stdout)
    assert chat_payload["tool"] == "pdf.ai.rag.chat"
    assert chat_payload["usage"]["citation_count"] >= 1
    assert chat_report.exists()
    assert chat_highlighted.exists()
    assert cite.exit_code == 0
    assert json.loads(cite.stdout)["tool"] == "pdf.ai.rag.cite_answer"


def test_ocr_cli_returns_regions(monkeypatch, tmp_path: Path) -> None:
    image = tmp_path / "scan.png"
    Image.new("RGB", (160, 80), color=(255, 255, 255)).save(image)
    monkeypatch.setattr("agentpdf.ocr_scan.local._run_tesseract_tsv", _fake_tesseract_tsv)

    result = runner.invoke(app, ["ocr", "ocr", str(image), "--language", "eng", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["tool"] == "pdf.ocr_scan.ocr"
    assert payload["usage"]["text"] == "Hello OCR"
    assert payload["usage"]["pages"][0]["regions"][0]["image_bbox"] == [10, 20, 50, 32]


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


def test_serve_api_invokes_local_rest_server(monkeypatch) -> None:
    called = {}

    def fake_run(app_path: str, **kwargs) -> None:
        called["app_path"] = app_path
        called["kwargs"] = kwargs

    monkeypatch.setattr("uvicorn.run", fake_run)

    result = runner.invoke(app, ["serve", "--api"])

    assert result.exit_code == 0
    assert called["app_path"] == "agentpdf.api.app:create_app"
    assert called["kwargs"]["factory"] is True
    assert called["kwargs"]["host"] == "127.0.0.1"
    assert called["kwargs"]["port"] == 7331


def test_serve_api_accepts_host_and_port_for_containers(monkeypatch) -> None:
    called = {}

    def fake_run(app_path: str, **kwargs) -> None:
        called["app_path"] = app_path
        called["kwargs"] = kwargs

    monkeypatch.setattr("uvicorn.run", fake_run)

    result = runner.invoke(app, ["serve", "--api", "--host", "0.0.0.0", "--port", "7332"])

    assert result.exit_code == 0
    assert called["app_path"] == "agentpdf.api.app:create_app"
    assert called["kwargs"]["host"] == "0.0.0.0"
    assert called["kwargs"]["port"] == 7332


def _write_authoring_brief(tmp_path: Path) -> Path:
    brief_path = tmp_path / "brief.json"
    brief_path.write_text(
        json.dumps(
            {
                "topic": "Independent developers going global",
                "goal": "Create a concise strategy deck",
                "audience": "founders",
                "page_count": 4,
                "deliverable": "deck",
            }
        ),
        encoding="utf-8",
    )
    return brief_path


def _write_evidence_cards(tmp_path: Path) -> Path:
    evidence_path = tmp_path / "evidence.json"
    evidence_path.write_text(
        json.dumps(
            {
                "evidence_cards": [
                    {
                        "id": "ev_market",
                        "claim": "Mobile monetization remains strong.",
                        "evidence": "Revenue growth continues while downloads flatten.",
                        "source_title": "State of Mobile 2026",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    return evidence_path


def _write_image_pdf(path: Path, image_path: Path) -> None:
    from reportlab.pdfgen import canvas

    document = canvas.Canvas(str(path), pagesize=(200, 200))
    document.drawImage(str(image_path), 24, 120, width=32, height=24)
    document.showPage()
    document.save()
