# 35 - Legacy PDF Domain Note

## Status

This file is no longer the product PRD. The okoffice product direction lives in:

- `docs/37_OKOFFICE_PRODUCT_STRATEGY.md`
- `docs/36_OKOFFICE_AGENT_NATIVE_OFFICE_INFRA_PRD.md`
- `docs/38_OKOFFICE_TOOL_TAXONOMY.md`
- `docs/42_LEGACY_PDF_COMPATIBILITY.md`

The old PDF-domain plan is retained only as compatibility context for currently implemented `pdf.*` tools.

## PDF Role In okoffice

PDF remains useful as:

- source material;
- final delivery packet;
- redaction and verification surface;
- render/visual-diff target;
- artifact inside a board pack or audit bundle.

PDF does not own the product concepts anymore. Context packets, source graphs, artifact profiles, composition IR, patch transactions, evidence coverage, workflows, and bundles are okoffice concepts shared across Word, Excel, PowerPoint, and PDF.

## Compatibility Scope

Keep current PDF tools stable while okoffice grows:

- inspect;
- merge/split/reorder/extract/rotate;
- render/extract text/extract images;
- metadata;
- validation;
- redaction verification;
- local RAG compatibility;
- PDF artifact manifests and bundles.

New PDF work should be justified by one of:

- okoffice workflow support;
- safety;
- validation;
- compatibility;
- source/delivery quality.

## What Not To Do

- Do not present PDF RAG as the product center.
- Do not keep adding PDF-only utility breadth as the default roadmap.
- Do not claim arbitrary perfect PDF body editing.
- Do not make PDF template creation the main okoffice creation story.
- Do not let `agentpdf` or `okpdf` branding dominate public docs.

## Migration Rule

When a PDF-domain concept is useful across formats, move it up to an okoffice namespace.

Examples:

- `pdf.context.*` becomes `office.context.*`.
- `pdf.evidence.*` becomes `office.evidence.*`.
- `pdf.patch.*` becomes `office.patch.*` with format-specific targets.
- `pdf.artifacts.*` becomes `office.bundle.*` or `office.artifacts.*`.
- `pdf.workflow.*` becomes `office.workflow.*`.

The current `pdf.*` names remain compatibility aliases until registry, CLI, MCP, REST, SDK, docs, and tests are migrated together.
