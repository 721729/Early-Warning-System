<template>
  <div class="dash">
    <!-- 顶栏 -->
    <header class="topbar">
      <div class="logo">⚡ 绿电哨兵</div>
      <div class="info">
        <span class="plant">新沂项目 #1炉 · 仿真运行中</span>
        <span class="time-ctrl">
          <button class="btn-time" @click="toggleAuto">{{ autoMode ? '⏸ 暂停' : '▶ 自动推进' }}</button>
          <button class="btn-time" @click="resetSim">🔄 重置</button>
          <button class="btn-time" @click="jumpToAnomaly">⏩ 快进到异常</button>
          <button class="btn-time" @click="jumpToDanger">🔴 危险工况</button>
          <span style="font-size:10px;color:#546e7a">{{ runDays }}h</span>
        </span>
        <span class="time">{{ now }}</span>
        <span class="user">{{ username }}</span>
        <span class="dot-live"></span> 仿真Demo
      </div>
    </header>

    <div class="body">
      <!-- 侧边栏 -->
      <nav class="side">
        <router-link to="/" class="nav-item active">🏠 总览</router-link>
        <router-link to="/alerts" class="nav-item">⚠️ 预警记录</router-link>
        <router-link to="/workorders" class="nav-item">📋 工单管理</router-link>
        <router-link to="/inventory" class="nav-item">📦 备件库存</router-link><router-link to="/ai" class="nav-item">🧠 AI分析</router-link>
        <router-link to="/audit" class="nav-item">📋 审计日志</router-link>
        <router-link to="/users" class="nav-item">👥 用户管理</router-link>
        <a href="#" class="nav-item" @click.prevent="logout">🚪 退出</a>
      </nav>

      <!-- 主区域 -->
      <main class="main">
        <!-- KPI 卡片行 -->
        <div class="kpis">
          <div class="kpi green"><div class="kv">6/6</div><div class="kl">设备在线</div></div>
          <div class="kpi cyan"><div class="kv">{{ runDays }}</div><div class="kl">运行天数</div></div>
          <div class="kpi orange pulse"><div class="kv">{{ activeAlerts }}</div><div class="kl">活跃预警</div></div>
          <div class="kpi blue"><div class="kv">{{ (data.wall_thickness || 5.9).toFixed(2) }}mm</div><div class="kl">高温过热器壁厚</div></div>
          <div class="kpi cyan"><div class="kv" style="font-size:14px">🤖 在线</div><div class="kl">PatchTST AI引擎</div></div>
          <div class="kpi" :class="data.ai_alert === 'orange' ? 'red' : data.ai_alert === 'yellow' ? 'orange' : 'green'"><div class="kv">{{ data.ai_alert === 'orange' ? '⚠' : data.ai_alert === 'yellow' ? '⚡' : '✓' }}</div><div class="kl">AI实时判定</div></div>
        </div>

        <!-- 通知栏: 只显示最新一条 -->
        <div class="notice-bar">
          <span class="notice-icon">📢</span>
          <div class="notice-scroll">
            <span v-if="!notices.length" class="notice-item">系统运行正常，暂无新通知</span>
            <span v-else class="notice-item" style="white-space:normal;word-break:break-all">{{ notices[0].content }} <small>({{ notices[0].created_by }} · {{ notices[0].created_at }})</small></span>
          </div>
          <button v-if="isAdmin" class="btn-notice-manage" @click="showNotices=!showNotices">⚙️ 管理</button>
        </div>
        <!-- admin通知管理面板 -->
        <div v-if="showNotices && isAdmin" class="notice-admin card">
          <h3>📢 通知管理</h3>
          <div class="notice-add-row">
            <input v-model="newNotice" placeholder="输入新通知内容..." class="inp" @keydown.enter.prevent />
            <button class="btn btn-primary btn-sm" @click="addNotice">发布</button>
          </div>
          <div v-for="n in notices" :key="'edit-'+n.id" class="notice-edit-row">
            <input v-model="n._edit" class="inp" @keydown.enter.prevent />
            <button class="btn btn-sm" @click="saveNotice(n)">保存</button>
            <button class="btn btn-sm btn-del" @click="delNotice(n.id)">删除</button>
          </div>
        </div>

        <!-- 焚烧炉剖面图 + 实时数据 -->
        <div class="row2">
          <section class="card boiler">
            <h3>🔥 焚烧炉受热面 · 实时健康度</h3>
            <div class="health-bars">
              <div v-for="d in healthDevs" :key="d.name" class="hbar">
                <span class="hname">{{ d.name }}</span>
                <div class="h-track"><div :class="'hfill '+d.health" :style="{width: d.pct+'%'}"></div></div>
                <span :class="'htag '+d.health">{{ d.label }} {{ d.pct }}%</span>
                <span class="hdetail">{{ d.rate }}mm/年</span>
              </div>
            </div>
            <div class="health-legend">
              <span><i class="dot g"></i>健康 &gt;90%</span><span><i class="dot y"></i>关注 75-90%</span><span><i class="dot o"></i>预警 50-75%</span><span><i class="dot r"></i>危险 &lt;50%</span>
            </div>
          </section>
          <section class="card live-data">
            <h3>📡 传感器数据 <span class="live-tag">仿真Demo · 阿伦尼乌斯方程驱动</span></h3>
            <div class="sensor-grid">
              <div class="sensor" v-for="s in sensors" :key="s.label">
                <div class="sl">{{ s.label }}</div>
                <div class="sv" :class="{ warn: s.warn, textVal: s.isText }">{{ s.value }} <small v-if="s.unit">{{ s.unit }}</small></div>
              </div>
            </div>
          </section>
        </div>

        <!-- 底部双面板 -->
        <div class="row3">
          <section class="card">
            <h3>📈 壁厚衰减趋势 — AI预测 vs 实际测量</h3>
            <div ref="trend" class="chart-l"></div>
          </section>
          <section class="card alerts-panel">
            <h3>⚠️ 实时预警</h3>
            <div v-if="mockAlerts.length === 0" class="empty">✅ 当前无活跃预警</div>
            <div v-for="a in mockAlerts" :key="a.id" :class="['alert-mini', a.level]">
              <div class="am-head">
                <span>{{ a.level === 'red' ? '🔴' : a.level === 'orange' ? '🟠' : '🟡' }} {{ a.title }}</span>
                <span class="am-time">{{ a.time }}</span>
              </div>
              <div class="am-body">{{ a.desc }}</div>
              <div class="am-ai">🤖 AI检测 | ⏱ 提前{{ a.rul_days || '?' }}天预警 | 预估损失: ¥{{ (a.loss||0).toLocaleString() }}</div>
              <div class="am-actions"><button class="btn btn-xs btn-primary" @click="showAdviceForAlert(a)">📋 运维建议</button></div>
            </div>
          </section>
        </div>
      </main>
    </div>

    <!-- 运维建议弹窗 -->
    <div v-if="adviceData" class="modal-overlay" @click.self="adviceData=null">
      <div class="modal"><h3>🔧 运维建议</h3>
        <div class="advice-sect"><b>故障现象:</b> {{ adviceData.phenomenon }}</div>
        <div class="advice-sect"><b>根因诊断:</b> {{ adviceData.root_cause }}</div>
        <div class="advice-sect"><b>处理方案:</b> {{ adviceData.action_plan }}</div>
        <div class="advice-sect"><b>备件清单:</b> {{ adviceData.spare_parts }}</div>
        <div class="advice-sect"><b>历史案例:</b> {{ adviceData.similar_cases }}</div>
        <p style="margin-top:8px;font-size:11px;color:#546e7a">工单ID: #{{ adviceData.work_order_id }}</p>
        <button class="btn btn-primary" style="margin-top:8px" @click="adviceData=null">关闭</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import request, { notifyAPI, healthAPI, maintenanceAPI, alertAPI } from '../api/request'

