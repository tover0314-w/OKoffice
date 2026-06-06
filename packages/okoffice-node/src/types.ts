export type JsonObject = Record<string, unknown>;

export type ToolRunStatus = "queued" | "running" | "succeeded" | "failed" | "cancelled";

export interface OKofficeError {
  code: string;
  message: string;
  details?: JsonObject | null;
}

export interface Artifact {
  artifact_id: string;
  path: string;
  mime_type: string;
  size_bytes?: number | null;
  sha256?: string | null;
  source_tool?: string | null;
  page_count?: number | null;
  created_at?: string | null;
  retention_hint?: string | null;
}

export interface ValidationCheck {
  name: string;
  status: "passed" | "failed" | "warning" | "skipped";
  details?: JsonObject;
  message?: string | null;
}

export interface ValidationReport {
  status: "passed" | "failed" | "warning" | "skipped";
  checks: ValidationCheck[];
  page_count?: number | null;
  warnings?: string[];
}

export interface ToolResult<TUsage extends JsonObject = JsonObject> {
  job_id: string;
  status: ToolRunStatus;
  tool: string;
  artifacts: Artifact[];
  validation?: ValidationReport | null;
  warnings: string[];
  usage: TUsage;
  next_recommended_tools: string[];
  data?: JsonObject | null;
  error?: OKofficeError | null;
}

export interface ToolSpec {
  name: string;
  status: string;
  description: string;
  category?: string | null;
  interfaces: string[];
  input_schema?: JsonObject | null;
  output_schema?: JsonObject | null;
  implemented: boolean;
}

export interface ToolManifest {
  manifest_version: string;
  tools: ToolSpec[];
}

export interface SetupClaudeCodeInput {
  outputPath?: string;
  safeRoot?: string;
  command?: string;
  argsPrefix?: string[];
  serverName?: string;
  scope?: "project" | "local" | "user";
}

export interface SetupCodexInput {
  outputPath?: string;
  safeRoot?: string;
  command?: string;
  argsPrefix?: string[];
  serverName?: string;
}

export interface SetupKiloCodeInput {
  outputPath?: string;
  safeRoot?: string;
  command?: string;
  argsPrefix?: string[];
  serverName?: string;
}

export interface SetupOpenClawInput {
  outputPath?: string;
  safeRoot?: string;
  command?: string;
  argsPrefix?: string[];
  serverName?: string;
}

export interface OfficeWorkersStatusInput {
  featureFlags?: Record<string, boolean>;
  commandPaths?: Record<string, string>;
}

export interface DeckValidatePresentationInput {
  path: string;
}

export interface WordValidateDocumentInput {
  path: string;
}

export type OfficeWorkerStatus = "disabled" | "available" | "missing_dependency" | "not_configured";

export interface OfficeWorkersStatusSummary extends JsonObject {
  worker_count: number;
  enabled_count: number;
  available_count: number;
  missing_dependency_count: number;
  cloud_required_count: number;
  default_core_dependency_count: number;
}

export interface OfficeWorkerCheck extends JsonObject {
  name: string;
  status: ValidationCheck["status"];
  path?: string;
  command?: string;
}

export interface OfficeWorkerStatusRecord extends JsonObject {
  worker_id: string;
  label: string;
  category: string;
  enabled: boolean;
  status: OfficeWorkerStatus;
  feature_flag: string;
  command?: string | null;
  executable_path?: string | null;
  install_extra?: string | null;
  cloud_required: boolean;
  default_core_dependency: boolean;
  license_note: string;
  description: string;
  output_evidence: string[];
  checks: OfficeWorkerCheck[];
}

export interface OfficeWorkerContract extends JsonObject {
  worker_id: string;
  label: string;
  category: string;
  feature_flag: string;
  command_name?: string | null;
  install_extra?: string | null;
  default_core_dependency: boolean;
  cloud_required: boolean;
  license_note: string;
  description: string;
  output_evidence: string[];
}

export interface OfficeWorkersFeatureFlagPolicy extends JsonObject {
  default_enabled: boolean;
  source: string;
  cloud_required_by_default: boolean;
}

