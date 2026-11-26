import axios from 'axios'

const API_BASE = '/api'

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
})

// Request interceptor to add auth token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('wzdm_session')
  if (token) {
    try {
      const parsed = JSON.parse(token)
      if (parsed.access_token) {
        config.headers.Authorization = `Bearer ${parsed.access_token}`
      }
    } catch (e) {
      // invalid token
    }
  }
  return config
})

// Response interceptor to handle 401
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('wzdm_session')
      window.location.href = '/sign-in'
    }
    return Promise.reject(err)
  },
)

export default api
