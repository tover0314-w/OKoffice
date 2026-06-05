import json
from pathlib import Path

from pypdf import PdfReader

from okoffice.creation.agent import create_pdf_from_prompt, create_template_preview, list_create_templates
from okoffice.core.pdf import create_markdown_pdf
from okoffice.ir.lite import parse_lite_pdf, write_document_ir_json, write_document_ir_markdown
from okoffice.rag.local import (
    chat_pdf,
    cite_answer,
    export_report,
    highlight_sources,
    ingest_pdf,
    query_index,
    search_index,
)


def test_parse_lite_pdf_returns_document_ir_with_page_citations(tmp_path: Path) -> None:
    source = tmp_path / "agent-report.pdf"
    create_markdown_pdf(
        "# OKoffice\n\nLocal RAG gives agents cited document evidence.\n\n## Safety\n\nNo cloud key required.",
        source,
    )

    result = parse_lite_pdf(source)

    assert result.status == "succeeded"
    assert result.tool == "pdf.ai.parse.lite"
    document_ir = result.usage["document_ir"]
    assert document_ir["ir_version"] == "0.1"
    assert document_ir["pages"][0]["page_number"] == 1
    assert document_ir["pages"][0]["blocks"][0]["type"] == "paragraph"
    assert "Local RAG" in document_ir["pages"][0]["blocks"][0]["text"]
    assert document_ir["pages"][0]["blocks"][0]["bbox"] == [0, 0, 612.0, 792.0]


def test_local_rag_ingest_and_query_return_cited_chunks(tmp_path: Path) -> None:
    source = tmp_path / "agent-report.pdf"
    index = tmp_path / "agent-report.index.json"
    create_markdown_pdf(
        "# OKoffice\n\nLocal RAG gives agents cited document evidence.\n\n## Safety\n\nNo cloud key required.",
        source,
    )

    ingest = ingest_pdf(source, index_path=index, max_chars=80)
    query = query_index(index, query="What gives agents cited evidence?", top_k=2)

    assert ingest.status == "succeeded"
    assert ingest.tool == "pdf.ai.rag.ingest"
    assert ingest.artifacts[0].mime_type == "application/json"
    assert ingest.usage["chunk_count"] >= 1
    assert index.exists()
    assert json.loads(index.read_text(encoding="utf-8"))["source_path"] == str(source.resolve())
    assert query.status == "succeeded"
    assert query.tool == "pdf.ai.rag.query"
    assert "Local RAG gives agents cited document evidence" in query.usage["answer"]
    assert query.usage["citations"][0]["page_number"] == 1
    assert query.usage["citations"][0]["bbox"] == [0, 0, 612.0, 792.0]


def test_pdf_to_json_writes_document_ir_artifact(tmp_path: Path) -> None:
    source = tmp_path / "agent-report.pdf"
    output = tmp_path / "agent-report.ir.json"
    create_markdown_pdf("# OKoffice\n\nDocument IR powers cited workflows.", source)

    result = write_document_ir_json(source, output_path=output)

    assert result.status == "succeeded"
    assert result.tool == "pdf.convert.pdf_to_json"
    assert result.artifacts[0].mime_type == "application/json"
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["ir_version"] == "0.1"
    assert payload["pages"][0]["blocks"][0]["text"] == "OKoffice\nDocument IR powers cited workflows."


def test_pdf_to_markdown_writes_cited_markdown_artifact(tmp_path: Path) -> None:
    source = tmp_path / "agent-report.pdf"
    output = tmp_path / "agent-report.md"
    create_markdown_pdf("# OKoffice\n\nDocument IR powers cited workflows.", source)

    result = write_document_ir_markdown(source, output_path=output)

    assert result.status == "succeeded"
    assert result.tool == "pdf.convert.pdf_to_markdown"
    assert result.artifacts[0].mime_type == "text/markdown"
    markdown = output.read_text(encoding="utf-8")
    assert "<!-- okoffice: page=1" in markdown
    assert "bbox=[0, 0, 612.0, 792.0]" in markdown
    assert "OKoffice" in markdown
    assert "Document IR powers cited workflows." in markdown


