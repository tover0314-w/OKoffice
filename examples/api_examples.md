# REST API Examples

Start the local API:

```bash
okpdf serve --api
```

## List tools

```bash
curl http://127.0.0.1:7331/v1/tools
```

## Template packs

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.ai.create.template_packs/run \
  -H 'Content-Type: application/json' \
  -d '{"output_path": ".agentpdf-out/template-packs.json"}'
```

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.ai.create.validate_template_pack/run \
  -H 'Content-Type: application/json' \
  -d '{
    "template_pack_path": "examples/template-packs/local-agent-starter.json",
    "output_path": ".agentpdf-out/template-pack.validation.json"
  }'
```

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.ai.create.plan_template_pack/run \
  -H 'Content-Type: application/json' \
  -d '{
    "template_pack_path": "examples/template-packs/local-agent-starter.json",
    "target_profile": "technical_audit",
    "context_packet_path": ".agentpdf-out/context.packet.json",
    "planned_output_path": ".agentpdf-out/board-audit.pdf",
    "output_path": ".agentpdf-out/board-audit.plan.json"
  }'
```

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.ai.create.agent/run \
  -H 'Content-Type: application/json' \
  -d '{
    "template_pack_path": "examples/template-packs/local-agent-starter.json",
    "target_profile": "technical_audit",
    "context_packet_path": ".agentpdf-out/context.packet.json",
    "output_path": ".agentpdf-out/board-audit.pdf",
    "plan_output_path": ".agentpdf-out/board-audit.plan.json",
    "coverage_output_path": ".agentpdf-out/board-audit.coverage.json",
    "context_classification_output_path": ".agentpdf-out/board-audit.context-classification.json",
    "context_report_output_path": ".agentpdf-out/board-audit.context-report.pdf",
    "context_report_json_output_path": ".agentpdf-out/board-audit.context-report.json",
    "bundle_output_path": ".agentpdf-out/board-audit.agentpdf-bundle.zip"
  }'
```

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.ai.create.from_template_pack/run \
  -H 'Content-Type: application/json' \
  -d '{
    "template_pack_path": "examples/template-packs/local-agent-starter.json",
    "template_id": "board_audit",
    "color_scheme": "executive_blue",
    "output_path": ".agentpdf-out/board-audit.pdf"
  }'
```

Context Packet items can be mapped into template blocks automatically:

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.ai.create.from_template_pack/run \
  -H 'Content-Type: application/json' \
  -d '{
    "template_pack_path": "examples/template-packs/local-agent-starter.json",
    "template_id": "board_audit",
    "color_scheme": "executive_blue",
    "context_packet_path": ".agentpdf-out/context.packet.json",
    "output_path": ".agentpdf-out/board-audit-from-context.pdf"
  }'
```

Agent-supplied blocks can target template slots and carry source refs:

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.ai.create.from_template_pack/run \
  -H 'Content-Type: application/json' \
  -d '{
    "template_pack_path": "examples/template-packs/local-agent-starter.json",
    "template_id": "board_audit",
    "color_scheme": "executive_blue",
    "output_path": ".agentpdf-out/board-audit-blocks.pdf",
    "data": {
      "title": "Agent Block Audit",
      "blocks": [
        {
          "block_id": "blk_agent_code",
          "type": "code",
          "title": "Risky Function",
          "target_slot": "evidence",
          "language": "python",
          "code": "def risky_total(items):\\n    return sum(items)\\n",
          "source_refs": ["ctx_code"]
        },
        {
          "block_id": "blk_agent_table",
          "type": "table",
          "title": "Runtime Metrics",
          "target_slot": "findings",
          "columns": ["metric", "value"],
          "rows": [["latency_ms", "42"]],
          "source_refs": ["ctx_metrics"]
        },
        {
          "block_id": "blk_agent_image",
          "type": "image",
          "title": "Architecture Figure",
          "target_slot": "evidence",
          "path": "assets/brand/okpdf-logo.png",
          "caption": "Local visual evidence rendered from an agent-supplied image block.",
          "source_refs": ["path://assets/brand/okpdf-logo.png"]
        },
        {
          "block_id": "blk_agent_citation",
          "type": "citation",
          "title": "Reference Note",
          "target_slot": "recommendations",
          "quote": "Local outputs need evidence, validation, and portable audit artifacts.",
          "source": "https://okpdf.local/docs/local-agent-integration",
          "page": "local",
          "source_refs": ["https://okpdf.local/docs/local-agent-integration"]
        }
      ]
    }
  }'
