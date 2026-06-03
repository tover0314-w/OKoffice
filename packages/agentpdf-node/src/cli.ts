#!/usr/bin/env node
import { readFile } from "node:fs/promises";
import { pathToFileURL } from "node:url";

import { AgentPDFClient } from "./client.js";
import type { AgentPDFFetch } from "./client.js";
import type { JsonObject, ToolResult } from "./types.js";

export interface CliRuntime {
  fetch?: AgentPDFFetch;
  stdout?: (line: string) => void;
  stderr?: (line: string) => void;
}

class UsageError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "UsageError";
  }
}

export async function runCli(
  argv: string[] = process.argv.slice(2),
  runtime: CliRuntime = {},
): Promise<number> {
  const args = [...argv];
  const stdout = runtime.stdout ?? ((line: string) => process.stdout.write(`${line}\n`));
  const stderr = runtime.stderr ?? ((line: string) => process.stderr.write(`${line}\n`));

  try {
    const baseUrl = takeOption(args, ["--base-url"]);
    const command = args.shift();
    if (!command || command === "--help" || command === "-h") {
      stdout(helpText());
      return 0;
    }

    const client = new AgentPDFClient({ baseUrl, fetch: runtime.fetch });
    if (command === "tools") {
      stdout(JSON.stringify(await client.listTools(), null, 2));
      return 0;
    }
    if (command === "run") {
      const toolName = args.shift();
      if (!toolName) {
        throw new UsageError("Missing tool name for run.");
      }
      const payload = parsePayload(takeRequiredOption(args, ["--payload"]));
      return emitResult(await client.runTool(toolName, payload), stdout);
    }
    if (command === "agent-setup-claude-code") {
      return emitResult(
        await client.setupClaudeCode({
          outputPath: takeOption(args, ["--output", "-o"]),
          safeRoot: takeOption(args, ["--safe-root"]),
          command: takeOption(args, ["--command"]),
          argsPrefix: takeOptions(args, ["--arg-prefix"]),
          serverName: takeOption(args, ["--server-name"]),
          scope: parseScope(takeOption(args, ["--scope"])),
        }),
        stdout,
      );
    }
    if (command === "agent-setup-codex") {
      return emitResult(
        await client.setupCodex({
          outputPath: takeOption(args, ["--output", "-o"]),
          safeRoot: takeOption(args, ["--safe-root"]),
          command: takeOption(args, ["--command"]),
          argsPrefix: takeOptions(args, ["--arg-prefix"]),
          serverName: takeOption(args, ["--server-name"]),
        }),
        stdout,
      );
    }
    if (command === "inspect") {
      const path = args.shift();
      if (!path) {
        throw new UsageError("Missing PDF path for inspect.");
      }
      return emitResult(await client.inspectDocument({ path }), stdout);
    }
    if (command === "inspect-pages") {
      const inputPath = args.shift();
      if (!inputPath) {
        throw new UsageError("Missing PDF path for inspect-pages.");
      }
      return emitResult(
        await client.inspectPages({
          inputPath,
          pages: takeOption(args, ["--pages"]),
          renderCheck: takeFlag(args, ["--render-check"]),
        }),
        stdout,
      );
    }
    if (command === "workflow-plan") {
      return emitResult(
        await client.workflowPlan({
          goal: takeRequiredOption(args, ["--goal"]),
          inputPath: takeOption(args, ["--input-path"]),
        }),
        stdout,
      );
    }
    if (command === "workflow-run") {
      const workflow = parsePayload(takeRequiredOption(args, ["--payload"]));
      const artifactDir = takeOption(args, ["--artifact-dir"]);
      const bindings = parseBindings(takeOptions(args, ["--binding"]));
      if (artifactDir) {
        workflow.artifact_dir = artifactDir;
      }
      if (Object.keys(bindings).length > 0) {
        workflow.bindings = {
          ...(isJsonObject(workflow.bindings) ? workflow.bindings : {}),
          ...bindings,
        };
      }
      return emitResult(
        await client.workflowRun({
          workflow,
          dryRun: takeFlag(args, ["--dry-run"]),
        }),
        stdout,
      );
    }
    if (command === "workflow-report") {
      return emitResult(
        await client.workflowReport({
          workflowRun: parsePayload(takeRequiredOption(args, ["--payload"])),
          outputPath: takeOption(args, ["--output", "-o"]),
        }),
        stdout,
      );
    }
    if (command === "context-build") {
      return emitResult(
        await client.buildContextPacket({
          contextItems: await contextItemsFromCli(
            takeOptions(args, ["--file"]),
            takeOptions(args, ["--text"]),
            takeOptions(args, ["--link"]),
            takeOptions(args, ["--item-json"]),
          ),
          outputPath: takeRequiredOption(args, ["--output", "-o"]),
          title: takeOption(args, ["--title"]),
          intent: takeOption(args, ["--intent"]),
        }),
        stdout,
      );
    }
    if (command === "context-ingest") {
      const contextItem = await contextItemFromCli({
        file: takeOption(args, ["--file"]),
        text: takeOption(args, ["--text"]),
        link: takeOption(args, ["--link"]),
        itemJson: takeOption(args, ["--item-json"]),
        role: takeOption(args, ["--role"]),
        label: takeOption(args, ["--label"]),
        itemType: takeOption(args, ["--type"]),
        transcript: takeOption(args, ["--transcript"]),
        durationSeconds: takeNumberOption(args, ["--duration-seconds"]),
      });
      return emitResult(
        await client.ingestContext({
          contextItem,
          outputPath: takeOption(args, ["--output", "-o"]),
        }),
        stdout,
      );
    }
    if (command === "context-packet") {
      return emitResult(
        await client.contextPacket({
          contextItems: await contextItemsFromCli(
            takeOptions(args, ["--file"]),
            takeOptions(args, ["--text"]),
            takeOptions(args, ["--link"]),
            takeOptions(args, ["--item-json"]),
          ),
          outputPath: takeRequiredOption(args, ["--output", "-o"]),
          title: takeOption(args, ["--title"]),
          intent: takeOption(args, ["--intent"]),
        }),
        stdout,
      );
    }
    if (command === "context-classify") {
      const contextPacketPath = args.shift();
      if (!contextPacketPath) {
        throw new UsageError("Missing context packet path for context-classify.");
      }
      const targetProfile = await parseOptionalObject(takeOption(args, ["--target-profile"]));
      return emitResult(
        await client.classifyContext({
          contextPacketPath,
          targetProfile: targetProfile ?? undefined,
          profile: takeOption(args, ["--profile"]),
          outputPath: takeOption(args, ["--output", "-o"]),
        }),
        stdout,
      );
    }
    if (command === "code-snapshot") {
      const path = args.shift();
      if (!path) {
        throw new UsageError("Missing code path for code-snapshot.");
      }
      return emitResult(
        await client.codeSnapshot({
          path,
          outputPath: takeOption(args, ["--output", "-o"]),
          label: takeOption(args, ["--label"]),
          role: takeOption(args, ["--role"]),
          contextItemId: takeOption(args, ["--context-item-id"]),
          lineStart: takeIntegerOption(args, ["--line-start"]),
          lineEnd: takeIntegerOption(args, ["--line-end"]),
          repositoryRoot: takeOption(args, ["--repository-root"]),
          includeDependencies: takeFlag(args, ["--include-dependencies"]),
        }),
        stdout,
      );
    }
    if (command === "data-profile") {
      const path = args.shift();
      if (!path) {
        throw new UsageError("Missing data path for data-profile.");
      }
      return emitResult(
        await client.dataProfile({
          path,
          outputPath: takeOption(args, ["--output", "-o"]),
          label: takeOption(args, ["--label"]),
          role: takeOption(args, ["--role"]),
          contextItemId: takeOption(args, ["--context-item-id"]),
          sheet: takeOption(args, ["--sheet"]),
          maxRows: takeIntegerOption(args, ["--max-rows"]),
        }),
        stdout,
      );
    }
    if (command === "target-profiles") {
      return emitResult(
        await client.targetProfiles({
          outputPath: takeOption(args, ["--output", "-o"]),
        }),
        stdout,
      );
    }
    if (command === "target-validate") {
      return emitResult(
        await client.validateTargetProfile({
          targetProfile: await parseOptionalObject(takeOption(args, ["--target-profile"])),
          profile: takeOption(args, ["--profile"]),
          outputPath: takeOption(args, ["--output", "-o"]),
        }),
        stdout,
      );
    }
    if (command === "compose-plan") {
      const contextPacketPath = args.shift();
      if (!contextPacketPath) {
        throw new UsageError("Missing context packet path for compose-plan.");
      }
      const targetProfile = await parseOptionalObject(takeOption(args, ["--target-profile"]));
      return emitResult(
        await client.composePlan({
          contextPacketPath,
          targetProfile: targetProfile ?? undefined,
          profile: takeOption(args, ["--profile"]),
          outputPath: takeOption(args, ["--output", "-o"]),
          stylePack: takeOption(args, ["--style-pack"]),
          title: takeOption(args, ["--title"]),
        }),
        stdout,
      );
    }
    if (command === "compose-render-ir") {
      const compositionPath = args.shift();
      if (!compositionPath) {
        throw new UsageError("Missing composition plan/IR path for compose-render-ir.");
      }
      return emitResult(
        await client.composeRenderIr({
          compositionPath,
          outputPath: takeRequiredOption(args, ["--output", "-o"]),
          stylePack: takeOption(args, ["--style-pack"]),
          title: takeOption(args, ["--title"]),
        }),
        stdout,
      );
    }
    if (command === "compose-from-context") {
      const contextPacketPath = args.shift();
      if (!contextPacketPath) {
        throw new UsageError("Missing context packet path for compose-from-context.");
      }
      const targetProfile = await parseOptionalObject(takeOption(args, ["--target-profile"]));
      return emitResult(
        await client.composeFromContext({
          contextPacketPath,
          targetProfile: targetProfile ?? undefined,
          profile: takeOption(args, ["--profile"]),
          outputPath: takeRequiredOption(args, ["--output", "-o"]),
          stylePack: takeOption(args, ["--style-pack"]),
          title: takeOption(args, ["--title"]),
        }),
        stdout,
      );
    }
    if (command === "compose-add-code-block") {
      const inputPath = args.shift();
      if (!inputPath) {
        throw new UsageError("Missing PDF path for compose-add-code-block.");
      }
      return emitResult(
        await client.composeAddCodeBlock({
          inputPath,
          outputPath: takeRequiredOption(args, ["--output", "-o"]),
          title: takeOption(args, ["--title"]) ?? "Code Block",
          code: takeRequiredOption(args, ["--code"]),
          language: takeOption(args, ["--language"]),
          sourceRefs: takeOptions(args, ["--source-ref"]),
          blockId: takeOption(args, ["--block-id"]),
          targetSlot: takeOption(args, ["--target-slot"]),
          compositionPath: takeOption(args, ["--composition"]),
          layerManifestPath: takeOption(args, ["--layers"]),
          manifestOutputPath: takeOption(args, ["--manifest-output"]),
        }),
        stdout,
      );
    }
    if (command === "compose-add-table") {
      const inputPath = args.shift();
      if (!inputPath) {
        throw new UsageError("Missing PDF path for compose-add-table.");
      }
      return emitResult(
        await client.composeAddTable({
          inputPath,
          outputPath: takeRequiredOption(args, ["--output", "-o"]),
          title: takeOption(args, ["--title"]) ?? "Table",
          columns: parseCsvValues(takeRequiredOption(args, ["--columns"])),
          rows: takeOptions(args, ["--row"]).map(parseCsvValues),
          sourceRefs: takeOptions(args, ["--source-ref"]),
          blockId: takeOption(args, ["--block-id"]),
          targetSlot: takeOption(args, ["--target-slot"]),
          compositionPath: takeOption(args, ["--composition"]),
          layerManifestPath: takeOption(args, ["--layers"]),
          manifestOutputPath: takeOption(args, ["--manifest-output"]),
        }),
        stdout,
      );
    }
    if (command === "compose-add-figure") {
      const inputPath = args.shift();
      if (!inputPath) {
        throw new UsageError("Missing PDF path for compose-add-figure.");
      }
      return emitResult(
        await client.composeAddFigure({
          inputPath,
          outputPath: takeRequiredOption(args, ["--output", "-o"]),
          title: takeOption(args, ["--title"]) ?? "Figure",
          imagePath: takeRequiredOption(args, ["--image"]),
          caption: takeOption(args, ["--caption"]),
          sourceRefs: takeOptions(args, ["--source-ref"]),
          blockId: takeOption(args, ["--block-id"]),
          targetSlot: takeOption(args, ["--target-slot"]),
          compositionPath: takeOption(args, ["--composition"]),
          layerManifestPath: takeOption(args, ["--layers"]),
          manifestOutputPath: takeOption(args, ["--manifest-output"]),
        }),
        stdout,
      );
    }
    if (command === "compose-add-appendix") {
      const inputPath = args.shift();
      if (!inputPath) {
        throw new UsageError("Missing PDF path for compose-add-appendix.");
      }
      return emitResult(
        await client.composeAddAppendix({
          inputPath,
          outputPath: takeRequiredOption(args, ["--output", "-o"]),
          title: takeOption(args, ["--title"]) ?? "Appendix",
          markdown: takeRequiredOption(args, ["--markdown"]),
          sourceRefs: takeOptions(args, ["--source-ref"]),
          blockId: takeOption(args, ["--block-id"]),
          targetSlot: takeOption(args, ["--target-slot"]),
          compositionPath: takeOption(args, ["--composition"]),
          layerManifestPath: takeOption(args, ["--layers"]),
          manifestOutputPath: takeOption(args, ["--manifest-output"]),
        }),
        stdout,
      );
    }
    if (command === "compose-add-citation") {
      const inputPath = args.shift();
      if (!inputPath) {
        throw new UsageError("Missing PDF path for compose-add-citation.");
      }
      return emitResult(
        await client.composeAddCitation({
          inputPath,
          outputPath: takeRequiredOption(args, ["--output", "-o"]),
          title: takeOption(args, ["--title"]) ?? "Citation",
          source: takeRequiredOption(args, ["--source"]),
          quote: takeOption(args, ["--quote"]),
          page: takeOption(args, ["--page"]),
          sourceRefs: takeOptions(args, ["--source-ref"]),
          blockId: takeOption(args, ["--block-id"]),
          targetSlot: takeOption(args, ["--target-slot"]),
          compositionPath: takeOption(args, ["--composition"]),
          layerManifestPath: takeOption(args, ["--layers"]),
          manifestOutputPath: takeOption(args, ["--manifest-output"]),
        }),
        stdout,
      );
    }
    if (command === "compose-add-media-reference") {
      const inputPath = args.shift();
      if (!inputPath) {
        throw new UsageError("Missing PDF path for compose-add-media-reference.");
      }
      return emitResult(
        await client.composeAddMediaReference({
          inputPath,
          outputPath: takeRequiredOption(args, ["--output", "-o"]),
          title: takeOption(args, ["--title"]) ?? "Media Reference",
          mediaPath: takeRequiredOption(args, ["--media"]),
          mediaKind: takeOption(args, ["--media-kind"]),
          transcriptExcerpt: takeOption(args, ["--transcript-excerpt"]),
          durationSeconds: takeNumberOption(args, ["--duration-seconds"]),
          chapterCount: takeIntegerOption(args, ["--chapter-count"]),
          keyframeCount: takeIntegerOption(args, ["--keyframe-count"]),
          sourceRefs: takeOptions(args, ["--source-ref"]),
          blockId: takeOption(args, ["--block-id"]),
          targetSlot: takeOption(args, ["--target-slot"]),
          compositionPath: takeOption(args, ["--composition"]),
          layerManifestPath: takeOption(args, ["--layers"]),
          manifestOutputPath: takeOption(args, ["--manifest-output"]),
        }),
        stdout,
      );
    }
    if (command === "compose-add-slide") {
      const inputPath = args.shift();
      if (!inputPath) {
        throw new UsageError("Missing PDF path for compose-add-slide.");
      }
      return emitResult(
        await client.composeAddSlide({
          inputPath,
          outputPath: takeRequiredOption(args, ["--output", "-o"]),
          title: takeOption(args, ["--title"]) ?? "Slide",
          subtitle: takeOption(args, ["--subtitle"]),
          body: takeOptions(args, ["--body"]),
          code: takeOption(args, ["--code"]),
          imagePath: takeOption(args, ["--image"]),
          sourceRefs: takeOptions(args, ["--source-ref"]),
          blockId: takeOption(args, ["--block-id"]),
          targetSlot: takeOption(args, ["--target-slot"]),
          compositionPath: takeOption(args, ["--composition"]),
          layerManifestPath: takeOption(args, ["--layers"]),
          manifestOutputPath: takeOption(args, ["--manifest-output"]),
        }),
        stdout,
      );
    }
    if (command === "evidence-coverage-report") {
      const compositionPath = args.shift();
      if (!compositionPath) {
        throw new UsageError("Missing composition path for evidence-coverage-report.");
      }
      return emitResult(
        await client.evidenceCoverageReport({
          compositionPath,
          outputPath: takeOption(args, ["--output", "-o"]),
        }),
        stdout,
      );
    }
    if (command === "evidence-map-sources") {
      const compositionPath = args[0] && !args[0].startsWith("-") ? args.shift() : undefined;
      return emitResult(
        await client.evidenceMapSources({
          compositionPath,
          blocks: await parseOptionalObjectList(takeOption(args, ["--blocks"])),
          claims: await parseOptionalObjectList(takeOption(args, ["--claims"])),
          contextPacketPath: takeOption(args, ["--context-packet"]),
          outputPath: takeOption(args, ["--output", "-o"]),
        }),
        stdout,
      );
    }
    if (command === "evidence-context-packet-report") {
      const contextPacketPath = args.shift();
      if (!contextPacketPath) {
        throw new UsageError("Missing context packet path for evidence-context-packet-report.");
      }
      return emitResult(
        await client.contextPacketReport({
          contextPacketPath,
          outputPath: takeRequiredOption(args, ["--output", "-o"]),
          reportOutputPath: takeOption(args, ["--report-output"]),
          title: takeOption(args, ["--title"]),
          stylePack: takeOption(args, ["--style-pack"]),
        }),
        stdout,
      );
    }
    if (command === "export-bundle") {
      const artifactPaths = takeOptions(args, ["--file"]);
      if (artifactPaths.length === 0) {
        throw new UsageError("Missing --file for export-bundle.");
      }
      const metadata = parseBindings(takeOptions(args, ["--metadata"]));
      return emitResult(
        await client.exportBundle({
          artifactPaths,
          outputPath: takeRequiredOption(args, ["--output", "-o"]),
          title: takeOption(args, ["--title"]),
          metadata: Object.keys(metadata).length > 0 ? metadata : undefined,
        }),
        stdout,
      );
    }
    if (command === "verify-bundle") {
      const bundlePath = args.shift();
      if (!bundlePath) {
        throw new UsageError("Missing bundle path for verify-bundle.");
      }
      return emitResult(
        await client.verifyBundle({
          bundlePath,
        }),
        stdout,
      );
    }
    if (command === "patch-plan") {
      const inputPath = args.shift();
      if (!inputPath) {
        throw new UsageError("Missing input PDF path for patch-plan.");
      }
      const operationList = parseOperationsPayload(takeRequiredOption(args, ["--operations"]));
      return emitResult(
        await client.patchPlan({
          inputPath,
          operations: operationList.filter(isJsonObject),
          outputPath: takeRequiredOption(args, ["--output", "-o"]),
          compositionPath: takeOption(args, ["--composition"]),
          layerManifestPath: takeOption(args, ["--layers"]),
          reason: takeOption(args, ["--reason"]),
        }),
        stdout,
      );
    }
    if (command === "patch-preview") {
      const patchManifestPath = args.shift();
      if (!patchManifestPath) {
        throw new UsageError("Missing patch manifest path for patch-preview.");
      }
      return emitResult(
        await client.patchPreview({
          patchManifestPath,
          outputPath: takeOption(args, ["--output", "-o"]),
        }),
        stdout,
      );
    }
    if (command === "patch-apply") {
      const patchManifestPath = args.shift();
      if (!patchManifestPath) {
        throw new UsageError("Missing patch manifest path for patch-apply.");
      }
      return emitResult(
        await client.patchApply({
          patchManifestPath,
          outputPath: takeRequiredOption(args, ["--output", "-o"]),
        }),
        stdout,
      );
    }
    if (command === "patch-verify") {
      const patchManifestPath = args.shift();
      const patchedPath = args.shift();
      if (!patchManifestPath || !patchedPath) {
        throw new UsageError("Missing patch manifest or patched PDF path for patch-verify.");
      }
      return emitResult(await client.patchVerify({ patchManifestPath, patchedPath }), stdout);
    }
    if (command === "image-to-pdf") {
      const outputPath = takeRequiredOption(args, ["--output", "-o"]);
      const imagePaths = [...args];
      if (imagePaths.length === 0) {
        throw new UsageError("Missing image path for image-to-pdf.");
      }
      return emitResult(await client.imageToPdf({ imagePaths, outputPath }), stdout);
    }
    if (command === "reorder-pages") {
      const inputPath = args.shift();
      if (!inputPath) {
        throw new UsageError("Missing PDF path for reorder-pages.");
      }
      return emitResult(
        await client.reorderPages({
          inputPath,
          order: takeRequiredOption(args, ["--order"]),
          outputPath: takeRequiredOption(args, ["--output", "-o"]),
        }),
        stdout,
      );
    }
    if (command === "insert-blank-pages") {
      const inputPath = args.shift();
      if (!inputPath) {
        throw new UsageError("Missing PDF path for insert-blank-pages.");
      }
      return emitResult(
        await client.insertBlankPages({
          inputPath,
          afterPage: takeRequiredIntegerOption(args, ["--after-page"]),
          outputPath: takeRequiredOption(args, ["--output", "-o"]),
          count: takeIntegerOption(args, ["--count"]),
        }),
        stdout,
      );
    }
    if (command === "compress") {
      const inputPath = args.shift();
      if (!inputPath) {
        throw new UsageError("Missing PDF path for compress.");
      }
      return emitResult(
        await client.compress({
          inputPath,
          outputPath: takeRequiredOption(args, ["--output", "-o"]),
        }),
        stdout,
      );
    }
    if (command === "repair") {
      const inputPath = args.shift();
      if (!inputPath) {
        throw new UsageError("Missing PDF path for repair.");
      }
      return emitResult(
        await client.repair({
          inputPath,
          outputPath: takeRequiredOption(args, ["--output", "-o"]),
        }),
        stdout,
      );
    }
    if (command === "watermark") {
      const inputPath = args.shift();
      if (!inputPath) {
        throw new UsageError("Missing PDF path for watermark.");
      }
      const text = takeRequiredOption(args, ["--text"]);
      const outputPath = takeRequiredOption(args, ["--output", "-o"]);
      return emitResult(
        await client.watermark({
          inputPath,
          text,
          outputPath,
          pages: takeOption(args, ["--pages"]),
          fontSize: takeIntegerOption(args, ["--font-size"]),
          opacity: takeNumberOption(args, ["--opacity"]),
          angle: takeIntegerOption(args, ["--angle"]),
        }),
        stdout,
      );
    }
    if (command === "page-numbers") {
      const inputPath = args.shift();
      if (!inputPath) {
        throw new UsageError("Missing PDF path for page-numbers.");
      }
      const outputPath = takeRequiredOption(args, ["--output", "-o"]);
      return emitResult(
        await client.addPageNumbers({
          inputPath,
          outputPath,
          pages: takeOption(args, ["--pages"]),
          template: takeOption(args, ["--template"]),
          fontSize: takeIntegerOption(args, ["--font-size"]),
        }),
        stdout,
      );
    }
    if (command === "validate") {
      const path = args.shift();
      if (!path) {
        throw new UsageError("Missing PDF path for validate.");
      }
      return emitResult(
        await client.validateOutput({
          path,
          expectedPages: takeIntegerOption(args, ["--expected-pages"]),
        }),
        stdout,
      );
    }
    if (command === "render-check") {
      const path = args.shift();
      if (!path) {
        throw new UsageError("Missing PDF path for render-check.");
      }
      return emitResult(
        await client.renderCheck({
          path,
          pages: takeOption(args, ["--pages"]),
        }),
        stdout,
      );
    }
    if (command === "blank-page-check") {
      const path = args.shift();
      if (!path) {
        throw new UsageError("Missing PDF path for blank-page-check.");
      }
      return emitResult(
        await client.blankPageCheck({
          path,
          pages: takeOption(args, ["--pages"]),
        }),
        stdout,
      );
    }
    if (command === "extract-images") {
      const inputPath = args.shift();
      if (!inputPath) {
        throw new UsageError("Missing PDF path for extract-images.");
      }
      return emitResult(
        await client.extractImages({
          inputPath,
          pages: takeOption(args, ["--pages"]),
          outDir: takeOption(args, ["--out-dir"]),
        }),
        stdout,
      );
    }
    if (command === "parse-lite") {
      const inputPath = args.shift();
      if (!inputPath) {
        throw new UsageError("Missing PDF path for parse-lite.");
      }
      return emitResult(
        await client.parseLite({ inputPath, pages: takeOption(args, ["--pages"]) }),
        stdout,
      );
    }
    if (command === "pdf-to-json") {
      const inputPath = args.shift();
      if (!inputPath) {
        throw new UsageError("Missing PDF path for pdf-to-json.");
      }
      const outputPath = takeRequiredOption(args, ["--output", "-o"]);
      return emitResult(
        await client.pdfToJson({ inputPath, outputPath, pages: takeOption(args, ["--pages"]) }),
        stdout,
      );
    }
    if (command === "pdf-to-markdown") {
      const inputPath = args.shift();
      if (!inputPath) {
        throw new UsageError("Missing PDF path for pdf-to-markdown.");
      }
      const outputPath = takeRequiredOption(args, ["--output", "-o"]);
      return emitResult(
        await client.pdfToMarkdown({
          inputPath,
          outputPath,
          pages: takeOption(args, ["--pages"]),
        }),
        stdout,
      );
    }
    if (command === "rag-ingest") {
      const inputPath = args.shift();
      if (!inputPath) {
        throw new UsageError("Missing PDF path for rag-ingest.");
      }
      const indexPath = takeRequiredOption(args, ["--index"]);
      return emitResult(
        await client.ragIngest({
          inputPath,
          indexPath,
          pages: takeOption(args, ["--pages"]),
          maxChars: takeIntegerOption(args, ["--max-chars"]),
          overlapChars: takeIntegerOption(args, ["--overlap-chars"]),
        }),
        stdout,
      );
    }
    if (command === "rag-query") {
      const indexPath = args.shift();
      if (!indexPath) {
        throw new UsageError("Missing index path for rag-query.");
      }
      return emitResult(
        await client.ragQuery({
          indexPath,
          query: takeRequiredOption(args, ["--query"]),
          topK: takeIntegerOption(args, ["--top-k"]),
        }),
        stdout,
      );
    }
    if (command === "rag-chat") {
      const inputPath = args.shift();
      if (!inputPath) {
        throw new UsageError("Missing PDF path for rag-chat.");
      }
      return emitResult(
        await client.ragChat({
          inputPath,
          question: takeRequiredOption(args, ["--question"]),
          indexPath: takeOption(args, ["--index"]),
          reportOutputPath: takeOption(args, ["--report-output"]),
          highlightOutputPath: takeOption(args, ["--highlight-output"]),
          pages: takeOption(args, ["--pages"]),
          topK: takeIntegerOption(args, ["--top-k"]),
          maxChars: takeIntegerOption(args, ["--max-chars"]),
          overlapChars: takeIntegerOption(args, ["--overlap-chars"]),
          stylePack: takeOption(args, ["--style-pack"]),
          highlightColor: takeOption(args, ["--highlight-color"]),
        }),
        stdout,
      );
    }
    if (command === "rag-search") {
      const indexPath = args.shift();
      if (!indexPath) {
        throw new UsageError("Missing index path for rag-search.");
      }
      return emitResult(
        await client.ragSearch({
          indexPath,
          query: takeRequiredOption(args, ["--query"]),
          topK: takeIntegerOption(args, ["--top-k"]),
        }),
        stdout,
      );
    }
    if (command === "rag-cite-answer") {
      const indexPath = args.shift();
      if (!indexPath) {
        throw new UsageError("Missing index path for rag-cite-answer.");
      }
      return emitResult(
        await client.ragCiteAnswer({
          indexPath,
          answer: takeRequiredOption(args, ["--answer"]),
          topK: takeIntegerOption(args, ["--top-k"]),
        }),
        stdout,
      );
    }
    if (command === "rag-highlight-sources") {
      const indexPath = args.shift();
      if (!indexPath) {
        throw new UsageError("Missing index path for rag-highlight-sources.");
      }
      return emitResult(
        await client.ragHighlightSources({
          indexPath,
          outputPath: takeRequiredOption(args, ["--output", "-o"]),
          answer: takeOption(args, ["--answer"]),
          query: takeOption(args, ["--query"]),
          topK: takeIntegerOption(args, ["--top-k"]),
          highlightColor: takeOption(args, ["--highlight-color"]),
        }),
        stdout,
      );
    }
    if (command === "rag-export-report") {
      const indexPath = args.shift();
      if (!indexPath) {
        throw new UsageError("Missing index path for rag-export-report.");
      }
      return emitResult(
        await client.ragExportReport({
          indexPath,
          outputPath: takeRequiredOption(args, ["--output", "-o"]),
          question: takeRequiredOption(args, ["--question"]),
          answer: takeOption(args, ["--answer"]),
          topK: takeIntegerOption(args, ["--top-k"]),
          includeCitations: takeBooleanOption(args, "--include-citations", "--no-citations"),
          title: takeOption(args, ["--title"]),
          stylePack: takeOption(args, ["--style-pack"]),
        }),
        stdout,
      );
    }
    if (command === "create-text") {
      const text = takeRequiredOption(args, ["--text"]);
      const outputPath = takeRequiredOption(args, ["--output", "-o"]);
      const title = takeOption(args, ["--title"]);
      return emitResult(await client.createTextPdf({ text, outputPath, title }), stdout);
    }
    if (command === "create-markdown") {
      const markdown = await readMarkdownOption(args);
      const outputPath = takeRequiredOption(args, ["--output", "-o"]);
      const title = takeOption(args, ["--title"]);
      const stylePack = takeOption(args, ["--style-pack"]);
      return emitResult(
        await client.createMarkdownPdf({ markdown, outputPath, title, stylePack }),
        stdout,
      );
    }
    if (command === "create-from-prompt") {
      const prompt = takeRequiredOption(args, ["--prompt"]);
      const outputPath = takeRequiredOption(args, ["--output", "-o"]);
      return emitResult(
        await client.createFromPrompt({
          prompt,
          outputPath,
          template: takeOption(args, ["--template"]),
          stylePack: takeOption(args, ["--style-pack"]),
          colors: parseColorOverrides(takeOptions(args, ["--color"])),
          data: await parseOptionalObject(takeOption(args, ["--data"])),
          title: takeOption(args, ["--title"]),
        }),
        stdout,
      );
    }
    if (command === "create-templates") {
      return emitResult(await client.createTemplates(), stdout);
    }
    if (command === "create-template-packs") {
      return emitResult(
        await client.createTemplatePacks({
          outputPath: takeOption(args, ["--output", "-o"]),
        }),
        stdout,
      );
    }
    if (command === "create-validate-template-pack") {
      const templatePackPath = args.shift();
      if (!templatePackPath) {
        throw new UsageError("Missing template pack path for create-validate-template-pack.");
      }
      return emitResult(
        await client.validateTemplatePack({
          templatePackPath,
          outputPath: takeOption(args, ["--output", "-o"]),
        }),
        stdout,
      );
    }
    if (command === "create-plan-template-pack") {
      const templatePackPath = args.shift();
      if (!templatePackPath) {
        throw new UsageError("Missing template pack path for create-plan-template-pack.");
      }
      return emitResult(
        await client.planTemplatePack({
          templatePackPath,
          targetProfile: await parseOptionalObject(takeOption(args, ["--target-profile"])),
          profile: takeOption(args, ["--profile"]),
          contextPacketPath: takeOption(args, ["--context-packet"]),
          plannedOutputPath: takeOption(args, ["--planned-output"]),
          outputPath: takeOption(args, ["--output", "-o"]),
          preferredTemplateId: takeOption(args, ["--preferred-template"]),
          preferredColorScheme: takeOption(args, ["--preferred-color-scheme"]),
        }),
        stdout,
      );
    }
    if (command === "create-agent") {
      const templatePackPath = args.shift();
      if (!templatePackPath) {
        throw new UsageError("Missing template pack path for create-agent.");
      }
      return emitResult(
        await client.createAgent({
          templatePackPath,
          targetProfile: await parseOptionalObject(takeOption(args, ["--target-profile"])),
          profile: takeOption(args, ["--profile"]),
          contextPacketPath: takeOption(args, ["--context-packet"]),
          outputPath: takeRequiredOption(args, ["--output", "-o"]),
          planOutputPath: takeOption(args, ["--plan-output"]),
          coverageOutputPath: takeOption(args, ["--coverage-output"]),
          contextClassificationOutputPath: takeOption(args, ["--context-classification-output"]),
          contextReportOutputPath: takeOption(args, ["--context-report-output"]),
          contextReportJsonOutputPath: takeOption(args, ["--context-report-json-output"]),
          bundleOutputPath: takeOption(args, ["--bundle-output"]),
          preferredTemplateId: takeOption(args, ["--preferred-template"]),
          preferredColorScheme: takeOption(args, ["--preferred-color-scheme"]),
          title: takeOption(args, ["--title"]),
          prompt: takeOption(args, ["--prompt"]),
          stylePack: takeOption(args, ["--style-pack"]),
        }),
        stdout,
      );
    }
    if (command === "create-from-template-pack") {
      const templatePackPath = args.shift();
      if (!templatePackPath) {
        throw new UsageError("Missing template pack path for create-from-template-pack.");
      }
      return emitResult(
        await client.createFromTemplatePack({
          templatePackPath,
          templateId: takeRequiredOption(args, ["--template"]),
          outputPath: takeRequiredOption(args, ["--output", "-o"]),
          colorScheme: takeOption(args, ["--color-scheme"]),
          data: await parseOptionalObject(takeOption(args, ["--data"])),
          contextPacketPath: takeOption(args, ["--context-packet"]),
          title: takeOption(args, ["--title"]),
          prompt: takeOption(args, ["--prompt"]),
          stylePack: takeOption(args, ["--style-pack"]),
        }),
        stdout,
      );
    }
    if (command === "create-template-preview") {
      const template = takeRequiredOption(args, ["--template"]);
      const outputPath = takeRequiredOption(args, ["--output", "-o"]);
      return emitResult(
        await client.createTemplatePreview({
          template,
          outputPath,
          stylePack: takeOption(args, ["--style-pack"]),
          colors: parseColorOverrides(takeOptions(args, ["--color"])),
          data: await parseOptionalObject(takeOption(args, ["--data"])),
        }),
        stdout,
      );
    }

    throw new UsageError(`Unknown command: ${command}`);
  } catch (error) {
    stderr(error instanceof Error ? error.message : String(error));
    return 1;
  }
}

