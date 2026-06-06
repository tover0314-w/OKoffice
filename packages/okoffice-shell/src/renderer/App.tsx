import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ConfigProvider } from '@arco-design/web-react';
import '@arco-design/web-react/dist/css/index.css';

import AppLayout from './components/layout/AppLayout';
import ChatPage from './pages/ChatPage';
import SettingsPage from './pages/SettingsPage';
import WorkflowPage from './pages/WorkflowPage';

const App: React.FC = () => {
  return (
    <ConfigProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<AppLayout />}>
            <Route path="/" element={<ChatPage />} />
            <Route path="/workflow/:id?" element={<WorkflowPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  );
};

export default App;
