import axios from 'axios'
import router from '../router'

const request = axios.create({
  baseURL: '/api/v1',
  timeout: 60000,  // AI推理+仿真生成最长60秒
  headers: { 'Content-Type': 'application/json' }
})

// -------- 请求拦截器: 自动带 JWT --------
request.interceptors.request.use(config => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
}, error => Promise.reject(error))

// -------- 响应拦截器: 401 → 清token跳登录 --------
request.interceptors.response.use(
  response => response,
  error => {
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('user_info')
      router.push('/login')
    }
    return Promise.reject(error)
  }
)

// -------- API 封装 --------
export const authAPI = {
  login: (data) => request.post('/auth/login', data),
  logout: () => request.post('/auth/logout')
}

export const healthAPI = {
  overview: (plantId = 1) => request.get('/health/overview', { params: { plant_id: plantId } }),
  detail: (deviceId, range = '7d') => request.get(`/health/device/${deviceId}`, { params: { time_range: range } })
}

export const alertAPI = {
  active: (plantId = 1) => request.get('/alert/active', { params: { plant_id: plantId } }),
  confirm: (alertId, data) => request.post(`/alert/${alertId}/confirm`, data),
  history: (plantId = 1, start, end) => request.get('/alert/history', { params: { plant_id: plantId, start, end } }),
  edit: (alertId, data) => request.put(`/alert/${alertId}`, data),
  delete: (alertId) => request.delete(`/alert/${alertId}`),
  updateStatus: (alertId, status) => request.put(`/alert/${alertId}/status`, null, { params: { status } }),
  deleteAll: () => request.delete('/alert/all')
}

export const predictAPI = {
  trend: (deviceId, horizon = '24h') => request.get(`/predict/trend/${deviceId}`, { params: { horizon } }),
  wall: (deviceId, horizon = '14d') => request.get(`/predict/wall/${deviceId}`, { params: { horizon } }),
  rul: (deviceId) => request.get(`/predict/rul/${deviceId}`)
}

export const maintenanceAPI = {
  advice: (alertId) => request.get(`/maintenance/advice/${alertId}`),
  workorders: () => request.get('/maintenance/workorders'),
  autoCreateWO: (alertId) => request.post('/maintenance/workorder/auto_create', { alert_id: alertId }),
  editWO: (woId, data) => request.put(`/maintenance/workorders/${woId}`, data),
  deleteWO: (woId) => request.delete(`/maintenance/workorders/${woId}`),
  deleteAllWO: () => request.delete('/maintenance/workorders/all')
}

export const userAPI = {
  list: () => request.get('/users'),
  create: (data) => request.post('/users', data),
  update: (uid, data) => request.put(`/users/${uid}`, data),
  changePassword: (uid, data) => request.put(`/users/${uid}/password`, data)
}

export const notifyAPI = {
  list: () => request.get('/notifications'),
  create: (content) => request.post('/notifications', { content }),
  edit: (nid, content) => request.put(`/notifications/${nid}`, { content }),
  delete: (nid) => request.delete(`/notifications/${nid}`)
}

export default request
