import axios from 'axios'

const baseURL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.code === 'ECONNABORTED' || error.code === 'ERR_NETWORK' || !error.response) {
      return Promise.reject({
        type: 'network',
        message: 'Backend connection unavailable.',
        detail: error.message,
      })
    }

    const data = error.response?.data
    let message = error.message

    if (data) {
      if (typeof data.error === 'string') {
        message = data.error
      } else if (typeof data.detail === 'string') {
        message = data.detail
      } else if (Array.isArray(data.detail)) {
        // FastAPI / Pydantic validation errors array
        message = data.detail
          .map((item) => (item.loc ? `${item.loc.slice(1).join('.')}: ${item.msg}` : item.msg || JSON.stringify(item)))
          .join('; ')
      } else if (typeof data.message === 'string') {
        message = data.message
      }
    }

    const payload = {
      type: 'http',
      status: error.response?.status,
      message,
      data,
    }
    return Promise.reject(payload)
  }
)

export default api
