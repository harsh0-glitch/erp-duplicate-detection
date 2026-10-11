import { useEffect, useState, useCallback } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { getProducts, deleteProduct } from '../services/products'
import { formatDate } from '../utils/format'
import { LoadingState, ErrorState, EmptyState } from '../components/StateComponents'
import { TableSkeleton } from '../components/Skeletons'
import StatusBadge, { ActiveBadge } from '../components/StatusBadge'

const Products = () => {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [products, setProducts] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [filters, setFilters] = useState({
    search: '',
    sku: '',
    category: '',
    subcategory: '',
    brand: '',
    is_active: '',
  })

  const loadProducts = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params = {
        page,
        page_size: pageSize,
      }
      if (filters.search?.trim()) params.search = filters.search.trim()
      if (filters.sku?.trim()) params.sku = filters.sku.trim()
      if (filters.brand?.trim()) params.brand = filters.brand.trim()
      if (filters.category?.trim()) params.category = filters.category.trim()
      if (filters.subcategory?.trim()) params.subcategory = filters.subcategory.trim()
      if (filters.is_active === 'true') params.is_active = true
      if (filters.is_active === 'false') params.is_active = false

      const res = await getProducts(params)
      const data = res.data
      const items = data.items || data.data || (Array.isArray(data) ? data : [])
      setProducts(items)
      const totalCount = data.pagination?.total ?? data.total ?? items.length
      setTotal(totalCount)
    } catch (e) {
      setError(e)
      setProducts([])
      setTotal(0)
    } finally {
      setLoading(false)
    }
  }, [filters, page, pageSize])

  useEffect(() => {
    loadProducts()
  }, [loadProducts])

  const handleFilterChange = (key, value) => {
    setFilters((prev) => ({ ...prev, [key]: value }))
    setPage(1)
  }

  const handleDeactivate = async (id) => {
    if (!window.confirm('Deactivate this product?')) return
    try {
      await deleteProduct(id)
      loadProducts()
    } catch (e) {
      alert('Failed to deactivate product: ' + (e.message || 'Unknown error'))
    }
  }

  const totalPages = Math.ceil(total / pageSize) || 1

  return (
    <div className="fade-in">
      <div className="page-header">
        <div className="page-header-row">
          <div>
            <h2>Products</h2>
            <div className="page-subtitle">Centralized product master catalog</div>
          </div>
          <button className="btn-navy btn-sm" onClick={() => navigate('/products/new')}>
            + Add Product
          </button>
        </div>
      </div>

      {/* Inline filters bar — compact, not sprawling */}
      <div className="filters-bar">
        <div className="filter-item">
          <label>Search</label>
          <input
            className="form-control-custom"
            style={{ width: '180px' }}
            placeholder="Product name…"
            value={filters.search}
            onChange={(e) => handleFilterChange('search', e.target.value)}
          />
        </div>
        <div className="filter-item">
          <label>SKU</label>
          <input
            className="form-control-custom"
            style={{ width: '140px' }}
            placeholder="SKU…"
            value={filters.sku}
            onChange={(e) => handleFilterChange('sku', e.target.value)}
          />
        </div>
        <div className="filter-item">
          <label>Brand</label>
          <input
            className="form-control-custom"
            style={{ width: '120px' }}
            placeholder="Brand…"
            value={filters.brand}
            onChange={(e) => handleFilterChange('brand', e.target.value)}
          />
        </div>
        <div className="filter-item">
          <label>Category</label>
          <input
            className="form-control-custom"
            style={{ width: '120px' }}
            placeholder="Category…"
            value={filters.category}
            onChange={(e) => handleFilterChange('category', e.target.value)}
          />
        </div>
        <div className="filter-item">
          <label>Subcategory</label>
          <input
            className="form-control-custom"
            style={{ width: '120px' }}
            placeholder="Subcategory…"
            value={filters.subcategory}
            onChange={(e) => handleFilterChange('subcategory', e.target.value)}
          />
        </div>
        <div className="filter-item">
          <label>Status</label>
          <select
            className="form-control-custom"
            style={{ width: '110px' }}
            value={filters.is_active}
            onChange={(e) => handleFilterChange('is_active', e.target.value)}
          >
            <option value="">All</option>
            <option value="true">Active</option>
            <option value="false">Inactive</option>
          </select>
        </div>
      </div>

      {/* Table */}
      <div className="panel panel-sage">
        {loading ? (
          <TableSkeleton rows={6} cols={8} />
        ) : error ? (
          error.type === 'network' ? (
            <EmptyState
              icon="—"
              title="Backend connection unavailable"
              message="Connect the FastAPI backend to load products."
            />
          ) : (
            <ErrorState message={error.message} />
          )
        ) : products.length === 0 ? (
          <EmptyState
            title="No products found"
            message="Add a product or adjust your filters to see results."
          >
            <button className="btn-navy btn-sm mt-3" onClick={() => navigate('/products/new')}>
              + Add Product
            </button>
          </EmptyState>
        ) : (
          <>
            <div className="table-wrap" style={{ border: 'none', borderRadius: 0 }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Product ID</th>
                    <th>SKU</th>
                    <th>Product Name</th>
                    <th>Brand</th>
                    <th>Category</th>
                    <th>Subcategory</th>
                    <th>Unit</th>
                    <th>Status</th>
                    <th>Created</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {products.map((p) => (
                    <tr key={p.id}>
                      <td style={{ fontFamily: 'monospace', fontSize: '0.8rem', color: 'var(--muted-text)' }}>
                        {p.id?.length > 12 ? p.id.substring(0, 8) + '…' : p.id}
                      </td>
                      <td style={{ fontWeight: 500 }}>{p.sku}</td>
                      <td>
                        <Link to={`/products/${p.id}`} className="action-link" style={{ fontWeight: 600 }}>
                          {p.name}
                        </Link>
                      </td>
                      <td>{p.brand || '—'}</td>
                      <td>{p.category || '—'}</td>
                      <td>{p.subcategory || '—'}</td>
                      <td>{p.unit || '—'}</td>
                      <td><ActiveBadge active={p.is_active} /></td>
                      <td style={{ color: 'var(--muted-text)', whiteSpace: 'nowrap' }}>{formatDate(p.created_at)}</td>
                      <td style={{ whiteSpace: 'nowrap' }}>
                        <Link to={`/products/${p.id}`} className="btn-ghost btn-sm">View</Link>
                        <Link to={`/products/${p.id}/edit`} className="btn-ghost btn-sm">Edit</Link>
                        {p.is_active && (
                          <button
                            className="btn-ghost btn-sm"
                            style={{ color: '#B85C3E' }}
                            onClick={() => handleDeactivate(p.id)}
                          >
                            Deactivate
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="pagination-bar">
              <div className="pagination-info">
                Showing {products.length} of {total} products
              </div>
              <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
                <button
                  className="btn-outline btn-sm"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => p - 1)}
                >
                  ← Prev
                </button>
                <span style={{ fontSize: '0.85rem', color: 'var(--muted-text)', padding: '0 8px' }}>
                  Page {page} of {totalPages}
                </span>
                <button
                  className="btn-outline btn-sm"
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Next →
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

export default Products
