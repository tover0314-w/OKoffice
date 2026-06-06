import { ipcMain, app, shell as electronShell, dialog } from 'electron';
import { readdir, stat } from 'fs/promises';
import { join, extname } from 'path';
import { IPC_CHANNELS } from '@shared/constants';
import type { MCPStatus, ToolResultDisplay, Message } from '@shared/types';
import type { McpClient } from './mcp/client';
import type { ToolRegistry } from './mcp/tool-registry';
import type { ToolRunner } from './mcp/tool-runner';
import type { WsBroadcaster } from './services/websocket-server';
import type { ConversationStore } from './db/conversation-store';
import type { SettingsStore } from './db/settings-store';
import type { WorkflowStore } from './db/workflow-store';
import type { LLMProvider } from './llm/provider';
import { ToolCallLoop } from './llm/tool-call-loop';
import { MessageFormatter } from './llm/message-formatter';

export interface IpcDependencies {
  mcpClient: McpClient;
  toolRegistry: ToolRegistry;
  toolRunner: ToolRunner;
  conversationStore: ConversationStore;
  settingsStore: SettingsStore;
  workflowStore: WorkflowStore;
  db: unknown;
  wsServer: WsBroadcaster;
}

let activeLoop: ToolCallLoop | null = null;

function createLLMProvider(config: {
  provider: string;
  apiKey: string;
  model: string;
  baseUrl?: string;
}): LLMProvider {
  switch (config.provider) {
    case 'anthropic': {
      const { AnthropicProvider } = require('./llm/anthropic-provider');
      return new AnthropicProvider(config.apiKey, config.model, config.baseUrl);
    }
    case 'ollama': {
      const { OllamaProvider } = require('./llm/ollama-provider');
      return new OllamaProvider(config.apiKey, config.model, config.baseUrl);
    }
    default: {
      const { OpenAIProvider } = require('./llm/openai-provider');
      return new OpenAIProvider(config.apiKey, config.model, config.baseUrl);
    }
  }
}

