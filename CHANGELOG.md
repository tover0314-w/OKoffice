# Changelog

This file follows Keep a Changelog style once implementation begins.

## 0.1.0 — 2026-06-06

### Added

- **Phase 1**: Registered 9 already-implemented tools (office.workflow.plan, office.manifest.show, word.extract.tables, sheet.read.workbook, sheet.profile.data, sheet.extract.tables, sheet.create.evidence_workbook, sheet.validate.workbook, deck.review.taste).
- **Phase 2**: Added 8 alias tools for cross-namespace access (office.artifacts.bundle, word.extract.structure, word.convert.to_pdf, word.convert.from_pdf, pdf.read.document, pdf.convert.to_docx/xlsx/pptx).
- **Phase 3**: Added 3 workflow orchestrators (office.workflow.source_to_deck, office.workflow.source_to_doc, deck.export.pdf).
- **Phase 4**: Implemented 5 new tools:
  - `office.workflow.multi_format_brief` — inspect mixed-format files and build structured briefs.
  - `word.comment.review` — review and resolve Word comments via OOXML patching.
  - `sheet.visualize.chart` — create charts (bar/line/pie/area/scatter) in Excel workbooks.
  - `deck.edit.apply_theme` — apply color themes to PPTX decks via OOXML manipulation.
  - `pdf.extract.tables` — detect and extract tables from PDF text layers.
- **Phase 7**: Migrated Node SDK from agentpdf-node to okoffice-node.
- **Phase 8**: Added Cursor and OpenAI Agents MCP config generators (6 agent platforms total).
- **Dependencies**: Added openpyxl>=3.1 for chart creation.
- **Tests**: 788 tests passing, including 11 new Phase 4 validation tests.

### Fixed

- Added missing MCP server imports (run_workflow_plan, run_watermark).
- Updated doctor.py to check okoffice-node instead of agentpdf-node.
- Fixed 6 MCP catalog maps_to naming mismatches.
- Removed duplicate office.validate.output from target manifest.
- Fixed agent integration test assertions (agentpdf -> okoffice tool manifest).
- Fixed chart.py empty data validation, word_comments.py silent resolve_ids discard, range string validation.
- Removed dead imports across Phase 4 modules.
- Standardized job_id format (12-char -> 16-char) in brief_builder.py.
- Replaced binary file text preview with safe skip message.

## 0.0.0-harness — 2026-06-01

### Added

- Codex development harness.
- Open-source project specification.
- Complete tool catalog.
- MCP/API/CLI/IR schema drafts.
- Security, contribution, governance, testing, and roadmap docs.
