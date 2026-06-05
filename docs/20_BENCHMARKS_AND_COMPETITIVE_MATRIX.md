# 20 - Benchmarks and Competitive Matrix

## Benchmark Goal

Track whether okoffice is becoming complete, reliable, and agent-friendly across Word, Excel, PowerPoint, PDF, and cross-format workflows.

The benchmark should answer:

- Can an agent discover the right tool?
- Does the tool return structured evidence?
- Does the output validate?
- Are source refs preserved?
- Are limitations explicit?
- Can the same workflow run locally through CLI, MCP, REST, and SDK?

## Tool Coverage Matrix

Compare against mainstream PDF utilities, Office automation tools, document AI systems, and agent-native infra projects.

PDF:

- Merge, split, compress, repair.
- Convert to/from PDF.
- Render pages.
- Extract text/images.
- OCR.
- Redact.
- Protect/unlock authorized files.
- Page numbers, watermark, rotate, crop.
- Compare.
- Forms.

Word:

- Inspect package.
- Extract headings/paragraphs/tables/comments.
- Detect tracked changes and metadata.
- Create report.
- Patch paragraph/table/comment.
- Validate styles, accessibility, render preview.

Excel:

- Inspect workbook.
- Extract sheets/tables/formulas/charts/named ranges.
- Detect hidden sheets and external links.
- Create evidence workbook.
- Validate formulas and chart refs.
- Create/validate financial model.

PowerPoint:

- Inspect deck.
- Extract slides/shapes/notes/media/charts.
- Create deck from claim spine.
- Validate contact sheet.
- Patch slide text/chart/notes.

Cross-format:

- DOCX/PDF to evidence workbook.
- Workbook to deck.
- Report/deck/workbook to PDF handout.
- Bundle export/verify.
- Source map and artifact graph.
- Patch plan/apply/verify.

## Agent-Readiness Matrix

For each tool, score:

- CLI support.
- MCP support.
- REST support.
- SDK support.
- JSON schema.
- Structured ToolResult.
- Validation report.
- Artifact manifest.
- Source refs.
- Stable error code.
- Tests.
- Docs examples.
- OSS/cloud boundary.

## Quality Benchmarks

PDF:

- Correct page counts.
- Render success rate.
- Blank page detection.
- Visual diff accuracy.
- Redaction verification.

Word:

- Heading/paragraph/table extraction accuracy.
- Comment/tracked-change detection.
- Style preservation.
- Metadata removal verification.
- Render preview consistency.

Excel:

- Sheet/table/range detection.
- Formula reference correctness.
- Formula error detection.
- Named range extraction.
- Chart source binding accuracy.
- Hidden/external-link detection.

PowerPoint:

- Slide count and order.
- Shape/text extraction.
- Notes extraction.
- Media relationship detection.
- Contact-sheet render success.
- Placeholder overflow warnings.

Cross-format:

- Source-ref coverage.
- Claim citation correctness.
- Number consistency from workbook to deck/report.
- Bundle verification.
- Workflow replayability.

## Performance Tiers

Track by file and workflow size:

- Tiny: 1-5 pages/slides/sheets.
- Small: 6-50 pages/slides or up to 10 sheets.
- Medium: 51-300 pages/slides or up to 50 sheets.
- Large: 301-1000 pages/slides or large workbooks.
- Huge: >1000 pages/slides or enterprise batches.

For workbooks, also track:

- Formula count.
- Cell count.
- Chart count.
- External link count.

## Public Benchmark Page

A future docs page should show transparent status:

```text
Tool                         Status     CLI  MCP  API  SDK  Tests  Validation
pdf.organize.merge           stable     yes  yes  yes  yes  yes    yes
pdf.validation.render_check  stable     yes  yes  yes  yes  yes    yes
word.inspect.document        beta       yes  yes  yes  yes  yes    yes
word.validation.document     beta       yes  yes  yes  yes  yes    yes
sheet.inspect.workbook       beta       yes  yes  yes  yes  yes    yes
deck.inspect.presentation    beta       yes  yes  yes  yes  yes    yes
office.context.build_packet  beta       yes  yes  yes  yes  yes    yes
office.extract.schema        beta       yes  yes  yes  yes  yes    yes
office.workflow.docset_to_sheet beta       yes  yes  yes  yes  yes    yes
deck.create.presentation     beta       yes  yes  yes  yes  yes    yes
office.workflow.sheet_to_deck beta       yes  yes  yes  yes  yes    yes
deck.validation.contact_sheet beta       yes  yes  yes  yes  yes    yes
deck.validation.presentation beta       yes  yes  yes  yes  yes    yes
office.bundle.export       beta       yes  yes  yes  yes  yes    yes
office.bundle.verify       beta       yes  yes  yes  yes  yes    yes
word.create.report         beta       yes  yes  yes  yes  yes    yes
office.workflow.board_pack beta       yes  yes  yes  yes  yes    yes
```

## Competitive Lens

okoffice should be judged against:

- PDF utilities for breadth and self-hosted ergonomics.
- Office automation tools for DOCX/XLSX/PPTX structure control, plus HTML-first preview routes for visual deck quality.
- Document AI systems for extraction and evidence quality.
- Agent toolkits for MCP/REST/SDK friendliness.
- OfficeCLI-style projects for schema-driven, single-binary Office operations.

The winning bar is not "can it produce a file once"; it is "can an agent reliably produce, validate, cite, patch, and explain the file locally."
