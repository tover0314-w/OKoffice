import { contextBridge, ipcRenderer } from 'electron';
import { IPC_CHANNELS } from '../shared/constants';
import type { OkofficeAPI } from './api-types';

function invoke<T>(channel: string, ...args: unknown[]): Promise<T> {
  return ipcRenderer.invoke(channel, ...args) as Promise<T>;
}

const okoffice: OkofficeAPI = {
  chat: {
    sendMessage(conversationId, content) {
      return invoke(IPC_CHANNELS.CHAT_SEND_MESSAGE, conversationId, content);
    },
    stopGeneration(conversationId) {
      return invoke(IPC_CHANNELS.CHAT_STOP_GENERATION, conversationId);
    },
    listConversations() {
      return invoke(IPC_CHANNELS.CHAT_LIST_CONVERSATIONS);
    },
    getConversation(id) {
      return invoke(IPC_CHANNELS.CHAT_GET_CONVERSATION, id);
    },
    deleteConversation(id) {
      return invoke(IPC_CHANNELS.CHAT_DELETE_CONVERSATION, id);
    },
    renameConversation(id, title) {
      return invoke(IPC_CHANNELS.CHAT_RENAME_CONVERSATION, id, title);
    },
  },

  tools: {
    list() {
      return invoke(IPC_CHANNELS.TOOLS_LIST);
    },
    getCategories() {
      return invoke(IPC_CHANNELS.TOOLS_GET_CATEGORIES);
    },
    execute(name, args) {
      return invoke(IPC_CHANNELS.TOOLS_EXECUTE, name, args);
    },
    inspect(name) {
      return invoke(IPC_CHANNELS.TOOLS_INSPECT, name);
    },
  },

  files: {
    listDirectory(path) {
      return invoke(IPC_CHANNELS.FILES_LIST_DIRECTORY, path);
    },
    readFile(path) {
      return invoke(IPC_CHANNELS.FILES_READ, path);
    },
    writeFile(path, content) {
      return invoke(IPC_CHANNELS.FILES_WRITE, path, content);
    },
    deleteFile(path) {
      return invoke(IPC_CHANNELS.FILES_DELETE, path);
    },
    moveFile(from, to) {
      return invoke(IPC_CHANNELS.FILES_MOVE, from, to);
    },
    selectDirectory() {
      return invoke(IPC_CHANNELS.FILES_SELECT_DIRECTORY);
    },
    selectFile(filters) {
      return invoke(IPC_CHANNELS.FILES_SELECT_FILE, filters);
    },
    getFileInfo(path) {
      return invoke(IPC_CHANNELS.FILES_GET_INFO, path);
    },
    watchDirectory(path) {
      return invoke(IPC_CHANNELS.FILES_WATCH, path);
    },
    unwatchDirectory(path) {
      return invoke(IPC_CHANNELS.FILES_UNWATCH, path);
    },
  },

  preview: {
    renderPdfPage(path, page, scale) {
      return invoke(IPC_CHANNELS.PREVIEW_RENDER_PDF_PAGE, path, page, scale);
    },
    getPdfPageInfo(path) {
      return invoke(IPC_CHANNELS.PREVIEW_GET_PDF_INFO, path);
    },
    extractText(path) {
      return invoke(IPC_CHANNELS.PREVIEW_EXTRACT_TEXT, path);
    },
    convertToPreview(path) {
      return invoke(IPC_CHANNELS.PREVIEW_CONVERT, path);
    },
  },

  workflows: {
    list() {
      return invoke(IPC_CHANNELS.WORKFLOW_LIST);
    },
    get(id) {
      return invoke(IPC_CHANNELS.WORKFLOW_GET, id);
    },
    save(workflow) {
      return invoke(IPC_CHANNELS.WORKFLOW_SAVE, workflow);
    },
    delete(id) {
      return invoke(IPC_CHANNELS.WORKFLOW_DELETE, id);
    },
    execute(id, inputs) {
      return invoke(IPC_CHANNELS.WORKFLOW_EXECUTE, id, inputs);
    },
  },

  settings: {
    get(key) {
      return invoke(IPC_CHANNELS.SETTINGS_GET, key);
    },
    set(key, value) {
      return invoke(IPC_CHANNELS.SETTINGS_SET, key, value);
    },
    getAll() {
      return invoke(IPC_CHANNELS.SETTINGS_GET_ALL);
    },
    getLLMConfig() {
      return invoke(IPC_CHANNELS.SETTINGS_GET_LLM_CONFIG);
    },
    setLLMConfig(config) {
      return invoke(IPC_CHANNELS.SETTINGS_SET_LLM_CONFIG, config);
    },
  },

  mcp: {
    getStatus() {
      return invoke(IPC_CHANNELS.MCP_GET_STATUS);
    },
    restart() {
      return invoke(IPC_CHANNELS.MCP_RESTART);
    },
    getServerLog() {
      return invoke(IPC_CHANNELS.MCP_GET_LOG);
    },
  },

  app: {
    getVersion() {
      return invoke(IPC_CHANNELS.APP_GET_VERSION);
    },
    quit() {
      return invoke(IPC_CHANNELS.APP_QUIT);
    },
    openExternal(url) {
      return invoke(IPC_CHANNELS.APP_OPEN_EXTERNAL, url);
    },
  },

  onEvent(callback) {
    const handler = (_event: Electron.IpcRendererEvent, data: unknown) => {
      callback(data as Parameters<typeof callback>[0]);
    };
    ipcRenderer.on(IPC_CHANNELS.EVENT_STREAM, handler);
    return () => {
      ipcRenderer.removeListener(IPC_CHANNELS.EVENT_STREAM, handler);
    };
  },
};

contextBridge.exposeInMainWorld('okoffice', okoffice);
