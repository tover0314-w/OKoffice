import type {
  AddMarginInput,
  AuthoringPlanInput,
  BookletInput,
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
  ContextImageAnalyzeInput,
  ContextPacketInput,
  ContextPacketReportInput,
  ContextWebCaptureInput,
  CreateAgentInput,
  CreateHtmlPackageInput,
  DesignTokensInput,
  CreateMarkdownPdfInput,
  CreateFromPromptInput,
  CreateFromTemplatePackInput,
  CreateTemplatePreviewInput,
  CreateTemplatePacksInput,
  CreateTextPdfInput,
  DataProfileInput,
  DeckValidatePresentationInput,
  EvidenceCoverageReportInput,
  EvidenceCiteClaimsInput,
  EvidenceMapSourcesInput,
  ArtifactGraphInput,
  ArtifactManifestInput,
  ArtifactSourceMapInput,
  ExportBundleInput,
  ExtractFontsInput,
  ExtractImagesInput,
  AddShapeInput,
  FormsCreateInput,
  FormsImportDataInput,
  FormsValidateInput,
  FreehandDrawInput,
  HtmlToPdfInput,
  ImageToPdfInput,
  InsertBlankPagesInput,
  IngestContextInput,
  InspectHealthInput,
  InspectDocumentInput,
  InspectPagesInput,
  JsonObject,
  MergePdfInput,
  MetadataPageInfoInput,
  MetadataUpdateOutlineInput,
  NUpInput,
  OcrInput,
  OcrMultilingualInput,
  OcrPdfRewriteInput,
  OcrSearchablePdfInput,
  OcrScanToPdfInput,
  OfficeToPdfInput,
  OfficeWorkersStatusInput,
  OfficeWorkersStatusUsage,
  OptimizePdfInput,
  MarkBboxInput,
  PageNumbersInput,
  PageCountCheckInput,
  PagesReviseInput,
  PagesWriteInput,
  PlanTemplatePackInput,
  RenderHtmlPackageInput,
  RenderHtmlPackageUsage,
  PatchApplyInput,
  PatchPlanInput,
  PatchPreviewInput,
  PatchVerifyInput,
  PdfToMarkdownInput,
  PdfToJsonInput,
  PdfToStructuredInput,
  ParseLiteInput,
  RagChatInput,
  RagCiteAnswerInput,
  RagExportReportInput,
  RagHighlightSourcesInput,
  RagIngestInput,
  RagQueryInput,
  RagSearchInput,
  QaVisualReportInput,
  RenderCheckInput,
  ReorderPagesInput,
  ResizePagesInput,
  ResearchEvidenceCardsInput,
  ResearchPlanInput,
  ResearchSourceCardsInput,
  SecurityAuthorizedPasswordInput,
  SecurityMalwareScanInput,
  SecurityPasswordInput,
  SecurityRedactInput,
  SecurityRemoveMetadataInput,
  SecuritySanitizeInput,
  SecuritySignInput,
  SecurityVerifyRedactionInput,
  SecurityVerifySignatureInput,
  SemanticDiffInput,
  SemanticParseInput,
  SelectTargetProfileInput,
  SetupClaudeCodeInput,
  SetupCodexInput,
  SetupKiloCodeInput,
  SetupOpenClawInput,
  TargetProfilesInput,
  ToolManifest,
  ToolResult,
  ToolSpec,
  ToPdfaInput,
  UnderlayInput,
  UrlToPdfInput,
  ValidateOutputInput,
  ValidatePdfaInput,
  ValidateTemplatePackInput,
  ValidateTargetProfileInput,
  ValidationRedactionCheckInput,
  VersionReportInput,
  VisualDiffInput,
  VerifyBundleInput,
  WatermarkInput,
  WordValidateDocumentInput,
  WorkflowCreatePdfInput,
  WorkflowCreatePdfToolUsage,
  WorkflowPlanInput,
  WorkflowResearchDeckInput,
  WorkflowReportInput,
  WorkflowRunInput,
  StoryboardPlanInput,
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

  async officeWorkersStatus(
    input: OfficeWorkersStatusInput = {},
  ): Promise<ToolResult<OfficeWorkersStatusUsage>> {
    return this.runTool("office.workers.status", {
      ...(input.featureFlags ? { feature_flags: input.featureFlags } : {}),
      ...(input.commandPaths ? { command_paths: input.commandPaths } : {}),
    });
  }

  async deckValidatePresentation(input: DeckValidatePresentationInput): Promise<ToolResult> {
    return this.runTool("deck.validation.presentation", {
      path: input.path,
    });
  }

  async wordValidateDocument(input: WordValidateDocumentInput): Promise<ToolResult> {
    return this.runTool("word.validation.document", {
      path: input.path,
    });
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

  async setupKiloCode(input: SetupKiloCodeInput = {}): Promise<ToolResult> {
    return this.runTool("agent.setup.kilo_code", {
      ...(input.outputPath ? { output_path: input.outputPath } : {}),
      ...(input.safeRoot ? { safe_root: input.safeRoot } : {}),
      ...(input.command ? { command: input.command } : {}),
      ...(input.argsPrefix && input.argsPrefix.length > 0 ? { args_prefix: input.argsPrefix } : {}),
      ...(input.serverName ? { server_name: input.serverName } : {}),
    });
  }

  async setupOpenClaw(input: SetupOpenClawInput = {}): Promise<ToolResult> {
    return this.runTool("agent.setup.openclaw", {
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

  async inspectHealth(input: InspectHealthInput): Promise<ToolResult> {
    return this.runTool("pdf.inspect.health", {
      input_path: input.inputPath,
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

  async workflowCreatePdf(input: WorkflowCreatePdfInput): Promise<ToolResult<WorkflowCreatePdfToolUsage>> {
    return this.runTool<WorkflowCreatePdfToolUsage>("pdf.workflow.createpdf", {
      pdf_output_path: input.pdfOutputPath,
      ...(input.htmlOutputPath ? { html_output_path: input.htmlOutputPath } : {}),
      ...(input.html ? { html: input.html } : {}),
      ...(input.htmlPath ? { html_path: input.htmlPath } : {}),
      ...(input.pageDocument ? { page_document: input.pageDocument } : {}),
      ...(input.contextPacket ? { context_packet: input.contextPacket } : {}),
      ...(input.contextPacketPath ? { context_packet_path: input.contextPacketPath } : {}),
      ...(input.targetProfile ? { target_profile: input.targetProfile } : {}),
      ...(input.stylePack ? { style_pack: input.stylePack } : {}),
      ...(input.title ? { title: input.title } : {}),
      ...(input.artifactDir ? { artifact_dir: input.artifactDir } : {}),
      ...(input.bundleOutputPath ? { bundle_output_path: input.bundleOutputPath } : {}),
      ...(input.rendererBackend ? { renderer_backend: input.rendererBackend } : {}),
      ...(input.expectedPageCount !== undefined ? { expected_page_count: input.expectedPageCount } : {}),
      ...(input.pages ? { pages: input.pages } : {}),
    });
  }

  async workflowResearchDeck(input: WorkflowResearchDeckInput): Promise<ToolResult> {
    return this.runTool("pdf.workflow.research_deck", {
      brief: input.brief,
      ...(input.evidenceCards ? { evidence_cards: input.evidenceCards } : {}),
      ...(input.htmlOutputPath ? { html_output_path: input.htmlOutputPath } : {}),
      ...(input.pdfOutputPath ? { pdf_output_path: input.pdfOutputPath } : {}),
      ...(input.artifactDir ? { artifact_dir: input.artifactDir } : {}),
      ...(input.execute !== undefined ? { execute: input.execute } : {}),
    });
  }

  async authoringPlan(input: AuthoringPlanInput): Promise<ToolResult> {
    return this.runTool("pdf.authoring.plan", {
      brief: input.brief,
    });
  }

  async researchPlan(input: ResearchPlanInput): Promise<ToolResult> {
    return this.runTool("pdf.research.plan", {
      brief: input.brief,
    });
  }

  async researchSourceCards(input: ResearchSourceCardsInput): Promise<ToolResult> {
    return this.runTool("pdf.research.source_cards", {
      sources: input.sources,
      ...(input.brief ? { brief: input.brief } : {}),
    });
  }

  async researchEvidenceCards(input: ResearchEvidenceCardsInput): Promise<ToolResult> {
    return this.runTool("pdf.research.evidence_cards", {
      source_cards: input.sourceCards,
    });
  }

  async designTokens(input: DesignTokensInput): Promise<ToolResult> {
    return this.runTool("pdf.design.tokens", {
      ...(input.theme ? { theme: input.theme } : {}),
      ...(input.overrides ? { overrides: input.overrides } : {}),
    });
  }

  async storyboardPlan(input: StoryboardPlanInput): Promise<ToolResult> {
    return this.runTool("pdf.storyboard.plan", {
      brief: input.brief,
      ...(input.authoringPlan ? { authoring_plan: input.authoringPlan } : {}),
      ...(input.evidenceCards ? { evidence_cards: input.evidenceCards } : {}),
    });
  }

  async pagesWrite(input: PagesWriteInput): Promise<ToolResult> {
    return this.runTool("pdf.pages.write", {
      brief: input.brief,
      storyboard: input.storyboard,
      ...(input.evidenceCards ? { evidence_cards: input.evidenceCards } : {}),
      ...(input.designTokens ? { design_tokens: input.designTokens } : {}),
    });
  }

  async pagesRevise(input: PagesReviseInput): Promise<ToolResult> {
    return this.runTool("pdf.pages.revise", {
      page_document: input.pageDocument,
      ...(input.revisions ? { revisions: input.revisions } : {}),
      ...(input.designTokens ? { design_tokens: input.designTokens } : {}),
    });
  }

  async createHtmlPackage(input: CreateHtmlPackageInput): Promise<ToolResult> {
    return this.runTool("pdf.create.html_package", {
      ...(input.pageDocument ? { page_document: input.pageDocument } : {}),
      ...(input.html ? { html: input.html } : {}),
      ...(input.htmlPath ? { html_path: input.htmlPath } : {}),
      html_output_path: input.htmlOutputPath,
      ...(input.title ? { title: input.title } : {}),
    });
  }

  async qaVisualReport(input: QaVisualReportInput): Promise<ToolResult> {
    return this.runTool("pdf.qa.visual_report", {
      input_path: input.inputPath,
      ...(input.expectedPageCount !== undefined ? { expected_page_count: input.expectedPageCount } : {}),
      ...(input.htmlPackageManifestPath ? { html_package_manifest_path: input.htmlPackageManifestPath } : {}),
      ...(input.pages ? { pages: input.pages } : {}),
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

  async contextWebCapture(input: ContextWebCaptureInput): Promise<ToolResult> {
    return this.runTool("pdf.context.web_capture", {
      url: input.url,
      ...(input.outputPath ? { output_path: input.outputPath } : {}),
      ...(input.label ? { label: input.label } : {}),
      ...(input.role ? { role: input.role } : {}),
      ...(input.contextItemId ? { context_item_id: input.contextItemId } : {}),
      ...(input.maxBytes !== undefined ? { max_bytes: input.maxBytes } : {}),
      ...(input.timeoutSeconds !== undefined ? { timeout_seconds: input.timeoutSeconds } : {}),
      ...(input.allowPrivateHosts !== undefined ? { allow_private_hosts: input.allowPrivateHosts } : {}),
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

  async contextImageAnalyze(input: ContextImageAnalyzeInput): Promise<ToolResult> {
    return this.runTool("pdf.context.image_analyze", {
      input_path: input.inputPath,
      ...(input.languages && input.languages.length > 0 ? { languages: input.languages } : {}),
      ...(input.runOcr !== undefined ? { run_ocr: input.runOcr } : {}),
      ...(input.engine ? { engine: input.engine } : {}),
      ...(input.psm !== undefined ? { psm: input.psm } : {}),
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
      ...(input.renderer ? { renderer: input.renderer } : {}),
      ...(input.htmlOutputPath ? { html_output_path: input.htmlOutputPath } : {}),
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
      ...(input.renderer ? { renderer: input.renderer } : {}),
      ...(input.htmlOutputPath ? { html_output_path: input.htmlOutputPath } : {}),
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

  async evidenceCiteClaims(input: EvidenceCiteClaimsInput): Promise<ToolResult> {
    return this.runTool("pdf.evidence.cite_claims", {
      claims: input.claims,
      ...(input.composition ? { composition: input.composition } : {}),
      ...(input.compositionPath ? { composition_path: input.compositionPath } : {}),
      ...(input.sourceMap ? { source_map: input.sourceMap } : {}),
      ...(input.sourceMapPath ? { source_map_path: input.sourceMapPath } : {}),
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

  async artifactManifest(input: ArtifactManifestInput): Promise<ToolResult> {
    return this.runTool("pdf.artifacts.manifest", {
      artifact_paths: input.artifactPaths,
      ...(input.outputPath ? { output_path: input.outputPath } : {}),
      ...(input.title ? { title: input.title } : {}),
      ...(input.metadata ? { metadata: input.metadata } : {}),
    });
  }

  async artifactGraph(input: ArtifactGraphInput): Promise<ToolResult> {
    return this.runTool("pdf.artifacts.graph", {
      ...(input.artifactManifestPath ? { artifact_manifest_path: input.artifactManifestPath } : {}),
      ...(input.artifactPaths ? { artifact_paths: input.artifactPaths } : {}),
      ...(input.outputPath ? { output_path: input.outputPath } : {}),
      ...(input.title ? { title: input.title } : {}),
    });
  }

  async artifactSourceMap(input: ArtifactSourceMapInput): Promise<ToolResult> {
    return this.runTool("pdf.artifacts.source_map", {
      ...(input.composition ? { composition: input.composition } : {}),
      ...(input.compositionPath ? { composition_path: input.compositionPath } : {}),
      ...(input.sourceMap ? { source_map: input.sourceMap } : {}),
      ...(input.sourceMapPath ? { source_map_path: input.sourceMapPath } : {}),
      ...(input.contextPacket ? { context_packet: input.contextPacket } : {}),
      ...(input.contextPacketPath ? { context_packet_path: input.contextPacketPath } : {}),
      ...(input.artifactManifestPath ? { artifact_manifest_path: input.artifactManifestPath } : {}),
      ...(input.artifactPaths ? { artifact_paths: input.artifactPaths } : {}),
      ...(input.outputPath ? { output_path: input.outputPath } : {}),
      ...(input.title ? { title: input.title } : {}),
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
      ...(input.artifactGraphPath ? { artifact_graph_path: input.artifactGraphPath } : {}),
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

  async nUp(input: NUpInput): Promise<ToolResult> {
    return this.runTool("pdf.organize.n_up", {
      input_path: input.inputPath,
      output_path: input.outputPath,
      ...(input.pages ? { pages: input.pages } : {}),
      ...(input.perSheet !== undefined ? { per_sheet: input.perSheet } : {}),
    });
  }

  async booklet(input: BookletInput): Promise<ToolResult> {
    return this.runTool("pdf.organize.booklet", {
      input_path: input.inputPath,
      output_path: input.outputPath,
      ...(input.pages ? { pages: input.pages } : {}),
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

  async removeUnusedObjects(input: OptimizePdfInput): Promise<ToolResult> {
    return this.runTool("pdf.optimize.remove_unused_objects", {
      input_path: input.inputPath,
      output_path: input.outputPath,
    });
  }

  async subsetFonts(input: OptimizePdfInput): Promise<ToolResult> {
    return this.runTool("pdf.optimize.subset_fonts", {
      input_path: input.inputPath,
      output_path: input.outputPath,
    });
  }

  async validatePdfa(input: ValidatePdfaInput): Promise<ToolResult> {
    return this.runTool("pdf.optimize.validate_pdfa", {
      input_path: input.inputPath,
    });
  }

  async toPdfa(input: ToPdfaInput): Promise<ToolResult> {
    return this.runTool("pdf.optimize.to_pdfa", {
      input_path: input.inputPath,
      output_path: input.outputPath,
      ...(input.profile ? { profile: input.profile } : {}),
    });
  }

  async htmlToPdf(input: HtmlToPdfInput): Promise<ToolResult> {
    return this.runTool("pdf.convert.html_to_pdf", {
      input_path: input.inputPath,
      output_path: input.outputPath,
    });
  }

  async renderHtmlPackage(input: RenderHtmlPackageInput): Promise<ToolResult<RenderHtmlPackageUsage>> {
    return this.runTool("pdf.render.html_package", {
      package_path: input.packagePath,
      output_path: input.outputPath,
      ...(input.rendererBackend ? { renderer_backend: input.rendererBackend } : {}),
    });
  }

  async urlToPdf(input: UrlToPdfInput): Promise<ToolResult> {
    return this.runTool("pdf.convert.url_to_pdf", {
      url: input.url,
      output_path: input.outputPath,
      ...(input.allowPrivateHosts !== undefined
        ? { allow_private_hosts: input.allowPrivateHosts }
        : {}),
      ...(input.allowFileUrls !== undefined ? { allow_file_urls: input.allowFileUrls } : {}),
    });
  }

  async docxToPdf(input: OfficeToPdfInput): Promise<ToolResult> {
    return this.runTool("pdf.convert.docx_to_pdf", officeToPdfPayload(input));
  }

  async pptxToPdf(input: OfficeToPdfInput): Promise<ToolResult> {
    return this.runTool("pdf.convert.pptx_to_pdf", officeToPdfPayload(input));
  }

  async xlsxToPdf(input: OfficeToPdfInput): Promise<ToolResult> {
    return this.runTool("pdf.convert.xlsx_to_pdf", officeToPdfPayload(input));
  }

  async pdfToHtml(input: PdfToStructuredInput): Promise<ToolResult> {
    return this.runTool("pdf.convert.pdf_to_html", pdfToStructuredPayload(input));
  }

  async pdfToDocx(input: PdfToStructuredInput): Promise<ToolResult> {
    return this.runTool("pdf.convert.pdf_to_docx", pdfToStructuredPayload(input));
  }

  async pdfToPptx(input: PdfToStructuredInput): Promise<ToolResult> {
    return this.runTool("pdf.convert.pdf_to_pptx", pdfToStructuredPayload(input));
  }

  async pdfToXlsx(input: PdfToStructuredInput): Promise<ToolResult> {
    return this.runTool("pdf.convert.pdf_to_xlsx", pdfToStructuredPayload(input));
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

  async addShape(input: AddShapeInput): Promise<ToolResult> {
    return this.runTool("pdf.edit.add_shape", {
      input_path: input.inputPath,
      output_path: input.outputPath,
      shape: input.shape,
      page: input.page,
      x: input.x,
      y: input.y,
      width: input.width,
      height: input.height,
      ...(input.strokeColor ? { stroke_color: input.strokeColor } : {}),
      ...(input.fillColor ? { fill_color: input.fillColor } : {}),
      ...(input.lineWidth !== undefined ? { line_width: input.lineWidth } : {}),
      ...(input.opacity !== undefined ? { opacity: input.opacity } : {}),
    });
  }

  async underline(input: MarkBboxInput): Promise<ToolResult> {
    return this.runTool("pdf.edit.underline", markBboxPayload(input));
  }

  async strikeout(input: MarkBboxInput): Promise<ToolResult> {
    return this.runTool("pdf.edit.strikeout", markBboxPayload(input));
  }

  async freehandDraw(input: FreehandDrawInput): Promise<ToolResult> {
    return this.runTool("pdf.edit.freehand_draw", {
      input_path: input.inputPath,
      output_path: input.outputPath,
      page: input.page,
      points: input.points,
      ...(input.strokeColor ? { stroke_color: input.strokeColor } : {}),
      ...(input.lineWidth !== undefined ? { line_width: input.lineWidth } : {}),
      ...(input.opacity !== undefined ? { opacity: input.opacity } : {}),
    });
  }

  async resizePages(input: ResizePagesInput): Promise<ToolResult> {
    return this.runTool("pdf.edit.resize_pages", {
      input_path: input.inputPath,
      output_path: input.outputPath,
      width: input.width,
      height: input.height,
      ...(input.pages ? { pages: input.pages } : {}),
    });
  }

  async addMargin(input: AddMarginInput): Promise<ToolResult> {
    return this.runTool("pdf.edit.add_margin", {
      input_path: input.inputPath,
      output_path: input.outputPath,
      ...(input.margin !== undefined ? { margin: input.margin } : {}),
      ...(input.pages ? { pages: input.pages } : {}),
      ...(input.top !== undefined ? { top: input.top } : {}),
      ...(input.right !== undefined ? { right: input.right } : {}),
      ...(input.bottom !== undefined ? { bottom: input.bottom } : {}),
      ...(input.left !== undefined ? { left: input.left } : {}),
    });
  }

  async underlay(input: UnderlayInput): Promise<ToolResult> {
    return this.runTool("pdf.edit.underlay", {
      input_path: input.inputPath,
      output_path: input.outputPath,
      text: input.text,
      ...(input.pages ? { pages: input.pages } : {}),
      ...(input.fontSize !== undefined ? { font_size: input.fontSize } : {}),
      ...(input.opacity !== undefined ? { opacity: input.opacity } : {}),
      ...(input.angle !== undefined ? { angle: input.angle } : {}),
      ...(input.color ? { color: input.color } : {}),
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
      ...(input.renderer ? { renderer: input.renderer } : {}),
      ...(input.htmlOutputPath ? { html_output_path: input.htmlOutputPath } : {}),
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

  async metadataUpdateOutline(input: MetadataUpdateOutlineInput): Promise<ToolResult> {
    return this.runTool("pdf.metadata.update_outline", {
      input_path: input.inputPath,
      outline: input.outline,
      output_path: input.outputPath,
    });
  }

  async securityRemoveMetadata(input: SecurityRemoveMetadataInput): Promise<ToolResult> {
    return this.runTool("pdf.security.remove_metadata", {
      input_path: input.inputPath,
      output_path: input.outputPath,
    });
  }

  async securitySanitize(input: SecuritySanitizeInput): Promise<ToolResult> {
    return this.runTool("pdf.security.sanitize", {
      input_path: input.inputPath,
      output_path: input.outputPath,
      ...(input.removeMetadata !== undefined ? { remove_metadata: input.removeMetadata } : {}),
    });
  }

  async securityProtect(input: SecurityPasswordInput): Promise<ToolResult> {
    return this.runTool("pdf.security.protect", securityPasswordPayload(input));
  }

  async securityEncrypt(input: SecurityPasswordInput): Promise<ToolResult> {
    return this.runTool("pdf.security.encrypt", securityPasswordPayload(input));
  }

  async securityUnlockAuthorized(input: SecurityAuthorizedPasswordInput): Promise<ToolResult> {
    return this.runTool("pdf.security.unlock_authorized", {
      input_path: input.inputPath,
      output_path: input.outputPath,
      password: input.password,
    });
  }

  async securityDecryptAuthorized(input: SecurityAuthorizedPasswordInput): Promise<ToolResult> {
    return this.runTool("pdf.security.decrypt_authorized", {
      input_path: input.inputPath,
      output_path: input.outputPath,
      password: input.password,
    });
  }

  async securitySign(input: SecuritySignInput): Promise<ToolResult> {
    return this.runTool("pdf.security.sign", {
      input_path: input.inputPath,
      output_path: input.outputPath,
      ...(input.secret ? { secret: input.secret } : {}),
    });
  }

  async securityVerifySignature(input: SecurityVerifySignatureInput): Promise<ToolResult> {
    return this.runTool("pdf.security.verify_signature", {
      input_path: input.inputPath,
      signature_path: input.signaturePath,
      ...(input.secret ? { secret: input.secret } : {}),
    });
  }

  async securityMalwareScan(input: SecurityMalwareScanInput): Promise<ToolResult> {
    return this.runTool("pdf.security.malware_scan", {
      input_path: input.inputPath,
    });
  }

  async securityRedact(input: SecurityRedactInput): Promise<ToolResult> {
    return this.runTool("pdf.security.redact", {
      input_path: input.inputPath,
      output_path: input.outputPath,
      regions: input.regions,
      ...(input.fillColor ? { fill_color: input.fillColor } : {}),
      ...(input.renderScale !== undefined ? { render_scale: input.renderScale } : {}),
    });
  }

  async securityVerifyRedaction(input: SecurityVerifyRedactionInput): Promise<ToolResult> {
    return this.runTool("pdf.security.verify_redaction", {
      input_path: input.inputPath,
      ...(input.searchTerms && input.searchTerms.length > 0
        ? { search_terms: input.searchTerms }
        : {}),
    });
  }

  async validationRedactionCheck(input: ValidationRedactionCheckInput): Promise<ToolResult> {
    return this.runTool("pdf.validation.redaction_check", {
      input_path: input.inputPath,
      ...(input.searchTerms && input.searchTerms.length > 0
        ? { search_terms: input.searchTerms }
        : {}),
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

  async extractFonts(input: ExtractFontsInput): Promise<ToolResult> {
    return this.runTool("pdf.convert.extract_fonts", {
      input_path: input.inputPath,
      ...(input.pages ? { pages: input.pages } : {}),
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

  async semanticDiff(input: SemanticDiffInput): Promise<ToolResult> {
    return this.runTool("pdf.compare.semantic_diff", {
      before_path: input.beforePath,
      after_path: input.afterPath,
      ...(input.pages ? { pages: input.pages } : {}),
    });
  }

  async compareSemanticDiff(input: SemanticDiffInput): Promise<ToolResult> {
    return this.semanticDiff(input);
  }

  async versionReport(input: VersionReportInput): Promise<ToolResult> {
    return this.runTool("pdf.compare.version_report", {
      before_path: input.beforePath,
      after_path: input.afterPath,
      ...(input.outputPath ? { output_path: input.outputPath } : {}),
      ...(input.pages ? { pages: input.pages } : {}),
    });
  }

  async compareVersionReport(input: VersionReportInput): Promise<ToolResult> {
    return this.versionReport(input);
  }

  async visualDiff(input: VisualDiffInput): Promise<ToolResult> {
    return this.runTool("pdf.compare.visual_diff", visualDiffPayload(input));
  }

  async compareVisualDiff(input: VisualDiffInput): Promise<ToolResult> {
    return this.visualDiff(input);
  }

  async validationVisualDiff(input: VisualDiffInput): Promise<ToolResult> {
    return this.runTool("pdf.validation.visual_diff", visualDiffPayload(input));
  }

  async parseFigures(input: SemanticParseInput): Promise<ToolResult> {
    return this.semanticParse("pdf.ai.parse.figures", input);
  }

  async parseFormulas(input: SemanticParseInput): Promise<ToolResult> {
    return this.semanticParse("pdf.ai.parse.formulas", input);
  }

  async parseCharts(input: SemanticParseInput): Promise<ToolResult> {
    return this.semanticParse("pdf.ai.parse.charts", input);
  }

  async parseReferences(input: SemanticParseInput): Promise<ToolResult> {
    return this.semanticParse("pdf.ai.parse.references", input);
  }

  async formsCreate(input: FormsCreateInput): Promise<ToolResult> {
    return this.runTool("pdf.forms.create", {
      output_path: input.outputPath,
      fields: input.fields,
    });
  }

  async formsImportData(input: FormsImportDataInput): Promise<ToolResult> {
    return this.runTool("pdf.forms.import_data", {
      input_path: input.inputPath,
      data: input.data,
      output_path: input.outputPath,
    });
  }

  async formsValidate(input: FormsValidateInput): Promise<ToolResult> {
    return this.runTool("pdf.forms.validate", {
      input_path: input.inputPath,
      ...(input.requiredFields && input.requiredFields.length > 0
        ? { required_fields: input.requiredFields }
        : {}),
    });
  }

  async ocrScanToPdf(input: OcrScanToPdfInput): Promise<ToolResult> {
    return this.runTool("pdf.ocr_scan.scan_to_pdf", {
      image_paths: input.imagePaths,
      output_path: input.outputPath,
    });
  }

  async ocr(input: OcrInput): Promise<ToolResult> {
    return this.runTool("pdf.ocr_scan.ocr", {
      input_path: input.inputPath,
      ...(input.pages ? { pages: input.pages } : {}),
      ...(input.languages && input.languages.length > 0 ? { languages: input.languages } : {}),
      ...(input.dpi !== undefined ? { dpi: input.dpi } : {}),
      ...(input.engine ? { engine: input.engine } : {}),
      ...(input.psm !== undefined ? { psm: input.psm } : {}),
    });
  }

  async ocrSearchablePdf(input: OcrSearchablePdfInput): Promise<ToolResult> {
    return this.runTool("pdf.ocr_scan.searchable_pdf", {
      input_path: input.inputPath,
      output_path: input.outputPath,
      ...(input.pages ? { pages: input.pages } : {}),
      ...(input.languages && input.languages.length > 0 ? { languages: input.languages } : {}),
      ...(input.dpi !== undefined ? { dpi: input.dpi } : {}),
      ...(input.engine ? { engine: input.engine } : {}),
      ...(input.psm !== undefined ? { psm: input.psm } : {}),
    });
  }

  async ocrDespeckle(input: OcrPdfRewriteInput): Promise<ToolResult> {
    return this.runTool("pdf.ocr_scan.despeckle", {
      input_path: input.inputPath,
      output_path: input.outputPath,
    });
  }

  async ocrRemoveExistingOcr(input: OcrPdfRewriteInput): Promise<ToolResult> {
    return this.runTool("pdf.ocr_scan.remove_existing_ocr", {
      input_path: input.inputPath,
      output_path: input.outputPath,
    });
  }

  async ocrMultilingual(input: OcrMultilingualInput): Promise<ToolResult> {
    return this.runTool("pdf.ocr_scan.multilingual_ocr", {
      input_path: input.inputPath,
      output_path: input.outputPath,
      ...(input.languages && input.languages.length > 0 ? { languages: input.languages } : {}),
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

  private async semanticParse(toolName: string, input: SemanticParseInput): Promise<ToolResult> {
    return this.runTool(toolName, {
      input_path: input.inputPath,
      ...(input.pages ? { pages: input.pages } : {}),
    });
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

function markBboxPayload(input: MarkBboxInput): JsonObject {
  return {
    input_path: input.inputPath,
    output_path: input.outputPath,
    page: input.page,
    bbox: input.bbox,
    ...(input.color ? { color: input.color } : {}),
    ...(input.lineWidth !== undefined ? { line_width: input.lineWidth } : {}),
  };
}

function officeToPdfPayload(input: OfficeToPdfInput): JsonObject {
  return {
    input_path: input.inputPath,
    output_path: input.outputPath,
  };
}

function pdfToStructuredPayload(input: PdfToStructuredInput): JsonObject {
  return {
    input_path: input.inputPath,
    output_path: input.outputPath,
    ...(input.pages ? { pages: input.pages } : {}),
  };
}

function securityPasswordPayload(input: SecurityPasswordInput): JsonObject {
  return {
    input_path: input.inputPath,
    output_path: input.outputPath,
    password: input.password,
    ...(input.ownerPassword ? { owner_password: input.ownerPassword } : {}),
  };
}

function visualDiffPayload(input: VisualDiffInput): JsonObject {
  return {
    before_path: input.beforePath,
    after_path: input.afterPath,
    ...(input.pages ? { pages: input.pages } : {}),
    ...(input.maxDifferenceRatio !== undefined
      ? { max_difference_ratio: input.maxDifferenceRatio }
      : {}),
    ...(input.renderScale !== undefined ? { render_scale: input.renderScale } : {}),
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
