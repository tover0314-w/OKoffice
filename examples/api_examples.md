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
    "style_pack": "plain_report"
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
