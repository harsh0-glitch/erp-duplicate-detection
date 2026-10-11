import { useEffect, useState, useCallback } from 'react'
import { getAuditLogs, getAuditActivityFeed } from '../services/audit'
import { formatDateTime } from '../utils/format'
import { LoadingState, ErrorState, EmptyState } from '../components/StateComponents'
import { TableSkeleton } from '../components/Skeletons'

const AuditTrail = () => {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [events, setEvents] = useState([])

  const loadAudit = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [logsRes, activityRes] = await Promise.allSettled([
        getAuditLogs({ page: 1, page_size: 50 }),
        getAuditActivityFeed({ limit: 50 }),
      ])

      let items = []
      if (logsRes.status === 'fulfilled') {
        items = logsRes.value.data.items || []
      } else if (activityRes.status === 'fulfilled') {
        items = activityRes.value.data.items || []
      }

      if (logsRes.status === 'rejected' && activityRes.status === 'rejected') {
        const firstErr = logsRes.reason || activityRes.reason
        setError(firstErr)
        setEvents([])
        return
      }

      setEvents(items)
    } catch (e) {
      setError(e)
      setEvents([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadAudit()
  }, [loadAudit])

  return (
    <div className="fade-in">
      <div className="page-header">
        <h2>Audit Trail</h2>
        <div className="page-subtitle">Chronological record of system and user actions</div>
      </div>

      <div className="panel-sage mb-4">
        <div className="panel-body" style={{ fontSize: '0.88rem', color: 'var(--navy)' }}>
          <strong>Note:</strong> System audit events and user decisions recorded by the backend.
          Chronological activity stream tracking product changes, bulk imports, and duplicate review actions.
        </div>
      </div>

      <div className="panel">
        {loading ? (
          <TableSkeleton rows={6} cols={5} />
        ) : error ? (
          error.type === 'network' ? (
            <EmptyState icon="—" title="Backend connection unavailable" message="Connect the backend to view audit data." />
          ) : (
            <ErrorState message={error.message || 'Failed to load audit logs.'} />
          )
        ) : events.length === 0 ? (
          <EmptyState
            icon="∅"
            title="No audit events yet"
            message="Product changes, imports, and duplicate decisions will be recorded here as system activity occurs."
          />
        ) : (
          <div className="table-wrap" style={{ border: 'none', borderRadius: 0 }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Action</th>
                  <th>Entity</th>
                  <th>User / Actor</th>
                  <th>Details</th>
                </tr>
              </thead>
              <tbody>
                {events.map((ev) => (
                  <tr key={ev.id}>
                    <td style={{ color: 'var(--muted-text)', whiteSpace: 'nowrap' }}>
                      {formatDateTime(ev.created_at)}
                    </td>
                    <td>
                      <span
                        className="badge-base"
                        style={{
                          background:
                            ev.action?.includes('REJECT') || ev.action?.includes('DELETE') || ev.action?.includes('DEACTIVAT')
                              ? 'var(--muted-peach-light)'
                              : ev.action?.includes('CONFIRM') || ev.action?.includes('CREATE') || ev.action?.includes('COMPLET')
                              ? 'var(--sage-light)'
                              : 'var(--powder-blue)',
                          color:
                            ev.action?.includes('REJECT') || ev.action?.includes('DELETE') || ev.action?.includes('DEACTIVAT')
                              ? '#B57A6A'
                              : ev.action?.includes('CONFIRM') || ev.action?.includes('CREATE') || ev.action?.includes('COMPLET')
                              ? 'var(--sage-dark)'
                              : 'var(--navy)',
                        }}
                      >
                        {ev.action}
                      </span>
                    </td>
                    <td>
                      {ev.entity_type}
                      {ev.entity_id ? ` #${ev.entity_id}` : ''}
                    </td>
                    <td>{ev.user_id || 'system'}</td>
                    <td style={{ color: 'var(--navy)' }}>
                      <div>{ev.description}</div>
                      {ev.new_values && Object.keys(ev.new_values).length > 0 && (
                        <div style={{ fontSize: '0.75rem', color: 'var(--muted-text)', marginTop: '2px' }}>
                          Updated: {Object.keys(ev.new_values).join(', ')}
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Potential audit events info */}
      <div className="panel panel-sage mt-4">
        <div className="panel-header"><h3>Tracked Event Types</h3></div>
        <div className="panel-body">
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            {[
              'PRODUCT_CREATED', 'PRODUCT_UPDATED', 'PRODUCT_DEACTIVATED',
              'BULK_UPLOAD_STARTED', 'BULK_UPLOAD_COMPLETED',
              'DUPLICATE_CHECK_STARTED', 'DUPLICATE_CONFIRMED', 'DUPLICATE_REJECTED',
            ].map((evt) => (
              <span key={evt} className="badge-base badge-powder">{evt}</span>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

export default AuditTrail
