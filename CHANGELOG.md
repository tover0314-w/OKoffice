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
- **Phase 5**: Registered 6 beta alias tools (office.workflow.extract_to_sheet, office.workflow.source_to_board_pack, word.read.document, word.write.document, sheet.edit.patch, word.edit.patch).
- **Phase 6**: Added deck template/spec-lock/animation tools:
  - `deck.template.list`, `deck.template.preview`, `deck.create.from_template` — template-driven deck creation.
  - `deck.spec_lock.create`, `deck.spec_lock.check_drift` — design specification locking and drift detection.
  - `deck.animation.apply` — CSS animation recipes for HTML slide content.
- **Phase 7**: Migrated Node SDK from agentpdf-node to okoffice-node.
- **Phase 8**: Added Cursor and OpenAI Agents MCP config generators (6 agent platforms total).
- **Resume/ATS**: Registered `pdf.resume.create_resume` and `pdf.validation.ats_compliance_check`.
- **Composition IR Patch**: Registered `pdf.patch.composition_ir.plan`, `pdf.patch.composition_ir.apply`, `pdf.patch.composition_ir.verify`.
- **Deck enhancements**: Added deck_animations, deck_backgrounds, deck_svg2pptx, deck_templates, deck_spec_lock modules. 16 HTML slide templates + 10 SVG layouts.
- **okoffice-shell**: Added Electron desktop application with MCP client, LLM providers, and React UI.
- **Dependencies**: Added openpyxl>=3.1 for chart creation.
- **Tests**: 910 tests passing.

### Fixed

- Added missing MCP server imports (run_workflow_plan, run_watermark).
- Updated doctor.py to check okoffice-node instead of agentpdf-node.
- Fixed 6 MCP catalog maps_to naming mismatches.
- Fixed MCP catalog server_name from agentpdf to okoffice.
- Registered missing deck tools in MCP server (template, spec_lock, animation, create_from_template).
- Added deck_validation_presentation alias handler and catalog entry.
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
