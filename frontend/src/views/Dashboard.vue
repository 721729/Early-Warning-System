<template>
  <div class="dashboard">
    <!-- ========== 顶栏 ========== -->
    <header class="topbar">
      <h1>⚡ 绿电哨兵 · 焚烧炉设备健康度</h1>
      <div class="user-area">
        <span class="plant">新沂项目 #1炉</span>
        <span class="role">{{ user.role }} | {{ user.real_name || user.username }}</span>
        <button class="btn-logout" @click="handleLogout">退出</button>
      </div>
    </header>

    <div class="layout">
      <!-- ========== 左侧设备树 ========== -->
      <aside class="sidebar">
        <h3>设备列表</h3>
        <div v-for="dev in devices" :key="dev.id"
             :class="['device-item', { active: selectedId === dev.id }]"
             @click="selectDevice(dev)">
          <span :class="['dot', dev.health]"></span>
          <span class="name">{{ dev.name }}</span>
          <span v-if="dev.rul_days < 100" class="badge">{{ dev.rul_days }}天</span>
        </div>
      </aside>

      <!-- ========== 中间主区域 ========== -->
      <main class="main">
        <!-- 焚烧炉剖面图 -->
        <section class="boiler-section">
          <h3>焚烧炉受热面健康度</h3>
          <div ref="boilerChart" class="chart-box"></div>
        </section>

        <!-- 底部双面板 -->
        <div class="bottom-panels">
          <!-- 壁厚趋势 -->
          <section class="panel">
            <h3>{{ selectedDevice?.name || '—' }} · 壁厚衰减趋势</h3>
            <div ref="trendChart" class="chart-box-small"></div>
          </section>

          <!-- 预警面板 -->
          <section class="panel">
            <h3>⚠️ 实时预警</h3>
            <div v-if="alerts.length === 0" class="empty">当前无活跃预警</div>
            <div v-for="a in alerts" :key="a.id"
                 :class="['alert-card', a.alert_level]">
              <div class="a-head">
                <span class="a-level">{{ a.alert_level === 'red' ? '🔴' : a.alert_level === 'orange' ? '🟠' : '🟡' }}
                {{ {yellow:'黄',orange:'橙',red:'红'}[a.alert_level] }}级预警</span>
                <span class="a-time">{{ a.alert_time }}</span>
              </div>
              <div class="a-reason">{{ a.reason }}</div>
              <div class="a-loss" v-if="a.predicted_loss">💰 预估损失: ¥{{ a.predicted_loss.toLocaleString() }}</div>
              <div class="a-actions">
                <button class="btn btn-sm btn-primary" @click="confirmAlert(a.id)">确认</button>
                <button class="btn btn-sm" @click="showAdvice(a.id)">运维建议</button>
              </div>
            </div>
          </section>
        </div>
      </main>
    </div>

    <!-- ========== 运维建议弹窗 ========== -->
    <div v-if="advice" class="modal-overlay" @click.self="advice = null">
      <div class="modal">
        <h3>🔧 运维建议</h3>
        <div class="advice-section"><b>故障现象:</b> {{ advice.phenomenon }}</div>
        <div class="advice-section"><b>根因诊断:</b> {{ advice.root_cause }}</div>
        <div class="advice-section"><b>处理方案:</b> {{ advice.action_plan }}</div>
        <div class="advice-section"><b>备件清单:</b> {{ advice.spare_parts }}</div>
        <div class="advice-section"><b>历史案例:</b> {{ advice.similar_cases }}</div>
        <button class="btn btn-primary" @click="createWorkOrder">生成工单</button>
        <button class="btn" @click="advice = null">关闭</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import { healthAPI, alertAPI, maintenanceAPI, authAPI } from '../api/request'

const router = useRouter()

// -------- 用户信息 --------
const user = reactive(JSON.parse(localStorage.getItem('user_info') || '{"role":"值长","username":"?"}'))

async function handleLogout() {
  try { await authAPI.logout() } catch (_) { /* ignore */ }
  localStorage.clear()
  router.push('/login')
}

