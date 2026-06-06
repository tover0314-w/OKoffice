import React, { useState, useEffect, useCallback } from 'react';
import { Typography, Spin } from '@arco-design/web-react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import api from '../../api/bridge';

const { Text } = Typography;

function detectLanguage(path: string): string {
  const ext = path.split('.').pop()?.toLowerCase() ?? '';
  const langMap: Record<string, string> = {
    ts: 'typescript',
    tsx: 'tsx',
    js: 'javascript',
    jsx: 'jsx',
    py: 'python',
    go: 'go',
    rs: 'rust',
    java: 'java',
    json: 'json',
    yaml: 'yaml',
    yml: 'yaml',
    md: 'markdown',
    html: 'html',
    css: 'css',
    sql: 'sql',
    sh: 'bash',
    bash: 'bash',
  };
  return langMap[ext] ?? 'text';
}

interface TextViewerProps {
  filePath: string;
}

const TextViewer: React.FC<TextViewerProps> = ({ filePath }) => {
  const [content, setContent] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadContent = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const text = await api.preview.extractText(filePath);
      setContent(text);
    } catch {
      setError('Failed to load text');
    } finally {
      setLoading(false);
    }
  }, [filePath]);

  useEffect(() => {
    loadContent();
  }, [loadContent]);

  if (loading) {
    return (
      <div className="flex items-center justify-center" style={{ padding: 24 }}>
        <Spin tip="Loading..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center" style={{ padding: 24 }}>
        <Text style={{ color: 'var(--ok-danger)' }}>{error}</Text>
      </div>
    );
  }

  if (!content) return null;

  const language = detectLanguage(filePath);

  return (
    <div
      style={{
        height: '100%',
        overflow: 'auto',
        background: '#1e1e1e',
      }}
    >
      <SyntaxHighlighter
        language={language}
        style={oneDark}
        showLineNumbers
        wrapLines
        customStyle={{
          margin: 0,
          padding: 12,
          fontSize: 12,
          background: 'transparent',
        }}
      >
        {content}
      </SyntaxHighlighter>
    </div>
  );
};

export default TextViewer;
