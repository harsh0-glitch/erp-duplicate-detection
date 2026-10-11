import api from './api'

export function checkDuplicates(data, params = {}) {
  return api.post('/api/duplicates/check', data, { params })
}

export function getDuplicateHistory(params = {}) {
  const query = { ...params }
  if (query.limit !== undefined && query.page_size === undefined) {
    query.page_size = Math.min(Number(query.limit), 100)
    delete query.limit
  }
  if (query.product_id !== undefined && query.query_product_id === undefined) {
    query.query_product_id = query.product_id
    delete query.product_id
  }
  return api.get('/api/duplicates/history', { params: query })
}

export function getDuplicateById(id) {
  return api.get(`/api/duplicates/${id}`)
}

export function confirmDuplicate(id, data = {}) {
  const payload = { ...data }
  if (payload.reviewer !== undefined && payload.reviewer_id === undefined) {
    payload.reviewer_id = payload.reviewer
    delete payload.reviewer
  }
  return api.post(`/api/duplicates/${id}/confirm`, payload)
}

export function rejectDuplicate(id, data = {}) {
  const payload = { ...data }
  if (payload.reviewer !== undefined && payload.reviewer_id === undefined) {
    payload.reviewer_id = payload.reviewer
    delete payload.reviewer
  }
  return api.post(`/api/duplicates/${id}/reject`, payload)
}
