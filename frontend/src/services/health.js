import api from './api'

export function checkHealth() {
  return api.get('/health')
}

export function checkDbHealth() {
  return api.get('/health/db')
}

export function getAppInfo() {
  return api.get('/')
}
