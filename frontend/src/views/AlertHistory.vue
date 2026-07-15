<template>
  <div class="dash"><header class="topbar"><div class="logo">⚡ 绿电哨兵</div><div class="info"><span>{{ username }}</span></div></header>
  <div class="body">
  <nav class="side"><router-link to="/" class="nav-item">🏠 总览</router-link><router-link to="/alerts" class="nav-item active">⚠️ 预警记录</router-link><router-link to="/ai" class="nav-item">🧠 AI分析</router-link><router-link to="/audit" class="nav-item">📋 审计日志</router-link><router-link to="/users" class="nav-item">👥 用户管理</router-link><a href="#" class="nav-item" @click.prevent="logout">🚪 退出</a></nav>
  <main class="main">
    <h2 style="font-size:18px;color:#00e5ff;margin-bottom:16px">⚠️ 预警历史记录</h2>
    <div class="card"><table><thead><tr><th>时间</th><th>等级</th><th>设备</th><th>预警原因</th><th>预估损失</th><th>状态</th><th>操作</th></tr></thead><tbody>
      <tr v-for="a in alerts" :key="a.id">
        <td>{{ (a.alert_time||'').slice(0,19) }}</td><td><span :class="'badge badge-'+(a.alert_level||'yellow')">{{ a.alert_level }}</span></td>
        <td>设备#{{ a.device_id }}</td><td style="max-width:300px;font-size:12px">{{ (a.reason||'').slice(0,80) }}</td>
        <td>¥{{ (a.predicted_loss||0).toLocaleString() }}</td><td>{{ a.status }}</td>
        <td><button class="btn-xs" @click="showDetail(a)">详情</button></td>
      </tr></tbody></table></div>
  </main></div></div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { alertAPI } from '../api/request'
const router = useRouter()
const username = ref(JSON.parse(localStorage.getItem('user_info')||'{}').username||'admin')
const alerts = ref([])

onMounted(async () => { try { const r = await alertAPI.history(); alerts.value = r.data } catch(_){} })
function showDetail(a) { alert(`设备ID: ${a.device_id}\n原因: ${a.reason}\n状态: ${a.status}`) }
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
.badge{padding:2px 8px;border-radius:10px;font-size:10px;font-weight:700}
.badge-orange{background:#ff9100;color:#000}.badge-red{background:#ff1744;color:#fff}.badge-yellow{background:#ffeb3b;color:#000}
.btn-xs{padding:4px 10px;font-size:11px;border:1px solid #37474f;border-radius:4px;background:transparent;color:#00e5ff;cursor:pointer}
</style>
