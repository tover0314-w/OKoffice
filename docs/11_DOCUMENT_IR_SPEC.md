# 11 — Document IR Specification

## Why IR matters

The core moat of AgentPDF is not file merging. It is a structured, agent-readable intermediate representation that makes parsing, RAG, editing, generation, citation, and validation composable.

## Design goals

- Preserve page geometry.
- Preserve reading order when known.
- Include confidence and source method.
- Support text, tables, images, figures, forms, annotations, signatures, links, and metadata.
- Enable page/bbox citations.
- Enable regeneration into PDF.
- Enable visual and semantic diff.

## Core model

```json
{
  "ir_version": "0.1",
  "document_id": "doc_...",
  "source": {
    "artifact_id": "art_...",
    "filename": "report.pdf",
    "sha256": "..."
  },
  "metadata": {
    "title": "Q1 Report",
    "page_count": 12,
    "language": "en",
    "has_text_layer": true,
    "has_scanned_pages": false
  },
  "pages": [
    {
      "page_number": 1,
      "width": 612,
      "height": 792,
      "rotation": 0,
      "blocks": [
        {
          "id": "blk_1",
          "type": "heading",
          "text": "Executive Summary",
          "bbox": [72, 80, 420, 120],
          "confidence": 0.98,
          "source": "text_layer"
        }
      ]
    }
  ]
}
```

## Block types

- `title`
- `heading`
- `paragraph`
- `list`
- `table`
- `figure`
- `image`
- `caption`
- `formula`
- `chart`
- `header`
- `footer`
- `page_number`
- `form_field`
- `annotation`
- `signature`
- `link`
- `unknown`

## Coordinate system

- User-facing bboxes should identify page coordinate system.
- Include `coordinate_origin`: `top_left` or `bottom_left`.
- Be explicit about units: PDF points by default.

## Citation object

```json
{
  "page": 3,
  "bbox": [72, 144, 520, 210],
  "text": "Revenue increased by 12%",
  "block_id": "blk_39",
  "confidence": 0.91,
  "source": "text_layer"
}
```

## IR export formats

- JSON.
- Markdown.
- HTML.
- Chunks for RAG.
- Style-aware render input.

## Schema

See `schemas/document-ir.schema.json`.
