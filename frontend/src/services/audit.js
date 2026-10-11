import api from './api'

export function getAuditLogs(params = {}) {
  const query = { ...params }
  if (query.limit !== undefined && query.page_size === undefined) {
    query.page_size = Math.min(Number(query.limit), 100)
    delete query.limit
  }
  return api.get('/api/audit-logs', { params: query })
}

export function getAuditActivityFeed(params = {}) {
  return api.get('/api/audit-logs/activity', { params })
}

export function getAuditLogById(id) {
  return api.get(`/api/audit-logs/${id}`)
}
