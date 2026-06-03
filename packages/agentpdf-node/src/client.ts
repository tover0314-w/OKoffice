import type {
  BlankPageCheckInput,
  BuildContextPacketInput,
  ClassifyContextInput,
  CodeSnapshotInput,
  ComposeAddAppendixInput,
  ComposeAddCitationInput,
  ComposeAddCodeBlockInput,
  ComposeAddFigureInput,
  ComposeAddMediaReferenceInput,
  ComposeAddSlideInput,
  ComposeAddTableInput,
  ComposeFromContextInput,
  ComposePlanInput,
  ComposeRenderIrInput,
  ContextPacketInput,
  ContextPacketReportInput,
  CreateAgentInput,
  CreateMarkdownPdfInput,
  CreateFromPromptInput,
  CreateFromTemplatePackInput,
  CreateTemplatePreviewInput,
  CreateTemplatePacksInput,
  CreateTextPdfInput,
  DataProfileInput,
  EvidenceCoverageReportInput,
  EvidenceMapSourcesInput,
  ExportBundleInput,
  ExtractImagesInput,
  ImageToPdfInput,
  InsertBlankPagesInput,
  IngestContextInput,
  InspectDocumentInput,
  InspectPagesInput,
  JsonObject,
  MergePdfInput,
  MetadataPageInfoInput,
  OptimizePdfInput,
  PageNumbersInput,
  PageCountCheckInput,
  PlanTemplatePackInput,
  PatchApplyInput,
  PatchPlanInput,
  PatchPreviewInput,
  PatchVerifyInput,
  PdfToMarkdownInput,
  PdfToJsonInput,
  ParseLiteInput,
  RagChatInput,
  RagCiteAnswerInput,
  RagExportReportInput,
  RagHighlightSourcesInput,
  RagIngestInput,
  RagQueryInput,
  RagSearchInput,
  RenderCheckInput,
  ReorderPagesInput,
  SecurityRemoveMetadataInput,
  SelectTargetProfileInput,
  SetupClaudeCodeInput,
  SetupCodexInput,
  TargetProfilesInput,
  ToolManifest,
  ToolResult,
  ToolSpec,
  ValidateOutputInput,
  ValidateTemplatePackInput,
  ValidateTargetProfileInput,
  VerifyBundleInput,
  WatermarkInput,
  WorkflowPlanInput,
  WorkflowReportInput,
  WorkflowRunInput,
} from "./types.js";

export type AgentPDFFetch = (input: string | URL, init?: RequestInit) => Promise<Response>;

export interface AgentPDFClientOptions {
  baseUrl?: string;
  fetch?: AgentPDFFetch;
}

export class AgentPDFHttpError extends Error {
  readonly status: number;
  readonly body: unknown;

  constructor(message: string, status: number, body: unknown) {
    super(message);
    this.name = "AgentPDFHttpError";
    this.status = status;
    this.body = body;
  }
}

const DEFAULT_BASE_URL = "http://127.0.0.1:7331";

export class AgentPDFClient {
  readonly baseUrl: string;
  private readonly fetchImpl: AgentPDFFetch;

  constructor(options: AgentPDFClientOptions = {}) {
    this.baseUrl = normalizeBaseUrl(
      options.baseUrl ?? process.env.AGENTPDF_BASE_URL ?? DEFAULT_BASE_URL,
    );
    const fetchImpl = options.fetch ?? globalThis.fetch;
    if (typeof fetchImpl !== "function") {
      throw new Error("AgentPDFClient requires a fetch implementation.");
    }
    this.fetchImpl = fetchImpl.bind(globalThis) as AgentPDFFetch;
  }

  async listTools(): Promise<ToolManifest> {
    return this.getJson<ToolManifest>("/v1/tools");
  }

  async getTool(toolName: string): Promise<ToolSpec> {
    return this.getJson<ToolSpec>(`/v1/tools/${encodeURIComponent(toolName)}`);
  }

  async runTool<TUsage extends JsonObject = JsonObject>(
    toolName: string,
    payload: JsonObject,
  ): Promise<ToolResult<TUsage>> {
    return this.postJson<ToolResult<TUsage>>(
      `/v1/tools/${encodeURIComponent(toolName)}/run`,
      payload,
    );
  }

  async inspectDocument(input: InspectDocumentInput): Promise<ToolResult> {
    return this.runTool("pdf.inspect.document", { path: input.path });
  }

