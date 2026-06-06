import { OpenAIProvider } from './openai-provider';

export class OllamaProvider extends OpenAIProvider {
  constructor(model: string, baseUrl?: string) {
    const resolvedBaseUrl = baseUrl ?? 'http://localhost:11434/v1';
    // Ollama's OpenAI-compatible endpoint does not require a real API key,
    // but the OpenAI SDK expects a non-empty string.
    super('ollama-placeholder', model, resolvedBaseUrl);
  }
}
