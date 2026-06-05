# 36 - okoffice Agent-native Office Infra PRD

Date: 2026-06-04

Status: Draft for product and implementation migration

## 1. Product Summary

okoffice is agent-native Office infrastructure for local and hosted workflows across Word, Excel, PowerPoint, PDF, and document bundles.

The product starts from a simple user goal:

```text
Use these documents and data to create the artifact I need.
```

It then executes an auditable workflow:

```text
ingest sources -> extract evidence -> create model/workbook -> compose report/deck/PDF -> validate -> export bundle
```

The current AgentPDF/okpdf harness becomes the PDF domain inside okoffice. Existing `pdf.*` tools stay compatible while new `office.*` tools define the broader target surface.

## 2. Why This Product Should Exist

Real document work rarely ends in one file type.

Examples:

- A consultant reads PDFs and Word memos, builds an Excel analysis, and presents a PowerPoint board deck.
- A legal reviewer extracts contract terms into a spreadsheet, writes a Word risk memo, and exports a redacted PDF packet.
- A research agent reads papers, builds a citation matrix, and generates a cited presentation.
- A finance agent turns messy supporting documents into a forecast workbook and management deck.

Existing tools are fragmented:

- PDF tools are file-operation-first.
- Office automation libraries are format-first.
- RAG tools are answer-first.
- Chat agents are flexible but weak at artifact verification.

okoffice is workflow-first and evidence-first.

## 3. Reference Learnings

### OfficeCLI

OfficeCLI is an important reference because it treats Office files as agent-operable artifacts. Its public project emphasizes:

- Single binary, no Office installation.
- `.docx`, `.xlsx`, and `.pptx` read/create/modify support.
- Structured JSON output.
- Schema-driven help.
- Built-in MCP server.
- HTML/screenshot/watch preview loop.
- Three-layer operation model: read, DOM edit, raw XML.
- Specialized skills for Word, Excel, PowerPoint, dashboards, financial models, pitch decks, academic papers, and animated decks.

