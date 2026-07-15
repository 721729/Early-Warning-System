<template>
  <div class="dash"><header class="topbar"><div class="logo">⚡ 绿电哨兵</div><div class="info"><span>{{ username }}</span></div></header>
  <div class="body">
  <nav class="side"><router-link to="/" class="nav-item">🏠 总览</router-link><router-link to="/alerts" class="nav-item active">⚠️ 预警记录</router-link><router-link to="/workorders" class="nav-item">📋 工单管理</router-link><router-link to="/inventory" class="nav-item">📦 备件库存</router-link><router-link to="/ai" class="nav-item">🧠 AI分析</router-link><router-link to="/audit" class="nav-item">📋 审计日志</router-link><router-link to="/users" class="nav-item">👥 用户管理</router-link><a href="#" class="nav-item" @click.prevent="logout">🚪 退出</a></nav>
  <main class="main">
    <h2 style="font-size:18px;color:#00e5ff;margin-bottom:16px">⚠️ 预警历史记录 <button class="btn btn-del" style="margin-left:12px" @click="delAll">🗑 一键清空</button></h2>
    <div class="card"><table><thead><tr><th>时间</th><th>等级</th><th>原因</th><th>损失</th><th>状态</th><th>修复记录</th><th>操作</th></tr></thead><tbody>
      <tr v-for="a in alerts" :key="a.id">
        <td>{{ (a.alert_time||'').slice(0,16) }}</td>
        <td><span :class="'badge badge-'+(a.alert_level||'yellow')">{{ a.alert_level }}</span></td>
        <td style="max-width:250px;font-size:12px">
          <span v-if="a._editing"><input v-model="a._reason" class="inp-xs" @keydown.enter.prevent /></span>
          <span v-else>{{ (a.reason||'').slice(0,60) }}</span>
        </td>
        <td>¥{{ (a.predicted_loss||0).toLocaleString() }}</td>
        <td>
          <select @change="chStatus(a,$event)" class="sel-xs" :value="a.status">
            <option value="pending">待处理</option><option value="confirmed">已确认</option><option value="processing">处理中</option><option value="resolved">已修复</option>
          </select>
        </td>
        <td><input v-model="a._res" placeholder="修复记录" class="inp-xs" @keydown.enter.prevent /></td>
        <td class="actions">
          <button v-if="!a._editing" class="btn-xs" @click="a._editing=true;a._reason=a.reason">✎</button>
          <button v-if="a._editing" class="btn-xs" @click="saveEdit(a)">💾</button>
          <button v-if="a._res!==(a.resolution||'')" class="btn-xs" @click="saveRes(a)">💾</button>
          <button class="btn-xs btn-del" @click="delAlert(a.id)">🗑</button>
        </td>
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
onMounted(load)
async function load() { try { const r = await alertAPI.history(); alerts.value = r.data.map(a=>({...a,_editing:false,_reason:a.reason,_res:a.resolution||''})) } catch(_){} }
async function saveEdit(a) { try { await alertAPI.edit(a.id,{reason:a._reason}); a.reason=a._reason; a._editing=false; load() } catch(_){} }
async function saveRes(a) { try { await alertAPI.edit(a.id,{resolution:a._res}); a.resolution=a._res; load() } catch(_){} }
async function chStatus(a,ev) { try { await alertAPI.updateStatus(a.id,ev.target.value); a.status=ev.target.value; load() } catch(_){} }
async function delAll(){if(!confirm("确认删除所有预警和工单?"))return;try{await alertAPI.deleteAll();load()}catch(_){}}
async function delAlert(id) { if(!confirm('确认删除?关联工单也会删除'))return; try{await alertAPI.delete(id);load()}catch(_){} }
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
.badge{padding:2px 8px;border-radius:10px;font-size:10px;font-weight:700}
.badge-orange{background:#ff9100;color:#000}.badge-red{background:#ff1744;color:#fff}.badge-yellow{background:#ffeb3b;color:#000}.badge-green{background:#00e676;color:#000}
.actions{display:flex;gap:4px}
.btn-xs{padding:3px 7px;font-size:10px;border:1px solid #37474f;border-radius:3px;background:transparent;color:#00e5ff;cursor:pointer}
.btn-del{border-color:#ff5252;color:#ff5252}
.inp-xs{padding:3px 6px;border:1px solid #37474f;border-radius:3px;background:#0a0e17;color:#ccd6f6;font-size:11px;width:100px}
.sel-xs{padding:3px;font-size:11px;border:1px solid #37474f;border-radius:3px;background:#0a0e17;color:#ccd6f6}
</style>
