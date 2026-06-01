import assert from "node:assert/strict";
import test from "node:test";

import { AgentPDFClient } from "../src/index.js";
import type { ToolManifest, ToolResult } from "../src/index.js";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

test("AgentPDFClient lists tools from the local REST API", async () => {
  const manifest: ToolManifest = {
    manifest_version: "0.1-full",
    tools: [
      {
        name: "pdf.inspect.document",
        status: "stable",
        description: "Inspect a PDF.",
        interfaces: ["cli", "mcp", "rest"],
        implemented: true,
      },
    ],
  };
  const calls: string[] = [];
  const client = new AgentPDFClient({
    baseUrl: "http://agentpdf.test",
    fetch: async (input) => {
      calls.push(String(input));
      return jsonResponse(manifest);
    },
  });

  const result = await client.listTools();

  assert.equal(calls[0], "http://agentpdf.test/v1/tools");
  assert.equal(result.tools[0]?.name, "pdf.inspect.document");
});

test("AgentPDFClient runs text-to-PDF with the expected payload", async () => {
  const toolResult: ToolResult = {
    job_id: "job_node",
    status: "succeeded",
    tool: "pdf.convert.text_to_pdf",
    artifacts: [],
    validation: null,
    warnings: [],
    usage: { text_length: 11 },
    next_recommended_tools: ["pdf.inspect.document"],
    error: null,
  };
  let postedBody: unknown;
  const client = new AgentPDFClient({
    baseUrl: "http://agentpdf.test/",
    fetch: async (input, init) => {
      assert.equal(String(input), "http://agentpdf.test/v1/tools/pdf.convert.text_to_pdf/run");
      assert.equal(init?.method, "POST");
      postedBody = JSON.parse(String(init?.body));
      return jsonResponse(toolResult);
    },
  });

  const result = await client.createTextPdf({
    text: "hello world",
    outputPath: "out.pdf",
    title: "Hello",
  });

  assert.deepEqual(postedBody, {
    text: "hello world",
    output_path: "out.pdf",
    title: "Hello",
  });
  assert.equal(result.tool, "pdf.convert.text_to_pdf");
});

test("AgentPDFClient returns failed ToolResult bodies instead of hiding them", async () => {
  const failed: ToolResult = {
    job_id: "job_failed",
    status: "failed",
    tool: "pdf.inspect.document",
    artifacts: [],
    validation: null,
    warnings: ["Input file not found"],
    usage: {},
    next_recommended_tools: [],
    error: { code: "file_not_found", message: "Input file not found" },
  };
  const client = new AgentPDFClient({
    baseUrl: "http://agentpdf.test",
    fetch: async () => jsonResponse(failed, 400),
  });

  const result = await client.inspectDocument({ path: "missing.pdf" });

  assert.equal(result.status, "failed");
  assert.equal(result.error?.code, "file_not_found");
});
