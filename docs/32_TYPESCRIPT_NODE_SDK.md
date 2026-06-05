# 32 - TypeScript And Node.js SDK

okoffice uses Python for the local core and TypeScript for agent/app ergonomics. The TypeScript package currently lives in `packages/okoffice-node` and talks to the local REST API.

Target package:

```text
@okoffice/node
```

Compatibility package:

```text
@okoffice/okoffice-node
```

## Why This Boundary

- Format engines remain consistent across CLI, MCP, REST, and SDK calls.
- Node.js agents and web apps can use typed results without spawning Python directly.
- Future hosted APIs can reuse the same client shape.
- The JavaScript package stays license-safe and lightweight.
- The SDK is a client, not a second Office/PDF engine.

## Current Local Development

```bash
npm install
npm run build:node
npm test --workspace @okoffice/okoffice-node
```

Run the local API:

```bash
okoffice serve --api
```

## Target Local Development

```bash
pnpm install
pnpm --filter @okoffice/node build
pnpm --filter @okoffice/node test
okoffice serve --api
```

## Current Compatibility Usage

```ts
import { OKofficeClient } from "@okoffice/okoffice-node";

const client = new OKofficeClient({ baseUrl: "http://127.0.0.1:7331" });

const tools = await client.listTools();
const result = await client.runTool("pdf.inspect.document", {
  path: "report.pdf",
});
```

## Target okoffice Usage

```ts
import { OkOfficeClient } from "@okoffice/node";

const client = new OkOfficeClient({ baseUrl: "http://127.0.0.1:7331" });

const pack = await client.runTool("office.workflow.board_pack", {
  files: ["memo.docx", "diligence.pdf", "metrics.xlsx"],
  schema: {
    fields: [
      { name: "vendor", type: "string", aliases: ["Vendor"] },
      { name: "renewal_date", type: "date", aliases: ["Renewal date"] },
    ],
  },
  out_dir: ".okoffice-out/board-pack",
  title: "Vendor Renewal Review",
  profile: "board_review",
  include_pdf_handout: true,
});

console.log(pack.artifacts);
console.log(pack.validation);
console.log(pack.warnings);
```

## Typed Convenience Methods

The SDK may add convenience methods, but each should delegate to `runTool`.

Examples:

```ts
await client.inspect("memo.docx");
await client.contextBuild({
  files: ["memo.docx", "diligence.pdf", "metrics.xlsx"],
  outputPath: ".okoffice-out/context.json",
});
await client.wordValidateDocument({
  path: "memo.docx",
});
await client.docsetToSheet({
  files: ["memo.docx", "diligence.pdf"],
  schemaPath: "examples/schemas/kpi-review.json",
  outputPath: ".okoffice-out/evidence.xlsx",
});
await client.sheetToDeck({
  workbookPath: ".okoffice-out/evidence.xlsx",
  outputPath: ".okoffice-out/board-review.pptx",
});
await client.deckValidatePresentation({
  path: ".okoffice-out/board-review.pptx",
});
await client.exportBundle({
  files: [
    ".okoffice-out/evidence.xlsx",
    ".okoffice-out/board-review.pptx",
    ".okoffice-out/board-review.pdf"
  ],
  outputPath: ".okoffice-out/board-pack.zip",
});
```

## ToolResult Contract

All SDK methods return the same envelope:

```ts
type ToolResult = {
  job_id: string;
  status: "succeeded" | "failed" | "running" | "queued";
  tool: string;
  artifacts: Artifact[];
  validation?: ValidationReport;
  warnings: string[];
  usage: Record<string, unknown>;
  next_recommended_tools: string[];
  error?: AgentError;
};
```

## SDK Responsibilities

The SDK should:

- Provide typed request/response helpers.
- Preserve raw `ToolResult` fields.
- Surface warnings and validation.
- Avoid hiding failed/skipped checks.
- Support local and hosted base URLs.
- Avoid bundling heavy Office/PDF dependencies.

The SDK should not:

- Parse Office files directly.
- Execute macros.
- Rewrite artifacts.
- Convert warnings into success.
- Depend on hosted okoffice for local deterministic operations.

## Migration Notes

During migration:

- Keep `OKofficeClient`.
- Add `OkOfficeClient` as a wrapper or alias once REST routes support `office.*`.
- Keep existing tests for `pdf.*`.
- Add new tests for `office.*` request shaping before implementation.
- Keep Node CLI compatibility commands until `okoffice-node` or `okoffice` CLI is ready.