```

## Claude Code setup

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/agent.setup.claude_code/run \
  -H 'Content-Type: application/json' \
  -d '{
    "output_path": ".mcp.json",
    "safe_root": "${CLAUDE_PROJECT_DIR:-.}"
  }'
```

## Codex setup

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/agent.setup.codex/run \
  -H 'Content-Type: application/json' \
  -d '{
    "output_path": "codex.mcp.json",
    "safe_root": "."
  }'
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

## Forms and OCR scan

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.forms.create/run \
  -H 'Content-Type: application/json' \
  -d '{
    "output_path": ".agentpdf-out/contact-form.pdf",
    "fields": [{"name": "name", "label": "Name", "required": true}]
  }'
```

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.forms.import_data/run \
  -H 'Content-Type: application/json' \
  -d '{
    "input_path": ".agentpdf-out/contact-form.pdf",
    "data": {"name": "Ada"},
    "output_path": ".agentpdf-out/contact-form-filled.pdf"
  }'
```

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.forms.validate/run \
  -H 'Content-Type: application/json' \
  -d '{
    "input_path": ".agentpdf-out/contact-form-filled.pdf",
    "required_fields": ["name"]
  }'
```

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.ocr_scan.scan_to_pdf/run \
  -H 'Content-Type: application/json' \
  -d '{
    "image_paths": ["assets/brand/okpdf-logo.png"],
    "output_path": ".agentpdf-out/scan.pdf"
  }'
```

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.ocr_scan.multilingual_ocr/run \
  -H 'Content-Type: application/json' \
  -d '{
    "input_path": ".agentpdf-out/scan.pdf",
    "output_path": ".agentpdf-out/scan-multilingual.pdf",
    "languages": ["eng", "chi_sim"]
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

## Create PDF from prompt and template

## Context Packet to target PDF

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.context.ingest/run \
  -H 'Content-Type: application/json' \
  -d '{
    "context_item": {
      "path": "src/agentpdf/compose/context.py",
      "role": "code_evidence",
      "label": "Composer Source"
    },
    "output_path": ".agentpdf-out/composer.context-item.json"
  }'

curl -X POST http://127.0.0.1:7331/v1/tools/pdf.context.code_snapshot/run \
  -H 'Content-Type: application/json' \
  -d '{
    "path": "src/agentpdf/compose/context.py",
    "line_start": 1,
    "line_end": 80,
    "repository_root": ".",
    "label": "Composer Source Snapshot",
    "output_path": ".agentpdf-out/composer.snapshot.context-item.json"
  }'

curl -X POST http://127.0.0.1:7331/v1/tools/pdf.context.data_profile/run \
  -H 'Content-Type: application/json' \
  -d '{
    "path": "examples/create-data/metrics.csv",
    "label": "Runtime Metrics",
    "output_path": ".agentpdf-out/metrics.profile.context-item.json"
  }'

curl -X POST http://127.0.0.1:7331/v1/tools/pdf.context.packet/run \
  -H 'Content-Type: application/json' \
  -d '{
    "context_items": [
      {"context_item": {"context_item_id": "ctx_001", "type": "code", "role": "code_evidence", "label": "Composer Source", "source_ref": "ctx_001", "metadata": {}, "content": {}}},
      {"text": "Create a technical audit PDF from pre-ingested code evidence.", "role": "brief"}
    ],
    "output_path": ".agentpdf-out/agent.context.packet.json",
    "title": "Agent Packet"
  }'

