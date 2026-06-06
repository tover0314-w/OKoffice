import type {
  Conversation,
  ConversationSummary,
  FileEntry,
  FileInfo,
  LLMConfig,
  MCPStatus,
  PdfPageInfo,
  PreviewData,
  StreamEvent,
  ToolCategory,
  ToolResultDisplay,
  ToolSpec,
  Workflow,
  WorkflowRunResult,
  WorkflowSummary,
} from '../shared/types';

export interface OkofficeAPI {
  chat: {
    sendMessage(conversationId: string, content: string): Promise<void>;
    stopGeneration(conversationId: string): Promise<void>;
    listConversations(): Promise<ConversationSummary[]>;
    getConversation(id: string): Promise<Conversation | null>;
    deleteConversation(id: string): Promise<void>;
    renameConversation(id: string, title: string): Promise<void>;
  };

  tools: {
    list(): Promise<ToolSpec[]>;
    getCategories(): Promise<ToolCategory[]>;
    execute(name: string, args: Record<string, unknown>): Promise<ToolResultDisplay>;
    inspect(name: string): Promise<ToolSpec>;
  };

  files: {
    listDirectory(path: string): Promise<FileEntry[]>;
    readFile(path: string): Promise<Uint8Array>;
    writeFile(path: string, content: Uint8Array): Promise<void>;
    deleteFile(path: string): Promise<void>;
    moveFile(from: string, to: string): Promise<void>;
    selectDirectory(): Promise<string | null>;
    selectFile(
      filters?: Array<{ name: string; extensions: string[] }>,
    ): Promise<string[] | null>;
    getFileInfo(path: string): Promise<FileInfo>;
    watchDirectory(path: string): Promise<void>;
    unwatchDirectory(path: string): Promise<void>;
  };

  preview: {
    renderPdfPage(path: string, page: number, scale: number): Promise<string>;
    getPdfPageInfo(path: string): Promise<PdfPageInfo>;
    extractText(path: string): Promise<string>;
    convertToPreview(path: string): Promise<PreviewData>;
  };

  workflows: {
    list(): Promise<WorkflowSummary[]>;
    get(id: string): Promise<Workflow | null>;
    save(workflow: Workflow): Promise<void>;
    delete(id: string): Promise<void>;
    execute(
      id: string,
      inputs?: Record<string, unknown>,
    ): Promise<WorkflowRunResult>;
  };

  settings: {
    get(key: string): Promise<string | null>;
    set(key: string, value: string): Promise<void>;
    getAll(): Promise<Record<string, string>>;
    getLLMConfig(): Promise<LLMConfig>;
    setLLMConfig(config: LLMConfig): Promise<void>;
  };

  mcp: {
    getStatus(): Promise<MCPStatus>;
    restart(): Promise<void>;
    getServerLog(): Promise<string>;
  };

  app: {
    getVersion(): Promise<string>;
    quit(): Promise<void>;
    openExternal(url: string): Promise<void>;
  };

  onEvent(callback: (event: StreamEvent) => void): () => void;
}