  async setupClaudeCode(input: SetupClaudeCodeInput = {}): Promise<ToolResult> {
    return this.runTool("agent.setup.claude_code", {
      ...(input.outputPath ? { output_path: input.outputPath } : {}),
      ...(input.safeRoot ? { safe_root: input.safeRoot } : {}),
      ...(input.command ? { command: input.command } : {}),
      ...(input.argsPrefix && input.argsPrefix.length > 0 ? { args_prefix: input.argsPrefix } : {}),
      ...(input.serverName ? { server_name: input.serverName } : {}),
      ...(input.scope ? { scope: input.scope } : {}),
    });
  }

  async setupCodex(input: SetupCodexInput = {}): Promise<ToolResult> {
    return this.runTool("agent.setup.codex", {
      ...(input.outputPath ? { output_path: input.outputPath } : {}),
      ...(input.safeRoot ? { safe_root: input.safeRoot } : {}),
      ...(input.command ? { command: input.command } : {}),
      ...(input.argsPrefix && input.argsPrefix.length > 0 ? { args_prefix: input.argsPrefix } : {}),
      ...(input.serverName ? { server_name: input.serverName } : {}),
    });
  }

  async inspectPages(input: InspectPagesInput): Promise<ToolResult> {
    return this.runTool("pdf.inspect.pages", {
      input_path: input.inputPath,
      ...(input.pages ? { pages: input.pages } : {}),
      ...(input.renderCheck !== undefined ? { render_check: input.renderCheck } : {}),
    });
  }

  async workflowPlan(input: WorkflowPlanInput): Promise<ToolResult> {
    return this.runTool("pdf.workflow.plan", {
      goal: input.goal,
      ...(input.inputPath ? { input_path: input.inputPath } : {}),
    });
  }

  async workflowRun(input: WorkflowRunInput): Promise<ToolResult> {
    return this.runTool("pdf.workflow.run", {
      workflow: input.workflow,
      ...(input.dryRun !== undefined ? { dry_run: input.dryRun } : {}),
    });
  }

  async workflowReport(input: WorkflowReportInput): Promise<ToolResult> {
    return this.runTool("pdf.workflow.report", {
      workflow_run: input.workflowRun,
      ...(input.outputPath ? { output_path: input.outputPath } : {}),
    });
  }

  async buildContextPacket(input: BuildContextPacketInput): Promise<ToolResult> {
    return this.runTool("pdf.context.build_packet", {
      context_items: input.contextItems,
      output_path: input.outputPath,
      ...(input.title ? { title: input.title } : {}),
      ...(input.intent ? { intent: input.intent } : {}),
    });
  }

  async ingestContext(input: IngestContextInput): Promise<ToolResult> {
    return this.runTool("pdf.context.ingest", {
      context_item: input.contextItem,
      ...(input.outputPath ? { output_path: input.outputPath } : {}),
    });
  }

  async contextPacket(input: ContextPacketInput): Promise<ToolResult> {
    return this.runTool("pdf.context.packet", {
      context_items: input.contextItems,
      output_path: input.outputPath,
      ...(input.title ? { title: input.title } : {}),
      ...(input.intent ? { intent: input.intent } : {}),
    });
  }

  async classifyContext(input: ClassifyContextInput): Promise<ToolResult> {
    return this.runTool("pdf.context.classify", {
      ...(input.contextPacket ? { context_packet: input.contextPacket } : {}),
      ...(input.contextPacketPath ? { context_packet_path: input.contextPacketPath } : {}),
      ...(input.targetProfile ? { target_profile: input.targetProfile } : {}),
      ...(input.profile ? { profile: input.profile } : {}),
      ...(input.outputPath ? { output_path: input.outputPath } : {}),
    });
  }

  async codeSnapshot(input: CodeSnapshotInput): Promise<ToolResult> {
    return this.runTool("pdf.context.code_snapshot", {
      path: input.path,
      ...(input.outputPath ? { output_path: input.outputPath } : {}),
      ...(input.label ? { label: input.label } : {}),
      ...(input.role ? { role: input.role } : {}),
      ...(input.contextItemId ? { context_item_id: input.contextItemId } : {}),
      ...(input.lineStart !== undefined ? { line_start: input.lineStart } : {}),
      ...(input.lineEnd !== undefined ? { line_end: input.lineEnd } : {}),
      ...(input.repositoryRoot ? { repository_root: input.repositoryRoot } : {}),
      ...(input.includeDependencies !== undefined ? { include_dependencies: input.includeDependencies } : {}),
    });
  }

