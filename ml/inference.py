#!/usr/bin/env python3
"""
推理服务 —— 加载训练好的 GitHub 原版 PatchTST 权重
提供腐蚀预测 & 异常检测 & RUL 估算
"""
import numpy as np
import torch
from pathlib import Path
import sys

# GitHub 原版 PatchTST
_PATCHTST_DIR = Path(__file__).parent / "PatchTST" / "PatchTST_supervised"
sys.path.insert(0, str(_PATCHTST_DIR))
from models.PatchTST import Model as PatchTST_Orig
from types import SimpleNamespace

from config import MATERIAL_PARAMS, SIMULATION

_DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
_MODEL = None
_NORM = None
_THRESHOLD = 0.002  # 训练集MSE 95分位


def make_config(seq_len=48):
    return SimpleNamespace(
        enc_in=15, seq_len=seq_len, pred_len=seq_len,
        e_layers=3, n_heads=4, d_model=128, d_ff=256,
        dropout=0.1, fc_dropout=0.1, head_dropout=0.0,
        patch_len=8, stride=4, padding_patch='end',
        individual=False,
        revin=False, affine=False, subtract_last=False,
        decomposition=False, kernel_size=25,
    )


def load_model(model_path=None, norm_path=None, threshold=0.007):
    """FastAPI 启动时调用一次, 加载模型权重和标准化参数"""
    global _MODEL, _NORM, _THRESHOLD
    root = Path(__file__).parent

    model_path = model_path or (root / "model_c_fusion.pth")
    norm_path = norm_path or (root / "norm_params.npz")

    _NORM = np.load(norm_path)
    _THRESHOLD = threshold

    config = make_config()
    _MODEL = PatchTST_Orig(config).to(_DEVICE)
    _MODEL.load_state_dict(torch.load(model_path, map_location=_DEVICE, weights_only=True))
    _MODEL.eval()
    return True


def predict(window_48h: np.ndarray) -> dict:
    """
    输入: (48, 15) — 48 小时传感器数据 (原始值, 未标准化)
    输出: {
        corrosion_rate:   腐蚀速率预测值 (mm/年)
        wall_thickness_pred: 壁厚预测值 (mm)
        reconstruction_error: AI重建误差
        anomaly_score:    异常得分 (0~1)
        alert_level:      green / yellow / orange / red
        rul_days:         剩余寿命预测 (天)
    }
    """
    global _MODEL, _NORM, _THRESHOLD
    if _MODEL is None:
        load_model()

    mean = _NORM["mean"]     # (1, 1, 15)
    std = _NORM["std"] + 1e-8

    # 标准化
    w_norm = (window_48h - mean) / std
    x_tensor = torch.from_numpy(w_norm).float().to(_DEVICE)

    with torch.no_grad():
        recon = _MODEL(x_tensor)
    mse = float(torch.mean((recon - x_tensor) ** 2))

    # ---- 物理模型: 阿伦尼乌斯方程 ----
    params = MATERIAL_PARAMS['T22']
    raw = window_48h[-1]           # 窗口最后时间步的原始值
    hcl_raw = max(float(raw[1]), 1)
    temp_raw = float(raw[0])
    temp_k = temp_raw + 273.15

    rate = (params.A
            * np.exp(-params.Ea / (params.R * temp_k))
            * (hcl_raw ** params.m)
            * (300 ** params.n))

    # ---- 壁厚预测 & RUL ----
    hours = window_48h.shape[0]
    wall_pred = SIMULATION['original_wall_thickness_mm'] - rate * hours / (365 * 24)
    remaining = max(wall_pred - SIMULATION['min_allowable_thickness_mm'], 0)
    rul_days = remaining / max(rate, 1e-8) * 365 if rate > 1e-8 else 9999

    # ---- 联合判定 (AI MSE为主，腐蚀速率为辅) ----
    threshold = _THRESHOLD
    anomaly_score = min(mse / max(0.0015, 1e-8), 1.0)
    mse_high = mse > 0.0015
    mse_danger = mse > 0.0025
    rate_high = rate > 0.30
    wall_danger = wall_pred < SIMULATION['min_allowable_thickness_mm'] * 1.3

    if wall_danger:                      alert_level = "red"
    elif mse_danger and rate_high:        alert_level = "orange"
    elif mse_high:                        alert_level = "yellow"
    else:                                 alert_level = "green"

    return {
        "corrosion_rate": round(rate, 4),
        "wall_thickness_pred": round(wall_pred, 2),
        "reconstruction_error": round(mse, 6),
        "anomaly_score": round(anomaly_score, 4),
        "alert_level": alert_level,
        "rul_days": round(rul_days, 1),
        "hcl_conc": round(hcl_raw, 1),
        "flue_temp": round(temp_raw, 1),
    }
