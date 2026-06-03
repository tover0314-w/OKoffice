# Authoring Workflow

AgentPDF treats PDF creation as an authoring workflow before rendering. The local OSS path can plan an authoring route, build a storyboard, write page JSON, create a self-contained HTML package, render it to PDF, and run visual QA. The HTML package is the inspectable source layer for the final PDF.

## When to Use It

Use this workflow when an agent needs to create a deck or report from a brief, evidence cards, and design constraints. It is most useful for fixed-page visual documents where source traceability and validation matter.

## CLI Example

```bash
okpdf authoring plan examples/research_deck_brief.json --json
okpdf storyboard plan examples/research_deck_brief.json --evidence-cards examples/research_deck_evidence.json --json
okpdf workflow research-deck examples/research_deck_brief.json --evidence-cards examples/research_deck_evidence.json --html-output output/deck.html --pdf-output output/deck.pdf --artifact-dir output/research-deck-artifacts --execute --json
```

Without `--execute`, `workflow research-deck` returns the workflow plan only. With `--execute`, it runs the planned local steps and returns `usage.workflow_run` plus PDF, HTML manifest, and QA artifacts.

## REST Example

```bash
curl -s http://127.0.0.1:7331/v1/tools/pdf.authoring.plan/run \
  -H "content-type: application/json" \
  -d '{"brief":{"topic":"AgentPDF authoring","page_count":6}}'

curl -s http://127.0.0.1:7331/v1/tools/pdf.workflow.research_deck/run \
  -H "content-type: application/json" \
  -d '{"brief":{"topic":"AgentPDF authoring","page_count":6,"deliverable":"deck"},"evidence_cards":[],"html_output_path":"output/deck.html","pdf_output_path":"output/deck.pdf","artifact_dir":"output/research-deck-artifacts","execute":true}'
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
  "next_recommended_tools": []
}
```

## Error Example

```json
{
  "status": "failed",
  "tool": "pdf.authoring.plan",
  "error": {
    "code": "authoring_invalid_brief",
    "message": "Authoring brief is invalid or incomplete."
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