export interface OfficeWorkersStatusUsage extends JsonObject {
  summary: OfficeWorkersStatusSummary;
  workers: OfficeWorkerStatusRecord[];
  "office.worker_contracts": OfficeWorkerContract[];
  feature_flag_policy: OfficeWorkersFeatureFlagPolicy;
}

export interface InspectDocumentInput {
  path: string;
}

export interface InspectPagesInput {
  inputPath: string;
  pages?: string;
  renderCheck?: boolean;
}

export interface InspectHealthInput {
  inputPath: string;
}

export interface WorkflowPlanInput {
  goal: string;
  inputPath?: string;
}

export interface WorkflowRunInput {
  workflow: JsonObject;
  dryRun?: boolean;
}

export interface WorkflowReportInput {
  workflowRun: JsonObject;
  outputPath?: string;
}

export interface AuthoringBrief extends JsonObject {
  topic?: string;
  goal?: string;
  audience?: string;
  page_count?: number;
  deliverable?: string;
}

export interface EvidenceCard extends JsonObject {
  id?: string;
  claim?: string;
  evidence?: string;
  source_title?: string;
  source_url?: string;
  confidence?: "high" | "medium" | "low";
  usable_for?: string[];
}

export interface SourceCard extends JsonObject {
  id?: string;
  title?: string;
  publisher?: string;
  source_date?: string;
  source_url?: string;
  source_type?: string;
  reliability?: string;
  summary?: string;
  key_points?: string[];
  useful_for?: string[];
  fetch_status?: string;
}

export interface ResearchPlanInput {
  brief: AuthoringBrief;
}

export interface ResearchSourceCardsInput {
  brief?: AuthoringBrief;
  sources: JsonObject[];
}

export interface ResearchEvidenceCardsInput {
  sourceCards: SourceCard[];
}

export interface DesignTokensInput {
  theme?: string;
  overrides?: JsonObject;
}

export interface WorkflowResearchDeckInput {
  brief: AuthoringBrief;
  evidenceCards?: EvidenceCard[];
  htmlOutputPath?: string;
  pdfOutputPath?: string;
  artifactDir?: string;
  execute?: boolean;
}

export interface WorkflowResearchDeckRequest extends WorkflowResearchDeckInput {}

export interface WorkflowCreatePdfInput {
  pdfOutputPath: string;
  htmlOutputPath?: string;
  html?: string;
  htmlPath?: string;
  pageDocument?: JsonObject;
  contextPacket?: JsonObject;
  contextPacketPath?: string;
  targetProfile?: JsonObject | string;
  stylePack?: string;
  title?: string;
  artifactDir?: string;
  bundleOutputPath?: string;
  rendererBackend?: "auto" | "local_html_package_fallback" | "browser_chromium" | string;
  expectedPageCount?: number;
  pages?: string;
}

export interface WorkflowCreatePdfAuditSummary extends JsonObject {
  artifact_count?: number;
  source_ref_count?: number;
  html_package_count?: number;
  html_render_profile_count?: number;
  renderer_backend_count?: number;
  html_layer_count?: number;
  context_packet_count?: number;
  source_graph_node_count?: number;
  source_graph_edge_count?: number;
  node_count?: number;
  edge_count?: number;
}

export interface WorkflowCreatePdfRenderProfileRef extends JsonObject {
  html_package_id?: string;
  path?: string;
  html_path?: string;
  renderer_contract?: string;
  render_profile_id: string;
  render_profile?: JsonObject;
  renderer_constraints?: JsonObject;
  page_size?: string;
  prefer_css_page_size?: boolean;
  print_background?: boolean;
  javascript_enabled?: boolean;
  remote_assets_enabled?: boolean;
}

export interface WorkflowCreatePdfHtmlLayerRef extends JsonObject {
  html_package_id?: string;
  path?: string;
  html_path?: string;
  layer_id: string;
  block_id?: string;
  block_type?: string;
  target_slot?: string;
  source_refs?: string[];
  anchor?: JsonObject;
  bbox_precision?: string;
  edit_policy?: JsonObject;
}

