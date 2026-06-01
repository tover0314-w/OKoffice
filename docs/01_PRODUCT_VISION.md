# 01 — Product Vision

## One-sentence positioning

AgentPDF Infra is the open-source PDF API and MCP infrastructure layer for AI agents and document automation.

## What problem it solves

Agents often encounter PDFs but lack reliable tools to:

- Inspect document structure.
- Extract text, tables, images, forms, metadata, annotations, and page geometry.
- Transform pages and files safely.
- Generate new PDFs from structured content.
- Modify PDFs predictably.
- Retrieve and cite answers from PDFs.
- Validate that generated PDFs are correct.

Traditional PDF SaaS tools are human-first. Parser products are extraction-first. AgentPDF is agent-first and artifact-first.

## Product analogy

- Firecrawl turns web pages into agent-ready context.
- AgentPDF turns PDFs into agent-ready context and action artifacts.

## North-star user stories

1. As a coding agent, I can merge, split, compress, and validate PDFs without browser automation.
2. As a research agent, I can parse papers, cite page/bbox sources, and create a literature summary PDF.
3. As a business agent, I can turn messy PDFs into polished board reports.
4. As a legal agent, I can extract contract terms, flag risks, redact sensitive data, and produce a review packet.
5. As a developer, I can embed PDF tools through MCP, REST, CLI, Python, or TypeScript.
6. As an enterprise admin, I can self-host deterministic tools and decide which AI/cloud features are allowed.

## Target audiences

- Agent developers.
- AI workflow builders.
- SaaS developers needing PDF automation.
- Research and legal teams.
- Education and training teams.
- Enterprises with document-heavy workflows.
- Open-source developers wanting a local PDF toolchain.

## Core values

- Complete tool coverage.
- Reliable execution.
- Evidence-first output.
- Local-first open source.
- Cloud-optional scale.
- Beautiful documentation.
- License-safe core.
- Security-conscious document handling.

## What “complete” means

Complete means the project has a well-organized tool family covering the same broad surface as mainstream PDF SaaS products:

- Organize pages.
- Optimize files.
- Convert to/from PDF.
- Edit and annotate.
- Forms.
- Security and signatures.
- OCR and scan cleanup.
- Compare and diff.
- Metadata and attachments.
- AI parse, RAG, extract, summarize, translate, create, edit, and review.

Implementation depth can grow over time, but public naming and user mental model should be complete from the start.
