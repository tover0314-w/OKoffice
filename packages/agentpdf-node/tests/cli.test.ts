import assert from "node:assert/strict";
import test from "node:test";

import { runCli } from "../src/cli.js";
import type { ToolResult } from "../src/index.js";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

test("runCli sends generic tool payloads to the local API", async () => {
  const toolResult: ToolResult = {
    job_id: "job_cli",
    status: "succeeded",
    tool: "pdf.convert.text_to_pdf",
    artifacts: [],
    validation: null,
    warnings: [],
    usage: {},
    next_recommended_tools: [],
    error: null,
  };
  const output: string[] = [];
  let postedBody: unknown;

  const code = await runCli(
    [
      "--base-url",
      "http://agentpdf.test",
      "run",
      "pdf.convert.text_to_pdf",
      "--payload",
      "{\"text\":\"hello\",\"output_path\":\"out.pdf\"}",
    ],
    {
      fetch: async (_input, init) => {
        postedBody = JSON.parse(String(init?.body));
        return jsonResponse(toolResult);
      },
      stdout: (line) => output.push(line),
      stderr: (line) => output.push(`ERR:${line}`),
    },
  );

  assert.equal(code, 0);
  assert.deepEqual(postedBody, { text: "hello", output_path: "out.pdf" });
  assert.equal(JSON.parse(output[0] ?? "{}").tool, "pdf.convert.text_to_pdf");
});

test("runCli exposes a convenient create-text command", async () => {
  const output: string[] = [];
  let postedBody: unknown;

  const code = await runCli(
    ["create-text", "--text", "Hello Node", "-o", "node.pdf"],
    {
      fetch: async (_input, init) => {
        postedBody = JSON.parse(String(init?.body));
        return jsonResponse({
          job_id: "job_create_text",
          status: "succeeded",
          tool: "pdf.convert.text_to_pdf",
          artifacts: [],
          validation: null,
          warnings: [],
          usage: {},
          next_recommended_tools: [],
          error: null,
        });
      },
      stdout: (line) => output.push(line),
      stderr: (line) => output.push(`ERR:${line}`),
    },
  );

  assert.equal(code, 0);
  assert.deepEqual(postedBody, { text: "Hello Node", output_path: "node.pdf" });
  assert.equal(JSON.parse(output[0] ?? "{}").status, "succeeded");
});
