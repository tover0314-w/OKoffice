# 16 - Release and Open-Source Standards

## Release Maturity

### 0.1.0 - PDF compatibility preview

Must include:

- CLI.
- Tool registry.
- Core schemas.
- PDF inspect/merge/split/extract/rotate/render/text/metadata basics.
- MCP server.
- Local REST server.
- Validation reports.
- README and examples.
- License/contributing/security docs.

### 0.2.0 - deterministic PDF utility layer

Add:

- Compression.
- Watermark.
- Page numbers.
- Markdown/HTML to PDF.
- Forms baseline.
- Security baseline.
- OCR optional worker contract.
- Artifact manifests and bundles for PDF workflows.

### 0.3.0 - AI-lite, RAG, and okoffice scaffolding

Add:

- Lite parse IR.
- Local RAG demo.
- Markdown/JSON export.
- Citation objects.
- Style packs.
- okoffice docs and CLI alias plan.
- Source Graph and Office IR schema drafts.

### 0.4.0 - Office inspect baseline

Add:

- `office.inspect.file`.
- `word.inspect.document`.
- `sheet.inspect.workbook`.
- `deck.inspect.presentation`.
- Office package safety checks.
- DOCX/XLSX/PPTX fixture suite.
- Validation docs for Word, Excel, and PowerPoint.

### 0.5.0 - cross-format workflows

Add:

- `office.workflow.docset_to_sheet`.
- `office.workflow.sheet_to_deck`.
- `word.create.document` baseline.
- `sheet.write.workbook` baseline.
- `deck.create.presentation` baseline.
- `office.bundle.export`.
- `office.bundle.verify`.

### 1.0.0 - stable open-source okoffice foundation

Required:

- Stable API/MCP/CLI contracts.
- Stable ToolResult schemas.
- Strong test suite.
- Docs site.
- Dependency/license review.
- Security policy.
- Compatibility matrix.
- Clear OSS/cloud boundary.
- PDF compatibility maintained or migration path documented.

## Semantic Versioning

Use semver. Breaking public schema/CLI/API changes require a major version after 1.0.

## Changelog

Keep `CHANGELOG.md` updated.

## GitHub Polish

Before public launch:

- README with demos.
- `README.zh-CN.md`.
- Issue templates.
- PR template.
- Security policy.
- Governance.
- Roadmap.
- Examples.
- Screenshots/GIFs if possible.
- Badges for tests, license, package version.
- Office/PDF workflow gallery.

## Package Publishing

Potential targets:

- PyPI: `okoffice` target, `agentpdf` compatibility package.
- Docker Hub/GHCR.
- npm: `@okoffice/node` target, `@okpdf/agentpdf-node` compatibility package.
- GitHub Releases.

## Maintainer Rules

- Prefer small, reviewable PRs.
- Require tests for core tools.
- Review dependencies for license and security.
- Mark unstable APIs clearly.
- Keep generated artifacts validated.
- Do not make cloud-only behavior look local.
