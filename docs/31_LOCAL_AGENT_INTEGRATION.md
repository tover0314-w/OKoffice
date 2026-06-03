# Local Agent Integration

okpdf's first implementation priority is local agent-callable PDF tooling. Cloud workers can be added later, but the local CLI, MCP server, and REST API must remain useful without paid services, hosted URLs, or proprietary keys.

The longer-term agent integration shape is larger than PDF chat. Agents should be able to collect heterogeneous context, choose a target PDF profile, build source graphs, compose new PDF artifacts, apply patch transactions, verify evidence coverage, and report artifact lineage. Current local tools provide the first runnable subset; planned namespaces such as `pdf.context.*`, `pdf.target.*`, `pdf.evidence.*`, `pdf.compose.*`, `pdf.patch.*`, `pdf.present.*`, and `pdf.artifacts.*` describe the next agent-native surface.

## Fast Setup

```bash
python scripts/setup_dev.py
python scripts/doctor.py
python scripts/smoke.py
```

`doctor.py --json` reports required local runtime checks separately from optional capabilities. Core Python, PDF, REST, MCP, and Node SDK checks must pass for local agents; optional checks such as Tesseract OCR and CJK font availability explain whether scan/OCR and multilingual PDF creation will be fully enabled on this machine.

## Local MCP Server

Run AgentPDF as a stdio MCP server:

```bash
okpdf serve --mcp --safe-root .
```

For HTTP-compatible MCP clients:

```bash
okpdf serve --mcp --transport streamable-http --safe-root .
```

## Claude Desktop / Claude Code Style Config

Generate a project-level Claude Code config:

```bash
okpdf agent setup claude-code -o .mcp.json --json
```

This writes a local `.mcp.json` that starts okpdf as a stdio MCP server from the Claude project directory. The same setup is also available as REST tool `agent.setup.claude_code` and MCP tool `agent_setup_claude_code`.

```json
{
  "mcpServers": {
    "agentpdf": {
      "type": "stdio",
      "command": "okpdf",
      "args": ["serve", "--mcp", "--safe-root", "${CLAUDE_PROJECT_DIR:-.}"]
    }
  }
}
```

## Codex / Agent Runtime Pattern

Generate a Codex-friendly config:

```bash
okpdf agent setup codex -o codex.mcp.json --safe-root . --json
```

This writes a local MCP stdio config and returns a starter prompt, recommended workspace files, recommended MCP tools, and local-only boundaries. The same setup is also available as REST tool `agent.setup.codex`, MCP tool `agent_setup_codex`, and Node command `agentpdf-node agent-setup-codex`.

Use the same stdio MCP command from any agent runtime that supports MCP:

```json
{
  "mcpServers": {
    "agentpdf": {
      "command": "okpdf",
      "args": ["serve", "--mcp", "--safe-root", "."]
    }
  }
}
```

## Kilo Code / OpenClaw Style Configs

Generate local MCP configs for Kilo Code or OpenClaw-style agent runtimes:

```bash
okpdf agent setup kilo-code -o kilo-code.mcp.json --safe-root . --json
okpdf agent setup openclaw -o openclaw.mcp.json --safe-root . --json
```

The same setup tools are exposed as REST tools `agent.setup.kilo_code` and `agent.setup.openclaw`, MCP tools `agent_setup_kilo_code` and `agent_setup_openclaw`, and Node commands `agentpdf-node agent-setup-kilo-code` and `agentpdf-node agent-setup-openclaw`.

## Exposed Local Tools

