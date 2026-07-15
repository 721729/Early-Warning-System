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
    <div class="card" style="margin-top:12px"><h3>❓ 为什么叫"物理约束"？其实是化学动力学</h3>
      <p style="font-size:13px;color:#b0bec5;line-height:1.8">
        阿伦尼乌斯方程描述的是<b>化学反应速率</b>——HCl 和 H₂S 在高温下腐蚀管壁，本质是化学过程。<br/>
        学术上这类方法统称 "Physics-Informed Neural Networks (PINN)"，"Physics" 在此泛指"科学定律约束"而非狭义物理。<br/>
        本方案的约束项准确说是<b>"化学动力学腐蚀方程约束"</b>——让 AI 的预测不得违背阿伦尼乌斯定律。
      </p>
    </div>
    <div class="card" style="margin-top:12px"><h3>📊 模型输入：15参数多传感器数据</h3>
      <p style="font-size:13px;color:#b0bec5;line-height:1.8">
        本方案使用<b>多参数</b>传感器数据而非单一参数（如只看HCl浓度）：<br/>
        炉膛温度、HCl浓度、SO₂浓度、CO浓度、O₂含量、颗粒物浓度、<br/>
        高/中/低过热器壁温×3、高/中/低过热器烟温×3、主蒸汽流量/压力/温度<br/>
        AI学的是这15个参数之间的<b>关联模式</b>——单个参数正常但组合异常时，阈值报警器看不出来，AI能。
      </p>
    </div>
    <div class="card" style="margin-top:12px"><h3>⚠️ 模型C漏报率偏高的原因</h3>
      <p style="font-size:13px;color:#b0bec5;line-height:1.8">
        物理约束在损失函数中作为正则项（λ=0.1），作用是<b>压制误报</b>——效果显著（6.0%→2.8%）。<br/>
        但代价是：部分真实异常的信号特征不够强（HCl升幅小、腐蚀加速不明显），<br/>
        被物理约束判定为"仍符合腐蚀规律"而未被检出。这是精确率与召回率的标准权衡。<br/>
        <b>解决方案</b>：Pilot 阶段做 λ 参数扫描（0.01 / 0.05 / 0.1 / 0.5 / 1.0），<br/>
        在误报率和漏报率之间找到最优平衡点。当前 λ=0.1 为起始实验值。
      </p>
    </div>
    <div class="card" style="margin-top:12px"><h3>⚗️ 阿伦尼乌斯参数说明（当前未校准）</h3>
      <p style="font-size:13px;color:#b0bec5;line-height:1.8">
        当前使用的腐蚀参数（A=55, Ea=85000, m=0.65, n=0.35）为 T22 管材在焚烧炉烟气环境下的<b>文献参考值</b>，<br/>
        尚未在真实焚烧厂的检修壁厚数据上校准。腐蚀误差 24% 和 RUL 偏差 ~1214 天即来源于此。<br/>
        <b>Pilot 校准方案</b>：取真实焚烧厂 3~5 次换管记录的"运行时长—HCl浓度—壁厚减少量"数据点，<br/>
        反向拟合阿伦尼乌斯方程中的 A、Ea、m 三个参数。校准后腐蚀误差预计可降至 8% 以内。
      </p>
    </div>
    <div class="card" style="margin-top:12px"><h3>🔄 从仿真到真实：实时监测数据路径</h3>
      <p style="font-size:13px;color:#b0bec5;line-height:1.8">
        <b>当前 Demo</b>：仿真数据生成器用阿伦尼乌斯方程+随机噪声模拟15个传感器，每3秒刷新。<br/>
        <b>生产环境</b>：DCS → OPC UA协议（加密证书认证）→ 单向隔离网闸（只读不控）→<br/>
          边缘工控机加载训练好的PatchTST权重 → 读取实时DCS数据流 → 本地推理 →<br/>
          输出腐蚀速率/异常得分/预警等级 → 前端每3秒轮询或WebSocket推送更新。<br/>
        当前页面展示的传感器数据均为<b>仿真数据</b>，标注为 "LIVE" 仅示范实时性——非真实焚烧厂DCS。
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
  { name: 'F1分数（精确率与召回率的调和平均，0~1越高越好）', b: '0.863', c: '0.855', effect: '持平' },
  { name: '误报率（正常工况下错误报警的比例）', b: '6.0%', c: '2.8%', effect: '↓53% ── 砍半' },
  { name: '漏报率（真实异常未被检出的比例）', b: '6.2%', c: '17.2%', effect: '↑11pp ── 代价，λ可调' },
  { name: '准确率（整体判断正确的比例）', b: '93.9%', c: '94.2%', effect: '+0.3pp' },
  { name: '化学一致性（预测不违反阿伦尼乌斯腐蚀定律）', b: '100%', c: '100%', effect: '持平' },
])
// 注：B=纯AI模型(无化学约束) C=本方案融合模型(化学+AI) ——消融实验验证化学约束效果
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