def test_local_rag_search_returns_ranked_matches(tmp_path: Path) -> None:
    source = tmp_path / "agent-report.pdf"
    index = tmp_path / "agent-report.index.json"
    create_markdown_pdf(
        "# OKoffice\n\nLocal RAG gives agents cited document evidence.\n\n## Safety\n\nNo cloud key required.",
        source,
    )
    ingest_pdf(source, index_path=index, max_chars=80)

    result = search_index(index, query="cloud key", top_k=3)

    assert result.status == "succeeded"
    assert result.tool == "pdf.ai.rag.search"
    assert result.usage["matches"][0]["page_number"] == 1
    assert "No cloud key required" in result.usage["matches"][0]["text"]


def test_local_rag_cite_answer_returns_page_bbox_evidence(tmp_path: Path) -> None:
    source = tmp_path / "agent-report.pdf"
    index = tmp_path / "agent-report.index.json"
    create_markdown_pdf(
        "# OKoffice\n\nLocal RAG gives agents cited document evidence.\n\n## Safety\n\nNo cloud key required.",
        source,
    )
    ingest_pdf(source, index_path=index, max_chars=80)

    result = cite_answer(index, answer="Local RAG gives cited evidence without a cloud key.", top_k=3)

    assert result.status == "succeeded"
    assert result.tool == "pdf.ai.rag.cite_answer"
    assert result.usage["citation_count"] >= 1
    assert result.usage["citations"][0]["page_number"] == 1
    assert result.usage["citations"][0]["bbox"] == [0, 0, 612.0, 792.0]
    assert "Local RAG gives agents cited document evidence" in result.usage["citations"][0]["text"]


def test_local_rag_highlight_sources_writes_annotated_pdf(tmp_path: Path) -> None:
    source = tmp_path / "agent-report.pdf"
    index = tmp_path / "agent-report.index.json"
    highlighted = tmp_path / "agent-report-highlighted.pdf"
    create_markdown_pdf(
        "# OKoffice\n\nLocal RAG gives agents cited document evidence.\n\n## Safety\n\nNo cloud key required.",
        source,
    )
    ingest_pdf(source, index_path=index, max_chars=80)

    result = highlight_sources(
        index,
        output_path=highlighted,
        answer="Local RAG gives cited evidence without a cloud key.",
        top_k=3,
    )

    assert result.status == "succeeded"
    assert result.tool == "pdf.ai.rag.highlight_sources"
    assert result.artifacts[0].mime_type == "application/pdf"
    assert result.artifacts[0].page_count == 1
    assert result.validation is not None
    assert result.validation.status == "passed"
    assert highlighted.exists()
    assert result.usage["citation_count"] >= 1
    assert result.usage["highlighted_pages"] == [1]
    reader = PdfReader(highlighted)
    assert reader.pages[0].get("/Annots") is not None


def test_local_rag_export_report_writes_cited_pdf_report(tmp_path: Path) -> None:
    source = tmp_path / "agent-report.pdf"
    index = tmp_path / "agent-report.index.json"
    report = tmp_path / "agent-report-rag-report.pdf"
    create_markdown_pdf(
        "# OKoffice\n\nLocal RAG gives agents cited document evidence.\n\n## Safety\n\nNo cloud key required.",
        source,
    )
    ingest_pdf(source, index_path=index, max_chars=80)

    result = export_report(
        index,
        output_path=report,
        question="What gives agents cited evidence?",
        answer="Local RAG gives agents cited document evidence.",
        top_k=3,
    )

    assert result.status == "succeeded"
    assert result.tool == "pdf.ai.rag.export_report"
    assert result.artifacts[0].mime_type == "application/pdf"
    assert result.artifacts[0].page_count >= 1
    assert result.validation is not None
    assert result.validation.status == "passed"
    assert report.exists()
    assert result.usage["citation_count"] >= 1
    assert result.usage["pages_cited"] == [1]
    text = "\n".join(page.extract_text() or "" for page in PdfReader(report).pages)
    assert "What gives agents cited evidence?" in text
    assert "Local RAG gives agents cited document evidence." in text
    assert "Page 1" in text


