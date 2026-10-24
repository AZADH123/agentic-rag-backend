import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import toast from 'react-hot-toast'
import { Upload, File } from 'lucide-react'
import { uploadDocument } from '../../api/client'
import type { DocumentUploadResponse } from '../../types'

interface Props {
  onUploaded?: (res: DocumentUploadResponse) => void
}

const ACCEPTED = {
  'application/pdf': ['.pdf'],
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
  'text/plain': ['.txt'],
}

export default function UploadZone({ onUploaded }: Props) {
  const [uploading, setUploading] = useState(false)
  const [fileName, setFileName] = useState<string | null>(null)

  const onDrop = useCallback(async (accepted: File[]) => {
    if (!accepted.length) return
    const file = accepted[0]
    setFileName(file.name)
    setUploading(true)
    try {
      const res = await uploadDocument(file)
      toast.success(`"${res.filename}" uploaded — job ${res.job_id.slice(0, 12)}…`)
      onUploaded?.(res)
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail ?? 'Upload failed'
      toast.error(msg)
    } finally {
      setUploading(false)
      setFileName(null)
    }
  }, [onUploaded])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPTED,
    maxFiles: 1,
    disabled: uploading,
    maxSize: 20 * 1024 * 1024,
  })

  return (
    <div {...getRootProps()} className={`dropzone${isDragActive ? ' active' : ''}`}>
      <input {...getInputProps()} />
      <div className="dropzone-icon">
        {uploading ? (
          <div className="spinner" />
        ) : (
          <Upload size={24} color="var(--accent-light)" />
        )}
      </div>

      {uploading ? (
        <>
          <div className="dropzone-title">
            <File size={14} style={{ display: 'inline', marginRight: 4 }} />
            {fileName}
          </div>
          <div className="dropzone-subtitle">Uploading & queueing ingestion…</div>
          <div className="upload-progress">
            <div className="progress-bar"><div className="progress-fill" style={{ width: '100%' }} /></div>
          </div>
        </>
      ) : (
        <>
          <div className="dropzone-title">
            {isDragActive ? 'Drop file here' : 'Drag & drop a document, or click to browse'}
          </div>
          <div className="dropzone-subtitle">Max 20 MB per file</div>
          <div className="dropzone-types">
            {['PDF', 'DOCX', 'TXT'].map(t => (
              <span key={t} className="dropzone-type-tag">{t}</span>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