  async dataProfile(input: DataProfileInput): Promise<ToolResult> {
    return this.runTool("pdf.context.data_profile", {
      path: input.path,
      ...(input.outputPath ? { output_path: input.outputPath } : {}),
      ...(input.label ? { label: input.label } : {}),
      ...(input.role ? { role: input.role } : {}),
      ...(input.contextItemId ? { context_item_id: input.contextItemId } : {}),
      ...(input.sheet ? { sheet: input.sheet } : {}),
      ...(input.maxRows !== undefined ? { max_rows: input.maxRows } : {}),
    });
  }

  async composeFromContext(input: ComposeFromContextInput): Promise<ToolResult> {
    return this.runTool("pdf.compose.from_context", {
      ...(input.contextPacket ? { context_packet: input.contextPacket } : {}),
      ...(input.contextPacketPath ? { context_packet_path: input.contextPacketPath } : {}),
      ...(input.targetProfile ? { target_profile: input.targetProfile } : {}),
      ...(input.profile ? { profile: input.profile } : {}),
      output_path: input.outputPath,
      ...(input.stylePack ? { style_pack: input.stylePack } : {}),
      ...(input.title ? { title: input.title } : {}),
    });
  }

  async composePlan(input: ComposePlanInput): Promise<ToolResult> {
    return this.runTool("pdf.compose.plan", {
      ...(input.contextPacket ? { context_packet: input.contextPacket } : {}),
      ...(input.contextPacketPath ? { context_packet_path: input.contextPacketPath } : {}),
      ...(input.targetProfile ? { target_profile: input.targetProfile } : {}),
      ...(input.profile ? { profile: input.profile } : {}),
      ...(input.outputPath ? { output_path: input.outputPath } : {}),
      ...(input.stylePack ? { style_pack: input.stylePack } : {}),
      ...(input.title ? { title: input.title } : {}),
    });
  }

  async composeRenderIr(input: ComposeRenderIrInput): Promise<ToolResult> {
    return this.runTool("pdf.compose.render_ir", {
      ...(input.composition ? { composition: input.composition } : {}),
      ...(input.compositionPath ? { composition_path: input.compositionPath } : {}),
      output_path: input.outputPath,
      ...(input.stylePack ? { style_pack: input.stylePack } : {}),
      ...(input.title ? { title: input.title } : {}),
    });
  }

  async composeAddCodeBlock(input: ComposeAddCodeBlockInput): Promise<ToolResult> {
    return this.runTool("pdf.compose.add_code_block", composeBlockPayload(input, {
      code: input.code,
      ...(input.language ? { language: input.language } : {}),
    }));
  }

  async composeAddTable(input: ComposeAddTableInput): Promise<ToolResult> {
    return this.runTool("pdf.compose.add_table", composeBlockPayload(input, {
      columns: input.columns,
      rows: input.rows,
    }));
  }

  async composeAddFigure(input: ComposeAddFigureInput): Promise<ToolResult> {
    return this.runTool("pdf.compose.add_figure", composeBlockPayload(input, {
      image_path: input.imagePath,
      ...(input.caption ? { caption: input.caption } : {}),
    }));
  }

  async composeAddAppendix(input: ComposeAddAppendixInput): Promise<ToolResult> {
    return this.runTool("pdf.compose.add_appendix", composeBlockPayload(input, {
      markdown: input.markdown,
    }));
  }

  async composeAddCitation(input: ComposeAddCitationInput): Promise<ToolResult> {
    return this.runTool("pdf.compose.add_citation", composeBlockPayload(input, {
      source: input.source,
      ...(input.quote ? { quote: input.quote } : {}),
      ...(input.page ? { page: input.page } : {}),
    }));
  }

  async composeAddMediaReference(input: ComposeAddMediaReferenceInput): Promise<ToolResult> {
    return this.runTool("pdf.compose.add_media_reference", composeBlockPayload(input, {
      media_path: input.mediaPath,
      ...(input.mediaKind ? { media_kind: input.mediaKind } : {}),
      ...(input.transcriptExcerpt ? { transcript_excerpt: input.transcriptExcerpt } : {}),
      ...(input.durationSeconds !== undefined ? { duration_seconds: input.durationSeconds } : {}),
      ...(input.chapterCount !== undefined ? { chapter_count: input.chapterCount } : {}),
      ...(input.keyframeCount !== undefined ? { keyframe_count: input.keyframeCount } : {}),
    }));
  }

