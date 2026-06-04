# 11 - Context, Source, Office IR, and Composition IR Specification

## Why IR Matters

The core moat of okoffice is not file conversion. It is a structured, agent-readable intermediate representation that makes parsing, extraction, evidence, editing, generation, citation, validation, and workflow orchestration composable across Word, Excel, PowerPoint, PDF, and other source materials.

okoffice needs these related representations:

- Context packet: what materials and intent the agent/user supplied.
- Target artifact profile: what kind of output should be produced.
- Source graph: where information came from.
- Office IR: what exists inside a parsed context item or generated artifact.
- Composition IR: what should be rendered into target artifacts.
- Patch manifest: what changes should be applied without mutating inputs.
- Artifact bundle manifest: what outputs and evidence travel together.

## Design Goals

- Preserve format-specific structure.
- Preserve geometry and layout when known.
- Preserve reading order when known.
- Include confidence and source method.
- Support text, tables, images, figures, forms, annotations, comments, revisions, formulas, charts, fields, links, metadata, code blocks, slides, speaker notes, cells, ranges, and pages.
- Enable page/bbox/paragraph/run/sheet/range/cell/slide/shape/timestamp/file/row citations.
- Enable regeneration into Word, Excel, PowerPoint, PDF, HTML, Markdown, JSON, and bundles.
- Enable visual, semantic, citation, source coverage, formula, and layout diff.
- Make generated artifacts traceable back to source material.
- Keep context input separate from target output, so PDFs, Word docs, workbooks, decks, images, videos, data, code, and links are not treated as subtypes of one another.

## Context Packet Model

A context packet is the user/agent-facing input container. It can mix material types before the system decides what to produce.

```bash
okoffice context build \
  --text "Create a board review from these sources." \
  --file diligence.pdf \
  --file memo.docx \
  --file metrics.xlsx \
  -o .okoffice-out/context.packet.json \
  --title "Board Review Context" \
  --json
```

```json
{
  "context_packet_id": "ctxpkt_...",
  "title": "Board Review Context",
  "intent": "Create a board review with an evidence workbook and deck.",
  "items": [
    {
      "context_item_id": "ctx_001",
      "type": "pdf",
      "source_ref": "src_pdf_001",
      "uri": "diligence.pdf"
    },
    {
      "context_item_id": "ctx_002",
      "type": "word_document",
      "source_ref": "src_docx_001",
      "uri": "memo.docx"
    },
    {
      "context_item_id": "ctx_003",
      "type": "workbook",
      "source_ref": "src_xlsx_001",
      "uri": "metrics.xlsx"
    }
  ],
  "source_graph": {
    "source_graph_id": "srcgraph_...",
    "nodes": []
  }
}
```

Context item types should include:

- `pdf`
- `word_document`
- `workbook`
- `deck`
- `image`
- `scan`
- `video`
- `audio`
- `web_link`
- `web_page`
- `markdown`
- `html`
- `text`
- `code_repository`
- `code_file`
- `csv`
- `database_result`
- `json`
- `prompt`
- `review_note`

## Target Artifact Profile Model

A target artifact profile defines the intended output type, structure, style, and validation policy.

```json
{
  "profile_id": "board_review_pack",
  "title": "Board Review Pack",
  "audience": "board and executive team",
  "outputs": ["evidence_workbook", "powerpoint_deck", "pdf_packet"],
  "style_pack": "executive_clear",
  "sections": ["Executive Summary", "KPI Review", "Risks", "Decisions", "Appendix"],
  "validation_required": [
    "office.validation.source_coverage",
    "office.validation.workbook_formula_check",
    "office.validation.deck_render_check",
    "office.validation.bundle_manifest_check"
  ]
}
```

Target artifact types should include:

- `word_report`
- `word_memo`
- `evidence_workbook`
- `excel_model`
- `powerpoint_deck`
- `board_deck`
- `pdf_packet`
- `research_brief`
- `legal_review_packet`
- `training_handout`
- `worksheet`
- `code_audit_packet`
- `invoice`
- `artifact_bundle`

## Source Graph Model

The source graph is derived from the context packet and records all inputs and derived source nodes.

```json
{
  "source_graph_id": "sg_...",
  "nodes": [
    {
      "source_id": "src_pdf_001_page_005",
      "type": "pdf_page",
      "parent_source_id": "src_pdf_001",
      "artifact_id": "art_...",
      "locator": {"page": 5},
      "sha256": "..."
    },
    {
      "source_id": "src_xlsx_001_range_revenue",
      "type": "sheet_range",
      "parent_source_id": "src_xlsx_001",
      "locator": {"sheet": "Revenue", "range": "B4:F18"},
      "confidence": 1.0
    },
    {
      "source_id": "src_docx_001_p_012",
      "type": "word_paragraph",
      "parent_source_id": "src_docx_001",
      "locator": {"paragraph_index": 12},
      "text": "Renewal risk is concentrated in enterprise accounts.",
      "confidence": 0.93
    }
  ],
  "edges": []
}
```

Source types should include:

- `pdf`, `pdf_page`, `pdf_block`
- `word_document`, `word_section`, `word_paragraph`, `word_run`, `word_table`, `word_cell`, `word_comment`, `word_revision`, `word_field`
- `workbook`, `sheet`, `cell`, `sheet_range`, `formula`, `table`, `pivot_table`, `chart`, `named_range`
- `deck`, `slide`, `shape`, `slide_table`, `slide_chart`, `speaker_note`, `media`
- `image`, `image_region`
- `scan`
- `video`, `video_frame`, `transcript_segment`
- `audio`
- `web_page`
- `markdown`, `html`, `text`
- `code_file`, `code_range`
- `csv_row`, `database_row`, `json_field`
- `prompt`, `review_note`

