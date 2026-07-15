<template>
  <div class="dash"><header class="topbar"><div class="logo">⚡ 绿电哨兵</div><div class="info"><span>{{ username }}</span></div></header>
  <div class="body">
  <nav class="side"><router-link to="/" class="nav-item">🏠 总览</router-link><router-link to="/alerts" class="nav-item">⚠️ 预警记录</router-link><router-link to="/workorders" class="nav-item active">📋 工单管理</router-link><router-link to="/inventory" class="nav-item">📦 备件库存</router-link><router-link to="/ai" class="nav-item">🧠 AI分析</router-link><router-link to="/audit" class="nav-item">📋 审计日志</router-link><router-link to="/users" class="nav-item">👥 用户管理</router-link><a href="#" class="nav-item" @click.prevent="logout">🚪 退出</a></nav>
  <main class="main">
    <h2 style="font-size:18px;color:#00e5ff;margin-bottom:16px">📋 工单管理 <button class="btn btn-del" style="margin-left:12px" @click="delAll">🗑 一键清空</button></h2>
    <div class="card"><table><thead><tr><th>#</th><th>关联预警</th><th>故障描述</th><th>处理方案</th><th>备件</th><th>维修人</th><th>状态</th><th>操作</th></tr></thead><tbody>
      <tr v-for="w in workorders" :key="w.id">
        <td style="color:#00e5ff">#{{ w.id }}</td>
        <td>{{ w.alert_id ? '#'+w.alert_id : '—' }}</td>
        <td><input v-if="w._editing" v-model="w._fault" class="inp-xs" />
            <span v-else style="font-size:12px">{{ (w.fault_desc||'').slice(0,40) }}</span></td>
        <td><input v-if="w._editing" v-model="w._plan" class="inp-xs" />
            <span v-else style="font-size:12px">{{ (w.action_plan||'').slice(0,40) }}</span></td>
        <td><input v-if="w._editing" v-model="w._parts" class="inp-xs" />
            <span v-else style="font-size:11px">{{ (w.spare_parts||'').slice(0,30) }}</span></td>
        <td><input v-model="w._assignee" class="inp-xs" placeholder="指派" @change="saveAssignee(w)" /></td>
        <td>
          <select @change="chStatus(w,$event)" class="sel-xs" :value="w.status">
            <option value="draft">草稿</option><option value="issued">已下发</option><option value="in_progress">维修中</option><option value="completed">已修复</option>
          </select>
        </td>
        <td class="actions">
          <button v-if="!w._editing" class="btn-xs" @click="startEdit(w)">✎</button>
          <button v-if="w._editing" class="btn-xs" @click="saveEdit(w)">💾</button>
          <button class="btn-xs btn-del" @click="delWO(w.id)">🗑</button>
        </td>
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
onMounted(load)
async function load() { try { const r = await maintenanceAPI.workorders(); workorders.value = r.data.map(w=>({...w,_editing:false,_fault:w.fault_desc,_plan:w.action_plan,_parts:w.spare_parts,_assignee:w.assignee})) } catch(_){} }
function startEdit(w) { w._editing=true; w._fault=w.fault_desc; w._plan=w.action_plan; w._parts=w.spare_parts }
async function saveEdit(w) { try { await maintenanceAPI.editWO(w.id,{fault_desc:w._fault,action_plan:w._plan,spare_parts:w._parts}); w.fault_desc=w._fault; w.action_plan=w._plan; w.spare_parts=w._parts; w._editing=false; load() } catch(_){} }
async function chStatus(w,ev) { try { await maintenanceAPI.editWO(w.id,{status:ev.target.value}); w.status=ev.target.value; load() } catch(_){} }
async function saveAssignee(w) { try { await maintenanceAPI.editWO(w.id,{assignee:w._assignee}) } catch(_){} }
async function delAll(){if(!confirm("确认删除所有工单?"))return;try{await maintenanceAPI.deleteAllWO();load()}catch(_){}}
async function delWO(id) { if(!confirm('确认删除?'))return; try{await maintenanceAPI.deleteWO(id);load()}catch(_){} }
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
th{text-align:left;padding:8px 6px;color:#8892b0;border-bottom:1px solid #1e2d3d;font-size:11px}
td{padding:8px 6px;border-bottom:1px solid #1a2332}
.actions{display:flex;gap:4px}
.btn-xs{padding:3px 7px;font-size:10px;border:1px solid #37474f;border-radius:3px;background:transparent;color:#00e5ff;cursor:pointer}
.btn-del{border-color:#ff5252;color:#ff5252}
.inp-xs{padding:3px 6px;border:1px solid #37474f;border-radius:3px;background:#0a0e17;color:#ccd6f6;font-size:11px;width:80px}
.sel-xs{padding:3px;font-size:11px;border:1px solid #37474f;border-radius:3px;background:#0a0e17;color:#ccd6f6}
</style>