  async composeAddSlide(input: ComposeAddSlideInput): Promise<ToolResult> {
    return this.runTool("pdf.compose.add_slide", composeBlockPayload(input, {
      ...(input.body && input.body.length > 0 ? { body: input.body } : {}),
      ...(input.subtitle ? { subtitle: input.subtitle } : {}),
      ...(input.code ? { code: input.code } : {}),
      ...(input.table ? { table: input.table } : {}),
      ...(input.imagePath ? { image_path: input.imagePath } : {}),
    }));
  }

  async targetProfiles(input: TargetProfilesInput = {}): Promise<ToolResult> {
    return this.runTool("pdf.target.profiles", {
      ...(input.outputPath ? { output_path: input.outputPath } : {}),
    });
  }

  async selectTargetProfile(input: SelectTargetProfileInput = {}): Promise<ToolResult> {
    return this.runTool("pdf.target.select_profile", {
      ...(input.goal ? { goal: input.goal } : {}),
      ...(input.contextPacket ? { context_packet: input.contextPacket } : {}),
      ...(input.contextPacketPath ? { context_packet_path: input.contextPacketPath } : {}),
      ...(input.preferredProfile ? { preferred_profile: input.preferredProfile } : {}),
      ...(input.profile ? { profile: input.profile } : {}),
      ...(input.outputPath ? { output_path: input.outputPath } : {}),
    });
  }

  async validateTargetProfile(input: ValidateTargetProfileInput = {}): Promise<ToolResult> {
    return this.runTool("pdf.target.validate_profile", {
      ...(input.targetProfile ? { target_profile: input.targetProfile } : {}),
      ...(input.profile ? { profile: input.profile } : {}),
      ...(input.outputPath ? { output_path: input.outputPath } : {}),
    });
  }

  async evidenceCoverageReport(input: EvidenceCoverageReportInput): Promise<ToolResult> {
    return this.runTool("pdf.evidence.coverage_report", {
      ...(input.composition ? { composition: input.composition } : {}),
      ...(input.compositionPath ? { composition_path: input.compositionPath } : {}),
      ...(input.outputPath ? { output_path: input.outputPath } : {}),
    });
  }

  async evidenceMapSources(input: EvidenceMapSourcesInput): Promise<ToolResult> {
    return this.runTool("pdf.evidence.map_sources", {
      ...(input.composition ? { composition: input.composition } : {}),
      ...(input.compositionPath ? { composition_path: input.compositionPath } : {}),
      ...(input.blocks ? { blocks: input.blocks } : {}),
      ...(input.claims ? { claims: input.claims } : {}),
      ...(input.contextPacket ? { context_packet: input.contextPacket } : {}),
      ...(input.contextPacketPath ? { context_packet_path: input.contextPacketPath } : {}),
      ...(input.outputPath ? { output_path: input.outputPath } : {}),
    });
  }

  async contextPacketReport(input: ContextPacketReportInput): Promise<ToolResult> {
    return this.runTool("pdf.evidence.context_packet_report", {
      ...(input.contextPacket ? { context_packet: input.contextPacket } : {}),
      ...(input.contextPacketPath ? { context_packet_path: input.contextPacketPath } : {}),
      output_path: input.outputPath,
      ...(input.reportOutputPath ? { report_output_path: input.reportOutputPath } : {}),
      ...(input.title ? { title: input.title } : {}),
      ...(input.stylePack ? { style_pack: input.stylePack } : {}),
    });
  }

  async exportBundle(input: ExportBundleInput): Promise<ToolResult> {
    return this.runTool("pdf.artifacts.export_bundle", {
      artifact_paths: input.artifactPaths,
      output_path: input.outputPath,
      ...(input.title ? { title: input.title } : {}),
      ...(input.metadata ? { metadata: input.metadata } : {}),
    });
  }

  async verifyBundle(input: VerifyBundleInput): Promise<ToolResult> {
    return this.runTool("pdf.artifacts.verify_bundle", {
      bundle_path: input.bundlePath,
    });
  }

  async patchPlan(input: PatchPlanInput): Promise<ToolResult> {
    return this.runTool("pdf.patch.plan", {
      input_path: input.inputPath,
      operations: input.operations,
      output_path: input.outputPath,
      ...(input.compositionPath ? { composition_path: input.compositionPath } : {}),
      ...(input.layerManifestPath ? { layer_manifest_path: input.layerManifestPath } : {}),
      ...(input.reason ? { reason: input.reason } : {}),
    });
  }