const router = useRouter()
const username = ref('admin')
const now = ref('')
const runDays = ref(195)
const autoMode = ref(true)

// 自动推进: 每次轮询前进1小时
async function autoAdvance() {
  try {
    const r = await request.get('/health/overview', { params: { advance: 1 } })
    if (r.data?.length) updateDashboard(r.data)
  } catch(e) { console.warn('[绿电哨兵]', e.message) }
}

// 跳转到异常时段
async function jumpToAnomaly() {
  autoMode.value = false
  try {
    await request.get('/health/overview', { params: { reset: true } })
    const r = await request.get('/health/overview', { params: { advance: 2880 } })
    if (r.data?.length) updateDashboard(r.data)
  } catch(e) {}
}

// 跳转到危险工况（danger模式：A=2500×60天）
async function jumpToDanger() {
  autoMode.value = false
  try {
    await request.get('/health/overview', { params: { reset: true, danger: true } })
    // 跳入危险期中段(×45加速, 约3600h), 而非跳过危险期 — advance=5000会完全错过危险窗口(2880-4320h)
    const r = await request.get('/health/overview', { params: { advance: 3600, danger: true } })
    if (r.data?.length) updateDashboard(r.data)
  } catch(e) {}
}

// 重置仿真
async function resetSim() {
  try {
    await request.get('/health/overview', { params: { reset: true } })
    pollAI()
  } catch(e) {}
}

