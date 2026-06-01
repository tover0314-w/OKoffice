# 06 — Core Tool Specifications

This document describes the first stable deterministic tools Codex should implement.

## Common input concepts

### File reference

```json
{
  "kind": "local_path",
  "path": "./report.pdf"
}
```

Future kinds may include `artifact_id`, `url`, `bytes`, `connector_file`, or `cloud_object`.

### Page range syntax

Support a human-friendly page range parser:

- `1`
- `1-3`
- `1,3,5`
- `1-3,7,10-12`
- `odd`
- `even`
- `all`

Pages are 1-indexed for user-facing APIs.

Internal page indices may be 0-indexed but must never leak ambiguously.

## `pdf.inspect.document`

### Purpose

Inspect a PDF and return agent-readable facts.

### Input

```json
{
  "file": {"kind": "local_path", "path": "report.pdf"},
  "include_page_details": true,
  "include_security": true,
  "include_recommendations": true
}
```

### Output highlights

```json
{
  "page_count": 12,
  "encrypted": false,
  "has_text_layer": true,
  "has_forms": false,
  "has_annotations": true,
  "has_attachments": false,
  "has_signatures": false,
  "scanned_page_estimate": [5, 6],
  "recommended_next_tools": ["pdf.ai.parse.lite", "pdf.validation.render_check"]
}
```

### Acceptance criteria

- Works for valid PDFs.
- Returns clear error for missing/encrypted/invalid PDFs.
- Detects page count and sizes.
- Returns metadata.
- Does not mutate input.

## `pdf.organize.merge`

### Input

```json
{
  "files": [
    {"kind": "local_path", "path": "a.pdf"},
    {"kind": "local_path", "path": "b.pdf"}
  ],
  "output": {"path": "merged.pdf"},
  "preserve_metadata": false,
  "validate": true
}
```

### Acceptance criteria

- Merges all pages in order.
- Output page count equals sum of input page counts.
- Produces validation report.
- Handles encrypted PDFs only when authorized credentials are provided.

## `pdf.organize.split`

### Input

```json
{
  "file": {"kind": "local_path", "path": "report.pdf"},
  "strategy": "ranges",
  "ranges": ["1-3", "4-6", "7-10"],
  "output_dir": "./parts",
  "filename_template": "report-part-{index}.pdf"
}
```

### Strategies

- `ranges`
- `every_n_pages`
- `bookmarks`
- `single_pages`

### Acceptance criteria

- Validates ranges.
- Creates one artifact per output file.
- Does not overwrite unless `overwrite=true`.
- Preserves page order.

## `pdf.convert.pdf_to_images`

### Input

```json
{
  "file": {"kind": "local_path", "path": "report.pdf"},
  "pages": "1-3",
  "format": "png",
  "dpi": 144,
  "output_dir": "./renders"
}
```

### Acceptance criteria

- Produces one image per page.
- Records dimensions and checksums.
- Supports controlled DPI.
- Fails gracefully when renderer dependency is missing.

## `pdf.convert.images_to_pdf`

### Input

```json
{
  "images": [
    {"kind": "local_path", "path": "page1.png"},
    {"kind": "local_path", "path": "page2.png"}
  ],
  "output": {"path": "scan.pdf"},
  "page_size": "auto",
  "fit": "contain"
}
```

## `pdf.convert.text_to_pdf`

### Input

```json
{
  "text": "Hello from okpdf",
  "output_path": "hello.pdf",
  "title": "Hello"
}
```

### Open-source baseline

The local implementation writes plain text into a validated PDF artifact with structured `ToolResult` output.

## `pdf.convert.markdown_to_pdf`

### Input

```json
{
  "markdown": "# Report\n\nHello",
  "style_pack": "plain_report",
  "output_path": "report.pdf"
}
```

### Open-source baseline

The first implementation may support simple Markdown and template-based CSS. Advanced AI style generation is cloud-only.

## `pdf.validation.validate_output`

### Input

```json
{
  "file": {"kind": "local_path", "path": "merged.pdf"},
  "expected": {
    "page_count": 10,
    "must_render": true,
    "no_blank_pages": true
  }
}
```

### Output

```json
{
  "valid": true,
  "checks": [
    {"name": "page_count", "passed": true},
    {"name": "render", "passed": true},
    {"name": "blank_pages", "passed": true}
  ]
}
```
