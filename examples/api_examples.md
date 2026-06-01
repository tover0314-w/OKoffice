# REST API Examples

Start the local API:

```bash
okpdf serve --api
```

## List tools

```bash
curl http://127.0.0.1:7331/v1/tools
```

## Run merge

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.organize.merge/run \
  -H 'Content-Type: application/json' \
  -d '{
    "input_paths": ["a.pdf", "b.pdf"],
    "output_path": "merged.pdf"
  }'
```

## Inspect

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.inspect.document/run \
  -H 'Content-Type: application/json' \
  -d '{"path": "report.pdf"}'
```

## Inspect pages

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.inspect.pages/run \
  -H 'Content-Type: application/json' \
  -d '{
    "input_path": "report.pdf",
    "pages": "1-3",
    "render_check": true
  }'
```

## Plan an agent workflow

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.workflow.plan/run \
  -H 'Content-Type: application/json' \
  -d '{
    "goal": "Chat with this PDF and cite answers",
    "input_path": "report.pdf"
  }'
```

## Run an agent workflow

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.workflow.run/run \
  -H 'Content-Type: application/json' \
  -d '{
    "workflow": {
      "steps": [
        {
          "step_id": "inspect",
          "tool": "pdf.inspect.document",
          "input": {"path": "report.pdf"}
        }
      ]
    }
  }'
```

## Report on an agent workflow

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.workflow.report/run \
  -H 'Content-Type: application/json' \
  -d '{
    "workflow_run": {
      "run_id": "wfrun_123",
      "status": "succeeded",
      "planned_steps": 1,
      "executed_steps": 1,
      "failed_steps": 0,
      "step_results": [
        {"step_id": "inspect", "tool": "pdf.inspect.document", "status": "succeeded"}
      ]
    },
    "output_path": ".agentpdf-out/workflow-report.md"
  }'
```

## Render

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.convert.pdf_to_images/run \
  -H 'Content-Type: application/json' \
  -d '{
    "input_path": "report.pdf",
    "pages": "1",
    "image_format": "png",
    "out_dir": ".agentpdf-out/renders"
  }'
```

## Extract embedded images

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.convert.extract_images/run \
  -H 'Content-Type: application/json' \
  -d '{
    "input_path": "report.pdf",
    "pages": "all",
    "out_dir": ".agentpdf-out/extracted-images"
  }'
```

## Create PDF from text

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.convert.text_to_pdf/run \
  -H 'Content-Type: application/json' \
  -d '{
    "text": "Hello from okpdf",
    "output_path": ".agentpdf-out/hello.pdf"
  }'
```

## Create PDF from Markdown

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.convert.markdown_to_pdf/run \
  -H 'Content-Type: application/json' \
  -d '{
    "markdown": "# Agent Report\n\n- Local first\n- Agent ready",
    "output_path": ".agentpdf-out/agent-report.pdf",
    "style_pack": "business_report_modern"
  }'
```

## Create PDF from images

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.convert.image_to_pdf/run \
  -H 'Content-Type: application/json' \
  -d '{
    "image_paths": ["cover.png", "page-2.jpg"],
    "output_path": ".agentpdf-out/scan.pdf"
  }'
```

## Add watermark

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.edit.watermark/run \
  -H 'Content-Type: application/json' \
  -d '{
    "input_path": ".agentpdf-out/scan.pdf",
    "text": "CONFIDENTIAL",
    "output_path": ".agentpdf-out/scan-watermarked.pdf"
  }'
```

## Add page numbers

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.edit.page_numbers/run \
  -H 'Content-Type: application/json' \
  -d '{
    "input_path": ".agentpdf-out/scan-watermarked.pdf",
    "template": "Page {page} of {total}",
    "output_path": ".agentpdf-out/scan-numbered.pdf"
  }'
```

## Remove pages

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.organize.remove_pages/run \
  -H 'Content-Type: application/json' \
  -d '{
    "input_path": "report.pdf",
    "pages": "1",
    "output_path": "without-cover.pdf"
  }'
```

## Rotate pages

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.organize.rotate_pages/run \
  -H 'Content-Type: application/json' \
  -d '{
    "input_path": "report.pdf",
    "pages": "1",
    "degrees": 90,
    "output_path": "rotated.pdf"
  }'
```

## Reorder pages

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.organize.reorder_pages/run \
  -H 'Content-Type: application/json' \
  -d '{
    "input_path": "report.pdf",
    "order": "3,1,2",
    "output_path": "reordered.pdf"
  }'
```

## Insert blank pages

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.organize.insert_blank_pages/run \
  -H 'Content-Type: application/json' \
  -d '{
    "input_path": "reordered.pdf",
    "after_page": 1,
    "count": 2,
    "output_path": "with-blanks.pdf"
  }'
