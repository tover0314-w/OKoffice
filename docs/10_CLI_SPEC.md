# 10 - okoffice CLI Specification

## Goal

Provide a beautiful, scriptable command-line interface for local agent-native Office workflows.

Target CLI:

```text
okoffice
```

Compatibility CLIs:

```text
okpdf
agentpdf
```

Compatibility commands stay documented in `docs/42_LEGACY_PDF_COMPATIBILITY.md`. The main CLI spec is okoffice-first.

## Target Commands

Discovery:

```bash
okoffice --help
okoffice tools list --json
okoffice tools show office.workflow.board_pack --json
```

Inspect:

```bash
okoffice inspect report.docx --json
okoffice inspect workbook.xlsx --json
okoffice inspect deck.pptx --json
okoffice inspect packet.pdf --json
```

Context and extraction:

```bash
okoffice context build --file memo.docx --file diligence.pdf --file metrics.xlsx -o .okoffice-out/context.json --json
okoffice extract schema .okoffice-out/context.json --schema examples/schemas/kpi-review.json -o .okoffice-out/evidence.json --json
```

Workbook:

```bash
okoffice sheet create-workbook .okoffice-out/evidence.json -o .okoffice-out/evidence.xlsx --json
okoffice sheet validate .okoffice-out/evidence.xlsx --json
```

Document and deck:

```bash
okoffice word create-report --from-workbook .okoffice-out/evidence.xlsx -o .okoffice-out/memo.docx --json
okoffice deck create --from-workbook .okoffice-out/evidence.xlsx --profile board_review -o .okoffice-out/board-review.pptx --json
```

Workflows:

```bash
okoffice workflow docset-to-sheet --file memo.docx --file diligence.pdf --schema examples/schemas/kpi-review.json -o .okoffice-out/evidence.xlsx --json
okoffice workflow sheet-to-deck --workbook .okoffice-out/evidence.xlsx --profile board_review -o .okoffice-out/board-review.pptx --json
okoffice workflow board-pack --file memo.docx --file diligence.pdf --file metrics.xlsx --out-dir .okoffice-out/board-pack --json
```

Patch:

```bash
okoffice patch plan artifact.docx --request "Update the risk wording" -o patch.json --json
okoffice patch preview patch.json -o preview.json --json
okoffice patch apply patch.json -o artifact.updated.docx --json
okoffice patch verify patch.json artifact.updated.docx --json
```

Bundle:

```bash
okoffice bundle export --file evidence.xlsx --file memo.docx --file board-review.pptx --file board-review.pdf -o board-pack.okoffice.zip --json
okoffice bundle verify board-pack.okoffice.zip --json
```

Serve:

```bash
okoffice serve --api --safe-root .
okoffice serve --mcp --safe-root .
```

## CLI Design Rules

- Provide `--json` for every agent-facing command.
- Never overwrite by default.
- Show artifact paths, validation result, and warnings.
- Use stable error codes.
- Keep optional worker failures explicit.
- Make target format and output path explicit.
- Avoid sending files to cloud unless configured.
- Keep examples copy-pasteable.

## Output Contract

Human output should be concise:

```text
Created board-pack.okoffice.zip
Artifacts: evidence.xlsx, memo.docx, board-review.pptx, board-review.pdf
Validation: passed with 2 warnings
Source coverage: 92%
```

JSON output returns ToolResult:

```json
{
  "job_id": "job_...",
  "status": "succeeded",
  "tool": "office.workflow.board_pack",
  "artifacts": [],
  "validation": {},
  "warnings": [],
  "usage": {},
  "next_recommended_tools": []
}
```

## Error Behavior

CLI errors should include:

- stable error code;
- message;
- retry hint;
- relevant path or tool name;
- optional worker requirement when applicable.

Example:

```json
{
  "code": "worker_unavailable",
  "message": "PowerPoint preview rendering requires an optional Office render worker.",
  "retry_hint": "Install an optional worker or rerun without deck preview validation."
}
```

## Migration Rule

Do not remove `okpdf` or `agentpdf` commands until `okoffice` commands are implemented, tested, documented, and released with clear compatibility notes.
