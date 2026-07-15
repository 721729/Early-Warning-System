/**
 * 仿真数据生成器 —— Demo阶段模拟实时DCS数据流
 * 阿伦尼乌斯方程驱动，每3秒更新一次
 */
let _timer = null
let _wallThickness = 5.98  // 起始壁厚
const HCl_NORMAL = [800, 1200]
const HCl_ANOMALY = [1600, 1800]

export function startSimulation(callback) {
  let tick = 0
  _timer = setInterval(() => {
    tick++
    const isAnomaly = tick > 600 && tick < 700  // 模拟异常时段

    const hcl = isAnomaly
      ? Math.random() * (HCl_ANOMALY[1] - HCl_ANOMALY[0]) + HCl_ANOMALY[0]
      : Math.random() * (HCl_NORMAL[1] - HCl_NORMAL[0]) + HCl_NORMAL[0]
    const temp = 560 + Math.random() * 30
    // 阿伦尼乌斯腐蚀速率
    const tempK = temp + 273.15
    const rate = 55.0 * Math.exp(-85000 / (8.314 * tempK)) * Math.pow(hcl, 0.65) * Math.pow(300, 0.35)
    _wallThickness -= rate / (365 * 24 * 3600) * 3  // 3秒衰减

    const data = {
      timestamp: new Date().toISOString(),
      furnace_temp: +(temp + (Math.random() - 0.5) * 5).toFixed(1),
      hcl_conc: +hcl.toFixed(1),
      so2_conc: +(200 + Math.random() * 30).toFixed(1),
      co_conc: +(50 + Math.random() * 10).toFixed(1),
      o2_conc: +(8 + (Math.random() - 0.5) * 1).toFixed(1),
      particle_conc: +(20 + (Math.random() - 0.5) * 4).toFixed(1),
      sh1_wall_temp: +(480 + (Math.random() - 0.5) * 5).toFixed(1),
      sh2_wall_temp: +(440 + (Math.random() - 0.5) * 5).toFixed(1),
      sh3_wall_temp: +(400 + (Math.random() - 0.5) * 5).toFixed(1),
      main_steam_flow: +(40 + (Math.random() - 0.5) * 2).toFixed(1),
      main_steam_press: +(4.0 + (Math.random() - 0.5) * 0.1).toFixed(2),
      main_steam_temp: +(400 + (Math.random() - 0.5) * 5).toFixed(1),
      wall_thickness: +_wallThickness.toFixed(3),
      corrosion_rate: +rate.toFixed(4),
      ai_anomaly_score: isAnomaly ? +(0.82 + Math.random() * 0.16).toFixed(4) : +(Math.random() * 0.1).toFixed(4),
      ai_alert: isAnomaly ? 'orange' : 'green',
      rul_days: +((_wallThickness - 3.0) / rate * 365).toFixed(0),
    }
    callback(data)
  }, 3000)
  return () => clearInterval(_timer)
}

export function stopSimulation() {
  if (_timer) { clearInterval(_timer); _timer = null }
}
