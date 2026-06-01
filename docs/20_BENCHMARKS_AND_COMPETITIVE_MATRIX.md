# 20 — Benchmarks and Competitive Matrix

## Benchmark goal

Track whether AgentPDF is becoming complete, reliable, and agent-friendly.

## Tool coverage matrix

Compare against mainstream PDF SaaS categories:

- Merge.
- Split.
- Compress.
- Convert to PDF.
- Convert from PDF.
- Edit.
- OCR.
- Sign.
- Redact.
- Protect/unlock.
- Page numbers.
- Watermark.
- Rotate.
- Crop.
- Compare.
- Repair.
- Forms.
- AI summarize.
- AI translate.
- AI RAG.
- AI create.
- AI edit.

## Agent-readiness matrix

For each tool, score:

- MCP support.
- REST support.
- CLI support.
- JSON output.
- Validation report.
- Artifact manifest.
- Error code.
- Tests.
- Docs.

## Quality benchmarks

- Correct page counts.
- Render success rate.
- Output file size.
- Processing time.
- Compression ratio.
- OCR confidence.
- Extraction accuracy.
- Table extraction accuracy.
- Citation correctness.
- Redaction verification.

## Performance tiers

Track:

- Tiny: 1-5 pages.
- Small: 6-50 pages.
- Medium: 51-300 pages.
- Large: 301-1000 pages.
- Huge: >1000 pages.

## Public benchmark page

A future docs page should show transparent status:

```text
Tool                Status     CLI  MCP  API  Tests  Validation
merge               stable     yes  yes  yes  yes    yes
split               stable     yes  yes  yes  yes    yes
compress            stable     yes  yes  yes  yes    yes
repair              beta       yes  yes  yes  yes    yes
pdf_to_docx         planned    no   no   no   no     no
agentic_parse       cloud      no   no   no   no     no
```
