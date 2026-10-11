import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { getDuplicateHistory } from '../services/duplicates'
import { formatDateTime } from '../utils/format'
import { LoadingState, ErrorState, EmptyState } from '../components/StateComponents'
import { TableSkeleton } from '../components/Skeletons'
import StatusBadge from '../components/StatusBadge'

const Reviews = () => {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [reviews, setReviews] = useState([])
  const [filters, setFilters] = useState({ search: '', status: '', reviewer: '' })

  const loadReviews = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params = { page_size: 50 }
      if (filters.status) {
        params.decision = filters.status.toUpperCase()
      }
      const res = await getDuplicateHistory(params)
      const data = res.data
      const items = data.items || data.data || (Array.isArray(data) ? data : [])
      const filterDec = filters.status ? filters.status.toUpperCase() : null

      const rows = []
      items.forEach((run) => {
        const matches = filterDec
          ? (run.matches || []).filter(
            (m) => (m.review_status || m.review_decision || 'PENDING').toUpperCase() === filterDec
          )
          : run.matches || []

        if (matches.length > 0) {
          matches.forEach((m) => {
            rows.push({
              id: m.id,
              run_id: run.id,
              product_name:
                run.query_product_name ||
                run.query_product_sku ||
                (run.input_product && run.input_product.name) ||
                (run.query_product_id ? `Product #${run.query_product_id}` : `Run #${run.id}`),
              candidate_name:
                m.matched_product_name ||
                m.matched_product_sku ||
                `Candidate #${m.id}`,
              review_status: m.review_status || m.review_decision || 'PENDING',
              reviewer: m.reviewer_id || '—',
              reason: '—',
              reviewed_at: m.reviewed_at || run.created_at,
              created_at: run.created_at,
            })
          })
        } else if (!filterDec) {
          rows.push({
            id: run.id,
            run_id: run.id,
            product_name:
              run.query_product_name ||
              run.query_product_sku ||
              (run.input_product && run.input_product.name) ||
              `Detection Run #${run.id}`,
            candidate_name: 'No matches found',
            review_status: run.status,
            reviewer: '—',
            reason: '—',
            reviewed_at: run.created_at,
            created_at: run.created_at,
          })
        }
      })

      let finalRows = rows
      if (filters.search) {
        const s = filters.search.toLowerCase()
        finalRows = finalRows.filter(
          (r) =>
            r.product_name.toLowerCase().includes(s) ||
            r.candidate_name.toLowerCase().includes(s)
        )
      }
      if (filters.reviewer) {
        const rev = filters.reviewer.toLowerCase()
        finalRows = finalRows.filter(
          (r) => r.reviewer && r.reviewer.toLowerCase().includes(rev)
        )
      }

      setReviews(finalRows)
    } catch (e) {
      setError(e)
      setReviews([])
    } finally {
      setLoading(false)
    }
  }, [filters])

  useEffect(() => {
    loadReviews()
  }, [loadReviews])

  const handleFilterChange = (key, value) => setFilters((prev) => ({ ...prev, [key]: value }))

  return (
    <div className="fade-in">
      <div className="page-header">
        <h2>Review History</h2>
        <div className="page-subtitle">Historical duplicate review decisions and investigation workspace</div>
      </div>

      {/* Filters */}
      <div className="filters-bar">
        <div className="filter-item">
          <label>Search</label>
          <input className="form-control-custom" style={{ width: '220px' }} placeholder="Search by product or candidate…" value={filters.search} onChange={(e) => handleFilterChange('search', e.target.value)} />
        </div>
        <div className="filter-item">
          <label>Status</label>
          <select className="form-control-custom" style={{ width: '150px' }} value={filters.status} onChange={(e) => handleFilterChange('status', e.target.value)}>
            <option value="">All</option>
            <option value="pending">Pending</option>
            <option value="confirmed">Confirmed</option>
            <option value="rejected">Rejected</option>
          </select>
        </div>
        <div className="filter-item">
          <label>Reviewer</label>
          <input className="form-control-custom" style={{ width: '160px' }} placeholder="Reviewer ID…" value={filters.reviewer} onChange={(e) => handleFilterChange('reviewer', e.target.value)} />
        </div>
      </div>

      {/* Table */}
      <div className="panel panel-sage">
        {loading ? (
          <TableSkeleton rows={5} cols={6} />
        ) : error ? (
          error.type === 'network' ? (
            <EmptyState icon="—" title="Backend connection unavailable" message="Connect the backend to load review history." />
          ) : (
            <ErrorState message={error.message} />
          )
        ) : reviews.length === 0 ? (
          <EmptyState icon="∅" title="No review history" message="Confirmed or rejected duplicates will appear here for audit and investigation." />
        ) : (
          <div className="table-wrap" style={{ border: 'none', borderRadius: 0 }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Duplicate ID</th>
                  <th>Product</th>
                  <th>Candidate</th>
                  <th>Status</th>
                  <th>Reviewer</th>
                  <th>Reason</th>
                  <th>Reviewed At</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {reviews.map((r) => (
                  <tr key={`${r.run_id}-${r.id}`}>
                    <td style={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>{r.id}</td>
                    <td>{r.product_name || '—'}</td>
                    <td>{r.candidate_name || '—'}</td>
                    <td><StatusBadge status={r.review_status || r.status} /></td>
                    <td>{r.reviewer || '—'}</td>
                    <td style={{ maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{r.reason || '—'}</td>
                    <td style={{ color: 'var(--muted-text)', whiteSpace: 'nowrap' }}>{formatDateTime(r.reviewed_at || r.created_at)}</td>
                    <td><button className="btn-ghost btn-sm" onClick={() => navigate(`/duplicates/${r.id}`)}>Investigate</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

export default Reviews