  async patchPreview(input: PatchPreviewInput): Promise<ToolResult> {
    return this.runTool("pdf.patch.preview", {
      ...(input.patchManifest ? { patch_manifest: input.patchManifest } : {}),
      ...(input.patchManifestPath ? { patch_manifest_path: input.patchManifestPath } : {}),
      ...(input.outputPath ? { output_path: input.outputPath } : {}),
    });
  }

  async patchApply(input: PatchApplyInput): Promise<ToolResult> {
    return this.runTool("pdf.patch.apply", {
      ...(input.patchManifest ? { patch_manifest: input.patchManifest } : {}),
      ...(input.patchManifestPath ? { patch_manifest_path: input.patchManifestPath } : {}),
      output_path: input.outputPath,
    });
  }

  async patchVerify(input: PatchVerifyInput): Promise<ToolResult> {
    return this.runTool("pdf.patch.verify", {
      ...(input.patchManifest ? { patch_manifest: input.patchManifest } : {}),
      ...(input.patchManifestPath ? { patch_manifest_path: input.patchManifestPath } : {}),
      patched_path: input.patchedPath,
    });
  }

  async merge(input: MergePdfInput): Promise<ToolResult> {
    return this.runTool("pdf.organize.merge", {
      input_paths: input.inputPaths,
      output_path: input.outputPath,
    });
  }

  async reorderPages(input: ReorderPagesInput): Promise<ToolResult> {
    return this.runTool("pdf.organize.reorder_pages", {
      input_path: input.inputPath,
      order: input.order,
      output_path: input.outputPath,
    });
  }

  async insertBlankPages(input: InsertBlankPagesInput): Promise<ToolResult> {
    return this.runTool("pdf.organize.insert_blank_pages", {
      input_path: input.inputPath,
      after_page: input.afterPage,
      output_path: input.outputPath,
      ...(input.count !== undefined ? { count: input.count } : {}),
    });
  }

  async compress(input: OptimizePdfInput): Promise<ToolResult> {
    return this.runTool("pdf.optimize.compress", {
      input_path: input.inputPath,
      output_path: input.outputPath,
    });
  }

  async repair(input: OptimizePdfInput): Promise<ToolResult> {
    return this.runTool("pdf.optimize.repair", {
      input_path: input.inputPath,
      output_path: input.outputPath,
    });
  }

  async imageToPdf(input: ImageToPdfInput): Promise<ToolResult> {
    return this.runTool("pdf.convert.image_to_pdf", {
      image_paths: input.imagePaths,
      output_path: input.outputPath,
    });
  }

  async watermark(input: WatermarkInput): Promise<ToolResult> {
    return this.runTool("pdf.edit.watermark", {
      input_path: input.inputPath,
      text: input.text,
      output_path: input.outputPath,
      ...(input.pages ? { pages: input.pages } : {}),
      ...(input.fontSize !== undefined ? { font_size: input.fontSize } : {}),
      ...(input.opacity !== undefined ? { opacity: input.opacity } : {}),
      ...(input.angle !== undefined ? { angle: input.angle } : {}),
    });
  }

  async addPageNumbers(input: PageNumbersInput): Promise<ToolResult> {
    return this.runTool("pdf.edit.page_numbers", {
      input_path: input.inputPath,
      output_path: input.outputPath,
      ...(input.pages ? { pages: input.pages } : {}),
      ...(input.template ? { template: input.template } : {}),
      ...(input.fontSize !== undefined ? { font_size: input.fontSize } : {}),
    });
  }

  async createTextPdf(input: CreateTextPdfInput): Promise<ToolResult> {
    return this.runTool("pdf.convert.text_to_pdf", {
      text: input.text,
      output_path: input.outputPath,
      ...(input.title ? { title: input.title } : {}),
    });
  }

  async createMarkdownPdf(input: CreateMarkdownPdfInput): Promise<ToolResult> {
    return this.runTool("pdf.convert.markdown_to_pdf", {
      markdown: input.markdown,
      output_path: input.outputPath,
      ...(input.title ? { title: input.title } : {}),
      ...(input.stylePack ? { style_pack: input.stylePack } : {}),
    });
  }

  async createFromPrompt(input: CreateFromPromptInput): Promise<ToolResult> {
    return this.runTool("pdf.ai.create.from_prompt", {
      prompt: input.prompt,
      output_path: input.outputPath,
      ...(input.template ? { template: input.template } : {}),
      ...(input.stylePack ? { style_pack: input.stylePack } : {}),
      ...(input.colors ? { colors: input.colors } : {}),
      ...(input.data ? { data: input.data } : {}),
      ...(input.title ? { title: input.title } : {}),
    });
  }

