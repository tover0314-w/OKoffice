from pathlib import Path

from PIL import Image
from fastapi.testclient import TestClient

from agentpdf.api.app import create_app
from agentpdf.tools.registry import load_tool_manifest


def test_api_healthz() -> None:
    client = TestClient(create_app())

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "agentpdf"}


def test_api_lists_complete_tool_manifest() -> None:
    client = TestClient(create_app())

    response = client.get("/v1/tools")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["tools"]) == len(load_tool_manifest().tools)
    assert any(tool["name"] == "pdf.inspect.document" for tool in payload["tools"])


def test_api_shows_single_tool() -> None:
    client = TestClient(create_app())

    response = client.get("/v1/tools/pdf.inspect.document")

    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "pdf.inspect.document"
    assert payload["implemented"] is True


def test_api_runs_ocr_tool(monkeypatch, tmp_path: Path) -> None:
    client = TestClient(create_app())
    image = tmp_path / "scan.png"
    Image.new("RGB", (160, 80), color=(255, 255, 255)).save(image)
    monkeypatch.setattr("agentpdf.ocr_scan.local._run_tesseract_tsv", _fake_tesseract_tsv)

    response = client.post(
        "/v1/tools/pdf.ocr_scan.ocr/run",
        json={"input_path": str(image), "languages": ["eng"]},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["tool"] == "pdf.ocr_scan.ocr"
    assert payload["usage"]["text"] == "Hello OCR"
    assert payload["usage"]["pages"][0]["regions"][0]["confidence"] == 96.0


def test_api_runs_image_analyze_tool(monkeypatch, tmp_path: Path) -> None:
    client = TestClient(create_app())
    image = tmp_path / "scan.png"
    Image.new("RGB", (160, 80), color=(255, 255, 255)).save(image)
    monkeypatch.setattr("agentpdf.ocr_scan.local._run_tesseract_tsv", _fake_tesseract_tsv)

    response = client.post(
        "/v1/tools/pdf.context.image_analyze/run",
        json={"input_path": str(image), "languages": ["eng"]},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["tool"] == "pdf.context.image_analyze"
    assert payload["usage"]["image"]["width"] == 160
    assert payload["usage"]["ocr"]["text"] == "Hello OCR"


def test_api_runs_inspect_tool(simple_pdf: Path) -> None:
    client = TestClient(create_app())

    response = client.post(
        "/v1/tools/pdf.inspect.document/run",
        json={"path": str(simple_pdf)},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "succeeded"
    assert payload["tool"] == "pdf.inspect.document"
    assert payload["usage"]["page_count"] == 1


def test_api_runs_inspect_pages_tool(text_pdf: Path) -> None:
    client = TestClient(create_app())

    response = client.post(
        "/v1/tools/pdf.inspect.pages/run",
        json={"input_path": str(text_pdf), "pages": "1", "render_check": True},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["tool"] == "pdf.inspect.pages"
    assert payload["usage"]["selected_pages"] == [1]
    assert payload["usage"]["pages"][0]["has_text_layer"] is True
    assert payload["usage"]["pages"][0]["render"]["status"] == "passed"


def test_api_runs_workflow_plan_tool() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/v1/tools/pdf.workflow.plan/run",
        json={"goal": "Chat with this PDF and cite the answer.", "input_path": "report.pdf"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["tool"] == "pdf.workflow.plan"
    assert payload["usage"]["workflow"]["steps"][0]["tool"] == "pdf.inspect.document"


def test_api_runs_workflow_run_tool(text_pdf: Path) -> None:
    client = TestClient(create_app())

    response = client.post(
        "/v1/tools/pdf.workflow.run/run",
        json={
            "workflow": {
                "steps": [
                    {
                        "step_id": "inspect",
                        "tool": "pdf.inspect.document",
                        "input": {"path": str(text_pdf)},
                    }
                ]
            }
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["tool"] == "pdf.workflow.run"
    assert payload["usage"]["workflow_run"]["executed_steps"] == 1
    assert payload["usage"]["workflow_run"]["step_results"][0]["status"] == "succeeded"


def test_api_runs_workflow_report_tool(text_pdf: Path, tmp_path: Path) -> None:
    client = TestClient(create_app())
    run_response = client.post(
        "/v1/tools/pdf.workflow.run/run",
        json={
            "workflow": {
                "steps": [
                    {
                        "step_id": "inspect",
                        "tool": "pdf.inspect.document",
                        "input": {"path": str(text_pdf)},
                    }
                ]
            }
        },
    )

    response = client.post(
        "/v1/tools/pdf.workflow.report/run",
        json={
            "workflow_run": run_response.json(),
            "output_path": str(tmp_path / "workflow-report.md"),
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["tool"] == "pdf.workflow.report"
    assert payload["usage"]["workflow_report"]["executed_steps"] == 1
    assert payload["artifacts"][0]["path"].endswith("workflow-report.md")


def test_api_runs_merge_tool(simple_pdf: Path, two_page_pdf: Path, tmp_path: Path) -> None:
    client = TestClient(create_app())
    output = tmp_path / "merged.pdf"

    response = client.post(
        "/v1/tools/pdf.organize.merge/run",
        json={"input_paths": [str(simple_pdf), str(two_page_pdf)], "output_path": str(output)},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "succeeded"
    assert payload["artifacts"][0]["page_count"] == 3
    assert output.exists()


def test_api_stores_job_and_artifact_after_run(
    simple_pdf: Path, two_page_pdf: Path, tmp_path: Path
) -> None:
    client = TestClient(create_app())
    output = tmp_path / "merged.pdf"

    run_response = client.post(
        "/v1/tools/pdf.organize.merge/run",
        json={"input_paths": [str(simple_pdf), str(two_page_pdf)], "output_path": str(output)},
    )
    result = run_response.json()
    job_id = result["job_id"]
    artifact_id = result["artifacts"][0]["artifact_id"]

    job_response = client.get(f"/v1/jobs/{job_id}")
    artifact_response = client.get(f"/v1/artifacts/{artifact_id}")
    download_response = client.get(f"/v1/artifacts/{artifact_id}/download")

    assert job_response.status_code == 200
    assert job_response.json()["job_id"] == job_id
    assert artifact_response.status_code == 200
    assert artifact_response.json()["artifact_id"] == artifact_id
    assert download_response.status_code == 200
    assert download_response.content.startswith(b"%PDF")


def test_api_runs_split_tool(two_page_pdf: Path, tmp_path: Path) -> None:
    client = TestClient(create_app())
    output = tmp_path / "first.pdf"

    response = client.post(
        "/v1/tools/pdf.organize.split/run",
        json={"input_path": str(two_page_pdf), "pages": "1", "output_path": str(output)},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "succeeded"
    assert payload["artifacts"][0]["page_count"] == 1


def test_api_runs_extract_remove_and_rotate_tools(two_page_pdf: Path, tmp_path: Path) -> None:
    client = TestClient(create_app())

    extract = client.post(
        "/v1/tools/pdf.organize.extract_pages/run",
        json={"input_path": str(two_page_pdf), "pages": "1", "output_path": str(tmp_path / "e.pdf")},
    )
    remove = client.post(
        "/v1/tools/pdf.organize.remove_pages/run",
        json={"input_path": str(two_page_pdf), "pages": "1", "output_path": str(tmp_path / "r.pdf")},
    )
    rotate = client.post(
        "/v1/tools/pdf.organize.rotate_pages/run",
        json={
            "input_path": str(two_page_pdf),
            "pages": "1",
            "degrees": 90,
            "output_path": str(tmp_path / "rot.pdf"),
        },
    )

    assert extract.status_code == 200
    assert extract.json()["tool"] == "pdf.organize.extract_pages"
    assert remove.status_code == 200
    assert remove.json()["tool"] == "pdf.organize.remove_pages"
    assert rotate.status_code == 200
    assert rotate.json()["tool"] == "pdf.organize.rotate_pages"


def test_api_runs_reorder_and_insert_blank_pages(two_page_pdf: Path, tmp_path: Path) -> None:
    client = TestClient(create_app())
    reordered = tmp_path / "reordered.pdf"
    with_blank = tmp_path / "with-blank.pdf"

    reorder = client.post(
        "/v1/tools/pdf.organize.reorder_pages/run",
        json={"input_path": str(two_page_pdf), "order": "2,1", "output_path": str(reordered)},
    )
    insert_blank = client.post(
        "/v1/tools/pdf.organize.insert_blank_pages/run",
        json={
            "input_path": str(reordered),
            "after_page": 1,
            "count": 1,
            "output_path": str(with_blank),
        },
    )
    n_up = client.post(
        "/v1/tools/pdf.organize.n_up/run",
        json={"input_path": str(with_blank), "per_sheet": 2, "output_path": str(tmp_path / "n-up.pdf")},
    )
    booklet = client.post(
        "/v1/tools/pdf.organize.booklet/run",
        json={"input_path": str(with_blank), "output_path": str(tmp_path / "booklet.pdf")},
    )

    assert reorder.status_code == 200
    assert reorder.json()["tool"] == "pdf.organize.reorder_pages"
    assert insert_blank.status_code == 200
    assert insert_blank.json()["artifacts"][0]["page_count"] == 3
    assert n_up.status_code == 200
    assert n_up.json()["tool"] == "pdf.organize.n_up"
    assert booklet.status_code == 200
    assert booklet.json()["tool"] == "pdf.organize.booklet"


def test_api_runs_optimize_compress_and_repair(two_page_pdf: Path, tmp_path: Path) -> None:
    client = TestClient(create_app())

    compress = client.post(
        "/v1/tools/pdf.optimize.compress/run",
        json={"input_path": str(two_page_pdf), "output_path": str(tmp_path / "compressed.pdf")},
    )
    repair = client.post(
        "/v1/tools/pdf.optimize.repair/run",
        json={"input_path": str(two_page_pdf), "output_path": str(tmp_path / "repaired.pdf")},
    )
    remove_unused = client.post(
        "/v1/tools/pdf.optimize.remove_unused_objects/run",
        json={"input_path": str(two_page_pdf), "output_path": str(tmp_path / "optimized.pdf")},
    )
    validate_pdfa = client.post(
        "/v1/tools/pdf.optimize.validate_pdfa/run",
        json={"input_path": str(two_page_pdf)},
    )

    assert compress.status_code == 200
    assert compress.json()["tool"] == "pdf.optimize.compress"
    assert repair.status_code == 200
    assert repair.json()["tool"] == "pdf.optimize.repair"
    assert remove_unused.status_code == 200
    assert remove_unused.json()["tool"] == "pdf.optimize.remove_unused_objects"
    assert validate_pdfa.status_code == 200
    assert validate_pdfa.json()["tool"] == "pdf.optimize.validate_pdfa"


def test_api_runs_render_tool(simple_pdf: Path, tmp_path: Path) -> None:
    client = TestClient(create_app())

    response = client.post(
        "/v1/tools/pdf.convert.pdf_to_images/run",
        json={
            "input_path": str(simple_pdf),
            "pages": "1",
            "image_format": "png",
            "out_dir": str(tmp_path),
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "succeeded"
    assert payload["artifacts"][0]["mime_type"] == "image/png"


def test_api_runs_extract_images_tool(tmp_path: Path) -> None:
    client = TestClient(create_app())
    image = tmp_path / "source.png"
    source = tmp_path / "source.pdf"
    Image.new("RGB", (32, 24), color=(40, 120, 80)).save(image)
    _write_image_pdf(source, image)

    response = client.post(
        "/v1/tools/pdf.convert.extract_images/run",
        json={"input_path": str(source), "pages": "1", "out_dir": str(tmp_path / "images")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["tool"] == "pdf.convert.extract_images"
    assert payload["usage"]["image_count"] == 1
    assert payload["artifacts"][0]["mime_type"] == "image/png"


def test_api_runs_text_and_metadata_tools(text_pdf: Path, metadata_pdf: Path, tmp_path: Path) -> None:
    client = TestClient(create_app())

    text = client.post(
        "/v1/tools/pdf.convert.pdf_to_text/run",
        json={"input_path": str(text_pdf), "pages": "1"},
    )
    fonts = client.post(
        "/v1/tools/pdf.convert.extract_fonts/run",
        json={"input_path": str(text_pdf), "pages": "1"},
    )
    read = client.post("/v1/tools/pdf.metadata.read/run", json={"input_path": str(metadata_pdf)})
    page_info = client.post(
        "/v1/tools/pdf.metadata.page_info/run",
        json={"input_path": str(text_pdf), "pages": "1"},
    )
    update = client.post(
        "/v1/tools/pdf.metadata.update/run",
        json={
            "input_path": str(metadata_pdf),
            "metadata": {"Title": "API Title"},
            "output_path": str(tmp_path / "updated.pdf"),
        },
    )
    outline = client.post(
        "/v1/tools/pdf.metadata.update_outline/run",
        json={
            "input_path": str(metadata_pdf),
            "outline": [{"title": "Page One", "page": 1}],
            "output_path": str(tmp_path / "outlined.pdf"),
        },
    )
    remove = client.post(
        "/v1/tools/pdf.metadata.remove/run",
        json={"input_path": str(metadata_pdf), "output_path": str(tmp_path / "clean.pdf")},
    )
    security_remove = client.post(
        "/v1/tools/pdf.security.remove_metadata/run",
        json={"input_path": str(metadata_pdf), "output_path": str(tmp_path / "security-clean.pdf")},
    )

    assert text.status_code == 200
    assert "AgentPDF local text layer" in text.json()["usage"]["text"]
    assert fonts.status_code == 200
    assert fonts.json()["tool"] == "pdf.convert.extract_fonts"
    assert read.status_code == 200
    assert read.json()["usage"]["metadata"]["Title"] == "Original Title"
    assert page_info.status_code == 200
    assert page_info.json()["tool"] == "pdf.metadata.page_info"
    assert update.status_code == 200
    assert update.json()["tool"] == "pdf.metadata.update"
    assert outline.status_code == 200
    assert outline.json()["tool"] == "pdf.metadata.update_outline"
    assert remove.status_code == 200
    assert remove.json()["tool"] == "pdf.metadata.remove"
    assert security_remove.status_code == 200
    assert security_remove.json()["tool"] == "pdf.security.remove_metadata"


def test_api_runs_create_text_and_markdown_tools(tmp_path: Path) -> None:
    client = TestClient(create_app())

    text = client.post(
        "/v1/tools/pdf.convert.text_to_pdf/run",
        json={"text": "API text PDF", "output_path": str(tmp_path / "text.pdf")},
    )
    markdown = client.post(
        "/v1/tools/pdf.convert.markdown_to_pdf/run",
        json={"markdown": "# API Report", "output_path": str(tmp_path / "markdown.pdf")},
    )

    assert text.status_code == 200
    assert text.json()["tool"] == "pdf.convert.text_to_pdf"
    assert markdown.status_code == 200
    assert markdown.json()["tool"] == "pdf.convert.markdown_to_pdf"


def test_api_runs_create_from_prompt_tool(tmp_path: Path) -> None:
    client = TestClient(create_app())
    output = tmp_path / "api-brief.pdf"

    response = client.post(
        "/v1/tools/pdf.ai.create.from_prompt/run",
        json={
            "prompt": "Create a proposal about local PDF template agents.",
            "output_path": str(output),
            "template": "proposal",
            "style_pack": "business_report_modern",
            "colors": {"primary": "#4f46e5", "accent": "#f59e0b"},
            "data": {
                "client": "Agent teams",
                "sections": [
                    {
                        "heading": "Local templates",
                        "body": "Agents can create PDFs locally before any cloud service exists.",
                    }
                ],
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["tool"] == "pdf.ai.create.from_prompt"
    assert payload["usage"]["template_id"] == "proposal"
    assert payload["usage"]["style_pack"] == "business_report_modern"
    assert payload["usage"]["colors"]["primary"] == "#4f46e5"
    assert output.exists()


def test_api_runs_create_templates_tool() -> None:
    client = TestClient(create_app())

    response = client.post("/v1/tools/pdf.ai.create.templates/run", json={})

    assert response.status_code == 200
    payload = response.json()
    assert payload["tool"] == "pdf.ai.create.templates"
    assert "proposal" in payload["usage"]["templates"]
    assert "paper_ink" in payload["usage"]["style_packs"]
    assert payload["usage"]["templates"]["invoice"]["preview_tool"] == "pdf.ai.create.template_preview"


def test_api_runs_create_template_preview_tool(tmp_path: Path) -> None:
    client = TestClient(create_app())
    output = tmp_path / "preview.pdf"

    response = client.post(
        "/v1/tools/pdf.ai.create.template_preview/run",
        json={"template": "invoice", "output_path": str(output)},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["tool"] == "pdf.ai.create.template_preview"
    assert payload["usage"]["template_id"] == "invoice"
    assert payload["usage"]["data_source"] == "template_sample_data"
    assert payload["validation"]["status"] == "passed"
    assert output.exists()


def test_api_runs_image_watermark_page_numbers_and_validate(tmp_path: Path) -> None:
    client = TestClient(create_app())
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
    Image.new("RGB", (160, 90), color=(80, 40, 120)).save(image)

    image_result = client.post(
        "/v1/tools/pdf.convert.image_to_pdf/run",
        json={"image_paths": [str(image)], "output_path": str(image_pdf)},
    )
    watermark = client.post(
        "/v1/tools/pdf.edit.watermark/run",
        json={"input_path": str(image_pdf), "text": "CONFIDENTIAL", "output_path": str(watermarked)},
    )
    page_numbers = client.post(
        "/v1/tools/pdf.edit.page_numbers/run",
        json={"input_path": str(watermarked), "output_path": str(numbered)},
    )
    shape = client.post(
        "/v1/tools/pdf.edit.add_shape/run",
        json={
            "input_path": str(numbered),
            "output_path": str(shaped),
            "shape": "rectangle",
            "page": 1,
            "x": 12,
            "y": 12,
            "width": 48,
            "height": 32,
        },
    )
    underline = client.post(
        "/v1/tools/pdf.edit.underline/run",
        json={"input_path": str(shaped), "output_path": str(underlined), "page": 1, "bbox": [10, 10, 80, 24]},
    )
    strikeout = client.post(
        "/v1/tools/pdf.edit.strikeout/run",
        json={"input_path": str(underlined), "output_path": str(struck), "page": 1, "bbox": [10, 10, 80, 24]},
    )
    draw = client.post(
        "/v1/tools/pdf.edit.freehand_draw/run",
        json={
            "input_path": str(struck),
            "output_path": str(drawn),
            "page": 1,
            "points": [[10, 10], [30, 40], [60, 20]],
        },
    )
    resize = client.post(
        "/v1/tools/pdf.edit.resize_pages/run",
        json={"input_path": str(drawn), "output_path": str(resized), "width": 200, "height": 200},
    )
    margin = client.post(
        "/v1/tools/pdf.edit.add_margin/run",
        json={"input_path": str(resized), "output_path": str(margined), "margin": 12},
    )
    underlay = client.post(
        "/v1/tools/pdf.edit.underlay/run",
        json={"input_path": str(margined), "output_path": str(underlaid), "text": "DRAFT"},
    )
    validate = client.post(
        "/v1/tools/pdf.validation.validate_output/run",
        json={"path": str(underlaid), "expected_pages": 1},
    )
    page_count = client.post(
        "/v1/tools/pdf.validation.page_count_check/run",
        json={"path": str(underlaid), "expected_pages": 1},
    )
    render_check = client.post(
        "/v1/tools/pdf.validation.render_check/run",
        json={"path": str(underlaid), "pages": "1"},
    )
    blank_check = client.post(
        "/v1/tools/pdf.validation.blank_page_check/run",
        json={"path": str(underlaid), "pages": "1"},
    )

    assert image_result.status_code == 200
    assert image_result.json()["tool"] == "pdf.convert.image_to_pdf"
    assert watermark.status_code == 200
    assert watermark.json()["tool"] == "pdf.edit.watermark"
    assert page_numbers.status_code == 200
    assert page_numbers.json()["tool"] == "pdf.edit.page_numbers"
    assert shape.status_code == 200
    assert shape.json()["tool"] == "pdf.edit.add_shape"
    assert underline.status_code == 200
    assert underline.json()["tool"] == "pdf.edit.underline"
    assert strikeout.status_code == 200
    assert strikeout.json()["tool"] == "pdf.edit.strikeout"
    assert draw.status_code == 200
    assert draw.json()["tool"] == "pdf.edit.freehand_draw"
    assert resize.status_code == 200
    assert resize.json()["tool"] == "pdf.edit.resize_pages"
    assert margin.status_code == 200
    assert margin.json()["tool"] == "pdf.edit.add_margin"
    assert underlay.status_code == 200
    assert underlay.json()["tool"] == "pdf.edit.underlay"
    assert validate.status_code == 200
    assert page_count.status_code == 200
    assert page_count.json()["tool"] == "pdf.validation.page_count_check"
    assert render_check.status_code == 200
    assert render_check.json()["tool"] == "pdf.validation.render_check"
    assert blank_check.status_code == 200
    assert blank_check.json()["tool"] == "pdf.validation.blank_page_check"


def test_api_runs_parse_lite_and_local_rag(tmp_path: Path) -> None:
    client = TestClient(create_app())
    source = tmp_path / "rag.pdf"
    index = tmp_path / "rag.index.json"
    ir_json = tmp_path / "rag.ir.json"
    ir_markdown = tmp_path / "rag.md"
    markdown = "# AgentPDF\n\nLocal RAG gives agents cited document evidence.\n"
    created = client.post(
        "/v1/tools/pdf.convert.markdown_to_pdf/run",
        json={"markdown": markdown, "output_path": str(source)},
    )

    parsed = client.post("/v1/tools/pdf.ai.parse.lite/run", json={"input_path": str(source)})
    pdf_json = client.post(
        "/v1/tools/pdf.convert.pdf_to_json/run",
        json={"input_path": str(source), "output_path": str(ir_json)},
    )
    pdf_markdown = client.post(
        "/v1/tools/pdf.convert.pdf_to_markdown/run",
        json={"input_path": str(source), "output_path": str(ir_markdown)},
    )
    ingest = client.post(
        "/v1/tools/pdf.ai.rag.ingest/run",
        json={"input_path": str(source), "index_path": str(index), "max_chars": 80},
    )
    query = client.post(
        "/v1/tools/pdf.ai.rag.query/run",
        json={"index_path": str(index), "query": "What gives cited evidence?"},
    )
    search = client.post(
        "/v1/tools/pdf.ai.rag.search/run",
        json={"index_path": str(index), "query": "cited evidence"},
    )
    highlighted = tmp_path / "rag-highlighted.pdf"
    report = tmp_path / "rag-report.pdf"
    chat_report = tmp_path / "rag-chat-report.pdf"
    chat_highlighted = tmp_path / "rag-chat-highlighted.pdf"
    highlight = client.post(
        "/v1/tools/pdf.ai.rag.highlight_sources/run",
        json={
            "index_path": str(index),
            "answer": "Local RAG gives cited document evidence.",
            "output_path": str(highlighted),
        },
    )
    export_report = client.post(
        "/v1/tools/pdf.ai.rag.export_report/run",
        json={
            "index_path": str(index),
            "question": "What gives cited evidence?",
            "answer": "Local RAG gives cited document evidence.",
            "output_path": str(report),
        },
    )
    chat = client.post(
        "/v1/tools/pdf.ai.rag.chat/run",
        json={
            "input_path": str(source),
            "question": "What gives cited evidence?",
            "index_path": str(tmp_path / "rag-chat.index.json"),
            "report_output_path": str(chat_report),
            "highlight_output_path": str(chat_highlighted),
        },
    )
    cite = client.post(
        "/v1/tools/pdf.ai.rag.cite_answer/run",
        json={"index_path": str(index), "answer": "Local RAG gives cited document evidence."},
    )

    assert created.status_code == 200
    assert parsed.status_code == 200
    assert parsed.json()["tool"] == "pdf.ai.parse.lite"
    assert pdf_json.status_code == 200
    assert pdf_json.json()["tool"] == "pdf.convert.pdf_to_json"
    assert pdf_markdown.status_code == 200
    assert pdf_markdown.json()["tool"] == "pdf.convert.pdf_to_markdown"
    assert ir_markdown.exists()
    assert ingest.status_code == 200
    assert ingest.json()["tool"] == "pdf.ai.rag.ingest"
    assert query.status_code == 200
    assert query.json()["usage"]["citations"][0]["page_number"] == 1
    assert search.status_code == 200
    assert search.json()["usage"]["matches"][0]["page_number"] == 1
    assert highlight.status_code == 200
    assert highlight.json()["tool"] == "pdf.ai.rag.highlight_sources"
    assert highlighted.exists()
    assert export_report.status_code == 200
    assert export_report.json()["tool"] == "pdf.ai.rag.export_report"
    assert report.exists()
    assert chat.status_code == 200
    assert chat.json()["tool"] == "pdf.ai.rag.chat"
    assert chat.json()["usage"]["citation_count"] >= 1
    assert chat_report.exists()
    assert chat_highlighted.exists()
    assert cite.status_code == 200
    assert cite.json()["tool"] == "pdf.ai.rag.cite_answer"
    assert cite.json()["usage"]["citations"][0]["page_number"] == 1


def test_api_rejects_unimplemented_tool() -> None:
    client = TestClient(create_app())

    response = client.post("/v1/tools/pdf.ai.parse.agentic/run", json={})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "tool_not_implemented"


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


def _write_image_pdf(path: Path, image_path: Path) -> None:
    from reportlab.pdfgen import canvas

    document = canvas.Canvas(str(path), pagesize=(200, 200))
    document.drawImage(str(image_path), 24, 120, width=32, height=24)
    document.showPage()
    document.save()
