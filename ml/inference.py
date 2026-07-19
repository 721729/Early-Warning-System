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

from config import DEFAULT_H2S_MG_M3, MATERIAL_PARAMS, SIMULATION
from physics import anomaly_score, calculate_rul, classify_alert, corrosion_rate, load_thresholds

_DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
_MODEL = None
_NORM = None
_THRESHOLDS = None  # 从 ml/thresholds.json 加载三级分位阈值 (BIZ-002: 单一来源, 删除硬编码_THRESHOLD)


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


def load_model(model_path=None, norm_path=None, thresholds_path=None):
    """启动时调用一次, 加载模型权重/标准化参数/三级分位阈值"""
    global _MODEL, _NORM, _THRESHOLDS
    root = Path(__file__).parent

    model_path = model_path or (root / "model_c_fusion.pth")
    norm_path = norm_path or (root / "norm_params.npz")

    _NORM = np.load(norm_path)
    _THRESHOLDS = load_thresholds(thresholds_path or (root / "thresholds.json"))

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
    global _MODEL, _NORM, _THRESHOLDS
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

    # ---- 物理模型: 阿伦尼乌斯方程 (统一实现 ml/physics.py) ----
    params = MATERIAL_PARAMS['T22']
    raw = window_48h[-1]           # 窗口最后时间步的原始值
    hcl_raw = max(float(raw[1]), 1)
    temp_raw = float(raw[0])
    temp_k = temp_raw + 273.15

    rate = float(corrosion_rate(temp_k, hcl_raw, DEFAULT_H2S_MG_M3, params))

    # ---- 壁厚预测 & RUL ----
    hours = window_48h.shape[0]
    wall_pred = SIMULATION['original_wall_thickness_mm'] - rate * hours / (365 * 24)
    rul = calculate_rul(wall_pred, rate, SIMULATION['min_allowable_thickness_mm'])

    # ---- 联合判定: 三级分位阈值 (BIZ-002, 与 backend/services/inference_service.py 同源) ----
    alert_level, _flags = classify_alert(
        mse, wall_pred, _THRESHOLDS,
        min_wall_mm=SIMULATION['min_allowable_thickness_mm'])
    score = anomaly_score(mse, _THRESHOLDS)

    return {
        "corrosion_rate": round(rate, 4),
        "wall_thickness_pred": round(wall_pred, 2),
        "reconstruction_error": round(mse, 6),
        "anomaly_score": round(score, 4),
        "alert_level": alert_level,
        "rul_days": rul["rul_days"],
        "rul_low_days": rul["rul_low_days"],
        "rul_high_days": rul["rul_high_days"],
        "hcl_conc": round(hcl_raw, 1),
        "flue_temp": round(temp_raw, 1),
    }
