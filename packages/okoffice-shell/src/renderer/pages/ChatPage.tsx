import React, { useState, useRef, useCallback, useEffect } from 'react';
import { Typography } from '@arco-design/web-react';
import type {
  Message,
  StreamEvent,
  ArtifactRef,
  ConversationSummary,
  FileType,
} from '@shared/types';
import MessageBubble from '../components/chat/MessageBubble';
import SendBox from '../components/chat/SendBox';
import api from '../api/bridge';
import { subscribe, unsubscribe } from '../api/events';
import { usePreview } from '../contexts/PreviewContext';

const { Text } = Typography;

function mimeTypeToFileType(mimeType: string): FileType {
  if (mimeType.includes('pdf')) return 'pdf';
  if (mimeType.includes('word') || mimeType.includes('docx')) return 'docx';
  if (mimeType.includes('sheet') || mimeType.includes('xlsx')) return 'xlsx';
  if (mimeType.includes('presentation') || mimeType.includes('pptx')) return 'pptx';
  if (mimeType.startsWith('image/')) return 'image';
  if (mimeType.includes('json')) return 'json';
  if (mimeType.includes('markdown')) return 'markdown';
  return 'other';
}

const ChatPage: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { setPreviewFile } = usePreview();

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // Load conversation list on mount
  useEffect(() => {
    api.chat.listConversations().then(setConversations).catch(() => {});
  }, []);

  // Subscribe to stream events
  useEffect(() => {
    function handleChunk(event: Extract<StreamEvent, { type: 'llm:chunk' }>) {
      if (event.conversationId !== conversationId) return;
      setMessages((prev) => {
        const updated = [...prev];
        const last = updated[updated.length - 1];
        if (last && last.role === 'assistant') {
          return [
            ...updated.slice(0, -1),
            { ...last, content: last.content + event.content },
          ];
        }
        return updated;
      });
    }

    function handleToolCallStarted(
      event: Extract<StreamEvent, { type: 'llm:tool_call_started' }>,
    ) {
      if (event.conversationId !== conversationId) return;
      setMessages((prev) => {
        const updated = [...prev];
        const last = updated[updated.length - 1];
        if (last && last.role === 'assistant') {
          const existingCalls = last.toolCalls ?? [];
          return [
            ...updated.slice(0, -1),
            {
              ...last,
              toolCalls: [...existingCalls, event.toolCall],
            },
          ];
        }
        return updated;
      });
    }

    function handleToolCallCompleted(
      event: Extract<StreamEvent, { type: 'llm:tool_call_completed' }>,
    ) {
      if (event.conversationId !== conversationId) return;
      setMessages((prev) => {
        const updated = [...prev];
        const last = updated[updated.length - 1];
        if (last && last.role === 'assistant' && last.toolCalls) {
          const updatedCalls = last.toolCalls.map((tc) =>
            tc.id === event.toolCallId
              ? {
                  ...tc,
                  status: 'completed' as const,
                  result: event.result,
                  completedAt: new Date().toISOString(),
                  durationMs:
                    tc.startedAt
                      ? Date.now() - new Date(tc.startedAt).getTime()
                      : undefined,
                }
              : tc,
          );
          const newArtifacts = event.result.artifacts ?? [];
          return [
            ...updated.slice(0, -1),
            {
              ...last,
              toolCalls: updatedCalls,
              artifacts: [...last.artifacts, ...newArtifacts],
            },
          ];
        }
        return updated;
      });
    }

    function handleStreamDone(
      event: Extract<StreamEvent, { type: 'llm:stream_done' }>,
    ) {
      if (event.conversationId !== conversationId) return;
      setStreaming(false);
    }

    subscribe('llm:chunk', handleChunk);
    subscribe('llm:tool_call_started', handleToolCallStarted);
    subscribe('llm:tool_call_completed', handleToolCallCompleted);
    subscribe('llm:stream_done', handleStreamDone);

    return () => {
      unsubscribe('llm:chunk', handleChunk);
      unsubscribe('llm:tool_call_started', handleToolCallStarted);
      unsubscribe('llm:tool_call_completed', handleToolCallCompleted);
      unsubscribe('llm:stream_done', handleStreamDone);
    };
  }, [conversationId]);

  const handleSend = useCallback(
    async (content: string, attachments: Array<{ path: string; name: string }>) => {
      if (streaming) return;

      const convId = conversationId ?? crypto.randomUUID();

      // Build user message content with file references
      const fileContext =
        attachments.length > 0
          ? attachments.map((a) => `[File: ${a.name} (${a.path})]`).join('\n')
          : '';
      const fullContent = fileContext
        ? `${content}\n\nAttached files:\n${fileContext}`
        : content;

      const userMessage: Message = {
        id: crypto.randomUUID(),
        conversationId: convId,
        role: 'user',
        content: fullContent,
        artifacts: attachments.map((a) => ({
          path: a.path,
          mimeType: 'application/octet-stream',
        })),
        createdAt: new Date().toISOString(),
      };

      const assistantMessage: Message = {
        id: crypto.randomUUID(),
        conversationId: convId,
        role: 'assistant',
        content: '',
        artifacts: [],
        createdAt: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, userMessage, assistantMessage]);
      setStreaming(true);

      if (!conversationId) {
        setConversationId(convId);
      }

      try {
        await api.chat.sendMessage(convId, fullContent);
      } catch {
        setStreaming(false);
      }
    },
    [streaming, conversationId],
  );

  const handleStop = useCallback(async () => {
    if (!conversationId) return;
    try {
      await api.chat.stopGeneration(conversationId);
    } catch {
      // stop may fail silently
    }
    setStreaming(false);
  }, [conversationId]);

  const handleArtifactClick = useCallback(
    (artifact: ArtifactRef) => {
      setPreviewFile({
        name: artifact.path.split(/[/\\]/).pop() ?? artifact.path,
        path: artifact.path,
        isDirectory: false,
        size: artifact.sizeBytes ?? 0,
        modifiedAt: new Date().toISOString(),
        fileType: mimeTypeToFileType(artifact.mimeType),
      });
    },
    [setPreviewFile],
  );

  return (
    <div className="flex-col h-full">
      {/* Chat messages area */}
      <div className="flex-1 overflow-auto" style={{ padding: '16px 24px' }}>
        {messages.length === 0 && (
          <div
            className="flex items-center justify-center"
            style={{ height: '100%', color: 'var(--ok-text-tertiary)' }}
          >
            <div className="text-center">
              <Text
                style={{
                  fontSize: 20,
                  fontWeight: 600,
                  display: 'block',
                  marginBottom: 8,
                }}
              >
                okoffice
              </Text>
              <Text className="text-secondary">
                Start a conversation to use PDF, Office, and document tools.
              </Text>
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <MessageBubble
            key={msg.id}
            message={msg}
            streaming={
              streaming &&
              msg === messages[messages.length - 1] &&
              msg.role === 'assistant'
            }
            onArtifactClick={handleArtifactClick}
          />
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Send box with file attachment support */}
      <SendBox
        disabled={false}
        streaming={streaming}
        onSend={handleSend}
        onStop={handleStop}
      />
    </div>
  );
};

export default ChatPage;
