import { app } from 'electron';
import { initDatabase, getDatabase, closeDatabase } from './db/database';
import { runMigrations } from './db/migrations';
import { ConversationStore } from './db/conversation-store';
import { SettingsStore } from './db/settings-store';
import { WorkflowStore } from './db/workflow-store';
import { McpClient } from './mcp/client';
import { ToolRegistry } from './mcp/tool-registry';
import { ToolRunner } from './mcp/tool-runner';
import { WindowManager } from './window';
import { registerIpcHandlers } from './ipc-handlers';
import { startWsServer, type WsBroadcaster } from './services/websocket-server';
import { DEFAULTS } from '@shared/constants';

// ── Single instance lock ──

const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
  app.quit();
}

// ── Globals ──

let mcpClient: McpClient;
let windowManager: WindowManager;
let wsServer: WsBroadcaster;

// ── App lifecycle ──

app.on('second-instance', () => {
  const win = windowManager?.getWindow();
  if (win) {
    if (win.isMinimized()) win.restore();
    win.focus();
  }
});

app.whenReady().then(async () => {
  // 1. Database
  const db = initDatabase();
  runMigrations(db);

  // 2. Stores
  const conversationStore = new ConversationStore(db);
  const settingsStore = new SettingsStore(db);
  const workflowStore = new WorkflowStore(db);

  // 3. MCP client
  mcpClient = new McpClient();
  const toolRegistry = new ToolRegistry();
  const toolRunner = new ToolRunner(mcpClient);

  try {
    await mcpClient.start();
    toolRegistry.loadTools(mcpClient.getToolList());
  } catch (err) {
    console.error('Failed to start MCP client:', err);
  }

  mcpClient.on('statusChanged', (status) => {
    if (status.connected) {
      toolRegistry.loadTools(mcpClient.getToolList());
    }
  });

  // 4. Window
  windowManager = new WindowManager();
  windowManager.createWindow();

  // 5. WebSocket server
  wsServer = startWsServer();

  // 6. IPC handlers
  registerIpcHandlers({
    mcpClient,
    toolRegistry,
    toolRunner,
    conversationStore,
    settingsStore,
    workflowStore,
    db,
    wsServer,
  });
});

app.on('window-all-closed', () => {
  // Keep alive for tray / background MCP server
});

app.on('before-quit', () => {
  try {
    mcpClient?.stop();
  } catch { /* best-effort */ }

  try {
    wsServer?.close();
  } catch { /* best-effort */ }

  try {
    closeDatabase();
  } catch { /* best-effort */ }
});