curl -X POST http://127.0.0.1:7331/v1/tools/pdf.context.build_packet/run \
  -H 'Content-Type: application/json' \
  -d '{
    "context_items": [
      {"text": "Create a technical audit PDF from these sources.", "role": "brief"},
      {"path": "src/agentpdf/compose/context.py", "role": "code_evidence"},
      {
        "table": {
          "columns": ["metric", "value"],
          "rows": [["latency_ms", "42"], ["error_rate", "0.01"]]
        },
        "role": "data_evidence",
        "label": "Runtime Metrics"
      },
      {"path": "assets/brand/okpdf-logo.png", "role": "image_evidence"},
      {
        "path": "examples/media/meeting-audio.mp3",
        "role": "audio_context",
        "label": "Meeting Audio",
        "transcript": "00:00 Kickoff\n00:12 Decision: keep the local worker boundary explicit.",
        "duration_seconds": 42.5,
        "chapters": [{"start_seconds": 0, "title": "Kickoff"}, {"start_seconds": 12, "title": "Decision"}]
      },
      {
        "path": "examples/media/training-video.mp4",
        "role": "video_context",
        "label": "Training Video",
        "transcript": "00:00 Dashboard tour\n00:20 Export demo",
        "duration_seconds": 84,
        "keyframes": [{"timestamp_seconds": 20, "label": "Export screen"}]
      },
      {"path": "examples/sample-documents/business_report.md", "role": "source_document"}
    ],
    "output_path": ".agentpdf-out/context.packet.json",
    "title": "Audit Context",
    "intent": "Compose a target PDF with source map evidence."
  }'
```

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.context.classify/run \
  -H 'Content-Type: application/json' \
  -d '{
    "context_packet_path": ".agentpdf-out/context.packet.json",
    "profile": "technical_audit",
    "output_path": ".agentpdf-out/context.classification.json"
  }'
```

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.target.profiles/run \
  -H 'Content-Type: application/json' \
  -d '{
    "output_path": ".agentpdf-out/target-profiles.json"
  }'
```

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.target.select_profile/run \
  -H 'Content-Type: application/json' \
  -d '{
    "goal": "Create a slide deck from meeting notes and source evidence.",
    "context_packet_path": ".agentpdf-out/context.packet.json",
    "output_path": ".agentpdf-out/selected-profile.json"
  }'
```

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.target.validate_profile/run \
  -H 'Content-Type: application/json' \
  -d '{
    "target_profile": {
      "profile_id": "media_learning_deck",
      "name": "Media Learning Deck",
      "layout_mode": "slides",
      "layout_slots": {
        "title": {"accepts": ["section"], "required": true},
        "evidence_slide": {"accepts": ["slide", "audio_reference", "video_reference"], "repeats": true}
      },
      "accepted_block_types": ["slide", "section", "audio_reference", "video_reference"],
      "accepted_context_types": ["text", "audio", "video"],
      "validation_required": ["render_check", "evidence_coverage_report"]
    },
    "output_path": ".agentpdf-out/media-learning-deck.validation.json"
  }'
```

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.compose.plan/run \
  -H 'Content-Type: application/json' \
  -d '{
    "context_packet_path": ".agentpdf-out/context.packet.json",
    "profile": "technical_audit",
    "output_path": ".agentpdf-out/technical-audit.plan.json",
    "title": "Technical Audit Plan"
  }'

curl -X POST http://127.0.0.1:7331/v1/tools/pdf.compose.render_ir/run \
  -H 'Content-Type: application/json' \
  -d '{
    "composition_path": ".agentpdf-out/technical-audit.plan.json",
    "output_path": ".agentpdf-out/technical-audit-from-ir.pdf"
  }'
```

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.compose.from_context/run \
  -H 'Content-Type: application/json' \
  -d '{
    "context_packet_path": ".agentpdf-out/context.packet.json",
    "profile": "technical_audit",
    "output_path": ".agentpdf-out/technical-audit.pdf",
    "renderer": "html",
    "html_output_path": ".agentpdf-out/technical-audit.html"
  }'
