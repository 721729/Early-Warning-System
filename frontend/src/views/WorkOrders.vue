<template>
  <div class="dash"><header class="topbar"><div class="logo">⚡ 绿电哨兵</div><div class="info"><span>{{ username }}</span></div></header>
  <div class="body">
  <nav class="side"><router-link to="/" class="nav-item">🏠 总览</router-link><router-link to="/alerts" class="nav-item">⚠️ 预警记录</router-link><router-link to="/workorders" class="nav-item active">📋 工单管理</router-link><router-link to="/ai" class="nav-item">🧠 AI分析</router-link><router-link to="/audit" class="nav-item">📋 审计日志</router-link><router-link to="/users" class="nav-item">👥 用户管理</router-link><a href="#" class="nav-item" @click.prevent="logout">🚪 退出</a></nav>
  <main class="main">
    <h2 style="font-size:18px;color:#00e5ff;margin-bottom:16px">📋 工单管理</h2>
    <div class="card"><table><thead><tr><th>工单号</th><th>关联预警</th><th>设备</th><th>故障描述</th><th>处理方案</th><th>备件</th><th>状态</th><th>创建时间</th></tr></thead><tbody>
      <tr v-for="w in workorders" :key="w.id">
        <td style="color:#00e5ff">#{{ w.id }}</td>
        <td>{{ w.alert_id ? '#'+w.alert_id : '—' }}</td>
        <td>设备#{{ w.device_id }}</td>
        <td style="max-width:200px;font-size:12px">{{ (w.fault_desc||'').slice(0,60) }}</td>
        <td style="max-width:180px;font-size:12px">{{ (w.action_plan||'').slice(0,60) }}</td>
        <td style="font-size:11px">{{ (w.spare_parts||'').slice(0,40) }}</td>
        <td><span :class="'badge badge-'+w.status">{{ w.status }}</span></td>
        <td>{{ (w.create_time||'').slice(0,16) }}</td>
      </tr></tbody></table></div>
  </main></div></div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { maintenanceAPI } from '../api/request'
const router = useRouter()
const username = ref(JSON.parse(localStorage.getItem('user_info')||'{}').username||'admin')
const workorders = ref([])
onMounted(async () => { try { const r = await maintenanceAPI.workorders(); workorders.value = r.data } catch(_){} })
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
.badge-draft{background:#546e7a;color:#fff}.badge-issued{background:#ff9100;color:#000}.badge-in_progress{background:#00bcd4;color:#000}.badge-completed{background:#00e676;color:#000}
</style>