function toggleAuto() { autoMode.value = !autoMode.value }
const notices = ref([])
const showNotices = ref(false)
const newNotice = ref('')
const isAdmin = ref((JSON.parse(localStorage.getItem('user_info')||'{}')).role === 'admin')

async function loadNotices() {
  try {
    const r = await notifyAPI.list()
    notices.value = r.data.map(n => ({...n, _edit: n.content}))
  } catch(_) {}
}
async function addNotice() {
  if (!newNotice.value.trim()) return
  try { await notifyAPI.create(newNotice.value.trim()); newNotice.value=''; loadNotices() } catch(_) {}
}
async function saveNotice(n) {
  try { await notifyAPI.edit(n.id, n._edit); n.content = n._edit; loadNotices() } catch(_) {}
}
async function delNotice(nid) {
  if (!confirm('确认删除此通知？')) return
  try { await notifyAPI.delete(nid); loadNotices() } catch(_) {}
}
// 运维建议弹窗
const adviceData = ref(null)
async function showAdviceForAlert(a) {
  try {
    const r = await maintenanceAPI.advice(a.id || 9999)
    adviceData.value = r.data
  } catch(_) { alert('运维建议加载失败') }
}

const data = reactive({ wall_thickness: 5.90, rul_days: 5000, ai_alert: 'green' })
const activeAlerts = ref(1)
const sensors = ref([])
const mockAlerts = ref([])
const healthDevs = ref([
  { name: '高温过热器(入口)', health: 'green', pct: 92, label: '健康 92%' },
  { name: '高温过热器(出口)', health: 'yellow', pct: 78, label: '关注 78%' },
  { name: '中温过热器', health: 'green', pct: 95, label: '健康 95%' },
  { name: '低温过热器', health: 'green', pct: 97, label: '健康 97%' },
  { name: '省煤器', health: 'green', pct: 99, label: '健康 99%' },
])

const clock = setInterval(() => { now.value = new Date().toLocaleString('zh-CN') }, 1000)

let pollTimer = null


// 每5秒从后端拉取AI推理的真实设备数据
// 轮询当前数据(不推进仿真)
async function pollAI() {
  try {
    const r = await request.get('/health/overview', { params: { advance: 0 } })
    if (r.data?.length) updateDashboard(r.data)
  } catch(e) { console.warn('[绿电哨兵]', e.message) }
}