```

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.evidence.context_packet_report/run \
  -H 'Content-Type: application/json' \
  -d '{
    "context_packet_path": ".agentpdf-out/context.packet.json",
    "output_path": ".agentpdf-out/context-report.pdf",
    "report_output_path": ".agentpdf-out/context-report.json",
    "title": "Audit Context Packet Report"
  }'
```

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.compose.from_context/run \
  -H 'Content-Type: application/json' \
  -d '{
    "context_packet_path": ".agentpdf-out/context.packet.json",
    "profile": "slide_deck",
    "output_path": ".agentpdf-out/agent-review-deck.pdf"
  }'
```

Append source-backed blocks in one local step:

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.compose.add_code_block/run \
  -H 'Content-Type: application/json' \
  -d '{
    "input_path": ".agentpdf-out/technical-audit.pdf",
    "output_path": ".agentpdf-out/technical-audit.code.pdf",
    "title": "Risky Function",
    "language": "python",
    "code": "def risky_total(items):\n    return sum(items)\n",
    "source_refs": ["ctx_002"],
    "target_slot": "code_review",
    "composition_path": ".agentpdf-out/technical-audit.composition.json"
  }'
```

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.compose.add_table/run \
  -H 'Content-Type: application/json' \
  -d '{
    "input_path": ".agentpdf-out/technical-audit.pdf",
    "output_path": ".agentpdf-out/technical-audit.table.pdf",
    "title": "Runtime Metrics",
    "columns": ["metric", "value"],
    "rows": [["latency_ms", "42"], ["error_rate", "0.01"]],
    "source_refs": ["ctx_003"],
    "target_slot": "evidence_table"
  }'
```

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.compose.add_figure/run \
  -H 'Content-Type: application/json' \
  -d '{
    "input_path": ".agentpdf-out/technical-audit.pdf",
    "output_path": ".agentpdf-out/technical-audit.figure.pdf",
    "title": "Architecture Figure",
    "image_path": "assets/brand/okpdf-logo.png",
    "caption": "Local visual evidence.",
    "source_refs": ["ctx_004"]
  }'
```

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.compose.add_appendix/run \
  -H 'Content-Type: application/json' \
  -d '{
    "input_path": ".agentpdf-out/technical-audit.pdf",
    "output_path": ".agentpdf-out/technical-audit.appendix.pdf",
    "title": "Source Appendix",
    "markdown": "## Sources\n\n- ctx_002\n- ctx_003\n- ctx_004",
    "source_refs": ["ctx_002", "ctx_003", "ctx_004"]
  }'
```

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.compose.add_citation/run \
  -H 'Content-Type: application/json' \
  -d '{
    "input_path": ".agentpdf-out/technical-audit.pdf",
    "output_path": ".agentpdf-out/technical-audit.citation.pdf",
    "title": "Source Citation",
    "quote": "Cited claim text.",
    "source": "https://example.com/research",
    "source_refs": ["ctx_web"],
    "target_slot": "citations"
  }'
```

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.compose.add_media_reference/run \
  -H 'Content-Type: application/json' \
  -d '{
    "input_path": ".agentpdf-out/technical-audit.pdf",
    "output_path": ".agentpdf-out/technical-audit.media.pdf",
    "title": "Meeting Audio",
    "media_path": "meeting.mp3",
    "media_kind": "audio",
    "transcript_excerpt": "00:00 Kickoff",
    "source_refs": ["ctx_audio"],
    "target_slot": "media_evidence"
  }'
```

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.compose.add_slide/run \
  -H 'Content-Type: application/json' \
  -d '{
    "input_path": ".agentpdf-out/technical-audit.pdf",
    "output_path": ".agentpdf-out/technical-audit.slide.pdf",
    "title": "Review Slide",
    "subtitle": "Decision evidence",
    "body": ["Patch transactions can append slide-like evidence pages."],
    "source_refs": ["ctx_slide"],
    "target_slot": "evidence_slide"
  }'
```