- `agent_setup_claude_code`
- `agent_setup_codex`
- `agent_setup_kilo_code`
- `agent_setup_openclaw`
- `agentpdf_tool_manifest`
- `pdf_inspect_document`
- `pdf_inspect_pages`
- `pdf_workflow_plan`
- `pdf_workflow_run`
- `pdf_workflow_report`
- `pdf_merge`
- `pdf_split`
- `pdf_extract_pages`
- `pdf_remove_pages`
- `pdf_rotate_pages`
- `pdf_reorder_pages`
- `pdf_insert_blank_pages`
- `pdf_optimize_compress`
- `pdf_optimize_repair`
- `pdf_image_to_pdf`
- `pdf_watermark`
- `pdf_add_page_numbers`
- `pdf_create_text`
- `pdf_create_markdown`
- `pdf_ai_create_from_prompt`
- `pdf_ai_create_templates`
- `pdf_ai_create_template_packs`
- `pdf_ai_create_validate_template_pack`
- `pdf_ai_create_plan_template_pack`
- `pdf_ai_create_agent`
- `pdf_ai_create_from_template_pack`
- `pdf_ai_create_template_preview`
- `pdf_context_build_packet`
- `pdf_context_ingest`
- `pdf_context_packet`
- `pdf_context_classify`
- `pdf_compose_from_context`
- `pdf_compose_add_code_block`
- `pdf_compose_add_table`
- `pdf_compose_add_figure`
- `pdf_compose_add_appendix`
- `pdf_compose_add_citation`
- `pdf_compose_add_media_reference`
- `pdf_compose_add_slide`
- `pdf_target_profiles`
- `pdf_target_validate_profile`
- `pdf_evidence_coverage_report`
- `pdf_evidence_map_sources`
- `pdf_evidence_cite_claims`
- `pdf_evidence_context_packet_report`
- `pdf_artifacts_export_bundle`
- `pdf_artifacts_verify_bundle`
- `pdf_patch_plan`
- `pdf_patch_preview`
- `pdf_patch_apply`
- `pdf_patch_verify`
- `pdf_render_pages`
- `pdf_extract_images`
- `pdf_extract_text`
- `pdf_pdf_to_json`
- `pdf_pdf_to_markdown`
- `pdf_metadata_read`
- `pdf_metadata_update`
- `pdf_metadata_remove`
- `pdf_validate_output`
- `pdf_render_check`
- `pdf_blank_page_check`
- `pdf_ai_parse_lite`
- `pdf_ai_rag_ingest`
- `pdf_ai_rag_chat`
- `pdf_ai_rag_cite_answer`
- `pdf_ai_rag_export_report`
- `pdf_ai_rag_highlight_sources`
- `pdf_ai_rag_query`
- `pdf_ai_rag_search`

Each tool returns the same AgentPDF `ToolResult` JSON used by the CLI.

## Local REST API

Run the local HTTP API:

```bash
okpdf serve --api
```

Useful endpoints:

- `GET /healthz`
- `GET /v1/tools`
- `GET /v1/tools/{tool_name}`
- `POST /v1/tools/{tool_name}/run`
- `GET /v1/jobs/{job_id}`
- `GET /v1/artifacts/{artifact_id}`
- `GET /v1/artifacts/{artifact_id}/download`

Example Claude Code setup request:

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/agent.setup.claude_code/run \
  -H 'Content-Type: application/json' \
  -d '{
    "output_path": ".mcp.json",
    "safe_root": "${CLAUDE_PROJECT_DIR:-.}"
  }'
```

Example Kilo Code and OpenClaw setup requests:

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/agent.setup.kilo_code/run \
  -H 'Content-Type: application/json' \
  -d '{"output_path": "kilo-code.mcp.json", "safe_root": "."}'

curl -X POST http://127.0.0.1:7331/v1/tools/agent.setup.openclaw/run \
  -H 'Content-Type: application/json' \
  -d '{"output_path": "openclaw.mcp.json", "safe_root": "."}'
```

Example inspect request:

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.inspect.document/run \
  -H 'Content-Type: application/json' \
  -d '{"path": "report.pdf"}'
```

Example page inspection request:

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.inspect.pages/run \
  -H 'Content-Type: application/json' \
  -d '{"input_path": "report.pdf", "pages": "1-3", "render_check": true}'
```

Example workflow planning request:

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.workflow.plan/run \
  -H 'Content-Type: application/json' \
  -d '{"goal": "Chat with this PDF and cite answers", "input_path": "report.pdf"}'
