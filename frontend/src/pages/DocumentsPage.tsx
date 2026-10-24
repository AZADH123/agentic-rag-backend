import { useState } from 'react'
import { Upload } from 'lucide-react'
import UploadZone from '../components/documents/UploadZone'
import DocumentList from '../components/documents/DocumentList'
import type { DocumentUploadResponse } from '../types'

export default function DocumentsPage() {
  const [refreshKey, setRefreshKey] = useState(0)

  const handleUploaded = (_res: DocumentUploadResponse) => {
    setRefreshKey(k => k + 1)
  }

  return (
    <>
      <div className="page-header">
        <div className="page-header-left">
          <h1 className="page-header-title">Documents</h1>
          <span className="page-header-desc">Upload and manage your knowledge base documents</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
          <Upload size={13} /> PDF · DOCX · TXT · up to 20 MB
        </div>
      </div>

      <div className="page-content fade-up">
        {/* Upload zone */}
        <div className="card" style={{ marginBottom: '1.5rem' }}>
          <div className="card-header">
            <h3>Upload Document</h3>
            <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
              Files are parsed, chunked, embedded, and indexed automatically
            </span>
          </div>
          <UploadZone onUploaded={handleUploaded} />
        </div>

        {/* Document list */}
        <div className="card">
          <div className="card-header">
            <h3>Document Library</h3>
          </div>
          <DocumentList refreshKey={refreshKey} />
        </div>
      </div>
    </>
  )
}
