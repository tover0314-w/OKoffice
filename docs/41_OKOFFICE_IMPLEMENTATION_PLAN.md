# 41 - okoffice Implementation Plan

## Principle

Stop adding broad PDF-only features by default. New work should move the repository toward okoffice unless it is required for compatibility, safety, or test stability.

## Phase 1 - Naming And Documentation Reset

Deliverables:

- okoffice-first README.
- Product strategy doc.
- Tool taxonomy doc.
- Cloud business doc.
- Agent infra doc.
- Legacy PDF compatibility doc.
- Updated Codex start and backlog docs.

Acceptance:

- README presents okoffice as the product.
- `okoffice/okoffice/pdf.*` appears as compatibility.
- Docs and registry tests pass.

## Phase 2 - okoffice Namespace Skeleton

Deliverables:

- `okoffice` CLI alias.
- target manifest scaffold for `office.*`, `word.*`, `sheet.*`, `deck.*`.
- MCP/REST naming strategy.
- SDK naming strategy.

Acceptance:

- Existing `okoffice` still works.
- `okoffice tools list --json` can show target and implemented tools without breaking current `pdf.*`.

## Phase 3 - Office IR And Source Locators

Deliverables:

- Office IR schemas.
- Source Graph extensions.
- Native locator models for Word/Excel/PPT/PDF.
- Artifact manifest extensions.

Acceptance:

- Schemas serialize and validate.
- Example source graph can reference a Word paragraph, Excel range, PowerPoint shape, and PDF bbox.

## Phase 4 - Deterministic Inspect MVP

Deliverables:

- `office.inspect.file`.
- `word.inspect.document`.
- `sheet.inspect.workbook`.
- `deck.inspect.presentation`.
- small fixtures.

Acceptance:

- DOCX inspect reports headings, paragraphs, tables, comments, styles, metadata markers.
- XLSX inspect reports sheets, ranges, formulas, tables, charts, names, hidden/external markers.
- PPTX inspect reports slides, text, notes, shapes, media, theme markers.
- Tools return ToolResult.

## Phase 5 - Validation MVP

Deliverables:

- `word.validation.document`.
- `sheet.validation.formulas` as structural formula QA.
- `deck.validation.presentation`.
- `office.validation.package`.

Acceptance:

- Unsafe package entries fail.
- Macro/external-link/hidden-content risks are warnings.
- Formula references and errors are reported where possible.
- Optional worker unavailability is structured.

## Phase 6 - Evidence Workbook Workflow

Deliverables:

- `office.context.build_packet` for DOCX/PDF/XLSX/PPTX sources.
- `office.extract.schema`.
- `sheet.create.evidence_workbook` as the okoffice-first evidence workbook writer.
- `office.evidence.coverage`.

Acceptance:

- Multiple Word/PDF sources produce a workbook with source-ref columns.
- Missing/low-confidence fields are warnings.
- Workbook validates structurally.

## Phase 7 - Sheet To Deck Workflow

Deliverables:

- `deck.compose.plan`.
- `deck.render.html` as the taste-driven HTML slide preview package writer.
- `deck.validation.html_preview`.
- `deck.validation.contact_sheet`.
- `deck.export.pptx`.
- `deck.create.presentation` as the okoffice-first convenience command; current beta direct PPTX writer, target HTML-first orchestrator.
- workbook-to-deck example.

Acceptance:

- Workbook tables/charts become a source-mapped deck plan and HTML preview package.
- The HTML preview package records slide ids, DOM anchors, style tokens, source refs, and render profile evidence.
- Editable PPTX export preserves slide order, speaker notes, and source-map links back to the plan/HTML package where feasible.
- Slides include source refs and speaker notes where configured.
- Contact-sheet worker absence returns structured skip.

## Phase 8 - Board Pack Bundle

Deliverables:

- `word.create.report`.
- `office.workflow.board_pack`.
- `office.bundle.export`.
- `office.bundle.verify`.

Acceptance:

- Workflow emits workbook, memo, deck, optional PDF packet, source map, validation report, and bundle.
- Bundle verifies hashes and expected artifacts.

## Phase 9 - Optional Workers

Deliverables:

- OfficeCLI adapter investigation.
- LibreOffice/render adapter contract.
- OCR worker contract.
- Formula engine contract.
- AI provider routing contract.

Acceptance:

- Workers are feature-flagged.
- License notes are explicit.
- Core works without them.

## Phase 10 - Hosted Surface

Deliverables:

- API key design.
- async jobs.
- artifact retention.
- source graph persistence.
- batch workflows.
- connector contracts.

Acceptance:

- Hosted design does not alter local ToolResult contract.
