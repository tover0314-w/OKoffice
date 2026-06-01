# 04 — Repository Structure

Codex should implement this structure.

```text
agentpdf/
  .github/
    ISSUE_TEMPLATE/
    workflows/
    PULL_REQUEST_TEMPLATE.md
  community/
  codex/
  docs/
  examples/
  packages/
    agentpdf-node/
      src/
        client.ts
        cli.ts
        index.ts
        types.ts
      tests/
  schemas/
  scripts/
  src/
    agentpdf/
      __init__.py
      api/
        __init__.py
        app.py
        routes.py
      artifacts/
        __init__.py
        store.py
        models.py
      cli/
        __init__.py
        main.py
      config/
        __init__.py
        settings.py
      core/
        __init__.py
        inspect.py
        organize.py
        render.py
        metadata.py
        convert.py
        create.py
      ir/
        __init__.py
        models.py
        lite_parse.py
      mcp/
        __init__.py
        server.py
        tools.py
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
        pdf_safety.py
      tools/
        __init__.py
        registry.py
        manifest.py
      validation/
        __init__.py
        pdf_validation.py
        visual_diff.py
      workers/
        __init__.py
        base.py
  tests/
    fixtures/
    golden/
    unit/
    integration/
  pyproject.toml
  package.json
  README.md
  AGENTS.md
```

## Important files Codex should create early

- `pyproject.toml`
- `src/agentpdf/cli/main.py`
- `src/agentpdf/tools/registry.py`
- `src/agentpdf/schemas/tool_result.py`
- `src/agentpdf/artifacts/models.py`
- `src/agentpdf/validation/pdf_validation.py`
- `tests/unit/test_tool_registry.py`
- `tests/integration/test_cli_inspect.py`

## Package naming

Recommended package import name: `agentpdf`.

Recommended CLI command: `agentpdf`.

Recommended TypeScript package name: `@okpdf/agentpdf-node`.

Recommended Node CLI command: `agentpdf-node`.

Repository name options:

- `agentpdf`
- `agentpdf-infra`
- `pdf-agent-infra`
- `pdfagent`

## Documentation organization

Keep reference docs in `docs/`. Keep machine-readable schemas in `schemas/`. Keep Codex instructions in `codex/`.

Do not bury critical implementation rules in informal chat transcripts.
