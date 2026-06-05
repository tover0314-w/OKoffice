# 08 - okoffice MCP Server Specification

## Goal

Expose okoffice tools to MCP-compatible clients such as coding agents, desktop assistants, IDEs, and local automation hosts.

The MCP server should make Office workflows safe for agents:

- Discover tools and schemas.
- Run local deterministic tools.
- Return structured results and artifact refs.
- Preserve validation evidence.
- Keep cloud/AI workers opt-in.

The current server exposes `pdf.*` tools through MCP wrappers. During migration, those wrappers remain the compatibility surface while `office.*`, `word.*`, `sheet.*`, and `deck.*` wrappers are added.

## MCP Design Principles

- Keep tool names stable.
- Group wrappers by domain.
- Prefer compact descriptions with clear limitations.
- Do not expose planned tools as executable before implementation.
- Provide machine-readable tool manifest resources.
- Return structured JSON in `structuredContent`.
- Include artifact references instead of large binary payloads.
- Avoid hidden network or model calls.
- Keep every path under the configured safe root.

## Discovery Resources

Current resource:

```text
agentpdf_tool_manifest
```

Target resources:

```text
okoffice_tool_manifest
okoffice_format_capabilities
okoffice_artifact_profiles
okoffice_style_packs
```

`okoffice_tool_manifest` should include implementation status, OSS/cloud boundary, required feature flags, accepted formats, and example inputs.

## Current PDF MCP Wrappers

The implemented compatibility wrappers include:

- `pdf_inspect_document`
- `pdf_inspect_pages`
- `pdf_workflow_plan`
- `pdf_workflow_run`
- `pdf_workflow_report`
- `pdf_merge`
- `pdf_split`
- `pdf_extract_pages`
- `pdf_remove_pages`
- `pdf_rotate_pages`
- `pdf_reorder_pages`
- `pdf_insert_blank_pages`
- `pdf_optimize_compress`
- `pdf_optimize_repair`
- `pdf_image_to_pdf`
- `pdf_watermark`
- `pdf_add_page_numbers`
- `pdf_create_text`
- `pdf_create_markdown`
- `pdf_render_pages`
- `pdf_extract_images`
- `pdf_extract_text`
- `pdf_pdf_to_json`
- `pdf_pdf_to_markdown`
- `pdf_metadata_read`
- `pdf_metadata_update`
- `pdf_metadata_remove`
- `pdf_validate_output`
- `pdf_render_check`
- `pdf_blank_page_check`
- `pdf_ai_parse_lite`
- `pdf_ai_rag_ingest`
- `pdf_ai_rag_chat`
- `pdf_ai_rag_cite_answer`
- `pdf_ai_rag_export_report`
- `pdf_ai_rag_highlight_sources`
- `pdf_ai_rag_query`
- `pdf_ai_rag_search`

## Target okoffice MCP Wrappers

First target wrappers:

- `office_inspect_file`
- `word_inspect_document`
- `word_validate_document`
- `sheet_inspect_workbook`
- `deck_inspect_presentation`
- `office_context_build_packet`
- `office_extract_schema`
- `sheet_write_workbook`
- `sheet_validate_formulas`
- `deck_create_presentation`
- `deck_validate_contact_sheet`
- `deck_validate_presentation`
- `word_create_report`
- `office_validation_package`
- `office_workflow_docset_to_sheet`
- `office_workflow_sheet_to_deck`
- `office_workflow_board_pack`
- `office_workers_status`
- `office_bundle_export`
- `office_bundle_verify`

Wrappers should map to canonical tool names in `structuredContent.tool`, for example:

```json
{
  "tool": "sheet.inspect.workbook"
}
```

Implemented example:

```python
office_inspect_file("model.xlsx")
word_inspect_document("report.docx")
word_validate_document("report.docx")
word_create_report("evidence.xlsx", "memo.docx", title="Vendor Renewal Memo")
sheet_inspect_workbook("model.xlsx")
deck_inspect_presentation("board.pptx")
office_context_build_packet(["report.docx", "model.xlsx", "board.pptx"], "context.json")
office_extract_schema("context.json", {"fields": [{"name": "vendor", "aliases": ["Vendor"]}]})
deck_create_presentation("evidence.xlsx", "board-review.pptx", title="Vendor Renewal Review")
deck_validate_contact_sheet("board-review.pptx")
deck_validate_presentation("board-review.pptx")
office_validation_package("report.docx")
office_workflow_sheet_to_deck("evidence.xlsx", "board-review.pptx", title="Vendor Renewal Review")
office_workflow_board_pack(
    ["contracts/vendor-a.docx"],
    {"fields": [{"name": "vendor", "aliases": ["Vendor"]}]},
    ".okoffice-out/vendor-board-pack",
    title="Vendor Renewal Review",
    include_pdf_handout=True,
)
office_workers_status({"libreoffice": True}, {"libreoffice": "soffice"})
office_bundle_export(["evidence.xlsx", "board-review.pptx"], "board-pack.okoffice.zip", title="Board Pack")
office_bundle_verify("board-pack.okoffice.zip")
```

