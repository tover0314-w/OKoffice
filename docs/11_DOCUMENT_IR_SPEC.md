# 11 - Context, Target, Document, Source, and Composition IR Specification

## Why IR matters

The core moat of AgentPDF is not file merging. It is a structured, agent-readable intermediate representation that makes parsing, RAG/evidence, editing, generation, citation, verification, and workflow orchestration composable.

AgentPDF needs five related representations:

- Context packet: what materials and intent the agent/user supplied.
- Target PDF profile: what kind of PDF should be produced.
- Source graph: where information came from.
- Document IR: what exists inside a parsed context item.
- Composition IR: what should be rendered into a target PDF artifact.

## Design goals

- Preserve page geometry.
- Preserve reading order when known.
- Include confidence and source method.
- Support text, tables, images, figures, forms, annotations, signatures, links, metadata, code blocks, slide blocks, and speaker notes.
- Enable page/bbox/timestamp/file/row citations.
- Enable regeneration into PDF.
- Enable visual, semantic, citation, source coverage, and layout diff.
- Make generated artifacts traceable back to source material.
- Keep context input separate from target PDF output, so images, videos, documents, code, and links are not treated as PDF subtypes.

## Context packet model

A context packet is the user/agent-facing input container. It can mix different material types before the system decides what PDF to produce. The local baseline implements this as `pdf.context.build_packet` and writes a JSON artifact shaped by `schemas/context-packet.schema.json`.

```bash
okpdf context build \
  --text "Create a technical audit PDF from these sources." \
  --file README.md \
  --file examples/sample-documents/business_report.md \
  -o .agentpdf-out/context.packet.json \
  --title "Audit Context" \
  --json
```

```json
{
  "context_packet_id": "ctxpkt_...",
  "title": "Audit Context",
  "intent": "Create a target PDF artifact with traceable evidence.",
  "items": [
    {"context_item_id": "ctx_001", "type": "text", "source_ref": "ctx_001", "role": "brief"},
    {"context_item_id": "ctx_002", "type": "document", "source_ref": "ctx_002", "uri": "D:/repo/README.md"}
  ],
  "source_graph": {
    "source_graph_id": "srcgraph_...",
    "nodes": []
  }
}
```

Context item types should include:

- `pdf`
- `image`
- `scan`
- `video`
- `audio`
- `web_link`
- `web_page`
- `markdown`
- `html`
- `office_document`
- `text`
- `code_repository`
- `code_file`
- `spreadsheet`
- `csv`
- `database_result`
- `json`
- `prompt`
- `review_note`

## Target PDF profile model

A target PDF profile defines the intended output type, structure, style, and validation policy. The local baseline implements target profiles in `pdf.compose.from_context` and documents the schema in `schemas/target-pdf-profile.schema.json`.

```json
{
  "profile_id": "technical_audit",
  "title": "AgentPDF Technical Audit",
  "audience": "agent infrastructure maintainers",
  "style_pack": "paper_ink",
  "sections": ["Executive Summary", "Evidence Table", "Code Review", "Source Map"],
  "validation_required": ["render_check", "evidence_coverage_report"]
}
```

```bash
okpdf compose from-context .agentpdf-out/context.packet.json \
  --profile technical_audit \
  -o .agentpdf-out/technical-audit.pdf \
  --json
```

Target PDF types should include:

- `learning_pdf`
- `resume_pdf`
- `academic_paper_pdf`
- `deck_pdf`
- `business_report_pdf`
- `board_deck_pdf`
- `legal_review_packet_pdf`
- `evidence_packet_pdf`
- `training_handout_pdf`
- `worksheet_pdf`
- `code_audit_pdf`
- `invoice_pdf`
- `formal_document_pdf`

## Source graph model

The source graph is derived from the context packet and records all inputs and derived source nodes.

```json
{
  "graph_id": "sg_...",
  "sources": [
    {
      "source_id": "src_pdf_001",
      "type": "pdf",
      "artifact_id": "art_...",
      "filename": "report.pdf",
      "sha256": "..."
    },
    {
      "source_id": "src_video_001_segment_004",
      "type": "transcript_segment",
      "parent_source_id": "src_video_001",
      "locator": {"time_range": ["00:03:12", "00:03:48"]},
      "text": "Renewal risk is concentrated in enterprise accounts.",
      "confidence": 0.88
    }
  ]
}
```

