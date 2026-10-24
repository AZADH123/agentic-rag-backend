import ChatInterface from '../components/chat/ChatInterface'

export default function ChatPage() {
  return (
    <>
      <div className="page-header" style={{ flexShrink: 0 }}>
        <div className="page-header-left">
          <h1 className="page-header-title">Chat</h1>
          <span className="page-header-desc">
            Agentic RAG powered by Gemini + MCP tools (search, calculator, weather)
          </span>
        </div>
      </div>
      <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        <ChatInterface />
      </div>
    </>
  )
}
