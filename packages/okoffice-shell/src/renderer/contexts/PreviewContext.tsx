import React, { createContext, useContext, useState } from 'react';
import type { FileEntry } from '@shared/types';

interface PreviewContextValue {
  previewFile: FileEntry | null;
  setPreviewFile: (file: FileEntry | null) => void;
}

const PreviewContext = createContext<PreviewContextValue>({
  previewFile: null,
  setPreviewFile: () => {},
});

export function usePreview() {
  return useContext(PreviewContext);
}

export function PreviewProvider({ children }: { children: React.ReactNode }) {
  const [previewFile, setPreviewFile] = useState<FileEntry | null>(null);

  return (
    <PreviewContext.Provider value={{ previewFile, setPreviewFile }}>
      {children}
    </PreviewContext.Provider>
  );
}

export default PreviewContext;
