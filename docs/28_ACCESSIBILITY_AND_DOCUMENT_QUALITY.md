# 28 — Accessibility and Document Quality

## Goal

Generated PDFs should be readable, well-structured, and eventually accessible.

## Open-source baseline

- Good typography.
- Clear headings.
- Page numbers.
- Sensible reading order where generated.
- Text layer present.
- Avoid rasterizing text when possible.

## Future accessibility tools

- `pdf.ai.review.accessibility_check`
- Tag structure inspection.
- Alt text detection.
- Reading order verification.
- Contrast checks for generated PDFs.
- PDF/UA-oriented validation where feasible.

## Agent behavior

When creating PDFs, agents should prefer:

- Semantic headings.
- Tables with headers.
- Descriptive figure captions.
- Avoiding tiny fonts.
- Avoiding color-only meaning.

## Validation

Generated PDFs should include a quality report separate from strict technical validation.
