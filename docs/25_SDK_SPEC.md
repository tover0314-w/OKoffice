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

## TypeScript SDK target

```ts
import { AgentPDF } from "@agentpdf/sdk";

const client = AgentPDF.local();
const result = await client.merge(["a.pdf", "b.pdf"], { output: "merged.pdf" });
```

## SDK principles

- SDK wraps the same tool registry.
- No separate hidden behavior.
- Local and hosted clients share the same method names.
- Hosted client adds auth, retries, and async polling.
- Results use the same ToolResult schema.

## Client modes

```text
AgentPDF.local()      -> in-process/local CLI-style execution
AgentPDF.api(url)     -> local/remote REST API
AgentPDF.cloud(key)   -> future hosted API
```

## Async jobs

SDK should support:

```python
job = client.jobs.submit("pdf.ai.parse.agentic", file="paper.pdf")
job.wait()
result = job.result()
```

Local deterministic tools may return immediately.
