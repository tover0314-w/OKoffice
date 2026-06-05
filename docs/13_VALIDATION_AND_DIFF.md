# 13 - Validation and Diff

## Principle

Office operations are not done until the output is validated.

Agents need evidence, not just `success: true`.

For okoffice, validation is format-aware:

- PDF validation checks renderability, page count, blank pages, text layer, redaction, and visual diff.
- Word validation checks schema, outline, fields, tables, metadata, placeholder leakage, and preview evidence.
- Excel validation checks formulas, cached values, charts, pivots, named ranges, truncation, source notes, and placeholder leakage.
- PowerPoint validation checks slide order, shape bounds, text overflow, contrast, speaker notes, HTML preview package evidence, screenshot/contact-sheet evidence, and placeholder leakage.
- Bundle validation checks manifest completeness, checksums, artifact existence, source maps, and validation report links.

## Always-on Checks

All artifact kinds:

- File exists.
- File size > 0.
- Artifact checksum generated.
- Input artifacts were not silently mutated.
- Artifact kind and MIME type are recorded.
- Source tool is recorded.
- Warnings are explicit.

Generated artifacts:

- Placeholder leakage check for patterns such as `{{`, `}}`, `<TODO>`, `lorem`, `xxxx`, `$fy$24`, and unfilled template tokens.
- Metadata safety check.
- Embedded-object/macro/external-link warning where relevant.
- Source coverage check when claims, rows, charts, slides, or generated sections depend on source evidence.

## PDF Checks

- PDF opens.
- Page count readable.
- Pages render or renderer dependency warning is emitted.
- No unexpected blank pages.
- Text layer exists when expected.
- Form fields filled when expected.
- Redacted text removed.
- Metadata removed when requested.
- Compression ratio target when relevant.
- PDF/A compliance when relevant.
- Signature verification when relevant.
- Visual diff threshold for edit operations.

## Word Checks

- DOCX opens or parser can inspect the package.
- Schema validation when a local validator is available.
- Heading hierarchy is coherent.
- Tables fit expected width or emit overflow warnings.
- Page fields/TOC fields exist when used.
- Comments and tracked changes are preserved or explicitly handled.
- Headers/footers are present when expected.
- Placeholder leakage check passes.
- Preview/render evidence exists when a local renderer is available.

## Excel Checks

- Workbook opens or parser can inspect the package.
- Formula error scan for `#REF!`, `#DIV/0!`, `#VALUE!`, `#NAME?`, and `#N/A`.
- Summary formula cached values are plausible when available.
- Required sheets, tables, named ranges, and pivots exist.
- Charts have non-empty anchors and source ranges.
- No visible `###` truncation in preview.
- Assumption/input cells have source notes when the workflow requires auditability.
- Placeholder leakage check passes.
- Preview/render evidence exists when a local renderer is available.

## PowerPoint Checks

- Deck opens or parser can inspect the package.
- HTML slide preview package exists for generated decks when the target route is used.
- HTML preview package is offline-renderable and rejects unsafe remote assets/scripts.
- Slide count and order match plan.
- Shape bounds stay within slide dimensions.
- Text does not overflow shapes.
- Placeholder leakage check passes.
- Speaker notes exist on content slides when the profile requires them.
- Contrast warnings are emitted for dark backgrounds with dark text.
- Charts/tables/images have expected source refs when generated from evidence.
- Taste rules are checked: one claim per slide, evidence on content slides, readable visual density, and non-duplicated section rhythm where configured.
- Per-slide screenshot or contact-sheet preview exists when a local renderer is available.

## Bundle Checks

- Bundle manifest exists.
- Every listed artifact exists.
- SHA-256 checksums match.
- Validation report links resolve.
- Source map exists when required.
- Parent/child artifact lineage is recorded.
- Retention hints are included.

## Validation Report Model

```json
{
  "status": "passed",
  "summary": "All required checks passed.",
  "checks": [
    {
      "name": "artifact_exists",
      "status": "passed",
      "details": {"path": ".okoffice-out/board-review.pptx"}
    },
    {
      "name": "placeholder_leakage_check",
      "status": "passed",
      "details": {"matches": []}
    }
  ],
  "warnings": [],
  "render_previews": []
}
```

## Visual Diff

For edit operations, optionally render before/after pages, slides, sheets, or document previews and compute differences.

Return:

- Changed artifact regions.
- Changed pages/slides/sheets.
- Difference score.
- Preview images.
- Warnings for unexpected changes.

## Redaction Verification

True redaction must:

- Remove text from extraction.
- Remove or modify image regions where needed.
- Avoid merely placing a black rectangle overlay.
- Re-render and search for redacted strings.
- Remove metadata and embedded traces when requested.

For Office files, redaction must also consider:

- Comments.
- Revisions/tracked changes.
- Headers/footers.
- Speaker notes.
- Hidden sheets.
- Formulas and named ranges.
- Embedded objects and alt text.

## Worker Unavailability

When a local renderer or Office worker is missing, tools should not pretend validation passed.

Return structured evidence:

```json
{
  "name": "deck_html_preview_or_render_check",
  "status": "skipped",
  "details": {
    "reason": "worker_unavailable",
    "worker": "deck_html_preview_or_office_renderer",
    "retry_hint": "Install an optional browser/Office preview worker or run the check in hosted mode."
  }
}
```

## Agent Recommendations

Validation report may include:

```json
{
  "next_recommended_tools": [
    "office.validation.visual_diff",
    "office.security.remove_metadata",
    "office.evidence.coverage_report"
  ]
}
```

Compatibility PDF tools may continue to recommend `pdf.compare.visual_diff` or `pdf.security.remove_metadata`.
