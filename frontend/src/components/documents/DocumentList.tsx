import { useState, useEffect, useCallback } from 'react'
import toast from 'react-hot-toast'
import { Trash2, RefreshCw, Layers, FileText, File } from 'lucide-react'
import { listDocuments, deleteDocument, reindexDocument } from '../../api/client'
import type { Document } from '../../types'
import StatusBadge from '../ui/StatusBadge'
import { formatDistanceToNow } from 'date-fns'

function formatBytes(b: number) {
  if (b < 1024) return `${b} B`
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`
  return `${(b / 1024 / 1024).toFixed(1)} MB`
}

function DocIcon({ contentType }: { contentType: string }) {
  if (contentType.includes('pdf')) return <FileText size={15} className="doc-filename-icon" />
  if (contentType.includes('word')) return <File size={15} className="doc-filename-icon" />
  return <File size={15} className="doc-filename-icon" />
}

interface Props {
  refreshKey?: number
}

export default function DocumentList({ refreshKey }: Props) {
  const [docs, setDocs] = useState<Document[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [deleting, setDeleting] = useState<string | null>(null)
  const [reindexing, setReindexing] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      const res = await listDocuments()
      setDocs(res.items)
      setTotal(res.total)
    } catch {
      toast.error('Failed to load documents')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load, refreshKey])

  // Auto-refresh while any doc is processing/queued
  useEffect(() => {
    const hasInFlight = docs.some(d => d.status === 'queued' || d.status === 'processing')
    if (!hasInFlight) return
    const id = setInterval(load, 4000)
    return () => clearInterval(id)
  }, [docs, load])

  const handleDelete = async (id: string, filename: string) => {
    if (!confirm(`Delete "${filename}"? This will also remove all chunks.`)) return
    setDeleting(id)
    try {
      await deleteDocument(id)
      toast.success(`Deleted "${filename}"`)
      load()
    } catch {
      toast.error('Delete failed')
    } finally {
      setDeleting(null)
    }
  }

  const handleReindex = async (id: string) => {
    setReindexing(id)
    try {
      await reindexDocument(id)
      toast.success('Reindex queued')
      load()
    } catch {
      toast.error('Reindex failed')
    } finally {
      setReindexing(null)
    }
  }

  if (loading) {
    return (
      <div className="loading-overlay">
        <div className="spinner spinner-lg" />
        <span>Loading documents…</span>
      </div>
    )
  }

  if (!docs.length) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">📂</div>
        <div className="empty-state-title">No documents yet</div>
        <div className="empty-state-desc">Upload a PDF, DOCX, or TXT file above to get started.</div>
      </div>
    )
  }

  return (
    <>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
        <h3 style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
          {total} document{total !== 1 ? 's' : ''} total
        </h3>
        <button className="btn btn-ghost btn-sm" onClick={load}>
          <RefreshCw size={13} /> Refresh
        </button>
      </div>
      <div className="doc-table-wrap">
        <table className="doc-table">
          <thead>
            <tr>
              <th>Filename</th>
              <th>Status</th>
              <th>Size</th>
              <th>Uploaded</th>
              <th>Document ID</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {docs.map(doc => (
              <tr key={doc.document_id}>
                <td>
                  <div className="doc-filename">
                    <DocIcon contentType={doc.content_type} />
                    {doc.filename}
                  </div>
                </td>
                <td><StatusBadge status={doc.status} /></td>
                <td className="doc-size">{formatBytes(doc.file_size_bytes)}</td>
                <td className="doc-size">
                  {formatDistanceToNow(new Date(doc.created_at), { addSuffix: true })}
                </td>
                <td className="doc-id">{doc.document_id}</td>
                <td>
                  <div className="doc-actions">
                    <button
                      className="btn btn-ghost btn-sm btn-icon"
                      title="Re-index"
                      disabled={reindexing === doc.document_id}
                      onClick={() => handleReindex(doc.document_id)}
                    >
                      {reindexing === doc.document_id
                        ? <div className="spinner" />
                        : <Layers size={14} />}
                    </button>
                    <button
                      className="btn btn-danger btn-sm btn-icon"
                      title="Delete"
                      disabled={deleting === doc.document_id}
                      onClick={() => handleDelete(doc.document_id, doc.filename)}
                    >
                      {deleting === doc.document_id
                        ? <div className="spinner" />
                        : <Trash2 size={14} />}
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  )
}