## Evidence coverage and patch transaction

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.evidence.coverage_report/run \
  -H 'Content-Type: application/json' \
  -d '{
    "composition_path": ".agentpdf-out/technical-audit.composition.json",
    "output_path": ".agentpdf-out/technical-audit.coverage.json"
  }'
```

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.evidence.map_sources/run \
  -H 'Content-Type: application/json' \
  -d '{
    "composition_path": ".agentpdf-out/technical-audit.composition.json",
    "context_packet_path": ".agentpdf-out/context.packet.json",
    "output_path": ".agentpdf-out/technical-audit.source-map.json"
  }'
```

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.artifacts.source_map/run \
  -H 'Content-Type: application/json' \
  -d '{
    "composition_path": ".agentpdf-out/technical-audit.composition.json",
    "context_packet_path": ".agentpdf-out/context.packet.json",
    "output_path": ".agentpdf-out/technical-audit.artifact-source-map.json",
    "title": "Technical Audit Artifact Source Map"
  }'
```

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.evidence.cite_claims/run \
  -H 'Content-Type: application/json' \
  -d '{
    "claims": [
      {
        "claim_id": "claim_latency",
        "text": "Runtime metrics include latency evidence.",
        "source_refs": ["ctx_002"]
      }
    ],
    "source_map_path": ".agentpdf-out/technical-audit.source-map.json",
    "output_path": ".agentpdf-out/technical-audit.citations.json"
  }'
```

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.patch.plan/run \
  -H 'Content-Type: application/json' \
  -d '{
    "input_path": ".agentpdf-out/technical-audit.pdf",
    "operations": [
      {
        "op": "append_code_block",
        "title": "Risky Function",
        "language": "python",
        "code": "def risky_total(items):\n    return sum(items)\n",
        "source_refs": ["ctx_001"],
        "block_id": "blk_ctx_001"
      },
      {
        "op": "append_table",
        "title": "Runtime Metrics",
        "columns": ["metric", "value"],
        "rows": [["latency_ms", "42"], ["error_rate", "0.01"]],
        "source_refs": ["ctx_002"],
        "target_slot": "findings"
      },
      {
        "op": "append_image",
        "title": "Architecture Figure",
        "path": "assets/brand/okpdf-logo.png",
        "caption": "Local visual evidence rendered into the patched PDF.",
        "source_refs": ["ctx_003"]
      },
      {
        "op": "append_citation",
        "title": "Source Citation",
        "quote": "Cited claim text.",
        "source": "https://example.com/research",
        "source_refs": ["ctx_web"]
      },
      {
        "op": "append_media_reference",
        "title": "Meeting Audio",
        "media_path": "meeting.mp3",
        "media_kind": "audio",
        "transcript_excerpt": "00:00 Kickoff",
        "source_refs": ["ctx_audio"]
      },
      {
        "op": "append_slide",
        "title": "Agent Review Appendix",
        "body": ["Patch transactions can append slide-like evidence pages."],
        "source_refs": ["ctx_001", "ctx_002", "ctx_003"]
      }
    ],
    "output_path": ".agentpdf-out/technical-audit.structured.patch.json",
    "composition_path": ".agentpdf-out/technical-audit.composition.json",
    "layer_manifest_path": ".agentpdf-out/technical-audit.layers.json",
    "reason": "Append code, table, image, citation, media, and slide evidence."
  }'
