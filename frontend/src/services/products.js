import api from './api'

export function getProducts(params = {}) {
  const query = { ...params }
  if (query.limit !== undefined && query.page_size === undefined) {
    query.page_size = Math.min(Number(query.limit), 100)
    delete query.limit
  }
  return api.get('/api/products', { params: query })
}

export function getProductById(id) {
  return api.get(`/api/products/${id}`)
}

export function createProduct(data) {
  return api.post('/api/products', data)
}

export function updateProduct(id, data) {
  return api.patch(`/api/products/${id}`, data)
}

export function deleteProduct(id) {
  return api.delete(`/api/products/${id}`)
}
