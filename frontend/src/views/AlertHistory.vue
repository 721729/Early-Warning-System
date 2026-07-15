<template>
  <div class="dash"><header class="topbar"><div class="logo">⚡ 绿电哨兵</div><div class="info"><span>{{ username }}</span></div></header>
  <div class="body">
  <nav class="side"><router-link to="/" class="nav-item">🏠 总览</router-link><router-link to="/alerts" class="nav-item active">⚠️ 预警记录</router-link><router-link to="/ai" class="nav-item">🧠 AI分析</router-link><router-link to="/audit" class="nav-item">📋 审计日志</router-link><router-link to="/users" class="nav-item">👥 用户管理</router-link><a href="#" class="nav-item" @click.prevent="logout">🚪 退出</a></nav>
  <main class="main">
    <h2 style="font-size:18px;color:#00e5ff;margin-bottom:16px">⚠️ 预警历史记录</h2>
    <div class="card"><table><thead><tr><th>时间</th><th>等级</th><th>设备</th><th>预警原因</th><th>AI置信度</th><th>状态</th><th>操作</th></tr></thead><tbody>
      <tr v-for="a in alerts" :key="a.id">
        <td>{{ a.time }}</td><td><span :class="'badge badge-'+a.level">{{ a.level }}</span></td>
        <td>{{ a.device }}</td><td style="max-width:300px;font-size:12px">{{ a.reason }}</td>
        <td>{{ a.conf }}%</td><td>{{ a.status }}</td>
        <td><button class="btn-xs" @click="showDetail(a)">详情</button></td>
      </tr></tbody></table></div>
  </main></div></div>
</template>
<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
const router = useRouter()
const username = ref(JSON.parse(localStorage.getItem('user_info')||'{}').username||'admin')
const alerts = ref([
  { id:1,time:'2026-07-15 08:15',level:'orange',device:'高温过热器入口段',reason:'HCl浓度连续48h超出基线30%，腐蚀速率加速至0.35mm/年',conf:85.2,status:'已确认'},
  { id:2,time:'2026-07-14 22:30',level:'yellow',device:'引风机',reason:'振动幅度超出正常范围15%',conf:62.1,status:'已关闭'},
  { id:3,time:'2026-07-13 14:00',level:'red',device:'高温过热器入口段',reason:'壁厚逼近最小允许值3.2mm，建议立即停炉',conf:96.7,status:'已处理'},
])
function showDetail(a) { alert(`设备: ${a.device}\n原因: ${a.reason}\nAI置信度: ${a.conf}%`) }
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
