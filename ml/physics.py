"""
阿伦尼乌斯腐蚀物理 & 三级阈值判定 —— 全仓库唯一实现 (BIZ-001/BIZ-002)

训练数据生成(ml/simulate.py) / 推理(ml/inference.py, backend/services/inference_service.py) /
实时仿真(backend/services/realtime_sim.py) 统一从此处导入, 禁止再各自实现或硬编码。

纯函数, 不依赖 torch / 数据库 / 全局状态, 可独立单测 (CODE-001)。
"""
import json
from pathlib import Path

import numpy as np

R_GAS = 8.314  # 气体常数 (J/mol·K)

THRESHOLDS_PATH = Path(__file__).parent / "thresholds.json"
# 三级统计分位阈值 (BIZ-002: 95/99/99.9 分位替代 1x/2x 拍脑袋系数)
THRESHOLD_KEYS = ("mse_p95", "mse_p99", "mse_p999")


def arrhenius_rate(temp_k, hcl, h2s, A, Ea, m, n, R=R_GAS):
    """腐蚀速率 rate = A·exp(-Ea/(R·T))·[HCl]^m·[H2S]^n  (mm/年)

    temp_k: 开尔文温度; hcl/h2s: mg/m³ (下限截断为1, 避免0/负数取幂)
    标量与 numpy 数组均可 (向量化)。
    """
    hcl = np.clip(hcl, 1.0, None)
    h2s = np.clip(h2s, 1.0, None)
    return A * np.exp(-Ea / (R * np.asarray(temp_k, dtype=float))) * hcl ** m * h2s ** n


def corrosion_rate(temp_k, hcl, h2s, params, accel=1.0):
    """按管材参数对象计算腐蚀速率。

    params: ml.config.CorrosionParams (A 的单一来源 — BIZ-001)
    accel:  异常工况加速乘子 (×1正常 / ×30异常 / ×45危险, 见 ml.config.ANOMALY_ACCEL)
            —— 异常不是"另一套A值", 而是同一物理参数 × 工况乘子
    """
    return accel * arrhenius_rate(temp_k, hcl, h2s,
                                  params.A, params.Ea, params.m, params.n, params.R)


def load_thresholds(path=None) -> dict:
    """加载数据驱动三级阈值 (由 ml/calc_thresholds.py 统计生成)"""
    p = Path(path) if path else THRESHOLDS_PATH
    with open(p, encoding="utf-8") as f:
        t = json.load(f)
    missing = [k for k in THRESHOLD_KEYS if k not in t]
    if missing:
        raise KeyError(f"thresholds.json 缺少 {missing} — 请运行 ml/calc_thresholds.py 重算")
    return t


def classify_alert(mse, wall_pred, thresholds, min_wall_mm=3.0):
    """三级预警判定 —— 完全由统计分位驱动 (BIZ-002), 无手拍系数:

      red    壁厚 ≤ 1.3×最小允许壁厚 (物理红线), 或 MSE>99.9分位 (0.1%误报率)
      orange MSE>99分位   (1%误报率)
      yellow MSE>95分位   (5%误报率)
      green  其余

    物理腐蚀速率不参与等级门控 (推理侧速率基于基准A, 对异常加速不可观测,
    在0.25附近掷硬币会随机降级 — 见P0-5修复记录); 速率仍用于RUL/运维建议/展示。
    返回 (level, flags字典)
    """
    flags = {
        # fail-safe: 压线(=1.3×最小允许壁厚)即判危险, 报警系统宁严勿松
        "wall_danger": bool(wall_pred <= min_wall_mm * 1.3),
        "mse_yellow": bool(mse > thresholds["mse_p95"]),
        "mse_orange": bool(mse > thresholds["mse_p99"]),
        "mse_red": bool(mse > thresholds["mse_p999"]),
    }
    if flags["wall_danger"] or flags["mse_red"]:
        level = "red"
    elif flags["mse_orange"]:
        level = "orange"
    elif flags["mse_yellow"]:
        level = "yellow"
    else:
        level = "green"
    return level, flags


def anomaly_score(mse, thresholds):
    """异常得分 —— 分位锚定的分段线性映射, 与三级等级语义对齐:

      [0, p95]    → [0, 0.5)   正常带
      (p95, p999] → [0.5, 0.9) 预警带 (黄/橙)
      >p999       → [0.9, 1.0] 危险带 (红), 超出部分饱和到1.0
    """
    p95 = max(thresholds["mse_p95"], 1e-12)
    p999 = max(thresholds["mse_p999"], p95 + 1e-12)
    if mse <= p95:
        return 0.5 * mse / p95
    if mse <= p999:
        return 0.5 + 0.4 * (mse - p95) / (p999 - p95)
    return min(0.9 + 0.1 * (mse / p999 - 1.0), 1.0)
