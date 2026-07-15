import { createRouter, createWebHistory } from 'vue-router'
import Login from '../views/Login.vue'
import Dashboard from '../views/Dashboard.vue'
import AlertHistory from '../views/AlertHistory.vue'
import AuditLog from '../views/AuditLog.vue'
import UserManagement from '../views/UserManagement.vue'
import AIAnalysis from '../views/AIAnalysis.vue'

const routes = [
  { path: '/login', name: 'Login', component: Login, meta: { guest: true } },
  { path: '/', name: 'Dashboard', component: Dashboard, meta: { requiresAuth: true } },
  { path: '/alerts', name: 'AlertHistory', component: AlertHistory, meta: { requiresAuth: true } },
  { path: '/audit', name: 'AuditLog', component: AuditLog, meta: { requiresAuth: true } },
  { path: '/users', name: 'UserManagement', component: UserManagement, meta: { requiresAuth: true } },
  { path: '/ai', name: 'AIAnalysis', component: AIAnalysis, meta: { requiresAuth: true } },
  { path: '/:pathMatch(.*)*', redirect: '/' }
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('access_token')
  if (to.meta.requiresAuth && !token) return next('/login')
  if (to.meta.guest && token) return next('/')
  next()
})

export default router