export interface WorkflowCreatePdfRendererBackendRef extends JsonObject {
  html_package_id?: string;
  path?: string;
  html_path?: string;
  renderer_contract?: string;
  backend_id: string;
  renderer_backend?: RenderHtmlPackageRendererBackend;
  engine?: string;
  source?: string;
  is_browser_renderer?: boolean;
  fallback?: boolean;
  fallback_reason?: string | null;
  layout_fidelity?: string;
  network?: string;
  javascript?: string;
  file_urls?: string;
}

export interface WorkflowCreatePdfStep extends JsonObject {
  tool: string;
  job_id?: string;
  status?: string;
  validation_status?: string | null;
  artifact_paths?: string[];
  warning_count?: number;
  renderer_backend_id?: string | null;
  render_skipped?: boolean;
}

export interface WorkflowCreatePdfUsage extends JsonObject {
  workflow_id?: string;
  mode?: "html_first" | "context_packet" | string;
  source_format?: "raw_html" | "page_document" | "context_packet" | string;
  context_packet_id?: string;
  context_packet_path?: string | null;
  target_profile?: JsonObject;
  renderer?: string;
  html_output_path: string;
  html_package_manifest_path: string;
  composition_path?: string;
  pdf_output_path: string;
  qa_report_path: string;
  artifact_manifest_path: string;
  artifact_graph_path: string;
  requested_renderer_backend?: string;
  renderer_backend: RenderHtmlPackageRendererBackend;
  render_skipped: boolean;
  render_skip_reason?: string | null;
  artifact_manifest_summary: WorkflowCreatePdfAuditSummary;
  artifact_graph_summary: WorkflowCreatePdfAuditSummary;
  html_render_profile_count: number;
  html_render_profile_refs: WorkflowCreatePdfRenderProfileRef[];
  renderer_backend_count: number;
  renderer_backend_refs: WorkflowCreatePdfRendererBackendRef[];
  html_layer_count: number;
  html_layer_refs: WorkflowCreatePdfHtmlLayerRef[];
  source_graph_node_count: number;
  source_graph_edge_count: number;
  bundle_path?: string;
  bundle_export?: ToolResult;
  bundle_verification?: ToolResult;
  steps: WorkflowCreatePdfStep[];
}

export interface WorkflowCreatePdfToolUsage extends JsonObject {
  createpdf: WorkflowCreatePdfUsage;
}

export interface AuthoringPlanInput {
  brief: AuthoringBrief;
}

export interface StoryboardPlanInput {
  brief: AuthoringBrief;
  authoringPlan?: JsonObject;
  evidenceCards?: EvidenceCard[];
}

export interface PagesWriteInput {
  brief: AuthoringBrief;
  storyboard: JsonObject;
  evidenceCards?: EvidenceCard[];
  designTokens?: JsonObject;
}

export interface PagesReviseInput {
  pageDocument: JsonObject;
  revisions?: JsonObject[];
  designTokens?: JsonObject;
}

export interface CreateHtmlPackageInput {
  pageDocument?: JsonObject;
  html?: string;
  htmlPath?: string;
  htmlOutputPath: string;
  title?: string;
}

export interface QaVisualReportInput {
  inputPath: string;
  expectedPageCount?: number;
  htmlPackageManifestPath?: string;
  pages?: string;
}

export interface BuildContextPacketInput {
  contextItems: JsonObject[];
  outputPath: string;
  title?: string;
  intent?: string;
}

export interface IngestContextInput {
  contextItem: JsonObject;
  outputPath?: string;
}

export interface ContextWebCaptureInput {
  url: string;
  outputPath?: string;
  label?: string;
  role?: string;
  contextItemId?: string;
  maxBytes?: number;
  timeoutSeconds?: number;
  allowPrivateHosts?: boolean;
}

export interface ContextPacketInput {
  contextItems: JsonObject[];
  outputPath: string;
  title?: string;
  intent?: string;
}

export interface ClassifyContextInput {
  contextPacket?: JsonObject;
  contextPacketPath?: string;
  targetProfile?: JsonObject | string;
  profile?: string;
  outputPath?: string;
}

export interface ContextImageAnalyzeInput {
  inputPath: string;
  languages?: string[];
  runOcr?: boolean;
  engine?: string;
  psm?: number;
}