// 更新仪表盘所有数据
function updateDashboard(devs) {
  if (!devs?.length) return
  const d1 = devs[0] || {}
  const safeGet = (obj, key, fb) => (obj && obj[key] != null) ? obj[key] : fb
  // 从仿真小时换算运行天数, 保留1位小数 (每2-3次轮询可见变化)
  const simHours = safeGet(d1, 'sim_hours', 0)
  runDays.value = Math.round(simHours / 24 * 10) / 10
  Object.assign(data, {
    wall_thickness: safeGet(d1, 'wall_thickness_ai', 5.9),
    corrosion_rate: safeGet(d1, 'corrosion_rate', 0.2),
    rul_days: safeGet(d1, 'rul_days', 5000),
    ai_alert: safeGet(d1, 'health', 'green'),
    hcl_conc: safeGet(d1, 'hcl_conc', 1000),
    flue_temp: safeGet(d1, 'flue_temp', 570),
    ai_score: safeGet(d1, 'ai_anomaly_score', 0.1),
  })
  if (d1.trend) window._trendData = d1.trend
  healthDevs.value = devs.slice(0, 6).map(d => {
    // 健康度百分比: 优先走后端 RUL 驱动的 health_score, 回退兼容旧公式
    const pct = d.health_score != null
      ? d.health_score  // 保留1位小数, 让每步0.05-0.5分的变化可见
      : Math.min(100, Math.max(1, +(((d.wall_thickness_ai || d.original || 6) - 3) / 3 * 100).toFixed(0)))
    // 颜色: AI判定为 yellow/orange/red 时用AI颜色(权威), 否则跟health_score百分比
    const aiLevel = d.health
    const hColor = (aiLevel && aiLevel !== 'green')
      ? aiLevel
      : (pct > 90 ? 'green' : pct > 75 ? 'yellow' : pct > 50 ? 'orange' : 'red')
    return {
      name: d.name, health: hColor, pct,
      label: pct > 90 ? '✓' : pct > 75 ? '⚡' : pct > 50 ? '⚠' : '🔴',
      rate: (d.corrosion_rate || 0.15).toFixed(2),
    }
  })
  const healthMap = { green: '✓ 正常', yellow: '⚡ 关注', orange: '⚠ 异常', red: '🔴 危险' }
  const h = d1.health || 'green'
  const anomaly = h !== 'green'  // AI检测到异常时标记相关参数
  // 15 维实时传感器: 优先读后端 live_sensors 真数据, 回退兼容旧字段
  const s = d1.sensors || {}
  sensors.value = [
    { label: '炉膛温度',      value: (s.flue_temp     ?? d1.flue_temp ?? 570).toFixed(1), unit: '°C',   warn: +(s.flue_temp) < 555 || anomaly },
    { label: 'HCl 浓度',      value: (s.hcl_conc      ?? d1.hcl_conc ?? 1000).toFixed(1), unit: 'mg/m³', warn: +(s.hcl_conc) > 1500 || anomaly },
    { label: 'SO₂ 浓度',      value: (s.so2_conc      ?? 200).toFixed(1), unit: 'mg/m³', warn: +(s.so2_conc) > 300 || anomaly },
    { label: 'CO 浓度',       value: (s.co_conc       ?? 50).toFixed(1), unit: 'mg/m³', warn: +(s.co_conc) > 80 || anomaly },
    { label: 'O₂ 含量',       value: (s.o2_content    ?? 8).toFixed(1), unit: '%',     warn: +(s.o2_content) < 5 || +(s.o2_content) > 11 || anomaly },
    { label: '颗粒物',        value: (s.particle_conc ?? 20).toFixed(1), unit: 'mg/m³', warn: +(s.particle_conc) > 25 || anomaly },
    { label: '高过壁温',      value: (s.sh1_wall_temp ?? 480).toFixed(1), unit: '°C',   warn: anomaly },
    { label: '中过壁温',      value: (s.sh2_wall_temp ?? 440).toFixed(1), unit: '°C',   warn: anomaly },
    { label: '低过壁温',      value: (s.sh3_wall_temp ?? 400).toFixed(1), unit: '°C',   warn: anomaly },
    { label: '高过烟温',      value: (s.sh1_flue_temp ?? 560).toFixed(1), unit: '°C',   warn: anomaly },
    { label: '中过烟温',      value: (s.sh2_flue_temp ?? 540).toFixed(1), unit: '°C',   warn: anomaly },
    { label: '低过烟温',      value: (s.sh3_flue_temp ?? 510).toFixed(1), unit: '°C',   warn: anomaly },
    { label: '主蒸汽流量',    value: (s.steam_flow    ?? 40).toFixed(1), unit: 't/h',   warn: anomaly },
    { label: '主蒸汽压力',    value: (s.steam_press   ?? 4.0).toFixed(2), unit: 'MPa',  warn: anomaly },
    { label: '主蒸汽温度',    value: (s.steam_temp    ?? 400).toFixed(1), unit: '°C',   warn: anomaly },
    { label: 'AI 异常检测',   value: healthMap[h], unit: '', warn: anomaly, isText: true },
    { label: '腐蚀速率',      value: (d1.corrosion_rate || 0).toFixed(2), unit: 'mm/年', warn: +(d1.corrosion_rate) > 1.5 || anomaly },
    { label: '壁厚监测',      value: (d1.wall_thickness_ai || 5.9).toFixed(2), unit: 'mm', warn: +(d1.wall_thickness_ai) < 4 },
    { label: '剩余寿命',      value: (d1.rul_days || 0).toFixed(1), unit: '天', warn: +(d1.rul_days) < 500 },
  ]
  // 预警卡片
  if (h !== 'green') {
    mockAlerts.value = [{
      id: Date.now(), level: h,
      title: h === 'red' ? '壁厚危险预警' : '过热器腐蚀加速预警',
      time: new Date().toLocaleTimeString('zh-CN'),
      desc: `HCl=${(d1.hcl_conc||0).toFixed(0)}mg/m³, 腐蚀${(d1.corrosion_rate||0).toFixed(2)}mm/年, AI-MSE=${(d1.ai_reconstruction_error||0).toFixed(6)}`,
      loss: 420000, rul_days: (d1.rul_days||0).toFixed(1), confidence: 85
    }]
  } else { mockAlerts.value = [] }
  activeAlerts.value = mockAlerts.value.length
  nextTick(drawTrend)
}