def test_local_rag_chat_runs_end_to_end_with_report_and_highlights(tmp_path: Path) -> None:
    source = tmp_path / "agent-chat.pdf"
    index = tmp_path / "agent-chat.index.json"
    report = tmp_path / "agent-chat-report.pdf"
    highlighted = tmp_path / "agent-chat-highlighted.pdf"
    create_markdown_pdf(
        "# OKoffice\n\nLocal RAG gives agents cited document evidence.\n\n## Safety\n\nNo cloud key required.",
        source,
    )

    result = chat_pdf(
        source,
        question="What gives agents cited evidence?",
        index_path=index,
        report_output_path=report,
        highlight_output_path=highlighted,
        top_k=3,
        style_pack="business_report_modern",
    )

    assert result.status == "succeeded"
    assert result.tool == "pdf.ai.rag.chat"
    assert [artifact.mime_type for artifact in result.artifacts] == [
        "application/json",
        "application/pdf",
        "application/pdf",
    ]
    assert index.exists()
    assert report.exists()
    assert highlighted.exists()
    assert "Local RAG gives agents cited document evidence" in result.usage["answer"]
    assert result.usage["citation_count"] >= 1
    assert result.usage["pages_cited"] == [1]
    assert result.usage["report_path"] == str(report.resolve())
    assert result.usage["highlighted_path"] == str(highlighted.resolve())
    report_text = "\n".join(page.extract_text() or "" for page in PdfReader(report).pages)
    assert "What gives agents cited evidence?" in report_text
    assert PdfReader(highlighted).pages[0].get("/Annots") is not None


def test_create_pdf_from_prompt_selects_template_and_validates_output(tmp_path: Path) -> None:
    output = tmp_path / "research-brief.pdf"

    result = create_pdf_from_prompt(
        "Create a research brief about local PDF agents. Include template selection, "
        "theme control, validation, and agent-callable outputs.",
        output_path=output,
        template="research_brief",
        style_pack="paper_ink",
        data={
            "audience": "agent infrastructure developers",
            "sections": [
                {"heading": "Template selection", "body": "Agents choose local templates."},
                {"heading": "Validation", "body": "Every PDF is validated after creation."},
            ],
        },
    )

    assert result.status == "succeeded"
    assert result.tool == "pdf.ai.create.from_prompt"
    assert result.artifacts[0].mime_type == "application/pdf"
    assert result.validation is not None
    assert result.validation.status == "passed"
    assert result.usage["template_id"] == "research_brief"
    assert result.usage["style_pack"] == "paper_ink"
    assert result.usage["agent_plan"]["steps"][0] == "select_template"
    assert "Template selection" in result.usage["generated_markdown"]
    assert output.exists()
    text = "\n".join(page.extract_text() or "" for page in PdfReader(output).pages)
    assert "local PDF agents" in text
    assert "Every PDF is validated after creation." in text


def test_create_template_catalog_returns_templates_and_style_packs() -> None:
    result = list_create_templates()

    assert result.status == "succeeded"
    assert result.tool == "pdf.ai.create.templates"
    assert result.usage["template_count"] >= 7
    assert result.usage["templates"]["research_brief"]["default_style_pack"] == "paper_ink"
    assert result.usage["templates"]["worksheet"]["default_sections"] == [
        "Learning Goal",
        "Practice",
        "Checklist",
    ]
    assert "paper_ink" in result.usage["style_packs"]
    assert result.next_recommended_tools == [
        "pdf.ai.create.template_preview",
        "pdf.ai.create.from_prompt",
    ]


def test_create_template_catalog_exposes_template_contracts_for_agents() -> None:
    result = list_create_templates()

    invoice = result.usage["templates"]["invoice"]

    assert invoice["template_kind"] == "structured_document"
    assert invoice["preview_tool"] == "pdf.ai.create.template_preview"
    assert invoice["fields"]["required"] == ["items"]
    assert "invoice_number" in invoice["fields"]["optional"]
    assert invoice["layout_slots"] == ["header", "billing", "line_items", "totals", "notes"]
    assert invoice["sample_data"]["invoice_number"] == "INV-1001"
    assert result.next_recommended_tools == [
        "pdf.ai.create.template_preview",
        "pdf.ai.create.from_prompt",
    ]


