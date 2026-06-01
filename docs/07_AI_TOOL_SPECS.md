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

Current baseline:

- Implemented in local Python core.
- Emits Document IR in the standard `ToolResult.usage.document_ir` field.
- Uses page-level bboxes when precise spans are unavailable.
- Returns warnings for pages without text-layer blocks.

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

Current baseline:

- Implemented with local keyword chunks.
- Stores `index.json`-compatible JSON when a directory path is provided.
- Each chunk stores `chunk_id`, `page_number`, `bbox`, text, source block id, and normalized tokens.

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

Current baseline provides extractive answers and cited chunks. Generative answers require configured model provider or cloud.

## `pdf.ai.rag.search`

### Purpose

Search local indexed chunks and return cited matches without composing an answer.

### Output

```json
{
  "matches": [
    {
      "chunk_id": "chunk_000001",
      "page_number": 1,
      "bbox": [0, 0, 612, 792],
      "text": "...",
      "score": 0.75
    }
  ]
}
```

Current baseline is local keyword search over chunks created by `pdf.ai.rag.ingest`.

## `pdf.ai.rag.chat`

### Purpose

Ask a local PDF in one tool call and return an extractive answer, page/bbox citations, a cited PDF answer report, and a highlighted source PDF.

### Input

```json
{
  "input_path": "./paper.pdf",
  "question": "What does this document say about local deployment?",
  "index_path": "./paper.index.json",
  "report_output_path": "./paper-chat-report.pdf",
  "highlight_output_path": "./paper-chat-highlighted.pdf",
  "top_k": 5,
  "style_pack": "business_report_modern"
}
```

If output paths are omitted, the local runner creates them under `.agentpdf-out/rag-chat/<job>/`.

### Output

```json
{
  "answer": "No cloud key required.",
  "citation_count": 1,
  "pages_cited": [1],
  "report_path": "./paper-chat-report.pdf",
  "highlighted_path": "./paper-chat-highlighted.pdf"
}
```

Current baseline is local and extractive. It chains `ingest`, `query`, `export_report`, and `highlight_sources` while preserving each artifact and step result for agents.

## `pdf.ai.rag.cite_answer`

### Purpose

Map an existing answer back to local page and bbox evidence from an okpdf RAG index.

### Input

```json
{
  "index_path": "./.agentpdf/indexes/paper/index.json",
  "answer": "The document says no cloud key is required.",
  "top_k": 5
}
```

### Output

```json
{
  "citation_mode": "page_bbox",
  "citation_count": 2,
  "citations": [
    {
      "chunk_id": "chunk_000004",
      "page_number": 1,
      "bbox": [0, 0, 612, 792],
      "text": "No cloud key required.",
      "score": 0.8
    }
  ]
}
```

Current baseline is local and extractive: it ranks stored chunks against the supplied answer and returns supporting citations. It does not generate or rewrite the answer.

## `pdf.ai.rag.highlight_sources`

### Purpose

Create a highlighted copy of the source PDF from local page/bbox citations.

### Input

```json
{
  "index_path": "./.agentpdf/indexes/paper/index.json",
  "answer": "The document says no cloud key is required.",
  "output_path": "./paper-highlighted.pdf",
  "top_k": 5,
  "highlight_color": "fff59d"
}
```

`query` can be supplied instead of `answer` when the caller wants to highlight search matches.

### Output

```json
{
  "citation_count": 2,
  "highlighted_pages": [1],
  "output_path": "./paper-highlighted.pdf",
  "citations": []
}
```

Current baseline is local and deterministic. It copies the source PDF from the RAG index, adds PDF highlight annotations for matched citation bboxes, writes a new PDF artifact, and validates the generated PDF.

## `pdf.ai.rag.export_report`

### Purpose

Create a cited PDF answer report from a local RAG index.

### Input

```json
{
  "index_path": "./.agentpdf/indexes/paper/index.json",
  "question": "What does the document say about local deployment?",
  "answer": "The document says no cloud key is required.",
  "output_path": "./paper-rag-report.pdf",
  "top_k": 5,
  "include_citations": true,
  "style_pack": "plain_report"
}
```

If `answer` is omitted, the local query tool produces an extractive answer first.

### Output

```json
{
  "output_path": "./paper-rag-report.pdf",
  "citation_count": 2,
  "pages_cited": [1],
  "answer_mode": "provided_answer_with_local_citations"
}
```

Current baseline is local and deterministic. It writes a new PDF artifact containing the question, answer, source metadata, citation snippets, page numbers, bboxes, and limitations, then validates the generated PDF.

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