  async createTemplates(): Promise<ToolResult> {
    return this.runTool("pdf.ai.create.templates", {});
  }

  async createTemplatePacks(input: CreateTemplatePacksInput = {}): Promise<ToolResult> {
    return this.runTool("pdf.ai.create.template_packs", {
      ...(input.outputPath ? { output_path: input.outputPath } : {}),
    });
  }

  async validateTemplatePack(input: ValidateTemplatePackInput): Promise<ToolResult> {
    return this.runTool("pdf.ai.create.validate_template_pack", {
      ...(input.templatePack ? { template_pack: input.templatePack } : {}),
      ...(input.templatePackPath ? { template_pack_path: input.templatePackPath } : {}),
      ...(input.outputPath ? { output_path: input.outputPath } : {}),
    });
  }

  async planTemplatePack(input: PlanTemplatePackInput): Promise<ToolResult> {
    return this.runTool("pdf.ai.create.plan_template_pack", {
      ...(input.templatePack ? { template_pack: input.templatePack } : {}),
      ...(input.templatePackPath ? { template_pack_path: input.templatePackPath } : {}),
      ...(input.targetProfile ? { target_profile: input.targetProfile } : {}),
      ...(input.profile ? { profile: input.profile } : {}),
      ...(input.contextPacket ? { context_packet: input.contextPacket } : {}),
      ...(input.contextPacketPath ? { context_packet_path: input.contextPacketPath } : {}),
      ...(input.plannedOutputPath ? { planned_output_path: input.plannedOutputPath } : {}),
      ...(input.outputPath ? { output_path: input.outputPath } : {}),
      ...(input.preferredTemplateId ? { preferred_template_id: input.preferredTemplateId } : {}),
      ...(input.preferredColorScheme ? { preferred_color_scheme: input.preferredColorScheme } : {}),
    });
  }

  async createAgent(input: CreateAgentInput): Promise<ToolResult> {
    return this.runTool("pdf.ai.create.agent", {
      ...(input.templatePack ? { template_pack: input.templatePack } : {}),
      ...(input.templatePackPath ? { template_pack_path: input.templatePackPath } : {}),
      ...(input.targetProfile ? { target_profile: input.targetProfile } : {}),
      ...(input.profile ? { profile: input.profile } : {}),
      ...(input.contextPacket ? { context_packet: input.contextPacket } : {}),
      ...(input.contextPacketPath ? { context_packet_path: input.contextPacketPath } : {}),
      output_path: input.outputPath,
      ...(input.planOutputPath ? { plan_output_path: input.planOutputPath } : {}),
      ...(input.coverageOutputPath ? { coverage_output_path: input.coverageOutputPath } : {}),
      ...(input.contextClassificationOutputPath ? { context_classification_output_path: input.contextClassificationOutputPath } : {}),
      ...(input.contextReportOutputPath ? { context_report_output_path: input.contextReportOutputPath } : {}),
      ...(input.contextReportJsonOutputPath ? { context_report_json_output_path: input.contextReportJsonOutputPath } : {}),
      ...(input.bundleOutputPath ? { bundle_output_path: input.bundleOutputPath } : {}),
      ...(input.preferredTemplateId ? { preferred_template_id: input.preferredTemplateId } : {}),
      ...(input.preferredColorScheme ? { preferred_color_scheme: input.preferredColorScheme } : {}),
      ...(input.title ? { title: input.title } : {}),
      ...(input.prompt ? { prompt: input.prompt } : {}),
      ...(input.stylePack ? { style_pack: input.stylePack } : {}),
    });
  }

  async createFromTemplatePack(input: CreateFromTemplatePackInput): Promise<ToolResult> {
    return this.runTool("pdf.ai.create.from_template_pack", {
      ...(input.templatePack ? { template_pack: input.templatePack } : {}),
      ...(input.templatePackPath ? { template_pack_path: input.templatePackPath } : {}),
      template_id: input.templateId,
      output_path: input.outputPath,
      ...(input.colorScheme ? { color_scheme: input.colorScheme } : {}),
      ...(input.data ? { data: input.data } : {}),
      ...(input.contextPacket ? { context_packet: input.contextPacket } : {}),
      ...(input.contextPacketPath ? { context_packet_path: input.contextPacketPath } : {}),
      ...(input.title ? { title: input.title } : {}),
      ...(input.prompt ? { prompt: input.prompt } : {}),
      ...(input.stylePack ? { style_pack: input.stylePack } : {}),
    });
  }

