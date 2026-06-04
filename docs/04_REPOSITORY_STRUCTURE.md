# 04 - Repository Structure

This repository currently uses the `agentpdf` Python package and okpdf-facing examples. During the okoffice migration, do not break those compatibility paths unless a deliberate migration task says so.

The target repository structure is:

```text
okoffice/
  .github/
    ISSUE_TEMPLATE/
    workflows/
    PULL_REQUEST_TEMPLATE.md
  community/
  codex/
  docs/
  examples/
    workflows/
    office/
    pdf/
    word/
    sheet/
    deck/
  packages/
    okoffice-node/
      src/
        client.ts
        cli.ts
        index.ts
        types.ts
      tests/
  schemas/
  scripts/
  src/
    okoffice/
      __init__.py
      api/
        __init__.py
        app.py
        routes.py
      artifacts/
        __init__.py
        store.py
        models.py
        graph.py
        bundle.py
      cli/
        __init__.py
        main.py
      config/
        __init__.py
        settings.py
      context/
        __init__.py
        ingest.py
        packet.py
        classify.py
      core/
        __init__.py
        pdf/
        word/
        sheet/
        deck/
      conversion/
        __init__.py
        local.py
      evidence/
        __init__.py
        citations.py
        coverage.py
        source_map.py
      extract/
        __init__.py
        schema.py
        tables.py
      ir/
        __init__.py
        document.py
        office.py
        composition.py
      mcp/
        __init__.py
        server.py
        tools.py
      patch/
        __init__.py
        manifest.py
        apply.py
        verify.py
      rag/
        __init__.py
        chunking.py
        retrieval.py
      schemas/
        __init__.py
        common.py
        tool_result.py
      security/
        __init__.py
        paths.py
        document_safety.py
      target/
        __init__.py
        profiles.py
      tools/
        __init__.py
        registry.py
        manifest.py
      validation/
        __init__.py
        common.py
        pdf.py
        word.py
        sheet.py
        deck.py
        visual_diff.py
        source_coverage.py
      workflows/
        __init__.py
        planner.py
        runner.py
        report.py
        docset_to_sheet.py
        sheet_to_deck.py
        docset_to_board_pack.py
      workers/
        __init__.py
        base.py
        officecli.py
        libreoffice.py
        browser.py
  tests/
    fixtures/
      pdf/
      docx/
      xlsx/
      pptx/
    golden/
    unit/
    integration/
  pyproject.toml
  package.json
  README.md
  AGENTS.md
```

## Current Compatibility Structure

Until migration tasks update code:

- Keep `src/agentpdf/`.
- Keep `packages/agentpdf-node/`.
- Keep current `pdf.*` tool names.
- Keep current CLI entrypoints that tests expect.
- Add okoffice docs, aliases, and wrappers incrementally.

## Important Files To Create Or Migrate Early

Current files to preserve:

- `src/agentpdf/cli/main.py`
- `src/agentpdf/tools/registry.py`
- `src/agentpdf/schemas/models.py`
- `src/agentpdf/artifacts/store.py`
- `src/agentpdf/validation/pdf.py`
- `src/agentpdf/context/packet.py`
- `src/agentpdf/ir/lite.py`
- `src/agentpdf/compose/context.py`
- `tests/unit/test_registry.py`
- `tests/integration/test_cli.py`

Target files to add during okoffice migration:

- `src/okoffice/__init__.py`
- `src/okoffice/core/word/inspect.py`
- `src/okoffice/core/sheet/inspect.py`
- `src/okoffice/core/deck/inspect.py`
- `src/okoffice/validation/word.py`
- `src/okoffice/validation/sheet.py`
- `src/okoffice/validation/deck.py`
- `src/okoffice/workflows/docset_to_sheet.py`
- `src/okoffice/workflows/sheet_to_deck.py`
- `src/okoffice/workflows/docset_to_board_pack.py`
- `src/okoffice/workers/officecli.py`
- `schemas/office-tool-manifest.target.json`
- `schemas/office-ir.schema.json`
- `schemas/target-artifact-profile.schema.json`

## Package Naming

Target package import name: `okoffice`.

Compatibility package import name: `agentpdf`.

Target CLI command: `okoffice`.

Compatibility CLI commands: `okpdf` and `agentpdf` where they already exist.

Target TypeScript package name: `@okoffice/node`.

Compatibility TypeScript package name: `@okpdf/agentpdf-node` until migration.

## Documentation Organization

Keep reference docs in `docs/`. Keep machine-readable schemas in `schemas/`. Keep Codex instructions in `codex/`.

Recommended future doc groups:

- `docs/product/`
- `docs/architecture/`
- `docs/reference/`
- `docs/guides/`
- `docs/workflows/`
- `docs/security/`

For now, preserve the numbered docs and add focused migration docs. Do not bury critical implementation rules in informal chat transcripts.
