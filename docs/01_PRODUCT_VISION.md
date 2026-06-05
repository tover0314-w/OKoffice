# 01 - Product Vision

## One-sentence Positioning

okoffice is the open-source, agent-native Office infrastructure layer for turning heterogeneous documents, data, and prompts into verified Word reports, Excel workbooks, PowerPoint decks, PDFs, and audit bundles.

## What Problem It Solves

Agents can read files and produce text, but they still struggle to reliably operate on real business artifacts:

- Word documents with sections, tables, comments, revisions, headers, footers, fields, and style systems.
- Excel workbooks with formulas, pivots, charts, assumptions, named ranges, and dashboards.
- PowerPoint decks with slide rhythm, speaker notes, charts, diagrams, media, brand systems, HTML preview packages, and visual QA.
- PDFs with page geometry, extraction ambiguity, redaction risk, render validation, and immutable delivery expectations.
- Multi-source workflows where evidence must move from PDFs and Word docs into a workbook, then into a deck and final PDF bundle.

okoffice treats Office artifacts as an agent-operable environment, not just a set of file converters.

## Product Analogy

- Firecrawl turns web pages into agent-ready context.
- OfficeCLI gives agents a command surface over Word, Excel, and PowerPoint files.
- okoffice turns heterogeneous document context into evidence-backed Office workflows and verified deliverables.

## Product Thesis

The durable enterprise output of agents is not a chat answer. It is a document pack: a report, workbook, deck, PDF, source map, validation report, and audit bundle that another human or system can trust.

The architecture starts with **context**:

- PDFs.
- Word documents.
- Excel workbooks.
- PowerPoint decks.
- Images and scans.
- Web captures.
- Markdown, HTML, text, CSV, JSON, database results, code, prompts, and review notes.

It then chooses a **target artifact profile**:

- Word report.
- Excel model.
- PowerPoint deck.
- PDF packet.
- Board pack.
- Evidence workbook.
- Research brief.
- Contract review packet.
- Training handout.
- Audit bundle.

The platform loop is:

```text
understand -> extract -> model -> compose -> operate -> verify -> report
```

Every serious action returns structured JSON, artifacts, source references, warnings, validation results, and next recommended actions.

## North-star User Stories

1. As a business agent, I can read multiple Word and PDF files, extract structured fields with source refs, and produce an Excel workbook that can be audited row by row.
2. As an analyst agent, I can turn an evidence workbook into a polished HTML-reviewed PowerPoint deck with charts, speaker notes, source refs, and PDF export.
3. As a consulting agent, I can produce a complete board pack: Word memo, Excel analysis, PowerPoint deck, PDF summary, source map, validation report, and portable bundle.
4. As a legal agent, I can inspect contracts, extract obligations, flag risks, redact sensitive material, verify redaction, and produce a review packet.
5. As a research agent, I can parse papers and reports, cite page/bbox sources, and create a literature review document or cited presentation.
6. As a developer, I can embed Office workflows through CLI, MCP, REST, Python, or TypeScript.
7. As an enterprise admin, I can self-host deterministic tools and decide which AI/cloud/optional-worker features are allowed.
8. As a support or training agent, I can turn SOPs, screenshots, videos, and docs into handouts, decks, quizzes, and searchable packets.

## Target Audiences

- Agent developers.
- AI workflow builders.
- SaaS developers needing Office automation.
- Consulting, finance, ops, and strategy teams.
- Research, legal, compliance, and audit teams.
- Education, support, and training teams.
- Enterprises with document-heavy workflows.
- Open-source developers wanting a local Office toolchain.

## Core Values

- Complete tool coverage.
- Agent-native structured outputs.
- Evidence and source traceability.
- Reliable execution and validation.
- Local-first open source.
- Cloud-optional scale.
- Beautiful documentation and artifacts.
- License-safe core.
- Security-conscious document handling.
- Honest limits for unsafe, unsupported, or unverifiable operations.

## What Complete Means

Complete means the project covers the broad Office artifact surface while adding agent-native infrastructure that traditional Office APIs, PDF SaaS tools, and simple RAG products usually lack.

Core Office breadth:

- Inspect documents, sheets, decks, and PDFs.
- Extract text, tables, formulas, charts, images, forms, annotations, comments, metadata, and source locators.
- Create Word reports, Excel workbooks, HTML-reviewed PowerPoint decks, PDFs, and bundles.
- Edit and annotate without silently mutating inputs.
- Convert across Office/PDF/HTML/Markdown/image formats.
- Validate structure, renderability, formula integrity, placeholder leakage, visual fit, redaction, and source coverage.

Agent-native breadth:

- Context packets, target artifact profiles, source graphs, and artifact lineage.
- Office IR and composition IR.
- Page/bbox/paragraph/run/sheet/range/slide/shape/timestamp/file/row citations.
- Cross-format composition and workflow plans.
- Patch transactions for explicit edits.
- Evidence coverage and citation verification.
- Workflow planning, execution, retries, and reports.
- Batch processing and audit trails.
- AI parse, RAG/evidence, extract, summarize, translate, create, edit, and review behind explicit boundaries.

Implementation depth can grow over time, but public naming and user mental model should be complete from the start.
