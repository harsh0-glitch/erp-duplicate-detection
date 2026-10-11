import { useState, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { checkDuplicates, getDuplicateHistory } from '../services/duplicates'
import { LoadingState, ErrorState, EmptyState } from '../components/StateComponents'
import StatusBadge from '../components/StatusBadge'
import { formatDateTime } from '../utils/format'

const Duplicates = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const [form, setForm] = useState({
    sku: '',
    name: '',
    brand: '',
    category: '',
    subcategory: '',
    unit: '',
  })
  const [attrPairs, setAttrPairs] = useState([{ key: '', value: '' }])
  const [productId, setProductId] = useState('')
  const [checking, setChecking] = useState(false)
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)
  const [history, setHistory] = useState([])
  const [historyLoading, setHistoryLoading] = useState(false)
  const [historyError, setHistoryError] = useState(null)

  useEffect(() => {
    if (location.state?.product) {
      const p = location.state.product
      setForm({
        sku: p.sku || '',
        name: p.name || '',
        brand: p.brand || '',
        category: p.category || '',
        subcategory: p.subcategory || '',
        unit: p.unit || '',
      })
      if (p.id) setProductId(String(p.id))
      if (p.attributes && typeof p.attributes === 'object') {
        const pairs = Object.entries(p.attributes).map(([k, v]) => ({ key: k, value: String(v) }))
        if (pairs.length > 0) setAttrPairs(pairs)
      }
    }
  }, [location.state])

  const loadHistory = async () => {
    setHistoryLoading(true)
    setHistoryError(null)
    try {
      const res = await getDuplicateHistory({ page_size: 10 })
      setHistory(res.data?.items || [])
    } catch (e) {
      setHistoryError(e)
      setHistory([])
    } finally {
      setHistoryLoading(false)
    }
  }

  useEffect(() => {
    loadHistory()
  }, [])

  const handleChange = (field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }))
    if (error) setError(null)
  }

  const handleAttrChange = (idx, field, value) => {
    setAttrPairs((prev) => {
      const next = [...prev]
      next[idx] = { ...next[idx], [field]: value }
      return next
    })
  }

  const addAttrRow = () => setAttrPairs((prev) => [...prev, { key: '', value: '' }])
  const removeAttrRow = (idx) => setAttrPairs((prev) => prev.filter((_, i) => i !== idx))

  const buildAttributes = () => {
    const attrs = {}
    attrPairs.forEach(({ key, value }) => {
      const k = key.trim()
      if (k) attrs[k] = value.trim()
    })
    return attrs
  }

  const handleCheck = async (e) => {
    e.preventDefault()
    if (!form.sku.trim() || !form.name.trim()) {
      setError({ message: 'SKU and Product Name are required to check for duplicates.' })
      return
    }

    setChecking(true)
    setError(null)
    setResult(null)
    try {
      const payload = {
        sku: form.sku.trim(),
        name: form.name.trim(),
        brand: form.brand.trim() || undefined,
        category: form.category.trim() || undefined,
        subcategory: form.subcategory.trim() || undefined,
        unit: form.unit.trim() || undefined,
        attributes: buildAttributes(),
      }
      if (productId.trim()) {
        const parsedId = parseInt(productId.trim(), 10)
        if (!isNaN(parsedId)) payload.product_id = parsedId
      }
      const res = await checkDuplicates(payload)
      setResult(res.data)
      loadHistory()
    } catch (err) {
      setError(err)
    } finally {
      setChecking(false)
    }
  }

  const candidates = result?.matches || result?.candidates || []
  const modelUnavailable = result?.status === 'model_unavailable' || result?.model_status === 'model_unavailable'

  return (
    <div className="fade-in">
      <div className="page-header">
        <h2>Duplicate Intelligence</h2>
        <div className="page-subtitle">Submit a product to detect potential duplicates</div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-3)' }} className="dup-grid">
        {/* Input form */}
        <div className="panel">
          <div className="panel-header"><h3>Product Input</h3></div>
          <div className="panel-body">
            <form onSubmit={handleCheck}>
              <div className="form-group">
                <label className="form-label">Product ID <span style={{ fontWeight: 400, color: 'var(--muted-text)', fontSize: '0.78rem' }}>(optional)</span></label>
                <input
                  className="form-control-custom"
                  value={productId}
                  onChange={(e) => setProductId(e.target.value)}
                  placeholder="Existing product ID to check"
                />
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div className="form-group">
                  <label className="form-label">SKU</label>
                  <input className="form-control-custom" value={form.sku} onChange={(e) => handleChange('sku', e.target.value)} placeholder="SKU" />
                </div>
                <div className="form-group">
                  <label className="form-label">Name</label>
                  <input className="form-control-custom" value={form.name} onChange={(e) => handleChange('name', e.target.value)} placeholder="Product name" />
                </div>
                <div className="form-group">
                  <label className="form-label">Brand</label>
                  <input className="form-control-custom" value={form.brand} onChange={(e) => handleChange('brand', e.target.value)} placeholder="Brand" />
                </div>
                <div className="form-group">
                  <label className="form-label">Category</label>
                  <input className="form-control-custom" value={form.category} onChange={(e) => handleChange('category', e.target.value)} placeholder="Category" />
                </div>
                <div className="form-group">
                  <label className="form-label">Subcategory</label>
                  <input className="form-control-custom" value={form.subcategory} onChange={(e) => handleChange('subcategory', e.target.value)} placeholder="Subcategory" />
                </div>
                <div className="form-group">
                  <label className="form-label">Unit</label>
                  <input className="form-control-custom" value={form.unit} onChange={(e) => handleChange('unit', e.target.value)} placeholder="Unit" />
                </div>
              </div>

              <div className="form-hint mb-3">Attributes (optional):</div>
              {attrPairs.map((pair, idx) => (
                <div key={idx} style={{ display: 'flex', gap: '8px', marginBottom: '8px', alignItems: 'center' }}>
                  <input className="form-control-custom" style={{ flex: 1 }} placeholder="Key (e.g. RAM)" value={pair.key} onChange={(e) => handleAttrChange(idx, 'key', e.target.value)} />
                  <span style={{ color: 'var(--muted-text)' }}>→</span>
                  <input className="form-control-custom" style={{ flex: 1 }} placeholder="Value (e.g. 16 GB)" value={pair.value} onChange={(e) => handleAttrChange(idx, 'value', e.target.value)} />
                  {attrPairs.length > 1 && <button type="button" className="btn-ghost btn-sm" onClick={() => removeAttrRow(idx)}>✕</button>}
                </div>
              ))}
              <button type="button" className="btn-outline btn-sm" onClick={addAttrRow}>＋ Add Attribute</button>

              <div className="mt-4">
                <button type="submit" className="btn-powder" disabled={checking} style={{ width: '100%', justifyContent: 'center' }}>
                  {checking ? 'Checking…' : 'Check for Duplicates'}
                </button>
              </div>
            </form>
          </div>
        </div>

        {/* Results */}
        <div className="panel-powder">
          <div className="panel-header"><h3>Detection Results</h3></div>
          <div className="panel-body">
            {checking ? (
              <LoadingState message="Running duplicate detection…" />
            ) : error ? (
              error.type === 'network' ? (
                <EmptyState icon="—" title="Backend connection unavailable" message="Connect the FastAPI backend to run duplicate detection." />
              ) : (
                <ErrorState message={error.message} />
              )
            ) : !result ? (
              <EmptyState
                icon="◎"
                title="No detection run yet"
                message="Fill in the product details and click Check for Duplicates to see candidate matches."
              />
            ) : modelUnavailable ? (
              <div className="state-container">
                <div className="state-icon muted">—</div>
                <div className="state-title">Duplicate Detection Model Unavailable</div>
                <div className="state-message" style={{ maxWidth: '420px', margin: '0 auto 12px' }}>
                  {result.message || 'The ML duplicate detection model is currently under development.'}
                </div>
                <StatusBadge status="model_unavailable" />
                {result.total_candidates_analyzed > 0 && (
                  <div style={{ fontSize: '0.8rem', color: 'var(--muted-text)', marginTop: '12px' }}>
                    {result.total_candidates_analyzed} catalog candidates were analyzed prior to model inference.
                  </div>
                )}
                {result.detection_run_id && (
                  <button
                    className="btn-ghost btn-sm mt-3"
                    onClick={() => navigate(`/duplicates/${result.detection_run_id}`)}
                  >
                    View Detection Run Record #{result.detection_run_id} →
                  </button>
                )}
              </div>
            ) : candidates.length === 0 ? (
              <EmptyState icon="✓" title="No potential duplicates found" message={result.message || "No matching products were detected for this input."} />
            ) : (
              <div>
                {candidates.map((c, idx) => {
                  const prod = c.matched_product || c.product || {}
                  const score = c.confidence_score ?? c.similarity_score ?? c.confidence
                  const rawFeatures = c.matching_features || {}
                  const featureList = Array.isArray(rawFeatures)
                    ? rawFeatures
                    : Object.entries(rawFeatures).map(([k, v]) => typeof v === 'boolean' ? (v ? k : null) : `${k}: ${v}`).filter(Boolean)
                  const targetId = c.id || c.matched_product_id || result?.detection_run_id

                  return (
                    <div key={c.id || idx} className="card-base mb-3" style={{ padding: 'var(--space-3)' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '8px' }}>
                        <div>
                          <div style={{ fontWeight: 600, fontSize: '0.95rem' }}>
                            #{c.rank || idx + 1} — {prod.name || c.name || 'Candidate Match'}
                          </div>
                          <div style={{ fontSize: '0.82rem', color: 'var(--muted-text)', marginTop: '2px' }}>
                            {prod.sku || c.sku || '—'} · {prod.brand || c.brand || ''} {prod.category ? `· ${prod.category}` : ''}
                          </div>
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '4px' }}>
                          {score != null && (
                            <span className="badge-base badge-powder">
                              {(score * 100).toFixed(1)}% {c.confidence_score != null ? 'confidence' : 'similarity'}
                            </span>
                          )}
                          <StatusBadge status={c.review_status || c.status || 'pending'} />
                        </div>
                      </div>
                      {featureList.length > 0 && (
                        <div style={{ marginTop: '10px' }}>
                          <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--muted-text)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '4px' }}>
                            Matching Features
                          </div>
                          <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                            {featureList.map((f) => (
                              <span key={f} className="badge-base badge-active" style={{ fontSize: '0.7rem' }}>{f}</span>
                            ))}
                          </div>
                        </div>
                      )}
                      {targetId && (
                        <button className="btn-ghost btn-sm mt-3" onClick={() => navigate(`/duplicates/${targetId}`)}>
                          Investigate →
                        </button>
                      )}
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* History */}
      <div className="panel panel-sage mt-4">
        <div className="panel-header"><h3>Recent Detection Activity</h3></div>
        <div className="panel-body">
          {historyLoading ? (
            <LoadingState message="Loading history…" />
          ) : historyError ? (
            <EmptyState icon="—" title="No history available" message="Detection history will appear here once the backend is connected." />
          ) : history.length === 0 ? (
            <EmptyState icon="∅" title="No duplicate detections yet" message="Run a duplicate check to start building detection history." />
          ) : (
            <div className="table-wrap" style={{ border: 'none' }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Run ID</th>
                    <th>Query Product</th>
                    <th>Candidate Match</th>
                    <th>Status</th>
                    <th>Score</th>
                    <th>Detected</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map((d) => {
                    const topMatch = d.matches?.[0]
                    const score = topMatch?.confidence_score ?? topMatch?.similarity_score ?? d.confidence
                    return (
                      <tr key={d.id}>
                        <td style={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>#{d.id}</td>
                        <td>{d.query_product_name || d.input_product?.name || (d.query_product_sku ? `SKU: ${d.query_product_sku}` : 'Catalog Query')}</td>
                        <td>{topMatch?.matched_product_name || (topMatch?.matched_product_sku ? `SKU: ${topMatch.matched_product_sku}` : d.matches?.length > 1 ? `${d.matches.length} candidates` : '—')}</td>
                        <td><StatusBadge status={topMatch?.review_status || d.status} /></td>
                        <td>{score != null ? `${(score * 100).toFixed(1)}%` : '—'}</td>
                        <td style={{ color: 'var(--muted-text)' }}>{formatDateTime(d.created_at)}</td>
                        <td><button className="btn-ghost btn-sm" onClick={() => navigate(`/duplicates/${d.id}`)}>View</button></td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default Duplicates
