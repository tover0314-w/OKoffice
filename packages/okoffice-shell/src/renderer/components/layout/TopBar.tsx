import React, { useEffect, useState } from 'react';
import { Button, Tooltip, Typography, Spin } from '@arco-design/web-react';
import { IconMenuFold, IconMenuUnfold, IconSettings } from '@arco-design/web-react/icon';
import { useNavigate, useLocation } from 'react-router-dom';
import type { MCPStatus, LLMConfig } from '@shared/types';
import api from '../../api/bridge';

const { Text } = Typography;

interface TopBarProps {
  sidebarCollapsed: boolean;
  onToggleSidebar: () => void;
  previewVisible: boolean;
  onTogglePreview: () => void;
}

const BREADCRUMB_MAP: Record<string, string> = {
  '/': 'Chat',
  '/settings': 'Settings',
  '/workflow': 'Workflows',
};

const TopBar: React.FC<TopBarProps> = ({
  sidebarCollapsed,
  onToggleSidebar,
}) => {
  const navigate = useNavigate();
  const location = useLocation();

  const [mcpStatus, setMcpStatus] = useState<MCPStatus | null>(null);
  const [llmConfig, setLlmConfig] = useState<LLMConfig | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [status, config] = await Promise.all([
          api.mcp.getStatus(),
          api.settings.getLLMConfig(),
        ]);
        setMcpStatus(status);
        setLlmConfig(config);
      } catch {
        // status remains null on error
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const breadcrumb = BREADCRUMB_MAP[location.pathname] ?? 'okoffice';

  return (
    <div className="flex items-center justify-between w-full">
      <div className="flex items-center gap-2">
        {sidebarCollapsed && (
          <Button
            size="small"
            type="text"
            icon={<IconMenuUnfold />}
            onClick={onToggleSidebar}
          />
        )}
        {!sidebarCollapsed && (
          <Button
            size="small"
            type="text"
            icon={<IconMenuFold />}
            onClick={onToggleSidebar}
          />
        )}
        <Text style={{ fontSize: 14 }}>{breadcrumb}</Text>
      </div>

      <div className="flex items-center gap-3">
        {loading ? (
          <Spin size={14} />
        ) : (
          <>
            {/* MCP status indicator */}
            <Tooltip
              content={
                mcpStatus?.connected
                  ? `MCP connected (${mcpStatus.toolCount} tools)`
                  : 'MCP disconnected'
              }
            >
              <div className="flex items-center gap-1">
                <div
                  style={{
                    width: 8,
                    height: 8,
                    borderRadius: '50%',
                    background: mcpStatus?.connected
                      ? 'var(--ok-success)'
                      : 'var(--ok-danger)',
                  }}
                />
                <Text className="text-xs text-tertiary">MCP</Text>
              </div>
            </Tooltip>

            {/* LLM provider display */}
            {llmConfig && (
              <Text className="text-xs text-tertiary">
                {llmConfig.provider} / {llmConfig.model}
              </Text>
            )}
          </>
        )}

        <Button
          size="small"
          type="text"
          icon={<IconSettings />}
          onClick={() => navigate('/settings')}
        />
      </div>
    </div>
  );
};

export default TopBar;
