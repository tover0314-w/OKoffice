# PDF Authoring Workflow Compatibility Reference

The current PDF domain treats PDF creation as an authoring workflow before rendering. The local OSS path can plan an authoring route, plan source gathering, normalize agent-supplied source cards, extract evidence cards, build a storyboard, write or revise page JSON, create a self-contained HTML package, render it to PDF, and run visual QA. The HTML package is the inspectable source layer for the final PDF.

In okoffice, this pattern becomes the broader creation model for Word reports, Excel workbooks, PowerPoint decks, PDFs, and audit bundles: plan first, create explicit source artifacts, validate the output, and preserve source refs.

## When to Use It

Use this workflow when an agent needs to create a deck or report from a brief, evidence cards, and design constraints. It is most useful for fixed-page visual documents where source traceability and validation matter.

## CLI Example

```bash
okpdf authoring plan examples/research_deck_brief.json --json
okpdf research plan examples/research_deck_brief.json --json
okpdf research source-cards --brief examples/research_deck_brief.json --sources examples/research_deck_sources.json --json
okpdf research evidence-cards --source-cards examples/research_deck_source_cards.json --json
okpdf design tokens --theme consulting --color primary_color=#123456 --json
okpdf storyboard plan examples/research_deck_brief.json --evidence-cards examples/research_deck_evidence.json --json
okpdf workflow research-deck examples/research_deck_brief.json --evidence-cards examples/research_deck_evidence.json --html-output output/deck.html --pdf-output output/deck.pdf --artifact-dir output/research-deck-artifacts --execute --json
okpdf createpdf --html "<main><h1>CreatePDF</h1><p>HTML-first source package.</p></main>" --html-output output/createpdf.html --pdf-output output/createpdf.pdf --artifact-dir output/createpdf-audit --bundle-output output/createpdf.agentpdf-bundle.zip --renderer-backend auto --json
okpdf createpdf --context-packet output/context.packet.json --profile technical_audit --html-output output/context-createpdf.html --pdf-output output/context-createpdf.pdf --artifact-dir output/context-createpdf-audit --bundle-output output/context-createpdf.agentpdf-bundle.zip --renderer-backend auto --json
```

Without `--execute`, `workflow research-deck` returns the workflow plan only. With `--execute`, it runs the planned local steps and returns `usage.workflow_run` plus PDF, HTML manifest, and QA artifacts.
Use `okpdf createpdf` when the agent already has HTML, page JSON, or a Context Packet and wants a single local workflow that writes the HTML package, renders the PDF, runs visual QA, and emits an artifact manifest plus graph. Adding `--bundle-output` / `bundle_output_path` exports those artifacts into a portable `.agentpdf-bundle.zip`, verifies the bundle checksum manifest immediately, and returns both `bundle_export` and `bundle_verification` in `usage.createpdf`. For Context Packet inputs, `createpdf` uses the target profile to compose the HTML and composition JSON first; those intermediate artifacts are kept in the audit manifest. Inline `context_packet` REST/MCP/SDK payloads are materialized as `PDF_STEM.context.packet.json` inside `artifact_dir` so the exact packet used for rendering is traceable. Composition HTML manifests include block-level `layer_map` entries with `data-layer-id`, source refs, estimated DOM anchors, `render_profile`, `renderer_constraints`, and `renderer_backend`; `pdf.render.html_package` rejects unsafe render profiles that enable JavaScript, remote assets, private hosts, file URLs, or allowed origins before writing a PDF. Render calls accept `renderer_backend=auto|local_html_package_fallback|browser_chromium`; `browser_chromium` uses the optional Playwright Chromium worker when installed and returns structured `dependency_missing` evidence with `render_skipped=true` otherwise. Render results expose `usage.requested_renderer_backend`, `usage.renderer_backend`, `render_skipped`, and `render_skip_reason` so agents can tell whether the current OSS fallback or a browser worker produced the artifact. Artifact manifests lift those entries into `html_render_profile_refs`, `renderer_backend_refs`, and `html_layer_refs`, and artifact graphs expose `html_render_profile`, `renderer_backend`, and `html_layer` nodes linked back to package/source refs. `pdf.patch.plan` can then consume the graph via `artifact_graph_path` / `--artifact-graph`; operations may cite `html_layer_id`, and the patch manifest records `html_layer_evidence` plus `operation_html_layer_map`. When those operations are `regenerate_block`, `pdf.patch.apply` writes a new patched HTML source package and rerenders the PDF in `html_layer_rerender` mode. Adding the patched PDF, patched HTML, patched HTML manifest, and `.patch-applied.json` to an artifact manifest records `html_layer_patch_refs` and graph edges back to the rewritten layer. These anchors are useful for audit and source editing, but they are explicitly not exact PDF glyph bboxes.