```

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.patch.plan/run \
  -H 'Content-Type: application/json' \
  -d '{
    "input_path": ".agentpdf-out/board-audit.pdf",
    "operations": [
      {
        "op": "regenerate_block",
        "title": "Regenerated Runtime Metrics Summary",
        "replacement_markdown": "## Regenerated Runtime Metrics Summary\n\nThe findings block was regenerated from `ctx_metrics` while preserving source and template-layer evidence.",
        "source_refs": ["ctx_metrics"],
        "layer_id": "layer_blk_agent_table",
        "block_id": "blk_agent_table",
        "target_slot": "findings"
      }
    ],
    "output_path": ".agentpdf-out/board-audit.regenerate.patch.json",
    "composition_path": ".agentpdf-out/board-audit.composition.json",
    "layer_manifest_path": ".agentpdf-out/board-audit.layers.json",
    "reason": "Regenerate a template block with layer evidence."
  }'
```

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.patch.preview/run \
  -H 'Content-Type: application/json' \
  -d '{
    "patch_manifest_path": ".agentpdf-out/technical-audit.patch.json",
    "output_path": ".agentpdf-out/technical-audit.patch-preview.json"
  }'
```

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.patch.apply/run \
  -H 'Content-Type: application/json' \
  -d '{
    "patch_manifest_path": ".agentpdf-out/technical-audit.patch.json",
    "output_path": ".agentpdf-out/technical-audit-patched.pdf"
  }'
```

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.patch.verify/run \
  -H 'Content-Type: application/json' \
  -d '{
    "patch_manifest_path": ".agentpdf-out/technical-audit.patch.json",
    "patched_path": ".agentpdf-out/technical-audit-patched.pdf"
  }'
```

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.artifacts.manifest/run \
  -H 'Content-Type: application/json' \
  -d '{
    "artifact_paths": [
      ".agentpdf-out/technical-audit-patched.pdf",
      ".agentpdf-out/technical-audit.composition.json",
      ".agentpdf-out/technical-audit.coverage.json",
      ".agentpdf-out/technical-audit.source-map.json",
      ".agentpdf-out/technical-audit.artifact-source-map.json",
      ".agentpdf-out/technical-audit.citations.json",
      ".agentpdf-out/technical-audit.patch.json"
    ],
    "output_path": ".agentpdf-out/technical-audit.artifacts.json",
    "title": "Technical Audit Artifacts",
    "metadata": {"workflow": "context-packet-patch", "agent": "codex"}
  }'
```

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.artifacts.graph/run \
  -H 'Content-Type: application/json' \
  -d '{
    "artifact_manifest_path": ".agentpdf-out/technical-audit.artifacts.json",
    "output_path": ".agentpdf-out/technical-audit.artifact-graph.json",
    "title": "Technical Audit Artifact Graph"
  }'
```

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.artifacts.export_bundle/run \
  -H 'Content-Type: application/json' \
  -d '{
    "artifact_paths": [
      ".agentpdf-out/technical-audit-patched.pdf",
      ".agentpdf-out/technical-audit.composition.json",
      ".agentpdf-out/technical-audit.coverage.json",
      ".agentpdf-out/technical-audit.patch.json"
    ],
    "output_path": ".agentpdf-out/technical-audit.agentpdf-bundle.zip",
    "title": "Technical Audit Bundle",
    "metadata": {"workflow": "context-packet-patch", "agent": "codex"}
  }'
```

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.artifacts.verify_bundle/run \
  -H 'Content-Type: application/json' \
  -d '{"bundle_path": ".agentpdf-out/technical-audit.agentpdf-bundle.zip"}'
```

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.ai.create.templates/run \
  -H 'Content-Type: application/json' \
  -d '{}'
```

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.ai.create.template_preview/run \
  -H 'Content-Type: application/json' \
  -d '{
    "template": "invoice",
    "output_path": ".agentpdf-out/invoice-preview.pdf"
  }'
```

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.ai.create.from_prompt/run \
  -H 'Content-Type: application/json' \
  -d '{
    "prompt": "Create a research brief about local PDF template agents.",
    "output_path": ".agentpdf-out/research-brief.pdf",
    "template": "research_brief",
    "style_pack": "paper_ink",
    "colors": {"primary": "#4f46e5", "accent": "#f59e0b"},
    "data": {
      "audience": "agent infrastructure developers",
      "sections": [
        {
          "heading": "Template selection",
          "body": "The local create agent chooses deterministic templates and validates output."
        }
      ]
    }
  }'
```

