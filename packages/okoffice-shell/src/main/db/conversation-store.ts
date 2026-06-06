import type Database from 'better-sqlite3';
import { randomUUID } from 'node:crypto';
import type {
  Conversation,
  ConversationSummary,
  Message,
  ToolCall,
  ToolResultRef,
  ArtifactRef,
} from '@shared/types';

export class ConversationStore {
  private db: Database.Database;

  constructor(db: Database.Database) {
    this.db = db;
  }

  create(
    title?: string,
    model?: string,
    provider?: string,
  ): Conversation {
    const now = new Date().toISOString();
    const id = randomUUID();

    const conversation: Conversation = {
      id,
      title: title ?? 'New Conversation',
      createdAt: now,
      updatedAt: now,
      model: model ?? '',
      provider: (provider as Conversation['provider']) ?? 'openai',
      systemPrompt: null,
      messages: [],
    };

    this.db
      .prepare(
        `INSERT INTO conversations (id, title, created_at, updated_at, model, provider, system_prompt, metadata)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
      )
      .run(
        conversation.id,
        conversation.title,
        conversation.createdAt,
        conversation.updatedAt,
        conversation.model,
        conversation.provider,
        conversation.systemPrompt,
        null,
      );

    return conversation;
  }

  getById(id: string): Conversation | null {
    const row = this.db
      .prepare(
        `SELECT id, title, created_at, updated_at, model, provider, system_prompt, metadata
         FROM conversations WHERE id = ?`,
      )
      .get(id) as ConversationRow | undefined;

    if (!row) {
      return null;
    }

    const messages = this.getMessages(id);

    return mapRowToConversation(row, messages);
  }

  list(): ConversationSummary[] {
    const rows = this.db
      .prepare(
        `SELECT
           c.id,
           c.title,
           c.created_at,
           c.updated_at,
           c.model,
           (SELECT COUNT(*) FROM messages m WHERE m.conversation_id = c.id) AS message_count,
           (SELECT m2.content FROM messages m2 WHERE m2.conversation_id = c.id ORDER BY m2.created_at DESC LIMIT 1) AS last_message
         FROM conversations c
         ORDER BY c.updated_at DESC`,
      )
      .all() as ConversationListRow[];

    return rows.map((row) => ({
      id: row.id,
      title: row.title,
      createdAt: row.created_at,
      updatedAt: row.updated_at,
      model: row.model,
      messageCount: row.message_count,
      lastMessagePreview: truncate(row.last_message ?? '', 120),
    }));
  }

  updateTitle(id: string, title: string): void {
    const now = new Date().toISOString();
    this.db
      .prepare('UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?')
      .run(title, now, id);
  }

  delete(id: string): void {
    this.db.prepare('DELETE FROM conversations WHERE id = ?').run(id);
  }

  addMessage(conversationId: string, message: Message): void {
    const now = new Date().toISOString();

    this.db
      .prepare(
        `INSERT INTO messages (id, conversation_id, role, content, tool_calls, tool_results, artifacts, created_at)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
      )
      .run(
        message.id,
        conversationId,
        message.role,
        message.content,
        message.toolCalls ? JSON.stringify(message.toolCalls) : null,
        message.toolResults ? JSON.stringify(message.toolResults) : null,
        message.artifacts.length > 0 ? JSON.stringify(message.artifacts) : null,
        message.createdAt ?? now,
      );

    this.db
      .prepare('UPDATE conversations SET updated_at = ? WHERE id = ?')
      .run(now, conversationId);
  }

  getMessages(conversationId: string): Message[] {
    const rows = this.db
      .prepare(
        `SELECT id, conversation_id, role, content, tool_calls, tool_results, artifacts, created_at
         FROM messages
         WHERE conversation_id = ?
         ORDER BY created_at ASC`,
      )
      .all(conversationId) as MessageRow[];

    return rows.map(mapRowToMessage);
  }
}

// --- Row types ---

interface ConversationRow {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  model: string;
  provider: string;
  system_prompt: string | null;
  metadata: string | null;
}

interface ConversationListRow {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  model: string;
  message_count: number;
  last_message: string | null;
}

interface MessageRow {
  id: string;
  conversation_id: string;
  role: string;
  content: string;
  tool_calls: string | null;
  tool_results: string | null;
  artifacts: string | null;
  created_at: string;
}

// --- Mappers ---

function mapRowToConversation(row: ConversationRow, messages: Message[]): Conversation {
  return {
    id: row.id,
    title: row.title,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
    model: row.model,
    provider: row.provider as Conversation['provider'],
    systemPrompt: row.system_prompt,
    messages,
  };
}

function mapRowToMessage(row: MessageRow): Message {
  return {
    id: row.id,
    conversationId: row.conversation_id,
    role: row.role as Message['role'],
    content: row.content,
    toolCalls: row.tool_calls ? (JSON.parse(row.tool_calls) as ToolCall[]) : undefined,
    toolResults: row.tool_results ? (JSON.parse(row.tool_results) as ToolResultRef[]) : undefined,
    artifacts: row.artifacts ? (JSON.parse(row.artifacts) as ArtifactRef[]) : [],
    createdAt: row.created_at,
  };
}

function truncate(text: string, maxLength: number): string {
  if (text.length <= maxLength) {
    return text;
  }
  return text.slice(0, maxLength - 1) + '…';
}
