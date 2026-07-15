"""
实时仿真引擎 —— 在内存中模拟焚烧炉DCS数据流
每次调用 advance(n_hours) 推进n小时, 返回最新的48h传感器窗口 + 壁厚趋势历史
"""
import numpy as np
from ml.config import MATERIAL_PARAMS, SIMULATION

_params = MATERIAL_PARAMS["T22"]
_state = {
    "hours": 0,          # 当前模拟小时数
    "wall_thickness": 6.0,  # 当前壁厚
    "history": [],       # [(hour, wall_thickness, hcl, temp, corrosion_rate), ...]
    "anomaly_active": False,
    "anomaly_start": 2880,  # 第120天(小时)
    "anomaly_spike": 2890,  # 突变点
}

def _gen_hcl(hour):
    """生成HCl浓度: 正常800-1200, 异常段1600-1800"""
    if _state["anomaly_spike"] <= hour < _state["anomaly_spike"] + 2:
        return np.random.uniform(1700, 1900)   # 2小时突变
    elif _state["anomaly_start"] <= hour < _state["anomaly_start"] + 336:  # 14天
        return np.random.uniform(1550, 1800)
    else:
        return 1000 + np.random.randn() * 80

def _gen_temp(hour):
    """生成炉温: 正常560-590, 异常段略降"""
    base = 575
    if _state["anomaly_spike"] <= hour < _state["anomaly_spike"] + 2:
        base = 555  # 突变时段炉温微降
    elif _state["anomaly_start"] <= hour < _state["anomaly_start"] + 336:
        base = 565
    return base + np.random.randn() * 8

def _corrosion_rate(hcl, temp_c):
    """阿伦尼乌斯方程"""
    p = _params
    tk = temp_c + 273.15
    return p.A * np.exp(-p.Ea / (p.R * tk)) * (max(hcl, 1) ** p.m) * (300 ** p.n)

def advance_to(target_hour):
    """推进仿真到目标小时，过程中生成所有数据"""
    while _state["hours"] < target_hour:
        h = _state["hours"]
        hcl = _gen_hcl(h)
        temp = _gen_temp(h)
        rate = _corrosion_rate(hcl, temp)
        _state["wall_thickness"] -= rate / (365 * 24)
        _state["history"].append({
            "hour": h, "wall": round(_state["wall_thickness"], 3),
            "hcl": round(hcl, 1), "temp": round(temp, 1),
            "rate": round(rate, 4)
        })
        _state["hours"] += 1


def generate_window(hours_back=48):
    """返回最近48小时传感器窗口 + 趋势历史"""
    # 确保有足够历史
    if _state["hours"] < hours_back:
        advance_to(hours_back)

    # 取最后48h
    recent = _state["history"][-hours_back:]
    # 构建15参数传感器窗口 (索引对应训练时的15个字段)
    window = np.zeros((hours_back, 15), dtype=np.float32)
    for i, r in enumerate(recent):
        window[i, 0] = r["temp"]          # 炉膛温度
        window[i, 1] = r["hcl"]           # HCl浓度
        window[i, 2] = r["hcl"] * 0.2     # SO2 (近似)
        window[i, 3] = 50 + np.random.randn() * 5    # CO
        window[i, 4] = 8 + np.random.randn() * 0.3   # O2
        window[i, 5] = 20 + np.random.randn() * 2    # 颗粒物
        window[i, 6] = r["temp"] - 90            # 壁温
        window[i, 7] = r["temp"] - 110
        window[i, 8] = r["temp"] - 140
        window[i, 9] = r["temp"] - 15            # 烟温
        window[i, 10] = r["temp"] - 30
        window[i, 11] = r["temp"] - 60
        window[i, 12] = 40 + np.random.randn()  # 蒸汽流量
        window[i, 13] = 4.0 + np.random.randn() * 0.05
        window[i, 14] = 400 + np.random.randn()

    return window, _state["history"]


def advance_hours(n=1):
    """推进n小时, 返回新的48h窗口 + 趋势数据"""
    _state["hours"] += n
    return generate_window()


def current_anomaly_info():
    """当前是否处于异常段"""
    h = _state["hours"]
    return {
        "in_anomaly": _state["anomaly_start"] <= h,
        "hours_since_start": h - _state["anomaly_start"] if h >= _state["anomaly_start"] else 0,
    }
