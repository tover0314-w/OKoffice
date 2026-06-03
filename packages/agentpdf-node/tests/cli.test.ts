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

test("runCli exposes context ingest and packet commands", async () => {
  const calls: Array<{ url: string; body: unknown }> = [];
  const output: string[] = [];
  const invoke = (argv: string[]) =>
    runCli(argv, {
      fetch: async (input, init) => {
        calls.push({
          url: String(input),
          body: JSON.parse(String(init?.body)),
        });
        return jsonResponse({
          job_id: "job_context_cli",
          status: "succeeded",
          tool: calls.length === 1 ? "pdf.context.ingest" : "pdf.context.packet",
          artifacts: [],
          validation: null,
          warnings: [],
          usage: {},
          next_recommended_tools: [],
          error: null,
        } satisfies ToolResult);
      },
      stdout: (line) => output.push(line),
      stderr: (line) => output.push(`ERR:${line}`),
    });

  assert.equal(
    await invoke([
      "context-ingest",
      "--file",
      "src/service.ts",
      "--role",
      "code_evidence",
      "--label",
      "Service Code",
      "-o",
      "service.context-item.json",
    ]),
    0,
  );
  assert.equal(
    await invoke([
      "context-packet",
      "--item-json",
      "{\"context_item_id\":\"ctx_001\",\"type\":\"code\",\"source_ref\":\"ctx_001\",\"role\":\"code_evidence\"}",
      "-o",
      "context.packet.json",
      "--title",
      "Agent Context",
      "--intent",
      "Compose a target PDF.",
    ]),
    0,
  );

  assert.deepEqual(calls.map((call) => call.url), [
    "http://127.0.0.1:7331/v1/tools/pdf.context.ingest/run",
    "http://127.0.0.1:7331/v1/tools/pdf.context.packet/run",
  ]);
  assert.deepEqual(calls[0]?.body, {
    context_item: {
      path: "src/service.ts",
      role: "code_evidence",
      label: "Service Code",
    },
    output_path: "service.context-item.json",
  });
  assert.deepEqual(calls[1]?.body, {
    context_items: [
      {
        context_item_id: "ctx_001",
        type: "code",
        source_ref: "ctx_001",
        role: "code_evidence",
      },
    ],
    output_path: "context.packet.json",
    title: "Agent Context",
    intent: "Compose a target PDF.",
  });
  assert.equal(JSON.parse(output[0] ?? "{}").tool, "pdf.context.ingest");
  assert.equal(JSON.parse(output[1] ?? "{}").tool, "pdf.context.packet");
});

test("runCli exposes context classify command", async () => {
  const output: string[] = [];
  let postedBody: unknown;
  const code = await runCli(
    [
      "context-classify",
      "context.packet.json",
      "--profile",
      "technical_audit",
      "-o",
      "context.classification.json",
    ],
    {
      fetch: async (input, init) => {
        assert.equal(String(input), "http://127.0.0.1:7331/v1/tools/pdf.context.classify/run");
        postedBody = JSON.parse(String(init?.body));
        return jsonResponse({
          job_id: "job_context_classify_cli",
          status: "succeeded",
          tool: "pdf.context.classify",
          artifacts: [],
          validation: null,
          warnings: [],
          usage: { classification_count: 2 },
          next_recommended_tools: ["pdf.compose.from_context"],
          error: null,
        } satisfies ToolResult);
      },
      stdout: (line) => output.push(line),
      stderr: (line) => output.push(`ERR:${line}`),
    },
  );

  assert.equal(code, 0);
  assert.deepEqual(postedBody, {
    context_packet_path: "context.packet.json",
    profile: "technical_audit",
    output_path: "context.classification.json",
  });
  assert.equal(JSON.parse(output[0] ?? "{}").tool, "pdf.context.classify");
});

