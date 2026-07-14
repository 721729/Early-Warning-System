import { createRouter, createWebHistory } from 'vue-router'
import Login from '../views/Login.vue'
import Dashboard from '../views/Dashboard.vue'

const routes = [
  { path: '/login', name: 'Login', component: Login, meta: { guest: true } },
  { path: '/', name: 'Dashboard', component: Dashboard, meta: { requiresAuth: true } },
  { path: '/:pathMatch(.*)*', redirect: '/' }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// -------- 路由守卫 --------
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('access_token')

  // 需要登录 → 没token → 跳登录
  if (to.meta.requiresAuth && !token) {
    return next('/login')
  }

  // 已登录 → 访问登录页 → 跳主页
  if (to.meta.guest && token) {
    return next('/')
  }

  next()
})

export default router
