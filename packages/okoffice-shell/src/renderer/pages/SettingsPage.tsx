import React, { useEffect, useState, useCallback } from 'react';
import {
  Tabs,
  TabPane,
  Form,
  Input,
  Select,
  Slider,
  Button,
  Typography,
  Message,
  Spin,
  Switch,
} from '@arco-design/web-react';
import { IconRefresh } from '@arco-design/web-react/icon';
import type { LLMConfig, LLMProviderType, MCPStatus } from '@shared/types';
import api from '../api/bridge';

const { Title, Text, Paragraph } = Typography;

const PROVIDER_OPTIONS: Array<{ label: string; value: LLMProviderType }> = [
  { label: 'OpenAI', value: 'openai' },
  { label: 'Anthropic', value: 'anthropic' },
  { label: 'Ollama', value: 'ollama' },
];

const MODEL_OPTIONS: Record<LLMProviderType, string[]> = {
  openai: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'o1', 'o1-mini'],
  anthropic: ['claude-sonnet-4-20250514', 'claude-opus-4-20250514', 'claude-haiku-4-20250514'],
  ollama: ['llama3', 'mistral', 'codellama', 'qwen2'],
};

const SettingsPage: React.FC = () => {
  const [llmConfig, setLLMConfig] = useState<LLMConfig | null>(null);
  const [mcpStatus, setMcpStatus] = useState<MCPStatus | null>(null);
  const [mcpLog, setMcpLog] = useState<string>('');
  const [theme, setTheme] = useState<'light' | 'dark'>('light');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [restarting, setRestarting] = useState(false);

  const loadSettings = useCallback(async () => {
    setLoading(true);
    try {
      const [config, status, allSettings] = await Promise.all([
        api.settings.getLLMConfig(),
        api.mcp.getStatus(),
        api.settings.getAll(),
      ]);
      setLLMConfig(config);
      setMcpStatus(status);
      const currentTheme = allSettings['theme'];
      if (currentTheme === 'dark' || currentTheme === 'light') {
        setTheme(currentTheme);
      }
    } catch {
      // settings remain null on error
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSettings();
  }, [loadSettings]);

  const handleSaveLLM = useCallback(
    async (values: Partial<LLMConfig>) => {
      if (!llmConfig) return;
      setSaving(true);
      try {
        const updated: LLMConfig = {
          ...llmConfig,
          ...values,
          temperature: Number(values.temperature ?? llmConfig.temperature),
          maxTokens: Number(values.maxTokens ?? llmConfig.maxTokens),
        };
        await api.settings.setLLMConfig(updated);
        setLLMConfig(updated);
        Message.success('LLM configuration saved');
      } catch {
        Message.error('Failed to save LLM configuration');
      } finally {
        setSaving(false);
      }
    },
    [llmConfig],
  );

  const handleRestartMcp = useCallback(async () => {
    setRestarting(true);
    try {
      await api.mcp.restart();
      const status = await api.mcp.getStatus();
      setMcpStatus(status);
      Message.success('MCP server restarted');
    } catch {
      Message.error('Failed to restart MCP server');
    } finally {
      setRestarting(false);
    }
  }, []);

  const handleLoadLog = useCallback(async () => {
    try {
      const log = await api.mcp.getServerLog();
      setMcpLog(log);
    } catch {
      setMcpLog('Failed to load server log');
    }
  }, []);

  const handleThemeChange = useCallback(
    async (isDark: boolean) => {
      const newTheme = isDark ? 'dark' : 'light';
      setTheme(newTheme);
      document.documentElement.setAttribute('data-theme', newTheme);
      try {
        await api.settings.set('theme', newTheme);
      } catch {
        // theme persists locally even if settings save fails
      }
    },
    [],
  );

  if (loading) {
    return (
      <div
        className="flex items-center justify-center"
        style={{ height: '100%', padding: 48 }}
      >
        <Spin tip="Loading settings..." />
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 640, padding: '24px 32px', overflow: 'auto' }}>
      <Title heading={5} style={{ marginBottom: 16 }}>
        Settings
      </Title>

      <Tabs defaultActiveTab="llm">
        {/* LLM Provider Tab */}
        <TabPane key="llm" title="LLM Provider">
          {llmConfig && (
            <Form
              layout="vertical"
              initialValues={{
                provider: llmConfig.provider,
                apiKey: llmConfig.apiKey,
                model: llmConfig.model,
                baseUrl: llmConfig.baseUrl ?? '',
                temperature: llmConfig.temperature,
              }}
              onSubmit={handleSaveLL as never}
              style={{ marginTop: 16 }}
            >
              <Form.Item label="Provider" field="provider">
                <Select options={PROVIDER_OPTIONS} />
              </Form.Item>

              <Form.Item label="API Key" field="apiKey">
                <Input.Password placeholder="Enter API key" />
              </Form.Item>

              <Form.Item label="Model" field="model">
                <Select options={(MODEL_OPTIONS[llmConfig.provider] ?? []).map((m) => ({ label: m, value: m }))} />
              </Form.Item>

              {llmConfig.provider === 'ollama' && (
                <Form.Item label="Base URL" field="baseUrl">
                  <Input placeholder="http://localhost:11434" />
                </Form.Item>
              )}

              <Form.Item label="Temperature" field="temperature">
                <Slider min={0} max={2} step={0.1} />
              </Form.Item>

              <Form.Item>
                <Button
                  type="primary"
                  htmlType="submit"
                  loading={saving}
                  style={{ marginTop: 8 }}
                >
                  Save
                </Button>
              </Form.Item>
            </Form>
          )}
        </TabPane>

        {/* MCP Server Tab */}
        <TabPane key="mcp" title="MCP Server">
          <div style={{ marginTop: 16 }}>
            <div className="flex items-center justify-between" style={{ marginBottom: 16 }}>
              <div className="flex items-center gap-2">
                <div
                  style={{
                    width: 10,
                    height: 10,
                    borderRadius: '50%',
                    background: mcpStatus?.connected
                      ? 'var(--ok-success)'
                      : 'var(--ok-danger)',
                  }}
                />
                <Text>
                  {mcpStatus?.connected
                    ? `Connected (${mcpStatus.toolCount} tools)`
                    : 'Disconnected'}
                </Text>
              </div>
              <Button
                type="primary"
                icon={<IconRefresh />}
                loading={restarting}
                onClick={handleRestartMcp}
              >
                Restart
              </Button>
            </div>

            {mcpStatus?.lastError && (
              <Paragraph
                className="text-sm"
                style={{
                  color: 'var(--ok-danger)',
                  background: 'var(--ok-bg-tertiary)',
                  padding: 8,
                  borderRadius: 'var(--ok-radius-sm)',
                  marginBottom: 12,
                }}
              >
                {mcpStatus.lastError}
              </Paragraph>
            )}

            <Button type="text" onClick={handleLoadLog}>
              Load Server Log
            </Button>

            {mcpLog && (
              <pre
                style={{
                  marginTop: 12,
                  padding: 12,
                  background: 'var(--ok-bg-tertiary)',
                  borderRadius: 'var(--ok-radius-sm)',
                  fontSize: 11,
                  maxHeight: 300,
                  overflow: 'auto',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-all',
                }}
              >
                {mcpLog}
              </pre>
            )}
          </div>
        </TabPane>

        {/* Appearance Tab */}
        <TabPane key="appearance" title="Appearance">
          <div style={{ marginTop: 16 }}>
            <div className="flex items-center justify-between" style={{ marginBottom: 8 }}>
              <Text>Dark Theme</Text>
              <Switch
                checked={theme === 'dark'}
                onChange={handleThemeChange}
              />
            </div>
            <Text className="text-xs text-tertiary">
              Toggle between light and dark appearance.
            </Text>
          </div>
        </TabPane>
      </Tabs>
    </div>
  );
};

export default SettingsPage;