Structured invoice and resume templates accept JSON data:

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.ai.create.from_prompt/run \
  -H 'Content-Type: application/json' \
  -d '{
    "prompt": "Create an invoice for okpdf local template work.",
    "output_path": ".agentpdf-out/invoice.pdf",
    "template": "invoice",
    "data": {
      "invoice_number": "INV-1001",
      "client": "AgentPDF Labs",
      "due_date": "2026-06-30",
      "items": [
        {"description": "Template implementation", "quantity": 2, "unit_price": 500},
        {"description": "Validation workflow", "quantity": 1, "unit_price": 350}
      ],
      "payment_notes": "Pay by bank transfer."
    }
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

curl -X POST http://127.0.0.1:7331/v1/tools/pdf.metadata.page_info/run \
  -H 'Content-Type: application/json' \
  -d '{"input_path": "report.pdf", "pages": "1-3"}'

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

curl -X POST http://127.0.0.1:7331/v1/tools/pdf.security.remove_metadata/run \
  -H 'Content-Type: application/json' \
  -d '{"input_path": "report.pdf", "output_path": "report-security-clean.pdf"}'
```

## Validate output

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.validation.validate_output/run \
  -H 'Content-Type: application/json' \
  -d '{"path": ".agentpdf-out/scan-numbered.pdf", "expected_pages": 2}'
```

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.validation.page_count_check/run \
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

## Local semantic diff

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.compare.semantic_diff/run \
  -H 'Content-Type: application/json' \
  -d '{
    "before_path": ".agentpdf-out/scan-v1.pdf",
    "after_path": ".agentpdf-out/scan-v2.pdf",
    "pages": "1"
  }'
```

## Version report

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.compare.version_report/run \
  -H 'Content-Type: application/json' \
  -d '{
    "before_path": ".agentpdf-out/scan-v1.pdf",
    "after_path": ".agentpdf-out/scan-v2.pdf",
    "output_path": ".agentpdf-out/scan.version-report.md"
  }'
```

## Visual diff

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.compare.visual_diff/run \
  -H 'Content-Type: application/json' \
  -d '{
    "before_path": ".agentpdf-out/scan-v1.pdf",
    "after_path": ".agentpdf-out/scan-v2.pdf",
    "pages": "1"
  }'
```

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.validation.visual_diff/run \
  -H 'Content-Type: application/json' \
  -d '{
    "before_path": ".agentpdf-out/scan-v1.pdf",
    "after_path": ".agentpdf-out/scan-v2.pdf",
    "max_difference_ratio": 0.001
  }'
```

## Redaction

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.security.redact/run \
  -H 'Content-Type: application/json' \
  -d '{
    "input_path": ".agentpdf-out/sensitive.pdf",
    "output_path": ".agentpdf-out/sensitive-redacted.pdf",
    "regions": [{"page": 1, "bbox": [60, 700, 280, 760], "label": "secret"}]
  }'
```

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.security.verify_redaction/run \
  -H 'Content-Type: application/json' \
  -d '{
    "input_path": ".agentpdf-out/sensitive-redacted.pdf",
    "search_terms": ["SECRET-CODE-123"]
  }'

curl -X POST http://127.0.0.1:7331/v1/tools/pdf.validation.redaction_check/run \
  -H 'Content-Type: application/json' \
  -d '{
    "input_path": ".agentpdf-out/sensitive-redacted.pdf",
    "search_terms": ["SECRET-CODE-123"]
  }'
```

## Semantic parse hints

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.ai.parse.figures/run \
  -H 'Content-Type: application/json' \
  -d '{"input_path": ".agentpdf-out/scan-numbered.pdf"}'

curl -X POST http://127.0.0.1:7331/v1/tools/pdf.ai.parse.references/run \
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