export function registerIpcHandlers(deps: IpcDependencies): void {
  const {
    mcpClient,
    toolRegistry,
    toolRunner,
    conversationStore,
    settingsStore,
    workflowStore,
    wsServer,
  } = deps;

  // ── Chat ──────────────────────────────────────────────────────────────

  ipcMain.handle(IPC_CHANNELS.CHAT_LIST_CONVERSATIONS, async () => {
    return conversationStore.list();
  });

  ipcMain.handle(IPC_CHANNELS.CHAT_GET_CONVERSATION, async (_event, id: string) => {
    return conversationStore.getById(id);
  });

  ipcMain.handle(IPC_CHANNELS.CHAT_DELETE_CONVERSATION, async (_event, id: string) => {
    return conversationStore.delete(id);
  });

  ipcMain.handle(IPC_CHANNELS.CHAT_RENAME_CONVERSATION, async (_event, id: string, title: string) => {
    return conversationStore.updateTitle(id, title);
  });

  ipcMain.handle(IPC_CHANNELS.CHAT_SEND_MESSAGE, async (_event, conversationId: string, content: string) => {
    const conversation = conversationStore.getById(conversationId);
    if (!conversation) {
      throw new Error(`Conversation not found: ${conversationId}`);
    }

    const userMessage: Message = {
      id: crypto.randomUUID(),
      conversationId,
      role: 'user',
      content,
      artifacts: [],
      createdAt: new Date().toISOString(),
    };
    conversationStore.addMessage(conversationId, userMessage);

    const llmConfig = settingsStore.getLLMConfig();
    const provider = createLLMProvider(llmConfig);
    const formatter = new MessageFormatter();

    const loop = new ToolCallLoop(
      provider,
      {
        async getToolDefinitions() {
          return toolRegistry.getFunctionCallingFormat();
        },
        async executeTool(name: string, args: Record<string, unknown>) {
          return toolRunner.execute(name, args);
        },
      },
      conversationStore,
      {
        broadcast(event: string, data: unknown) {
          wsServer.emit({
            type: event as any,
            ...((typeof data === 'object' && data !== null) ? data : {}),
          });
        },
      },
      formatter,
    );

    activeLoop = loop;

    loop.run(conversationId).catch((err) => {
      console.error('ToolCallLoop error:', err);
      wsServer.emit({
        type: 'llm:stream_done',
        conversationId,
      });
    }).finally(() => {
      if (activeLoop === loop) {
        activeLoop = null;
      }
    });

    return { acknowledged: true };
  });

  ipcMain.handle(IPC_CHANNELS.CHAT_STOP_GENERATION, async () => {
    if (activeLoop) {
      activeLoop.stop();
      activeLoop = null;
    }
    return { stopped: true };
  });

  // ── Tools ─────────────────────────────────────────────────────────────

  ipcMain.handle(IPC_CHANNELS.TOOLS_LIST, async () => {
    return toolRegistry.getAllTools();
  });

  ipcMain.handle(IPC_CHANNELS.TOOLS_GET_CATEGORIES, async () => {
    return toolRegistry.getCategories();
  });

  ipcMain.handle(IPC_CHANNELS.TOOLS_EXECUTE, async (_event, toolName: string, args: Record<string, unknown>) => {
    return toolRunner.execute(toolName, args);
  });

  ipcMain.handle(IPC_CHANNELS.TOOLS_INSPECT, async (_event, toolName: string) => {
    return toolRegistry.findTool(toolName) ?? null;
  });

  // ── Files ─────────────────────────────────────────────────────────────

  ipcMain.handle(IPC_CHANNELS.FILES_LIST_DIRECTORY, async (_event, dirPath: string) => {
    const entries = await readdir(dirPath, { withFileTypes: true });
    const results = await Promise.all(
      entries.map(async (entry) => {
        const fullPath = join(dirPath, entry.name);
        try {
          const stats = await stat(fullPath);
          return {
            name: entry.name,
            path: fullPath,
            isDirectory: entry.isDirectory(),
            size: stats.size,
            modifiedAt: stats.mtime.toISOString(),
          };
        } catch {
          return null;
        }
      }),
    );
    return results.filter(Boolean);
  });

  ipcMain.handle(IPC_CHANNELS.FILES_READ, async (_event, filePath: string) => {
    const { readFile } = await import('fs/promises');
    const buffer = await readFile(filePath);
    return buffer.toString('base64');
  });

  ipcMain.handle(IPC_CHANNELS.FILES_WRITE, async (_event, filePath: string, content: string) => {
    const { writeFile } = await import('fs/promises');
    const buffer = Buffer.from(content, 'base64');
    await writeFile(filePath, buffer);
    return { written: true };
  });

  ipcMain.handle(IPC_CHANNELS.FILES_DELETE, async (_event, filePath: string) => {
    const { unlink } = await import('fs/promises');
    await unlink(filePath);
    return { deleted: true };
  });

  ipcMain.handle(IPC_CHANNELS.FILES_MOVE, async (_event, oldPath: string, newPath: string) => {
    const { rename } = await import('fs/promises');
    await rename(oldPath, newPath);
    return { moved: true };
  });

  ipcMain.handle(IPC_CHANNELS.FILES_SELECT_DIRECTORY, async () => {
    const result = await dialog.showOpenDialog({ properties: ['openDirectory'] });
    return result.canceled ? null : result.filePaths[0] ?? null;
  });

  ipcMain.handle(IPC_CHANNELS.FILES_SELECT_FILE, async (_event, filters?: Array<{ name: string; extensions: string[] }>) => {
    const result = await dialog.showOpenDialog({
      properties: ['openFile', 'multiSelections'],
      filters: filters ?? [{ name: 'All Files', extensions: ['*'] }],
    });
    return result.canceled ? null : result.filePaths;
  });

  ipcMain.handle(IPC_CHANNELS.FILES_GET_INFO, async (_event, filePath: string) => {
    const stats = await stat(filePath);
    const ext = extname(filePath).toLowerCase();
    const mimeMap: Record<string, string> = {
      '.pdf': 'application/pdf',
      '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
      '.png': 'image/png',
      '.jpg': 'image/jpeg',
      '.jpeg': 'image/jpeg',
      '.md': 'text/markdown',
      '.txt': 'text/plain',
      '.json': 'application/json',
    };
    return {
      path: filePath,
      mimeType: mimeMap[ext] ?? 'application/octet-stream',
      size: stats.size,
    };
  });

  ipcMain.handle(IPC_CHANNELS.FILES_WATCH, async (_event, _dirPath: string) => {
    return { watching: true };
  });

  ipcMain.handle(IPC_CHANNELS.FILES_UNWATCH, async (_event, _dirPath: string) => {
    return { unwatched: true };
  });

  // ── Preview ───────────────────────────────────────────────────────────

  ipcMain.handle(IPC_CHANNELS.PREVIEW_RENDER_PDF_PAGE, async (_event, filePath: string, page: number, scale: number) => {
    try {
      const result = await toolRunner.execute('pdf_render_pages', {
        input_path: filePath,
        pages: String(page),
        out_dir: '.okoffice-out/preview',
      });
      return result;
    } catch {
      return null;
    }
  });

  ipcMain.handle(IPC_CHANNELS.PREVIEW_GET_PDF_INFO, async (_event, filePath: string) => {
    try {
      return await toolRunner.execute('pdf_metadata_page_info', { input_path: filePath });
    } catch {
      return null;
    }
  });

  ipcMain.handle(IPC_CHANNELS.PREVIEW_EXTRACT_TEXT, async (_event, filePath: string) => {
    try {
      return await toolRunner.execute('pdf_extract_text', { input_path: filePath });
    } catch {
      return null;
    }
  });

  ipcMain.handle(IPC_CHANNELS.PREVIEW_CONVERT, async (_event, filePath: string) => {
    const ext = extname(filePath).toLowerCase();
    try {
      if (ext === '.docx') {
        return await toolRunner.execute('word_extract_text', { path: filePath });
      }
      if (ext === '.xlsx') {
        return await toolRunner.execute('sheet_read_workbook', { path: filePath, max_rows_per_sheet: 100 });
      }
      if (ext === '.pptx') {
        return await toolRunner.execute('deck_extract_text', { path: filePath });
      }
      return await toolRunner.execute('pdf_extract_text', { input_path: filePath });
    } catch {
      return null;
    }
  });

  // ── Workflows ─────────────────────────────────────────────────────────

  ipcMain.handle(IPC_CHANNELS.WORKFLOW_LIST, async () => {
    return workflowStore.list();
  });

  ipcMain.handle(IPC_CHANNELS.WORKFLOW_GET, async (_event, id: string) => {
    return workflowStore.get(id);
  });

  ipcMain.handle(IPC_CHANNELS.WORKFLOW_SAVE, async (_event, workflow: unknown) => {
    return workflowStore.save(workflow);
  });

  ipcMain.handle(IPC_CHANNELS.WORKFLOW_DELETE, async (_event, id: string) => {
    return workflowStore.delete(id);
  });

  ipcMain.handle(IPC_CHANNELS.WORKFLOW_EXECUTE, async (_event, id: string, params?: Record<string, unknown>) => {
    return { status: 'pending', message: 'Workflow engine not yet implemented' };
  });

  // ── Settings ──────────────────────────────────────────────────────────

  ipcMain.handle(IPC_CHANNELS.SETTINGS_GET, async (_event, key: string) => {
    return settingsStore.get(key);
  });

  ipcMain.handle(IPC_CHANNELS.SETTINGS_SET, async (_event, key: string, value: string) => {
    settingsStore.set(key, value);
    return { set: true };
  });

  ipcMain.handle(IPC_CHANNELS.SETTINGS_GET_ALL, async () => {
    return settingsStore.getAll();
  });

  ipcMain.handle(IPC_CHANNELS.SETTINGS_GET_LLM_CONFIG, async () => {
    return settingsStore.getLLMConfig();
  });

  ipcMain.handle(IPC_CHANNELS.SETTINGS_SET_LLM_CONFIG, async (_event, config: unknown) => {
    settingsStore.setLLMConfig(config as any);
    return { set: true };
  });

  // ── MCP ───────────────────────────────────────────────────────────────

  ipcMain.handle(IPC_CHANNELS.MCP_GET_STATUS, async () => {
    return mcpClient.getStatus();
  });

  ipcMain.handle(IPC_CHANNELS.MCP_RESTART, async () => {
    await mcpClient.restart();
    return { restarted: true };
  });

  ipcMain.handle(IPC_CHANNELS.MCP_GET_LOG, async () => {
    return { log: '' };
  });

  // ── App ───────────────────────────────────────────────────────────────

  ipcMain.handle(IPC_CHANNELS.APP_GET_VERSION, async () => {
    return app.getVersion();
  });

  ipcMain.handle(IPC_CHANNELS.APP_QUIT, async () => {
    app.quit();
  });

  ipcMain.handle(IPC_CHANNELS.APP_OPEN_EXTERNAL, async (_event, url: string) => {
    await electronShell.openExternal(url);
    return { opened: true };
  });
}
