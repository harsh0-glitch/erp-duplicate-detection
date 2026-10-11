import { useEffect, useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { getProductById, deleteProduct } from '../services/products'
import { getDuplicateHistory } from '../services/duplicates'
import { formatDateTime, formatDate } from '../utils/format'
import { LoadingState, ErrorState, EmptyState, UnavailableState } from '../components/StateComponents'
import { CardSkeleton } from '../components/Skeletons'
import StatusBadge, { ActiveBadge } from '../components/StatusBadge'

const ProductProfile = () => {
  const { id } = useParams()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [product, setProduct] = useState(null)
  const [dups, setDups] = useState([])
  const [dupsLoading, setDupsLoading] = useState(false)
  const [dupsError, setDupsError] = useState(null)

  useEffect(() => {
    let active = true
    async function load() {
      setLoading(true)
      setError(null)
      try {
        const res = await getProductById(id)
        if (!active) return
        setProduct(res.data)
      } catch (e) {
        if (active) setError(e)
      } finally {
        if (active) setLoading(false)
      }
    }
    load()
    return () => { active = false }
  }, [id])

  useEffect(() => {
    let active = true
    async function loadDups() {
      if (!product?.id) return
      setDupsLoading(true)
      setDupsError(null)
      try {
        const res = await getDuplicateHistory({ query_product_id: product.id })
        if (!active) return
        const runs = res.data?.items || []
        const records = []
        runs.forEach((run) => {
          if (Array.isArray(run.matches) && run.matches.length > 0) {
            run.matches.forEach((m) => {
              records.push({
                id: m.id,
                matched_name: m.matched_product_name || (m.matched_product_sku ? `SKU: ${m.matched_product_sku}` : '—'),
                status: m.review_status || run.status,
                confidence: m.confidence_score ?? m.similarity_score,
                created_at: run.created_at,
              })
            })
          }
        })
        setDups(records)
      } catch (err) {
        if (active) {
          setDupsError(err)
          setDups([])
        }
      } finally {
        if (active) setDupsLoading(false)
      }
    }
    loadDups()
    return () => { active = false }
  }, [product])

  const handleDeactivate = async () => {
    if (!window.confirm('Deactivate this product?')) return
    try {
      await deleteProduct(product.id)
      navigate('/products')
    } catch (e) {
      alert('Failed to deactivate: ' + (e.message || 'Unknown error'))
    }
  }

  if (loading) {
    return (
      <div className="fade-in">
        <div className="page-header"><h2>Product Profile</h2></div>
        <div className="panel"><CardSkeleton /></div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="fade-in">
        <div className="page-header"><h2>Product Profile</h2></div>
        <div className="panel">
          {error.type === 'network' ? (
            <UnavailableState
              title="Backend connection unavailable"
              message="Connect the FastAPI backend to view this product."
            />
          ) : (
            <ErrorState message={error.message} />
          )}
        </div>
      </div>
    )
  }

  if (!product) {
    return (
      <div className="panel">
        <EmptyState icon="?" title="Product not found" message="This product may have been removed." />
      </div>
    )
  }

  const attrs = product.attributes || {}
  const attrEntries = Object.entries(attrs)

  return (
    <div className="fade-in">
      <div className="page-header">
        <div className="page-header-row">
          <div>
            <h2>{product.name}</h2>
            <div className="page-subtitle">{product.sku} · {product.brand || 'No brand'} · {product.category || 'Uncategorized'}</div>
          </div>
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            <Link to={`/products/${product.id}/edit`} className="btn-navy">Edit Product</Link>
            {product.is_active && (
              <button className="btn-outline" onClick={handleDeactivate}>Deactivate</button>
            )}
            <button className="btn-powder" onClick={() => navigate('/duplicates')}>Check for Duplicates</button>
          </div>
        </div>
      </div>

      {/* Status bar */}
      <div className="panel mb-4">
        <div className="panel-body" style={{ display: 'flex', gap: 'var(--space-4)', flexWrap: 'wrap' }}>
          <div>
            <div className="stat-label">Status</div>
            <div className="mt-3"><ActiveBadge active={product.is_active} /></div>
          </div>
          <div>
            <div className="stat-label">Product ID</div>
            <div style={{ fontFamily: 'monospace', fontSize: '0.85rem', marginTop: '4px' }}>{product.id}</div>
          </div>
          <div>
            <div className="stat-label">Created</div>
            <div style={{ fontSize: '0.85rem', marginTop: '4px' }}>{formatDateTime(product.created_at)}</div>
          </div>
          <div>
            <div className="stat-label">Last Updated</div>
            <div style={{ fontSize: '0.85rem', marginTop: '4px' }}>{formatDateTime(product.updated_at)}</div>
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-3)' }} className="profile-grid">
        {/* Product Information — Powder Blue panel */}
        <div className="panel-powder">
          <div className="panel-header">
            <h3>Product Information</h3>
          </div>
          <div className="panel-body">
            <div className="compare-field">
              <span className="field-label">SKU</span>
              <span className="field-value">{product.sku}</span>
            </div>
            <div className="compare-field">
              <span className="field-label">Name</span>
              <span className="field-value">{product.name}</span>
            </div>
            <div className="compare-field">
              <span className="field-label">Brand</span>
              <span className="field-value">{product.brand || '—'}</span>
            </div>
            <div className="compare-field">
              <span className="field-label">Category</span>
              <span className="field-value">{product.category || '—'}</span>
            </div>
            <div className="compare-field">
              <span className="field-label">Subcategory</span>
              <span className="field-value">{product.subcategory || '—'}</span>
            </div>
            <div className="compare-field">
              <span className="field-label">Unit</span>
              <span className="field-value">{product.unit || '—'}</span>
            </div>
            {product.description && (
              <div style={{ marginTop: 'var(--space-3)' }}>
                <div className="stat-label mb-3">Description</div>
                <div style={{ fontSize: '0.9rem', color: 'var(--navy)' }}>{product.description}</div>
              </div>
            )}
          </div>
        </div>

        {/* Attributes / Specifications */}
        <div className="panel">
          <div className="panel-header">
            <h3>Attributes &amp; Specifications</h3>
          </div>
          <div className="panel-body">
            {attrEntries.length === 0 ? (
              <EmptyState icon="∅" title="No attributes" message="This product has no specifications recorded." />
            ) : (
              <div className="attr-list">
                {attrEntries.map(([key, val]) => (
                  <div key={key} className="attr-chip">
                    <span className="attr-key">{key}:</span>{' '}
                    <span className="attr-val">{String(val)}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Duplicate Intelligence section */}
      <div className="panel mt-4">
        <div className="panel-header">
          <h3>Duplicate Intelligence</h3>
          <Link to="/duplicates" className="btn-ghost btn-sm">Run new check</Link>
        </div>
        <div className="panel-body">
          {dupsLoading ? (
            <LoadingState message="Loading duplicate history…" />
          ) : dupsError ? (
            <ErrorState message={dupsError.message || 'Failed to load duplicate history.'} />
          ) : dups.length === 0 ? (
            <EmptyState
              icon="∅"
              title="No duplicate detections for this product"
              message="Run a duplicate check to see potential matches here."
            />
          ) : (
            <div className="table-wrap" style={{ border: 'none' }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Duplicate ID</th>
                    <th>Matched Product</th>
                    <th>Status</th>
                    <th>Confidence</th>
                    <th>Detected</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {dups.map((d) => (
                    <tr key={d.id}>
                      <td style={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>#{d.id}</td>
                      <td>{d.matched_name || d.product_b?.name || d.candidate_name || '—'}</td>
                      <td><StatusBadge status={d.status} /></td>
                      <td>{d.confidence != null ? `${(d.confidence * 100).toFixed(1)}%` : '—'}</td>
                      <td style={{ color: 'var(--muted-text)' }}>{formatDate(d.created_at)}</td>
                      <td>
                        <Link to={`/duplicates/${d.id}`} className="btn-ghost btn-sm">Investigate</Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default ProductProfile
