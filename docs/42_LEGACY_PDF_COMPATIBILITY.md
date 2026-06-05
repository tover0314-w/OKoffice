# 42 - Legacy PDF Compatibility

## Purpose

The repository currently contains a large PDF-domain implementation under `okoffice`, `okoffice`, and `pdf.*`. This remains useful and should not be broken casually, but it is no longer the product identity.

okoffice treats PDF as one supported format domain.

## Compatibility Names

Current names:

- Python package: `okoffice`
- CLI: `okoffice`
- TypeScript package: `@okoffice/okoffice-node`
- Tool namespace: `pdf.*`
- Agent setup namespace: `agent.setup.*`
- Output folder convention: `.okoffice-out`

Target names:

- Python package: `okoffice`
- CLI: `okoffice`
- TypeScript package: `@okoffice/node`
- Cross-format namespace: `office.*`
- Format namespaces: `word.*`, `sheet.*`, `deck.*`, `pdf.*`
- Output folder convention: `.okoffice-out`

## What Stays For Now

Keep these until a separate code migration plan exists:

- `okoffice` imports.
- `okoffice` command.
- current `pdf.*` machine manifest rows.
- current PDF tests.
- current Node package name.
- current generated examples required by tests.

## What Moves Out Of Mainline Docs

Demote these from the README and product strategy:

- long PDF command walls;
- PDF RAG as product center;
- PDF creation platform positioning;
- target PDF profile as the main product object;
- "AI PDF" category language;
- hosted PDF SaaS monetization framing.

These can remain in compatibility docs when they describe implemented behavior.

## Compatibility Rules

- Do not remove a working `pdf.*` tool without a deprecation plan.
- Do not add new PDF-only features unless they support okoffice workflows, safety, validation, or compatibility.
- Do not rename package imports in place without migration shims.
- Do not change machine manifest rows without updating registry, CLI, MCP, REST, SDK, and tests together.
- Do not let compatibility docs become the public product entry point.

## PDF Role In okoffice

PDF remains important as:

- source documents;
- immutable delivery packets;
- render/validation targets;
- redaction surfaces;
- audit-bundle artifacts;
- compatibility with existing workflows.

PDF should not be the only artifact that okoffice can understand or create.

## Current Compatibility Quickstart

```bash
python scripts/setup_dev.py
python scripts/doctor.py
okoffice tools list --json
okoffice inspect tests/fixtures/simple.pdf --json
okoffice merge a.pdf b.pdf -o merged.pdf --json
okoffice serve --mcp --safe-root .
okoffice serve --api
```

## Migration Strategy

1. Add okoffice docs and target namespaces.
2. Add `okoffice` CLI alias while preserving `okoffice`.
3. Add okoffice manifests without breaking `pdf.*`.
4. Add Office inspect/validate tools.
5. Add cross-format workflows.
6. Deprecate legacy branding only after users have stable replacements.