// -------- 设备列表 --------
const devices = ref([])
const selectedId = ref(1)
const selectedDevice = ref(null)

async function loadDevices() {
  try {
    const res = await healthAPI.overview(1)
    devices.value = res.data
    selectedDevice.value = res.data[0]
  } catch (_) {
    devices.value = []
  }
}

function selectDevice(dev) {
  selectedId.value = dev.id
  selectedDevice.value = dev
  loadTrend()
}

// -------- 预警 --------
const alerts = ref([])
async function loadAlerts() {
  try {
    const res = await alertAPI.active(1)
    alerts.value = res.data
  } catch (_) { alerts.value = [] }
}

async function confirmAlert(id) {
  try {
    await alertAPI.confirm(id, { confirm_by: user.real_name || user.username, action: '已确认' })
    loadAlerts()
  } catch (_) { /* ignore */ }
}

const advice = ref(null)
async function showAdvice(id) {
  try {
    const res = await maintenanceAPI.advice(id)
    advice.value = res.data
  } catch (_) { /* ignore */ }
}

async function createWorkOrder() {
  if (!advice.value) return
  try {
    await maintenanceAPI.autoCreateWO(advice.value.alert_id)
    alert('工单已生成')
    advice.value = null
  } catch (_) { alert('工单生成失败') }
}

// -------- 焚烧炉剖面图 (ECharts) --------
const boilerChart = ref(null)
function drawBoiler() {
  if (!boilerChart.value) return
  const c = echarts.init(boilerChart.value)
  const devs = devices.value.length ? devices.value : [
    { name: '高过入口', health: 'orange' }, { name: '高过出口', health: 'yellow' },
    { name: '中温过热器', health: 'green' }, { name: '低温过热器', health: 'green' },
    { name: '省煤器', health: 'green' }
  ]
  const colorMap = { green: '#4caf50', yellow: '#ffeb3b', orange: '#ff9800', red: '#f44336' }
  c.setOption({
    backgroundColor: '#1a2a3a',
    tooltip: { trigger: 'item' },
    grid: { left: 80, right: 40, top: 10, bottom: 10 },
    xAxis: { type: 'value', min: 0, max: 10, show: false },
    yAxis: { type: 'value', min: 0, max: 14, show: false },
    series: [{
      type: 'bar',
      barWidth: '50%',
      label: { show: true, position: 'inside', fontSize: 11, color: '#fff' },
      data: devs.map((d, i) => ({
        value: [i + 2, 10],
        name: d.name,
        itemStyle: { color: colorMap[d.health] || '#4caf50' }
      }))
    }]
  })
  c.on('click', (p) => {
    if (p.dataIndex !== undefined && devices.value[p.dataIndex]) {
      selectDevice(devices.value[p.dataIndex])
    }
  })
}

// -------- 壁厚趋势图 --------
const trendChart = ref(null)
function drawTrend() {
  if (!trendChart.value) return
  const c = echarts.init(trendChart.value)
  const days = []; const wall = []; let v = 5.1
  for (let i = 0; i < 180; i++) { days.push(i + 1); wall.push(+(v - 0.35 / 365 * i).toFixed(2)) }
  c.setOption({
    backgroundColor: '#1a2a3a',
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: days, axisLabel: { color: '#78909c' } },
    yAxis: { type: 'value', name: 'mm', axisLabel: { color: '#78909c' } },
    series: [{
      type: 'line', data: wall, smooth: true,
      lineStyle: { color: '#ff9800', width: 2 }, symbol: 'none',
      markLine: { silent: true, lineStyle: { color: '#f44336', type: 'dotted' },
                  data: [{ yAxis: 3.0, label: { formatter: '3.0mm 危险', color: '#f44336' } }] }
    }]
  })
}

function loadTrend() { nextTick(drawTrend) }

// -------- 初始化 --------
onMounted(async () => {
  await loadDevices()
  await loadAlerts()
  nextTick(() => { drawBoiler(); drawTrend() })
})
</script>

