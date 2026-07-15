<template>
  <div class="dash"><header class="topbar"><div class="logo">⚡ 绿电哨兵</div><div class="info"><span>{{ username }}</span></div></header>
  <div class="body">
  <nav class="side"><router-link to="/" class="nav-item">🏠 总览</router-link><router-link to="/alerts" class="nav-item">⚠️ 预警记录</router-link><router-link to="/workorders" class="nav-item">📋 工单管理</router-link><router-link to="/inventory" class="nav-item active">📦 备件库存</router-link><router-link to="/ai" class="nav-item">🧠 AI分析</router-link><router-link to="/audit" class="nav-item">📋 审计日志</router-link><router-link to="/users" class="nav-item">👥 用户管理</router-link><a href="#" class="nav-item" @click.prevent="logout">🚪 退出</a></nav>
  <main class="main">
    <h2 style="font-size:18px;color:#00e5ff;margin-bottom:16px">📦 备件库存管理 {{ isAdmin ? '(可编辑)' : '(只读)' }}</h2>
    <div class="card"><table><thead><tr><th>名称</th><th>类型</th><th>库存量</th><th>最低库存</th><th>状态</th><th>库位</th><th v-if="isAdmin">操作</th></tr></thead><tbody>
      <tr v-for="s in stock" :key="s.id">
        <td>{{ s.name }}</td><td>{{ s.type }}</td>
        <td>
          <input v-if="isAdmin && s._editing" v-model.number="s._qty" type="number" class="inp-xs" />
          <span v-else :class="s.qty <= s.min_stock ? 'warn' : ''">{{ s.qty }} {{ s.unit }}</span>
        </td>
        <td><input v-if="isAdmin && s._editing" v-model.number="s._min" type="number" class="inp-xs" style="width:50px"/>
            <span v-else>{{ s.min_stock }}</span></td>
        <td><span :class="s.qty <= s.min_stock ? 'badge badge-red' : 'badge badge-green'">{{ s.qty <= s.min_stock ? '⚠ 不足' : '✓ 充足' }}</span></td>
        <td><input v-if="isAdmin && s._editing" v-model="s._loc" class="inp-xs" />
            <span v-else>{{ s.location }}</span></td>
        <td v-if="isAdmin" class="actions">
          <button v-if="!s._editing" class="btn-xs" @click="s._editing=true;s._qty=s.qty;s._min=s.min_stock;s._loc=s.location">✎</button>
          <button v-if="s._editing" class="btn-xs" @click="save(s)">💾</button>
          <button v-if="s._editing" class="btn-xs" @click="s._editing=false">✖</button>
        </td>
      </tr></tbody></table></div>
  </main></div></div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import request from '../api/request'
const router = useRouter()
const username = ref(JSON.parse(localStorage.getItem('user_info')||'{}').username||'admin')
const isAdmin = ref((JSON.parse(localStorage.getItem('user_info')||'{}')).role === 'admin')
const stock = ref([])
onMounted(async () => { try { const r = await request.get('/inventory/list'); stock.value = r.data } catch(_){} })
async function save(s) { try { await request.put(`/inventory/${s.id}`,{qty:s._qty,min_stock:s._min,location:s._loc}); s.qty=s._qty; s.min_stock=s._min; s.location=s._loc; s._editing=false } catch(_){} }
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
.warn{color:#ff9100;font-weight:700}
.badge{padding:2px 8px;border-radius:10px;font-size:10px;font-weight:700}
.badge-green{background:#00e676;color:#000}.badge-red{background:#ff1744;color:#fff}
.actions{display:flex;gap:4px}
.btn-xs{padding:3px 7px;font-size:10px;border:1px solid #37474f;border-radius:3px;background:transparent;color:#00e5ff;cursor:pointer}
.inp-xs{padding:3px 6px;border:1px solid #37474f;border-radius:3px;background:#0a0e17;color:#ccd6f6;font-size:11px;width:70px}
</style>