export interface CodeSnapshotInput {
  path: string;
  outputPath?: string;
  label?: string;
  role?: string;
  contextItemId?: string;
  lineStart?: number;
  lineEnd?: number;
  repositoryRoot?: string;
  includeDependencies?: boolean;
}

export interface DataProfileInput {
  path: string;
  outputPath?: string;
  label?: string;
  role?: string;
  contextItemId?: string;
  sheet?: string;
  maxRows?: number;
}

export interface ComposeFromContextInput {
  contextPacket?: JsonObject;
  contextPacketPath?: string;
  targetProfile?: JsonObject | string;
  profile?: string;
  outputPath: string;
  stylePack?: string;
  title?: string;
  renderer?: "markdown" | "html" | string;
  htmlOutputPath?: string;
}

export interface ComposePlanInput {
  contextPacket?: JsonObject;
  contextPacketPath?: string;
  targetProfile?: JsonObject | string;
  profile?: string;
  outputPath?: string;
  stylePack?: string;
  title?: string;
}

export interface ComposeRenderIrInput {
  composition?: JsonObject;
  compositionPath?: string;
  outputPath: string;
  stylePack?: string;
  title?: string;
  renderer?: string;
  htmlOutputPath?: string;
}

export interface ComposeBlockInputBase {
  inputPath: string;
  outputPath: string;
  title: string;
  sourceRefs?: string[];
  blockId?: string;
  targetSlot?: string;
  compositionPath?: string;
  layerManifestPath?: string;
  manifestOutputPath?: string;
}

export interface ComposeAddCodeBlockInput extends ComposeBlockInputBase {
  code: string;
  language?: string;
}

export interface ComposeAddTableInput extends ComposeBlockInputBase {
  columns: string[];
  rows: string[][];
}

export interface ComposeAddFigureInput extends ComposeBlockInputBase {
  imagePath: string;
  caption?: string;
}

export interface ComposeAddAppendixInput extends ComposeBlockInputBase {
  markdown: string;
}

export interface ComposeAddCitationInput extends ComposeBlockInputBase {
  source: string;
  quote?: string;
  page?: string;
}

export interface ComposeAddMediaReferenceInput extends ComposeBlockInputBase {
  mediaPath: string;
  mediaKind?: "audio" | "video" | "media" | string;
  transcriptExcerpt?: string;
  durationSeconds?: number;
  chapterCount?: number;
  keyframeCount?: number;
}

export interface ComposeAddSlideInput extends ComposeBlockInputBase {
  body?: string[];
  subtitle?: string;
  code?: string;
  table?: JsonObject;
  imagePath?: string;
}

export interface TargetProfilesInput {
  outputPath?: string;
}

export interface SelectTargetProfileInput {
  goal?: string;
  contextPacket?: JsonObject | string;
  contextPacketPath?: string;
  preferredProfile?: string;
  profile?: string;
  outputPath?: string;
}

export interface ValidateTargetProfileInput {
  targetProfile?: JsonObject | string;
  profile?: string;
  outputPath?: string;
}

export interface EvidenceCoverageReportInput {
  composition?: JsonObject;
  compositionPath?: string;
  outputPath?: string;
}

export interface EvidenceMapSourcesInput {
  composition?: JsonObject;
  compositionPath?: string;
  blocks?: JsonObject[];
  claims?: JsonObject[];
  contextPacket?: JsonObject | string;
  contextPacketPath?: string;
  outputPath?: string;
}

export interface EvidenceCiteClaimsInput {
  claims: JsonObject[];
  composition?: JsonObject;
  compositionPath?: string;
  sourceMap?: JsonObject | JsonObject[];
  sourceMapPath?: string;
  contextPacket?: JsonObject | string;
  contextPacketPath?: string;
  outputPath?: string;
}

export interface ContextPacketReportInput {
  contextPacket?: JsonObject;
  contextPacketPath?: string;
  outputPath: string;
  reportOutputPath?: string;
  title?: string;
  stylePack?: string;
}

export interface ExportBundleInput {
  artifactPaths: string[];
  outputPath: string;
  title?: string;
  metadata?: JsonObject;
}

