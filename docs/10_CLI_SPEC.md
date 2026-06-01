# 10 — CLI Specification

## Goal

Provide a beautiful, scriptable command-line interface.

## Top-level commands

```text
agentpdf --help
agentpdf inspect FILE
agentpdf merge FILE... -o OUT.pdf
agentpdf split FILE --pages 1-3,7 -o out.pdf
agentpdf extract-pages FILE --pages 1-3 -o out.pdf
agentpdf remove-pages FILE --pages 2,4 -o out.pdf
agentpdf rotate-pages FILE --pages all --degrees 90 -o out.pdf
agentpdf render FILE --pages 1-3 --format png --out-dir renders/
agentpdf extract-text FILE --pages all
agentpdf create text "Hello from okpdf" -o out.pdf
agentpdf create markdown input.md --style-pack plain_report -o out.pdf
agentpdf watermark FILE --text "Confidential" -o out.pdf
agentpdf page-numbers FILE -o out.pdf
agentpdf validate FILE
agentpdf serve --api
agentpdf serve --mcp
agentpdf tools list
agentpdf tools show pdf.organize.merge
```

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
