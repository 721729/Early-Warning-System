<template>
  <div class="dash"><header class="topbar"><div class="logo">⚡ 绿电哨兵</div><div class="info"><span>{{ username }}</span></div></header>
  <div class="body">
  <nav class="side"><router-link to="/" class="nav-item">🏠 总览</router-link><router-link to="/alerts" class="nav-item">⚠️ 预警记录</router-link><router-link to="/workorders" class="nav-item">📋 工单管理</router-link><router-link to="/inventory" class="nav-item">📦 备件库存</router-link><router-link to="/ai" class="nav-item">🧠 AI分析</router-link><router-link to="/audit" class="nav-item active">📋 审计日志</router-link><router-link to="/users" class="nav-item">👥 用户管理</router-link><a href="#" class="nav-item" @click.prevent="logout">🚪 退出</a></nav>
  <main class="main">
    <h2 style="font-size:18px;color:#00e5ff;margin-bottom:16px">📋 操作审计日志（只读，不可删改）</h2>
    <div class="card"><table><thead><tr><th>时间</th><th>用户</th><th>操作</th><th>对象</th><th>IP</th><th>结果</th></tr></thead><tbody>
      <tr v-for="l in logs" :key="l.id"><td>{{ l.time }}</td><td>{{ l.user }}</td><td>{{ l.action }}</td><td>{{ l.resource }}</td><td>{{ l.ip }}</td><td><span :class="l.result==='success'?'ok':'fail'">{{ l.result }}</span></td></tr></tbody></table></div>
  </main></div></div>
</template>
<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
const router = useRouter()
const username = ref('admin')
const logs = ref([
  { id:1, time:'2026-07-15 10:30', user:'admin', action:'登录', resource:'系统', ip:'192.168.1.100', result:'success' },
  { id:2, time:'2026-07-15 09:15', user:'admin', action:'确认预警', resource:'预警#1', ip:'192.168.1.100', result:'success' },
  { id:3, time:'2026-07-15 08:00', user:'operator01', action:'登录失败(密码错误)', resource:'系统', ip:'192.168.1.105', result:'failure' },
  { id:4, time:'2026-07-14 22:30', user:'admin', action:'创建工单', resource:'工单#2026001', ip:'192.168.1.100', result:'success' },
])
function logout() { localStorage.clear(); router.push('/login') }
</script>
<style scoped>
.dash{display:flex;flex-direction:column;height:100vh}
.topbar{display:flex;justify-content:space-between;align-items:center;padding:0 20px;height:50px;background:#0d1117;border-bottom:1px solid #1e2d3d}
.topbar .logo{font-size:18px;font-weight:700;color:#00e5ff}
.topbar .info{font-size:12px;color:#8892b0}
.body{display:flex;flex:1;overflow:hidden}
.side{width:180px;background:#0d1117;border-right:1px solid #1e2d3d;padding:12px 0;flex-shrink:0;display:flex;flex-direction:column}
.nav-item{padding:12px 20px;font-size:13px;color:#8892b0;text-decoration:none;transition:all .2s;border-left:3px solid transparent}
.nav-item:hover,.nav-item.active{color:#00e5ff;background:rgba(0,229,255,.06);border-left-color:#00e5ff}
.main{flex:1;overflow-y:auto;padding:16px}
.card{background:#111827;border:1px solid #1e2d3d;border-radius:8px;padding:14px;overflow-x:auto}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;padding:10px 8px;color:#8892b0;border-bottom:1px solid #1e2d3d;font-size:11px}
td{padding:10px 8px;border-bottom:1px solid #1a2332}
.ok{color:#00e676}.fail{color:#ff1744}
</style>
