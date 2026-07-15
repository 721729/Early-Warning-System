"""
推理服务 —— 加载 GitHub 原版 PatchTST 权重，提供真实推理
基于: github.com/yuqinie98/PatchTST (MIT License)
"""
import numpy as np
import torch
import sys
from pathlib import Path

_ML_DIR = Path(__file__).parent.parent.parent / "ml"
_PATCHTST_DIR = _ML_DIR / "PatchTST" / "PatchTST_supervised"
sys.path.insert(0, str(_PATCHTST_DIR))
from models.PatchTST import Model as PatchTST_Orig
from types import SimpleNamespace

from ml.config import MATERIAL_PARAMS, SIMULATION

_DEVICE = torch.device("cpu")
_MODEL = None
_NORM = None
_THRESHOLD = 0.002  # 训练集MSE 95分位，高于此值=异常


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


def load_model(model_path=None):
    """FastAPI 启动时调用一次"""
    global _MODEL, _NORM
    root = _ML_DIR
    model_path = model_path or (root / "model_c_fusion.pth")
    norm_path = root / "norm_params.npz"

    _NORM = np.load(norm_path)
    config = make_config()
    _MODEL = PatchTST_Orig(config).to(_DEVICE)
    _MODEL.load_state_dict(torch.load(model_path, map_location=_DEVICE, weights_only=True))
    _MODEL.eval()
    return True


def predict(window_48h: np.ndarray) -> dict:
    """
    输入: (48, 15) 原始传感器数据
    输出: 腐蚀速率、壁厚预测、异常得分、预警等级、RUL
    """
    if _MODEL is None:
        load_model()

    mean = _NORM["mean"]; std = _NORM["std"] + 1e-8
    w_norm = (window_48h - mean) / std
    x_tensor = torch.from_numpy(w_norm).float().to(_DEVICE)

    with torch.no_grad():
        recon = _MODEL(x_tensor)
    mse = float(torch.mean((recon - x_tensor) ** 2))

    params = MATERIAL_PARAMS['T22']
    raw = window_48h[-1]
    hcl_raw = max(float(raw[1]), 1)
    temp_raw = float(raw[0])
    temp_k = temp_raw + 273.15
    rate = (params.A * np.exp(-params.Ea / (params.R * temp_k))
            * (hcl_raw ** params.m) * (300 ** params.n))

    wall_pred = SIMULATION['original_wall_thickness_mm'] - rate * 48 / (365 * 24)
    remaining = max(wall_pred - SIMULATION['min_allowable_thickness_mm'], 0)
    rul_days = remaining / max(rate, 1e-8) * 365 if rate > 1e-8 else 9999

    # 判定阈值 (与异常得分归一化共用)
    MSE_NORMAL = 0.00025
    mse_high = mse > MSE_NORMAL
    mse_danger = mse > MSE_NORMAL * 2
    rate_high = rate > 0.25
    wall_danger = wall_pred < SIMULATION['min_allowable_thickness_mm'] * 1.3

    if wall_danger:                       alert_level = "red"
    elif mse_danger and rate_high:         alert_level = "orange"
    elif mse_high:                         alert_level = "yellow"
    else:                                  alert_level = "green"

    # 异常得分: 基于相同阈值, 1.0=严重异常
    score = min(mse / max(MSE_NORMAL * 2, 1e-8), 1.0)

    return {
        "corrosion_rate": round(rate, 4),
        "wall_thickness_pred": round(wall_pred, 2),
        "reconstruction_error": round(mse, 6),
        "anomaly_score": round(score, 4),
        "alert_level": alert_level,
        "rul_days": round(rul_days, 1),
        "hcl_conc": round(hcl_raw, 1),
        "flue_temp": round(temp_raw, 1),
    }