test("runCli exposes code snapshot and data profile commands", async () => {
  const calls: Array<{ url: string; body: unknown }> = [];
  const output: string[] = [];

  async function invoke(args: string[]): Promise<number> {
    return runCli(args, {
      fetch: async (input, init) => {
        calls.push({ url: String(input), body: JSON.parse(String(init?.body)) });
        return jsonResponse({
          job_id: "job_context_profile_cli",
          status: "succeeded",
          tool: calls.at(-1)?.url.split("/v1/tools/")[1]?.split("/run")[0] ?? "unknown",
          artifacts: [],
          validation: null,
          warnings: [],
          usage: {},
          next_recommended_tools: [],
          error: null,
        } satisfies ToolResult);
      },
      stdout: (line) => output.push(line),
      stderr: (line) => output.push(`ERR:${line}`),
    });
  }

  assert.equal(
    await invoke([
      "code-snapshot",
      "src/service.ts",
      "--line-start",
      "2",
      "--line-end",
      "8",
      "--repository-root",
      ".",
      "--include-dependencies",
      "-o",
      "service.context-item.json",
    ]),
    0,
  );
  assert.equal(
    await invoke([
      "data-profile",
      "metrics.xlsx",
      "--sheet",
      "Sheet1",
      "--max-rows",
      "50",
      "-o",
      "metrics.context-item.json",
    ]),
    0,
  );
  assert.equal(
    await invoke([
      "context-image-analyze",
      "scan.png",
      "--language",
      "eng",
      "--skip-ocr",
      "--engine",
      "tesseract",
      "--psm",
      "6",
    ]),
    0,
  );

  assert.deepEqual(calls, [
    {
      url: "http://127.0.0.1:7331/v1/tools/pdf.context.code_snapshot/run",
      body: {
        path: "src/service.ts",
        output_path: "service.context-item.json",
        line_start: 2,
        line_end: 8,
        repository_root: ".",
        include_dependencies: true,
      },
    },
    {
      url: "http://127.0.0.1:7331/v1/tools/pdf.context.data_profile/run",
      body: {
        path: "metrics.xlsx",
        output_path: "metrics.context-item.json",
        sheet: "Sheet1",
        max_rows: 50,
      },
    },
    {
      url: "http://127.0.0.1:7331/v1/tools/pdf.context.image_analyze/run",
      body: {
        input_path: "scan.png",
        languages: ["eng"],
        run_ocr: false,
        engine: "tesseract",
        psm: 6,
      },
    },
  ]);
  assert.equal(JSON.parse(output[0] ?? "{}").tool, "pdf.context.code_snapshot");
  assert.equal(JSON.parse(output[1] ?? "{}").tool, "pdf.context.data_profile");
  assert.equal(JSON.parse(output[2] ?? "{}").tool, "pdf.context.image_analyze");
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

test("runCli exposes compose plan and render IR commands", async () => {
  const calls: Array<{ url: string; body: unknown }> = [];

  async function invoke(args: string[]): Promise<number> {
    return runCli(args, {
      fetch: async (input, init) => {
        calls.push({ url: String(input), body: JSON.parse(String(init?.body)) });
        return jsonResponse({
          job_id: "job_compose_ir_cli",
          status: "succeeded",
          tool: calls.length === 1 ? "pdf.compose.plan" : "pdf.compose.render_ir",
          artifacts: [],
          validation: null,
          warnings: [],
          usage: {},
          next_recommended_tools: [],
          error: null,
        } satisfies ToolResult);
      },
      stdout: () => undefined,
      stderr: () => undefined,
    });
  }

  assert.equal(
    await invoke([
      "compose-plan",
      "context.packet.json",
      "--profile",
      "technical_audit",
      "-o",
      "composition.plan.json",
      "--title",
      "Technical Audit Plan",
    ]),
    0,
  );
  assert.equal(
    await invoke(["compose-render-ir", "composition.plan.json", "-o", "technical-audit.pdf"]),
    0,
  );

  assert.deepEqual(calls, [
    {
      url: "http://127.0.0.1:7331/v1/tools/pdf.compose.plan/run",
      body: {
        context_packet_path: "context.packet.json",
        profile: "technical_audit",
        output_path: "composition.plan.json",
        title: "Technical Audit Plan",
      },
    },
    {
      url: "http://127.0.0.1:7331/v1/tools/pdf.compose.render_ir/run",
      body: {
        composition_path: "composition.plan.json",
        output_path: "technical-audit.pdf",
      },
    },
  ]);
});

test("runCli exposes compose block commands", async () => {
  const calls: Array<{ url: string; body: unknown }> = [];

  async function invoke(args: string[]): Promise<number> {
    return runCli(args, {
      fetch: async (input, init) => {
        calls.push({ url: String(input), body: JSON.parse(String(init?.body)) });
        const url = String(input);
        const tool = url.includes("add_table")
          ? "pdf.compose.add_table"
          : url.includes("add_figure")
            ? "pdf.compose.add_figure"
            : url.includes("add_appendix")
              ? "pdf.compose.add_appendix"
              : url.includes("add_citation")
                ? "pdf.compose.add_citation"
                : url.includes("add_media_reference")
                  ? "pdf.compose.add_media_reference"
                  : url.includes("add_slide")
                    ? "pdf.compose.add_slide"
                    : "pdf.compose.add_code_block";
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

  assert.equal(
    await invoke([
      "compose-add-code-block",
      "base.pdf",
      "--title",
      "Risk Function",
      "--code",
      "def risky_total(items):\n    return sum(items)\n",
      "--language",
      "python",
      "--source-ref",
      "ctx_code",
      "--block-id",
      "blk_code",
      "--target-slot",
      "code_review",
      "-o",
      "code.pdf",
    ]),
    0,
  );
  assert.equal(
    await invoke([
      "compose-add-table",
      "base.pdf",
      "--title",
      "Runtime Metrics",
      "--columns",
      "metric,value",
      "--row",
      "latency_ms,42",
      "--source-ref",
      "ctx_metrics",
      "-o",
      "table.pdf",
    ]),
    0,
  );
  assert.equal(
    await invoke([
      "compose-add-figure",
      "base.pdf",
      "--title",
      "Architecture Figure",
      "--image",
      "diagram.png",
      "--caption",
      "Local visual evidence.",
      "--source-ref",
      "ctx_image",
      "-o",
      "figure.pdf",
    ]),
    0,
  );
  assert.equal(
    await invoke([
      "compose-add-appendix",
      "base.pdf",
      "--title",
      "Source Appendix",
      "--markdown",
      "## Sources\n\n- ctx_code",
      "--source-ref",
      "ctx_code",
      "-o",
      "appendix.pdf",
    ]),
    0,
  );
  assert.equal(
    await invoke([
      "compose-add-citation",
      "base.pdf",
      "--title",
      "Source Citation",
      "--quote",
      "AgentPDF keeps citation source refs auditable.",
      "--source",
      "https://example.com/research",
      "--page",
      "section 2",
      "--source-ref",
      "ctx_web",
      "--block-id",
      "blk_citation",
      "--target-slot",
      "citations",
      "-o",
      "citation.pdf",
    ]),
    0,
  );
  assert.equal(
    await invoke([
      "compose-add-media-reference",
      "base.pdf",
      "--title",
      "Meeting Media",
      "--media",
      "clip.mp4",
      "--media-kind",
      "video",
      "--transcript-excerpt",
      "00:00 visual evidence frame.",
      "--duration-seconds",
      "12.75",
      "--keyframe-count",
      "1",
      "--source-ref",
      "ctx_media",
      "--block-id",
      "blk_media",
      "--target-slot",
      "media_evidence",
      "-o",
      "media.pdf",
    ]),
    0,
  );
  assert.equal(
    await invoke([
      "compose-add-slide",
      "base.pdf",
      "--title",
      "Review Slide",
      "--subtitle",
      "Decision evidence",
      "--body",
      "First slide bullet.",
      "--body",
      "Second slide bullet.",
      "--code",
      "score = 42",
      "--source-ref",
      "ctx_slide",
      "--block-id",
      "blk_slide",
      "--target-slot",
      "evidence_slide",
      "-o",
      "slide.pdf",
    ]),
    0,
  );

  assert.deepEqual(calls, [
    {
      url: "http://127.0.0.1:7331/v1/tools/pdf.compose.add_code_block/run",
      body: {
        input_path: "base.pdf",
        output_path: "code.pdf",
        title: "Risk Function",
        code: "def risky_total(items):\n    return sum(items)\n",
        language: "python",
        source_refs: ["ctx_code"],
        block_id: "blk_code",
        target_slot: "code_review",
      },
    },
    {
      url: "http://127.0.0.1:7331/v1/tools/pdf.compose.add_table/run",
      body: {
        input_path: "base.pdf",
        output_path: "table.pdf",
        title: "Runtime Metrics",
        columns: ["metric", "value"],
        rows: [["latency_ms", "42"]],
        source_refs: ["ctx_metrics"],
      },
    },
    {
      url: "http://127.0.0.1:7331/v1/tools/pdf.compose.add_figure/run",
      body: {
        input_path: "base.pdf",
        output_path: "figure.pdf",
        title: "Architecture Figure",
        image_path: "diagram.png",
        caption: "Local visual evidence.",
        source_refs: ["ctx_image"],
      },
    },
    {
      url: "http://127.0.0.1:7331/v1/tools/pdf.compose.add_appendix/run",
      body: {
        input_path: "base.pdf",
        output_path: "appendix.pdf",
        title: "Source Appendix",
        markdown: "## Sources\n\n- ctx_code",
        source_refs: ["ctx_code"],
      },
    },
    {
      url: "http://127.0.0.1:7331/v1/tools/pdf.compose.add_citation/run",
      body: {
        input_path: "base.pdf",
        output_path: "citation.pdf",
        title: "Source Citation",
        quote: "AgentPDF keeps citation source refs auditable.",
        source: "https://example.com/research",
        page: "section 2",
        source_refs: ["ctx_web"],
        block_id: "blk_citation",
        target_slot: "citations",
      },
    },
    {
      url: "http://127.0.0.1:7331/v1/tools/pdf.compose.add_media_reference/run",
      body: {
        input_path: "base.pdf",
        output_path: "media.pdf",
        title: "Meeting Media",
        media_path: "clip.mp4",
        media_kind: "video",
        transcript_excerpt: "00:00 visual evidence frame.",
        duration_seconds: 12.75,
        keyframe_count: 1,
        source_refs: ["ctx_media"],
        block_id: "blk_media",
        target_slot: "media_evidence",
      },
    },
    {
      url: "http://127.0.0.1:7331/v1/tools/pdf.compose.add_slide/run",
      body: {
        input_path: "base.pdf",
        output_path: "slide.pdf",
        title: "Review Slide",
        subtitle: "Decision evidence",
        body: ["First slide bullet.", "Second slide bullet."],
        code: "score = 42",
        source_refs: ["ctx_slide"],
        block_id: "blk_slide",
        target_slot: "evidence_slide",
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
        "--context-classification-output",
        "board-audit.context-classification.json",
        "--context-report-output",
        "board-audit.context-report.pdf",
        "--context-report-json-output",
        "board-audit.context-report.json",
        "--bundle-output",
        "board-audit.agentpdf-bundle.zip",
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
        "--renderer",
        "html",
        "--html-output",
        "board-audit.html",
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
        context_classification_output_path: "board-audit.context-classification.json",
        context_report_output_path: "board-audit.context-report.pdf",
        context_report_json_output_path: "board-audit.context-report.json",
        bundle_output_path: "board-audit.agentpdf-bundle.zip",
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
        renderer: "html",
        html_output_path: "board-audit.html",
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

test("runCli exposes authoring workflow commands", async () => {
  const tempDir = await mkdtemp(join(tmpdir(), "agentpdf-node-authoring-"));
  const briefPath = join(tempDir, "brief.json");
  const evidencePath = join(tempDir, "evidence.json");
  const calls: Array<{ url: string; body: unknown }> = [];

  await writeFile(
    briefPath,
    JSON.stringify({
      topic: "Independent developers going global",
      page_count: 4,
      deliverable: "deck",
    }),
  );
  await writeFile(
    evidencePath,
    JSON.stringify([
      {
        id: "ev_market",
        claim: "Mobile monetization remains strong.",
        evidence: "Revenue growth continues while downloads flatten.",
        source_title: "State of Mobile 2026",
      },
    ]),
  );

  async function invoke(args: string[]): Promise<number> {
    return runCli(args, {
      fetch: async (input, init) => {
        calls.push({ url: String(input), body: JSON.parse(String(init?.body)) });
        return jsonResponse({
          job_id: "job_cli_authoring",
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
    assert.equal(await invoke(["authoring-plan", "--brief", briefPath]), 0);
    assert.equal(
      await invoke([
        "workflow-research-deck",
        "--brief",
        briefPath,
        "--evidence-cards",
        evidencePath,
        "--html-output",
        "deck.html",
        "--pdf-output",
        "deck.pdf",
        "--artifact-dir",
        "workflow-artifacts",
        "--execute",
      ]),
      0,
    );
  } finally {
    await rm(tempDir, { recursive: true, force: true });
  }

  assert.deepEqual(calls.map((call) => call.url), [
    "http://127.0.0.1:7331/v1/tools/pdf.authoring.plan/run",
    "http://127.0.0.1:7331/v1/tools/pdf.workflow.research_deck/run",
  ]);
  assert.deepEqual(calls[0]?.body, {
    brief: {
      topic: "Independent developers going global",
      page_count: 4,
      deliverable: "deck",
    },
  });
  assert.deepEqual(calls[1]?.body, {
    brief: {
      topic: "Independent developers going global",
      page_count: 4,
      deliverable: "deck",
    },
    evidence_cards: [
      {
        id: "ev_market",
        claim: "Mobile monetization remains strong.",
        evidence: "Revenue growth continues while downloads flatten.",
        source_title: "State of Mobile 2026",
      },
    ],
    html_output_path: "deck.html",
    pdf_output_path: "deck.pdf",
    artifact_dir: "workflow-artifacts",
    execute: true,
  });
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

test("runCli exposes artifact manifest command", async () => {
  const output: string[] = [];
  let postedBody: unknown;

  const code = await runCli(
    [
      "artifact-manifest",
      "--file",
      "report.pdf",
      "--file",
      "report.composition.json",
      "--file",
      "report.coverage.json",
      "-o",
      "report.artifacts.json",
      "--title",
      "Report Artifact Manifest",
      "--metadata",
      "agent=codex",
    ],
    {
      fetch: async (input, init) => {
        assert.equal(String(input), "http://127.0.0.1:7331/v1/tools/pdf.artifacts.manifest/run");
        postedBody = JSON.parse(String(init?.body));
        return jsonResponse({
          job_id: "job_artifact_manifest_cli",
          status: "succeeded",
          tool: "pdf.artifacts.manifest",
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
  assert.equal(JSON.parse(output[0] ?? "{}").tool, "pdf.artifacts.manifest");
  assert.deepEqual(postedBody, {
    artifact_paths: ["report.pdf", "report.composition.json", "report.coverage.json"],
    output_path: "report.artifacts.json",
    title: "Report Artifact Manifest",
    metadata: { agent: "codex" },
  });
});

test("runCli exposes artifact graph command", async () => {
  const output: string[] = [];
  let postedBody: unknown;

  const code = await runCli(
    [
      "artifact-graph",
      "--manifest",
      "report.artifacts.json",
      "--file",
      "report.pdf",
      "--file",
      "report.composition.json",
      "-o",
      "report.artifact-graph.json",
      "--title",
      "Report Artifact Graph",
    ],
    {
      fetch: async (input, init) => {
        assert.equal(String(input), "http://127.0.0.1:7331/v1/tools/pdf.artifacts.graph/run");
        postedBody = JSON.parse(String(init?.body));
        return jsonResponse({
          job_id: "job_artifact_graph_cli",
          status: "succeeded",
          tool: "pdf.artifacts.graph",
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
  assert.equal(JSON.parse(output[0] ?? "{}").tool, "pdf.artifacts.graph");
  assert.deepEqual(postedBody, {
    artifact_manifest_path: "report.artifacts.json",
    artifact_paths: ["report.pdf", "report.composition.json"],
    output_path: "report.artifact-graph.json",
    title: "Report Artifact Graph",
  });
});

test("runCli exposes artifact source map command", async () => {
  const output: string[] = [];
  let postedBody: unknown;

  const code = await runCli(
    [
      "artifact-source-map",
      "--composition",
      "report.composition.json",
      "--context-packet",
      "context.packet.json",
      "--manifest",
      "report.artifacts.json",
      "-o",
      "report.artifact-source-map.json",
      "--title",
      "Report Artifact Source Map",
    ],
    {
      fetch: async (input, init) => {
        assert.equal(String(input), "http://127.0.0.1:7331/v1/tools/pdf.artifacts.source_map/run");
        postedBody = JSON.parse(String(init?.body));
        return jsonResponse({
          job_id: "job_artifact_source_map_cli",
          status: "succeeded",
          tool: "pdf.artifacts.source_map",
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
  assert.equal(JSON.parse(output[0] ?? "{}").tool, "pdf.artifacts.source_map");
  assert.deepEqual(postedBody, {
    composition_path: "report.composition.json",
    context_packet_path: "context.packet.json",
    artifact_manifest_path: "report.artifacts.json",
    output_path: "report.artifact-source-map.json",
    title: "Report Artifact Source Map",
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

test("runCli exposes Codex agent setup command", async () => {
  const output: string[] = [];
  let postedBody: unknown;

  const code = await runCli(
    [
      "agent-setup-codex",
      "-o",
      "codex.mcp.json",
      "--safe-root",
      ".",
      "--command",
      "python",
      "--arg-prefix",
      "-m",
      "--arg-prefix",
      "agentpdf.cli",
      "--server-name",
      "agentpdf",
    ],
    {
      fetch: async (input, init) => {
        assert.equal(String(input), "http://127.0.0.1:7331/v1/tools/agent.setup.codex/run");
        postedBody = JSON.parse(String(init?.body));
        return jsonResponse({
          job_id: "job_codex_setup",
          status: "succeeded",
          tool: "agent.setup.codex",
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
  assert.equal(JSON.parse(output[0] ?? "{}").tool, "agent.setup.codex");
  assert.deepEqual(postedBody, {
    output_path: "codex.mcp.json",
    safe_root: ".",
    command: "python",
    args_prefix: ["-m", "agentpdf.cli"],
    server_name: "agentpdf",
  });
});

test("runCli exposes Kilo Code and OpenClaw agent setup commands", async () => {
  const output: string[] = [];
  const calls: Array<{ url: string; body: unknown }> = [];

  async function invoke(args: string[]): Promise<number> {
    return runCli(args, {
      fetch: async (input, init) => {
        const body = JSON.parse(String(init?.body));
        calls.push({ url: String(input), body });
        return jsonResponse({
          job_id: "job_agent_setup",
          status: "succeeded",
          tool: String(input).includes("kilo_code")
            ? "agent.setup.kilo_code"
            : "agent.setup.openclaw",
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
    });
  }

  assert.equal(
    await invoke([
      "agent-setup-kilo-code",
      "-o",
      "kilo-code.mcp.json",
      "--safe-root",
      ".",
      "--command",
      "python",
      "--arg-prefix",
      "-m",
      "--arg-prefix",
      "agentpdf.cli",
    ]),
    0,
  );
  assert.equal(
    await invoke([
      "agent-setup-openclaw",
      "-o",
      "openclaw.mcp.json",
      "--safe-root",
      ".",
      "--server-name",
      "agentpdf",
    ]),
    0,
  );

  assert.deepEqual(calls.map((call) => call.url), [
    "http://127.0.0.1:7331/v1/tools/agent.setup.kilo_code/run",
    "http://127.0.0.1:7331/v1/tools/agent.setup.openclaw/run",
  ]);
  assert.deepEqual(calls[0]?.body, {
    output_path: "kilo-code.mcp.json",
    safe_root: ".",
    command: "python",
    args_prefix: ["-m", "agentpdf.cli"],
  });
  assert.deepEqual(calls[1]?.body, {
    output_path: "openclaw.mcp.json",
    safe_root: ".",
    server_name: "agentpdf",
  });
  assert.equal(JSON.parse(output[0] ?? "{}").tool, "agent.setup.kilo_code");
  assert.equal(JSON.parse(output[1] ?? "{}").tool, "agent.setup.openclaw");
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
      "--renderer",
      "html",
      "--html-output",
      "technical-audit.html",
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
      "evidence-map-sources",
      "technical-audit.composition.json",
      "--context-packet",
      "context.packet.json",
      "-o",
      "technical-audit.source-map.json",
    ]),
    0,
  );
  assert.equal(
    await invoke([
      "evidence-cite-claims",
      "--claims",
      "[{\"claim_id\":\"claim_cli\",\"text\":\"Runtime metrics include latency evidence.\",\"source_refs\":[\"ctx_002\"]}]",
      "--source-map",
      "technical-audit.source-map.json",
      "-o",
      "technical-audit.citations.json",
    ]),
    0,
  );
  assert.equal(
    await invoke([
      "evidence-context-packet-report",
      "context.packet.json",
      "-o",
      "context-report.pdf",
      "--report-output",
      "context-report.json",
      "--title",
      "Context Report",
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
  assert.equal(await invoke(["inspect-health", "cover.pdf"]), 0);

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
    "http://127.0.0.1:7331/v1/tools/pdf.evidence.map_sources/run",
    "http://127.0.0.1:7331/v1/tools/pdf.evidence.cite_claims/run",
    "http://127.0.0.1:7331/v1/tools/pdf.evidence.context_packet_report/run",
    "http://127.0.0.1:7331/v1/tools/pdf.patch.plan/run",
    "http://127.0.0.1:7331/v1/tools/pdf.patch.preview/run",
    "http://127.0.0.1:7331/v1/tools/pdf.patch.apply/run",
    "http://127.0.0.1:7331/v1/tools/pdf.patch.verify/run",
    "http://127.0.0.1:7331/v1/tools/pdf.convert.extract_images/run",
    "http://127.0.0.1:7331/v1/tools/pdf.inspect.health/run",
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
    renderer: "html",
    html_output_path: "technical-audit.html",
  });
  assert.deepEqual(calls[19]?.body, {
    composition_path: "technical-audit.composition.json",
    output_path: "technical-audit.coverage.json",
  });
  assert.deepEqual(calls[20]?.body, {
    composition_path: "technical-audit.composition.json",
    context_packet_path: "context.packet.json",
    output_path: "technical-audit.source-map.json",
  });
  assert.deepEqual(calls[21]?.body, {
    claims: [
      {
        claim_id: "claim_cli",
        text: "Runtime metrics include latency evidence.",
        source_refs: ["ctx_002"],
      },
    ],
    source_map_path: "technical-audit.source-map.json",
    output_path: "technical-audit.citations.json",
  });
  assert.deepEqual(calls[22]?.body, {
    context_packet_path: "context.packet.json",
    output_path: "context-report.pdf",
    report_output_path: "context-report.json",
    title: "Context Report",
  });
  assert.deepEqual(calls[23]?.body, {
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
  assert.deepEqual(calls[24]?.body, {
    patch_manifest_path: "technical-audit.patch.json",
    output_path: "technical-audit.patch-preview.json",
  });
  assert.deepEqual(calls[25]?.body, {
    patch_manifest_path: "technical-audit.patch.json",
    output_path: "technical-audit-patched.pdf",
  });
  assert.deepEqual(calls[26]?.body, {
    patch_manifest_path: "technical-audit.patch.json",
    patched_path: "technical-audit-patched.pdf",
  });
  assert.deepEqual(calls[27]?.body, {
    input_path: "numbered.pdf",
    pages: "1",
    out_dir: "images",
  });
});

test("runCli exposes optimization, font, and edit commands", async () => {
  const calls: Array<{ url: string; body: unknown }> = [];

  async function invoke(args: string[]): Promise<number> {
    return runCli(args, {
      fetch: async (input, init) => {
        calls.push({ url: String(input), body: JSON.parse(String(init?.body)) });
        return jsonResponse({
          job_id: "job_cli_pdf_edit",
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

  assert.equal(await invoke(["remove-unused-objects", "report.pdf", "-o", "report.optimized.pdf"]), 0);
  assert.equal(await invoke(["validate-pdfa", "report.pdf"]), 0);
  assert.equal(await invoke(["extract-fonts", "report.pdf", "--pages", "1"]), 0);
  assert.equal(
    await invoke([
      "add-shape",
      "report.pdf",
      "-o",
      "report.shape.pdf",
      "--shape",
      "rectangle",
      "--page",
      "1",
      "--x",
      "72",
      "--y",
      "640",
      "--width",
      "120",
      "--height",
      "40",
      "--stroke-color",
      "#2563eb",
    ]),
    0,
  );
  assert.equal(
    await invoke(["underline", "report.shape.pdf", "-o", "report.underline.pdf", "--page", "1", "--bbox", "72,640,180,656"]),
    0,
  );
  assert.equal(
    await invoke(["strikeout", "report.underline.pdf", "-o", "report.strikeout.pdf", "--page", "1", "--bbox", "72,640,180,656"]),
    0,
  );
  assert.equal(
    await invoke(["freehand-draw", "report.strikeout.pdf", "-o", "report.drawn.pdf", "--page", "1", "--points", "[[72,680],[120,700]]"]),
    0,
  );
  assert.equal(
    await invoke(["resize-pages", "report.drawn.pdf", "-o", "report.resized.pdf", "--width", "300", "--height", "400"]),
    0,
  );
  assert.equal(await invoke(["add-margin", "report.resized.pdf", "-o", "report.margin.pdf", "--margin", "36"]), 0);
  assert.equal(await invoke(["underlay", "report.margin.pdf", "-o", "report.underlay.pdf", "--text", "DRAFT"]), 0);

  assert.deepEqual(calls.map((call) => call.url), [
    "http://127.0.0.1:7331/v1/tools/pdf.optimize.remove_unused_objects/run",
    "http://127.0.0.1:7331/v1/tools/pdf.optimize.validate_pdfa/run",
    "http://127.0.0.1:7331/v1/tools/pdf.convert.extract_fonts/run",
    "http://127.0.0.1:7331/v1/tools/pdf.edit.add_shape/run",
    "http://127.0.0.1:7331/v1/tools/pdf.edit.underline/run",
    "http://127.0.0.1:7331/v1/tools/pdf.edit.strikeout/run",
    "http://127.0.0.1:7331/v1/tools/pdf.edit.freehand_draw/run",
    "http://127.0.0.1:7331/v1/tools/pdf.edit.resize_pages/run",
    "http://127.0.0.1:7331/v1/tools/pdf.edit.add_margin/run",
    "http://127.0.0.1:7331/v1/tools/pdf.edit.underlay/run",
  ]);
  assert.deepEqual(calls[0]?.body, {
    input_path: "report.pdf",
    output_path: "report.optimized.pdf",
  });
  assert.deepEqual(calls[1]?.body, { input_path: "report.pdf" });
  assert.deepEqual(calls[2]?.body, { input_path: "report.pdf", pages: "1" });
  assert.deepEqual(calls[4]?.body, {
    input_path: "report.shape.pdf",
    output_path: "report.underline.pdf",
    page: 1,
    bbox: [72, 640, 180, 656],
  });
  assert.deepEqual(calls[9]?.body, {
    input_path: "report.margin.pdf",
    output_path: "report.underlay.pdf",
    text: "DRAFT",
  });
});

test("runCli exposes compare and semantic parse commands", async () => {
  const calls: Array<{ url: string; body: unknown }> = [];

  async function invoke(args: string[]): Promise<number> {
    return runCli(args, {
      fetch: async (input, init) => {
        calls.push({ url: String(input), body: JSON.parse(String(init?.body)) });
        return jsonResponse({
          job_id: "job_cli_compare_parse",
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

  assert.equal(await invoke(["semantic-diff", "before.pdf", "after.pdf", "--pages", "1"]), 0);
  assert.equal(
    await invoke(["version-report", "before.pdf", "after.pdf", "-o", "version-report.md"]),
    0,
  );
  assert.equal(await invoke(["compare-visual-diff", "before.pdf", "after.pdf", "--pages", "1"]), 0);
  assert.equal(
    await invoke([
      "visual-diff",
      "before.pdf",
      "after.pdf",
      "--pages",
      "1",
      "--max-difference-ratio",
      "0",
    ]),
    0,
  );
  assert.equal(await invoke(["parse-figures", "report.pdf", "--pages", "1"]), 0);
  assert.equal(await invoke(["parse-formulas", "report.pdf"]), 0);
  assert.equal(await invoke(["parse-charts", "report.pdf"]), 0);
  assert.equal(await invoke(["parse-references", "report.pdf"]), 0);

  assert.deepEqual(calls.map((call) => call.url), [
    "http://127.0.0.1:7331/v1/tools/pdf.compare.semantic_diff/run",
    "http://127.0.0.1:7331/v1/tools/pdf.compare.version_report/run",
    "http://127.0.0.1:7331/v1/tools/pdf.compare.visual_diff/run",
    "http://127.0.0.1:7331/v1/tools/pdf.validation.visual_diff/run",
    "http://127.0.0.1:7331/v1/tools/pdf.ai.parse.figures/run",
    "http://127.0.0.1:7331/v1/tools/pdf.ai.parse.formulas/run",
    "http://127.0.0.1:7331/v1/tools/pdf.ai.parse.charts/run",
    "http://127.0.0.1:7331/v1/tools/pdf.ai.parse.references/run",
  ]);
  assert.deepEqual(calls[0]?.body, {
    before_path: "before.pdf",
    after_path: "after.pdf",
    pages: "1",
  });
  assert.deepEqual(calls[1]?.body, {
    before_path: "before.pdf",
    after_path: "after.pdf",
    output_path: "version-report.md",
  });
  assert.deepEqual(calls[2]?.body, {
    before_path: "before.pdf",
    after_path: "after.pdf",
    pages: "1",
  });
  assert.deepEqual(calls[3]?.body, {
    before_path: "before.pdf",
    after_path: "after.pdf",
    pages: "1",
    max_difference_ratio: 0,
  });
  assert.deepEqual(calls[4]?.body, {
    input_path: "report.pdf",
    pages: "1",
  });
  assert.deepEqual(calls[7]?.body, {
    input_path: "report.pdf",
  });
});

test("runCli exposes forms and OCR commands", async () => {
  const calls: Array<{ url: string; body: unknown }> = [];

  async function invoke(args: string[]): Promise<number> {
    return runCli(args, {
      fetch: async (input, init) => {
        calls.push({ url: String(input), body: JSON.parse(String(init?.body)) });
        return jsonResponse({
          job_id: "job_cli_forms_ocr",
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

  assert.equal(
    await invoke([
      "forms-create",
      "-o",
      "form.pdf",
      "--field",
      '{"name":"name","label":"Name","required":true}',
    ]),
    0,
  );
  assert.equal(
    await invoke(["forms-import-data", "form.pdf", "--data", '{"name":"Ada"}', "-o", "filled.pdf"]),
    0,
  );
  assert.equal(await invoke(["forms-validate", "filled.pdf", "--required-field", "name"]), 0);
  assert.equal(await invoke(["ocr", "scan.png", "--language", "eng", "--psm", "6"]), 0);
  assert.equal(
    await invoke([
      "ocr-searchable-pdf",
      "scan.pdf",
      "-o",
      "searchable.pdf",
      "--pages",
      "1",
      "--language",
      "eng",
      "--dpi",
      "250",
    ]),
    0,
  );
  assert.equal(await invoke(["ocr-scan-to-pdf", "scan.png", "-o", "scan.pdf"]), 0);
  assert.equal(await invoke(["ocr-despeckle", "scan.pdf", "-o", "despeckled.pdf"]), 0);
  assert.equal(await invoke(["ocr-remove-existing", "scan.pdf", "-o", "no-ocr.pdf"]), 0);
  assert.equal(
    await invoke([
      "ocr-multilingual",
      "scan.pdf",
      "-o",
      "multi-ocr.pdf",
      "--language",
      "eng",
      "--language",
      "chi_sim",
    ]),
    0,
  );

  assert.deepEqual(calls.map((call) => call.url), [
    "http://127.0.0.1:7331/v1/tools/pdf.forms.create/run",
    "http://127.0.0.1:7331/v1/tools/pdf.forms.import_data/run",
    "http://127.0.0.1:7331/v1/tools/pdf.forms.validate/run",
    "http://127.0.0.1:7331/v1/tools/pdf.ocr_scan.ocr/run",
    "http://127.0.0.1:7331/v1/tools/pdf.ocr_scan.searchable_pdf/run",
    "http://127.0.0.1:7331/v1/tools/pdf.ocr_scan.scan_to_pdf/run",
    "http://127.0.0.1:7331/v1/tools/pdf.ocr_scan.despeckle/run",
    "http://127.0.0.1:7331/v1/tools/pdf.ocr_scan.remove_existing_ocr/run",
    "http://127.0.0.1:7331/v1/tools/pdf.ocr_scan.multilingual_ocr/run",
  ]);
  assert.deepEqual(calls[0]?.body, {
    output_path: "form.pdf",
    fields: [{ name: "name", label: "Name", required: true }],
  });
  assert.deepEqual(calls[2]?.body, {
    input_path: "filled.pdf",
    required_fields: ["name"],
  });
  assert.deepEqual(calls[3]?.body, {
    input_path: "scan.png",
    languages: ["eng"],
    psm: 6,
  });
  assert.deepEqual(calls[4]?.body, {
    input_path: "scan.pdf",
    output_path: "searchable.pdf",
    pages: "1",
    languages: ["eng"],
    dpi: 250,
  });
  assert.deepEqual(calls[5]?.body, {
    image_paths: ["scan.png"],
    output_path: "scan.pdf",
  });
  assert.deepEqual(calls[8]?.body, {
    input_path: "scan.pdf",
    output_path: "multi-ocr.pdf",
    languages: ["eng", "chi_sim"],
  });
});

test("runCli exposes conversion, PDF/A, and security commands", async () => {
  const calls: Array<{ url: string; body: unknown }> = [];

  async function invoke(args: string[]): Promise<number> {
    return runCli(args, {
      fetch: async (input, init) => {
        calls.push({ url: String(input), body: JSON.parse(String(init?.body)) });
        return jsonResponse({
          job_id: "job_cli_conversion_security",
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

  assert.equal(await invoke(["subset-fonts", "report.pdf", "-o", "report.subset.pdf"]), 0);
  assert.equal(await invoke(["to-pdfa", "report.pdf", "-o", "report.pdfa.pdf", "--profile", "PDF/A-2b"]), 0);
  assert.equal(await invoke(["html-to-pdf", "page.html", "-o", "page.pdf"]), 0);
  assert.equal(await invoke(["render-html-package", "page.html-manifest.json", "-o", "page.pdf"]), 0);
  assert.equal(
    await invoke([
      "url-to-pdf",
      "https://example.com",
      "-o",
      "url.pdf",
      "--allow-private-hosts",
      "--allow-file-urls",
    ]),
    0,
  );
  assert.equal(await invoke(["docx-to-pdf", "report.docx", "-o", "report.pdf"]), 0);
  assert.equal(await invoke(["pptx-to-pdf", "deck.pptx", "-o", "deck.pdf"]), 0);
  assert.equal(await invoke(["xlsx-to-pdf", "metrics.xlsx", "-o", "metrics.pdf"]), 0);
  assert.equal(await invoke(["pdf-to-html", "report.pdf", "-o", "report.html", "--pages", "1"]), 0);
  assert.equal(await invoke(["pdf-to-docx", "report.pdf", "-o", "report.docx"]), 0);
  assert.equal(await invoke(["pdf-to-pptx", "report.pdf", "-o", "report.pptx"]), 0);
  assert.equal(await invoke(["pdf-to-xlsx", "report.pdf", "-o", "report.xlsx"]), 0);
  assert.equal(
    await invoke([
      "security-protect",
      "report.pdf",
      "-o",
      "protected.pdf",
      "--password",
      "open",
      "--owner-password",
      "owner",
    ]),
    0,
  );
  assert.equal(
    await invoke(["security-encrypt", "report.pdf", "-o", "encrypted.pdf", "--password", "open"]),
    0,
  );
  assert.equal(
    await invoke(["security-unlock-authorized", "protected.pdf", "-o", "unlocked.pdf", "--password", "open"]),
    0,
  );
  assert.equal(
    await invoke(["security-decrypt-authorized", "encrypted.pdf", "-o", "decrypted.pdf", "--password", "open"]),
    0,
  );
  assert.equal(
    await invoke(["security-sign", "report.pdf", "-o", "signed.pdf", "--secret", "local-secret"]),
    0,
  );
  assert.equal(
    await invoke([
      "security-verify-signature",
      "signed.pdf",
      "--signature",
      "signed.pdf.signature.json",
      "--secret",
      "local-secret",
    ]),
    0,
  );
  assert.equal(await invoke(["security-malware-scan", "report.pdf"]), 0);
  assert.equal(await invoke(["security-sanitize", "report.pdf", "-o", "sanitized.pdf"]), 0);
  assert.equal(
    await invoke([
      "security-redact",
      "report.pdf",
      "-o",
      "redacted.pdf",
      "--region",
      '{"page":1,"bbox":[60,700,280,760],"label":"secret"}',
    ]),
    0,
  );
  assert.equal(
    await invoke(["security-verify-redaction", "redacted.pdf", "--search-term", "SECRET-CODE-123"]),
    0,
  );
  assert.equal(await invoke(["redaction-check", "redacted.pdf", "--search-term", "SECRET-CODE-123"]), 0);

  assert.deepEqual(calls.map((call) => call.url), [
    "http://127.0.0.1:7331/v1/tools/pdf.optimize.subset_fonts/run",
    "http://127.0.0.1:7331/v1/tools/pdf.optimize.to_pdfa/run",
    "http://127.0.0.1:7331/v1/tools/pdf.convert.html_to_pdf/run",
    "http://127.0.0.1:7331/v1/tools/pdf.render.html_package/run",
    "http://127.0.0.1:7331/v1/tools/pdf.convert.url_to_pdf/run",
    "http://127.0.0.1:7331/v1/tools/pdf.convert.docx_to_pdf/run",
    "http://127.0.0.1:7331/v1/tools/pdf.convert.pptx_to_pdf/run",
    "http://127.0.0.1:7331/v1/tools/pdf.convert.xlsx_to_pdf/run",
    "http://127.0.0.1:7331/v1/tools/pdf.convert.pdf_to_html/run",
    "http://127.0.0.1:7331/v1/tools/pdf.convert.pdf_to_docx/run",
    "http://127.0.0.1:7331/v1/tools/pdf.convert.pdf_to_pptx/run",
    "http://127.0.0.1:7331/v1/tools/pdf.convert.pdf_to_xlsx/run",
    "http://127.0.0.1:7331/v1/tools/pdf.security.protect/run",
    "http://127.0.0.1:7331/v1/tools/pdf.security.encrypt/run",
    "http://127.0.0.1:7331/v1/tools/pdf.security.unlock_authorized/run",
    "http://127.0.0.1:7331/v1/tools/pdf.security.decrypt_authorized/run",
    "http://127.0.0.1:7331/v1/tools/pdf.security.sign/run",
    "http://127.0.0.1:7331/v1/tools/pdf.security.verify_signature/run",
    "http://127.0.0.1:7331/v1/tools/pdf.security.malware_scan/run",
    "http://127.0.0.1:7331/v1/tools/pdf.security.sanitize/run",
    "http://127.0.0.1:7331/v1/tools/pdf.security.redact/run",
    "http://127.0.0.1:7331/v1/tools/pdf.security.verify_redaction/run",
    "http://127.0.0.1:7331/v1/tools/pdf.validation.redaction_check/run",
  ]);
  assert.deepEqual(calls[1]?.body, {
    input_path: "report.pdf",
    output_path: "report.pdfa.pdf",
    profile: "PDF/A-2b",
  });
  assert.deepEqual(calls[3]?.body, {
    package_path: "page.html-manifest.json",
    output_path: "page.pdf",
  });
  assert.deepEqual(calls[4]?.body, {
    url: "https://example.com",
    output_path: "url.pdf",
    allow_private_hosts: true,
    allow_file_urls: true,
  });
  assert.deepEqual(calls[8]?.body, {
    input_path: "report.pdf",
    output_path: "report.html",
    pages: "1",
  });
  assert.deepEqual(calls[12]?.body, {
    input_path: "report.pdf",
    output_path: "protected.pdf",
    password: "open",
    owner_password: "owner",
  });
  assert.deepEqual(calls[17]?.body, {
    input_path: "signed.pdf",
    signature_path: "signed.pdf.signature.json",
    secret: "local-secret",
  });
  assert.deepEqual(calls[18]?.body, {
    input_path: "report.pdf",
  });
  assert.deepEqual(calls[19]?.body, {
    input_path: "report.pdf",
    output_path: "sanitized.pdf",
  });
  assert.deepEqual(calls[20]?.body, {
    input_path: "report.pdf",
    output_path: "redacted.pdf",
    regions: [{ page: 1, bbox: [60, 700, 280, 760], label: "secret" }],
  });
  assert.deepEqual(calls[21]?.body, {
    input_path: "redacted.pdf",
    search_terms: ["SECRET-CODE-123"],
  });
  assert.deepEqual(calls[22]?.body, {
    input_path: "redacted.pdf",
    search_terms: ["SECRET-CODE-123"],
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