```

Example workflow execution request:

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.workflow.run/run \
  -H 'Content-Type: application/json' \
  -d '{
    "workflow": {
      "input_path": "report.pdf",
      "artifact_dir": ".agentpdf-out/workflows/chat",
      "bindings": {
        "<question>": "What does this PDF say?",
        "<answer>": "This PDF is locally indexed."
      },
      "steps": [
        {"step_id": "inspect", "tool": "pdf.inspect.document", "input": {"path": "<input.pdf>"}},
        {"step_id": "index", "tool": "pdf.ai.rag.ingest", "input": {"input_path": "<input.pdf>", "index_path": "<output.index.json>"}},
        {"step_id": "answer", "tool": "pdf.ai.rag.query", "input": {"index_path": "<output.index.json>", "query": "<question>"}}
      ]
    }
  }'
```

Example workflow report request:

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

Example text extraction request:

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.convert.pdf_to_text/run \
  -H 'Content-Type: application/json' \
  -d '{"input_path": "report.pdf", "pages": "all"}'
```

Example embedded image extraction request:

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.convert.extract_images/run \
  -H 'Content-Type: application/json' \
  -d '{"input_path": "report.pdf", "pages": "all", "out_dir": "extracted-images"}'
```

Example one-shot local PDF chat request:

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.ai.rag.chat/run \
  -H 'Content-Type: application/json' \
  -d '{"input_path": "report.pdf", "question": "What does this report describe?", "report_output_path": "report-chat.pdf", "highlight_output_path": "report-highlighted.pdf"}'
```

Example citation support request:

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.ai.rag.cite_answer/run \
  -H 'Content-Type: application/json' \
  -d '{"index_path": "report.index.json", "answer": "The report describes local evidence."}'
```

Example highlighted source request:

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.ai.rag.highlight_sources/run \
  -H 'Content-Type: application/json' \
  -d '{"index_path": "report.index.json", "answer": "The report describes local evidence.", "output_path": "report-highlighted.pdf"}'
```

Example cited answer report request:

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.ai.rag.export_report/run \
  -H 'Content-Type: application/json' \
  -d '{"index_path": "report.index.json", "question": "What does the report describe?", "answer": "The report describes local evidence.", "output_path": "report-rag.pdf"}'
```

Example PDF creation request:

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.convert.markdown_to_pdf/run \
  -H 'Content-Type: application/json' \
  -d '{"markdown": "# Agent Report\n\n- Created locally", "output_path": "agent-report.pdf"}'
