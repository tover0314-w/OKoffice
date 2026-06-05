# 37 - okoffice Product Strategy

## Thesis

okoffice is agent-native Office infrastructure. It should let agents inspect, extract, create, edit, validate, cite, and bundle Word documents, Excel workbooks, PowerPoint decks, PDFs, and related evidence artifacts through local-first tools.

The product is not a PDF suite. PDF is one important format domain inside a larger Office workflow platform.

## Primary User

The first user is a coding or workflow agent operating on local files:

- Codex-style coding agents.
- Claude Code / Claude Desktop through MCP.
- Cursor and IDE agents.
- Kilo Code and OpenClaw-style runtimes.
- OpenAI Agents.
- LangChain and LlamaIndex pipelines.
- SaaS builders calling REST/SDK tools.

Humans benefit from the generated artifacts, but agents are the first-class tool callers.

## Core Promise

okoffice should make this reliable:

```text
read many messy source files
-> extract cited evidence
-> build a workbook/model
-> create a report and HTML-reviewed deck
-> export a PDF packet
-> validate everything
-> ship an audit bundle
```

Every tool call should produce evidence:

- structured JSON;
- artifact refs;
- source refs;
- native locators;
- validation reports;
- warnings;
- next recommended tools.

## Strategic Pillars

### 1. Local-first OSS

The local core must work without hosted URLs, paid accounts, or proprietary keys. Deterministic inspect/extract/validate/create basics should stay free.

### 2. Office-native structure

Do not flatten everything into text too early. Preserve native format structure:

- Word paragraphs, sections, comments, tables, styles, fields, and revisions.
- Excel sheets, ranges, formulas, tables, charts, pivots, names, comments, and validation.
- PowerPoint slides, shapes, placeholders, notes, media, themes, and charts.
- PDF pages, bboxes, annotations, signatures, attachments, text layers, and render evidence.

### 3. Evidence-backed creation

Creation is not just generation. It is source-backed composition with traceability:

- each row can cite a source;
- each chart can cite a range;
- each slide claim can cite evidence;
- each report paragraph can cite sources;
- each PDF packet can validate page/render output.

### 4. Format-specific validation

Every output needs validation appropriate to its format:

- Word: styles, comments, revisions, metadata, accessibility hints, render preview.
- Excel: formulas, ranges, charts, hidden sheets, external links, checks.
- PowerPoint: slide count, notes, placeholders, media, HTML preview package, contact sheet, and editable PPTX export evidence.
- PDF: page count, renderability, blank pages, metadata, redaction.
- Bundle: hashes, manifest, artifact graph, source coverage.

### 5. Taste-driven deck creation

Decks are judged by story and visual quality, not only by valid OOXML. The target OKoffice route is `deck.compose.plan -> deck.render.html -> deck.validation.html_preview -> deck.validation.contact_sheet -> deck.export.pptx -> deck.validate.presentation`. Direct PPTX writing remains useful as a local fallback and compatibility path, but the product direction is HTML-first preview, then editable PowerPoint delivery.

### 6. Explicit cloud boundary

Cloud is for heavy workers, scale, persistence, connectors, and governance. Cloud must not be a hidden dependency of local deterministic tools.

## What To Remove From Mainline Positioning

Remove or demote these ideas from primary docs:

- PDF-only product framing.
- "AI PDF" as the category.
- PDF RAG as the core product.
- Huge PDF command walls in the README.
- Claims that PDF creation/editing is the main roadmap.
- Hosted PDF SaaS language.
- More PDF utility breadth as the default next step.

These topics may remain in legacy compatibility docs when they describe currently implemented behavior.

## Product Scenarios

### Board Pack

Inputs:

- contracts;
- diligence PDFs;
- metric spreadsheets;
- meeting notes;
- prior decks.

Outputs:

- evidence workbook;
- executive memo;
- board deck;
- PDF handout;
- okoffice bundle.

### Research To Brief

Inputs:

- papers;
- notes;
- figures;
- spreadsheets;
- source snippets.

Outputs:

- cited Word report;
- evidence table workbook;
- presentation deck;
- source appendix.

### Financial Review

Inputs:

- model workbook;
- quarterly PDF reports;
- forecast notes.

Outputs:

- validated workbook;
- formula risk report;
- deck of findings;
- executive PDF packet.

### Contract Portfolio

Inputs:

- many Word/PDF contracts;
- amendments;
- invoice files.

Outputs:

- obligation workbook;
- renewal calendar;
- risk memo;
- redaction report;
- bundle.

## Non-Goals For The Near Term

- Perfect arbitrary layout-preserving edits.
- Full Office desktop replacement.
- Macro execution.
- Cloud-only default workflows.
- Full visual design app.
- Hosted billing inside OSS core.
- Large connector ecosystem before local contracts are stable.

## Product North Star

An agent should be able to answer:

```text
What files did I use, what did I extract, what did I create,
what evidence supports it, what validation passed,
what warnings remain, and what should I run next?
```

If okoffice answers that across Word, Excel, PowerPoint, and PDF, it becomes infrastructure rather than another converter.