export interface ArtifactManifestInput {
  artifactPaths: string[];
  outputPath?: string;
  title?: string;
  metadata?: JsonObject;
}

export interface ArtifactGraphInput {
  artifactManifestPath?: string;
  artifactPaths?: string[];
  outputPath?: string;
  title?: string;
}

export interface ArtifactSourceMapInput {
  composition?: JsonObject;
  compositionPath?: string;
  sourceMap?: JsonObject | JsonObject[];
  sourceMapPath?: string;
  contextPacket?: JsonObject;
  contextPacketPath?: string;
  artifactManifestPath?: string;
  artifactPaths?: string[];
  outputPath?: string;
  title?: string;
}

export interface VerifyBundleInput {
  bundlePath: string;
}

export interface PatchPlanInput {
  inputPath: string;
  operations: JsonObject[];
  outputPath: string;
  compositionPath?: string;
  layerManifestPath?: string;
  artifactGraphPath?: string;
  reason?: string;
}

export interface PatchPreviewInput {
  patchManifest?: JsonObject;
  patchManifestPath?: string;
  outputPath?: string;
}

export interface PatchApplyInput {
  patchManifest?: JsonObject;
  patchManifestPath?: string;
  outputPath: string;
}

export interface PatchVerifyInput {
  patchManifest?: JsonObject;
  patchManifestPath?: string;
  patchedPath: string;
}

export interface MergePdfInput {
  inputPaths: string[];
  outputPath: string;
}

export interface ReorderPagesInput {
  inputPath: string;
  order: string;
  outputPath: string;
}

export interface InsertBlankPagesInput {
  inputPath: string;
  afterPage: number;
  outputPath: string;
  count?: number;
}

export interface NUpInput {
  inputPath: string;
  outputPath: string;
  pages?: string;
  perSheet?: number;
}

export interface BookletInput {
  inputPath: string;
  outputPath: string;
  pages?: string;
}

export interface OptimizePdfInput {
  inputPath: string;
  outputPath: string;
}

export interface ToPdfaInput extends OptimizePdfInput {
  profile?: string;
}

export interface ValidatePdfaInput {
  inputPath: string;
}

export interface HtmlToPdfInput {
  inputPath: string;
  outputPath: string;
}

export interface RenderHtmlPackageInput {
  packagePath: string;
  outputPath: string;
  rendererBackend?: "auto" | "local_html_package_fallback" | "browser_chromium" | string;
}

export interface RenderHtmlPackageRendererBackend extends JsonObject {
  backend_id: string;
  engine: string;
  source: string;
  is_browser_renderer: boolean;
  fallback: boolean;
  available?: boolean;
  fallback_reason?: string | null;
  missing_optional_dependency?: string | null;
  install_extra?: string | null;
  layout_fidelity: string;
  network: string;
  javascript: string;
  file_urls: string;
}

export interface RenderHtmlPackageUsage extends JsonObject {
  renderer: string;
  requested_renderer_backend?: string;
  renderer_backend: RenderHtmlPackageRendererBackend;
  input: string;
  html_path: string;
  output: string;
  render_skipped: boolean;
  render_skip_reason?: string | null;
  render_profile: JsonObject;
  renderer_constraints: JsonObject;
  html_package_manifest: JsonObject;
  html_package_validation: JsonObject;
}

export interface UrlToPdfInput {
  url: string;
  outputPath: string;
  allowPrivateHosts?: boolean;
  allowFileUrls?: boolean;
}

export interface OfficeToPdfInput {
  inputPath: string;
  outputPath: string;
}

export interface PdfToStructuredInput {
  inputPath: string;
  outputPath: string;
  pages?: string;
}

export interface ImageToPdfInput {
  imagePaths: string[];
  outputPath: string;
}

export interface WatermarkInput {
  inputPath: string;
  text: string;
  outputPath: string;
  pages?: string;
  fontSize?: number;
  opacity?: number;
  angle?: number;
}

export interface PageNumbersInput {
  inputPath: string;
  outputPath: string;
  pages?: string;
  template?: string;
  fontSize?: number;
}

