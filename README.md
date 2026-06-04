<p align="center">
  <img src="assets/brand/okpdf-logo.png" alt="okoffice logo" width="160" />
</p>

<h1 align="center">okoffice</h1>

<p align="center">
  Local-first, agent-native Office infrastructure for Word, Excel, PowerPoint, PDF, bundles, CLI, MCP, REST, and SDK workflows.
</p>

<p align="center">
  <a href="https://github.com/tover0314-w/okpdf"><img alt="GitHub repo" src="https://img.shields.io/badge/github-okoffice-0b1220"></a>
  <img alt="Python" src="https://img.shields.io/badge/python-3.11%2B-blue">
  <img alt="TypeScript" src="https://img.shields.io/badge/typescript-sdk-3178c6">
  <img alt="Node.js" src="https://img.shields.io/badge/node.js-20%2B-339933">
  <img alt="License" src="https://img.shields.io/badge/license-Apache--2.0-green">
  <img alt="Local first" src="https://img.shields.io/badge/local--first-yes-brightgreen">
  <img alt="MCP" src="https://img.shields.io/badge/MCP-ready-purple">
</p>

<p align="center">
  <a href="README.md">English</a>
  |
  <a href="README.zh-CN.md">Simplified Chinese</a>
  |
  <a href="docs/i18n/README.md">Translation guide</a>
</p>

okoffice is the open-source foundation for agent-native Office workflows. It gives coding agents and local automation systems a structured way to inspect, extract, create, edit, validate, cite, and bundle Word documents, Excel workbooks, PowerPoint decks, PDFs, and evidence-backed artifacts.

The old project identity was `agentpdf` / `okpdf`. Those names are now legacy compatibility surfaces for the current PDF-domain implementation. The product direction is okoffice.

## The Product Loop

```text
many sources
  -> source graph
  -> evidence extraction
  -> workbook/model
  -> Word report + PowerPoint deck + PDF packet
  -> validation
  -> portable okoffice bundle
```

The flagship workflow:

```text
multiple Word/PDF sources -> cited Excel workbook -> polished PowerPoint deck -> executive memo -> PDF handout -> audit bundle
```

## Why This Exists

- Agents need structured tools, not one-off scripts.
- Office files need native locators: paragraphs, tables, comments, cells, formulas, charts, slides, shapes, notes, pages, and bboxes.
- Generated artifacts need validation evidence, not just `success: true`.
- Local OSS should work without a cloud account.
- Cloud should add workers, connectors, persistence, batch scale, and governance without becoming a hidden dependency.

## Target Tool Surface

| Domain | Example tools |
|---|---|
| Inspect | `office.inspect.file`, `word.inspect.document`, `sheet.inspect.workbook`, `deck.inspect.presentation`, `pdf.inspect.document` |
| Extract | `word.extract.tables`, `sheet.extract.formulas`, `deck.extract.notes`, `office.extract.schema` |
| Create | `word.create.report`, `sheet.create.evidence_workbook`, `deck.create.presentation`, `pdf.create.handout` |
| Patch | `office.patch.plan`, `word.patch.apply`, `sheet.patch.apply`, `deck.patch.apply` |
| Validate | `word.validation.document`, `sheet.validation.formulas`, `deck.validation.contact_sheet`, `pdf.validation.render_check` |
| Evidence | `office.context.build_packet`, `office.evidence.coverage`, `office.source_map.create` |
| Workflow | `office.workflow.docset_to_sheet`, `office.workflow.sheet_to_deck`, `office.workflow.board_pack` |
| Bundle | `office.bundle.export`, `office.bundle.verify` |
| Agents | `office.agent.setup.codex`, `office.agent.setup.claude_code`, `office.agent.setup.cursor` |

The current machine manifest still contains **241** public `pdf.*` and agent setup tools. That manifest is preserved for compatibility while the okoffice namespace is introduced deliberately.

## What Works Today

The runnable implementation is the legacy PDF domain:

- CLI command: `okpdf`
- Internal Python package: `agentpdf`
- Current TypeScript package: `@okpdf/agentpdf-node`
- Current namespaces: `pdf.*` and `agent.setup.*`

This compatibility layer already provides local PDF inspect, organize, render, validate, metadata, RAG-lite, workflow, artifact, patch, MCP, REST, and Node SDK surfaces. It is useful, but it is no longer the product boundary.

See [docs/42_LEGACY_PDF_COMPATIBILITY.md](docs/42_LEGACY_PDF_COMPATIBILITY.md) for the compatibility rules.

