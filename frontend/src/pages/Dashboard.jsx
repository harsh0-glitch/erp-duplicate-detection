import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  getDashboardOverview,
  getDashboardProductStats,
  getDashboardDuplicateStats,
  getDashboardActivity,
} from '../services/dashboard'
import { formatRelative } from '../utils/format'
import StatusBadge from '../components/StatusBadge'
import { StatSkeleton } from '../components/Skeletons'

const CompactEmpty = ({ title, message }) => (
  <div style={{ padding: '20px 0', textAlign: 'left' }}>
    <div style={{ fontSize: '0.88rem', fontWeight: 600, color: 'var(--navy)', marginBottom: '4px' }}>{title}</div>
    <div style={{ fontSize: '0.8rem', color: 'var(--muted-text)', lineHeight: 1.45 }}>{message}</div>
  </div>
)

const Dashboard = () => {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [overview, setOverview] = useState(null)
  const [productStats, setProductStats] = useState(null)
  const [duplicateStats, setDuplicateStats] = useState(null)
  const [activityFeed, setActivityFeed] = useState(null)

  useEffect(() => {
    let active = true
    async function load() {
      setLoading(true)
      setError(null)
      try {
        const [overviewRes, prodRes, dupRes, actRes] = await Promise.allSettled([
          getDashboardOverview(),
          getDashboardProductStats(),
          getDashboardDuplicateStats({ activity_limit: 5 }),
          getDashboardActivity({ limit: 7 }),
        ])
        if (!active) return

        if (overviewRes.status === 'fulfilled') setOverview(overviewRes.value.data)
        else setOverview(null)

        if (prodRes.status === 'fulfilled') setProductStats(prodRes.value.data)
        else setProductStats(null)

        if (dupRes.status === 'fulfilled') setDuplicateStats(dupRes.value.data)
        else setDuplicateStats(null)

        if (actRes.status === 'fulfilled') setActivityFeed(actRes.value.data)
        else setActivityFeed(null)

        const allRejected = [overviewRes, prodRes, dupRes, actRes].every(
          (r) => r.status === 'rejected'
        )
        if (allRejected) {
          const firstErr = overviewRes.reason || prodRes.reason || dupRes.reason || actRes.reason
          setError(firstErr?.type === 'network' ? 'network' : (firstErr?.message || 'Failed to load dashboard data'))
        }
      } catch (e) {
        if (active) setError(e?.type === 'network' ? 'network' : (e?.message || 'Failed to load dashboard data'))
      } finally {
        if (active) setLoading(false)
      }
    }
    load()
    return () => { active = false }
  }, [])

  const totalProducts = overview?.total_products ?? productStats?.total_products ?? 0
  const activeProducts = overview?.active_products ?? productStats?.active_products ?? 0
  const inactiveProducts = overview?.inactive_products ?? productStats?.inactive_products ?? 0
  const pendingDuplicates = overview?.pending_duplicates ?? duplicateStats?.pending_duplicates ?? 0
  const confirmedDuplicates = overview?.confirmed_duplicates ?? duplicateStats?.confirmed_duplicates ?? 0
  const rejectedDuplicates = overview?.rejected_duplicates ?? duplicateStats?.rejected_duplicates ?? 0

  const recentDuplicates = duplicateStats?.recent_activity || []
  const activityItems = activityFeed?.items || []

  return (
    <div className="fade-in">
      <div className="page-header">
        <h2>Overview</h2>
        <div className="page-subtitle">Catalog and duplicate activity at a glance</div>
      </div>

      {/* === CATALOG SUMMARY — inline metric strip, not floating cards === */}
      <div className="dash-section">
        <div className="dash-section-header">
          <span className="section-label">Product Catalog</span>
          <Link to="/products" className="section-link">Browse all products →</Link>
        </div>
        {loading ? (
          <div className="metric-strip">
            <div className="metric-cell"><StatSkeleton /></div>
            <div className="metric-cell"><StatSkeleton /></div>
            <div className="metric-cell"><StatSkeleton /></div>
          </div>
        ) : (
          <div className="metric-strip">
            <div className="metric-cell">
              <div className="metric-label">Products indexed</div>
              <div className="metric-value">{totalProducts}</div>
              {productStats?.by_category && (
                <div className="metric-sub">
                  {productStats.by_category.length} categories · {productStats.by_brand?.length || 0} brands
                </div>
              )}
            </div>
            <div className="metric-cell success">
              <div className="metric-label">Active</div>
              <div className="metric-value">{activeProducts}</div>
              {inactiveProducts > 0 && (
                <div className="metric-sub">{inactiveProducts} inactive</div>
              )}
            </div>
            <div className="metric-cell alert">
              <div className="metric-label">Needs review</div>
              <div className="metric-value">{pendingDuplicates}</div>
              {duplicateStats?.total_duplicate_checks != null && (
                <div className="metric-sub">
                  Across {duplicateStats.total_duplicate_checks} check{duplicateStats.total_duplicate_checks === 1 ? '' : 's'}
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* === MAIN GRID — asymmetric: duplicate intelligence (wide) + activity (narrow) === */}
      <div className="dash-main-grid">
        {/* DUPLICATE INTELLIGENCE — focal section on powder blue data surface */}
        <div className="dash-section">
          <div className="dash-section-header">
            <span className="section-label">Duplicate Intelligence</span>
            <Link to="/duplicates" className="section-link">Open workspace →</Link>
          </div>
          <div className="panel-powder" style={{ minHeight: '320px' }}>
            <div className="panel-body">
              {loading ? (
                <div style={{ padding: '20px 0' }}>
                  <div className="skeleton skeleton-line medium" />
                  <div className="skeleton skeleton-line" />
                  <div className="skeleton skeleton-line short" />
                </div>
              ) : error === 'network' ? (
                <CompactEmpty
                  title="No intelligence data available"
                  message="Backend connection unavailable. Duplicate detection data will appear here once connected."
                />
              ) : error ? (
                <CompactEmpty
                  title="Failed to load intelligence data"
                  message={typeof error === 'string' ? error : (error?.message || 'Unable to fetch duplicate statistics.')}
                />
              ) : (recentDuplicates.length === 0 && pendingDuplicates === 0 && confirmedDuplicates === 0 && rejectedDuplicates === 0) ? (
                <CompactEmpty
                  title="No duplicate detections yet"
                  message="Run a duplicate check from the Duplicate Intelligence workspace to start seeing potential matches here."
                />
              ) : (
                <>
                  {/* Inline metrics — not cards */}
                  <div className="dup-metrics">
                    <div className="dup-metric review">
                      <div className="dup-metric-num">{pendingDuplicates}</div>
                      <div className="dup-metric-label">Needs review</div>
                    </div>
                    <div className="dup-metric confirmed">
                      <div className="dup-metric-num">{confirmedDuplicates}</div>
                      <div className="dup-metric-label">Confirmed</div>
                    </div>
                    <div className="dup-metric rejected">
                      <div className="dup-metric-num">{rejectedDuplicates}</div>
                      <div className="dup-metric-label">Rejected</div>
                    </div>
                  </div>

                  {/* Recent cases as compact rows */}
                  <div style={{ borderTop: '1px solid var(--powder-blue)', paddingTop: '8px' }}>
                    {recentDuplicates.length === 0 ? (
                      <div style={{ padding: '12px 0', fontSize: '0.8rem', color: 'var(--muted-text)' }}>
                        No recent detection runs recorded.
                      </div>
                    ) : (
                      recentDuplicates.slice(0, 5).map((d) => (
                        <div
                          key={d.run_id}
                          className="activity-item"
                          style={{ cursor: 'pointer' }}
                          onClick={() => navigate(`/duplicates/${d.run_id}`)}
                        >
                          <div className={`activity-dot ${(d.status || '').toLowerCase() === 'pending' ? 'yellow' : (d.status || '').toLowerCase() === 'completed' ? 'sage' : 'peach'}`} />
                          <div className="activity-content">
                            <div className="activity-title">
                              {d.query_name || d.query_sku || `Detection Run #${d.run_id}`}
                              {d.total_candidates > 0 ? ` · ${d.total_candidates} candidate${d.total_candidates === 1 ? '' : 's'}` : ''}
                            </div>
                            <div className="activity-time" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                              {formatRelative(d.created_at)}
                              <StatusBadge status={d.status} />
                            </div>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </>
              )}
            </div>
          </div>
        </div>

        {/* CATALOG ACTIVITY — compact timeline feed */}
        <div className="dash-section">
          <div className="dash-section-header">
            <span className="section-label">Catalog Activity</span>
            <Link to="/products" className="section-link">View all →</Link>
          </div>
          <div className="panel panel-sage" style={{ minHeight: '320px' }}>
            <div className="panel-body">
              {loading ? (
                <div style={{ padding: '20px 0' }}>
                  <div className="skeleton skeleton-line medium" />
                  <div className="skeleton skeleton-line" />
                  <div className="skeleton skeleton-line short" />
                </div>
              ) : error === 'network' ? (
                <CompactEmpty
                  title="No recent catalog activity"
                  message="Products and imports will appear here as activity occurs."
                />
              ) : error ? (
                <CompactEmpty
                  title="Failed to load activity feed"
                  message={typeof error === 'string' ? error : (error?.message || 'Unable to fetch activity records.')}
                />
              ) : activityItems.length === 0 ? (
                <CompactEmpty
                  title="No recent catalog activity"
                  message="System activity will appear here as catalog updates and reviews occur."
                />
              ) : (
                activityItems.slice(0, 7).map((item) => (
                  <div key={item.id} className="activity-row">
                    <div className="activity-time">{formatRelative(item.created_at)}</div>
                    <div>
                      <div className="activity-title">{item.description}</div>
                      <div className="activity-meta">
                        {item.action} · {item.entity_type}
                        {item.user_id ? ` · ${item.user_id}` : ''}
                      </div>
                    </div>
                    <span
                      className="activity-badge"
                      style={{
                        background:
                          item.action === 'REJECT' || item.action === 'DELETE'
                            ? 'var(--muted-peach-light)'
                            : item.action === 'CONFIRM' || item.action === 'CREATE'
                            ? 'var(--sage-light)'
                            : 'var(--powder-blue)',
                        color:
                          item.action === 'REJECT' || item.action === 'DELETE'
                            ? '#B57A6A'
                            : item.action === 'CONFIRM' || item.action === 'CREATE'
                            ? 'var(--sage-dark)'
                            : 'var(--navy)',
                      }}
                    >
                      {item.action}
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>

      {/* === QUICK ACTIONS — compact inline controls === */}
      <div className="dash-section mt-4">
        <div className="dash-section-header">
          <span className="section-label">Quick Actions</span>
        </div>
        <div className="quick-actions">
          <div className="quick-action" onClick={() => navigate('/products/new')}>
            <span className="qa-icon">+</span>
            <span className="qa-label">Add Product</span>
          </div>
          <div className="quick-action" onClick={() => navigate('/imports')}>
            <span className="qa-icon">↑</span>
            <span className="qa-label">Import Products</span>
          </div>
          <div className="quick-action" onClick={() => navigate('/duplicates')}>
            <span className="qa-icon">◎</span>
            <span className="qa-label">Check for Duplicates</span>
          </div>
          <div className="quick-action" onClick={() => navigate('/reviews')}>
            <span className="qa-icon">✓</span>
            <span className="qa-label">Review History</span>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Dashboard
