import json
from pathlib import Path

from PIL import Image
from typer.testing import CliRunner

from agentpdf.cli.main import app


runner = CliRunner()


def test_tools_list_json_includes_complete_manifest() -> None:
    result = runner.invoke(app, ["tools", "list", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert len(payload["tools"]) >= 100
    assert any(tool["name"] == "pdf.organize.merge" for tool in payload["tools"])


def test_tools_show_json_returns_one_tool() -> None:
    result = runner.invoke(app, ["tools", "show", "pdf.inspect.document", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["name"] == "pdf.inspect.document"
    assert payload["implemented"] is True


def test_agents_config_cli_generates_claude_mcp_config(tmp_path: Path) -> None:
    output = tmp_path / "claude_desktop_config.json"

    result = runner.invoke(
        app,
        [
            "agents",
            "config",
            "--client",
            "claude-desktop",
            "--command",
            "okpdf",
            "--safe-root",
            ".",
            "--output",
            str(output),
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["tool"] == "agent.config.generate"
    assert payload["status"] == "succeeded"
    assert payload["usage"]["client"] == "claude-desktop"
    assert payload["usage"]["config"]["mcpServers"]["agentpdf"]["command"] == "okpdf"
    assert payload["usage"]["config"]["mcpServers"]["agentpdf"]["args"] == [
        "serve",
        "--mcp",
        "--safe-root",
        ".",
    ]
    assert payload["artifacts"][0]["path"] == str(output)
    assert output.exists()


def test_agents_doctor_cli_reports_agent_readiness() -> None:
    result = runner.invoke(app, ["agents", "doctor", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["tool"] == "agent.local.doctor"
    assert payload["usage"]["checks"]["python"]["ok"] is True
    assert payload["usage"]["checks"]["agentpdf_import"]["ok"] is True
    assert payload["usage"]["checks"]["mcp_dependency"]["ok"] is True
    assert payload["usage"]["checks"]["mcp_config_examples"]["ok"] is True
    assert payload["usage"]["tools"]["implemented_count"] >= 30
    assert "agents config" in " ".join(payload["next_recommended_tools"])


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

    assert reorder.exit_code == 0
    assert json.loads(reorder.stdout)["tool"] == "pdf.organize.reorder_pages"
    assert insert_blank.exit_code == 0
    payload = json.loads(insert_blank.stdout)
    assert payload["tool"] == "pdf.organize.insert_blank_pages"
    assert payload["artifacts"][0]["page_count"] == 3


def test_optimize_compress_and_repair_cli(two_page_pdf: Path, tmp_path: Path) -> None:
    compressed = tmp_path / "compressed.pdf"
    repaired = tmp_path / "repaired.pdf"

    compress = runner.invoke(
        app,
        ["compress", str(two_page_pdf), "-o", str(compressed), "--json"],
    )
    repair = runner.invoke(
        app,
        ["repair", str(two_page_pdf), "-o", str(repaired), "--json"],
    )

    assert compress.exit_code == 0
    assert json.loads(compress.stdout)["tool"] == "pdf.optimize.compress"
    assert compressed.exists()
    assert repair.exit_code == 0
    assert json.loads(repair.stdout)["tool"] == "pdf.optimize.repair"
    assert repaired.exists()


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

    text = runner.invoke(app, ["extract-text", str(text_pdf), "--pages", "1", "--json"])
    read = runner.invoke(app, ["metadata", "read", str(metadata_pdf), "--json"])
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

    assert text.exit_code == 0
    assert "AgentPDF local text layer" in json.loads(text.stdout)["usage"]["text"]
    assert read.exit_code == 0
    assert json.loads(read.stdout)["usage"]["metadata"]["Title"] == "Original Title"
    assert update.exit_code == 0
    assert json.loads(update.stdout)["tool"] == "pdf.metadata.update"
    assert remove.exit_code == 0
    assert json.loads(remove.stdout)["tool"] == "pdf.metadata.remove"


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


def test_image_watermark_page_numbers_and_validate_cli(tmp_path: Path) -> None:
    image = tmp_path / "cover.png"
    image_pdf = tmp_path / "cover.pdf"
    watermarked = tmp_path / "watermarked.pdf"
    numbered = tmp_path / "numbered.pdf"
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
    validate_result = runner.invoke(app, ["validate", str(numbered), "--json"])
    render_check = runner.invoke(app, ["render-check", str(numbered), "--pages", "1", "--json"])
    blank_check = runner.invoke(app, ["blank-page-check", str(numbered), "--pages", "1", "--json"])

    assert image_result.exit_code == 0
    assert json.loads(image_result.stdout)["tool"] == "pdf.convert.image_to_pdf"
    assert watermark_result.exit_code == 0
    assert json.loads(watermark_result.stdout)["tool"] == "pdf.edit.watermark"
    assert page_numbers_result.exit_code == 0
    assert json.loads(page_numbers_result.stdout)["tool"] == "pdf.edit.page_numbers"
    assert validate_result.exit_code == 0
    assert json.loads(validate_result.stdout)["tool"] == "pdf.validation.validate_output"
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


def _write_image_pdf(path: Path, image_path: Path) -> None:
    from reportlab.pdfgen import canvas

    document = canvas.Canvas(str(path), pagesize=(200, 200))
    document.drawImage(str(image_path), 24, 120, width=32, height=24)
    document.showPage()
    document.save()
