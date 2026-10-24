import { NavLink, useLocation } from 'react-router-dom'
import { useEffect, useState } from 'react'
import {
  LayoutDashboard,
  FileText,
  MessageSquare,
  Search,
  Wrench,
  Brain,
  Key,
  Check,
} from 'lucide-react'
import { getReady, getApiKey, setApiKey } from '../../api/client'
import type { ReadyResponse } from '../../types'

const navItems = [
  { to: '/dashboard',  label: 'Dashboard',  Icon: LayoutDashboard },
  { to: '/documents',  label: 'Documents',   Icon: FileText },
  { to: '/chat',       label: 'Chat',        Icon: MessageSquare },
  { to: '/retrieval',  label: 'Retrieval',   Icon: Search },
  { to: '/tools',      label: 'MCP Tools',   Icon: Wrench },
]

export default function Sidebar() {
  const location = useLocation()
  const [health, setHealth] = useState<ReadyResponse | null>(null)
  const [apiKeyVal, setApiKeyVal] = useState(getApiKey())
  const [showKeyEdit, setShowKeyEdit] = useState(false)
  const [savedKey, setSavedKey] = useState(false)

  useEffect(() => {
    const check = async () => {
      try {
        const data = await getReady()
        setHealth(data)
      } catch {
        setHealth(null)
      }
    }
    check()
    const id = setInterval(check, 30_000)
    return () => clearInterval(id)
  }, [])

  const handleSaveKey = () => {
    setApiKey(apiKeyVal.trim())
    setSavedKey(true)
    setTimeout(() => {
      setSavedKey(false)
      setShowKeyEdit(false)
    }, 1200)
  }

  const allOk = health?.components
    ? Object.values(health.components).every(v => v === 'ok')
    : false

  const anyDegraded = health?.components
    ? Object.values(health.components).some(v => v !== 'ok')
    : false

  const dotClass = health
    ? allOk ? 'ok' : anyDegraded ? 'degraded' : 'error'
    : ''

  const healthText = health
    ? allOk
      ? 'All systems operational'
      : `Degraded: ${Object.entries(health.components).filter(([, v]) => v !== 'ok').map(([k]) => k).join(', ')}`
    : 'Checking backend…'

  return (
    <aside className="sidebar">
      {/* Logo */}
      <div className="sidebar-logo">
        <div className="sidebar-logo-icon">
          <Brain size={18} color="#fff" />
        </div>
        <div className="sidebar-logo-text">
          <span className="sidebar-logo-title">AgenticRAG</span>
          <span className="sidebar-logo-subtitle">Document Intelligence</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="sidebar-nav">
        <div className="nav-section-label">Navigation</div>
        {navItems.map(({ to, label, Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `nav-item${isActive || location.pathname.startsWith(to) ? ' active' : ''}`
            }
          >
            <Icon size={17} className="nav-item-icon" />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Footer: API Key & Health status */}
      <div className="sidebar-footer">
        {/* API Key configuration */}
        <div style={{ marginBottom: '0.65rem' }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              fontSize: '0.73rem',
              color: 'var(--text-dim)',
              cursor: 'pointer',
              userSelect: 'none',
            }}
            onClick={() => setShowKeyEdit(prev => !prev)}
          >
            <span style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
              <Key size={12} color="var(--accent-light)" />
              <span>API Key: <strong style={{ color: 'var(--text-secondary)' }}>{apiKeyVal ? '••••' + apiKeyVal.slice(-3) : 'none'}</strong></span>
            </span>
            <span style={{ fontSize: '0.68rem', color: 'var(--accent-light)' }}>
              {showKeyEdit ? 'close' : 'change'}
            </span>
          </div>

          {showKeyEdit && (
            <div style={{ marginTop: '0.4rem', display: 'flex', gap: '4px' }}>
              <input
                type="password"
                placeholder="Enter API Key"
                value={apiKeyVal}
                onChange={e => setApiKeyVal(e.target.value)}
                style={{
                  flex: 1,
                  background: 'var(--bg-input)',
                  border: '1px solid var(--border-light)',
                  borderRadius: 'var(--radius-sm)',
                  padding: '0.25rem 0.5rem',
                  fontSize: '0.75rem',
                  color: '#fff',
                  outline: 'none',
                }}
              />
              <button
                className="btn btn-primary btn-sm btn-icon"
                onClick={handleSaveKey}
                title="Save Key"
                style={{ padding: '0.25rem 0.45rem' }}
              >
                {savedKey ? <Check size={12} /> : 'Save'}
              </button>
            </div>
          )}
        </div>

        {/* Health status */}
        <div className="health-badge">
          <span className={`health-dot ${dotClass}`} />
          <span>{healthText}</span>
        </div>
      </div>
    </aside>
  )
}
