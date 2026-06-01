# 16 — Release and Open-source Standards

## Release maturity

### 0.1.0 — first open-source preview

Must include:

- CLI.
- Tool registry.
- Core schemas.
- Inspect/merge/split/extract/rotate/render/text/metadata basics.
- MCP server.
- Local REST server.
- Validation reports.
- README and examples.
- License/contributing/security docs.

### 0.2.0 — full deterministic utility layer

Add:

- Compression.
- Watermark.
- Page numbers.
- Markdown/HTML to PDF.
- Forms baseline.
- Security baseline.
- OCR optional worker.

### 0.3.0 — AI-lite and RAG

Add:

- Lite parse IR.
- Local RAG demo.
- Markdown/JSON export.
- Citation objects.
- Style packs.

### 1.0.0 — stable open-source foundation

Required:

- Stable API/MCP/CLI contracts.
- Strong test suite.
- Docs site.
- Dependency/license review.
- Security policy.
- Compatibility matrix.

## Semantic versioning

Use semver. Breaking public schema/CLI/API changes require major version after 1.0.

## Changelog

Keep `CHANGELOG.md` updated.

## GitHub polish

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

## Package publishing

Potential targets:

- PyPI: `agentpdf`.
- Docker Hub/GHCR.
- npm package for MCP bridge or TS SDK.
- GitHub Releases.

## Maintainer rules

- Prefer small, reviewable PRs.
- Require tests for core tools.
- Review dependencies for license and security.
- Mark unstable APIs clearly.