  async createTemplatePreview(input: CreateTemplatePreviewInput): Promise<ToolResult> {
    return this.runTool("pdf.ai.create.template_preview", {
      template: input.template,
      output_path: input.outputPath,
      ...(input.stylePack ? { style_pack: input.stylePack } : {}),
      ...(input.colors ? { colors: input.colors } : {}),
      ...(input.data ? { data: input.data } : {}),
    });
  }

  async validateOutput(input: ValidateOutputInput): Promise<ToolResult> {
    return this.runTool("pdf.validation.validate_output", {
      path: input.path,
      ...(input.expectedPages !== undefined ? { expected_pages: input.expectedPages } : {}),
    });
  }

  async pageCountCheck(input: PageCountCheckInput): Promise<ToolResult> {
    return this.runTool("pdf.validation.page_count_check", {
      path: input.path,
      expected_pages: input.expectedPages,
    });
  }

  async metadataPageInfo(input: MetadataPageInfoInput): Promise<ToolResult> {
    return this.runTool("pdf.metadata.page_info", {
      input_path: input.inputPath,
      ...(input.pages ? { pages: input.pages } : {}),
    });
  }

  async securityRemoveMetadata(input: SecurityRemoveMetadataInput): Promise<ToolResult> {
    return this.runTool("pdf.security.remove_metadata", {
      input_path: input.inputPath,
      output_path: input.outputPath,
    });
  }

  async renderCheck(input: RenderCheckInput): Promise<ToolResult> {
    return this.runTool("pdf.validation.render_check", {
      path: input.path,
      ...(input.pages ? { pages: input.pages } : {}),
    });
  }

  async extractImages(input: ExtractImagesInput): Promise<ToolResult> {
    return this.runTool("pdf.convert.extract_images", {
      input_path: input.inputPath,
      ...(input.pages ? { pages: input.pages } : {}),
      ...(input.outDir ? { out_dir: input.outDir } : {}),
    });
  }

  async blankPageCheck(input: BlankPageCheckInput): Promise<ToolResult> {
    return this.runTool("pdf.validation.blank_page_check", {
      path: input.path,
      ...(input.pages ? { pages: input.pages } : {}),
    });
  }

  async parseLite(input: ParseLiteInput): Promise<ToolResult> {
    return this.runTool("pdf.ai.parse.lite", {
      input_path: input.inputPath,
      ...(input.pages ? { pages: input.pages } : {}),
    });
  }

  async ragIngest(input: RagIngestInput): Promise<ToolResult> {
    return this.runTool("pdf.ai.rag.ingest", {
      input_path: input.inputPath,
      index_path: input.indexPath,
      ...(input.pages ? { pages: input.pages } : {}),
      ...(input.maxChars !== undefined ? { max_chars: input.maxChars } : {}),
      ...(input.overlapChars !== undefined ? { overlap_chars: input.overlapChars } : {}),
    });
  }

  async ragQuery(input: RagQueryInput): Promise<ToolResult> {
    return this.runTool("pdf.ai.rag.query", {
      index_path: input.indexPath,
      query: input.query,
      ...(input.topK !== undefined ? { top_k: input.topK } : {}),
    });
  }

  async ragChat(input: RagChatInput): Promise<ToolResult> {
    return this.runTool("pdf.ai.rag.chat", {
      input_path: input.inputPath,
      question: input.question,
      ...(input.indexPath ? { index_path: input.indexPath } : {}),
      ...(input.reportOutputPath ? { report_output_path: input.reportOutputPath } : {}),
      ...(input.highlightOutputPath ? { highlight_output_path: input.highlightOutputPath } : {}),
      ...(input.pages ? { pages: input.pages } : {}),
      ...(input.topK !== undefined ? { top_k: input.topK } : {}),
      ...(input.maxChars !== undefined ? { max_chars: input.maxChars } : {}),
      ...(input.overlapChars !== undefined ? { overlap_chars: input.overlapChars } : {}),
      ...(input.stylePack ? { style_pack: input.stylePack } : {}),
      ...(input.highlightColor ? { highlight_color: input.highlightColor } : {}),
    });
  }

  async ragSearch(input: RagSearchInput): Promise<ToolResult> {
    return this.runTool("pdf.ai.rag.search", {
      index_path: input.indexPath,
      query: input.query,
      ...(input.topK !== undefined ? { top_k: input.topK } : {}),
    });
  }