def test_create_template_preview_uses_sample_data_and_validates_pdf(tmp_path: Path) -> None:
    output = tmp_path / "invoice-preview.pdf"

    result = create_template_preview("invoice", output_path=output)

    assert result.status == "succeeded"
    assert result.tool == "pdf.ai.create.template_preview"
    assert result.validation is not None
    assert result.validation.status == "passed"
    assert result.usage["template_id"] == "invoice"
    assert result.usage["data_source"] == "template_sample_data"
    assert result.usage["preview_prompt"].startswith("Preview the Invoice template")
    assert result.usage["create_result"]["tool"] == "pdf.ai.create.from_prompt"
    assert output.exists()
    text = "\n".join(page.extract_text() or "" for page in PdfReader(output).pages)
    assert "Invoice INV-1001" in text
    assert "Template implementation" in text


def test_create_pdf_from_prompt_applies_color_overrides(tmp_path: Path) -> None:
    output = tmp_path / "branded-proposal.pdf"

    result = create_pdf_from_prompt(
        "Create a proposal about branded local PDF templates.",
        output_path=output,
        template="proposal",
        colors={"primary": "#4f46e5", "accent": "#f59e0b", "text": "#111827"},
    )

    assert result.status == "succeeded"
    assert result.usage["template_id"] == "proposal"
    assert result.usage["style_pack"] == "business_report_modern"
    assert result.usage["colors"] == {
        "primary": "#4f46e5",
        "accent": "#f59e0b",
        "text": "#111827",
    }
    assert result.usage["agent_plan"]["steps"][2] == "apply_theme"
    assert output.exists()


def test_create_invoice_template_renders_structured_items_and_totals(tmp_path: Path) -> None:
    output = tmp_path / "invoice.pdf"

    result = create_pdf_from_prompt(
        "Create an invoice for okpdf local template work.",
        output_path=output,
        template="invoice",
        data={
            "title": "Invoice INV-1001",
            "invoice_number": "INV-1001",
            "client": "OKoffice Labs",
            "due_date": "2026-06-30",
            "items": [
                {"description": "Template implementation", "quantity": 2, "unit_price": 500},
                {"description": "Validation workflow", "quantity": 1, "unit_price": 350},
            ],
            "payment_notes": "Pay by bank transfer.",
        },
    )

    assert result.status == "succeeded"
    assert result.usage["template_id"] == "invoice"
    assert result.usage["template_renderer"] == "invoice"
    markdown = result.usage["generated_markdown"]
    assert "| Template implementation | 2 | 500 | 1000 |" in markdown
    assert "| Validation workflow | 1 | 350 | 350 |" in markdown
    assert "**Total:** 1350" in markdown
    text = "\n".join(page.extract_text() or "" for page in PdfReader(output).pages)
    assert "INV-1001" in text
    assert "Template implementation" in text
    assert "1350" in text


def test_create_resume_template_renders_profile_experience_and_skills(tmp_path: Path) -> None:
    output = tmp_path / "resume.pdf"

    result = create_pdf_from_prompt(
        "Create a resume for an agent infrastructure engineer.",
        output_path=output,
        template="resume",
        data={
            "name": "Alex Agent",
            "headline": "Agent Infrastructure Engineer",
            "contact": {"email": "alex@example.com", "location": "Remote"},
            "summary": "Builds local-first document agents.",
            "skills": ["PDF tooling", "MCP", "TypeScript", "Python"],
            "experience": [
                {
                    "role": "Lead Engineer",
                    "company": "OkPDF",
                    "period": "2024-2026",
                    "bullets": [
                        "Built template-driven PDF creation.",
                        "Designed agent-readable validation reports.",
                    ],
                }
            ],
        },
    )

    assert result.status == "succeeded"
    assert result.usage["template_id"] == "resume"
    assert result.usage["template_renderer"] == "resume"
    markdown = result.usage["generated_markdown"]
    assert "# Alex Agent" in markdown
    assert "Agent Infrastructure Engineer" in markdown
    assert "- PDF tooling" in markdown
    assert "Lead Engineer - OkPDF" in markdown
    text = "\n".join(page.extract_text() or "" for page in PdfReader(output).pages)
    assert "Alex Agent" in text
    assert "PDF tooling" in text
    assert "Lead Engineer" in text