<style scoped>
.dashboard { display: flex; flex-direction: column; height: 100vh; }
.topbar {
  display: flex; justify-content: space-between; align-items: center;
  padding: 10px 20px; background: #1a2a3a; border-bottom: 1px solid #2a3a4a;
}
.topbar h1 { font-size: 18px; color: #4fc3f7; }
.user-area { display: flex; align-items: center; gap: 12px; font-size: 13px; color: #78909c; }
.plant { color: #81c784; }
.btn-logout { padding: 4px 12px; border: 1px solid #546e7a; border-radius: 4px;
  background: transparent; color: #b0bec5; cursor: pointer; font-size: 12px; }
.layout { display: flex; flex: 1; overflow: hidden; }

/* 侧边栏 */
.sidebar { width: 200px; background: #1a2a3a; padding: 12px; overflow-y: auto; border-right: 1px solid #2a3a4a; }
.sidebar h3 { font-size: 13px; color: #78909c; margin-bottom: 10px; }
.device-item { padding: 8px; margin: 2px 0; border-radius: 4px; cursor: pointer;
  display: flex; align-items: center; gap: 8px; font-size: 12px; transition: background .2s; }
.device-item:hover { background: #253548; }
.device-item.active { background: #1e4a6b; border-left: 3px solid #4fc3f7; }
.dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.dot.green { background: #4caf50; } .dot.yellow { background: #ffeb3b; }
.dot.orange { background: #ff9800; animation: pulse 1.5s infinite; }
.dot.red { background: #f44336; animation: pulse .8s infinite; }
@keyframes pulse { 50% { opacity: .4; } }
.badge { margin-left: auto; font-size: 10px; background: #ff9800; color: #000; padding: 1px 5px; border-radius: 8px; }

/* 主区域 */
.main { flex: 1; padding: 16px; overflow-y: auto; display: flex; flex-direction: column; gap: 12px; }
.boiler-section { background: #1a2a3a; border-radius: 8px; padding: 12px; }
.boiler-section h3 { font-size: 14px; color: #4fc3f7; margin-bottom: 8px; }
.chart-box { width: 100%; height: 240px; }
.bottom-panels { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; flex: 1; }
.panel { background: #1a2a3a; border-radius: 8px; padding: 12px; }
.panel h3 { font-size: 13px; color: #4fc3f7; margin-bottom: 8px; }
.chart-box-small { width: 100%; height: 200px; }
.empty { color: #546e7a; font-size: 13px; padding: 20px; text-align: center; }

/* 预警卡片 */
.alert-card { padding: 10px; margin-bottom: 8px; border-radius: 6px;
  background: #253548; border-left: 4px solid #ff9800; }
.alert-card.red { border-left-color: #f44336; }
.a-head { display: flex; justify-content: space-between; font-size: 12px; color: #b0bec5; }
.a-reason { font-size: 12px; margin: 6px 0; line-height: 1.5; }
.a-loss { font-size: 12px; color: #ff9800; margin-bottom: 6px; }
.a-actions { display: flex; gap: 6px; }

/* 按钮 */
.btn { padding: 6px 14px; border: 1px solid #546e7a; border-radius: 4px;
  background: transparent; color: #b0bec5; cursor: pointer; font-size: 12px; }
.btn-primary { background: #1976d2; border-color: #1976d2; color: #fff; }
.btn-sm { padding: 4px 10px; font-size: 11px; }

/* 弹窗 */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.6);
  display: flex; align-items: center; justify-content: center; z-index: 999; }
.modal { background: #1a2a3a; border-radius: 10px; padding: 24px; width: 500px; max-width: 90vw; }
.modal h3 { font-size: 16px; color: #4fc3f7; margin-bottom: 14px; }
.advice-section { font-size: 13px; margin-bottom: 10px; line-height: 1.6; }
.modal .btn { margin-right: 8px; margin-top: 10px; }
</style>
