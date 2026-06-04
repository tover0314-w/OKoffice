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
- `sheet_inspect_workbook`
- `deck_inspect_presentation`
- `deck_compose_plan`
- `deck_create_from_outline`
- `deck_validate_presentation`
- `office_context_build_packet`
- `office_extract_schema`
- `sheet_create_evidence_workbook`
- `sheet_write_workbook`
- `deck_create_presentation`
- `word_create_document`
- `office_workflow_docset_to_sheet`
- `office_workflow_sheet_to_deck`
- `office_workflow_board_pack`
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
office_context_build_packet(["memo.docx", "model.xlsx"], ".okoffice-out/context.packet.json")
office_extract_schema(".okoffice-out/context.packet.json", {"fields": [{"name": "vendor"}]}, ".okoffice-out/evidence.json")
office_validation_package("memo.docx")
sheet_create_evidence_workbook(
    {
        "records": [
            {
                "source_path": "memo.docx",
                "source_format": "docx",
                "values": ["Vendor A", "250000"],
                "source_refs": [{"document_path": "memo.docx", "row_index": 1}],
            }
        ]
    },
    ".okoffice-out/evidence.xlsx",
)
office_workflow_extract_to_sheet([], ".okoffice-out/evidence.xlsx", context_packet_path=".okoffice-out/context.packet.json")
deck_compose_plan(".okoffice-out/evidence.xlsx", ".okoffice-out/deck.plan.json", title="Board Review")
deck_validate_presentation(".okoffice-out/vendor-board-deck.pptx")
office_workflow_board_pack(
    [".okoffice-out/vendor-evidence.xlsx", ".okoffice-out/vendor-board-deck.pptx"],
    ".okoffice-out/vendor-board-pack.zip",
)
office_bundle_verify(".okoffice-out/vendor-board-pack.zip")
```

Returns a ToolResult JSON string. For `office.bundle.verify`, the JSON includes `tool: office.bundle.verify`, validation checks for manifest/report/member/hash/size integrity, warnings, artifact refs, and `next_recommended_tools`.

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
      "valid": true,
      "checks": [
        {"name": "package_opened", "status": "passed"},
        {"name": "formula_refs", "status": "passed"}
      ]
    },
    "warnings": [],
    "usage": {
      "sheet_count": 4,
      "formula_count": 127,
      "chart_count": 2
    },
    "next_recommended_tools": ["sheet.validation.formulas"]
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
  "sources": [
    {"kind": "local_path", "path": "sources/vendor-a.docx"},
    {"kind": "local_path", "path": "sources/vendor-b.pdf"}
  ],
  "schema": {
    "fields": ["vendor", "renewal_date", "annual_amount"]
  },
  "output_path": ".okoffice-out/vendor-evidence.xlsx",
  "style_pack": "evidence_workbook_clean"
}
```

Output should include the workbook artifact, source map, extraction warnings, and recommended sheet validation.

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