## Locator Shapes

PDF:

```json
{"page": 2, "bbox": [72, 144, 520, 210]}
```

Word:

```json
{"section": 1, "paragraph_index": 14, "run_index": 2}
```

Excel:

```json
{"sheet": "KPI", "cell": "D12"}
```

Excel range:

```json
{"sheet": "Revenue", "range": "B4:F18", "row": 8, "column": "D"}
```

PowerPoint:

```json
{"slide": 7, "shape_id": "shape_12", "bbox": [1.5, 4.0, 14.2, 6.8], "unit": "cm"}
```

Transcript:

```json
{"time_range": ["00:03:12", "00:03:48"]}
```

Code:

```json
{"path": "src/okoffice/workflows/docset_to_sheet.py", "line_start": 20, "line_end": 48}
```

## Office IR Model

Office IR describes an existing parsed context item or generated artifact.

```json
{
  "ir_version": "0.3",
  "document_id": "doc_...",
  "artifact_kind": "workbook",
  "source": {
    "source_id": "src_xlsx_001",
    "artifact_id": "art_...",
    "filename": "metrics.xlsx",
    "sha256": "..."
  },
  "metadata": {
    "title": "Q1 Metrics",
    "sheet_count": 4,
    "has_macros": false,
    "has_external_links": false
  },
  "sheets": [
    {
      "name": "Revenue",
      "used_range": "A1:F40",
      "tables": [],
      "formulas": [
        {
          "cell": "F12",
          "formula": "SUM(B12:E12)",
          "cached_value": 1250000,
          "source_ref": {
            "source_id": "src_xlsx_001",
            "locator": {"sheet": "Revenue", "cell": "F12"}
          }
        }
      ],
      "charts": []
    }
  ]
}
```

Format-specific top-level sections:

- PDF IR: `pages`, `blocks`, `annotations`, `forms`, `attachments`, `metadata`.
- Word IR: `sections`, `paragraphs`, `tables`, `comments`, `revisions`, `fields`, `headers`, `footers`.
- Excel IR: `sheets`, `cells`, `ranges`, `tables`, `formulas`, `pivots`, `charts`, `named_ranges`.
- PowerPoint IR: `slides`, `shapes`, `tables`, `charts`, `notes`, `comments`, `media`, `theme`.

## Composition IR Model

Composition IR describes new artifacts to create for a target profile.

```json
{
  "composition_version": "0.2",
  "composition_id": "cmp_...",
  "outputs": [
    {
      "artifact_kind": "xlsx",
      "target_profile_id": "evidence_workbook",
      "sheet_plan": [
        {"name": "Executive Summary", "role": "summary"},
        {"name": "Extracted Evidence", "role": "source_backed_table"},
        {"name": "Checks", "role": "validation"}
      ]
    },
    {
      "artifact_kind": "pptx",
      "target_profile_id": "board_deck",
      "deck_plan": [
        {"slide_id": "s1", "title": "Renewal risk is concentrated", "proof_object": "chart"},
        {"slide_id": "s2", "title": "Three actions reduce exposure", "proof_object": "decision_table"}
      ]
    }
  ],
  "blocks": [
    {
      "id": "claim_renewal_risk",
      "type": "claim",
      "text": "Renewal risk is concentrated in enterprise accounts.",
      "source_refs": [
        {
          "source_id": "src_docx_001_p_012",
          "locator": {"paragraph_index": 12},
          "confidence": 0.93
        },
        {
          "source_id": "src_pdf_001_page_005",
          "locator": {"page": 5, "bbox": [72, 144, 520, 210]},
          "confidence": 0.88
        }
      ]
    }
  ],
  "validation_required": [
    "office.validation.source_coverage",
    "office.validation.workbook_formula_check",
    "office.validation.deck_render_check"
  ]
}
```

## Patch Manifest Model

Patch manifests represent edits explicitly and non-mutatingly.

```json
{
  "patch_version": "0.2",
  "patch_id": "patch_...",
  "input_artifact": "art_docx_001",
  "output_artifact_kind": "docx",
  "operations": [
    {
      "op": "replace_text",
      "target": {
        "source_id": "src_docx_001_p_012",
        "locator": {"paragraph_index": 12}
      },
      "replacement": "Renewal exposure is concentrated in enterprise accounts.",
      "reason": "Use the finance team's preferred term."
    }
  ],
  "validation_required": [
    "office.validation.schema_check",
    "office.validation.placeholder_check",
    "office.validation.source_map_check"
  ]
}
```

## Validation Reports

Validation reports should be format-aware.

Common check fields:

```json
{
  "name": "placeholder_leakage_check",
  "status": "passed",
  "details": {
    "patterns_checked": ["{{", "}}", "<TODO>", "lorem", "xxxx"],
    "matches": []
  }
}
```

Examples:

- `pdf_render_check`
- `word_outline_check`
- `word_field_presence_check`
- `sheet_formula_error_check`
- `sheet_cached_value_check`
- `deck_shape_bounds_check`
- `deck_notes_coverage_check`
- `source_coverage_report`
- `bundle_manifest_check`

## Compatibility Notes

Existing schemas such as `context-packet.schema.json`, `document-ir.schema.json`, `composition-ir.schema.json`, and `target-pdf-profile.schema.json` are PDF-oriented but already point in the right direction.

Migration should add Office-aware schemas while preserving current tests:

- `office-ir.schema.json`
- `target-artifact-profile.schema.json`
- `office-source-locator.schema.json`
- `office-workflow.schema.json`

Do not rename or remove current schemas until aliases and tests are in place.
