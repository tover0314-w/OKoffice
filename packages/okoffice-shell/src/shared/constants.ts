export const IPC_CHANNELS = {
  // Chat
  CHAT_SEND_MESSAGE: 'okoffice:chat.sendMessage',
  CHAT_STOP_GENERATION: 'okoffice:chat.stopGeneration',
  CHAT_LIST_CONVERSATIONS: 'okoffice:chat.listConversations',
  CHAT_GET_CONVERSATION: 'okoffice:chat.getConversation',
  CHAT_DELETE_CONVERSATION: 'okoffice:chat.deleteConversation',
  CHAT_RENAME_CONVERSATION: 'okoffice:chat.renameConversation',

  // Tools
  TOOLS_LIST: 'okoffice:tools.list',
  TOOLS_GET_CATEGORIES: 'okoffice:tools.getCategories',
  TOOLS_EXECUTE: 'okoffice:tools.execute',
  TOOLS_INSPECT: 'okoffice:tools.inspect',

  // Files
  FILES_LIST_DIRECTORY: 'okoffice:files.listDirectory',
  FILES_READ: 'okoffice:files.readFile',
  FILES_WRITE: 'okoffice:files.writeFile',
  FILES_DELETE: 'okoffice:files.deleteFile',
  FILES_MOVE: 'okoffice:files.moveFile',
  FILES_SELECT_DIRECTORY: 'okoffice:files.selectDirectory',
  FILES_SELECT_FILE: 'okoffice:files.selectFile',
  FILES_GET_INFO: 'okoffice:files.getFileInfo',
  FILES_WATCH: 'okoffice:files.watchDirectory',
  FILES_UNWATCH: 'okoffice:files.unwatchDirectory',

  // Preview
  PREVIEW_RENDER_PDF_PAGE: 'okoffice:preview.renderPdfPage',
  PREVIEW_GET_PDF_INFO: 'okoffice:preview.getPdfPageInfo',
  PREVIEW_EXTRACT_TEXT: 'okoffice:preview.extractText',
  PREVIEW_CONVERT: 'okoffice:preview.convertToPreview',

  // Workflows
  WORKFLOW_LIST: 'okoffice:workflows.list',
  WORKFLOW_GET: 'okoffice:workflows.get',
  WORKFLOW_SAVE: 'okoffice:workflows.save',
  WORKFLOW_DELETE: 'okoffice:workflows.delete',
  WORKFLOW_EXECUTE: 'okoffice:workflows.execute',

  // Settings
  SETTINGS_GET: 'okoffice:settings.get',
  SETTINGS_SET: 'okoffice:settings.set',
  SETTINGS_GET_ALL: 'okoffice:settings.getAll',
  SETTINGS_GET_LLM_CONFIG: 'okoffice:settings.getLLMConfig',
  SETTINGS_SET_LLM_CONFIG: 'okoffice:settings.setLLMConfig',

  // MCP
  MCP_GET_STATUS: 'okoffice:mcp.getStatus',
  MCP_RESTART: 'okoffice:mcp.restart',
  MCP_GET_LOG: 'okoffice:mcp.getServerLog',

  // App
  APP_GET_VERSION: 'okoffice:app.getVersion',
  APP_QUIT: 'okoffice:app.quit',
  APP_OPEN_EXTERNAL: 'okoffice:app.openExternal',

  // Events (main -> renderer push)
  EVENT_STREAM: 'okoffice:event',
} as const;

export const WS_EVENTS = {
  LLM_CHUNK: 'llm:chunk',
  LLM_TOOL_CALL_STARTED: 'llm:tool_call_started',
  LLM_TOOL_CALL_COMPLETED: 'llm:tool_call_completed',
  LLM_STREAM_DONE: 'llm:stream_done',
  FILE_CHANGED: 'file:changed',
  WORKFLOW_STEP_PROGRESS: 'workflow:step_progress',
} as const;

export const DEFAULTS = {
  APP_PORT: 17531,
  MCP_COMMAND: 'okoffice',
  MCP_ARGS: ['serve', '--mcp', '--transport', 'stdio'],
  DB_NAME: 'okoffice.db',
  MAX_TOOL_LOOP_ITERATIONS: 20,
  TOOL_CALL_TIMEOUT_MS: 60_000,
  STREAM_THROTTLE_MS: 16,
} as const;
