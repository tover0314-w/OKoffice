import assert from "node:assert/strict";
import { mkdtemp, rm, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { tmpdir } from "node:os";
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

test("runCli exposes target profile commands", async () => {
  const calls: Array<{ url: string; body: unknown }> = [];

  async function invoke(args: string[]): Promise<number> {
    return runCli(args, {
      fetch: async (input, init) => {
        calls.push({ url: String(input), body: JSON.parse(String(init?.body)) });
        const tool = String(input).includes("validate_profile")
          ? "pdf.target.validate_profile"
          : "pdf.target.profiles";
        return jsonResponse({
          job_id: `job_${tool}`,
          status: "succeeded",
          tool,
          artifacts: [],
          validation: null,
          warnings: [],
          usage: {},
          next_recommended_tools: [],
          error: null,
        });
      },
      stdout: () => undefined,
      stderr: () => undefined,
    });
  }

  assert.equal(await invoke(["target-profiles", "-o", "profiles.json"]), 0);
  assert.equal(
    await invoke([
      "target-validate",
      "--target-profile",
      "{\"profile_id\":\"board_packet\",\"layout_mode\":\"document\"}",
      "-o",
      "profile.validation.json",
    ]),
    0,
  );
  assert.deepEqual(calls, [
    {
      url: "http://127.0.0.1:7331/v1/tools/pdf.target.profiles/run",
      body: { output_path: "profiles.json" },
    },
    {
      url: "http://127.0.0.1:7331/v1/tools/pdf.target.validate_profile/run",
      body: {
        target_profile: { profile_id: "board_packet", layout_mode: "document" },
        output_path: "profile.validation.json",
      },
    },
  ]);
});

test("runCli exposes template pack commands", async () => {
  const calls: Array<{ url: string; body: unknown }> = [];
  const tempDir = await mkdtemp(join(tmpdir(), "agentpdf-node-cli-"));
  const dataPath = join(tempDir, "agent-block-data.json");
  await writeFile(
    dataPath,
    JSON.stringify({
      title: "Agent Block Audit",
      blocks: [
        {
          block_id: "blk_agent_code",
          type: "code",
          title: "Risky Function",
          code: "def risky_total(items):\n    return sum(items)\n",
          source_refs: ["ctx_code"],
        },
      ],
    }),
    "utf8",
  );

  async function invoke(args: string[]): Promise<number> {
    return runCli(args, {
      fetch: async (input, init) => {
        calls.push({ url: String(input), body: JSON.parse(String(init?.body)) });
        return jsonResponse({
          job_id: "job_template_pack_cli",
          status: "succeeded",
          tool: calls.at(-1)?.url.split("/v1/tools/")[1]?.split("/run")[0] ?? "unknown",
          artifacts: [],
          validation: null,
          warnings: [],
          usage: {},
          next_recommended_tools: [],
          error: null,
        });
      },
      stdout: () => undefined,
      stderr: () => undefined,
    });
  }

  try {
    assert.equal(await invoke(["create-template-packs", "-o", "template-packs.json"]), 0);
    assert.equal(
      await invoke([
        "create-validate-template-pack",
        "examples/template-packs/local-agent-starter.json",
        "-o",
        "template-pack.validation.json",
      ]),
      0,
    );
    assert.equal(
      await invoke([
        "create-plan-template-pack",
        "examples/template-packs/local-agent-starter.json",
        "--profile",
        "technical_audit",
        "--context-packet",
        "context.packet.json",
        "--planned-output",
        "board-audit.pdf",
        "-o",
        "board-audit.plan.json",
      ]),
      0,
    );
    assert.equal(
      await invoke([
        "create-agent",
        "examples/template-packs/local-agent-starter.json",
        "--profile",
        "technical_audit",
        "--context-packet",
        "context.packet.json",
        "-o",
        "board-audit.pdf",
        "--plan-output",
        "board-audit.plan.json",
        "--coverage-output",
        "board-audit.coverage.json",
      ]),
      0,
    );
    assert.equal(
      await invoke([
        "create-from-template-pack",
        "examples/template-packs/local-agent-starter.json",
        "--template",
        "board_audit",
        "--color-scheme",
        "executive_blue",
        "--data",
        dataPath,
        "--context-packet",
        "context.packet.json",
        "-o",
        "board-audit.pdf",
      ]),
      0,
    );
  } finally {
    await rm(tempDir, { recursive: true, force: true });
  }

  assert.deepEqual(calls, [
    {
      url: "http://127.0.0.1:7331/v1/tools/pdf.ai.create.template_packs/run",
      body: { output_path: "template-packs.json" },
    },
    {
      url: "http://127.0.0.1:7331/v1/tools/pdf.ai.create.validate_template_pack/run",
      body: {
        template_pack_path: "examples/template-packs/local-agent-starter.json",
        output_path: "template-pack.validation.json",
      },
    },
    {
      url: "http://127.0.0.1:7331/v1/tools/pdf.ai.create.plan_template_pack/run",
      body: {
        template_pack_path: "examples/template-packs/local-agent-starter.json",
        profile: "technical_audit",
        context_packet_path: "context.packet.json",
        planned_output_path: "board-audit.pdf",
        output_path: "board-audit.plan.json",
      },
    },
    {
      url: "http://127.0.0.1:7331/v1/tools/pdf.ai.create.agent/run",
      body: {
        template_pack_path: "examples/template-packs/local-agent-starter.json",
        profile: "technical_audit",
        context_packet_path: "context.packet.json",
        output_path: "board-audit.pdf",
        plan_output_path: "board-audit.plan.json",
        coverage_output_path: "board-audit.coverage.json",
      },
    },
    {
      url: "http://127.0.0.1:7331/v1/tools/pdf.ai.create.from_template_pack/run",
      body: {
        template_pack_path: "examples/template-packs/local-agent-starter.json",
        template_id: "board_audit",
        output_path: "board-audit.pdf",
        color_scheme: "executive_blue",
        context_packet_path: "context.packet.json",
        data: {
          title: "Agent Block Audit",
          blocks: [
            {
              block_id: "blk_agent_code",
              type: "code",
              title: "Risky Function",
              code: "def risky_total(items):\n    return sum(items)\n",
              source_refs: ["ctx_code"],
            },
          ],
        },
      },
    },
  ]);
});

test("runCli exposes artifact bundle export command", async () => {
  const output: string[] = [];
  let postedBody: unknown;

  const code = await runCli(
    [
      "export-bundle",
      "--file",
      "report.pdf",
      "--file",
      "report.composition.json",
      "-o",
      "report.agentpdf-bundle.zip",
      "--title",
      "Report Bundle",
      "--metadata",
      "agent=codex",
    ],
    {
      fetch: async (input, init) => {
        assert.equal(String(input), "http://127.0.0.1:7331/v1/tools/pdf.artifacts.export_bundle/run");
        postedBody = JSON.parse(String(init?.body));
        return jsonResponse({
          job_id: "job_bundle_cli",
          status: "succeeded",
          tool: "pdf.artifacts.export_bundle",
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
  assert.equal(JSON.parse(output[0] ?? "{}").tool, "pdf.artifacts.export_bundle");
  assert.deepEqual(postedBody, {
    artifact_paths: ["report.pdf", "report.composition.json"],
    output_path: "report.agentpdf-bundle.zip",
    title: "Report Bundle",
    metadata: { agent: "codex" },
  });
});

test("runCli exposes artifact bundle verify command", async () => {
  const output: string[] = [];
  let postedBody: unknown;

  const code = await runCli(
    ["verify-bundle", "report.agentpdf-bundle.zip"],
    {
      fetch: async (input, init) => {
        assert.equal(String(input), "http://127.0.0.1:7331/v1/tools/pdf.artifacts.verify_bundle/run");
        postedBody = JSON.parse(String(init?.body));
        return jsonResponse({
          job_id: "job_bundle_verify_cli",
          status: "succeeded",
          tool: "pdf.artifacts.verify_bundle",
          artifacts: [],
          validation: { status: "passed", checks: [], warnings: [] },
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
  assert.equal(JSON.parse(output[0] ?? "{}").tool, "pdf.artifacts.verify_bundle");
  assert.deepEqual(postedBody, {
    bundle_path: "report.agentpdf-bundle.zip",
  });
});

test("runCli exposes Claude Code agent setup command", async () => {
  const output: string[] = [];
  let postedBody: unknown;

  const code = await runCli(
    [
      "agent-setup-claude-code",
      "-o",
      ".mcp.json",
      "--safe-root",
      "${CLAUDE_PROJECT_DIR:-.}",
      "--command",
      "python",
      "--arg-prefix",
      "-m",
      "--arg-prefix",
      "agentpdf.cli",
    ],
    {
      fetch: async (input, init) => {
        assert.equal(String(input), "http://127.0.0.1:7331/v1/tools/agent.setup.claude_code/run");
        postedBody = JSON.parse(String(init?.body));
        return jsonResponse({
          job_id: "job_agent_setup",
          status: "succeeded",
          tool: "agent.setup.claude_code",
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
  assert.equal(JSON.parse(output[0] ?? "{}").tool, "agent.setup.claude_code");
  assert.deepEqual(postedBody, {
    output_path: ".mcp.json",
    safe_root: "${CLAUDE_PROJECT_DIR:-.}",
    command: "python",
    args_prefix: ["-m", "agentpdf.cli"],
  });
});

test("runCli exposes high-frequency PDF utility commands", async () => {
  const calls: Array<{ url: string; body: unknown }> = [];

  async function invoke(args: string[]): Promise<number> {
    return runCli(args, {
      fetch: async (input, init) => {
        calls.push({ url: String(input), body: JSON.parse(String(init?.body)) });
        return jsonResponse({
          job_id: "job_cli_util",
          status: "succeeded",
          tool: calls.at(-1)?.url.split("/v1/tools/")[1]?.split("/run")[0] ?? "unknown",
          artifacts: [],
          validation: null,
          warnings: [],
          usage: {},
          next_recommended_tools: [],
          error: null,
        });
      },
      stdout: () => undefined,
      stderr: () => undefined,
    });
  }

  assert.equal(await invoke(["inspect-pages", "cover.pdf", "--pages", "1", "--render-check"]), 0);
  assert.equal(
    await invoke(["workflow-plan", "--goal", "Chat with this PDF and cite answers.", "--input-path", "cover.pdf"]),
    0,
  );
  assert.equal(
    await invoke([
      "workflow-run",
      "--payload",
      "{\"steps\":[{\"step_id\":\"inspect\",\"tool\":\"pdf.inspect.document\",\"input\":{\"path\":\"cover.pdf\"}}]}",
      "--artifact-dir",
      "workflow-artifacts",
      "--binding",
      "<question>=What is covered?",
      "--dry-run",
    ]),
    0,
  );
  assert.equal(
    await invoke([
      "workflow-report",
      "--payload",
      "{\"run_id\":\"wfrun_node\",\"status\":\"succeeded\",\"planned_steps\":1,\"executed_steps\":1,\"failed_steps\":0,\"step_results\":[]}",
      "-o",
      "workflow-report.md",
    ]),
    0,
  );
  assert.equal(await invoke(["image-to-pdf", "cover.png", "-o", "cover.pdf"]), 0);
  assert.equal(await invoke(["reorder-pages", "cover.pdf", "--order", "1", "-o", "reordered.pdf"]), 0);
  assert.equal(
    await invoke([
      "insert-blank-pages",
      "reordered.pdf",
      "--after-page",
      "1",
      "--count",
      "1",
      "-o",
      "blank.pdf",
    ]),
    0,
  );
  assert.equal(await invoke(["compress", "blank.pdf", "-o", "compressed.pdf"]), 0);
  assert.equal(await invoke(["repair", "compressed.pdf", "-o", "repaired.pdf"]), 0);
  assert.equal(
    await invoke(["watermark", "cover.pdf", "--text", "CONFIDENTIAL", "-o", "wm.pdf"]),
    0,
  );
  assert.equal(await invoke(["page-numbers", "wm.pdf", "-o", "numbered.pdf"]), 0);
  assert.equal(await invoke(["validate", "numbered.pdf", "--expected-pages", "1"]), 0);
  assert.equal(await invoke(["render-check", "numbered.pdf", "--pages", "1"]), 0);
  assert.equal(await invoke(["blank-page-check", "numbered.pdf", "--pages", "1"]), 0);
  assert.equal(
    await invoke([
      "create-from-prompt",
      "--prompt",
      "Create a worksheet about local PDF templates.",
      "-o",
      "worksheet.pdf",
      "--template",
      "worksheet",
      "--style-pack",
      "paper_ink",
      "--color",
      "primary=#4f46e5",
      "--color",
      "accent=#f59e0b",
      "--data",
      "{\"sections\":[{\"heading\":\"Templates\",\"body\":\"Agents can create PDFs locally.\"}]}",
    ]),
    0,
  );
  assert.equal(await invoke(["create-templates"]), 0);
  assert.equal(
    await invoke(["create-template-preview", "--template", "invoice", "-o", "invoice-preview.pdf"]),
    0,
  );
  assert.equal(
    await invoke([
      "context-build",
      "--text",
      "Create a technical audit PDF.",
      "--file",
      "src/service.py",
      "--item-json",
      "{\"path\":\"examples/media/meeting-audio.mp3\",\"role\":\"audio_context\",\"label\":\"Meeting Audio\",\"transcript\":\"00:00 Kickoff\"}",
      "-o",
      "context.packet.json",
      "--title",
      "Audit Context",
      "--intent",
      "Compose a target PDF with evidence.",
    ]),
    0,
  );
  assert.equal(
    await invoke([
      "compose-from-context",
      "context.packet.json",
      "--profile",
      "technical_audit",
      "-o",
      "technical-audit.pdf",
    ]),
    0,
  );
  assert.equal(
    await invoke([
      "evidence-coverage-report",
      "technical-audit.composition.json",
      "-o",
      "technical-audit.coverage.json",
    ]),
    0,
  );
  assert.equal(
    await invoke([
      "patch-plan",
      "technical-audit.pdf",
      "--operations",
      "[{\"op\":\"append_table\",\"title\":\"Runtime Metrics\",\"columns\":[\"metric\",\"value\"],\"rows\":[[\"latency_ms\",\"42\"]],\"source_refs\":[\"ctx_002\"]}]",
      "-o",
      "technical-audit.patch.json",
      "--composition",
      "technical-audit.composition.json",
      "--layers",
      "technical-audit.layers.json",
      "--reason",
      "Append structured evidence.",
    ]),
    0,
  );
  assert.equal(
    await invoke(["patch-preview", "technical-audit.patch.json", "-o", "technical-audit.patch-preview.json"]),
    0,
  );
  assert.equal(
    await invoke(["patch-apply", "technical-audit.patch.json", "-o", "technical-audit-patched.pdf"]),
    0,
  );
  assert.equal(await invoke(["patch-verify", "technical-audit.patch.json", "technical-audit-patched.pdf"]), 0);
  assert.equal(await invoke(["extract-images", "numbered.pdf", "--pages", "1", "--out-dir", "images"]), 0);

  assert.deepEqual(calls.map((call) => call.url), [
    "http://127.0.0.1:7331/v1/tools/pdf.inspect.pages/run",
    "http://127.0.0.1:7331/v1/tools/pdf.workflow.plan/run",
    "http://127.0.0.1:7331/v1/tools/pdf.workflow.run/run",
    "http://127.0.0.1:7331/v1/tools/pdf.workflow.report/run",
    "http://127.0.0.1:7331/v1/tools/pdf.convert.image_to_pdf/run",
    "http://127.0.0.1:7331/v1/tools/pdf.organize.reorder_pages/run",
    "http://127.0.0.1:7331/v1/tools/pdf.organize.insert_blank_pages/run",
    "http://127.0.0.1:7331/v1/tools/pdf.optimize.compress/run",
    "http://127.0.0.1:7331/v1/tools/pdf.optimize.repair/run",
    "http://127.0.0.1:7331/v1/tools/pdf.edit.watermark/run",
    "http://127.0.0.1:7331/v1/tools/pdf.edit.page_numbers/run",
    "http://127.0.0.1:7331/v1/tools/pdf.validation.validate_output/run",
    "http://127.0.0.1:7331/v1/tools/pdf.validation.render_check/run",
    "http://127.0.0.1:7331/v1/tools/pdf.validation.blank_page_check/run",
    "http://127.0.0.1:7331/v1/tools/pdf.ai.create.from_prompt/run",
    "http://127.0.0.1:7331/v1/tools/pdf.ai.create.templates/run",
    "http://127.0.0.1:7331/v1/tools/pdf.ai.create.template_preview/run",
    "http://127.0.0.1:7331/v1/tools/pdf.context.build_packet/run",
    "http://127.0.0.1:7331/v1/tools/pdf.compose.from_context/run",
    "http://127.0.0.1:7331/v1/tools/pdf.evidence.coverage_report/run",
    "http://127.0.0.1:7331/v1/tools/pdf.patch.plan/run",
    "http://127.0.0.1:7331/v1/tools/pdf.patch.preview/run",
    "http://127.0.0.1:7331/v1/tools/pdf.patch.apply/run",
    "http://127.0.0.1:7331/v1/tools/pdf.patch.verify/run",
    "http://127.0.0.1:7331/v1/tools/pdf.convert.extract_images/run",
  ]);
  assert.deepEqual(calls[0]?.body, {
    input_path: "cover.pdf",
    pages: "1",
    render_check: true,
  });
  assert.deepEqual(calls[1]?.body, {
    goal: "Chat with this PDF and cite answers.",
    input_path: "cover.pdf",
  });
  assert.deepEqual(calls[2]?.body, {
    workflow: {
      steps: [{ step_id: "inspect", tool: "pdf.inspect.document", input: { path: "cover.pdf" } }],
      artifact_dir: "workflow-artifacts",
      bindings: {
        "<question>": "What is covered?",
      },
    },
    dry_run: true,
  });
  assert.deepEqual(calls[3]?.body, {
    workflow_run: {
      run_id: "wfrun_node",
      status: "succeeded",
      planned_steps: 1,
      executed_steps: 1,
      failed_steps: 0,
      step_results: [],
    },
    output_path: "workflow-report.md",
  });
  assert.deepEqual(calls[4]?.body, {
    image_paths: ["cover.png"],
    output_path: "cover.pdf",
  });
  assert.deepEqual(calls[5]?.body, {
    input_path: "cover.pdf",
    order: "1",
    output_path: "reordered.pdf",
  });
  assert.deepEqual(calls[6]?.body, {
    input_path: "reordered.pdf",
    after_page: 1,
    count: 1,
    output_path: "blank.pdf",
  });
  assert.deepEqual(calls[7]?.body, {
    input_path: "blank.pdf",
    output_path: "compressed.pdf",
  });
  assert.deepEqual(calls[8]?.body, {
    input_path: "compressed.pdf",
    output_path: "repaired.pdf",
  });
  assert.deepEqual(calls[9]?.body, {
    input_path: "cover.pdf",
    text: "CONFIDENTIAL",
    output_path: "wm.pdf",
  });
  assert.deepEqual(calls[10]?.body, {
    input_path: "wm.pdf",
    output_path: "numbered.pdf",
  });
  assert.deepEqual(calls[11]?.body, {
    path: "numbered.pdf",
    expected_pages: 1,
  });
  assert.deepEqual(calls[12]?.body, {
    path: "numbered.pdf",
    pages: "1",
  });
  assert.deepEqual(calls[13]?.body, {
    path: "numbered.pdf",
    pages: "1",
  });
  assert.deepEqual(calls[14]?.body, {
    prompt: "Create a worksheet about local PDF templates.",
    output_path: "worksheet.pdf",
    template: "worksheet",
    style_pack: "paper_ink",
    colors: {
      primary: "#4f46e5",
      accent: "#f59e0b",
    },
    data: {
      sections: [{ heading: "Templates", body: "Agents can create PDFs locally." }],
    },
  });
  assert.deepEqual(calls[15]?.body, {});
  assert.deepEqual(calls[16]?.body, {
    template: "invoice",
    output_path: "invoice-preview.pdf",
  });
  assert.deepEqual(calls[17]?.body, {
    context_items: [
      { text: "Create a technical audit PDF.", role: "brief" },
      { path: "src/service.py", role: "source" },
      {
        path: "examples/media/meeting-audio.mp3",
        role: "audio_context",
        label: "Meeting Audio",
        transcript: "00:00 Kickoff",
      },
    ],
    output_path: "context.packet.json",
    title: "Audit Context",
    intent: "Compose a target PDF with evidence.",
  });
  assert.deepEqual(calls[18]?.body, {
    context_packet_path: "context.packet.json",
    profile: "technical_audit",
    output_path: "technical-audit.pdf",
  });
  assert.deepEqual(calls[19]?.body, {
    composition_path: "technical-audit.composition.json",
    output_path: "technical-audit.coverage.json",
  });
  assert.deepEqual(calls[20]?.body, {
    input_path: "technical-audit.pdf",
    operations: [
      {
        op: "append_table",
        title: "Runtime Metrics",
        columns: ["metric", "value"],
        rows: [["latency_ms", "42"]],
        source_refs: ["ctx_002"],
      },
    ],
    output_path: "technical-audit.patch.json",
    composition_path: "technical-audit.composition.json",
    layer_manifest_path: "technical-audit.layers.json",
    reason: "Append structured evidence.",
  });
  assert.deepEqual(calls[21]?.body, {
    patch_manifest_path: "technical-audit.patch.json",
    output_path: "technical-audit.patch-preview.json",
  });
  assert.deepEqual(calls[22]?.body, {
    patch_manifest_path: "technical-audit.patch.json",
    output_path: "technical-audit-patched.pdf",
  });
  assert.deepEqual(calls[23]?.body, {
    patch_manifest_path: "technical-audit.patch.json",
    patched_path: "technical-audit-patched.pdf",
  });
  assert.deepEqual(calls[24]?.body, {
    input_path: "numbered.pdf",
    pages: "1",
    out_dir: "images",
  });
});

test("runCli exposes lite parse and local RAG commands", async () => {
  const calls: Array<{ url: string; body: unknown }> = [];

  async function invoke(args: string[]): Promise<number> {
    return runCli(args, {
      fetch: async (input, init) => {
        calls.push({ url: String(input), body: JSON.parse(String(init?.body)) });
        return jsonResponse({
          job_id: "job_cli_ai",
          status: "succeeded",
          tool: calls.at(-1)?.url.split("/v1/tools/")[1]?.split("/run")[0] ?? "unknown",
          artifacts: [],
          validation: null,
          warnings: [],
          usage: {},
          next_recommended_tools: [],
          error: null,
        });
      },
      stdout: () => undefined,
      stderr: () => undefined,
    });
  }

  assert.equal(await invoke(["parse-lite", "report.pdf"]), 0);
  assert.equal(await invoke(["pdf-to-json", "report.pdf", "-o", "report.ir.json"]), 0);
  assert.equal(await invoke(["pdf-to-markdown", "report.pdf", "-o", "report.md"]), 0);
  assert.equal(
    await invoke(["rag-ingest", "report.pdf", "--index", "report.index.json", "--max-chars", "80"]),
    0,
  );
  assert.equal(await invoke(["rag-query", "report.index.json", "--query", "What is cited?"]), 0);
  assert.equal(await invoke(["rag-search", "report.index.json", "--query", "cited evidence"]), 0);
  assert.equal(await invoke(["rag-cite-answer", "report.index.json", "--answer", "cited evidence"]), 0);
  assert.equal(
    await invoke([
      "rag-highlight-sources",
      "report.index.json",
      "--answer",
      "cited evidence",
      "-o",
      "report-highlighted.pdf",
    ]),
    0,
  );
  assert.equal(
    await invoke([
      "rag-export-report",
      "report.index.json",
      "--question",
      "What is cited?",
      "--answer",
      "cited evidence",
      "-o",
      "report-rag.pdf",
      "--top-k",
      "2",
    ]),
    0,
  );
  assert.equal(
    await invoke([
      "rag-chat",
      "report.pdf",
      "--question",
      "What is cited?",
      "--index",
      "report-chat.index.json",
      "--report-output",
      "report-chat.pdf",
      "--highlight-output",
      "report-chat-highlighted.pdf",
      "--top-k",
      "2",
    ]),
    0,
  );

  assert.deepEqual(calls.map((call) => call.url), [
    "http://127.0.0.1:7331/v1/tools/pdf.ai.parse.lite/run",
    "http://127.0.0.1:7331/v1/tools/pdf.convert.pdf_to_json/run",
    "http://127.0.0.1:7331/v1/tools/pdf.convert.pdf_to_markdown/run",
    "http://127.0.0.1:7331/v1/tools/pdf.ai.rag.ingest/run",
    "http://127.0.0.1:7331/v1/tools/pdf.ai.rag.query/run",
    "http://127.0.0.1:7331/v1/tools/pdf.ai.rag.search/run",
    "http://127.0.0.1:7331/v1/tools/pdf.ai.rag.cite_answer/run",
    "http://127.0.0.1:7331/v1/tools/pdf.ai.rag.highlight_sources/run",
    "http://127.0.0.1:7331/v1/tools/pdf.ai.rag.export_report/run",
    "http://127.0.0.1:7331/v1/tools/pdf.ai.rag.chat/run",
  ]);
  assert.deepEqual(calls[0]?.body, { input_path: "report.pdf" });
  assert.deepEqual(calls[1]?.body, {
    input_path: "report.pdf",
    output_path: "report.ir.json",
  });
  assert.deepEqual(calls[2]?.body, {
    input_path: "report.pdf",
    output_path: "report.md",
  });
  assert.deepEqual(calls[3]?.body, {
    input_path: "report.pdf",
    index_path: "report.index.json",
    max_chars: 80,
  });
  assert.deepEqual(calls[4]?.body, {
    index_path: "report.index.json",
    query: "What is cited?",
  });
  assert.deepEqual(calls[5]?.body, {
    index_path: "report.index.json",
    query: "cited evidence",
  });
  assert.deepEqual(calls[6]?.body, {
    index_path: "report.index.json",
    answer: "cited evidence",
  });
  assert.deepEqual(calls[7]?.body, {
    index_path: "report.index.json",
    answer: "cited evidence",
    output_path: "report-highlighted.pdf",
  });
  assert.deepEqual(calls[8]?.body, {
    index_path: "report.index.json",
    question: "What is cited?",
    answer: "cited evidence",
    output_path: "report-rag.pdf",
    top_k: 2,
  });
  assert.deepEqual(calls[9]?.body, {
    input_path: "report.pdf",
    question: "What is cited?",
    index_path: "report-chat.index.json",
    report_output_path: "report-chat.pdf",
    highlight_output_path: "report-chat-highlighted.pdf",
    top_k: 2,
  });
});