function emitResult(result: ToolResult, stdout: (line: string) => void): number {
  stdout(JSON.stringify(result, null, 2));
  return result.status === "failed" ? 1 : 0;
}

function takeRequiredOption(args: string[], names: string[]): string {
  const value = takeOption(args, names);
  if (!value) {
    throw new UsageError(`Missing required option: ${names[0]}`);
  }
  return value;
}

function takeOption(args: string[], names: string[]): string | undefined {
  const index = args.findIndex((arg) => names.includes(arg));
  if (index === -1) {
    return undefined;
  }
  const value = args[index + 1];
  if (!value) {
    throw new UsageError(`Missing value for option: ${args[index]}`);
  }
  args.splice(index, 2);
  return value;
}

function takeOptions(args: string[], names: string[]): string[] {
  const values: string[] = [];
  let value = takeOption(args, names);
  while (value !== undefined) {
    values.push(value);
    value = takeOption(args, names);
  }
  return values;
}

function takeFlag(args: string[], names: string[]): boolean {
  const index = args.findIndex((arg) => names.includes(arg));
  if (index === -1) {
    return false;
  }
  args.splice(index, 1);
  return true;
}

function takeBooleanOption(args: string[], trueName: string, falseName: string): boolean | undefined {
  const trueIndex = args.indexOf(trueName);
  const falseIndex = args.indexOf(falseName);
  if (trueIndex === -1 && falseIndex === -1) {
    return undefined;
  }
  if (trueIndex !== -1 && falseIndex !== -1) {
    throw new UsageError(`Use only one of ${trueName} or ${falseName}.`);
  }
  if (trueIndex !== -1) {
    args.splice(trueIndex, 1);
    return true;
  }
  args.splice(falseIndex, 1);
  return false;
}

