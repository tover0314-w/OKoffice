import React, { useState, useRef, useCallback, useEffect } from 'react';
import { Input, Button, Typography, Spin } from '@arco-design/web-react';
import { IconSend, IconStop } from '@arco-design/web-react/icon';
import type { Message, Conversation, StreamEvent } from '@shared/types';
import api from '../api/bridge';
import { subscribe, unsubscribe } from '../api/events';

const { Text, Paragraph } = Typography;
const { TextArea } = Input;

const ChatPage: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [streaming, setStreaming] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

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

    function handleStreamDone(event: Extract<StreamEvent, { type: 'llm:stream_done' }>) {
      if (event.conversationId !== conversationId) return;
      setStreaming(false);
    }

    subscribe('llm:chunk', handleChunk);
    subscribe('llm:stream_done', handleStreamDone);

    return () => {
      unsubscribe('llm:chunk', handleChunk);
      unsubscribe('llm:stream_done', handleStreamDone);
    };
  }, [conversationId]);

  const handleSend = useCallback(async () => {
    const content = inputValue.trim();
    if (!content || streaming) return;

    const userMessage: Message = {
      id: crypto.randomUUID(),
      conversationId: conversationId ?? '',
      role: 'user',
      content,
      artifacts: [],
      createdAt: new Date().toISOString(),
    };

    const assistantMessage: Message = {
      id: crypto.randomUUID(),
      conversationId: conversationId ?? '',
      role: 'assistant',
      content: '',
      artifacts: [],
      createdAt: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage, assistantMessage]);
    setInputValue('');
    setStreaming(true);
    setLoading(true);

    try {
      const convId = conversationId ?? crypto.randomUUID();
      if (!conversationId) {
        setConversationId(convId);
      }
      await api.chat.sendMessage(convId, content);
    } catch {
      setStreaming(false);
    } finally {
      setLoading(false);
    }
  }, [inputValue, streaming, conversationId]);

  const handleStop = useCallback(async () => {
    if (!conversationId) return;
    try {
      await api.chat.stopGeneration(conversationId);
    } catch {
      // stop request may fail silently
    }
    setStreaming(false);
  }, [conversationId]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex-col h-full">
      {/* Chat messages area */}
      <div className="flex-1 overflow-auto" style={{ padding: '16px 24px' }}>
        {messages.length === 0 && !loading && (
          <div
            className="flex items-center justify-center"
            style={{ height: '100%', color: 'var(--ok-text-tertiary)' }}
          >
            <Text className="text-secondary">
              Start a conversation by typing a message below.
            </Text>
          </div>
        )}

        {messages.map((msg) => (
          <div
            key={msg.id}
            className="flex gap-3"
            style={{
              marginBottom: 16,
              flexDirection: msg.role === 'user' ? 'row-reverse' : 'row',
            }}
          >
            <div
              style={{
                maxWidth: '75%',
                padding: '8px 12px',
                borderRadius: 'var(--ok-radius-md)',
                background:
                  msg.role === 'user'
                    ? 'var(--ok-primary)'
                    : 'var(--ok-bg-secondary)',
                color:
                  msg.role === 'user' ? 'var(--ok-primary-text)' : 'var(--ok-text)',
              }}
            >
              <Paragraph
                style={{
                  margin: 0,
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                }}
              >
                {msg.content || (msg.role === 'assistant' && streaming ? '' : '')}
              </Paragraph>
              {msg.role === 'assistant' && streaming && msg.content === '' && (
                <Spin size={14} />
              )}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Send box */}
      <div
        style={{
          padding: '8px 24px 16px',
          borderTop: '1px solid var(--ok-border-light)',
          background: 'var(--ok-bg)',
        }}
      >
        <div className="flex items-end gap-2">
          <TextArea
            value={inputValue}
            onChange={setInputValue}
            onKeyDown={handleKeyDown}
            placeholder="Type a message..."
            autoSize={{ minRows: 1, maxRows: 6 }}
            style={{ flex: 1 }}
            disabled={streaming}
          />
          {streaming ? (
            <Button
              type="primary"
              danger
              icon={<IconStop />}
              onClick={handleStop}
            />
          ) : (
            <Button
              type="primary"
              icon={<IconSend />}
              onClick={handleSend}
              disabled={!inputValue.trim()}
            />
          )}
        </div>
      </div>
    </div>
  );
};

export default ChatPage;
