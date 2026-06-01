# 07 — AI Tool Specifications

The open-source project should expose AI-oriented tool namespaces while making local/free and cloud/paid boundaries clear.

## Two-tier parse model

### `pdf.ai.parse.lite`

Local, free, open-source.

- Uses existing text layer.
- Uses simple page geometry and heuristics.
- Produces Document IR.
- Best for clean, digital PDFs.
- Does not require model tokens.

### `pdf.ai.parse.agentic`

Future cloud or advanced optional mode.

- Uses OCR/VLM/LLM as needed.
- Handles charts, complex tables, multi-column layouts, formulas, scans.
- Returns confidence, bboxes, and warnings.
- Token-consuming and likely paid.

## `pdf.ai.rag.ingest`

### Purpose

Turn PDF into searchable chunks with page and bbox citations.

### Open-source baseline

- Use lite parse.
- Chunk by headings/page/paragraph.
- Store local JSON index.
- Support keyword or optional local embedding provider.

### Input

```json
{
  "file": {"kind": "local_path", "path": "paper.pdf"},
  "index_path": "./.agentpdf/indexes/paper",
  "chunking": {
    "strategy": "page_paragraph",
    "max_chars": 1200,
    "overlap_chars": 120
  },
  "embedding": {
    "provider": "none"
  }
}
```

### Output

```json
{
  "index_id": "idx_local_paper",
  "chunk_count": 83,
  "pages_indexed": 12,
  "citation_mode": "page_bbox_optional"
}
```

## `pdf.ai.rag.query`

### Purpose

Answer questions with evidence.

### Input

```json
{
  "index": {"kind": "local_path", "path": "./.agentpdf/indexes/paper"},
  "query": "What are the main contributions?",
  "top_k": 5,
  "answer_mode": "extractive"
}
```

### Output

```json
{
  "answer": "The paper contributes ...",
  "citations": [
    {
      "page": 3,
      "bbox": [72, 140, 510, 220],
      "text": "...",
      "confidence": 0.82
    }
  ]
}
```

Open-source baseline may provide extractive answers and cite chunks. Generative answers require configured model provider or cloud.

## `pdf.ai.create.*`

PDF creation should support two modes.

### Template mode

Open-source, deterministic:

- Markdown/HTML + style pack.
- Resume templates.
- Invoice templates.
- Report templates.
- Academic paper template.

### AI mode

Cloud/BYOK/optional:

- Prompt-to-PDF.
- Source PDFs to summary report.
- Brand/style transformation.
- Model-generated content.

## `pdf.ai.edit.*`

Separate safe edits from AI regeneration.

### Safe deterministic edits

Use `pdf.edit.*` tools.

### AI regeneration edits

Pipeline:

```text
PDF -> parse IR -> transform content/style -> render new PDF -> validate -> diff report
```

Never promise arbitrary lossless in-place PDF body text editing.

## AI model provider design

Open-source project may support:

- `none`: no model, deterministic only.
- `byok`: user-configured model keys.
- `local`: local model provider.
- `cloud`: future hosted AgentPDF service.

Public code should not include private API keys or hard-coded hosted endpoints.