export interface AddShapeInput {
  inputPath: string;
  outputPath: string;
  shape: "rectangle" | "line" | "circle" | "ellipse" | string;
  page: number;
  x: number;
  y: number;
  width: number;
  height: number;
  strokeColor?: string;
  fillColor?: string;
  lineWidth?: number;
  opacity?: number;
}

export interface MarkBboxInput {
  inputPath: string;
  outputPath: string;
  page: number;
  bbox: number[];
  color?: string;
  lineWidth?: number;
}

export interface FreehandDrawInput {
  inputPath: string;
  outputPath: string;
  page: number;
  points: number[][];
  strokeColor?: string;
  lineWidth?: number;
  opacity?: number;
}

export interface ResizePagesInput {
  inputPath: string;
  outputPath: string;
  width: number;
  height: number;
  pages?: string;
}

export interface AddMarginInput {
  inputPath: string;
  outputPath: string;
  margin?: number;
  pages?: string;
  top?: number;
  right?: number;
  bottom?: number;
  left?: number;
}

export interface UnderlayInput {
  inputPath: string;
  outputPath: string;
  text: string;
  pages?: string;
  fontSize?: number;
  opacity?: number;
  angle?: number;
  color?: string;
}

export interface CreateTextPdfInput {
  text: string;
  outputPath: string;
  title?: string;
}

export interface CreateMarkdownPdfInput {
  markdown: string;
  outputPath: string;
  title?: string;
  stylePack?: string;
}

export interface CreateFromPromptInput {
  prompt: string;
  outputPath: string;
  template?: string;
  stylePack?: string;
  colors?: Record<string, string>;
  data?: JsonObject;
  title?: string;
}

export interface CreateTemplatePreviewInput {
  template: string;
  outputPath: string;
  stylePack?: string;
  colors?: Record<string, string>;
  data?: JsonObject;
}

export interface CreateTemplatePacksInput {
  outputPath?: string;
}

export interface ValidateTemplatePackInput {
  templatePack?: JsonObject | string;
  templatePackPath?: string;
  outputPath?: string;
}

export interface PlanTemplatePackInput {
  templatePack?: JsonObject | string;
  templatePackPath?: string;
  targetProfile?: JsonObject | string;
  profile?: string;
  contextPacket?: JsonObject | string;
  contextPacketPath?: string;
  plannedOutputPath?: string;
  outputPath?: string;
  preferredTemplateId?: string;
  preferredColorScheme?: string;
}

export interface CreateAgentInput {
  templatePack?: JsonObject | string;
  templatePackPath?: string;
  targetProfile?: JsonObject | string;
  profile?: string;
  contextPacket?: JsonObject | string;
  contextPacketPath?: string;
  outputPath: string;
  planOutputPath?: string;
  coverageOutputPath?: string;
  contextClassificationOutputPath?: string;
  contextReportOutputPath?: string;
  contextReportJsonOutputPath?: string;
  bundleOutputPath?: string;
  preferredTemplateId?: string;
  preferredColorScheme?: string;
  title?: string;
  prompt?: string;
  stylePack?: string;
}

export interface CreateFromTemplatePackInput {
  templatePack?: JsonObject | string;
  templatePackPath?: string;
  templateId: string;
  outputPath: string;
  colorScheme?: string;
  data?: JsonObject;
  contextPacket?: JsonObject | string;
  contextPacketPath?: string;
  title?: string;
  prompt?: string;
  stylePack?: string;
  renderer?: "markdown" | "html" | string;
  htmlOutputPath?: string;
}

export interface ValidateOutputInput {
  path: string;
  expectedPages?: number;
}

export interface PageCountCheckInput {
  path: string;
  expectedPages: number;
}

export interface RenderCheckInput {
  path: string;
  pages?: string;
}

export interface MetadataPageInfoInput {
  inputPath: string;
  pages?: string;
}

export interface MetadataUpdateOutlineInput {
  inputPath: string;
  outline: JsonObject[];
  outputPath: string;
}

export interface SecurityRemoveMetadataInput {
  inputPath: string;
  outputPath: string;
}