  async ragCiteAnswer(input: RagCiteAnswerInput): Promise<ToolResult> {
    return this.runTool("pdf.ai.rag.cite_answer", {
      index_path: input.indexPath,
      answer: input.answer,
      ...(input.topK !== undefined ? { top_k: input.topK } : {}),
    });
  }

  async ragHighlightSources(input: RagHighlightSourcesInput): Promise<ToolResult> {
    return this.runTool("pdf.ai.rag.highlight_sources", {
      index_path: input.indexPath,
      output_path: input.outputPath,
      ...(input.answer ? { answer: input.answer } : {}),
      ...(input.query ? { query: input.query } : {}),
      ...(input.topK !== undefined ? { top_k: input.topK } : {}),
      ...(input.highlightColor ? { highlight_color: input.highlightColor } : {}),
    });
  }

  async ragExportReport(input: RagExportReportInput): Promise<ToolResult> {
    return this.runTool("pdf.ai.rag.export_report", {
      index_path: input.indexPath,
      output_path: input.outputPath,
      question: input.question,
      ...(input.answer ? { answer: input.answer } : {}),
      ...(input.topK !== undefined ? { top_k: input.topK } : {}),
      ...(input.includeCitations !== undefined ? { include_citations: input.includeCitations } : {}),
      ...(input.title ? { title: input.title } : {}),
      ...(input.stylePack ? { style_pack: input.stylePack } : {}),
    });
  }

  async pdfToJson(input: PdfToJsonInput): Promise<ToolResult> {
    return this.runTool("pdf.convert.pdf_to_json", {
      input_path: input.inputPath,
      output_path: input.outputPath,
      ...(input.pages ? { pages: input.pages } : {}),
    });
  }

  async pdfToMarkdown(input: PdfToMarkdownInput): Promise<ToolResult> {
    return this.runTool("pdf.convert.pdf_to_markdown", {
      input_path: input.inputPath,
      output_path: input.outputPath,
      ...(input.pages ? { pages: input.pages } : {}),
    });
  }

  private async getJson<T>(path: string): Promise<T> {
    const response = await this.fetchImpl(this.url(path), {
      headers: { accept: "application/json" },
    });
    return parseJsonResponse<T>(response);
  }

  private async postJson<T>(path: string, payload: JsonObject): Promise<T> {
    const response = await this.fetchImpl(this.url(path), {
      method: "POST",
      headers: {
        accept: "application/json",
        "content-type": "application/json",
      },
      body: JSON.stringify(payload),
    });
    return parseJsonResponse<T>(response);
  }

  private url(path: string): string {
    return `${this.baseUrl}${path}`;
  }
}

function composeBlockPayload(
  input: {
    inputPath: string;
    outputPath: string;
    title: string;
    sourceRefs?: string[];
    blockId?: string;
    targetSlot?: string;
    compositionPath?: string;
    layerManifestPath?: string;
    manifestOutputPath?: string;
  },
  extras: JsonObject,
): JsonObject {
  return {
    input_path: input.inputPath,
    output_path: input.outputPath,
    title: input.title,
    ...extras,
    ...(input.sourceRefs && input.sourceRefs.length > 0 ? { source_refs: input.sourceRefs } : {}),
    ...(input.blockId ? { block_id: input.blockId } : {}),
    ...(input.targetSlot ? { target_slot: input.targetSlot } : {}),
    ...(input.compositionPath ? { composition_path: input.compositionPath } : {}),
    ...(input.layerManifestPath ? { layer_manifest_path: input.layerManifestPath } : {}),
    ...(input.manifestOutputPath ? { manifest_output_path: input.manifestOutputPath } : {}),
  };
}

async function parseJsonResponse<T>(response: Response): Promise<T> {
  const raw = await response.text();
  const body = raw ? (JSON.parse(raw) as unknown) : null;
  if (!response.ok && !isToolResult(body)) {
    throw new AgentPDFHttpError(
      `AgentPDF API request failed with HTTP ${response.status}`,
      response.status,
      body,
    );
  }
  return body as T;
}

function normalizeBaseUrl(baseUrl: string): string {
  return baseUrl.replace(/\/+$/, "");
}

function isToolResult(value: unknown): value is ToolResult {
  if (!value || typeof value !== "object") {
    return false;
  }
  const candidate = value as Partial<ToolResult>;
  return (
    typeof candidate.job_id === "string" &&
    typeof candidate.status === "string" &&
    typeof candidate.tool === "string"
  );
}
