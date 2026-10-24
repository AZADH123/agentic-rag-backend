import { Routes, Route, Navigate } from 'react-router-dom'
import Sidebar from './components/layout/Sidebar'
import {
  DashboardPage,
  DocumentsPage,
  ChatPage,
  RetrievalPage,
  ToolsPage,
} from './pages'

export default function App() {
  return (
    <div className="app-shell">
      <Sidebar />
      <div className="main-area">
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/documents" element={<DocumentsPage />} />
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/chat/:conversationId" element={<ChatPage />} />
          <Route path="/retrieval" element={<RetrievalPage />} />
          <Route path="/tools" element={<ToolsPage />} />
        </Routes>
      </div>
    </div>
  )
}
