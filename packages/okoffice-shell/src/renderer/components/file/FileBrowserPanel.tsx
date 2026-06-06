import React, { useState, useCallback, useEffect } from 'react';
import { Typography, Button, Spin, Input } from '@arco-design/web-react';
import {
  IconFolder,
  IconFile,
  IconFilePdf,
  IconFileImage,
  IconRefresh,
} from '@arco-design/web-react/icon';
import type { FileEntry, FileType } from '@shared/types';
import api from '../../api/bridge';

const { Text } = Typography;

function fileTypeIcon(type: FileType): React.ReactNode {
  switch (type) {
    case 'pdf':
      return <IconFilePdf style={{ color: '#ef4444' }} />;
    case 'image':
      return <IconFileImage style={{ color: '#8b5cf6' }} />;
    case 'docx':
      return <IconFile style={{ color: '#2563eb' }} />;
    case 'xlsx':
      return <IconFile style={{ color: '#16a34a' }} />;
    case 'pptx':
      return <IconFile style={{ color: '#ea580c' }} />;
    case 'code':
      return <IconFile style={{ color: '#6366f1' }} />;
    default:
      return <IconFile style={{ color: 'var(--ok-text-tertiary)' }} />;
  }
}

interface FileTreeItemProps {
  entry: FileEntry;
  depth: number;
  onFileClick: (entry: FileEntry) => void;
  onDirClick: (entry: FileEntry) => void;
}

const FileTreeItem: React.FC<FileTreeItemProps> = ({
  entry,
  depth,
  onFileClick,
  onDirClick,
}) => {
  const [expanded, setExpanded] = useState(false);
  const [children, setChildren] = useState<FileEntry[]>([]);
  const [loading, setLoading] = useState(false);

  const handleClick = useCallback(async () => {
    if (entry.isDirectory) {
      if (!expanded && children.length === 0) {
        setLoading(true);
        try {
          const items = await api.files.listDirectory(entry.path);
          setChildren(items);
        } catch {
          // directory listing may fail
        } finally {
          setLoading(false);
        }
      }
      setExpanded(!expanded);
      onDirClick(entry);
    } else {
      onFileClick(entry);
    }
  }, [entry, expanded, children.length, onFileClick, onDirClick]);

  return (
    <div>
      <div
        className="flex items-center gap-1"
        style={{
          paddingLeft: depth * 16 + 4,
          paddingRight: 4,
          paddingTop: 2,
          paddingBottom: 2,
          cursor: 'pointer',
          borderRadius: 'var(--ok-radius-sm)',
          fontSize: 12,
        }}
        onClick={handleClick}
        onMouseEnter={(e) => {
          e.currentTarget.style.background = 'var(--ok-bg-secondary)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = 'transparent';
        }}
      >
        {entry.isDirectory ? (
          <IconFolder style={{
            color: '#eab308',
            fontSize: 16,
            flexShrink: 0,
            transform: expanded ? 'rotate(-90deg)' : 'none',
            transition: 'transform 0.15s',
          }} />
        ) : (
          <span style={{ flexShrink: 0 }}>{fileTypeIcon(entry.fileType)}</span>
        )}
        <Text
          className="text-xs"
          ellipsis
          style={{ flex: 1 }}
        >
          {entry.name}
        </Text>
        {loading && <Spin size={12} />}
      </div>

      {expanded && children.length > 0 && (
        <div>
          {children.map((child) => (
            <FileTreeItem
              key={child.path}
              entry={child}
              depth={depth + 1}
              onFileClick={onFileClick}
              onDirClick={onDirClick}
            />
          ))}
        </div>
      )}
    </div>
  );
};

interface FileBrowserPanelProps {
  onFileSelect: (entry: FileEntry) => void;
  initialPath?: string;
}

const FileBrowserPanel: React.FC<FileBrowserPanelProps> = ({
  onFileSelect,
  initialPath,
}) => {
  const [rootPath, setRootPath] = useState(initialPath ?? '');
  const [entries, setEntries] = useState<FileEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadDirectory = useCallback(async (path: string) => {
    if (!path) return;
    setLoading(true);
    setError(null);
    try {
      const items = await api.files.listDirectory(path);
      setEntries(items);
    } catch (err) {
      setError('Failed to load directory');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (rootPath) {
      loadDirectory(rootPath);
    }
  }, [rootPath, loadDirectory]);

  const handleSelectDirectory = useCallback(async () => {
    try {
      const dir = await api.files.selectDirectory();
      if (dir) {
        setRootPath(dir);
      }
    } catch {
      // dialog cancelled
    }
  }, []);

  const handleDirClick = useCallback(() => {
    // could track current directory for breadcrumb
  }, []);

  return (
    <div
      className="flex-col"
      style={{
        height: '100%',
        borderRight: '1px solid var(--ok-border-light)',
        background: 'var(--ok-bg)',
      }}
    >
      {/* Directory selector */}
      <div
        className="flex items-center gap-1"
        style={{ padding: '8px 8px 4px', borderBottom: '1px solid var(--ok-border-light)' }}
      >
        <Input
          value={rootPath}
          onChange={setRootPath}
          placeholder="Directory path..."
          size="mini"
          style={{ flex: 1 }}
          onKeyDown={(e) => {
            if (e.key === 'Enter') loadDirectory(rootPath);
          }}
        />
        <Button
          size="mini"
          icon={<IconRefresh />}
          onClick={() => loadDirectory(rootPath)}
          disabled={!rootPath}
        />
        <Button size="mini" onClick={handleSelectDirectory}>
          ...
        </Button>
      </div>

      {/* File tree */}
      <div style={{ flex: 1, overflow: 'auto', padding: '4px 0' }}>
        {loading && (
          <div className="flex items-center justify-center" style={{ padding: 24 }}>
            <Spin tip="Loading..." />
          </div>
        )}

        {error && (
          <div style={{ padding: 8 }}>
            <Text className="text-xs" style={{ color: 'var(--ok-danger)' }}>
              {error}
            </Text>
          </div>
        )}

        {!loading && !error && entries.length === 0 && rootPath && (
          <div style={{ padding: 8 }}>
            <Text className="text-xs text-tertiary">
              Empty directory
            </Text>
          </div>
        )}

        {!rootPath && (
          <div
            className="flex items-center justify-center"
            style={{ padding: 24 }}
          >
            <Text className="text-xs text-tertiary">
              Select a directory to browse files
            </Text>
          </div>
        )}

        {entries.map((entry) => (
          <FileTreeItem
            key={entry.path}
            entry={entry}
            depth={0}
            onFileClick={onFileSelect}
            onDirClick={handleDirClick}
          />
        ))}
      </div>
    </div>
  );
};

export default FileBrowserPanel;