These return ToolResult JSON strings. `office_inspect_file` returns `tool: office.inspect.file`, `usage.file`, `usage.format`, and `usage.safety`. `word_inspect_document` returns `tool: word.inspect.document`, `usage.summary`, native Word locators, warnings, validation, and `next_recommended_tools`. `word_validate_document` returns `tool: word.validation.document`, package validation evidence, comments/tracked-change policies, metadata, accessibility hints, and skipped render-preview evidence when no local renderer is configured. `word_create_report` returns `tool: word.create.report`, a DOCX artifact, row/source-ref summaries, and structural validation from `word.inspect.document`. `sheet_inspect_workbook` returns `tool: sheet.inspect.workbook`, workbook structure, native Sheet locators, formula structural status, warnings, validation, and `next_recommended_tools`. `deck_inspect_presentation` returns `tool: deck.inspect.presentation`, slide structure, native Deck locators, layout structural status, warnings, validation, and `next_recommended_tools`. `office_context_build_packet` returns `tool: office.context.build_packet`, a reusable packet artifact, per-source summaries, a source graph, warnings, validation, and extraction workflow recommendations. `office_extract_schema` returns `tool: office.extract.schema`, rows, per-field evidence, source refs, confidence, warnings, and evidence workflow recommendations. `deck_create_presentation` returns `tool: deck.create.presentation`, a PPTX artifact, slide ids, source refs in speaker notes, structural validation, and contact-sheet worker availability as a skipped local check when no renderer is configured. `deck_validate_contact_sheet` returns `tool: deck.validation.contact_sheet`, presentation inspect evidence, and a structured skipped renderer check when no contact-sheet worker is configured. `deck_validate_presentation` returns `tool: deck.validation.presentation`, structural title/notes/media/theme/safety checks, Deck locators for warnings, and skipped render-evidence checks when no local renderer is configured. `office_validation_package` returns `tool: office.validation.package`, package structure checks, unsafe-entry failures, macro/external-link warnings, and next recommended tools. `office_workflow_sheet_to_deck` returns `tool: office.workflow.sheet_to_deck`, step summaries for workbook inspect, formula validation, deck creation, deck inspect, presentation validation, and contact-sheet validation, plus the generated deck artifact. `office_workflow_board_pack` returns `tool: office.workflow.board_pack`, step summaries for docset-to-sheet, Word memo creation, sheet-to-deck, optional HTML-first PDF handout creation, bundle export, and bundle verification, plus the generated workbook, sidecars, memo, deck, optional handout evidence, and checksum bundle. `office_workers_status` returns `tool: office.workers.status`, optional worker contracts, feature flags, dependency availability, license notes, cloud-boundary evidence, warnings, and next recommended tools. `office_bundle_export` and `office_bundle_verify` return canonical okoffice bundle ToolResults while reusing the local manifest and checksum bundle engine.

## Example MCP Tool Result

```json
{
  "content": [
    {
      "type": "text",
      "text": "Inspected workbook evidence.xlsx. Found 4 sheets, 127 formulas, 0 formula errors, and 2 charts."
    }
  ],
  "structuredContent": {
    "job_id": "job_01HX...",
    "status": "succeeded",
    "tool": "sheet.inspect.workbook",
    "artifacts": [],
    "validation": {
      "status": "passed",
      "checks": [
        {"name": "workbook_xml_present", "status": "passed"},
        {"name": "formula_evaluation_explicit", "status": "passed"}
      ]
    },
    "warnings": [],
    "usage": {
      "summary": {
        "sheet_count": 4,
        "formula_count": 127,
        "chart_count": 2
      },
      "formula_evaluation": {
        "status": "structural_only",
        "evaluated": false
      }
    },
    "next_recommended_tools": ["sheet.validation.formulas", "office.context.build_packet"]
  }
}
```

## Example Cross-Format Workflow

Target wrapper:

```text
office_workflow_docset_to_sheet
```

Input:

```json
{
  "files": [
    "sources/vendor-a.docx",
    "sources/vendor-b.pdf"
  ],
  "schema": {
    "fields": [
      {"name": "vendor", "type": "string"},
      {"name": "renewal_date", "type": "string"},
      {"name": "annual_amount", "type": "number"}
    ]
  },
  "output_path": ".okoffice-out/vendor-evidence.xlsx"
}
```

Output should include the workbook artifact, context/evidence sidecars, extraction warnings, workbook validation, and recommended next tools.

## Example Client Config

Current examples live in:

```text
examples/mcp/
```

The migration should preserve current `okpdf serve --mcp` behavior and add:

```bash
okoffice serve --mcp --safe-root .
```

## Safety

- Default file root should be the current working directory or configured safe root.
- Reject path traversal and unsafe archive/package entries.
- Do not fetch external URLs unless URL fetch is explicitly enabled.
- Do not use cloud models unless explicitly configured.
- Do not return document binaries inline.
- Never mutate input files.
- Report macros, external links, embedded files, suspicious package parts, and metadata risks.
