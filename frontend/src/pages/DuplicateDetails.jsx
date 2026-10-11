import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { getDuplicateById, confirmDuplicate, rejectDuplicate } from '../services/duplicates'
import { formatDateTime, formatDate } from '../utils/format'
import { LoadingState, ErrorState, EmptyState, UnavailableState } from '../components/StateComponents'
import { CardSkeleton } from '../components/Skeletons'
import StatusBadge from '../components/StatusBadge'

const COMPARISON_FIELDS = [
  { key: 'name', label: 'Name' },
  { key: 'sku', label: 'SKU' },
  { key: 'brand', label: 'Brand' },
  { key: 'category', label: 'Category' },
  { key: 'subcategory', label: 'Subcategory' },
  { key: 'unit', label: 'Unit' },
]

const DuplicateDetails = () => {
  const { id } = useParams()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [dup, setDup] = useState(null)
  const [reviewOpen, setReviewOpen] = useState(null)
  const [reviewForm, setReviewForm] = useState({ reviewer: '', reason: '' })
  const [submitting, setSubmitting] = useState(false)
  const [reviewError, setReviewError] = useState(null)
  const [reviewSuccess, setReviewSuccess] = useState(null)

  useEffect(() => {
    let active = true
    async function load() {
      setLoading(true)
      setError(null)
      try {
        const res = await getDuplicateById(id)
        if (!active) return
        setDup(res.data)
      } catch (e) {
        if (active) setError(e)
      } finally {
        if (active) setLoading(false)
      }
    }
    load()
    return () => { active = false }
  }, [id])

  const openReview = (type) => {
    setReviewOpen(type)
    setReviewError(null)
    setReviewSuccess(null)
    setReviewForm({ reviewer: '', reason: '' })
  }

  const handleReviewSubmit = async (e) => {
    e.preventDefault()
    if (!reviewForm.reviewer.trim()) {
      setReviewError('Reviewer ID is required')
      return
    }
    setSubmitting(true)
    setReviewError(null)
    try {
      const payload = {
        reviewer_id: reviewForm.reviewer.trim(),
        reason: reviewForm.reason.trim() || undefined,
      }
      if (reviewOpen === 'confirm') {
        await confirmDuplicate(id, payload)
      } else {
        await rejectDuplicate(id, payload)
      }
      setReviewSuccess(reviewOpen === 'confirm' ? 'Duplicate confirmed successfully.' : 'Duplicate rejected successfully.')
      const res = await getDuplicateById(id)
      setDup(res.data)
      setTimeout(() => setReviewOpen(null), 1500)
    } catch (err) {
      setReviewError(err.message || 'Failed to submit review.')
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) {
    return (
      <div className="fade-in">
        <div className="page-header"><h2>Duplicate Details</h2></div>
        <div className="panel"><CardSkeleton /></div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="fade-in">
        <div className="page-header"><h2>Duplicate Details</h2></div>
        <div className="panel">
          {error.type === 'network' ? (
            <UnavailableState title="Backend connection unavailable" message="Connect the backend to view this duplicate." />
          ) : (
            <ErrorState message={error.message} />
          )}
        </div>
      </div>
    )
  }

  if (!dup) {
    return <div className="panel"><EmptyState icon="?" title="Duplicate not found" /></div>
  }

  const productA = dup.query_product || dup.product_a || dup.product || {}
  const productB = dup.matched_product || dup.product_b || dup.candidate || (dup.matches?.[0] ? {
    name: dup.matches[0].matched_product_name,
    sku: dup.matches[0].matched_product_sku,
  } : {})
  const attrsA = productA.attributes || {}
  const attrsB = productB.attributes || {}
  const allAttrKeys = Array.from(new Set([...Object.keys(attrsA), ...Object.keys(attrsB)]))

  const rawFeatures = dup.matching_features || {}
  const matchingFeatures = Array.isArray(rawFeatures)
    ? rawFeatures
    : Object.entries(rawFeatures).map(([k, v]) => typeof v === 'boolean' ? (v ? k : null) : `${k}: ${v}`).filter(Boolean)

  const isFieldMatch = (key) => {
    const a = productA[key]
    const b = productB[key]
    if (a == null && b == null) return true
    return String(a || '').toLowerCase() === String(b || '').toLowerCase()
  }

  const isAttrMatch = (key) => {
    const a = attrsA[key]
    const b = attrsB[key]
    if (a == null && b == null) return true
    return String(a || '').toLowerCase() === String(b || '').toLowerCase()
  }

  const reviewStatus = (dup.review_status || dup.status || '').toUpperCase()
  const reviewDone = reviewStatus === 'CONFIRMED' || reviewStatus === 'REJECTED'
  const reviewer = dup.review?.reviewer_id || dup.reviewer
  const reason = dup.review?.reason || dup.reason
  const reviewedAt = dup.review?.updated_at || dup.review?.created_at || dup.reviewed_at
  const score = dup.confidence_score ?? dup.similarity_score ?? dup.confidence

  return (
    <div className="fade-in">
      <div className="page-header">
        <div className="page-header-row">
          <div>
            <h2>Duplicate Investigation</h2>
            <div className="page-subtitle">
              ID: <span style={{ fontFamily: 'monospace' }}>{dup.id}</span>
            </div>
          </div>
          <Link to="/duplicates" className="btn-outline">← Back to Intelligence</Link>
        </div>
      </div>

      {/* Status bar */}
      <div className="panel mb-4">
        <div className="panel-body" style={{ display: 'flex', gap: 'var(--space-4)', flexWrap: 'wrap' }}>
          <div>
            <div className="stat-label">Detection Status</div>
            <div className="mt-3"><StatusBadge status={dup.status} /></div>
          </div>
          <div>
            <div className="stat-label">Review Status</div>
            <div className="mt-3"><StatusBadge status={dup.review_status || 'pending'} /></div>
          </div>
          <div>
            <div className="stat-label">Confidence</div>
            <div style={{ fontSize: '1.1rem', fontWeight: 600, marginTop: '4px' }}>
              {score != null ? `${(score * 100).toFixed(1)}%` : '—'}
            </div>
          </div>
          <div>
            <div className="stat-label">Rank</div>
            <div style={{ fontSize: '1.1rem', fontWeight: 600, marginTop: '4px' }}>{dup.rank ?? '—'}</div>
          </div>
          <div>
            <div className="stat-label">Created</div>
            <div style={{ fontSize: '0.85rem', marginTop: '4px' }}>{formatDateTime(dup.created_at)}</div>
          </div>
          {reviewedAt && (
            <div>
              <div className="stat-label">Reviewed</div>
              <div style={{ fontSize: '0.85rem', marginTop: '4px' }}>{formatDateTime(reviewedAt)}</div>
            </div>
          )}
        </div>
      </div>

      {/* Comparison — Powder Blue surface */}
      <div className="panel-powder mb-4">
        <div className="panel-header"><h3>Product Comparison</h3></div>
        <div className="panel-body">
          <div className="compare-grid">
            <div className="compare-col">
              <h4>{productA.name || 'Product A'}</h4>
              {COMPARISON_FIELDS.map((f) => (
                <div key={f.key} className="compare-field">
                  <span className="field-label">{f.label}</span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span className="field-value">{productA[f.key] || '—'}</span>
                    {isFieldMatch(f.key) ? <span className="field-match">MATCH</span> : <span className="field-differ">DIFFERENT</span>}
                  </div>
                </div>
              ))}
            </div>
            <div className="compare-col">
              <h4>{productB.name || 'Product B'}</h4>
              {COMPARISON_FIELDS.map((f) => (
                <div key={f.key} className="compare-field">
                  <span className="field-label">{f.label}</span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span className="field-value">{productB[f.key] || '—'}</span>
                    {isFieldMatch(f.key) ? <span className="field-match">MATCH</span> : <span className="field-differ">DIFFERENT</span>}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Attribute comparison */}
          {allAttrKeys.length > 0 && (
            <>
              <h4 className="mt-4 mb-3">Attribute Comparison</h4>
              <div className="compare-grid">
                <div className="compare-col">
                  {allAttrKeys.map((key) => (
                    <div key={key} className="compare-field">
                      <span className="field-label">{key}</span>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span className="field-value">{attrsA[key] != null ? String(attrsA[key]) : '—'}</span>
                        {isAttrMatch(key) ? <span className="field-match">MATCH</span> : <span className="field-differ">DIFFERENT</span>}
                      </div>
                    </div>
                  ))}
                </div>
                <div className="compare-col">
                  {allAttrKeys.map((key) => (
                    <div key={key} className="compare-field">
                      <span className="field-label">{key}</span>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span className="field-value">{attrsB[key] != null ? String(attrsB[key]) : '—'}</span>
                        {isAttrMatch(key) ? <span className="field-match">MATCH</span> : <span className="field-differ">DIFFERENT</span>}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}

          {/* Matching features summary */}
          {matchingFeatures.length > 0 && (
            <div className="mt-4">
              <div className="stat-label mb-3">Matching Features Identified by Model</div>
              <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                {matchingFeatures.map((f) => (
                  <span key={f} className="badge-base badge-active">{f}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Review section */}
      <div className="panel">
        <div className="panel-header"><h3>Review Decision</h3></div>
        <div className="panel-body">
          {reviewDone && !reviewOpen ? (
            <div style={{ padding: '12px', borderRadius: 'var(--radius-md)', background: reviewStatus === 'CONFIRMED' ? 'var(--sage-light)' : 'var(--muted-peach-light)', fontSize: '0.9rem', fontWeight: 500 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <StatusBadge status={reviewStatus} />
                {reviewer && <span style={{ color: 'var(--muted-text)' }}>by {reviewer}</span>}
              </div>
              {reason && <div style={{ marginTop: '6px', color: 'var(--muted-text)' }}>Reason: {reason}</div>}
            </div>
          ) : reviewOpen ? (
            <form onSubmit={handleReviewSubmit} className="fade-in" style={{ maxWidth: '500px' }}>
              <h4 className="mb-3">{reviewOpen === 'confirm' ? 'Confirm Duplicate' : 'Reject Duplicate'}</h4>
              {reviewSuccess && (
                <div className="card-base mb-3" style={{ padding: '10px 14px', borderColor: 'var(--sage)', background: 'var(--sage-light)', color: 'var(--sage-dark)', fontSize: '0.85rem', fontWeight: 500 }}>
                  {reviewSuccess}
                </div>
              )}
              {reviewError && (
                <div className="card-base mb-3" style={{ padding: '10px 14px', borderColor: 'var(--muted-peach)', background: 'var(--muted-peach-light)', color: '#B57A6A', fontSize: '0.85rem', fontWeight: 500 }}>
                  {reviewError}
                </div>
              )}
              <div className="form-group">
                <label className="form-label">Reviewer ID<span className="required">*</span></label>
                <input className="form-control-custom" value={reviewForm.reviewer} onChange={(e) => setReviewForm((p) => ({ ...p, reviewer: e.target.value }))} placeholder="Your reviewer ID" />
              </div>
              <div className="form-group">
                <label className="form-label">Reason</label>
                <textarea className="form-control-custom" rows={2} value={reviewForm.reason} onChange={(e) => setReviewForm((p) => ({ ...p, reason: e.target.value }))} placeholder="Explain your decision…" />
              </div>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button type="submit" className={reviewOpen === 'confirm' ? 'btn-sage' : 'btn-yellow'} disabled={submitting}>
                  {submitting ? 'Submitting…' : reviewOpen === 'confirm' ? 'Confirm Duplicate' : 'Reject Duplicate'}
                </button>
                <button type="button" className="btn-outline" onClick={() => setReviewOpen(null)}>Cancel</button>
              </div>
            </form>
          ) : dup.record_type === 'detection_run' ? (
            <div style={{ fontSize: '0.88rem', color: 'var(--muted-text)' }}>
              This record is a detection run. Individual duplicate matches can be reviewed from candidate match records.
            </div>
          ) : (
            <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
              <button className="btn-sage" onClick={() => openReview('confirm')}>Confirm Duplicate</button>
              <button className="btn-yellow" onClick={() => openReview('reject')}>Reject Duplicate</button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default DuplicateDetails
