import type Database from 'better-sqlite3';
import type { LLMConfig } from '@shared/types';

const LLM_CONFIG_KEY = 'llm_config';

const DEFAULT_LLM_CONFIG: LLMConfig = {
  provider: 'openai',
  apiKey: '',
  model: 'gpt-4o',
  temperature: 0.7,
  maxTokens: 4096,
  systemPrompt:
    'You are an OKoffice assistant. Help users create, inspect, and transform PDF and Office documents using the available tools.',
};

export class SettingsStore {
  private db: Database.Database;

  constructor(db: Database.Database) {
    this.db = db;
  }

  get(key: string): string | null {
    const row = this.db.prepare('SELECT value FROM settings WHERE key = ?').get(key) as
      | { value: string }
      | undefined;
    return row?.value ?? null;
  }

  set(key: string, value: string): void {
    this.db
      .prepare('INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value')
      .run(key, value);
  }

  getAll(): Record<string, string> {
    const rows = this.db.prepare('SELECT key, value FROM settings').all() as Array<{
      key: string;
      value: string;
    }>;
    const result: Record<string, string> = {};
    for (const row of rows) {
      result[row.key] = row.value;
    }
    return result;
  }

  getLLMConfig(): LLMConfig {
    const raw = this.get(LLM_CONFIG_KEY);
    if (!raw) {
      return { ...DEFAULT_LLM_CONFIG };
    }
    try {
      const parsed = JSON.parse(raw) as Partial<LLMConfig>;
      return {
        provider: parsed.provider ?? DEFAULT_LLM_CONFIG.provider,
        apiKey: parsed.apiKey ?? DEFAULT_LLM_CONFIG.apiKey,
        model: parsed.model ?? DEFAULT_LLM_CONFIG.model,
        baseUrl: parsed.baseUrl,
        temperature: parsed.temperature ?? DEFAULT_LLM_CONFIG.temperature,
        maxTokens: parsed.maxTokens ?? DEFAULT_LLM_CONFIG.maxTokens,
        systemPrompt: parsed.systemPrompt ?? DEFAULT_LLM_CONFIG.systemPrompt,
      };
    } catch {
      return { ...DEFAULT_LLM_CONFIG };
    }
  }

  setLLMConfig(config: LLMConfig): void {
    this.set(LLM_CONFIG_KEY, JSON.stringify(config));
  }
}