## What Comes Next

The next implementation work should not add more PDF-only breadth by default. Build okoffice in this order:

1. Add `okoffice` CLI and package-level naming without breaking `okpdf`.
2. Add okoffice tool manifest scaffolding above the current `pdf.*` manifest.
3. Add Office IR and source locator schemas.
4. Add deterministic DOCX/XLSX/PPTX inspect tools.
5. Add Word/Excel/PowerPoint validation reports.
6. Add `office.workflow.docset_to_sheet`.
7. Add `office.workflow.sheet_to_deck`.
8. Add `office.workflow.board_pack`.
9. Add optional workers for render/convert/OCR/formula/AI.
10. Add hosted APIs only after the local contract is credible.

## Quickstart

Current compatibility quickstart:

```bash
python scripts/setup_dev.py
python scripts/doctor.py
python scripts/smoke.py
okpdf tools list --json
okpdf inspect tests/fixtures/simple.pdf --json
okpdf serve --mcp --safe-root .
okpdf serve --api
```

Target okoffice commands:

```bash
okoffice tools list --json
okoffice inspect report.docx --json
okoffice inspect model.xlsx --json
okoffice inspect deck.pptx --json
okoffice workflow docset-to-sheet sources/*.docx sources/*.pdf -o .okoffice-out/evidence.xlsx --json
okoffice workflow sheet-to-deck .okoffice-out/evidence.xlsx -o .okoffice-out/board-deck.pptx --json
okoffice bundle verify .okoffice-out/board-pack.okoffice.zip --json
```

The target commands document product direction; current runnable commands are the compatibility `okpdf` commands until the okoffice CLI is implemented.

## Agent Infrastructure

okoffice is built for coding agents first:

- CLI with `--json`.
- MCP server.
- Local REST API.
- Python and TypeScript SDKs.
- JSON schemas.
- Tool manifest.
- Artifact references instead of inline binaries.
- Source refs and native locators.
- Validation reports and warnings.
- Agent setup configs for Codex, Claude Code/Desktop, Cursor, Kilo Code, OpenClaw, OpenAI Agents, LangChain, LlamaIndex, Vercel AI SDK, n8n, Zapier, and Make.

See [docs/40_OKOFFICE_AGENT_INFRA.md](docs/40_OKOFFICE_AGENT_INFRA.md).

## Cloud Boundary

The OSS core stays local-first and free for deterministic operations. Hosted okoffice can monetize:

- managed Office render/convert workers;
- advanced OCR and agentic parse;
- formula recalculation and workbook QA at scale;
- source-backed report/workbook/deck generation;
- persistent source graphs and artifact graphs;
- batch orchestration;
- managed connectors;
- enterprise audit, retention, SSO, VPC, and on-prem controls.

See [docs/39_OKOFFICE_CLOUD_BUSINESS.md](docs/39_OKOFFICE_CLOUD_BUSINESS.md).

## Documentation Map

- [Product strategy](docs/37_OKOFFICE_PRODUCT_STRATEGY.md)
- [Tool taxonomy](docs/38_OKOFFICE_TOOL_TAXONOMY.md)
- [Cloud business](docs/39_OKOFFICE_CLOUD_BUSINESS.md)
- [Agent infrastructure](docs/40_OKOFFICE_AGENT_INFRA.md)
- [Implementation plan](docs/41_OKOFFICE_IMPLEMENTATION_PLAN.md)
- [Legacy PDF compatibility](docs/42_LEGACY_PDF_COMPATIBILITY.md)
- [Office PRD](docs/36_OKOFFICE_AGENT_NATIVE_OFFICE_INFRA_PRD.md)
- [Architecture](docs/03_ARCHITECTURE.md)
- [Office IR](docs/11_DOCUMENT_IR_SPEC.md)

## Development

```bash
python scripts/setup_dev.py
pytest -q
npm test --workspace @okpdf/agentpdf-node
ruff check src tests scripts
```

This workspace currently has no required cloud service for local development.

## Repository Hygiene

Commit source code, schemas, tests, small generated fixtures, examples with clear provenance, and docs. Do not commit local outputs, dependency folders, caches, secrets, personal MCP configs, build artifacts, logs, databases, or ad hoc generated files. The full policy lives in [docs/REPOSITORY_HYGIENE.md](docs/REPOSITORY_HYGIENE.md).

## License

Apache-2.0. See [LICENSE](LICENSE).

# OKoffice
