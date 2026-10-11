import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { createProduct, getProductById, updateProduct, deleteProduct } from '../services/products'
import { LoadingState, ErrorState } from '../components/StateComponents'

const emptyForm = {
  sku: '',
  name: '',
  description: '',
  brand: '',
  category: '',
  subcategory: '',
  unit: '',
  attributes: {},
}

const ProductForm = ({ mode }) => {
  const { id } = useParams()
  const navigate = useNavigate()
  const isEdit = mode === 'edit'

  const [form, setForm] = useState(emptyForm)
  const [attrPairs, setAttrPairs] = useState([{ key: '', value: '' }])
  const [errors, setErrors] = useState({})
  const [loading, setLoading] = useState(isEdit)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [checkDupBeforeSave, setCheckDupBeforeSave] = useState(false)

  useEffect(() => {
    if (!isEdit) return
    let active = true
    async function load() {
      setLoading(true)
      try {
        const res = await getProductById(id)
        if (!active) return
        const p = res.data
        setForm({
          sku: p.sku || '',
          name: p.name || '',
          description: p.description || '',
          brand: p.brand || '',
          category: p.category || '',
          subcategory: p.subcategory || '',
          unit: p.unit || '',
          attributes: p.attributes || {},
        })
        const entries = Object.entries(p.attributes || {})
        setAttrPairs(entries.length > 0 ? entries.map(([k, v]) => ({ key: k, value: String(v) })) : [{ key: '', value: '' }])
      } catch (e) {
        if (active) setError(e)
      } finally {
        if (active) setLoading(false)
      }
    }
    load()
    return () => { active = false }
  }, [id, isEdit])

  const handleChange = (field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }))
    if (error) setError(null)
    if (errors[field]) {
      setErrors((prev) => {
        const c = { ...prev }
        delete c[field]
        return c
      })
    }
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

  const validate = () => {
    const e = {}
    if (!form.sku.trim()) e.sku = 'SKU is required'
    if (!form.name.trim()) e.name = 'Product name is required'
    setErrors(e)
    return Object.keys(e).length === 0
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!validate()) return

    setSaving(true)
    setError(null)
    try {
      if (isEdit) {
        const updatePayload = {
          name: form.name.trim(),
          description: form.description.trim() || undefined,
          brand: form.brand.trim() || undefined,
          category: form.category.trim() || undefined,
          subcategory: form.subcategory.trim() || undefined,
          unit: form.unit.trim() || undefined,
          attributes: buildAttributes(),
        }
        await updateProduct(id, updatePayload)
        navigate(`/products/${id}`)
      } else {
        const createPayload = {
          sku: form.sku.trim(),
          name: form.name.trim(),
          description: form.description.trim() || undefined,
          brand: form.brand.trim() || undefined,
          category: form.category.trim() || undefined,
          subcategory: form.subcategory.trim() || undefined,
          unit: form.unit.trim() || undefined,
          attributes: buildAttributes(),
          is_active: true,
        }
        const res = await createProduct(createPayload)
        const newProduct = res.data
        const newId = newProduct?.id
        if (checkDupBeforeSave && newProduct) {
          navigate('/duplicates', { state: { product: newProduct } })
        } else {
          navigate(newId ? `/products/${newId}` : '/products')
        }
      }
    } catch (err) {
      setError(err)
      if (err.status === 409) {
        setErrors((prev) => ({
          ...prev,
          sku: err.message || `A product with SKU '${form.sku.trim()}' already exists.`,
        }))
      }
      setSaving(false)
    }
  }

  const handleDeactivate = async () => {
    if (!window.confirm('Deactivate this product?')) return
    try {
      await deleteProduct(id)
      navigate('/products')
    } catch (err) {
      alert('Failed to deactivate: ' + (err.message || 'Unknown error'))
    }
  }

  if (loading) {
    return (
      <div className="fade-in">
        <div className="page-header"><h2>{isEdit ? 'Edit Product' : 'Add Product'}</h2></div>
        <div className="panel"><LoadingState message="Loading product…" /></div>
      </div>
    )
  }

  if (error && isEdit && !form.sku) {
    return (
      <div className="fade-in">
        <div className="page-header"><h2>Edit Product</h2></div>
        <div className="panel">
          {error.type === 'network' ? (
            <ErrorState title="Backend connection unavailable" message="Connect the backend to edit this product." />
          ) : (
            <ErrorState message={error.message} />
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="fade-in">
      <div className="page-header">
        <div className="page-header-row">
          <div>
            <h2>{isEdit ? 'Edit Product' : 'Add Product'}</h2>
            <div className="page-subtitle">
              {isEdit ? `Editing ${form.name || form.sku}` : 'Create a new product master record'}
            </div>
          </div>
          <Link to={isEdit ? `/products/${id}` : '/products'} className="btn-outline">
            ← Back
          </Link>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="panel" style={{ maxWidth: '800px' }}>
        <div className="panel-body">
          {error && (
            <div className="card-base mb-3" style={{ padding: '12px 16px', borderColor: 'var(--muted-peach)', background: 'var(--muted-peach-light)' }}>
              <div style={{ fontSize: '0.85rem', color: '#B57A6A', fontWeight: 500 }}>
                {error.message || 'An error occurred while saving.'}
              </div>
            </div>
          )}

          {/* Required fields */}
          <h4 className="mb-3">Required Information</h4>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-3)' }} className="form-grid">
            <div className="form-group">
              <label className="form-label">SKU<span className="required">*</span></label>
              <input
                className="form-control-custom"
                value={form.sku}
                onChange={(e) => handleChange('sku', e.target.value)}
                disabled={isEdit}
                placeholder="e.g. LP-Dell-XPS15-2024"
              />
              {errors.sku && <div className="form-error">{errors.sku}</div>}
              {isEdit && <div className="form-hint">SKU cannot be changed after creation</div>}
            </div>
            <div className="form-group">
              <label className="form-label">Product Name<span className="required">*</span></label>
              <input
                className="form-control-custom"
                value={form.name}
                onChange={(e) => handleChange('name', e.target.value)}
                placeholder="e.g. Dell XPS 15 9530"
              />
              {errors.name && <div className="form-error">{errors.name}</div>}
            </div>
          </div>

          {/* Optional fields */}
          <h4 className="mt-4 mb-3">Additional Details</h4>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-3)' }} className="form-grid">
            <div className="form-group">
              <label className="form-label">Brand</label>
              <input
                className="form-control-custom"
                value={form.brand}
                onChange={(e) => handleChange('brand', e.target.value)}
                placeholder="e.g. Dell"
              />
            </div>
            <div className="form-group">
              <label className="form-label">Category</label>
              <input
                className="form-control-custom"
                value={form.category}
                onChange={(e) => handleChange('category', e.target.value)}
                placeholder="e.g. Laptops"
              />
            </div>
            <div className="form-group">
              <label className="form-label">Subcategory</label>
              <input
                className="form-control-custom"
                value={form.subcategory}
                onChange={(e) => handleChange('subcategory', e.target.value)}
                placeholder="e.g. Ultrabooks"
              />
            </div>
            <div className="form-group">
              <label className="form-label">Unit</label>
              <input
                className="form-control-custom"
                value={form.unit}
                onChange={(e) => handleChange('unit', e.target.value)}
                placeholder="e.g. pcs"
              />
            </div>
          </div>
          <div className="form-group">
            <label className="form-label">Description</label>
            <textarea
              className="form-control-custom"
              rows={3}
              value={form.description}
              onChange={(e) => handleChange('description', e.target.value)}
              placeholder="Product description…"
            />
          </div>

          {/* Dynamic attributes */}
          <h4 className="mt-4 mb-3">Attributes &amp; Specifications</h4>
          <div className="form-hint mb-3">Add key/value pairs for product specifications like Model, RAM, Storage, Processor, Screen Size, etc.</div>
          {attrPairs.map((pair, idx) => (
            <div key={idx} style={{ display: 'flex', gap: '8px', marginBottom: '8px', alignItems: 'center' }}>
              <input
                className="form-control-custom"
                style={{ flex: 1 }}
                placeholder="Attribute name (e.g. RAM)"
                value={pair.key}
                onChange={(e) => handleAttrChange(idx, 'key', e.target.value)}
              />
              <span style={{ color: 'var(--muted-text)' }}>→</span>
              <input
                className="form-control-custom"
                style={{ flex: 1 }}
                placeholder="Value (e.g. 16 GB)"
                value={pair.value}
                onChange={(e) => handleAttrChange(idx, 'value', e.target.value)}
              />
              {attrPairs.length > 1 && (
                <button type="button" className="btn-ghost btn-sm" onClick={() => removeAttrRow(idx)}>
                  ✕
                </button>
              )}
            </div>
          ))}
          <button type="button" className="btn-outline btn-sm" onClick={addAttrRow}>
            ＋ Add Attribute
          </button>

          {/* Check for duplicates option (add mode only) */}
          {!isEdit && (
            <div className="mt-4" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <input
                type="checkbox"
                id="checkDup"
                checked={checkDupBeforeSave}
                onChange={(e) => setCheckDupBeforeSave(e.target.checked)}
              />
              <label htmlFor="checkDup" style={{ fontSize: '0.88rem', cursor: 'pointer', color: 'var(--navy)' }}>
                Check for duplicates before saving
              </label>
            </div>
          )}

          {/* Actions */}
          <div className="mt-4" style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', borderTop: '1px solid var(--soft-border)', paddingTop: 'var(--space-3)' }}>
            <button type="submit" className="btn-navy" disabled={saving}>
              {saving ? 'Saving…' : isEdit ? 'Save Changes' : 'Create Product'}
            </button>
            <Link to={isEdit ? `/products/${id}` : '/products'} className="btn-outline">
              Cancel
            </Link>
            {isEdit && (
              <button type="button" className="btn-outline" style={{ color: '#B85C3E', borderColor: 'var(--muted-peach)' }} onClick={handleDeactivate}>
                Deactivate
              </button>
            )}
          </div>
        </div>
      </form>
    </div>
  )
}

export default ProductForm
