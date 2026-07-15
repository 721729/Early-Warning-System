<template>
  <div class="dash"><header class="topbar"><div class="logo">⚡ 绿电哨兵</div><div class="info"><span>{{ username }}</span></div></header>
  <div class="body">
  <nav class="side"><router-link to="/" class="nav-item">🏠 总览</router-link><router-link to="/alerts" class="nav-item">⚠️ 预警记录</router-link><router-link to="/ai" class="nav-item">🧠 AI分析</router-link><router-link to="/audit" class="nav-item">📋 审计日志</router-link><router-link to="/users" class="nav-item active">👥 用户管理</router-link><a href="#" class="nav-item" @click.prevent="logout">🚪 退出</a></nav>
  <main class="main">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
      <h2 style="font-size:18px;color:#00e5ff">👥 用户管理</h2>
      <button class="btn" @click="showAdd=!showAdd">{{ showAdd?'取消':'+ 新建用户' }}</button>
    </div>
    <div v-if="showAdd" class="card" style="margin-bottom:12px">
      <h3>新建用户</h3>
      <form @submit.prevent="addUser" class="add-form">
        <input v-model="nu.username" placeholder="工号" required class="inp" />
        <input v-model="nu.password" type="password" placeholder="密码" required class="inp" />
        <select v-model="nu.role" class="inp"><option value="admin">管理员</option><option value="plant_manager">厂长</option><option value="maintenance_lead">检修班长</option><option value="operator">值长</option></select>
        <button type="submit" class="btn btn-primary">创建</button>
      </form>
    </div>
    <div class="card"><table><thead><tr><th>ID</th><th>工号</th><th>角色</th><th>姓名</th><th>状态</th><th>创建时间</th><th>操作</th></tr></thead><tbody>
      <tr v-for="u in users" :key="u.id">
        <td>{{ u.id }}</td><td>{{ u.username }}</td><td>{{ u.role }}</td><td>{{ u.realName }}</td><td><span :class="u.active?'ok':'fail'">{{ u.active?'活跃':'禁用' }}</span></td>
        <td>{{ u.created }}</td>
        <td><button class="btn-xs" @click="toggleUser(u)">{{ u.active?'禁用':'启用' }}</button></td>
      </tr></tbody></table></div>
  </main></div></div>
</template>
<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
const router = useRouter()
const username = ref('admin')
const showAdd = ref(false)
const nu = reactive({ username: '', password: '', role: 'operator' })
const users = ref([
  { id:1, username:'admin', role:'管理员', realName:'System Admin', active:true, created:'2026-07-01' },
  { id:2, username:'operator01', role:'值长', realName:'张工', active:true, created:'2026-07-10' },
])
function addUser() {
  users.value.push({ id: users.value.length+1, username: nu.username, role: {admin:'管理员',plant_manager:'厂长',maintenance_lead:'检修班长',operator:'值长'}[nu.role], realName: nu.username, active: true, created: new Date().toISOString().slice(0,10) })
  nu.username=''; nu.password=''; showAdd.value=false
}
function toggleUser(u) { u.active = !u.active }
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
.card h3{font-size:13px;color:#ccd6f6;margin-bottom:10px}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;padding:10px 8px;color:#8892b0;border-bottom:1px solid #1e2d3d;font-size:11px}
td{padding:10px 8px;border-bottom:1px solid #1a2332}
.btn{padding:6px 16px;border:1px solid #37474f;border-radius:4px;background:transparent;color:#00e5ff;cursor:pointer;font-size:12px}
.btn-primary{background:#1565c0;border-color:#1565c0;color:#fff}
.btn-xs{padding:4px 10px;font-size:11px;border:1px solid #37474f;border-radius:4px;background:transparent;color:#00e5ff;cursor:pointer}
.add-form{display:flex;gap:8px}
.inp{padding:6px 10px;border:1px solid #37474f;border-radius:4px;background:#0a0e17;color:#ccd6f6;font-size:13px;flex:1;outline:none}
.inp:focus{border-color:#00e5ff}
.ok{color:#00e676}.fail{color:#ff1744}
</style>
