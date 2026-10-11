export const StatusBadge = ({ status }) => {
  const map = {
    pending: 'badge-pending',
    confirmed: 'badge-confirmed',
    rejected: 'badge-rejected',
    active: 'badge-active',
    inactive: 'badge-inactive',
    processing: 'badge-processing',
    completed: 'badge-completed',
    completed_with_errors: 'badge-completed-errors',
    completed_with_errors_alt: 'badge-completed-errors',
    failed: 'badge-failed',
    model_unavailable: 'badge-model-unavailable',
  }

  const labelMap = {
    completed_with_errors: 'COMPLETED WITH ERRORS',
    model_unavailable: 'MODEL UNAVAILABLE',
    pending: 'PENDING',
    confirmed: 'CONFIRMED',
    rejected: 'REJECTED',
    active: 'ACTIVE',
    inactive: 'INACTIVE',
    processing: 'PROCESSING',
    completed: 'COMPLETED',
    failed: 'FAILED',
  }

  const normalized = status ? String(status).toLowerCase() : ''
  const cls = map[normalized] || 'badge-inactive'
  const label = labelMap[normalized] || (status ? String(status).toUpperCase() : 'UNKNOWN')

  return <span className={`badge-base ${cls}`}>{label}</span>
}

export const ActiveBadge = ({ active }) => (
  <span className={`badge-base ${active ? 'badge-active' : 'badge-inactive'}`}>
    {active ? 'ACTIVE' : 'INACTIVE'}
  </span>
)

export default StatusBadge