```

Example local create-agent request:

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.ai.create.templates/run \
  -H 'Content-Type: application/json' \
  -d '{}'

curl -X POST http://127.0.0.1:7331/v1/tools/pdf.ai.create.template_packs/run \
  -H 'Content-Type: application/json' \
  -d '{"output_path": "template-packs.json"}'

curl -X POST http://127.0.0.1:7331/v1/tools/pdf.ai.create.validate_template_pack/run \
  -H 'Content-Type: application/json' \
  -d '{"template_pack_path": "examples/template-packs/local-agent-starter.json"}'

curl -X POST http://127.0.0.1:7331/v1/tools/pdf.ai.create.plan_template_pack/run \
  -H 'Content-Type: application/json' \
  -d '{"template_pack_path": "examples/template-packs/local-agent-starter.json", "target_profile": "technical_audit", "context_packet_path": "context.packet.json", "planned_output_path": "board-audit.pdf", "output_path": "board-audit.plan.json"}'

curl -X POST http://127.0.0.1:7331/v1/tools/pdf.ai.create.agent/run \
  -H 'Content-Type: application/json' \
  -d '{"template_pack_path": "examples/template-packs/local-agent-starter.json", "target_profile": "technical_audit", "context_packet_path": "context.packet.json", "output_path": "board-audit.pdf", "plan_output_path": "board-audit.plan.json", "coverage_output_path": "board-audit.coverage.json", "context_classification_output_path": "board-audit.context-classification.json", "context_report_output_path": "board-audit.context-report.pdf", "context_report_json_output_path": "board-audit.context-report.json", "bundle_output_path": "board-audit.agentpdf-bundle.zip"}'

curl -X POST http://127.0.0.1:7331/v1/tools/pdf.ai.create.from_template_pack/run \
  -H 'Content-Type: application/json' \
  -d '{"template_pack_path": "examples/template-packs/local-agent-starter.json", "template_id": "board_audit", "color_scheme": "executive_blue", "output_path": "board-audit.pdf"}'

curl -X POST http://127.0.0.1:7331/v1/tools/pdf.ai.create.from_template_pack/run \
  -H 'Content-Type: application/json' \
  -d '{"template_pack_path": "examples/template-packs/local-agent-starter.json", "template_id": "board_audit", "color_scheme": "executive_blue", "context_packet_path": "context.packet.json", "output_path": "board-audit-from-context.pdf", "renderer": "html", "html_output_path": "board-audit-from-context.html"}'

curl -X POST http://127.0.0.1:7331/v1/tools/pdf.ai.create.template_preview/run \
  -H 'Content-Type: application/json' \
  -d '{"template": "invoice", "output_path": "invoice-preview.pdf"}'

curl -X POST http://127.0.0.1:7331/v1/tools/pdf.ai.create.from_prompt/run \
  -H 'Content-Type: application/json' \
  -d '{"prompt": "Create a research brief about local PDF agents.", "output_path": "research-brief.pdf", "template": "research_brief", "style_pack": "paper_ink", "colors": {"primary": "#4f46e5"}}'

curl -X POST http://127.0.0.1:7331/v1/tools/pdf.authoring.plan/run \
  -H 'Content-Type: application/json' \
  -d '{"brief": {"topic": "Independent developers going global in 2026", "page_count": 6, "deliverable": "deck"}}'

curl -X POST http://127.0.0.1:7331/v1/tools/pdf.workflow.research_deck/run \
  -H 'Content-Type: application/json' \
  -d '{"brief": {"topic": "Independent developers going global in 2026", "page_count": 6, "deliverable": "deck"}, "evidence_cards": [{"id": "ev_market", "claim": "Mobile monetization remains strong.", "evidence": "Revenue growth continues while downloads flatten.", "source_title": "State of Mobile 2026"}], "html_output_path": "research-deck.html", "pdf_output_path": "research-deck.pdf", "artifact_dir": "research-deck-artifacts", "execute": true}'
```

`pdf.workflow.research_deck` returns a runnable plan by default. With `execute: true`, it runs `pdf.create.html_package`, then `pdf.render.html_package`, then `pdf.qa.visual_report`, so agents can inspect the HTML source package before or after the final PDF render.

