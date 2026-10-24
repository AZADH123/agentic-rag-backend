import { useEffect, useState } from 'react'
import { FileText, MessageSquare, Database, Activity } from 'lucide-react'
import { listDocuments, listConversations, getReady } from '../api/client'
import type { ReadyResponse } from '../types'
import { useNavigate } from 'react-router-dom'

interface StatItem {
  label: string
  value: number | string
  icon: React.ReactNode
  colorClass: string
  onClick?: () => void
}

export default function DashboardPage() {
  const navigate = useNavigate()
  const [docCount, setDocCount] = useState<number | null>(null)
  const [convCount, setConvCount] = useState<number | null>(null)
  const [health, setHealth] = useState<ReadyResponse | null>(null)
  const [indexedCount, setIndexedCount] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.allSettled([
      listDocuments(200).then(r => {
        setDocCount(r.total)
        setIndexedCount(r.items.filter(d => d.status === 'indexed').length)
      }),
      listConversations().then(r => setConvCount(r.total)),
      getReady().then(r => setHealth(r)),
    ]).finally(() => setLoading(false))
  }, [])

  const stats: StatItem[] = [
    {
      label: 'Total Documents',
      value: loading ? '…' : docCount ?? 0,
      icon: <FileText size={20} />,
      colorClass: 'stat-blue',
      onClick: () => navigate('/documents'),
    },
    {
      label: 'Indexed Documents',
      value: loading ? '…' : indexedCount ?? 0,
      icon: <Database size={20} />,
      colorClass: 'stat-green',
      onClick: () => navigate('/documents'),
    },
    {
      label: 'Conversations',
      value: loading ? '…' : convCount ?? 0,
      icon: <MessageSquare size={20} />,
      colorClass: 'stat-purple',
      onClick: () => navigate('/chat'),
    },
    {
      label: 'Backend Status',
      value: health
        ? Object.values(health.components).every(v => v === 'ok')
          ? 'Healthy'
          : 'Degraded'
        : loading ? '…' : 'Offline',
      icon: <Activity size={20} />,
      colorClass: health
        ? Object.values(health.components).every(v => v === 'ok')
          ? 'stat-green'
          : 'stat-yellow'
        : 'stat-yellow',
    },
  ]

  return (
    <>
      <div className="page-header">
        <div className="page-header-left">
          <h1 className="page-header-title">Dashboard</h1>
          <span className="page-header-desc">Overview of your Agentic RAG system</span>
        </div>
      </div>
      <div className="page-content fade-up">
        {/* Stats */}
        <div className="stats-grid">
          {stats.map(s => (
            <div
              key={s.label}
              className={`stat-card ${s.colorClass}`}
              style={{ cursor: s.onClick ? 'pointer' : 'default' }}
              onClick={s.onClick}
            >
              <div className="stat-card-icon">{s.icon}</div>
              <div className="stat-value">{s.value}</div>
              <div className="stat-label">{s.label}</div>
            </div>
          ))}
        </div>

        {/* Health breakdown */}
        {health && (
          <div className="card" style={{ marginTop: '0.5rem' }}>
            <div className="card-header">
              <h3>System Health</h3>
              <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                Live readiness check from <code>/api/v1/health/ready</code>
              </span>
            </div>
            <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
              {Object.entries(health.components).map(([name, status]) => (
                <div
                  key={name}
                  style={{
                    display: 'flex', alignItems: 'center', gap: '0.5rem',
                    padding: '0.6rem 1rem',
                    background: 'var(--bg-elevated)',
                    border: `1px solid ${status === 'ok' ? 'rgba(16,185,129,0.3)' : 'rgba(245,158,11,0.3)'}`,
                    borderRadius: 'var(--radius-md)',
                  }}
                >
                  <span style={{
                    width: 8, height: 8, borderRadius: '50%',
                    background: status === 'ok' ? 'var(--green)' : 'var(--yellow)',
                    boxShadow: status === 'ok' ? '0 0 6px var(--green-glow)' : '0 0 6px var(--yellow-glow)',
                  }} />
                  <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)' }}>{name}</span>
                  <span style={{ fontSize: '0.78rem', color: status === 'ok' ? 'var(--green)' : 'var(--yellow)' }}>{status}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Quick actions */}
        <div className="card" style={{ marginTop: '1rem' }}>
          <div className="card-header">
            <h3>Quick Actions</h3>
          </div>
          <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
            <button className="btn btn-primary" onClick={() => navigate('/documents')}>
              <FileText size={15} /> Upload Document
            </button>
            <button className="btn btn-secondary" onClick={() => navigate('/chat')}>
              <MessageSquare size={15} /> Start Chat
            </button>
            <button className="btn btn-secondary" onClick={() => navigate('/retrieval')}>
              Semantic Search
            </button>
            <button className="btn btn-secondary" onClick={() => navigate('/tools')}>
              View MCP Tools
            </button>
          </div>
        </div>

        {/* Architecture note */}
        <div className="card" style={{ marginTop: '1rem', borderColor: 'rgba(59,130,246,0.2)' }}>
          <div className="card-header">
            <h3>Architecture</h3>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
            {[
              ['📤 Upload', 'POST /documents/upload → validates → MinIO S3 → queues Redis task'],
              ['⚙️ Ingestion', 'Taskiq worker → parse (pypdf/docx) → BGE embed → pgvector upsert'],
              ['🔍 Retrieval', 'POST /retrieval/search → cosine similarity → rerank → citations'],
              ['🤖 Agent Loop', 'POST /chat → Gemini → MCP tools (RAG, calc, weather) → persist'],
            ].map(([step, desc]) => (
              <div key={step} style={{ display: 'flex', gap: '1rem', alignItems: 'flex-start' }}>
                <span style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--accent-light)', minWidth: 100, flexShrink: 0 }}>{step}</span>
                <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>{desc}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </>
  )
}
