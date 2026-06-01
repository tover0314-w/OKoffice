# 08 — MCP Server Specification

## Goal

Expose AgentPDF tools to MCP-compatible clients such as coding agents, desktop assistants, and IDEs.

## MCP design principles

- Keep tool names stable.
- Use compact, precise descriptions.
- Group tools by namespace.
- Avoid exposing every planned tool as executable before implementation.
- Provide `tool_manifest` and `list_tools` resources.
- Return structured JSON results.
- Include artifact references instead of giant binary payloads.

## Initial MCP tools

- `pdf_inspect_document`
- `pdf_merge`
- `pdf_split`
- `pdf_extract_pages`
- `pdf_remove_pages`
- `pdf_rotate_pages`
- `pdf_image_to_pdf`
- `pdf_watermark`
- `pdf_add_page_numbers`
- `pdf_create_text`
- `pdf_create_markdown`
- `pdf_render_pages`
- `pdf_extract_text`
- `pdf_metadata_read`
- `pdf_metadata_update`
- `pdf_metadata_remove`
- `pdf_validate_output`

## Example MCP tool result

```json
{
  "content": [
    {
      "type": "text",
      "text": "Merged 2 PDFs into merged.pdf. Output has 17 pages. Validation passed."
    }
  ],
  "structuredContent": {
    "job_id": "job_01HX...",
    "status": "succeeded",
    "tool": "pdf.organize.merge",
    "artifacts": [
      {
        "artifact_id": "art_01HX...",
        "path": "./merged.pdf",
        "mime_type": "application/pdf",
        "sha256": "...",
        "page_count": 17
      }
    ],
    "validation": {
      "valid": true,
      "checks": []
    }
  }
}
```

## Example Claude Desktop config

See `examples/mcp/claude_desktop_config.json`.

## Tool discovery

Expose a resource or tool:

```text
agentpdf_tool_manifest
```

It should return current implementation status and all planned namespaces.

## Safety

- Default file root should be current working directory or configured safe root.
- Reject path traversal.
- Do not fetch external URLs unless URL fetch is explicitly enabled.
- Do not use cloud models unless explicitly configured.
