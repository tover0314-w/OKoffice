# 10 — CLI Specification

## Goal

Provide a beautiful, scriptable command-line interface.

## Top-level commands

```text
okpdf --help
okpdf inspect FILE
okpdf merge FILE... -o OUT.pdf
okpdf split FILE --pages 1-3,7 -o out.pdf
okpdf extract-pages FILE --pages 1-3 -o out.pdf
okpdf remove-pages FILE --pages 2,4 -o out.pdf
okpdf rotate-pages FILE --pages all --degrees 90 -o out.pdf
okpdf image-to-pdf IMAGE... -o out.pdf
okpdf render FILE --pages 1-3 --format png --out-dir renders/
okpdf extract-text FILE --pages all
okpdf create text "Hello from okpdf" -o out.pdf
okpdf create markdown input.md --style-pack plain_report -o out.pdf
okpdf watermark FILE --text "Confidential" -o out.pdf
okpdf page-numbers FILE -o out.pdf
okpdf validate FILE
okpdf serve --api
okpdf serve --mcp
okpdf tools list
okpdf tools show pdf.organize.merge
```

`agentpdf` remains available as a backwards-compatible alias.

## CLI design

- Use Typer/Rich if possible.
- Print concise human-readable output.
- Provide `--json` for machine-readable output.
- Never overwrite by default.
- Show artifact paths and validation result.
- Make errors clear and actionable.

## Example output

```text
✓ Merged 3 PDFs into merged.pdf
  Pages: 42
  Size: 4.2 MB
  SHA-256: abcd...
  Validation: passed
```

JSON mode:

```bash
agentpdf merge a.pdf b.pdf -o merged.pdf --json
```

Returns the standard `ToolResult` JSON.