function takeIntegerOption(args: string[], names: string[]): number | undefined {
  const raw = takeOption(args, names);
  if (raw === undefined) {
    return undefined;
  }
  const value = Number(raw);
  if (!Number.isInteger(value)) {
    throw new UsageError(`Option must be an integer: ${names[0]}`);
  }
  return value;
}

function takeRequiredIntegerOption(args: string[], names: string[]): number {
  const value = takeIntegerOption(args, names);
  if (value === undefined) {
    throw new UsageError(`Missing required option: ${names[0]}`);
  }
  return value;
}

function takeNumberOption(args: string[], names: string[]): number | undefined {
  const raw = takeOption(args, names);
  if (raw === undefined) {
    return undefined;
  }
  const value = Number(raw);
  if (!Number.isFinite(value)) {
    throw new UsageError(`Option must be a number: ${names[0]}`);
  }
  return value;
}

function parsePayload(raw: string): JsonObject {
  const parsed = JSON.parse(raw) as unknown;
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new UsageError("--payload must be a JSON object.");
  }
  return parsed as JsonObject;
}

async function parseOptionalObject(raw: string | undefined): Promise<JsonObject | undefined> {
  if (raw === undefined) {
    return undefined;
  }
  try {
    return parsePayload(raw);
  } catch {
    try {
      return parsePayload(await readFile(raw, "utf8"));
    } catch (error) {
      throw new UsageError(`--data must be a JSON object or readable JSON file: ${String(error)}`);
    }
  }
}

