import { useEffect, useRef, useState, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import toast from 'react-hot-toast'
import { Send, Plus, Trash2, Bot, User } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import {
  sendChat,
  listConversations,
  getConversation,
  deleteConversation,
} from '../../api/client'
import type {
  ConversationResponse,
  MessageResponse,
  Citation,
  ToolCallRecord,
} from '../../types'
import StatusBadge from '../ui/StatusBadge'

// ─── Citation Chips ────────────────────────────────────────────────────────────
function CitationChips({ citations }: { citations: Citation[] }) {
  if (!citations.length) return null
  return (
    <div className="citations-block">
      {citations.map(c => (
        <div key={c.chunk_id} className="citation-chip" title={c.snippet ?? ''}>
          <span className="citation-icon">📄</span>
          <span className="citation-filename">{c.filename ?? c.document_id.slice(0, 12)}</span>
          {c.page != null && <span className="citation-page">p.{c.page}</span>}
          {c.snippet && (
            <span style={{ color: 'var(--text-dim)', fontSize: '0.72rem', marginLeft: 4, maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              — {c.snippet}
            </span>
          )}
        </div>
      ))}
    </div>
  )
}

// ─── Tool Call Chips ───────────────────────────────────────────────────────────
function ToolChips({ toolCalls, steps }: { toolCalls: ToolCallRecord[]; steps: number }) {
  if (!toolCalls.length) return null
  return (
    <div className="tool-calls-block">
      {toolCalls.map((t, i) => (
        <div key={i} className={`tool-chip ${t.status}`}>
          🔧 {t.tool_name}
          <StatusBadge status={t.status} />
        </div>
      ))}
      <span className="steps-badge">{steps} step{steps !== 1 ? 's' : ''}</span>
    </div>
  )
}

// ─── Single message bubble ─────────────────────────────────────────────────────
function ChatMessage({ msg }: { msg: MessageResponse }) {
  const isUser = msg.role === 'user'
  return (
    <div className={`message ${msg.role} fade-up`}>
      <div className="message-avatar">
        {isUser ? <User size={15} /> : <Bot size={15} />}
      </div>
      <div className="message-body">
        <div className="message-bubble">
          {isUser ? (
            msg.content
          ) : (
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
          )}
        </div>
        {!isUser && msg.citations.length > 0 && (
          <CitationChips citations={msg.citations} />
        )}
        {!isUser && msg.tool_calls.length > 0 && (
          <ToolChips toolCalls={msg.tool_calls} steps={0} />
        )}
        <div className="message-meta">
          {formatDistanceToNow(new Date(msg.created_at), { addSuffix: true })}
        </div>
      </div>
    </div>
  )
}

// ─── Optimistic message shape ──────────────────────────────────────────────────
interface OptimisticMsg {
  id: string
  role: 'user' | 'assistant'
  content: string
  citations: Citation[]
  tool_calls: ToolCallRecord[]
  steps_taken: number
  created_at: string
}

export default function ChatInterface() {
  const { conversationId: paramConvId } = useParams()
  const navigate = useNavigate()

  const [conversations, setConversations] = useState<ConversationResponse[]>([])
  const [activeConvId, setActiveConvId] = useState<string | null>(paramConvId ?? null)
  const [messages, setMessages] = useState<OptimisticMsg[]>([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Load conversations list
  const loadConversations = useCallback(async () => {
    try {
      const res = await listConversations()
      setConversations(res.items)
    } catch {
      /* silently fail */
    }
  }, [])

  useEffect(() => { loadConversations() }, [loadConversations])

  // Load messages when conversation changes
  useEffect(() => {
    if (!activeConvId) { setMessages([]); return }
    ;(async () => {
      try {
        const conv = await getConversation(activeConvId)
        setMessages(
          conv.messages.map(m => ({
            id: m.message_id,
            role: m.role,
            content: m.content,
            citations: m.citations,
            tool_calls: m.tool_calls,
            steps_taken: 0,
            created_at: m.created_at,
          }))
        )
      } catch {
        toast.error('Failed to load conversation')
      }
    })()
  }, [activeConvId])

  // Scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, sending])

  const handleSend = async () => {
    const text = input.trim()
    if (!text || sending) return
    setInput('')

    // Optimistic user message
    const userMsg: OptimisticMsg = {
      id: `opt-user-${Date.now()}`,
      role: 'user',
      content: text,
      citations: [],
      tool_calls: [],
      steps_taken: 0,
      created_at: new Date().toISOString(),
    }
    setMessages(prev => [...prev, userMsg])
    setSending(true)

    try {
      const res = await sendChat({ message: text, conversation_id: activeConvId ?? undefined })

      // Update active conversation
      if (!activeConvId) {
        setActiveConvId(res.conversation_id)
        navigate(`/chat/${res.conversation_id}`, { replace: true })
        loadConversations()
      }

      // Append assistant response
      const assistantMsg: OptimisticMsg = {
        id: `opt-asst-${Date.now()}`,
        role: 'assistant',
        content: res.answer,
        citations: res.citations,
        tool_calls: res.tool_calls,
        steps_taken: res.steps_taken,
        created_at: new Date().toISOString(),
      }
      setMessages(prev => [...prev, assistantMsg])
      loadConversations()
    } catch (err: unknown) {
      toast.error('Failed to get response from agent')
      // Remove optimistic user message
      setMessages(prev => prev.filter(m => m.id !== userMsg.id))
    } finally {
      setSending(false)
      textareaRef.current?.focus()
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() }
  }

  const handleNewChat = () => {
    setActiveConvId(null)
    setMessages([])
    navigate('/chat', { replace: true })
  }

  const handleDeleteConversation = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    try {
      await deleteConversation(id)
      if (activeConvId === id) handleNewChat()
      loadConversations()
      toast.success('Conversation deleted')
    } catch {
      toast.error('Failed to delete conversation')
    }
  }

  // Auto-resize textarea
  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value)
    e.target.style.height = 'auto'
    e.target.style.height = Math.min(e.target.scrollHeight, 180) + 'px'
  }

  return (
    <div className="chat-layout">
      {/* Conversations panel */}
      <div className="conversations-panel">
        <div className="conversations-panel-header">
          <span style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
            Conversations
          </span>
          <button className="btn btn-ghost btn-sm btn-icon" onClick={handleNewChat} title="New chat">
            <Plus size={15} />
          </button>
        </div>
        <div className="conv-list">
          {!conversations.length && (
            <div style={{ padding: '1rem 0.5rem', fontSize: '0.78rem', color: 'var(--text-dim)', textAlign: 'center' }}>
              No conversations yet
            </div>
          )}
          {conversations.map(c => (
            <div
              key={c.conversation_id}
              className={`conv-item${activeConvId === c.conversation_id ? ' active' : ''}`}
              onClick={() => {
                setActiveConvId(c.conversation_id)
                navigate(`/chat/${c.conversation_id}`)
              }}
            >
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 4 }}>
                <div className="conv-title">
                  {c.title ?? c.conversation_id.slice(0, 20) + '…'}
                </div>
                <button
                  className="btn btn-ghost btn-sm btn-icon"
                  style={{ padding: '2px', flexShrink: 0 }}
                  onClick={(e) => handleDeleteConversation(c.conversation_id, e)}
                >
                  <Trash2 size={11} />
                </button>
              </div>
              <div className="conv-date">
                {formatDistanceToNow(new Date(c.created_at), { addSuffix: true })}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Main chat area */}
      <div className="chat-main">
        <div className="chat-messages">
          {!messages.length && !sending ? (
            <div className="chat-empty">
              <div className="chat-empty-icon">🧠</div>
              <div className="chat-empty-title">Ask the Agentic RAG system anything</div>
              <div className="chat-empty-desc">
                The agent can search your documents, perform calculations, and retrieve live weather data using MCP tools.
              </div>
            </div>
          ) : (
            messages.map(msg => (
              <div key={msg.id}>
                <ChatMessage
                  msg={{
                    message_id: msg.id,
                    conversation_id: activeConvId ?? '',
                    role: msg.role,
                    content: msg.content,
                    citations: msg.citations,
                    tool_calls: msg.tool_calls,
                    created_at: msg.created_at,
                  }}
                />
                {msg.role === 'assistant' && msg.citations.length > 0 && (
                  <CitationChips citations={msg.citations} />
                )}
                {msg.role === 'assistant' && msg.tool_calls.length > 0 && (
                  <div style={{ paddingLeft: '3rem' }}>
                    <ToolChips toolCalls={msg.tool_calls} steps={msg.steps_taken} />
                  </div>
                )}
              </div>
            ))
          )}

          {/* Typing indicator */}
          {sending && (
            <div className="message assistant fade-up">
              <div className="message-avatar"><Bot size={15} /></div>
              <div className="message-body">
                <div className="typing-indicator">
                  <div className="typing-dot" />
                  <div className="typing-dot" />
                  <div className="typing-dot" />
                </div>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div className="chat-input-area">
          <div className="chat-input-row">
            <textarea
              ref={textareaRef}
              className="chat-textarea"
              placeholder="Ask anything about your documents…"
              value={input}
              onChange={handleInput}
              onKeyDown={handleKeyDown}
              rows={1}
              disabled={sending}
            />
            <button
              className="chat-send-btn"
              onClick={handleSend}
              disabled={!input.trim() || sending}
            >
              <Send size={16} />
            </button>
          </div>
          <div className="chat-input-hint">
            Enter to send · Shift+Enter for newline · Gemini agent with MCP tools
          </div>
        </div>
      </div>
    </div>
  )
}