Source: [OfficeCLI GitHub](https://github.com/iOfficeAI/OfficeCLI)

okoffice should not simply clone this low-level surface. It should support optional Office workers like OfficeCLI while owning the higher-level workflow contract: source graph, evidence coverage, composition IR, validation, and artifact bundles.

### Microsoft Office Agent

Microsoft's Office Agent material is a strong taste and architecture signal for presentation generation:

- It frames deck creation as taste-driven development rather than simple file generation.
- It describes specialized agents that create HTML5 slides before converting the result into editable PowerPoint output.
- It treats visual review and refinement as part of the product loop.
- It reinforces an OKoffice requirement: PPTX should be the editable delivery artifact, while HTML preview packages, contact sheets, validation reports, and source maps are the agent-observable creation layer.

Sources: [Microsoft Tech Community Office Agent post](https://techcommunity.microsoft.com/blog/microsoft365copilotblog/office-agent-%E2%80%93-%E2%80%9Ctaste-driven%E2%80%9D-multi-agent-system-for-microsoft-365-copilot/4457397), [Microsoft Source Asia Office Agent article](https://news.microsoft.com/source/asia/2025/09/30/office-agent-%E6%89%93%E9%80%A0%E5%93%81%E5%91%B3%E9%A9%B1%E5%8A%A8%E7%9A%84%E5%A4%9A%E6%99%BA%E8%83%BD%E4%BD%93%E7%B3%BB%E7%BB%9F%EF%BC%8C%E5%85%A8%E9%9D%A2/?lang=zh-hans)

### Word/DOCX Skill Lessons

Good Word output is not just text in a `.docx` file. The document layer needs:

- Outline and heading hierarchy.
- Styles, sections, headers, footers, page fields, TOCs, tables, comments, tracked changes, and metadata.
- Render/preview QA when possible.
- Placeholder leakage detection.
- Live-field caveats and field-presence verification.
- Template preservation for edits.

### Excel/XLSX Skill Lessons

Good workbook output is not just a grid. The sheet layer needs:

- Formula integrity and zero formula-error policy.
- Source-backed assumptions.
- Explicit widths, number formats, tables, filters, named ranges, charts, pivots, dashboards, and print layout.
- Cached-value sanity checks.
- Visual preview for truncation, `###`, broken charts, and placeholder leakage.

### PowerPoint/PPTX Skill Lessons

Good decks need narrative and visual QA:

- Claim spine.
- One idea per slide.
- Proof objects, charts, screenshots, diagrams, or visuals on content slides.
- Speaker notes.
- Explicit typography, grid, palette, contrast, and layout rules.
- HTML-first slide preview as the taste-driven creation surface before PPTX export when available.
- Contact-sheet or per-slide screenshot QA.
- Template-following mode for existing decks.

## 4. Product Principles

1. **Office is the artifact surface, not just file conversion**
   The core product is a workflow engine that can reason across documents, sheets, decks, PDFs, and bundles.

2. **Evidence beats fluent prose**
   Every generated table, claim, chart, slide, and report section should preserve source refs where possible.

3. **Validation is part of creation**
   Generated artifacts must include structural validation, render/preview evidence, blank/overflow/token checks, and limitations.

4. **Local-first means useful without cloud**
   Deterministic read/create/validate workflows should run locally. Model-enabled workflows are explicit optional layers.

5. **PDF remains first-class**
   PDF is still critical for delivery, validation, redaction, audit packets, and source extraction. It is no longer the only product surface.

6. **No silent mutation**
   Inputs are immutable. Edits produce new artifacts and patch manifests.

7. **Workers are pluggable**
   OfficeCLI, LibreOffice, artifact-tool, browser renderers, and future native workers can sit behind the same okoffice worker interface.

8. **Beautiful by default**
   Reports, workbooks, decks, PDFs, README examples, CLI output, and validation reports should look intentional.

## 5. Target Product Surface

### CLI

```bash
okoffice inspect source.docx --json
okoffice inspect workbook.xlsx --json
okoffice context build --file brief.docx --file diligence.pdf --file metrics.xlsx -o context.json --json
okoffice extract schema context.json --schema examples/schemas/kpi-review.json -o evidence.xlsx --json
okoffice deck compose-plan evidence.xlsx -o board-review.plan.json --profile board_review --json
okoffice deck render-html board-review.plan.json -o board-review.html --json
okoffice deck export-pptx board-review.html -o board-review.pptx --json
okoffice export pdf board-review.pptx -o board-review.pdf --json
okoffice bundle export --file evidence.xlsx --file board-review.pptx --file board-review.pdf -o board-pack.zip --json
```

### MCP

Agents should discover stable tools such as:

```text
office.context.ingest
office.context.packet
office.word.inspect
office.sheet.inspect
office.deck.inspect
office.pdf.inspect
office.extract.schema
sheet.write.workbook
office.deck.create
office.document.create_report
office.convert.to_pdf
office.validation.validate_artifact
office.workflow.docset_to_sheet
office.workflow.sheet_to_deck
office.workflow.board_pack
office.bundle.export
```

### REST

REST mirrors the same tool names and returns the same `ToolResult` envelope:

```http
POST /v1/tools/office.workflow.board_pack/run
```

## 6. Target Namespaces

Do not immediately delete existing `pdf.*` names. Treat them as a compatibility domain.

Target okoffice namespaces:

- `office.context.*`
- `office.source.*`
- `office.ir.*`
- `office.word.*`
- `office.sheet.*`
- `office.deck.*`
- `office.pdf.*`
- `office.extract.*`
- `office.compose.*`
- `office.convert.*`
- `office.patch.*`
- `office.evidence.*`
- `office.validation.*`
- `office.workflow.*`
- `office.bundle.*`
- `office.agent.setup.*`

Compatibility:

- Existing `pdf.*` tools remain valid.
- `office.pdf.*` can eventually wrap or alias `pdf.*`.
- The Python package may remain `agentpdf` until a compatibility plan introduces `okoffice`.

## 7. Core Data Model

### Context Packet

Holds inputs and intent:

```json
{
  "context_packet_id": "ctxpkt_...",
  "intent": "Create a board review from diligence documents and metrics.",
  "items": [
    {"type": "word_document", "uri": "brief.docx", "source_ref": "src_docx_001"},
    {"type": "pdf", "uri": "diligence.pdf", "source_ref": "src_pdf_001"},
    {"type": "workbook", "uri": "metrics.xlsx", "source_ref": "src_xlsx_001"}
  ]
}
```

### Source Locator

Source refs need format-specific locators:

```json
{
  "source_id": "src_xlsx_001",
  "locator": {
    "sheet": "Revenue",
    "range": "B4:F18",
    "row": 8,
    "column": "D"
  }
}
```

Other locator shapes include:

- PDF page and bbox.
- Word paragraph/run/table cell/comment/revision.
- PowerPoint slide/shape/table cell/chart/notes.
- Image region.
- Transcript timestamp.
- Code file line range.
- Web URL and text fragment.

### Office IR

Office IR describes parsed source artifacts and planned target artifacts. It should preserve both semantic and visual facts:

- Document outline.
- Tables.
- Formulas.
- Charts.
- Slides and shapes.
- Notes and comments.
- Media.
- Fields and metadata.
- Geometry and render warnings.
- Source refs and confidence.

### Artifact Bundle

A workflow should be able to export:

- Final artifacts.
- Intermediate artifacts.
- Source map.
- Validation reports.
- Warnings and limitations.
- Checksums.
- Tool execution trace.

## 8. Hero Workflows

### `office.workflow.docset_to_sheet`

Input:

- Multiple PDFs, Word docs, emails, notes, or web captures.
- Extraction schema.

Output:

- Evidence workbook.
- Source map by row/cell.
- Confidence report.
- Missing-field report.

### `office.workflow.sheet_to_deck`

Input:

- Workbook or structured JSON.
- Deck profile and style constraints.

Output:

- HTML slide preview package.
- Editable `.pptx`.
- Optional PDF export.
- Speaker notes.
- Chart and source map.
- Visual validation report.

### `office.workflow.board_pack`

Input:

- Source documents.
- Desired audience and board-pack profile.

Output:

- Evidence workbook.
- Word memo.
- PowerPoint deck.
- PDF executive summary.
- Portable audit bundle.

### `office.workflow.review_and_patch`

Input:

- Existing Office/PDF artifact.
- Requested change.

Output:

- Patch manifest.
- Preview.
- New artifact.
- Validation and diff report.

## 9. Validation Requirements

Every generated artifact must include a validation object. Required checks vary by format.

Word:

- OpenXML/schema validation when available.
- Outline/heading sanity.
- Placeholder leakage.
- Table overflow/truncation.
- Field presence for page numbers/TOC when used.
- Metadata safety.
- Render/preview evidence when available.

Excel:

- Formula error scan.
- Cached-value sanity for summary cells when available.
- `###` and truncation scan.
- Chart source and empty-anchor checks.
- Pivot/table/named-range integrity.
- Source note coverage for assumptions.

PowerPoint:

- Slide count and order.
- Shape bounds.
- Text overflow.
- Placeholder leakage.
- Contrast checks.
- Speaker notes coverage.
- HTML preview package safety, offline renderability, and source refs.
- Per-slide screenshot/contact-sheet QA when available.

PDF:

- Page count.
- Renderability.
- Blank page detection.
- Text-layer checks where relevant.
- Redaction verification when relevant.
- Visual diff when relevant.

Bundle:

- Manifest integrity.
- SHA-256 checksums.
- Source map completeness.
- Artifact existence and retention hints.

## 10. Open-source / Cloud Boundary

Open source:

- Deterministic local CLI/MCP/REST.
- Schemas and tool registry.
- Basic inspect/extract/create/validate.
- Context packets and source graphs.
- Local workflows with deterministic or optional-worker execution.
- Examples and docs.

Optional or hosted:

- Model extraction.
- VLM/OCR at scale.
- Managed rendering.
- Long-running batch workers.
- Persistent artifact storage.
- Team/workspace/account/billing features.
- Enterprise policy, audit logs, SSO, VPC/on-prem.

## 11. Migration Plan From AgentPDF

Phase 1:

- Rewrite product docs to okoffice.
- Keep existing `pdf.*` manifest and code.
- Add target namespace docs and PRD.

Phase 2:

- Add `office.*` schemas and aliases without removing `pdf.*`.
- Add format-specific fixtures and validation tests.
- Add `office.context.*` wrappers over current context tools.

Phase 3:

- Implement DOCX/XLSX/PPTX inspect and validation.
- Implement `docset_to_sheet` and the source-mapped `sheet_to_deck` planning path.
- Expand the deck HTML preview/export beta (`deck.render.html`, `deck.validation.html_preview`, `deck.export.pptx`) from the local baseline toward richer worker-backed rendering and export.
- Add worker abstraction.

Phase 4:

- Introduce `okoffice` CLI/package while keeping compatibility entrypoints.
- Expand MCP and REST tool catalog.
- Publish examples and docs site.

## 12. Success Criteria

The first okoffice release succeeds if a developer can run a local workflow like:

```bash
okoffice workflow board-pack \
  --file diligence.pdf \
  --file memo.docx \
  --file metrics.xlsx \
  --out-dir .okoffice-out/board-pack \
  --json
```

and receive:

- An evidence workbook.
- A polished deck.
- A PDF export.
- A validation report.
- A source map.
- A bundle manifest.
- Honest warnings and next recommended tools.