async function parseOptionalObjectList(raw: string | undefined): Promise<JsonObject[] | undefined> {
  if (raw === undefined) {
    return undefined;
  }
  let payloadText = raw;
  let parsed: unknown;
  try {
    parsed = JSON.parse(payloadText) as unknown;
  } catch {
    try {
      payloadText = await readFile(raw, "utf8");
      parsed = JSON.parse(payloadText) as unknown;
    } catch (error) {
      throw new UsageError(`Expected a JSON array or readable JSON file: ${String(error)}`);
    }
  }
  if (!Array.isArray(parsed) || !parsed.every(isJsonObject)) {
    throw new UsageError("Expected a JSON array of objects.");
  }
  return parsed;
}

function parseScope(raw: string | undefined): "project" | "local" | "user" | undefined {
  if (raw === undefined) {
    return undefined;
  }
  if (raw === "project" || raw === "local" || raw === "user") {
    return raw;
  }
  throw new UsageError("--scope must be project, local, or user.");
}

function parseOperationsPayload(raw: string): JsonObject[] {
  const parsed = JSON.parse(raw) as unknown;
  const operations = Array.isArray(parsed)
    ? parsed
    : isJsonObject(parsed) && Array.isArray(parsed.operations)
      ? parsed.operations
      : [parsed];
  if (!operations.every(isJsonObject)) {
    throw new UsageError("--operations must be a JSON object, an array of objects, or {\"operations\":[...]}.");
  }
  return operations;
}