export interface SecuritySanitizeInput {
  inputPath: string;
  outputPath: string;
  removeMetadata?: boolean;
}

export interface SecurityPasswordInput {
  inputPath: string;
  outputPath: string;
  password: string;
  ownerPassword?: string;
}

export interface SecurityAuthorizedPasswordInput {
  inputPath: string;
  outputPath: string;
  password: string;
}

export interface SecuritySignInput {
  inputPath: string;
  outputPath: string;
  secret?: string;
}

export interface SecurityVerifySignatureInput {
  inputPath: string;
  signaturePath: string;
  secret?: string;
}

export interface SecurityMalwareScanInput {
  inputPath: string;
}

export interface RedactionRegion {
  page: number;
  bbox: [number, number, number, number] | number[];
  label?: string;
}

export interface SecurityRedactInput {
  inputPath: string;
  outputPath: string;
  regions: RedactionRegion[];
  fillColor?: string;
  renderScale?: number;
}

export interface SecurityVerifyRedactionInput {
  inputPath: string;
  searchTerms?: string[];
}

export type ValidationRedactionCheckInput = SecurityVerifyRedactionInput;

export interface ExtractImagesInput {
  inputPath: string;
  pages?: string;
  outDir?: string;
}

export interface ExtractFontsInput {
  inputPath: string;
  pages?: string;
}

export interface BlankPageCheckInput {
  path: string;
  pages?: string;
}

export interface ParseLiteInput {
  inputPath: string;
  pages?: string;
}

export interface SemanticDiffInput {
  beforePath: string;
  afterPath: string;
  pages?: string;
}

export interface VisualDiffInput extends SemanticDiffInput {
  maxDifferenceRatio?: number;
  renderScale?: number;
}

export interface VersionReportInput extends SemanticDiffInput {
  outputPath?: string;
}

export interface SemanticParseInput {
  inputPath: string;
  pages?: string;
}

export interface FormsCreateInput {
  outputPath: string;
  fields: JsonObject[];
}

export interface FormsImportDataInput {
  inputPath: string;
  data: JsonObject;
  outputPath: string;
}

export interface FormsValidateInput {
  inputPath: string;
  requiredFields?: string[];
}

export interface OcrScanToPdfInput {
  imagePaths: string[];
  outputPath: string;
}

export interface OcrInput {
  inputPath: string;
  pages?: string;
  languages?: string[];
  dpi?: number;
  engine?: string;
  psm?: number;
}

export interface OcrSearchablePdfInput extends OcrInput {
  outputPath: string;
}

export interface OcrPdfRewriteInput {
  inputPath: string;
  outputPath: string;
}

export interface OcrMultilingualInput extends OcrPdfRewriteInput {
  languages?: string[];
}

export interface RagIngestInput {
  inputPath: string;
  indexPath: string;
  pages?: string;
  maxChars?: number;
  overlapChars?: number;
}

export interface RagQueryInput {
  indexPath: string;
  query: string;
  topK?: number;
}

export interface RagChatInput {
  inputPath: string;
  question: string;
  indexPath?: string;
  reportOutputPath?: string;
  highlightOutputPath?: string;
  pages?: string;
  topK?: number;
  maxChars?: number;
  overlapChars?: number;
  stylePack?: string;
  highlightColor?: string;
}

export interface RagSearchInput {
  indexPath: string;
  query: string;
  topK?: number;
}

export interface RagCiteAnswerInput {
  indexPath: string;
  answer: string;
  topK?: number;
}

export interface RagHighlightSourcesInput {
  indexPath: string;
  outputPath: string;
  answer?: string;
  query?: string;
  topK?: number;
  highlightColor?: string;
}

export interface RagExportReportInput {
  indexPath: string;
  outputPath: string;
  question: string;
  answer?: string;
  topK?: number;
  includeCitations?: boolean;
  title?: string;
  stylePack?: string;
}

/** @deprecated Use OKofficeError */
export type AgentPDFError = OKofficeError;

export interface PdfToJsonInput {
  inputPath: string;
  outputPath: string;
  pages?: string;
}

export interface PdfToMarkdownInput {
  inputPath: string;
  outputPath: string;
  pages?: string;
}