For structured templates, agents should call `pdf.ai.create.templates` or `pdf.ai.create.template_packs` first, inspect `fields`, `layout_slots`, `supported_block_types`, `sample_data`, `target_profile`, and color schemes, optionally run `pdf.ai.create.plan_template_pack` to pick a template from a Context Packet and Target PDF Profile, or call `pdf.ai.create.agent` to plan, classify Context Packet routing, create a Context Packet PDF/JSON report, create the target PDF, render-check, blank-check, write coverage evidence, and optionally export plus verify a portable audit bundle in one local step. The local starter pack now covers technical audits, research briefs, evidence packets, resumes, invoices, proposals, worksheets, and media review decks. Template pack `data.blocks` can include `section`, `code`, `table`, `image`, `slide`, `audio_reference`, `video_reference`, `media_reference`, and `citation` blocks with `target_slot` and `source_refs`; these render into the PDF and are recorded at block level. When a Context Packet is supplied, okpdf automatically maps packet text/document/PDF items into sections, code into code blocks, tables into tables, images into embedded image blocks, web links into citations, and media into target-profile-aware blocks: document profiles use `audio_reference`, `video_reference`, or `media_reference` evidence slots, while slide profiles can keep media as slide blocks. The create-agent run also stores a nested `context_classification` ToolResult and can include that classification JSON in the audit bundle. The returned `slot_routing_plan` records every block placement with route ids, target slots, source refs, accepted/warning status, block-type support checks, slot-known facts, target profile compatibility, candidate target-profile slots, and a routing reason. Code items include local `code_evidence` with language, line count, character count, SHA-256 code hash, symbol count, and a lightweight function/class symbol list. Document items include local `document_evidence`; DOCX context extracts paragraph text from `word/document.xml` for source-backed composition without claiming full Office layout conversion. Table items include local `table_evidence` with row count, column count, preview row count, inferred column types, and a deterministic table hash. PDF items include local `pdf_evidence` with text-layer availability, extracted page count, text character count, page-level text previews, and page bboxes. Image blocks validate the local image file and record dimensions/MIME evidence plus a local `visual_evidence` scaffold: aspect ratio, average RGB color, non-white ratio, blank detection, and a 16-character perceptual hash. Media reference blocks use local file metadata plus agent-provided transcripts, chapters, and keyframes when present. Web links become citation blocks with local `citation_evidence`: normalized URL, scheme, domain, path/query/fragment, optional title/snippet/author/publication fields, and `fetch_status=not_fetched` by default. These are deterministic local evidence scaffolds for traceability and routing, not claims of OCR, VLM, code execution, audio transcription, web-fetch understanding, or layout-preserving Office conversion. Template pack creation writes sibling `.composition.json` and `.layers.json` artifacts. The composition artifact includes `composition_ir`, `source_map`, `slot_routing_plan`, and `evidence_coverage`; the layer manifest includes stable layer ids, block ids, target slots, source refs, source kinds, estimated normalized-page anchors, and edit policies for template/block editing agents. Because the current renderer does not yet return exact physical bboxes, layer anchors are explicitly marked `estimated_slot_anchor` rather than exact layout coordinates. When a patch plan receives `composition_path`, it verifies every operation `source_refs` value against the composition `source_map`; matched mappings are written to `source_map_evidence`, and unknown refs fail with `source_ref_not_found`. When it also receives `layer_manifest_path` or CLI `--layers`, operations may include `layer_id`, `block_id`, or `target_slot`; matched layers are written to `layer_evidence` and `operation_layer_map` with anchor and edit-policy evidence. Patch planning enforces `edit_policy`: if a matched layer is not editable or the operation is not allowed, the call fails with `layer_operation_not_allowed` and details listing the layer id, block id, target slot, and allowed operations. The local `regenerate_block` operation additionally accepts `replacement_markdown`, requires source refs and a target layer/block/slot ref, and appends an audited regenerated block appendix to a new PDF artifact. It does not mutate the input PDF or claim layout-preserving in-place body edits. The invoice renderer supports `invoice_number`, `client`, `due_date`, `items`, and `payment_notes`; the resume renderer supports `name`, `headline`, `contact`, `summary`, `skills`, and `experience`.

Example context-to-PDF request:

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.context.ingest/run \
  -H 'Content-Type: application/json' \
  -d '{"context_item": {"path": "src/agentpdf/compose/context.py", "role": "code_evidence", "label": "Composer Source"}, "output_path": "composer.context-item.json"}'

curl -X POST http://127.0.0.1:7331/v1/tools/pdf.context.packet/run \
  -H 'Content-Type: application/json' \
  -d '{"context_items": [{"context_item": {"context_item_id": "ctx_001", "type": "code", "role": "code_evidence", "label": "Composer Source", "source_ref": "ctx_001", "metadata": {}, "content": {}}}, {"text": "Create a technical audit PDF from pre-ingested code evidence.", "role": "brief"}], "output_path": "agent.context.packet.json", "title": "Agent Packet"}'

