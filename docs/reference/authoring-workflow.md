# Authoring Workflow

AgentPDF treats PDF creation as an authoring workflow before rendering. The local OSS path can plan an authoring route, plan source gathering, normalize agent-supplied source cards, extract evidence cards, build a storyboard, write or revise page JSON, create a self-contained HTML package, render it to PDF, and run visual QA. The HTML package is the inspectable source layer for the final PDF.

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
okpdf createpdf --html "<main><h1>CreatePDF</h1><p>HTML-first source package.</p></main>" --html-output output/createpdf.html --pdf-output output/createpdf.pdf --artifact-dir output/createpdf-audit --json
```

Without `--execute`, `workflow research-deck` returns the workflow plan only. With `--execute`, it runs the planned local steps and returns `usage.workflow_run` plus PDF, HTML manifest, and QA artifacts.
Use `okpdf createpdf` when the agent already has HTML or page JSON and wants a single local workflow that writes the HTML package, renders the PDF, runs visual QA, and emits an artifact manifest plus graph.

The `pdf.research.*` tools are local normalizers: they do not browse, fetch, summarize remote pages, or create fresh claims from the web. Agents should provide source metadata gathered elsewhere, then let AgentPDF preserve source ids, confidence, useful page targets, and `fetch_status=not_fetched`.

## REST Example

```bash
curl -s http://127.0.0.1:7331/v1/tools/pdf.authoring.plan/run \
  -H "content-type: application/json" \
  -d '{"brief":{"topic":"AgentPDF authoring","page_count":6}}'

curl -s http://127.0.0.1:7331/v1/tools/pdf.research.source_cards/run \
  -H "content-type: application/json" \
  -d '{"brief":{"topic":"AgentPDF authoring","page_count":6},"sources":[{"title":"State of Mobile 2026","source_type":"report","summary":"Revenue growth continues while downloads flatten.","key_points":["Revenue growth continues while downloads flatten."]}]}'

curl -s http://127.0.0.1:7331/v1/tools/pdf.workflow.research_deck/run \
  -H "content-type: application/json" \
  -d '{"brief":{"topic":"AgentPDF authoring","page_count":6,"deliverable":"deck"},"evidence_cards":[],"html_output_path":"output/deck.html","pdf_output_path":"output/deck.pdf","artifact_dir":"output/research-deck-artifacts","execute":true}'

curl -s http://127.0.0.1:7331/v1/tools/pdf.workflow.createpdf/run \
  -H "content-type: application/json" \
  -d '{"html":"<main><h1>CreatePDF</h1><p>HTML-first source package.</p></main>","html_output_path":"output/createpdf.html","pdf_output_path":"output/createpdf.pdf","artifact_dir":"output/createpdf-audit"}'
```

## MCP Example

```json
{
  "tool": "pdf_workflow_research_deck",
  "arguments": {
    "brief": {
      "topic": "AgentPDF authoring",
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
    "artifact_dir": "output/createpdf-audit"
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
- HTML/CSS rendering uses the existing local HTML package path and may not match a managed browser renderer exactly.
- DOCX and PPTX routes are recommended by `pdf.authoring.plan`, but this MVP implements the HTML source-package path.

## License and Dependency Notes

The default local path uses existing AgentPDF dependencies and does not add GPL or AGPL libraries. Optional browser or Office workers must stay behind explicit feature flags and documentation.