The `pdf.research.*` tools are local normalizers: they do not browse, fetch, summarize remote pages, or create fresh claims from the web. Agents should provide source metadata gathered elsewhere, then let the PDF compatibility layer preserve source ids, confidence, useful page targets, and `fetch_status=not_fetched`.

## REST Example

```bash
curl -s http://127.0.0.1:7331/v1/tools/pdf.authoring.plan/run \
  -H "content-type: application/json" \
  -d '{"brief":{"topic":"okoffice PDF authoring","page_count":6}}'

curl -s http://127.0.0.1:7331/v1/tools/pdf.research.source_cards/run \
  -H "content-type: application/json" \
  -d '{"brief":{"topic":"okoffice PDF authoring","page_count":6},"sources":[{"title":"State of Mobile 2026","source_type":"report","summary":"Revenue growth continues while downloads flatten.","key_points":["Revenue growth continues while downloads flatten."]}]}'

curl -s http://127.0.0.1:7331/v1/tools/pdf.workflow.research_deck/run \
  -H "content-type: application/json" \
  -d '{"brief":{"topic":"okoffice PDF authoring","page_count":6,"deliverable":"deck"},"evidence_cards":[],"html_output_path":"output/deck.html","pdf_output_path":"output/deck.pdf","artifact_dir":"output/research-deck-artifacts","execute":true}'

curl -s http://127.0.0.1:7331/v1/tools/pdf.workflow.createpdf/run \
  -H "content-type: application/json" \
  -d '{"html":"<main><h1>CreatePDF</h1><p>HTML-first source package.</p></main>","html_output_path":"output/createpdf.html","pdf_output_path":"output/createpdf.pdf","artifact_dir":"output/createpdf-audit","bundle_output_path":"output/createpdf.agentpdf-bundle.zip","renderer_backend":"auto"}'

curl -s http://127.0.0.1:7331/v1/tools/pdf.workflow.createpdf/run \
  -H "content-type: application/json" \
  -d '{"context_packet_path":"output/context.packet.json","target_profile":"technical_audit","html_output_path":"output/context-createpdf.html","pdf_output_path":"output/context-createpdf.pdf","artifact_dir":"output/context-createpdf-audit","bundle_output_path":"output/context-createpdf.agentpdf-bundle.zip","renderer_backend":"auto"}'
```

## MCP Example

```json
{
  "tool": "pdf_workflow_research_deck",
  "arguments": {
    "brief": {
      "topic": "okoffice PDF authoring",
      "page_count": 6,
      "deliverable": "deck"
    },
    "evidence_cards": [],
    "html_output_path": "output/deck.html",
    "pdf_output_path": "output/deck.pdf",
    "artifact_dir": "output/research-deck-artifacts",
    "execute": true
  }
}
```

```json
{
  "tool": "pdf_workflow_createpdf",
  "arguments": {
    "html": "<main><h1>CreatePDF</h1><p>HTML-first source package.</p></main>",
    "html_output_path": "output/createpdf.html",
    "pdf_output_path": "output/createpdf.pdf",
    "artifact_dir": "output/createpdf-audit",
    "bundle_output_path": "output/createpdf.agentpdf-bundle.zip",
    "renderer_backend": "auto"
  }
}
```

