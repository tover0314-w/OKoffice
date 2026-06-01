# 25 — SDK Specification

## Python SDK target

```python
from agentpdf import AgentPDF

client = AgentPDF.local()

result = client.tools.run(
    "pdf.organize.merge",
    files=["a.pdf", "b.pdf"],
    output="merged.pdf",
    validate=True,
)

print(result.artifacts[0].path)
```

Convenience methods:

```python
client.inspect("report.pdf")
client.merge(["a.pdf", "b.pdf"], output="merged.pdf")
client.split("report.pdf", pages="1-3", output_dir="parts")
client.render("report.pdf", pages="1", output_dir="renders")
client.ask("report.pdf", "What are the risks?")
client.create_from_markdown("summary.md", style="business_report_modern", output="report.pdf")
```

## TypeScript SDK

```ts
import { AgentPDFClient } from "@okpdf/agentpdf-node";

const client = new AgentPDFClient({ baseUrl: "http://127.0.0.1:7331" });
const result = await client.merge({
  inputPaths: ["a.pdf", "b.pdf"],
  outputPath: "merged.pdf",
});
```

Convenience methods:

```ts
client.listTools();
client.getTool("pdf.organize.merge");
client.runTool("pdf.convert.text_to_pdf", {
  text: "Hello",
  output_path: "hello.pdf",
});
client.inspectDocument({ path: "report.pdf" });
client.inspectPages({ inputPath: "report.pdf", pages: "1-3", renderCheck: true });
client.workflowPlan({ goal: "Chat with this PDF", inputPath: "report.pdf" });
client.workflowRun({ workflow: { input_path: "report.pdf", steps: [] } });
client.workflowReport({ workflowRun: { run_id: "wfrun_123", step_results: [] } });
client.merge({ inputPaths: ["a.pdf", "b.pdf"], outputPath: "merged.pdf" });
client.reorderPages({ inputPath: "merged.pdf", order: "2,1", outputPath: "reordered.pdf" });
client.insertBlankPages({ inputPath: "reordered.pdf", afterPage: 1, count: 1, outputPath: "with-blank.pdf" });
client.compress({ inputPath: "with-blank.pdf", outputPath: "with-blank-compressed.pdf" });
client.repair({ inputPath: "with-blank-compressed.pdf", outputPath: "with-blank-repaired.pdf" });
client.imageToPdf({ imagePaths: ["cover.png"], outputPath: "cover.pdf" });
client.watermark({ inputPath: "cover.pdf", text: "DRAFT", outputPath: "cover-draft.pdf" });
client.addPageNumbers({ inputPath: "cover-draft.pdf", outputPath: "cover-numbered.pdf" });
client.createTextPdf({ text: "Hello", outputPath: "hello.pdf" });
client.createMarkdownPdf({
  markdown: "# Report\n\nHello",
  outputPath: "report.pdf",
  stylePack: "business_report_modern",
});
client.validateOutput({ path: "cover-numbered.pdf", expectedPages: 1 });
client.renderCheck({ path: "cover-numbered.pdf", pages: "1" });
client.blankPageCheck({ path: "with-blank.pdf", pages: "all" });
client.extractImages({ inputPath: "cover-numbered.pdf", pages: "all", outDir: "cover-images" });
client.parseLite({ inputPath: "cover-numbered.pdf" });
client.pdfToJson({ inputPath: "cover-numbered.pdf", outputPath: "cover-numbered.ir.json" });
client.pdfToMarkdown({ inputPath: "cover-numbered.pdf", outputPath: "cover-numbered.md" });
client.ragIngest({
  inputPath: "cover-numbered.pdf",
  indexPath: "cover-numbered.index.json",
});
client.ragChat({
  inputPath: "cover-numbered.pdf",
  question: "What is this PDF about?",
  reportOutputPath: "cover-chat-report.pdf",
  highlightOutputPath: "cover-chat-highlighted.pdf",
});
client.ragQuery({
  indexPath: "cover-numbered.index.json",
  query: "What is this PDF about?",
});
client.ragSearch({
  indexPath: "cover-numbered.index.json",
  query: "PDF",
});
client.ragHighlightSources({
  indexPath: "cover-numbered.index.json",
  answer: "The cover is numbered.",
  outputPath: "cover-highlighted.pdf",
});
client.ragExportReport({
  indexPath: "cover-numbered.index.json",
  question: "What is this PDF about?",
  answer: "The cover is numbered.",
  outputPath: "cover-rag-report.pdf",
});
```

## SDK principles

- SDK wraps the same tool registry.
- No separate hidden behavior.
- Local and hosted clients should share the same method names.
- Hosted client later adds auth, retries, and async polling.
- Results use the same ToolResult schema.

## Client modes

```text
AgentPDF.local()      -> in-process/local CLI-style execution
AgentPDF.api(url)     -> local/remote REST API
AgentPDF.cloud(key)   -> future hosted API
AgentPDFClient(url)   -> TypeScript REST client for Node.js agents and apps
```

## Async jobs

SDK should support:

```python
job = client.jobs.submit("pdf.ai.parse.agentic", file="paper.pdf")
job.wait()
result = job.result()
```

Local deterministic tools may return immediately.
