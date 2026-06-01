# 24 — Workflow Recipes

This file describes agent workflows as tool chains.

Agents can use `pdf.workflow.plan` first to turn a natural-language goal into ordered local tool steps, agent roles, validation checks, and cloud-boundary notes. Concrete manifests can then run through `pdf.workflow.run`, which executes supported local tools in order and returns per-step evidence. The run can be closed with `pdf.workflow.report`, which summarizes status, artifacts, warnings, and failed steps for agent handoff.

## 1. Basic merge and validate

```text
pdf.inspect.document -> pdf.organize.merge -> pdf.validation.validate_output
```

Agent behavior:

1. Inspect inputs.
2. Reject encrypted PDFs unless credentials are supplied.
3. Merge.
4. Validate expected page count.
5. Return output artifact and checksum.

## 2. Split report into executive summary and appendix

```text
pdf.inspect.document -> pdf.organize.extract_pages -> pdf.validation.validate_output
```

## 3. Research paper RAG

```text
pdf.inspect.document -> pdf.ai.parse.lite -> pdf.ai.rag.ingest -> pdf.ai.rag.query -> pdf.ai.rag.export_report -> pdf.ai.rag.highlight_sources
```

Return answer, cited chunks, page numbers, bboxes, a cited answer report PDF, and a highlighted source PDF.

One-shot local agent shortcut:

```text
pdf.ai.rag.chat
```

Use this when an agent wants the whole local chat evidence packet from one PDF and one question.

## 4. Scanned PDF to searchable PDF

```text
pdf.inspect.document -> pdf.ocr_scan.auto_rotate -> pdf.ocr_scan.deskew -> pdf.ocr_scan.ocr -> pdf.validation.text_layer_check
```

## 5. Contract redaction packet

```text
pdf.ai.parse.lite -> pdf.ai.review.sensitive_data_detect -> pdf.security.redact -> pdf.security.verify_redaction -> pdf.validation.visual_diff
```

## 6. Business report generation

```text
source docs -> pdf.ai.parse.lite -> pdf.ai.extract.schema -> pdf.ai.create.report -> pdf.validation.validate_output
```

Open-source baseline can replace AI creation with Markdown + style pack.

## 7. Resume generation

```text
resume.json/markdown -> pdf.convert.markdown_to_pdf(style=resume_modern) -> pdf.validation.validate_output
```

## 8. Bilingual translation workflow

```text
pdf.inspect.document -> pdf.ai.parse.agentic -> pdf.ai.translate.bilingual_pdf -> pdf.validation.visual_diff
```

Cloud-only by default because it consumes model tokens and complex layout handling.

## 9. PDF compare and review

```text
pdf.compare.text_diff -> pdf.compare.visual_diff -> pdf.compare.version_report
```

## 10. Batch folder processing

```text
for each PDF:
  pdf.inspect.document -> selected tool -> pdf.validation.validate_output
aggregate:
  batch.report
```

Batch orchestration should be an OSS workflow later, but cloud can monetize high concurrency.