curl -X POST http://127.0.0.1:7331/v1/tools/pdf.context.build_packet/run \
  -H 'Content-Type: application/json' \
  -d '{"context_items": [{"text": "Create a technical audit PDF.", "role": "brief"}, {"path": "src/agentpdf/compose/context.py", "role": "code_evidence"}, {"table": {"columns": ["metric", "value"], "rows": [["latency_ms", "42"], ["error_rate", "0.01"]]}, "role": "data_evidence", "label": "Runtime Metrics"}, {"path": "assets/brand/okpdf-logo.png", "role": "image_evidence"}, {"path": "examples/media/meeting-audio.mp3", "role": "audio_context", "label": "Meeting Audio", "transcript": "00:00 Kickoff\n00:12 Decision: keep the local worker boundary explicit.", "duration_seconds": 42.5, "chapters": [{"start_seconds": 0, "title": "Kickoff"}, {"start_seconds": 12, "title": "Decision"}]}, {"path": "examples/media/training-video.mp4", "role": "video_context", "label": "Training Video", "transcript": "00:00 Dashboard tour\n00:20 Export demo", "duration_seconds": 84, "keyframes": [{"timestamp_seconds": 20, "label": "Export screen"}]}, {"path": "README.md", "role": "project_context"}], "output_path": "context.packet.json", "title": "Audit Context"}'

curl -X POST http://127.0.0.1:7331/v1/tools/pdf.context.classify/run \
  -H 'Content-Type: application/json' \
  -d '{"context_packet_path": "context.packet.json", "profile": "technical_audit", "output_path": "context.classification.json"}'

curl -X POST http://127.0.0.1:7331/v1/tools/pdf.target.profiles/run \
  -H 'Content-Type: application/json' \
  -d '{"output_path": "target-profiles.json"}'

curl -X POST http://127.0.0.1:7331/v1/tools/pdf.target.validate_profile/run \
  -H 'Content-Type: application/json' \
  -d '{"target_profile": {"profile_id": "media_learning_deck", "layout_mode": "slides", "layout_slots": {"title": {"accepts": ["section"], "required": true}, "evidence_slide": {"accepts": ["slide", "audio_reference", "video_reference"], "repeats": true}}, "accepted_block_types": ["slide", "section", "audio_reference", "video_reference"], "accepted_context_types": ["text", "audio", "video"], "validation_required": ["render_check", "evidence_coverage_report"]}, "output_path": "media-learning-deck.validation.json"}'

curl -X POST http://127.0.0.1:7331/v1/tools/pdf.compose.from_context/run \
  -H 'Content-Type: application/json' \
  -d '{"context_packet_path": "context.packet.json", "profile": "technical_audit", "output_path": "technical-audit.pdf", "renderer": "html", "html_output_path": "technical-audit.html"}'

curl -X POST http://127.0.0.1:7331/v1/tools/pdf.render.html_package/run \
  -H 'Content-Type: application/json' \
  -d '{"package_path": "technical-audit.html-manifest.json", "output_path": "technical-audit-rendered.pdf"}'

curl -X POST http://127.0.0.1:7331/v1/tools/pdf.evidence.context_packet_report/run \
  -H 'Content-Type: application/json' \
  -d '{"context_packet_path": "context.packet.json", "output_path": "context-report.pdf", "report_output_path": "context-report.json", "title": "Context Packet Report"}'

curl -X POST http://127.0.0.1:7331/v1/tools/pdf.compose.from_context/run \
  -H 'Content-Type: application/json' \
  -d '{"context_packet_path": "context.packet.json", "profile": "slide_deck", "output_path": "agent-review-deck.pdf"}'
