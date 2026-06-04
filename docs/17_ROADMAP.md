# 17 - Roadmap

## Phase 0 - okoffice Product Reset

Status: in progress.

Deliverables:

- okoffice-first README.
- product strategy.
- tool taxonomy.
- cloud business model.
- agent infrastructure plan.
- implementation order.
- legacy PDF compatibility rules.

## Phase 1 - Namespace And Manifest Foundation

Goal: make okoffice discoverable without breaking current compatibility tools.

Deliverables:

- `okoffice` CLI alias.
- target manifest sections for `office.*`, `word.*`, `sheet.*`, `deck.*`, and `pdf.*`.
- status labels for implemented, planned, optional worker, cloud-only, and legacy compatibility.
- MCP/REST/SDK naming strategy.

## Phase 2 - Office IR And Source Graph

Goal: define the structured model agents use across formats.

Deliverables:

- Office IR schemas.
- native locators for Word, Excel, PowerPoint, and PDF.
- source graph examples.
- artifact manifest extensions.
- validation report extensions.

## Phase 3 - Deterministic Inspect

Goal: locally inspect Office artifacts without cloud or Office desktop.

Deliverables:

- `office.inspect.file`.
- `word.inspect.document`.
- `sheet.inspect.workbook`.
- `deck.inspect.presentation`.
- fixture suite for DOCX/XLSX/PPTX.

## Phase 4 - Validation Baseline

Goal: validate package health and common risks.

Deliverables:

- `office.validation.package`.
- `word.validation.document`.
- `sheet.validation.formulas`.
- `deck.validation.presentation`.
- macro/external-link/hidden-content warnings.
- optional worker capability reports.

## Phase 5 - Evidence Workbook

Goal: make `docset_to_sheet` real.

Deliverables:

- Office-aware context packets.
- schema extraction from mixed sources.
- evidence workbook creation.
- source refs per row/cell.
- coverage reports.

## Phase 6 - Workbook To Deck

Goal: turn evidence workbooks into editable presentations.

Deliverables:

- deck composition plan.
- PowerPoint creation.
- workbook range/chart source refs.
- speaker notes.
- contact-sheet validation or structured worker skip.

## Phase 7 - Board Pack

Goal: deliver the flagship workflow.

Deliverables:

- evidence workbook.
- Word memo.
- PowerPoint deck.
- optional PDF handout.
- source map.
- validation reports.
- okoffice bundle export/verify.

## Phase 8 - Optional Workers

Goal: add heavyweight capabilities without bloating OSS core.

Deliverables:

- OfficeCLI adapter investigation.
- LibreOffice/render worker.
- browser renderer.
- OCR.
- formula engine.
- BYOK/model routing.
- worker capability matrix.

## Phase 9 - Hosted Service

Goal: monetize convenience, scale, persistence, connectors, and governance.

Deliverables:

- API keys.
- async jobs.
- queues.
- webhooks.
- artifact/source graph persistence.
- batch workflows.
- managed connectors.
- team/org controls.
- enterprise deployment options.

## Compatibility Baseline

Current `pdf.*` tools remain useful and should stay stable. New PDF work should support okoffice workflows, safety, validation, or compatibility rather than expanding a separate PDF product.
