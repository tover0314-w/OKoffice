# 12 — PDF Creation and Style Packs

## Goal

AgentPDF should generate polished PDFs for many contexts:

- Business reports.
- Consulting reports.
- Academic papers.
- Research briefs.
- Resumes.
- Invoices.
- Contracts.
- Product datasheets.
- Training materials.
- Education worksheets.
- Startup pitch handouts.
- Annual reports.
- Financial reports.
- Government/formal documents.

## Style pack schema

A style pack defines layout, fonts, colors, spacing, components, and document structure.

```json
{
  "style_id": "business_report_modern",
  "name": "Business Report Modern",
  "description": "Clean board-report style with executive summary and metric cards.",
  "page": {
    "size": "A4",
    "orientation": "portrait",
    "margins": {"top": 56, "right": 56, "bottom": 56, "left": 56}
  },
  "typography": {
    "heading_font": "system-sans",
    "body_font": "system-sans",
    "base_size": 10
  },
  "components": [
    "cover",
    "toc",
    "section_header",
    "metric_card",
    "table",
    "callout",
    "appendix"
  ]
}
```

## Open-source style packs

Initial open-source packs:

- `plain_report`
- `business_report_modern`
- `academic_paper_basic`
- `resume_modern`
- `resume_classic`
- `invoice_clean`
- `contract_plain`
- `research_brief`
- `training_handout`
- `education_worksheet`

## AI generation boundary

Open-source deterministic mode:

```text
Markdown/HTML/JSON + style pack -> PDF
```

Future AI mode:

```text
prompt/source documents -> generated content/IR -> styled PDF
```

## UX requirements

Generated PDFs should include:

- Consistent spacing.
- Good typography.
- Proper page breaks.
- Optional cover page.
- Optional table of contents.
- Headers/footers.
- Page numbers.
- Validation report.

## Template examples

See `examples/style-packs/`.
