# Translation Guide

okoffice uses English as the canonical release language and welcomes community-maintained translations for onboarding, examples, and contributor guidance.

## Current Languages

| Language | Entry point | Status | Notes |
|---|---|---|---|
| English | [README.md](../../README.md) | Canonical | Release source of truth. |
| Simplified Chinese | [README.zh-CN.md](../../README.zh-CN.md) | Maintained | Mirrors the main onboarding path and contributor rules. |

## Translation Rules

- Keep command names, tool names, JSON fields, file paths, package names, and error codes unchanged.
- Translate intent and explanations, not public API identifiers.
- Preserve examples that prove local-first behavior: CLI, MCP, REST, Node SDK, Docker, validation, and safety.
- Do not translate legal license names such as Apache-2.0, GPL, LGPL, or AGPL.
- When the English README changes, update translated READMEs in the same PR when the change affects setup, safety, public contracts, or examples.
- If a translation cannot be updated immediately, add a short note at the top of that translated file explaining which canonical section should be checked.

## Adding a Language

1. Create `README.<locale>.md` at the repository root, for example `README.ja.md`.
2. Add it to the language switcher in `README.md` and every translated README.
3. Add a row to the language table above.
4. Keep the first version focused on the onboarding path: mission, install, quickstart, interfaces, ToolResult, repository hygiene, contribution links.
5. Open the PR with the `i18n` and `documentation` labels.

## Review Checklist

- [ ] The translation links back to the English README.
- [ ] Shell commands are executable as written.
- [ ] JSON examples remain valid.
- [ ] Safety and cloud-boundary language is not weakened.
- [ ] Generated artifact policy is still clear.
- [ ] No private URLs, tokens, or machine-specific paths were introduced.
