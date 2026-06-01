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
