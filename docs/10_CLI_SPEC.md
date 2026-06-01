# 10 — CLI Specification

## Goal

Provide a beautiful, scriptable command-line interface.

## Top-level commands

```text
okpdf --help
okpdf inspect FILE
okpdf inspect-pages FILE --pages 1-3 --render-check
okpdf workflow plan --goal "Chat with this PDF and cite answers" --input-path FILE
okpdf workflow run workflow.json --artifact-dir .agentpdf-out/workflows/run --binding "<question>=What are the risks?"
okpdf workflow report run-result.json -o workflow-report.md
okpdf merge FILE... -o OUT.pdf
okpdf split FILE --pages 1-3,7 -o out.pdf
okpdf extract-pages FILE --pages 1-3 -o out.pdf
okpdf remove-pages FILE --pages 2,4 -o out.pdf
okpdf rotate-pages FILE --pages all --degrees 90 -o out.pdf
okpdf reorder-pages FILE --order 3,1,2 -o out.pdf
okpdf insert-blank-pages FILE --after-page 1 --count 2 -o out.pdf
okpdf compress FILE -o out.pdf
okpdf repair FILE -o out.pdf
okpdf image-to-pdf IMAGE... -o out.pdf
okpdf render FILE --pages 1-3 --format png --out-dir renders/
okpdf extract-images FILE --pages all --out-dir extracted-images/
okpdf extract-text FILE --pages all
okpdf create text "Hello from okpdf" -o out.pdf
okpdf create markdown input.md --style-pack plain_report -o out.pdf
okpdf watermark FILE --text "Confidential" -o out.pdf
okpdf page-numbers FILE -o out.pdf
okpdf validate FILE
okpdf render-check FILE --pages 1-3
okpdf blank-page-check FILE --pages all
okpdf parse-lite FILE
okpdf pdf-to-json FILE -o out.ir.json
okpdf pdf-to-markdown FILE -o out.md
okpdf rag ingest FILE --index index.json
okpdf rag chat FILE --question "What are the risks?" --report-output rag-report.pdf --highlight-output highlighted.pdf
okpdf rag query index.json --query "What are the risks?"
okpdf rag search index.json --query "risk margin"
okpdf rag cite-answer index.json --answer "The document describes risk margin."
okpdf rag highlight-sources index.json --answer "The document describes risk margin." -o highlighted.pdf
okpdf rag export-report index.json --question "What are the risks?" --answer "The document describes risk margin." -o rag-report.pdf
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
