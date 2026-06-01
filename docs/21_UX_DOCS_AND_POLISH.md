# 21 — UX, Documentation, and Polish

## Brand principles

- Clear.
- Technical but not intimidating.
- Agent-first.
- Trustworthy.
- Beautiful by default.
- Honest about limitations.

## README first screen

The public README should show:

- Tagline.
- One diagram.
- Quick install.
- 5 CLI examples.
- MCP example.
- Tool family grid.
- Open-source vs cloud boundary.
- Roadmap status.

## Docs style

Use:

- Short explanations.
- Concrete examples.
- JSON snippets.
- Before/after artifacts.
- Mermaid diagrams.
- Status labels.
- Warnings for hard PDF tasks.

## CLI polish

- Use clean success indicators.
- Show concise validation results.
- Provide `--json` for agents.
- Include retry hints in errors.

## Error message style

Bad:

```text
Exception: failed
```

Good:

```text
Invalid page range: 10-20 exceeds document page count 8.
Try: agentpdf inspect report.pdf
```

## Generated PDF polish

Even OSS templates should look good. Avoid ugly default PDFs.

- Sensible margins.
- Readable typography.
- Clean headings.
- Proper page numbers.
- Good table styling.
- Stable page breaks.

## Example gallery

Create examples for:

- Merge/split workflow.
- Research paper RAG.
- Business report generation.
- Resume generation.
- Contract redaction.
- Form filling.
- PDF comparison.
- Batch processing.
