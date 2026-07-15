#!/usr/bin/env python3
"""
仿真数据生成器 —— 阿伦尼乌斯方程正向模拟焚烧炉6个月运行数据
16字段, 分钟级采样, 含正常工况+异常工况+传感器噪声
输出: simulation_data.csv
"""
import numpy as np
import pandas as pd
from pathlib import Path
from config import SIMULATION as S, MATERIAL_PARAMS

np.random.seed(42)

def corrosion_rate(hcl_conc, h2s_conc, flue_temp_k, params):
    """阿伦尼乌斯方程: rate = A × exp(-Ea/(R×T)) × [HCl]^m × [H₂S]^n"""
    hcl = np.clip(hcl_conc, 1, None)
    h2s = np.clip(h2s_conc, 1, None)
    return (params.A
            * np.exp(-params.Ea / (params.R * flue_temp_k))
            * (hcl ** params.m)
            * (h2s ** params.n))


def generate_ar1(n, phi=0.995, sigma=20, init=1000):
    """AR(1)过程生成自相关的HCl浓度序列(比纯高斯噪声更像真实工况)"""
    x = np.zeros(n)
    x[0] = init
    for t in range(1, n):
        x[t] = phi * x[t-1] + (1-phi) * init + np.random.normal(0, sigma)
    return x


def run():
    total_steps = S["duration_days"] * 24 * 60  # 分钟数
    params = MATERIAL_PARAMS[S["material"]]

    # ---- 时间轴 ----
    timestamps = pd.date_range("2025-01-01", periods=total_steps, freq="min")
    days = np.arange(total_steps) / (24 * 60)

    # ---- HCl浓度 (AR1) ----
    hcl = np.clip(generate_ar1(total_steps, phi=0.995, sigma=20,
                                init=np.mean(S["hcl_normal_range"])), 100, 3000)
    h2s = np.clip(generate_ar1(total_steps, phi=0.997, sigma=8, init=300), 50, 600)

    # ---- 温度 (AR1 + 压限) ----
    flue_temp = generate_ar1(total_steps, phi=0.999, sigma=2,
                             init=np.mean(S["flue_temp_range"]))
    flue_temp = np.clip(flue_temp, *S["flue_temp_range"])

    # 壁温比烟温低约80-130°C
    wall_temp = flue_temp - np.random.uniform(80, 130, total_steps)

    # 各段过热器温度(存在纵向温差)
    sh1_f = flue_temp + np.random.normal(0, 5, total_steps)
    sh2_f = flue_temp - np.random.uniform(20, 40, total_steps)
    sh3_f = flue_temp - np.random.uniform(60, 90, total_steps)
    sh1_w = wall_temp + np.random.normal(0, 3, total_steps)
    sh2_w = wall_temp - np.random.uniform(15, 30, total_steps)
    sh3_w = wall_temp - np.random.uniform(45, 70, total_steps)

    # ---- 腐蚀速率 & 壁厚衰减 ----
    flue_temp_k = flue_temp + 273.15
    rates = corrosion_rate(hcl, h2s, flue_temp_k, params)
    # 累积壁厚减少量 (mm)
    wall_loss = np.cumsum(rates / (365 * 24 * 60))  # 年速率→分钟
    wall_thickness = S["original_wall_thickness_mm"] - wall_loss

    # 超声探头每日采集一次(其余时间为NaN)
    ultra_daily = np.full(total_steps, np.nan)
    daily_idx = np.arange(0, total_steps, 24 * 60)
    ultra_daily[daily_idx] = wall_thickness[daily_idx]

    # ---- 其他参数 ----
    so2 = generate_ar1(total_steps, phi=0.996, sigma=10, init=200)
    co = generate_ar1(total_steps, phi=0.995, sigma=5, init=50)
    o2 = generate_ar1(total_steps, phi=0.998, sigma=0.3, init=8)
    o2 = np.clip(o2, 4, 12)
    particle_conc = generate_ar1(total_steps, phi=0.997, sigma=2, init=20)
    particle_conc = np.clip(particle_conc, 5, 30)

    main_steam_flow = generate_ar1(total_steps, phi=0.999, sigma=0.5, init=40)
    main_steam_flow = np.clip(main_steam_flow, 35, 45)
    main_steam_press = generate_ar1(total_steps, phi=0.999, sigma=0.05, init=4.0)
    main_steam_temp = generate_ar1(total_steps, phi=0.999, sigma=1.5, init=400)

    # ---- 异常注入: 第120天突然投入高氯垃圾 → HCl在2h内从1000飙到1800 + 炉温波动 + O₂变化 ----
    anomaly_start = S["anomaly_start_day"] * 24 * 60
    anomaly_spike = 120  # 2小时突变
    spike_mid = anomaly_start + 60
    hcl[spike_mid:spike_mid+anomaly_spike] = np.random.uniform(*S["hcl_anomaly_range"], anomaly_spike)
    flue_temp[spike_mid:spike_mid+anomaly_spike] -= 10  # 燃烧不稳炉温微降
    o2[spike_mid:spike_mid+anomaly_spike] += 1.5           # O₂升高
    # 持续2周高HCl期
    anomaly_end = anomaly_start + S["anomaly_duration_days"] * 24 * 60
    hcl[spike_mid+anomaly_spike:anomaly_end] = np.random.uniform(*S["hcl_anomaly_range"],
        anomaly_end - spike_mid - anomaly_spike)

    # ---- 加噪声 (3%白噪声) ----
    def add_noise(arr):
        return arr * (1 + np.random.normal(0, S["noise_std_pct"], len(arr)))

    data = pd.DataFrame({
        "timestamp": timestamps,
        "炉膛温度": add_noise(flue_temp),
        "HCl浓度": add_noise(hcl),
        "SO2浓度": add_noise(so2),
        "CO浓度": add_noise(co),
        "O2含量": add_noise(o2),
        "颗粒物浓度": add_noise(particle_conc),
        "高温过热器壁温": add_noise(sh1_w),
        "中温过热器壁温": add_noise(sh2_w),
        "低温过热器壁温": add_noise(sh3_w),
        "高温过热器烟温": add_noise(sh1_f),
        "中温过热器烟温": add_noise(sh2_f),
        "低温过热器烟温": add_noise(sh3_f),
        "主蒸汽流量": add_noise(main_steam_flow),
        "主蒸汽压力": add_noise(main_steam_press),
        "主蒸汽温度": add_noise(main_steam_temp),
        "管壁超声厚度": ultra_daily,
        "实际壁厚": wall_thickness,    # ground truth (无噪声)
        "实际腐蚀速率": rates,          # ground truth
        "标签": 0,                      # 正常=0
    })
    # 标注异常段
    data.loc[anomaly_start:anomaly_end, "标签"] = 1

    out = Path(__file__).parent / "simulation_data.csv"
    data.to_csv(out, index=False)
    print(f"[OK] {len(data)} rows → {out}")
    print(f"  壁厚衰减: {wall_thickness[0]:.2f} → {wall_thickness[-1]:.2f} mm")
    print(f"  异常时段: 第{S['anomaly_start_day']}~{S['anomaly_start_day']+S['anomaly_duration_days']}天")
    print(f"  正常HCl: {S['hcl_normal_range']} mg/m³ → 异常HCl: {S['hcl_anomaly_range']} mg/m³")


if __name__ == "__main__":
    run()