```json
{
  "tool": "pdf_workflow_createpdf",
  "arguments": {
    "context_packet_path": "output/context.packet.json",
    "target_profile": "technical_audit",
    "html_output_path": "output/context-createpdf.html",
    "pdf_output_path": "output/context-createpdf.pdf",
    "artifact_dir": "output/context-createpdf-audit",
    "bundle_output_path": "output/context-createpdf.agentpdf-bundle.zip",
    "renderer_backend": "auto"
  }
}
```

## Expected Output

```json
{
  "job_id": "job_...",
  "status": "succeeded",
  "tool": "pdf.workflow.research_deck",
  "artifacts": [{"mime_type": "application/pdf"}],
  "validation": null,
  "warnings": [],
  "usage": {
    "workflow": {
      "steps": [
        {"tool": "pdf.authoring.plan"},
        {"tool": "pdf.storyboard.plan"},
        {"tool": "pdf.pages.write"},
        {"tool": "pdf.create.html_package"},
        {"tool": "pdf.render.html_package"},
        {"tool": "pdf.qa.visual_report"}
      ]
    },
    "workflow_run": {
      "executed_steps": 6,
      "failed_steps": 0
    }
  },
  "next_recommended_tools": ["pdf.workflow.report"]
}
```

For `pdf.workflow.createpdf` with `bundle_output_path`, the success response also includes bundle evidence:

```json
{
  "job_id": "job_...",
  "status": "succeeded",
  "tool": "pdf.workflow.createpdf",
  "artifacts": [{"mime_type": "application/pdf"}],
  "usage": {
    "createpdf": {
      "source_format": "raw_html",
      "html_package_manifest_path": "output/createpdf.html-manifest.json",
      "qa_report_path": "output/createpdf-audit/createpdf.qa.json",
      "artifact_manifest_path": "output/createpdf-audit/createpdf.artifact-manifest.json",
      "artifact_graph_path": "output/createpdf-audit/createpdf.artifact-graph.json",
      "requested_renderer_backend": "auto",
      "renderer_backend": {
        "backend_id": "local_html_package_fallback",
        "fallback": true,
        "fallback_reason": "browser_renderer_worker_unavailable",
        "layout_fidelity": "text_layout_approximation"
      },
      "render_skipped": false,
      "renderer_backend_count": 1,
      "renderer_backend_refs": [
        {"backend_id": "local_html_package_fallback", "fallback": true}
      ],
      "html_render_profile_count": 1,
      "html_render_profile_refs": [
        {"render_profile_id": "browser_print_a4_v0", "page_size": "A4"}
      ],
      "artifact_graph_summary": {
        "html_render_profile_count": 1,
        "html_layer_count": 0
      },
      "bundle_path": "output/createpdf.agentpdf-bundle.zip",
      "bundle_export": {"tool": "pdf.artifacts.export_bundle"},
      "bundle_verification": {
        "tool": "pdf.artifacts.verify_bundle",
        "validation": {"status": "passed"}
      }
    }
  },
  "next_recommended_tools": ["pdf.patch.plan", "pdf.artifacts.verify_bundle"]
}
```

## Error Example

```json
{
  "status": "failed",
  "tool": "pdf.authoring.plan",
  "error": {
    "code": "authoring_invalid_brief",
    "message": "Authoring brief is invalid or unsafe.",
    "retry_hint": "Provide a non-empty topic and a page_count between 1 and 80."
  }
}
```

## Limitations

- The OSS MVP does not browse the web.
- The OSS MVP does not call an LLM to synthesize insights.
- HTML/CSS rendering defaults to the local fallback unless `browser_chromium` and the optional Playwright worker are installed.
- DOCX and PPTX routes are recommended by `pdf.authoring.plan`, but this MVP implements the HTML source-package path. Target okoffice routes should use `word.create.document` and `deck.create.presentation` once implemented.

## License and Dependency Notes

The default local path uses existing PDF-domain dependencies and does not add GPL or AGPL libraries. Optional browser or Office workers must stay behind explicit feature flags and documentation.