```

## Compress PDF

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.optimize.compress/run \
  -H 'Content-Type: application/json' \
  -d '{
    "input_path": "with-blanks.pdf",
    "output_path": "with-blanks-compressed.pdf"
  }'
```

## Repair / rewrite PDF

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.optimize.repair/run \
  -H 'Content-Type: application/json' \
  -d '{
    "input_path": "with-blanks-compressed.pdf",
    "output_path": "with-blanks-repaired.pdf"
  }'
```

## Job and artifact lookup

```bash
curl http://127.0.0.1:7331/v1/jobs/job_123
curl http://127.0.0.1:7331/v1/artifacts/art_123
curl -o output.pdf http://127.0.0.1:7331/v1/artifacts/art_123/download
```

## Extract text

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.convert.pdf_to_text/run \
  -H 'Content-Type: application/json' \
  -d '{"input_path": "report.pdf", "pages": "all"}'
```

## Metadata

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.metadata.read/run \
  -H 'Content-Type: application/json' \
  -d '{"input_path": "report.pdf"}'

curl -X POST http://127.0.0.1:7331/v1/tools/pdf.metadata.update/run \
  -H 'Content-Type: application/json' \
  -d '{
    "input_path": "report.pdf",
    "metadata": {"Title": "Board Report"},
    "output_path": "report-with-title.pdf"
  }'

curl -X POST http://127.0.0.1:7331/v1/tools/pdf.metadata.remove/run \
  -H 'Content-Type: application/json' \
  -d '{"input_path": "report.pdf", "output_path": "report-clean.pdf"}'
```

## Validate output

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.validation.validate_output/run \
  -H 'Content-Type: application/json' \
  -d '{"path": ".agentpdf-out/scan-numbered.pdf", "expected_pages": 2}'
```

## Render check

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.validation.render_check/run \
  -H 'Content-Type: application/json' \
  -d '{"path": ".agentpdf-out/scan-numbered.pdf", "pages": "1"}'
```

## Blank page check

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.validation.blank_page_check/run \
  -H 'Content-Type: application/json' \
  -d '{"path": "with-blanks.pdf", "pages": "all"}'
```

## Lite parse

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.ai.parse.lite/run \
  -H 'Content-Type: application/json' \
  -d '{"input_path": ".agentpdf-out/scan-numbered.pdf"}'
```

## Export Document IR JSON

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.convert.pdf_to_json/run \
  -H 'Content-Type: application/json' \
  -d '{
    "input_path": ".agentpdf-out/scan-numbered.pdf",
    "output_path": ".agentpdf-out/scan.ir.json"
  }'
```

## Export cited Markdown

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.convert.pdf_to_markdown/run \
  -H 'Content-Type: application/json' \
  -d '{
    "input_path": ".agentpdf-out/scan-numbered.pdf",
    "output_path": ".agentpdf-out/scan.md"
  }'
```

## Local RAG ingest

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.ai.rag.ingest/run \
  -H 'Content-Type: application/json' \
  -d '{
    "input_path": ".agentpdf-out/scan-numbered.pdf",
    "index_path": ".agentpdf-out/scan.index.json"
  }'
```

## Local RAG query

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.ai.rag.query/run \
  -H 'Content-Type: application/json' \
  -d '{
    "index_path": ".agentpdf-out/scan.index.json",
    "query": "What does this PDF say?"
  }'
```

## Local RAG one-shot chat

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.ai.rag.chat/run \
  -H 'Content-Type: application/json' \
  -d '{
    "input_path": ".agentpdf-out/scan.pdf",
    "question": "Where does the invoice total appear?",
    "report_output_path": ".agentpdf-out/scan-chat-report.pdf",
    "highlight_output_path": ".agentpdf-out/scan-chat-highlighted.pdf"
  }'
```

## Local RAG search

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.ai.rag.search/run \
  -H 'Content-Type: application/json' \
  -d '{
    "index_path": ".agentpdf-out/scan.index.json",
    "query": "invoice total"
  }'
```

## Local RAG cite answer

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.ai.rag.cite_answer/run \
  -H 'Content-Type: application/json' \
  -d '{
    "index_path": ".agentpdf-out/scan.index.json",
    "answer": "The invoice total appears in the document."
  }'
```

## Local RAG highlighted source PDF

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.ai.rag.highlight_sources/run \
  -H 'Content-Type: application/json' \
  -d '{
    "index_path": ".agentpdf-out/scan.index.json",
    "answer": "The invoice total appears in the document.",
    "output_path": ".agentpdf-out/scan-highlighted.pdf"
  }'
```

## Local RAG cited answer report PDF

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.ai.rag.export_report/run \
  -H 'Content-Type: application/json' \
  -d '{
    "index_path": ".agentpdf-out/scan.index.json",
    "question": "Where does the invoice total appear?",
    "answer": "The invoice total appears in the document.",
    "output_path": ".agentpdf-out/scan-rag-report.pdf"
  }'
```
