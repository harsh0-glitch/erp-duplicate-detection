import { useEffect, useState, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { getDashboardProductStats } from '../services/dashboard'
import { LoadingState, ErrorState, EmptyState } from '../components/StateComponents'
import { TableSkeleton } from '../components/Skeletons'

const Categories = () => {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [categories, setCategories] = useState([])

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await getDashboardProductStats({ category_limit: 50 })
      const data = res.data
      const rawCategories = data.by_category || []
      setCategories(rawCategories.map((c) => ({
        name: c.category,
        count: c.count,
        subcategories: [],
        brands: [],
      })))
    } catch (e) {
      setError(e)
      setCategories([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  return (
    <div className="fade-in">
      <div className="page-header">
        <h2>Categories</h2>
        <div className="page-subtitle">Catalog organization view — derived from product data</div>
      </div>

      <div className="panel-sage mb-4">
        <div className="panel-body" style={{ fontSize: '0.88rem', color: 'var(--navy)' }}>
          Categories are derived from existing product records. No category management endpoint is currently available.
          When products are added with categories, they will appear here automatically.
        </div>
      </div>

      {loading ? (
        <div className="panel"><TableSkeleton rows={4} cols={4} /></div>
      ) : error ? (
        <div className="panel">
          {error.type === 'network' ? (
            <EmptyState icon="—" title="Backend connection unavailable" message="Connect the backend to view categories." />
          ) : (
            <ErrorState message={error.message} />
          )}
        </div>
      ) : categories.length === 0 ? (
        <div className="panel">
          <EmptyState
            icon="∅"
            title="No categories available"
            message="Categories will appear here once products are added to the catalog. Example categories include Laptops, Mobile Phones, GPUs, Monitors, Keyboards, Mice, Components, and Accessories."
          />
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 'var(--space-3)' }}>
          {categories.map((cat) => (
            <div key={cat.name} className="card-base card-pad">
              <h3 style={{ marginBottom: 'var(--space-1)' }}>{cat.name}</h3>
              <div className="stat-label mb-3">{cat.count} product{cat.count !== 1 ? 's' : ''}</div>

              {cat.subcategories.length > 0 && (
                <div className="mb-3">
                  <div style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--muted-text)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '6px' }}>
                    Subcategories
                  </div>
                  <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                    {cat.subcategories.map((s) => (
                      <span key={s} className="badge-base badge-powder">{s}</span>
                    ))}
                  </div>
                </div>
              )}

              {cat.brands.length > 0 && (
                <div>
                  <div style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--muted-text)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '6px' }}>
                    Brands
                  </div>
                  <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                    {cat.brands.map((b) => (
                      <span key={b} className="badge-base badge-active">{b}</span>
                    ))}
                  </div>
                </div>
              )}

              <Link to={`/products?category=${encodeURIComponent(cat.name)}`} className="btn-ghost btn-sm mt-3">
                View products →
              </Link>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default Categories
