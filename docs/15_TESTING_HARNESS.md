# 15 - Testing Harness

## Test Philosophy

Office tools require more than unit tests. okoffice must verify package integrity, structured output, rendered previews when available, formula correctness, source maps, artifact manifests, and safety warnings.

The current PDF-domain tests remain important. The migration adds Word, Excel, PowerPoint, and cross-format workflow tests without weakening the existing PDF contract.

## Test Categories

### Unit Tests

- Path safety and package entry validation.
- Page, slide, and cell range parsers.
- Tool registry and manifest consistency.
- Pydantic schema validation.
- Artifact manifest and checksum generation.
- Error codes.
- Style pack and artifact profile loading.
- Source Graph and Office IR serialization.

### Integration Tests

- CLI commands.
- REST endpoints.
- MCP tools.
- Core PDF operations.
- DOCX/XLSX/PPTX inspect tools.
- Validation reports.
- Cross-format workflows.
- Bundle export/verify.

### Golden PDF Tests

Use small fixture PDFs:

- `simple_text.pdf`
- `multi_page.pdf`
- `with_metadata.pdf`
- `with_annotations.pdf`
- `with_form.pdf`
- `scanned_like.pdf`
- `encrypted_known_password.pdf`
- `corrupt_repairable.pdf`
- `image_heavy.pdf`

Checks:

- Page count.
- Renderability.
- Blank pages.
- Expected watermark/page number location.
- Redaction verification.
- Unexpected full-page differences.

### Golden DOCX Tests

Use small fixture Word files:

- `simple_report.docx`
- `with_headings.docx`
- `with_tables.docx`
- `with_comments.docx`
- `with_tracked_changes.docx`
- `with_metadata.docx`

Checks:

- Package opens and relationships are safe.
- Heading/paragraph/table/comment counts.
- Style extraction.
- Metadata detection/removal.
- Tracked changes policy.
- Optional rendered preview when a renderer is configured.

### Golden XLSX Tests

Use small fixture workbooks:

- `simple_table.xlsx`
- `with_formulas.xlsx`
- `with_charts.xlsx`
- `with_named_ranges.xlsx`
- `with_hidden_sheet.xlsx`
- `with_external_link.xlsx`

Checks:

- Sheet list and used ranges.
- Table extraction.
- Formula refs and formula errors.
- Named ranges.
- Chart source refs.
- Hidden sheet and external link warnings.
- CSV formula-injection guards where relevant.

### Golden PPTX Tests

Use small fixture decks:

- `simple_deck.pptx`
- `with_notes.pptx`
- `with_charts.pptx`
- `with_images.pptx`
- `with_hidden_slide.pptx`
- `with_theme.pptx`

Checks:

- Slide count and slide order.
- Shape/text extraction.
- Placeholder detection.
- Speaker notes policy.
- Media relationships.
- Theme/layout facts.
- Optional contact-sheet render.

### Cross-Format Workflow Tests

Target workflows:

- Multiple DOCX/PDF sources to cited XLSX workbook.
- XLSX workbook to PowerPoint deck.
- Word report plus workbook plus deck to PDF handout and bundle.
- Patch plan/apply/verify across Word, Excel, PowerPoint, and PDF.
- Bundle export/verify with source map and validation reports.

Every generated artifact should have:

- Manifest entry.
- SHA-256 checksum.
- Format-specific validation.
- Warnings list.
- Next recommended tools.

### Security Tests

- Path traversal rejected.
- Oversized files rejected by configurable limits.
- Unsafe ZIP/package entries rejected.
- Unauthorized encrypted PDFs rejected.
- Macro-enabled files reported but not executed.
- External links reported and disabled by default.
- Hidden sheets/slides/comments/tracked changes surfaced.
- Redaction verification fails if sensitive content remains.

## Acceptance Commands

Current compatibility commands:

```bash
pytest -q
agentpdf tools list --json
agentpdf inspect tests/fixtures/simple_text.pdf --json
agentpdf merge tests/fixtures/simple_text.pdf tests/fixtures/multi_page.pdf -o .agentpdf-out/merged.pdf --json
agentpdf validate .agentpdf-out/merged.pdf --json
```

Target okoffice commands:

```bash
okoffice tools list --json
okoffice inspect tests/fixtures/simple_report.docx --json
okoffice inspect tests/fixtures/simple_table.xlsx --json
okoffice inspect tests/fixtures/simple_deck.pptx --json
okoffice workflow docset-to-sheet tests/fixtures/simple_report.docx tests/fixtures/simple_text.pdf -o .okoffice-out/evidence.xlsx --json
okoffice workflow sheet-to-deck .okoffice-out/evidence.xlsx -o .okoffice-out/deck.pptx --json
okoffice bundle verify .okoffice-out/board-pack.okoffice.zip --json
```

## CI Expectations

GitHub Actions should run:

- Python lint.
- Type check.
- Unit tests.
- Integration smoke tests.
- Manifest/docs consistency tests.
- License/dependency scan if feasible.
- Docs link check if feasible.

Office-specific CI should keep fixtures tiny and license-safe. Heavy renderers, OCR, formula engines, and conversion workers should be optional jobs or feature-flagged matrix entries.

## Fixture Generation

Prefer generating fixtures in tests or scripts using permissive libraries to avoid copyright issues.

Include scripts such as:

```bash
python scripts/generate_fixtures.py
python scripts/generate_office_fixtures.py
```

Generated fixtures must be small, reproducible, and documented.