```

For context-to-PDF composition, agents should build a context packet, inspect the returned `source_graph`, run `pdf.context.classify` to get deterministic local block and target-slot routing hints, optionally run `pdf.evidence.context_packet_report` to create a validated PDF/JSON audit appendix for the packet, call `pdf.target.profiles` to inspect available target slots and accepted block/context types, optionally call `pdf.target.validate_profile` for a custom profile, then compose. Document-style runs can pass `renderer=html` and `html_output_path` to write an inspectable HTML package plus `.html-manifest.json` before the final PDF conversion. Local image assets are copied into a sibling `*.assets/` directory, hashed, recorded in the manifest, and checked by `html_package_validation`; remote and `file://` assets are blocked by default. The current OSS converter keeps this evidence contract while using a lightweight layout approximation until a browser renderer worker is available. The local baseline now accepts text, files, links, inline table JSON, and audio/video media files with optional agent-provided transcripts, chapters, and keyframes. Code files become `code` blocks, CSV/inline tables become `table` blocks, image files become embedded `image` blocks, PDFs become `pdf_reference` blocks, and media files become `audio_reference` or `video_reference` blocks in `composition_ir`. The context packet report records source refs, source graph nodes, checksums, primary evidence kinds, media transcript excerpts, and explicit local limitations such as no default web fetching, OCR, or vision-model interpretation. The `slide_deck` profile renders one slide-like PDF page per deck slide and stores `slide` blocks with slide numbers and source refs. The result includes a PDF artifact, a `.composition.json` artifact, optional HTML package artifacts, `composition_ir`, `source_map`, and `evidence_coverage`.

For quick agent edits after a PDF already exists, `pdf.compose.add_code_block`, `pdf.compose.add_table`, `pdf.compose.add_figure`, `pdf.compose.add_appendix`, `pdf.compose.add_citation`, `pdf.compose.add_media_reference`, and `pdf.compose.add_slide` provide a one-step append-only composition layer. Each call writes a new PDF, a `.compose-block.json` manifest, patch evidence, rollback metadata, validation, and an `input_unchanged` proof. Citation append records local citation metadata with `fetch_status=not_fetched` by default; media-reference append records local file metadata, MIME type, size, SHA-256, and provided transcript excerpts without transcribing audio/video by default. Agents can pass `source_refs`, `block_id`, `target_slot`, `composition_path`, and `layer_manifest_path`; when those evidence files are present, the same source-ref and layer edit-policy checks used by patch transactions are enforced. These tools are meant for safe block insertion and evidence appendices, not layout-preserving in-place body edits.

Example evidence and patch transaction request:

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.evidence.coverage_report/run \
  -H 'Content-Type: application/json' \
  -d '{"composition_path": "technical-audit.composition.json", "output_path": "technical-audit.coverage.json"}'

curl -X POST http://127.0.0.1:7331/v1/tools/pdf.patch.plan/run \
  -H 'Content-Type: application/json' \
  -d '{"input_path": "technical-audit.pdf", "operations": [{"op": "append_code_block", "title": "Risky Function", "language": "python", "code": "def risky_total(items):\n    return sum(items)\n", "source_refs": ["ctx_001"], "block_id": "blk_ctx_001"}, {"op": "append_table", "title": "Runtime Metrics", "columns": ["metric", "value"], "rows": [["latency_ms", "42"], ["error_rate", "0.01"]], "source_refs": ["ctx_002"], "target_slot": "findings"}, {"op": "append_image", "title": "Architecture Figure", "path": "assets/brand/okpdf-logo.png", "caption": "Local visual evidence rendered into the patched PDF.", "source_refs": ["ctx_003"]}, {"op": "append_citation", "title": "Source Citation", "quote": "Cited claim text.", "source": "https://example.com/research", "source_refs": ["ctx_web"], "target_slot": "citations"}, {"op": "append_media_reference", "title": "Meeting Audio", "media_path": "meeting.mp3", "media_kind": "audio", "transcript_excerpt": "00:00 Kickoff", "source_refs": ["ctx_audio"], "target_slot": "media_evidence"}, {"op": "append_slide", "title": "Agent Review Appendix", "body": ["Patch transactions can append slide-like evidence pages."], "source_refs": ["ctx_001", "ctx_002", "ctx_003"]}], "output_path": "technical-audit.patch.json", "composition_path": "technical-audit.composition.json", "layer_manifest_path": "technical-audit.layers.json", "reason": "Append structured evidence appendix."}'

curl -X POST http://127.0.0.1:7331/v1/tools/pdf.patch.preview/run \
  -H 'Content-Type: application/json' \
  -d '{"patch_manifest_path": "technical-audit.patch.json", "output_path": "technical-audit.patch-preview.json"}'