function parseColorOverrides(rawColors: string[]): Record<string, string> | undefined {
  if (rawColors.length === 0) {
    return undefined;
  }
  const colors: Record<string, string> = {};
  for (const item of rawColors) {
    const separatorIndex = item.indexOf("=");
    if (separatorIndex <= 0) {
      throw new UsageError("--color must use KEY=#RRGGBB syntax.");
    }
    colors[item.slice(0, separatorIndex)] = item.slice(separatorIndex + 1);
  }
  return colors;
}

function parseCsvValues(raw: string): string[] {
  return raw.split(",").map((item) => item.trim()).filter(Boolean);
}

async function contextItemFromCli(input: {
  file?: string;
  text?: string;
  link?: string;
  itemJson?: string;
  role?: string;
  label?: string;
  itemType?: string;
  transcript?: string;
  durationSeconds?: number;
}): Promise<JsonObject> {
  const items = await contextItemsFromCli(
    input.file ? [input.file] : [],
    input.text ? [input.text] : [],
    input.link ? [input.link] : [],
    input.itemJson ? [input.itemJson] : [],
  );
  if (items.length !== 1) {
    throw new UsageError("context-ingest requires exactly one of --file, --text, --link, or --item-json.");
  }
  const item: JsonObject = { ...items[0] };
  if (input.role !== undefined) {
    item.role = input.role;
  }
  if (input.label !== undefined) {
    item.label = input.label;
  }
  if (input.itemType !== undefined) {
    item.type = input.itemType;
  }
  if (input.transcript !== undefined) {
    item.transcript = input.transcript;
  }
  if (input.durationSeconds !== undefined) {
    item.duration_seconds = input.durationSeconds;
  }
  return item;
}