onMounted(() => {
  loadNotices()
  pollAI()
  pollTimer = setInterval(() => { if (autoMode.value) autoAdvance() }, 3000)  // 自动模式每3秒推进1h
  nextTick(drawTrend)
})
onUnmounted(() => { clearInterval(clock); if (pollTimer) clearInterval(pollTimer) })

const trend = ref(null)
function drawTrend() {
  if (!trend.value) return
  const c = echarts.init(trend.value)
  // 优先使用API返回的真实趋势数据
  let days = [], wall = [], ai = []
  if (window._trendData && window._trendData.length) {
    const td = window._trendData
    for (let i = 0; i < td.length; i++) {
      days.push(td[i].h || td[i].hour || i+1)
      wall.push(td[i].w || td[i].wall || 5.9)
      ai.push((td[i].w || td[i].wall || 5.9) + (Math.random()-0.5)*0.03)
    }
  } else {
    let v = 5.98
    for (let i = 0; i < 195; i++) { days.push(i+1); wall.push(+(v-0.35/365*i).toFixed(2)); ai.push(+(v-0.35/365*i+(Math.random()-0.5)*0.06).toFixed(2)) }
  }
  c.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' },
    legend: { data: ['🤖 AI+化学预测值', '📏 实际测量(超声)', '⚠ 危险阈值(3.0mm)'], textStyle: { color: '#8892b0', fontSize: 11 }, top: 5 },
    grid: { left: 65, right: 30, top: 40, bottom: 55 },
    xAxis: { type: 'value', min: days[0]||0, max: days[days.length-1]||200, axisLabel: { color: '#8892b0', fontSize: 9, formatter: v => Math.floor(v)+'h' }, name: '运行时间(小时)', nameTextStyle: { color: '#8892b0' }, splitLine: { show: false } },
    yAxis: { type: 'value', min: 2.5, max: 6.5, axisLabel: { color: '#8892b0' }, name: '壁厚(mm)', nameTextStyle: { color: '#8892b0' }, splitLine: { show: false } },
    series: [
      { name: '🤖 AI预测值', type: 'line', data: days.map((d,i) => [d, ai[i]]), smooth: true, lineStyle: { color: '#00e5ff', width: 2.5 }, symbol: 'none', areaStyle: { color: 'rgba(0,229,255,0.06)' } },
      { name: '📏 实际测量', type: 'line', data: days.map((d,i) => [d, wall[i]]), smooth: true, lineStyle: { color: '#ff9100', width: 2 }, symbol: 'none' },
      { name: '⚠ 危险阈值(3.0mm)', type: 'line', markLine: { silent: true, symbol: 'none', lineStyle: { color: '#ff1744', type: 'dashed', width: 2 }, data: [{ yAxis: 3.0, label: { formatter: '3.0mm — 立即停炉', color: '#ff1744', fontSize: 11 } }] }, data: [] }
    ]
  })
}

