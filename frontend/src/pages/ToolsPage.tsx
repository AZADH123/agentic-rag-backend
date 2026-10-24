import { useEffect, useState } from 'react'
import { listTools } from '../api/client'
import type { Tool } from '../types'
import toast from 'react-hot-toast'

const toolIcons: Record<string, string> = {
  search_documents: '🔍',
  calculate:        '🧮',
  get_weather:      '🌤️',
}

function getToolIcon(name: string) {
  return toolIcons[name] ?? '🔧'
}

export default function ToolsPage() {
  const [tools, setTools] = useState<Tool[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    listTools()
      .then(r => setTools(r.tools))
      .catch(() => toast.error('Failed to load MCP tools'))
      .finally(() => setLoading(false))
  }, [])

  return (
    <>
      <div className="page-header">
        <div className="page-header-left">
          <h1 className="page-header-title">MCP Tools</h1>
          <span className="page-header-desc">
            Tools available to the Gemini agent via the Model Context Protocol
          </span>
        </div>
      </div>
      <div className="page-content fade-up">
        {loading ? (
          <div className="loading-overlay">
            <div className="spinner spinner-lg" />
            <span>Loading tools…</span>
          </div>
        ) : !tools.length ? (
          <div className="empty-state">
            <div className="empty-state-icon">🔧</div>
            <div className="empty-state-title">No tools available</div>
            <div className="empty-state-desc">
              MCP servers may not have started. Check the API logs for <code>mcp_init_failed</code>.
            </div>
          </div>
        ) : (
          <>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '1.25rem' }}>
              {tools.length} tool{tools.length !== 1 ? 's' : ''} registered — these are automatically
              offered to the agent during every chat request.
            </p>
            <div className="tools-grid">
              {tools.map(tool => (
                <div key={tool.name} className="tool-card">
                  <div className="tool-card-header">
                    <div className="tool-card-icon">{getToolIcon(tool.name)}</div>
                    <div>
                      <div className="tool-card-name">{tool.name}</div>
                    </div>
                  </div>
                  <div className="tool-card-desc">
                    {tool.description ?? 'No description provided.'}
                  </div>
                  {tool.input_schema && (
                    <div style={{ marginTop: '0.75rem' }}>
                      <h4 style={{ marginBottom: '0.4rem' }}>Input Schema</h4>
                      <pre
                        style={{
                          background: 'var(--bg-elevated)',
                          border: '1px solid var(--border)',
                          borderRadius: 'var(--radius-md)',
                          padding: '0.65rem 0.85rem',
                          fontSize: '0.73rem',
                          color: 'var(--text-muted)',
                          overflowX: 'auto',
                          whiteSpace: 'pre-wrap',
                        }}
                      >
                        {JSON.stringify(tool.input_schema, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </>
  )
}
