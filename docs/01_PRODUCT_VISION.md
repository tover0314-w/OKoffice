# 01 - Product Vision

## One-sentence positioning

AgentPDF Infra is the open-source, agent-native infrastructure layer for turning heterogeneous context into specific, verifiable PDF artifacts such as learning PDFs, resumes, papers, deck-like PDFs, reports, packets, and audits.

## What problem it solves

Agents often encounter PDFs, images, videos, code, spreadsheets, web pages, and business data but lack reliable infrastructure to turn those materials into trustworthy document deliverables.

They need tools to:

- Inspect document structure and safety before acting.
- Extract text, tables, images, forms, metadata, annotations, page geometry, timestamps, code references, and data ranges.
- Transform pages and files safely.
- Compose polished target PDFs from heterogeneous context.
- Insert rich content such as images, charts, code blocks, callouts, citations, and appendices.
- Generate slide-like presentation PDFs, reports, packets, briefs, and handouts.
- Modify existing PDFs predictably through patch transactions.
- Retrieve and cite evidence from context materials.
- Validate that generated or edited PDFs are correct, renderable, traceable, and safe.

Traditional PDF SaaS tools are human-first. Parser products are extraction-first. Simple RAG products are question-answering-first. AgentPDF is agent-first, artifact-first, and verification-first.

## Product analogy

- Firecrawl turns web pages into agent-ready context.
- AgentPDF turns heterogeneous context into agent-ready actions and evidence-backed target PDF artifacts.

## Product thesis

PDF should be treated as an agent-operable environment and a durable delivery artifact, not just a file format.

The architecture starts with **context**: images, videos, documents, PDFs, code, spreadsheets, databases, network links, prompts, and review notes. It then chooses a **target PDF profile**: learning PDF, resume PDF, academic paper PDF, PPT/deck-like PDF, business report, evidence packet, training handout, worksheet, code audit, or formal document.

The product should support this loop:

```text
understand -> compose -> operate -> verify -> report
```

Every serious action should return structured JSON, artifacts, source references, warnings, validation results, and next recommended actions.

## North-star user stories

1. As a coding agent, I can merge, split, compress, validate, and package PDFs without browser automation.
2. As a research agent, I can parse papers, cite page/bbox sources, and create a literature summary PDF or slide-like presentation PDF.
3. As a business agent, I can turn messy PDFs, spreadsheets, screenshots, and meeting videos into polished board reports and decks.
4. As a legal agent, I can extract contract terms, flag risks, redact sensitive data, verify redaction, and produce a review packet.
5. As a developer, I can embed PDF tools through MCP, REST, CLI, Python, or TypeScript.
6. As an enterprise admin, I can self-host deterministic tools and decide which AI/cloud features are allowed.
7. As a support or training agent, I can turn videos, screenshots, SOPs, and product docs into handouts, worksheets, and presentation PDFs.
8. As an audit agent, I can create PDFs with code snippets, file references, dependency findings, logs, and evidence appendices.

## Target audiences

- Agent developers.
- AI workflow builders.
- SaaS developers needing PDF and document automation.
- Research and legal teams.
- Education, support, and training teams.
- Business operations, finance, and consulting teams.
- Enterprises with document-heavy workflows.
- Open-source developers wanting a local PDF toolchain.

## Core values

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

## What complete means

Complete means the project has a well-organized tool family covering the same broad surface as mainstream PDF SaaS products while adding agent-native infrastructure that those tools usually lack.

Core PDF breadth:

- Organize pages.
- Optimize files.
- Convert to/from PDF.
- Edit and annotate.
- Forms.
- Security and signatures.
- OCR and scan cleanup.
- Compare and diff.
- Metadata and attachments.
- Validation and repair.

Agent-native breadth:

- Context packets, target PDF profiles, source graph, and artifact lineage.
- Document IR and composition IR.
- Page/bbox/timestamp/file/row citations.
- Multimodal-to-PDF composition.
- PDF patch transactions.
- Presentation PDF generation.
- Evidence coverage and citation verification.
- Workflow planning, execution, retries, and reports.
- Batch processing and audit trails.
- AI parse, RAG/evidence, extract, summarize, translate, create, edit, and review.

Implementation depth can grow over time, but public naming and user mental model should be complete from the start.
