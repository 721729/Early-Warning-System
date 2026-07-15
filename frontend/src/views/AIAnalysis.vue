<template>
  <div class="dash"><header class="topbar"><div class="logo">⚡ 绿电哨兵</div><div class="info"><span>{{ username }}</span></div></header>
  <div class="body">
  <nav class="side"><router-link to="/" class="nav-item">🏠 总览</router-link><router-link to="/alerts" class="nav-item">⚠️ 预警记录</router-link><router-link to="/ai" class="nav-item active">🧠 AI分析</router-link><router-link to="/audit" class="nav-item">📋 审计日志</router-link><router-link to="/users" class="nav-item">👥 用户管理</router-link><a href="#" class="nav-item" @click.prevent="logout">🚪 退出</a></nav>
  <main class="main">
    <h2 style="font-size:18px;color:#00e5ff;margin-bottom:16px">🧠 AI 模型分析</h2>
    <div class="grid2">
      <div class="card"><h3>📊 消融实验结果</h3>
        <table><thead><tr><th>指标</th><th>纯AI</th><th>物理+AI</th><th>效果</th></tr></thead>
        <tbody><tr v-for="r in ablation" :key="r.name"><td>{{ r.name }}</td><td>{{ r.b }}</td><td>{{ r.c }}</td><td>{{ r.effect }}</td></tr></tbody></table>
      </div>
      <div class="card"><h3>⚙️ 模型信息</h3>
        <div class="info-list"><div v-for="i in modelInfo" :key="i.k" class="info-row"><span class="ik">{{ i.k }}</span><span class="iv">{{ i.v }}</span></div></div>
      </div>
    </div>
    <div class="card" style="margin-top:12px"><h3>🔬 RevIN 开关对比</h3>
      <p style="font-size:13px;color:#b0bec5;line-height:1.8">
        原版 PatchTST 默认启用 RevIN 实例归一化。实测对比：<br/>
        <b>RevIN=ON</b>：训练 loss 0.012（优秀）→ 异常检测 F1=0.04（几乎全部漏检）<br/>
        <b>RevIN=OFF</b>：训练 loss 0.020（可接受）→ 异常检测 F1=0.86（检出优秀）<br/>
        结论：RevIN 为时序预测设计，会抹除正常/异常的分布差异。本方案采用 RevIN=OFF 配置。
      </p>
    </div>
  </main></div></div>
</template>
<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
const router = useRouter()
const username = ref('admin')
const ablation = ref([
  { name: 'F1分数', b: '0.863', c: '0.855', effect: '持平' },
  { name: '误报率', b: '6.0%', c: '2.8%', effect: '↓53%' },
  { name: '漏报率', b: '6.2%', c: '17.2%', effect: '↑11pp' },
  { name: '准确率', b: '93.9%', c: '94.2%', effect: '+0.3pp' },
  { name: '物理一致性', b: '100%', c: '100%', effect: '持平' },
])
const modelInfo = ref([
  { k: '模型架构', v: 'GitHub 原版 PatchTST (ICLR 2023)' },
  { k: '参数量', v: '473,907' },
  { k: '序列长度', v: '48 小时（小时级采样）' },
  { k: '物理约束', v: '阿伦尼乌斯腐蚀方程 (λ=0.1)' },
  { k: '训练数据', v: '前100天正常工况, 471个窗口' },
  { k: '测试数据', v: '后80天, 312个窗口（含异常段）' },
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
.card{background:#111827;border:1px solid #1e2d3d;border-radius:8px;padding:14px}
.card h3{font-size:13px;color:#ccd6f6;margin-bottom:10px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:12px}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;padding:8px;color:#8892b0;border-bottom:1px solid #1e2d3d;font-size:11px}
td{padding:8px;border-bottom:1px solid #1a2332}
.info-list{display:flex;flex-direction:column;gap:8px}
.info-row{display:flex;justify-content:space-between;font-size:13px;padding:6px 0;border-bottom:1px solid #1a2332}
.ik{color:#8892b0}.iv{color:#00e5ff}
</style>
