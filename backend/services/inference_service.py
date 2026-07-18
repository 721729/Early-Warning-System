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

from ml.config import DEFAULT_H2S_MG_M3, MATERIAL_PARAMS, SIMULATION
from ml.physics import anomaly_score, classify_alert, corrosion_rate, load_thresholds

_DEVICE = torch.device("cpu")
_MODEL = None
_NORM = None
_THRESHOLDS = None  # 启动时从 ml/thresholds.json 加载三级分位阈值 (BIZ-002: 单一来源, 无硬编码回退)


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
    """FastAPI 启动时调用一次；阈值文件缺失/缺键直接抛错 (由调用方降级处理), 不再静默用默认值"""
    global _MODEL, _NORM, _THRESHOLDS
    root = _ML_DIR
    model_path = model_path or (root / "model_c_fusion.pth")
    norm_path = root / "norm_params.npz"

    _NORM = np.load(norm_path)
    config = make_config()
    _MODEL = PatchTST_Orig(config).to(_DEVICE)
    _MODEL.load_state_dict(torch.load(model_path, map_location=_DEVICE, weights_only=True))
    _MODEL.eval()

    # 三级统计分位阈值 (ml/calc_thresholds.py 重算生成)
    _THRESHOLDS = load_thresholds(root / "thresholds.json")
    print(f"[AI] 三级阈值已加载: p95={_THRESHOLDS['mse_p95']:.6f} "
          f"p99={_THRESHOLDS['mse_p99']:.6f} p999={_THRESHOLDS['mse_p999']:.6f} "
          f"(分离比{_THRESHOLDS.get('separation_ratio', '?')}x)")
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
    # 统一物理实现 (ml/physics.py); H2S 名义浓度与训练数据均值一致
    rate = float(corrosion_rate(temp_k, hcl_raw, DEFAULT_H2S_MG_M3, params))

    wall_pred = SIMULATION['original_wall_thickness_mm'] - rate * 48 / (365 * 24)
    remaining = max(wall_pred - SIMULATION['min_allowable_thickness_mm'], 0)
    rul_days = remaining / max(rate, 1e-8) * 365 if rate > 1e-8 else 9999

    # 三级分位判定 (BIZ-002): yellow>p95 / orange>p99 / red=壁厚危险或>p99.9 — 纯统计分位驱动
    alert_level, _flags = classify_alert(
        mse, wall_pred, _THRESHOLDS,
        min_wall_mm=SIMULATION['min_allowable_thickness_mm'])

    # 异常得分归一化: 1.0 = MSE达到99.9分位(red档)
    score = anomaly_score(mse, _THRESHOLDS)

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
