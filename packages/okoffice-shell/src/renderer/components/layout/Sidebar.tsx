import React, { useEffect, useState, useCallback } from 'react';
import { Button, Typography, Dropdown, Menu } from '@arco-design/web-react';
import {
  IconPlus,
  IconSettings,
  IconExperiment,
  IconMoreVertical,
} from '@arco-design/web-react/icon';
import { useNavigate, useLocation } from 'react-router-dom';
import type { ConversationSummary } from '@shared/types';
import api from '../../api/bridge';

const { Text } = Typography;

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

const Sidebar: React.FC<SidebarProps> = ({ collapsed }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);

  const loadConversations = useCallback(async () => {
    try {
      const list = await api.chat.listConversations();
      setConversations(list);
    } catch {
      // conversations will remain empty on error
    }
  }, []);

  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  const handleNewConversation = () => {
    setActiveId(null);
    navigate('/');
  };

  const handleSelectConversation = (id: string) => {
    setActiveId(id);
    navigate('/');
  };

  const handleDelete = async (id: string) => {
    await api.chat.deleteConversation(id);
    if (activeId === id) {
      setActiveId(null);
    }
    loadConversations();
  };

  const handleRename = async (id: string) => {
    const title = window.prompt('Rename conversation:', '');
    if (!title) return;
    await api.chat.renameConversation(id, title);
    loadConversations();
  };

  if (collapsed) return null;

  const isActive = (id: string) => id === activeId;
  const isSettingsActive = location.pathname === '/settings';

  return (
    <div
      className="flex-col h-full"
      style={{ background: 'var(--ok-bg-secondary)' }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between"
        style={{ padding: '12px 12px 8px', borderBottom: '1px solid var(--ok-border-light)' }}
      >
        <Text bold style={{ fontSize: 15 }}>
          okoffice
        </Text>
        <Button
          size="small"
          type="primary"
          icon={<IconPlus />}
          onClick={handleNewConversation}
        >
          New
        </Button>
      </div>

      {/* Conversation list */}
      <div className="flex-1 overflow-auto" style={{ padding: '4px 0' }}>
        {conversations.map((conv) => (
          <div
            key={conv.id}
            className="flex items-center cursor-pointer"
            style={{
              padding: '8px 12px',
              gap: 8,
              background: isActive(conv.id) ? 'var(--ok-bg-hover)' : 'transparent',
              borderRight: isActive(conv.id)
                ? '2px solid var(--ok-primary)'
                : '2px solid transparent',
            }}
            onClick={() => handleSelectConversation(conv.id)}
          >
            <div className="flex-1 overflow-hidden">
              <div
                className="truncate font-medium"
                style={{ fontSize: 13, lineHeight: '18px' }}
              >
                {conv.title || 'Untitled'}
              </div>
              <div
                className="truncate text-xs text-tertiary"
                style={{ marginTop: 2 }}
              >
                {conv.lastMessagePreview || 'No messages'}
              </div>
            </div>

            <Dropdown
              droplist={
                <Menu>
                  <Menu.Item onClick={() => handleRename(conv.id)}>
                    Rename
                  </Menu.Item>
                  <Menu.Item
                    onClick={() => handleDelete(conv.id)}
                    style={{ color: 'var(--ok-danger)' }}
                  >
                    Delete
                  </Menu.Item>
                </Menu>
              }
              trigger="click"
              position="br"
            >
              <Button
                size="mini"
                type="text"
                icon={<IconMoreVertical />}
                onClick={(e) => e.stopPropagation()}
                style={{ flexShrink: 0 }}
              />
            </Dropdown>
          </div>
        ))}

        {conversations.length === 0 && (
          <div
            className="text-xs text-tertiary"
            style={{ padding: '16px 12px', textAlign: 'center' }}
          >
            No conversations yet
          </div>
        )}
      </div>

      {/* Bottom navigation */}
      <div style={{ borderTop: '1px solid var(--ok-border-light)', padding: 8 }}>
        <Button
          long
          size="small"
          type={isSettingsActive ? 'primary' : 'text'}
          icon={<IconSettings />}
          onClick={() => navigate('/settings')}
          style={{ justifyContent: 'flex-start', marginBottom: 4 }}
        >
          Settings
        </Button>
        <Button
          long
          size="small"
          type="text"
          icon={<IconExperiment />}
          onClick={() => navigate('/workflow')}
          style={{ justifyContent: 'flex-start' }}
        >
          Workflows
        </Button>
      </div>
    </div>
  );
};

export default Sidebar;