async function contextItemsFromCli(
  files: string[],
  texts: string[],
  links: string[],
  itemPayloads: string[],
): Promise<JsonObject[]> {
  const structuredItems: JsonObject[] = [];
  for (const payload of itemPayloads) {
    structuredItems.push(...(await parseContextItemPayload(payload)));
  }
  return [
    ...texts.map((text) => ({ text, role: "brief" })),
    ...files.map((path) => ({ path, role: "source" })),
    ...links.map((uri) => ({ uri, role: "link" })),
    ...structuredItems,
  ];
}

async function parseContextItemPayload(raw: string): Promise<JsonObject[]> {
  let payloadText = raw;
  let parsed: unknown;
  try {
    parsed = JSON.parse(payloadText) as unknown;
  } catch {
    try {
      payloadText = await readFile(raw, "utf8");
      parsed = JSON.parse(payloadText) as unknown;
    } catch (error) {
      throw new UsageError(`--item-json must be a JSON object, JSON array, or readable JSON file: ${String(error)}`);
    }
  }
  if (isJsonObject(parsed)) {
    return [parsed];
  }
  if (Array.isArray(parsed) && parsed.every(isJsonObject)) {
    return parsed;
  }
  throw new UsageError("--item-json must decode to a JSON object or array of objects.");
}

