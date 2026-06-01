# 13 — Validation and Diff

## Principle

PDF operations are not done until the output is validated.

Agents need evidence, not just `success: true`.

## Validation checks

### Always-on checks

- File exists.
- File size > 0.
- PDF opens.
- Page count readable.
- Pages render or renderer dependency warning is emitted.
- Artifact checksum generated.

### Conditional checks

- Expected page count.
- No blank pages.
- Text layer exists.
- Form fields filled.
- Redacted text removed.
- Metadata removed.
- Compression ratio target.
- Visual diff threshold.
- PDF/A compliance.
- Signature verification.

## Validation report model

```json
{
  "valid": true,
  "summary": "All required checks passed.",
  "checks": [
    {
      "name": "page_count",
      "passed": true,
      "expected": 12,
      "actual": 12
    }
  ],
  "warnings": [],
  "render_previews": []
}
```

## Visual diff

For edit operations, optionally render before/after pages and compute differences.

Return:

- Changed pages.
- Difference score.
- Preview images.
- Warnings for unexpected changes.

## Redaction verification

True redaction must:

- Remove text from extraction.
- Remove or modify image regions where needed.
- Avoid merely placing a black rectangle overlay.
- Re-render and search for redacted strings.

## Agent recommendations

Validation report may include:

```json
{
  "next_recommended_tools": ["pdf.compare.visual_diff", "pdf.security.remove_metadata"]
}
```
