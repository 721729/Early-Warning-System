<template>
  <div class="dash">
    <!-- 顶栏 -->
    <header class="topbar">
      <div class="logo">⚡ 绿电哨兵</div>
      <div class="info">
        <span class="plant">新沂项目 #1炉 · 运行中</span>
        <span class="time">{{ now }}</span>
        <span class="user">{{ username }}</span>
        <span class="dot-live"></span> 实时
      </div>
    </header>

    <div class="body">
      <!-- 侧边栏 -->
      <nav class="side">
        <router-link to="/" class="nav-item active">🏠 总览</router-link>
        <router-link to="/alerts" class="nav-item">⚠️ 预警记录</router-link>
        <router-link to="/ai" class="nav-item">🧠 AI分析</router-link>
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
          <div class="kpi" :class="data.ai_alert === 'orange' ? 'red' : 'green'"><div class="kv">{{ data.ai_alert === 'orange' ? '⚠ 异常' : '✓ 正常' }}</div><div class="kl">化学+AI 实时判定</div></div>
        </div>

        <!-- 焚烧炉剖面图 + 实时数据 -->
        <div class="row2">
          <section class="card boiler">
            <h3>🔥 焚烧炉受热面 · 实时健康度</h3>
            <div class="health-bars">
              <div v-for="d in healthDevs" :key="d.name" class="hbar">
                <span class="hname">{{ d.name }}</span>
                <div class="h-track"><div :class="'hfill '+d.health" :style="{width: d.pct+'%'}"></div></div>
                <span :class="'htag '+d.health">{{ d.label }}</span>
              </div>
            </div>
            <div class="health-legend">
              <span><i class="dot g"></i>健康(>85%)</span><span><i class="dot y"></i>关注(70-85%)</span><span><i class="dot o"></i>预警(50-70%)</span><span><i class="dot r"></i>危险(<50%)</span>
            </div>
          </section>
          <section class="card live-data">
            <h3>📡 实时传感器数据 <span class="live-tag">LIVE</span></h3>
            <div class="sensor-grid">
              <div class="sensor" v-for="s in sensors" :key="s.label">
                <div class="sl">{{ s.label }}</div>
                <div class="sv" :class="{ warn: s.warn }">{{ s.value }} <small>{{ s.unit }}</small></div>
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
              <div class="am-ai">🤖 AI置信度: {{ a.confidence }}% | 预估损失: ¥{{ a.loss.toLocaleString() }}</div>
            </div>
          </section>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import { startSimulation } from '../api/simulator'

const router = useRouter()
const username = ref('admin')
const now = ref('')
const runDays = ref(195)
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

let stopSim = null
onMounted(() => {
  stopSim = startSimulation((d) => {
    Object.assign(data, d)
    runDays.value = 195 + Math.floor(Math.random() * 3)
    // 更新健康度
    healthDevs.value[0].health = d.ai_alert === 'orange' ? 'orange' : 'green'
    healthDevs.value[0].pct = +((d.wall_thickness || 5.9) / 6.0 * 100).toFixed(0)
    healthDevs.value[0].label = d.ai_alert === 'orange' ? `预警 ${healthDevs.value[0].pct}%` : `健康 ${healthDevs.value[0].pct}%`
    sensors.value = [
      { label: '炉膛温度', value: d.furnace_temp, unit: '°C', warn: d.furnace_temp < 550 },
      { label: 'HCl 浓度', value: d.hcl_conc, unit: 'mg/m³', warn: d.hcl_conc > 1500 },
      { label: 'SO₂ 浓度', value: d.so2_conc, unit: 'mg/m³', warn: false },
      { label: 'O₂ 含量', value: d.o2_conc, unit: '%', warn: false },
      { label: '主蒸汽流量', value: d.main_steam_flow, unit: 't/h', warn: false },
      { label: '主蒸汽温度', value: d.main_steam_temp, unit: '°C', warn: false },
    ]
    mockAlerts.value = d.ai_alert === 'orange' ? [{
      id: Date.now(), level: 'orange',
      title: '过热器腐蚀加速预警',
      time: new Date().toLocaleTimeString('zh-CN'),
      desc: `HCl浓度升高至${d.hcl_conc}mg/m³，AI检测到腐蚀速率异常加速，当前壁厚${d.wall_thickness}mm`,
      confidence: +(d.ai_anomaly_score * 100).toFixed(1),
      loss: 420000
    }] : []
    activeAlerts.value = mockAlerts.value.length
    nextTick(drawTrend)
  })
  nextTick(drawTrend)
})
onUnmounted(() => { clearInterval(clock); if (stopSim) stopSim() })

const trend = ref(null)
function drawTrend() {
  if (!trend.value) return
  const c = echarts.init(trend.value)
  const days = [], wall = [], ai = []
  let v = 5.98
  for (let i = 0; i < 195; i++) {
    days.push(i + 1)
    wall.push(+(v - 0.35 / 365 * i).toFixed(2))
    ai.push(+(v - 0.35 / 365 * i + (Math.random() - 0.5) * 0.06).toFixed(2))
  }
  c.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' },
    legend: { data: ['🤖 AI+化学预测值', '📏 实际测量(超声)', '⚠ 危险阈值(3.0mm)'], textStyle: { color: '#8892b0', fontSize: 11 }, top: 5 },
    grid: { left: 60, right: 30, top: 40, bottom: 40 },
    xAxis: { type: 'category', data: days, axisLabel: { color: '#8892b0', fontSize: 10 }, name: '运行天数', nameTextStyle: { color: '#8892b0' }, splitLine: { show: false } },
    yAxis: { type: 'value', min: 2.5, max: 6.5, axisLabel: { color: '#8892b0' }, name: '壁厚 (mm)', nameTextStyle: { color: '#8892b0' }, splitLine: { show: false } },
    series: [
      { name: '🤖 AI预测值', type: 'line', data: ai, smooth: true, lineStyle: { color: '#00e5ff', width: 2.5 }, symbol: 'none', areaStyle: { color: 'rgba(0,229,255,0.06)' } },
      { name: '📏 实际测量(超声)', type: 'line', data: wall, smooth: true, lineStyle: { color: '#ff9100', width: 2 }, symbol: 'none' },
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
.chart-l { width: 100%; height: 280px; }
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
.health-legend { display: flex; gap: 16px; margin-top: 10px; font-size: 10px; color: #546e7a; }
.health-legend .dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 4px; }
.dot.g { background: #00e676; } .dot.y { background: #ffeb3b; } .dot.o { background: #ff9100; } .dot.r { background: #ff1744; }
.sensor-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.sensor { background: #0a0e17; border-radius: 6px; padding: 10px; }
.sl { font-size: 11px; color: #8892b0; margin-bottom: 4px; }
.sv { font-size: 20px; font-weight: 700; color: #00e5ff; }
.sv.warn { color: #ff9100; }
.sv small { font-size: 11px; color: #8892b0; }
.alert-mini { background: #1a2332; border-radius: 6px; padding: 10px; margin-bottom: 8px; border-left: 3px solid #ff9100; }
.alert-mini.red { border-left-color: #ff1744; }
.am-head { display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 4px; }
.am-time { color: #546e7a; font-size: 10px; }
.am-body { font-size: 12px; color: #b0bec5; margin: 4px 0; line-height: 1.4; }
.am-ai { font-size: 10px; color: #00bcd4; }
.empty { color: #546e7a; font-size: 13px; text-align: center; padding: 30px; }
</style>
