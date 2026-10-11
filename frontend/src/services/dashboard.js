import api from './api'

export function getDashboardOverview() {
  return api.get('/api/dashboard/overview')
}

export function getDashboardProductStats(params = {}) {
  return api.get('/api/dashboard/products', { params })
}

export function getDashboardDuplicateStats(params = {}) {
  return api.get('/api/dashboard/duplicates', { params })
}

export function getDashboardActivity(params = {}) {
  return api.get('/api/dashboard/activity', { params })
}
