import React, { useState, useCallback, useRef } from 'react';
import { Input, Button, Typography, Tag } from '@arco-design/web-react';
import { IconSend, IconStop, IconPlus, IconClose, IconFile } from '@arco-design/web-react/icon';

const { Text } = Typography;
const { TextArea } = Input;

interface AttachedFile {
  path: string;
  name: string;
}

interface SendBoxProps {
  disabled?: boolean;
  streaming?: boolean;
  onSend: (content: string, attachments: AttachedFile[]) => void;
  onStop: () => void;
}

const SendBox: React.FC<SendBoxProps> = ({ disabled, streaming, onSend, onStop }) => {
  const [inputValue, setInputValue] = useState('');
  const [attachments, setAttachments] = useState<AttachedFile[]>([]);
  const textAreaRef = useRef<HTMLTextAreaElement | null>(null);

  const handleSend = useCallback(() => {
    const content = inputValue.trim();
    if (!content && attachments.length === 0) return;
    onSend(content, attachments);
    setInputValue('');
    setAttachments([]);
  }, [inputValue, attachments, onSend]);

  const handleStop = useCallback(() => {
    onStop();
  }, [onStop]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleAttachFile = useCallback(async () => {
    try {
      const api = (window as unknown as { okoffice: { files: { selectFile: (f?: Array<{ name: string; extensions: string[] }>) => Promise<string[] | null> } } }).okoffice;
      const paths = await api.files.selectFile([
        { name: 'Documents', extensions: ['pdf', 'docx', 'xlsx', 'pptx'] },
        { name: 'Images', extensions: ['png', 'jpg', 'jpeg', 'gif', 'webp'] },
        { name: 'All Files', extensions: ['*'] },
      ]);
      if (paths) {
        const newFiles: AttachedFile[] = paths.map((p) => ({
          path: p,
          name: p.split(/[/\\]/).pop() ?? p,
        }));
        setAttachments((prev) => [...prev, ...newFiles]);
      }
    } catch {
      // dialog cancelled
    }
  }, []);

  const handleRemoveAttachment = useCallback((index: number) => {
    setAttachments((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const canSend = inputValue.trim().length > 0 || attachments.length > 0;

  return (
    <div
      style={{
        padding: '8px 24px 16px',
        borderTop: '1px solid var(--ok-border-light)',
        background: 'var(--ok-bg)',
      }}
    >
      {/* Attachment chips */}
      {attachments.length > 0 && (
        <div className="flex flex-wrap gap-1" style={{ marginBottom: 8 }}>
          {attachments.map((a, i) => (
            <Tag
              key={`${a.path}-${i}`}
              closable
              onClose={() => handleRemoveAttachment(i)}
              style={{ fontSize: 11 }}
            >
              <IconFile style={{ marginRight: 4 }} />
              {a.name}
            </Tag>
          ))}
        </div>
      )}

      <div className="flex items-end gap-2">
        <Button
          type="text"
          size="small"
          icon={<IconPlus />}
          onClick={handleAttachFile}
          title="Attach file"
          disabled={disabled || streaming}
        />
        <TextArea
          ref={textAreaRef as never}
          value={inputValue}
          onChange={setInputValue}
          onKeyDown={handleKeyDown}
          placeholder="Type a message or ask about a document..."
          autoSize={{ minRows: 1, maxRows: 6 }}
          style={{ flex: 1 }}
          disabled={disabled}
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
            disabled={!canSend}
          />
        )}
      </div>
    </div>
  );
};

export default SendBox;