function logout() { localStorage.clear(); router.push('/login') }
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: "PingFang SC","Microsoft YaHei",sans-serif; background: #0a0e17; color: #ccd6f6; }
.dash { display: flex; flex-direction: column; height: 100vh; overflow: hidden; }
.topbar { display: flex; justify-content: space-between; align-items: center; padding: 0 20px; height: 50px; background: #0d1117; border-bottom: 1px solid #1e2d3d; flex-shrink: 0; }
.topbar .logo { font-size: 18px; font-weight: 700; color: #00e5ff; letter-spacing: 1px; }
.topbar .info { display: flex; align-items: center; gap: 16px; font-size: 12px; color: #8892b0; }
.topbar .plant { color: #64ffda; }
.dot-live { width: 8px; height: 8px; background: #00e676; border-radius: 50%; animation: pulse2 1.5s infinite; }
@keyframes pulse2 { 50% { opacity: .3; } }
.body { display: flex; flex: 1; overflow: hidden; }
.side { width: 180px; background: #0d1117; border-right: 1px solid #1e2d3d; padding: 12px 0; flex-shrink: 0; display: flex; flex-direction: column; }

.nav-item { padding: 12px 20px; font-size: 13px; color: #8892b0; text-decoration: none; transition: all .2s; border-left: 3px solid transparent; }
.nav-item:hover, .nav-item.active { color: #00e5ff; background: rgba(0,229,255,.06); border-left-color: #00e5ff; }
.main { flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 12px; }
.kpis { display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; }
.kpi { background: #111827; border: 1px solid #1e2d3d; border-radius: 8px; padding: 16px; text-align: center; }
.kpi.green { border-left: 3px solid #00e676; }
.kpi.orange { border-left: 3px solid #ff9100; }
.kpi.cyan { border-left: 3px solid #00e5ff; }
.kpi.blue { border-left: 3px solid #448aff; }
.kpi.red { border-left: 3px solid #ff1744; }
.kpi.pulse { animation: borderPulse 2s infinite; }
@keyframes borderPulse { 50% { border-left-color: #ff5252; } }
.kv { font-size: 28px; font-weight: 700; margin-bottom: 4px; }
.kl { font-size: 11px; color: #8892b0; }
.row2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.row3 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.card { background: #111827; border: 1px solid #1e2d3d; border-radius: 8px; padding: 14px; }
.card h3 { font-size: 13px; color: #ccd6f6; margin-bottom: 10px; font-weight: 600; }
.live-tag { color: #00e676; font-size: 10px; margin-left: 6px; animation: pulse2 1s infinite; }
.chart-l { width: 100%; height: 320px; }
.health-bars { display: flex; flex-direction: column; gap: 10px; padding: 8px 0; }
.hbar { display: flex; align-items: center; gap: 10px; }
.hname { width: 120px; font-size: 12px; color: #b0bec5; text-align: right; flex-shrink: 0; }
.h-track { flex: 1; height: 18px; background: #1a2332; border-radius: 9px; overflow: hidden; }
.hfill { height: 100%; border-radius: 9px; transition: width .5s; }
.hfill.green { background: linear-gradient(90deg, #00c853, #00e676); }
.hfill.yellow { background: linear-gradient(90deg, #f9a825, #ffeb3b); }
.hfill.orange { background: linear-gradient(90deg, #e65100, #ff9100); animation: hPulse 1.5s infinite; }
.hfill.red { background: linear-gradient(90deg, #b71c1c, #ff1744); animation: hPulse .8s infinite; }
@keyframes hPulse { 50% { opacity: .7; } }
.htag { width: 80px; font-size: 11px; font-weight: 700; flex-shrink: 0; }
.htag.green { color: #00e676; } .htag.yellow { color: #ffeb3b; } .htag.orange { color: #ff9100; } .htag.red { color: #ff1744; }
.hdetail { width: 160px; font-size: 10px; color: #546e7a; flex-shrink: 0; text-align: right; }
.health-legend { display: flex; gap: 16px; margin-top: 10px; font-size: 10px; color: #546e7a; }
.health-legend .dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 4px; }
.dot.g { background: #00e676; } .dot.y { background: #ffeb3b; } .dot.o { background: #ff9100; } .dot.r { background: #ff1744; }
.sensor-grid { display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 6px; }
.sensor { background: #0a0e17; border-radius: 6px; padding: 8px; }
.sl { font-size: 10px; color: #8892b0; margin-bottom: 2px; }
.sv { font-size: 15px; font-weight: 700; color: #00e5ff; }
.sv.warn { color: #ff9100; }
.sv.textVal { font-size: 16px; }
.sv small { font-size: 11px; color: #8892b0; }
.alert-mini { background: #1a2332; border-radius: 6px; padding: 10px; margin-bottom: 8px; border-left: 3px solid #ff9100; }
.alert-mini.red { border-left-color: #ff1744; }
.am-head { display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 4px; }
.am-time { color: #546e7a; font-size: 10px; }
.am-body { font-size: 12px; color: #b0bec5; margin: 4px 0; line-height: 1.4; }
.am-ai { font-size: 10px; color: #00bcd4; }
.empty { color: #546e7a; font-size: 13px; text-align: center; padding: 30px; }
.notice-bar { background: #1a2332; border: 1px solid #1e2d3d; border-radius: 6px; padding: 8px 14px; display: flex; align-items: center; gap: 10px; font-size: 12px; color: #ffab40; }
.notice-icon { font-size: 16px; flex-shrink: 0; }
.notice-scroll { overflow: hidden; white-space: nowrap; }
.notice-item { margin-right: 40px; }
.notice-item small { color: #546e7a; margin-left: 8px; }
.btn-notice-manage { padding: 4px 10px; border: 1px solid #37474f; border-radius: 4px; background: transparent; color: #00e5ff; cursor: pointer; font-size: 11px; flex-shrink: 0; }
.notice-admin { margin-top: 12px; }
.notice-add-row { display: flex; gap: 8px; margin-bottom: 10px; }
.notice-edit-row { display: flex; gap: 8px; margin-bottom: 6px; align-items: center; }
.notice-edit-row .inp { flex: 1; }
.inp { padding: 6px 10px; border: 1px solid #37474f; border-radius: 4px; background: #0a0e17; color: #ccd6f6; font-size: 12px; outline: none; }
.inp:focus { border-color: #00e5ff; }
.btn-sm { padding: 4px 10px; font-size: 11px; }
.btn-del { border-color: #ff5252; color: #ff5252; }
.btn-del:hover { background: rgba(255,82,82,.1); }
.am-actions { margin-top: 6px; }
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.7); display: flex; align-items: center; justify-content: center; z-index: 999; }
.modal { background: #111827; border: 1px solid #1e2d3d; border-radius: 10px; padding: 24px; width: 520px; max-width: 90vw; max-height: 80vh; overflow-y: auto; }
.modal h3 { font-size: 16px; color: #00e5ff; margin-bottom: 14px; }
.advice-sect { font-size: 13px; color: #b0bec5; margin-bottom: 10px; line-height: 1.6; }
.btn-time { padding: 3px 8px; border: 1px solid #37474f; border-radius: 3px; background: transparent; color: #00e5ff; cursor: pointer; font-size: 10px; margin: 0 2px; }
.btn-time:hover { background: rgba(0,229,255,.1); }
.time-ctrl { display: flex; align-items: center; gap: 4px; font-size: 11px; color: #8892b0; }
</style>
