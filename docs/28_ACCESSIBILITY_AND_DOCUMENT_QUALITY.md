# 28 - Accessibility and Document Quality

## Goal

Generated artifacts should be readable, well-structured, and eventually accessible across Word, Excel, PowerPoint, and PDF.

Quality is not cosmetic. For agent-native Office workflows, quality means the file is understandable to humans, inspectable by agents, and safe to validate or patch later.

## Open-Source Baseline

All formats:

- Clear structure.
- Useful metadata without sensitive leakage.
- Source refs where generated from evidence.
- Validation report.
- Warnings for unsupported quality checks.

Word:

- Semantic headings.
- Named styles.
- Tables with headers.
- Figure/table captions.
- Comments/tracked changes policy.
- Metadata/privacy report.

Excel:

- Typed tables.
- Freeze panes where useful.
- Clear input/calculation/output separation.
- No formula errors.
- Chart source ranges.
- Source-ref columns for extracted evidence.

PowerPoint:

- One main claim per slide where appropriate.
- Readable typography.
- Consistent layouts.
- Speaker notes when required.
- Meaningful chart/table titles.
- Contact-sheet render validation when available.

PDF:

- Good typography.
- Clear headings.
- Page numbers.
- Sensible reading order where generated.
- Text layer present.
- Avoid rasterizing text when possible.
- Render and blank-page checks.

## Future Accessibility Tools

Target tools:

- `word.validation.accessibility`
- `sheet.validation.accessibility`
- `deck.validation.accessibility`
- `pdf.ai.review.accessibility_check`
- `office.review.document_quality`

Future checks:

- Tag/semantic structure inspection.
- Alt text detection.
- Reading order verification.
- Contrast checks.
- Table header checks.
- Slide title checks.
- PDF/UA-oriented validation where feasible.

## Agent Behavior

When creating Office artifacts, agents should prefer:

- Semantic headings.
- Tables with headers.
- Descriptive figure captions.
- Slide titles that summarize the claim.
- Charts with clear axes and source notes.
- Speaker notes for evidence-heavy decks.
- Avoiding tiny fonts.
- Avoiding color-only meaning.
- Recording limitations rather than hiding them.

## Validation

Generated artifacts should include a quality report separate from strict technical validation.

Example:

```json
{
  "quality": {
    "format": "pptx",
    "checks": [
      {"name": "slide_titles", "status": "passed"},
      {"name": "speaker_notes", "status": "warning", "message": "2 slides lack speaker notes."},
      {"name": "contact_sheet", "status": "passed"}
    ]
  }
}
```

Quality reports should be visible in CLI, MCP, REST, SDK, and bundles.
