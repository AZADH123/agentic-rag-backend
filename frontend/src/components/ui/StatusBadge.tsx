import type { DocumentStatus } from '../../types'

interface Props {
  status: DocumentStatus | string
}

const labels: Record<string, string> = {
  indexed:    'Indexed',
  queued:     'Queued',
  processing: 'Processing',
  uploaded:   'Uploaded',
  failed:     'Failed',
  completed:  'Completed',
  error:      'Error',
  success:    'Success',
  skipped:    'Skipped',
}

export default function StatusBadge({ status }: Props) {
  const label = labels[status] ?? status
  return (
    <span className={`badge badge-${status}`}>
      <span className="badge-dot" />
      {label}
    </span>
  )
}
