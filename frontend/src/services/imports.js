import api from './api'

export function uploadProductsFile(file) {
  const formData = new FormData()
  formData.append('file', file)
  return api.post('/api/bulk-upload/products', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
  })
}

export function getImportJob(jobId) {
  return api.get(`/api/bulk-upload/${jobId}`)
}