function parseBindings(rawBindings: string[]): JsonObject {
  const bindings: JsonObject = {};
  for (const item of rawBindings) {
    const separatorIndex = item.indexOf("=");
    if (separatorIndex <= 0) {
      throw new UsageError("--binding must use KEY=VALUE syntax.");
    }
    bindings[item.slice(0, separatorIndex)] = item.slice(separatorIndex + 1);
  }
  return bindings;
}

function isJsonObject(value: unknown): value is JsonObject {
  return Boolean(value && typeof value === "object" && !Array.isArray(value));
}

async function readMarkdownOption(args: string[]): Promise<string> {
  const inline = takeOption(args, ["--markdown"]);
  if (inline !== undefined) {
    return inline;
  }
  const markdownFile = takeOption(args, ["--markdown-file"]);
  if (markdownFile) {
    return readFile(markdownFile, "utf-8");
  }
  throw new UsageError("Missing --markdown or --markdown-file for create-markdown.");
}

function helpText(): string {
  return [
    "agentpdf-node: TypeScript/Node client for a local okpdf REST server",
    "",
    "Commands:",
    "  agentpdf-node tools [--base-url URL]",
    "  agentpdf-node run TOOL --payload '{...}' [--base-url URL]",
    "  agentpdf-node agent-setup-claude-code [-o .mcp.json] [--safe-root '${CLAUDE_PROJECT_DIR:-.}']",
    "  agentpdf-node agent-setup-codex [-o codex.mcp.json] [--safe-root .]",
    "  agentpdf-node inspect PATH [--base-url URL]",
    "  agentpdf-node inspect-pages PATH [--pages 1-3] [--render-check]",
    "  agentpdf-node workflow-plan --goal GOAL [--input-path FILE]",
    "  agentpdf-node workflow-run --payload '{...}' [--binding KEY=VALUE] [--dry-run]",
    "  agentpdf-node workflow-report --payload '{...}' [-o report.md]",
    "  agentpdf-node context-build --text TEXT --file FILE --item-json '{...}' -o context.packet.json",
    "  agentpdf-node context-ingest --file FILE [-o context-item.json] [--role ROLE] [--label LABEL]",
    "  agentpdf-node context-packet --item-json context-item.json --file FILE -o context.packet.json",
    "  agentpdf-node context-classify context.packet.json [--profile technical_audit] [-o context.classification.json]",
    "  agentpdf-node code-snapshot src/service.ts [--line-start 1 --line-end 20] [-o code.context-item.json]",
    "  agentpdf-node data-profile metrics.csv [--sheet Sheet1] [-o data.context-item.json]",
    "  agentpdf-node target-profiles [-o profiles.json]",
    "  agentpdf-node target-validate --target-profile '{...}' [-o validation.json]",
    "  agentpdf-node compose-plan context.packet.json --profile technical_audit [-o composition.plan.json]",
    "  agentpdf-node compose-render-ir composition.plan.json -o report.pdf",
    "  agentpdf-node compose-from-context context.packet.json --profile technical_audit -o report.pdf",
    "  agentpdf-node compose-add-code-block report.pdf --code 'print(1)' --source-ref ctx_code -o report.code.pdf",
    "  agentpdf-node compose-add-table report.pdf --columns metric,value --row latency_ms,42 -o report.table.pdf",
    "  agentpdf-node compose-add-figure report.pdf --image diagram.png --source-ref ctx_image -o report.figure.pdf",
    "  agentpdf-node compose-add-appendix report.pdf --markdown '## Sources' --source-ref ctx_code -o report.appendix.pdf",
    "  agentpdf-node compose-add-citation report.pdf --source https://example.com --quote 'Claim text' --source-ref ctx_web -o report.citation.pdf",
    "  agentpdf-node compose-add-media-reference report.pdf --media meeting.mp3 --media-kind audio --transcript-excerpt '00:00 Kickoff' --source-ref ctx_audio -o report.media.pdf",
    "  agentpdf-node compose-add-slide report.pdf --title 'Review Slide' --body 'Decision evidence' --source-ref ctx_slide -o report.slide.pdf",
    "  agentpdf-node evidence-coverage-report report.composition.json [-o coverage.json]",
    "  agentpdf-node evidence-map-sources [report.composition.json] [--context-packet context.packet.json] [--blocks blocks.json] [-o source-map.json]",
    "  agentpdf-node evidence-context-packet-report context.packet.json -o context-report.pdf [--report-output context-report.json]",
    "  agentpdf-node export-bundle --file OUT.pdf --file OUT.composition.json -o audit-bundle.zip",
    "  agentpdf-node verify-bundle audit-bundle.zip",
    "  agentpdf-node patch-plan report.pdf --operations '{...}' -o patch.json",
    "  agentpdf-node patch-preview patch.json [-o preview.json]",
    "  agentpdf-node patch-apply patch.json -o patched.pdf",
    "  agentpdf-node patch-verify patch.json patched.pdf",
    "  agentpdf-node image-to-pdf IMAGE... -o OUT.pdf",
    "  agentpdf-node reorder-pages FILE --order 3,1,2 -o OUT.pdf",
    "  agentpdf-node insert-blank-pages FILE --after-page 1 -o OUT.pdf",
    "  agentpdf-node compress FILE -o OUT.pdf",
    "  agentpdf-node repair FILE -o OUT.pdf",
    "  agentpdf-node watermark FILE --text TEXT -o OUT.pdf",
    "  agentpdf-node page-numbers FILE -o OUT.pdf",
    "  agentpdf-node validate FILE [--expected-pages N]",
    "  agentpdf-node render-check FILE [--pages 1-3]",
    "  agentpdf-node blank-page-check FILE [--pages 1-3]",
    "  agentpdf-node extract-images FILE [--pages 1-3] [--out-dir DIR]",
    "  agentpdf-node parse-lite FILE",
    "  agentpdf-node pdf-to-json FILE -o OUT.json",
    "  agentpdf-node pdf-to-markdown FILE -o OUT.md",
    "  agentpdf-node rag-ingest FILE --index INDEX.json",
    "  agentpdf-node rag-query INDEX.json --query QUERY",
    "  agentpdf-node rag-chat FILE --question QUERY",
    "  agentpdf-node rag-search INDEX.json --query QUERY",
    "  agentpdf-node rag-cite-answer INDEX.json --answer ANSWER",
    "  agentpdf-node rag-highlight-sources INDEX.json --answer ANSWER -o OUT.pdf",
    "  agentpdf-node rag-export-report INDEX.json --question QUERY -o OUT.pdf",
    "  agentpdf-node create-text --text TEXT -o OUT.pdf [--title TITLE]",
    "  agentpdf-node create-markdown --markdown '# Title' -o OUT.pdf",
    "  agentpdf-node create-markdown --markdown-file input.md -o OUT.pdf",
    "  agentpdf-node create-from-prompt --prompt TEXT -o OUT.pdf [--template research_brief] [--color primary=#4f46e5]",
    "  agentpdf-node create-templates",
    "  agentpdf-node create-template-packs [-o packs.json]",
    "  agentpdf-node create-validate-template-pack PACK.json [-o validation.json]",
    "  agentpdf-node create-plan-template-pack PACK.json --profile technical_audit --context-packet context.packet.json --planned-output OUT.pdf [-o plan.json]",
    "  agentpdf-node create-agent PACK.json --profile technical_audit --context-packet context.packet.json -o OUT.pdf [--plan-output plan.json] [--coverage-output coverage.json] [--context-classification-output classification.json] [--context-report-output context-report.pdf] [--bundle-output audit-bundle.zip]",
    "  agentpdf-node create-from-template-pack PACK.json --template board_audit -o OUT.pdf [--color-scheme executive_blue] [--context-packet context.packet.json]",
    "  agentpdf-node create-template-preview --template invoice -o preview.pdf",
  ].join("\n");
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  runCli().then((code) => {
    process.exitCode = code;
  });
}