curl -X POST http://127.0.0.1:7331/v1/tools/pdf.patch.apply/run \
  -H 'Content-Type: application/json' \
  -d '{"patch_manifest_path": "technical-audit.patch.json", "output_path": "technical-audit-patched.pdf"}'

curl -X POST http://127.0.0.1:7331/v1/tools/pdf.patch.verify/run \
  -H 'Content-Type: application/json' \
  -d '{"patch_manifest_path": "technical-audit.patch.json", "patched_path": "technical-audit-patched.pdf"}'

curl -X POST http://127.0.0.1:7331/v1/tools/pdf.artifacts.export_bundle/run \
  -H 'Content-Type: application/json' \
  -d '{"artifact_paths": ["technical-audit-patched.pdf", "technical-audit.composition.json", "technical-audit.coverage.json", "technical-audit.patch.json"], "output_path": "technical-audit.agentpdf-bundle.zip", "title": "Technical Audit Bundle", "metadata": {"workflow": "context-packet-patch"}}'

curl -X POST http://127.0.0.1:7331/v1/tools/pdf.artifacts.verify_bundle/run \
  -H 'Content-Type: application/json' \
  -d '{"bundle_path": "technical-audit.agentpdf-bundle.zip"}'
```

For patch workflows, agents should always plan first, preview the transaction, apply to a new output path, verify, export an artifact bundle, then verify the bundle before handing it to another agent or human reviewer. The current local patch implementation supports audited append-only Markdown, code block, table, image, citation, media-reference, and slide page operations; it records the original PDF SHA, page-count delta, rollback manifest, source-ref validation, matched source-map evidence, and validation report. The bundle adds a portable manifest and SHA-256 checksums for downstream review. It must not claim layout-preserving body edits.

Example compression request:

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.optimize.compress/run \
  -H 'Content-Type: application/json' \
  -d '{"input_path": "agent-report.pdf", "output_path": "agent-report-compressed.pdf"}'
```

`pdf.context.code_snapshot` and `pdf.context.data_profile` are the dedicated local evidence tools for code and data sources. Code snapshots are static: they can include selected line ranges, symbol hashes, repository-relative paths, and optional import hints, but they do not execute code. Data profiles create table previews and `data_profile_evidence` for CSV, TSV, JSON, JSONL, and XLSX sources; XLSX support reads worksheet XML locally and does not evaluate formulas, macros, or legacy `.xls` binary content.

## TypeScript / Node.js Agents

Node agents should use the TypeScript package in `packages/agentpdf-node` and call the REST API instead of reimplementing PDF processing:

```bash
npm install
npm run build:node
okpdf serve --api
node packages/agentpdf-node/dist/src/cli.js create-text --text "Hello Node" -o node.pdf
node packages/agentpdf-node/dist/src/cli.js compress node.pdf -o node-compressed.pdf
```

```ts
import { AgentPDFClient } from "@okpdf/agentpdf-node";

const client = new AgentPDFClient();
const result = await client.runTool("pdf.convert.markdown_to_pdf", {
  markdown: "# Agent Report\n\n- Created from Node",
  output_path: "agent-report.pdf",
});
```

## Open-Source PDF Project Patterns To Borrow

AgentPDF should continue studying projects such as pdf-craft and other mature PDF/OCR/document-processing systems. The patterns to borrow are architectural:

- Local-first processing for privacy and repeatability.
- Clear handler boundaries for PDF reading, rendering, OCR, extraction, and output writing.
- Optional heavyweight workers with explicit dependency and model/cache locations.
- Per-page warnings and partial-failure reporting instead of opaque failures.
- Deterministic artifact manifests for generated files.
- Cloud/model integration as a layer above the local core, never hidden inside local deterministic tools.

Do not copy implementation code without a license review. Default core dependencies must avoid GPL/AGPL.

## Cloud Boundary

Future cloud integration should be exposed through separate tools or workers, for example `pdf.ai.parse.agentic` or hosted batch processing. Local tools should continue to work offline and should return `cloud_only` or `tool_not_implemented` for capabilities that require hosted services.
