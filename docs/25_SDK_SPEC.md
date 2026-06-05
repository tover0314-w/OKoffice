# 25 - okoffice SDK Specification

## SDK Goal

The SDK should wrap the same ToolResult contract exposed by CLI, MCP, and REST. It should not create a second behavior layer or hide validation evidence.

Current compatibility clients:

- Python import path: `agentpdf`
- TypeScript package: `@okpdf/agentpdf-node`

Target okoffice clients:

- Python import path: `okoffice`
- TypeScript package: `@okoffice/node`

## Python SDK Target

```python
from okoffice import OkOffice

client = OkOffice.local()

result = client.tools.run(
    "sheet.inspect.workbook",
    file={"kind": "local_path", "path": "evidence.xlsx"},
    include_formulas=True,
)

print(result.usage["sheet_count"])
```

Compatibility:

```python
from agentpdf import AgentPDF

client = AgentPDF.local()
result = client.tools.run(
    "pdf.organize.merge",
    files=["a.pdf", "b.pdf"],
    output="merged.pdf",
    validate=True,
)
```

## Python Convenience Methods

Target methods:

```python
client.inspect("report.docx")
client.inspect("model.xlsx")
client.inspect("deck.pptx")
client.inspect("packet.pdf")

client.word.inspect("report.docx")
client.sheet.inspect("model.xlsx")
client.deck.inspect("deck.pptx")
client.pdf.inspect("packet.pdf")

client.workflow.docset_to_sheet(
    sources=["sources/a.docx", "sources/b.pdf"],
    output="evidence.xlsx",
    schema={"fields": ["vendor", "renewal_date", "annual_amount"]},
)

client.workflow.sheet_to_deck(
    workbook="evidence.xlsx",
    output="board-deck.pptx",
    profile="board_deck",
)

client.bundle.export(
    artifacts=["evidence.xlsx", "board-deck.pptx", "handout.pdf"],
    output="board-pack.okoffice.zip",
)
```

PDF compatibility methods:

```python
client.pdf.merge(["a.pdf", "b.pdf"], output="merged.pdf")
client.pdf.split("report.pdf", pages="1-3", output_dir="parts")
client.pdf.render("report.pdf", pages="1", output_dir="renders")
client.pdf.ask("report.pdf", "What are the risks?")
client.pdf.create_from_markdown("summary.md", style="business_report_modern", output="report.pdf")
```

## TypeScript SDK Target

```ts
import { OkOfficeClient } from "@okoffice/node";

const client = new OkOfficeClient({ baseUrl: "http://127.0.0.1:7331" });

const workbook = await client.runTool("sheet.inspect.workbook", {
  file: { kind: "local_path", path: "evidence.xlsx" },
  includeFormulas: true,
});

console.log(workbook.usage.sheet_count);
```

Compatibility:

```ts
import { AgentPDFClient } from "@okpdf/agentpdf-node";

const client = new AgentPDFClient({ baseUrl: "http://127.0.0.1:7331" });
const result = await client.merge({
  inputPaths: ["a.pdf", "b.pdf"],
  outputPath: "merged.pdf",
});
```

## TypeScript Convenience Methods

Target methods:

```ts
client.listTools();
client.getTool("sheet.inspect.workbook");
client.runTool("office.inspect.file", {
  file: { kind: "local_path", path: "report.docx" },
});

client.inspect({ path: "report.docx" });
client.word.inspectDocument({ path: "report.docx" });
client.wordValidateDocument({ path: "report.docx" });
client.sheet.inspectWorkbook({ path: "model.xlsx" });
client.deck.inspectPresentation({ path: "deck.pptx" });
client.deckValidatePresentation({ path: "deck.pptx" });

client.workflow.docsetToSheet({
  sources: ["sources/a.docx", "sources/b.pdf"],
  outputPath: "evidence.xlsx",
  schema: { fields: ["vendor", "annual_amount"] },
});

client.workflow.sheetToDeck({
  workbookPath: "evidence.xlsx",
  outputPath: "board-deck.pptx",
  profile: "board_deck",
});

client.bundle.export({
  artifacts: ["evidence.xlsx", "board-deck.pptx", "handout.pdf"],
  outputPath: "board-pack.okoffice.zip",
});
```

PDF compatibility methods can continue to mirror `@okpdf/agentpdf-node` until the migration is complete.

## SDK Principles

- SDK wraps the same tool registry.
- No separate hidden behavior.
- Local and hosted clients share method names.
- Hosted client later adds auth, retries, async polling, and signed downloads.
- Results use the same ToolResult schema.
- Binary artifacts are referenced by path/artifact id, not embedded in large JSON by default.
- Warnings and validation are first-class fields, not console-only messages.

## Client Modes

```text
OkOffice.local()      -> in-process/local CLI-style execution
OkOffice.api(url)     -> local/remote REST API
OkOffice.cloud(key)   -> future hosted API
OkOfficeClient(url)   -> TypeScript REST client for Node.js agents and apps
```

Compatibility:

```text
AgentPDF.local()      -> compatibility PDF-domain client
AgentPDF.api(url)     -> compatibility local/remote REST API client
AgentPDFClient(url)   -> current TypeScript REST client
```

## Async Jobs

SDK should support:

```python
job = client.jobs.submit(
    "office.workflow.docset_to_sheet",
    sources=["a.docx", "b.pdf"],
    output_path="evidence.xlsx",
)
job.wait()
result = job.result()
```

Local deterministic tools may return immediately. Hosted or optional workers may use polling, webhooks, or durable job ids.

## Type Shape

The SDK should expose the public envelope:

```ts
type ToolResult<TUsage = Record<string, unknown>> = {
  job_id: string;
  status: "succeeded" | "failed" | "warning";
  tool: string;
  artifacts: ArtifactRef[];
  validation: Record<string, unknown>;
  warnings: string[];
  usage: TUsage;
  next_recommended_tools: string[];
};
```
