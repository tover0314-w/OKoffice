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

## 11. Multi-source business report

```text
pdf.context.packet -> pdf.target.select_profile -> pdf.compose.plan -> pdf.compose.render_ir -> pdf.evidence.coverage_report -> pdf.validation.validate_output -> pdf.artifacts.export_bundle
```

Inputs may include PDFs, spreadsheets, screenshots, Markdown notes, and web links/captures. The output target profile may be a business report, board deck, or appendix packet with source refs, appendix material, and validation warnings.

## 12. Video to presentation PDF

```text
pdf.context.video_transcribe -> pdf.context.video_keyframes -> pdf.target.select_profile -> pdf.compose.plan -> pdf.present.create_deck -> pdf.evidence.coverage_report -> pdf.validation.render_check
```

Cloud/optional by default because transcription, keyframe extraction, and slide planning consume compute/model resources. A local demo may use pre-supplied transcript and images.

Expected outputs:

- Slide-like PDF.
- Speaker notes.
- Transcript appendix.
- Timestamp citations.
- Source map.
- Validation report.

## 13. Image evidence packet

```text
pdf.context.ingest -> pdf.context.image_analyze -> pdf.target.select_profile -> pdf.compose.compile_packet -> pdf.evidence.coverage_report -> pdf.validation.validate_output
```

Use for screenshots, scans, field photos, legal evidence, QA reports, or operational reviews. Local baseline can accept manually described images and render an evidence packet with source refs.

## 14. Code repository to audit PDF

```text
pdf.context.code_snapshot -> pdf.target.select_profile -> pdf.compose.plan -> pdf.compose.add_code_block -> pdf.compose.render_ir -> pdf.evidence.coverage_report -> pdf.validation.validate_output
```

The output should include code snippets with file/line refs, dependency notes, warnings, and a reviewer-ready PDF report.

## 15. PDF patch transaction

```text
pdf.inspect.document -> pdf.ai.parse.lite -> pdf.patch.plan -> pdf.patch.preview -> pdf.patch.apply -> pdf.patch.verify -> pdf.validation.visual_diff -> pdf.artifacts.export_bundle
```

Use when an agent needs to insert figures, code blocks, appendices, highlights, revised summaries, or evidence pages into an existing PDF. The input file must never be silently mutated.

## 16. Research paper to cited deck

```text
pdf.ai.parse.lite -> pdf.evidence.cite_claims -> pdf.present.paper_to_deck -> pdf.evidence.coverage_report -> pdf.validation.render_check
```

Return a slide-like PDF with claim citations, figure/table references, and a source appendix.

## 17. Compliance and redaction packet

```text
pdf.ai.parse.lite -> pdf.ai.review.sensitive_data_detect -> pdf.security.redact -> pdf.security.verify_redaction -> pdf.evidence.context_packet_report -> pdf.workflow.report
```

Return redacted artifacts, true redaction verification, metadata removal status, warnings, and a review packet for audit handoff.
