# 24 - okoffice Workflow Recipes

This file describes agent workflows as tool chains. okoffice workflows produce Office artifacts and bundles, not just PDFs.

Use this sequence as the default mental model:

```text
inspect -> build source graph -> extract evidence -> create artifact -> validate -> bundle
```

## 1. Docset To Evidence Workbook

Core workflow:

```text
office.inspect.batch
-> office.context.build_packet
-> office.extract.schema
-> sheet.create.evidence_workbook
-> sheet.validation.formulas
-> office.evidence.coverage
```

Inputs:

- Word contracts.
- PDF reports.
- spreadsheets.
- Markdown notes.
- web captures.

Outputs:

- `.xlsx` evidence workbook;
- source refs per row/cell;
- missing-field report;
- confidence report;
- validation report.

## 2. Evidence Workbook To Executive Deck

```text
sheet.inspect.workbook
-> sheet.extract.tables
-> deck.compose.plan
-> deck.create.presentation
-> deck.validation.contact_sheet
```

Outputs:

- editable `.pptx`;
- chart/range source refs;
- speaker notes;
- contact-sheet validation;
- slide warnings.

## 3. Board Pack

Flagship workflow:

```text
office.workflow.docset_to_sheet
-> word.create.report
-> office.workflow.sheet_to_deck
-> pdf.create.handout
-> office.bundle.export
-> office.bundle.verify
```

Current local OSS slice:

```text
office.context.build_packet
-> office.workflow.extract_to_sheet --context-packet
-> office.workflow.sheet_to_deck
-> office.workflow.board_pack
-> office.bundle.verify
```

Direct-file compatibility slice:

```text
office.workflow.extract_to_sheet
-> office.workflow.sheet_to_deck
-> office.workflow.board_pack
-> office.bundle.verify
```

Outputs:

- evidence workbook;
- Word memo;
- PowerPoint deck;
- PDF handout;
- source map;
- validation reports;
- portable `.okoffice.zip` bundle.

## 4. Contract Portfolio Review

```text
office.context.build_packet
-> office.extract.obligations
-> sheet.create.evidence_workbook
-> word.create.report
-> office.evidence.coverage
-> office.bundle.export
```

Use when extracting renewals, obligations, risks, owners, and money terms from many contracts.

## 5. Financial Model Review

```text
sheet.inspect.workbook
-> sheet.extract.formulas
-> sheet.validation.formulas
-> sheet.review.model
-> deck.create.presentation
-> office.bundle.export
```

Quality gates:

- formula references;
- external links;
- hidden sheets;
- hardcoded assumptions;
- chart source ranges;
- number consistency across workbook and deck.

## 6. Research To Brief And Deck

```text
office.context.build_packet
-> office.extract.claims
-> office.evidence.verify_citations
-> word.create.report
-> deck.create.presentation
-> office.bundle.export
```

Outputs:

- cited Word report;
- cited deck;
- source appendix;
- citation validation report.

## 7. Review And Patch

```text
office.inspect.file
-> office.patch.plan
-> office.patch.preview
-> office.patch.apply
-> office.patch.verify
-> office.validation.package
```

Rules:

- never mutate inputs;
- target native locators;
- write a new artifact;
- verify patch lineage;
- report ambiguous/stale locators.

## 8. Redaction Packet

```text
office.inspect.batch
-> office.security.detect_sensitive_data
-> office.patch.plan
-> office.patch.apply
-> office.security.verify_redaction
-> office.bundle.export
```

Format-specific checks:

- PDF text/image content;
- Word comments/tracked changes/metadata;
- Excel hidden sheets/comments/formulas/names;
- PowerPoint notes/hidden slides/off-slide shapes/media.

## Legacy PDF Compatibility Recipes

These remain valid for the current implementation but are not the okoffice product center.

### PDF Merge And Validate

```text
pdf.inspect.document -> pdf.organize.merge -> pdf.validation.validate_output
```

### Local PDF RAG

```text
pdf.ai.parse.lite -> pdf.ai.rag.ingest -> pdf.ai.rag.query -> pdf.ai.rag.cite_answer
```

### PDF HTML Package Render

```text
pdf.create.html_package -> pdf.render.html_package -> pdf.validation.render_check
```

Compatibility recipes should migrate upward when their concepts become cross-format:

- `pdf.context.*` to `office.context.*`;
- `pdf.evidence.*` to `office.evidence.*`;
- `pdf.patch.*` to `office.patch.*`;
- `pdf.artifacts.*` to `office.bundle.*`;
- `pdf.workflow.*` to `office.workflow.*`.