Source types should include:

- `pdf`
- `pdf_page`
- `pdf_block`
- `image`
- `image_region`
- `scan`
- `video`
- `video_frame`
- `transcript_segment`
- `audio`
- `web_page`
- `markdown`
- `html`
- `text`
- `code_file`
- `code_range`
- `spreadsheet`
- `data_range`
- `json_field`
- `prompt`
- `review_note`

## Document IR model

Document IR describes an existing parsed context item, such as a PDF, web page, code file, transcript, spreadsheet, or document.

```json
{
  "ir_version": "0.2",
  "document_id": "doc_...",
  "source": {
    "source_id": "src_pdf_001",
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
          "source": "text_layer",
          "source_ref": {
            "source_id": "src_pdf_001",
            "locator": {"page": 1, "bbox": [72, 80, 420, 120]}
          }
        }
      ]
    }
  ]
}
```

## Composition IR model

Composition IR describes a new PDF artifact to render for a specific target PDF profile.

```json
{
  "composition_version": "0.1",
  "composition_id": "cmp_...",
  "output": {
    "artifact_kind": "pdf",
    "target_profile_id": "target_business_report",
    "pdf_type": "business_report_pdf",
    "layout_mode": "report",
    "style_pack": "business_report_modern"
  },
  "blocks": [
    {
      "id": "blk_summary_003",
      "type": "paragraph",
      "text": "Renewal risk is the largest short-term revenue concern.",
      "source_refs": [
        {
          "source_id": "src_video_001_segment_004",
          "locator": {"time_range": ["00:03:12", "00:03:48"]},
          "confidence": 0.86
        },
        {
          "source_id": "src_pdf_001",
          "locator": {"page": 5, "bbox": [72, 144, 520, 210]},
          "confidence": 0.91
        }
      ],
      "layout": {
        "role": "body",
        "keep_with_next": false,
        "max_lines": 5
      }
    }
  ],
  "validation_required": [
    "pdf.validation.render_check",
    "pdf.evidence.coverage_report"
  ]
}
```

## Block types

Document and composition IR should support:

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
- `code_block`
- `callout`
- `quote`
- `metric_card`
- `timeline`
- `slide`
- `speaker_note`
- `appendix`
- `citation_list`
- `source_ref`
- `header`
- `footer`
- `page_number`
- `form_field`
- `annotation`
- `signature`
- `link`
- `review_comment`
- `approval_marker`
- `unknown`

## Coordinate and locator system

User-facing bboxes should identify page coordinate system.

- Include `coordinate_origin`: `top_left` or `bottom_left`.
- Be explicit about units: PDF points by default.
- Use timestamps for video/audio sources.
- Use file path and line ranges for code sources.
- Use row/range locators for tabular data.
- Use URL and fragment/text offsets for web sources when available.

## Citation object

```json
{
  "source_id": "src_pdf_001",
  "page": 3,
  "bbox": [72, 144, 520, 210],
  "text": "Revenue increased by 12%",
  "block_id": "blk_39",
  "confidence": 0.91,
  "source": "text_layer"
}
```

Non-PDF citation example:

```json
{
  "source_id": "src_code_001",
  "locator": {"path": "src/billing.py", "line_start": 40, "line_end": 67},
  "text": "class BillingEvent",
  "confidence": 1.0,
  "source": "code_snapshot"
}
```

## Patch transaction references

Patch manifests should target existing blocks, pages, bboxes, sections, or source refs. They should produce a new artifact and preserve rollback information.

```json
{
  "patch_id": "patch_...",
  "operations": [
    {
      "op": "insert_block",
      "target": {"after_block_id": "blk_10"},
      "block": {
        "type": "code_block",
        "language": "python",
        "text": "def validate_pdf(path): ...",
        "source_refs": [
          {"source_id": "src_code_001", "locator": {"path": "src/validation/pdf.py", "line_start": 1, "line_end": 18}}
        ]
      }
    }
  ]
}
```

## IR export formats

- JSON.
- Markdown.
- HTML.
- Chunks for RAG/evidence.
- Source map JSON.
- Patch manifest JSON.
- Style-aware render input.

## Schema

See `schemas/document-ir.schema.json` for the current baseline. Future schema work should add source graph, composition IR, source map, and patch manifest schemas rather than overloading raw Document IR.
