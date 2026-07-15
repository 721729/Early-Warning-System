<template>
  <div class="dash"><header class="topbar"><div class="logo">⚡ 绿电哨兵</div><div class="info"><span>{{ username }}</span></div></header>
  <div class="body">
  <nav class="side"><router-link to="/" class="nav-item">🏠 总览</router-link><router-link to="/alerts" class="nav-item">⚠️ 预警记录</router-link><router-link to="/workorders" class="nav-item">📋 工单管理</router-link><router-link to="/inventory" class="nav-item">📦 备件库存</router-link><router-link to="/ai" class="nav-item">🧠 AI分析</router-link><router-link to="/audit" class="nav-item">📋 审计日志</router-link><router-link to="/users" class="nav-item active">👥 用户管理</router-link><a href="#" class="nav-item" @click.prevent="logout">🚪 退出</a></nav>
  <main class="main">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
      <h2 style="font-size:18px;color:#00e5ff">👥 用户管理</h2>
      <button class="btn" @click="showAdd=!showAdd">{{ showAdd?'取消':'+ 新建用户' }}</button>
    </div>
    <div v-if="showAdd" class="card" style="margin-bottom:12px"><h3>新建用户</h3>
      <form @submit.prevent="addUser" class="add-form">
        <input v-model="nu.username" placeholder="工号（字母数字下划线）" required class="inp" pattern="[a-zA-Z0-9_]{2,32}" />
        <input v-model="nu.password" type="password" placeholder="密码（至少6位）" required class="inp" />
        <select v-model="nu.role" class="inp"><option value="operator">值长</option><option value="maintenance_lead">检修班长</option><option value="plant_manager">厂长</option><option value="admin">管理员</option></select>
        <button type="submit" class="btn btn-primary">创建</button>
      </form>
      <p v-if="msg" :class="msgType">{{ msg }}</p>
    </div>
    <!-- 修改密码 -->
    <div v-if="showPwd" class="card" style="margin-bottom:12px"><h3>修改密码 · {{ pwdTarget.username }}</h3>
      <form @submit.prevent="changePwd" class="add-form">
        <input v-if="!isAdmin" v-model="pwd.old" type="password" placeholder="旧密码" class="inp" />
        <input v-model="pwd.new" type="password" placeholder="新密码（至少6位）" required class="inp" />
        <button type="submit" class="btn btn-primary">确认修改</button>
        <button type="button" class="btn" @click="showPwd=false">取消</button>
      </form>
    </div>
    <div class="card"><table><thead><tr><th>ID</th><th>工号</th><th>角色</th><th>状态</th><th>创建时间</th><th>操作</th></tr></thead><tbody>
      <tr v-for="u in users" :key="u.id">
        <td>{{ u.id }}</td><td>{{ u.username }}</td><td>{{ roleMap[u.role] || u.role }}</td>
        <td><span :class="u.is_active?'ok':'fail'">{{ u.is_active?'活跃':'禁用' }}</span></td>
        <td>{{ (u.created_at||'').slice(0,10) }}</td>
        <td class="actions">
          <button class="btn-xs" @click="startPwd(u)">改密</button>
          <button class="btn-xs" @click="toggleUser(u)">{{ u.is_active?'禁用':'启用' }}</button>
          <select @change="changeRole(u, $event)" class="sel-xs">
            <option value="">角色...</option>
            <option value="operator">值长</option>
            <option value="maintenance_lead">检修班长</option>
            <option value="plant_manager">厂长</option>
            <option value="admin">管理员</option>
          </select>
        </td>
      </tr></tbody></table></div>
  </main></div></div>
</template>
<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { userAPI } from '../api/request'
const router = useRouter()
const username = ref(JSON.parse(localStorage.getItem('user_info')||'{}').username||'admin')
const isAdmin = ref(true)
const users = ref([])
const showAdd = ref(false), showPwd = ref(false), msg = ref(''), msgType = ref('ok')
const nu = reactive({ username:'', password:'', role:'operator' })
const pwd = reactive({ old:'', new:'' }), pwdTarget = ref({})
const roleMap = { admin:'管理员', plant_manager:'厂长', maintenance_lead:'检修班长', operator:'值长' }

onMounted(loadUsers)
async function loadUsers() {
  try { const r = await userAPI.list(); users.value = r.data } catch(_){}
}
async function addUser() {
  try { await userAPI.create({ username:nu.username, password:nu.password, role:nu.role, real_name:nu.username }); nu.username=''; nu.password=''; showAdd.value=false; msg.value='创建成功'; msgType.value='ok'; loadUsers() } catch(e) { msg.value=e.response?.data?.detail||'创建失败'; msgType.value='err' }
}
function startPwd(u) { pwdTarget.value = u; pwd.old=''; pwd.new=''; showPwd.value = true }
async function changePwd() {
  try { await userAPI.changePassword(pwdTarget.value.id, { old_password: pwd.old||'', new_password: pwd.new }); showPwd.value=false; msg.value='密码已修改'; msgType.value='ok' } catch(e) { msg.value=e.response?.data?.detail||'修改失败'; msgType.value='err' }
}
async function toggleUser(u) {
  try { await userAPI.update(u.id, { is_active: !u.is_active }); loadUsers() } catch(e) { alert(e.response?.data?.detail||'操作失败') }
}
async function changeRole(u, ev) {
  if (!ev.target.value) return
  try { await userAPI.update(u.id, { role: ev.target.value }); loadUsers() } catch(e) { alert(e.response?.data?.detail||'操作失败') }
}
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
.card{background:#111827;border:1px solid #1e2d3d;border-radius:8px;padding:14px;overflow-x:auto;margin-bottom:12px}
.card h3{font-size:13px;color:#ccd6f6;margin-bottom:10px}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;padding:10px 8px;color:#8892b0;border-bottom:1px solid #1e2d3d;font-size:11px}
td{padding:10px 8px;border-bottom:1px solid #1a2332}
.actions{display:flex;gap:6px;align-items:center}
.btn{padding:6px 16px;border:1px solid #37474f;border-radius:4px;background:transparent;color:#00e5ff;cursor:pointer;font-size:12px}
.btn-primary{background:#1565c0;border-color:#1565c0;color:#fff}
.btn-xs{padding:4px 8px;font-size:11px;border:1px solid #37474f;border-radius:4px;background:transparent;color:#00e5ff;cursor:pointer}
.sel-xs{padding:4px;font-size:11px;border:1px solid #37474f;border-radius:4px;background:#0a0e17;color:#ccd6f6}
.add-form{display:flex;gap:8px;flex-wrap:wrap}
.inp{padding:6px 10px;border:1px solid #37474f;border-radius:4px;background:#0a0e17;color:#ccd6f6;font-size:13px;outline:none}
.inp:focus{border-color:#00e5ff}
.ok{color:#00e676}.fail{color:#ff1744}.err{color:#ff1744;font-size:12px}
</style>
