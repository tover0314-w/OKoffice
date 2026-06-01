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

## `pdf.inspect.pages`

### Purpose

Return per-page facts that agents can use before parsing, OCR, editing, or validation workflows.

### Input

```json
{
  "input_path": "report.pdf",
  "pages": "1-3",
  "render_check": true
}
```

### Output highlights

```json
{
  "selected_pages": [1, 2, 3],
  "pages": [
    {
      "page_number": 1,
      "width": 612,
      "height": 792,
      "rotation": 0,
      "has_text_layer": true,
      "text_char_count": 842,
      "image_count": 2,
      "render": {"status": "passed", "width": 306, "height": 396}
    }
  ]
}
```

### Acceptance criteria

- Supports the standard page range syntax.
- Reports page size, rotation, text presence, text character count, and embedded image count.
- Optionally renders selected pages in memory and attaches render evidence.
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

## `pdf.optimize.compress`

### Input

```json
{
  "input_path": "report.pdf",
  "output_path": "report-compressed.pdf"
}
```

### Open-source baseline

The local implementation rewrites pages through the PDF writer, compresses page content streams when the backend supports it, preserves page count, records original/output byte counts, and validates the generated PDF. It may warn when the source is already compressed or the rewritten output is not smaller.

## `pdf.optimize.repair`

### Input

```json
{
  "input_path": "report.pdf",
  "output_path": "report-repaired.pdf"
}
```

### Open-source baseline

The local implementation reads a parseable or mildly recoverable PDF and writes a fresh PDF object structure. This is a safe local rewrite helper, not a promise to recover every corrupted file; richer diagnostics can be added later with optional qpdf-style workers.

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

## `pdf.convert.extract_images`

### Input

```json
{
  "input_path": "report.pdf",
  "pages": "all",
  "out_dir": "./extracted-images"
}
```

### Open-source baseline

The local implementation extracts decoded embedded images from selected PDF pages, writes image artifacts, and returns page number, image index, dimensions, source object name, artifact id, output path, and MIME type. This supports agent workflows that need to hand figures, scans, charts, or photos to OCR/vision workers later.

## `pdf.convert.image_to_pdf`

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

### Open-source baseline

The local implementation accepts one or more image paths, creates one PDF page per image, returns a `ToolResult`, and validates the generated PDF.

## `pdf.edit.watermark`

### Input

```json
{
  "input_path": "report.pdf",
  "text": "CONFIDENTIAL",
  "pages": "all",
  "output_path": "report-watermarked.pdf"
}
```

### Open-source baseline

The local implementation adds a text overlay to selected pages, writes a new PDF, and validates the output. It does not claim secure redaction.

## `pdf.edit.page_numbers`

### Input

```json
{
  "input_path": "report.pdf",
  "template": "Page {page} of {total}",
  "pages": "all",
  "output_path": "report-numbered.pdf"
}
```

### Open-source baseline

The local implementation adds bottom-centered page labels to selected pages and validates the generated PDF.

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

The local implementation supports simple Markdown plus deterministic style packs. `style_pack` can be a built-in id such as `plain_report`, `business_report_modern`, `academic_paper_basic`, `resume_modern`, or `invoice_clean`, or a path to a local JSON style pack file. The result usage includes resolved style id, name, source, page settings, colors, and components so agents can audit the selected template. Advanced AI style generation is cloud-only.

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
