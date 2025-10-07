import axios from 'axios'
import { getToken } from './auth'

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'
})

api.interceptors.request.use(config => {
  const token = getToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

export const fetchSystem = () => api.get('/api/stats/system').then(r=>r.data)
export const fetchUsers = () => api.get('/api/stats/users').then(r=>r.data)
export const fetchMessages = () => api.get('/api/stats/messages').then(r=>r.data)
export const login = (username, password) => {
  const fd = new URLSearchParams()
  fd.set('username', username)
  fd.set('password', password)
  fd.set('grant_type', 'password')
  return api.post('/api/auth/login', fd).then(r=>r.data)
}

export default api
