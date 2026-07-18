#!/usr/bin/env python3
"""
三级分位阈值重算脚本 (BIZ-002; 硬约束: 物理参数A/乘子变更后必须重跑)

统计口径: 实时仿真(backend/services/realtime_sim.Simulation)生成的传感器窗口
经训练好的 PatchTST(model_c_fusion.pth) 重建, 取【正常段】MSE 的 95/99/99.9 分位。
三级预警以此为准: yellow>p95 / orange>p99且速率高 / red=壁厚危险 或 >p99.9且速率高。

用法(仓库根目录):  .venv/bin/python ml/calc_thresholds.py
结果写回 ml/thresholds.json (含统计时的物理口径, 便于审计追溯)。
"""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import torch

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))                                               # backend.* / ml.*
sys.path.insert(0, str(_ROOT / "ml" / "PatchTST" / "PatchTST_supervised"))   # models.PatchTST

from models.PatchTST import Model as PatchTST_Orig  # noqa: E402

from backend.services.realtime_sim import Simulation  # noqa: E402
from ml.config import ANOMALY_ACCEL, MATERIAL_PARAMS  # noqa: E402

SEED = 42
ML_DIR = _ROOT / "ml"
OUT = ML_DIR / "thresholds.json"

# 学术诚实性声明 —— 项目亮点, 任何重算不得删除
_DISCLAIMER = ("仿真数据用阿伦尼乌斯方程生成，AI用同一方程约束——这是验证架构可行性，"
               "不是证明模型准确性。真实场景需Pilot阶段用检修壁厚数据重新校准。")


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


def load_model():
    model = PatchTST_Orig(make_config()).to("cpu")
    model.load_state_dict(torch.load(ML_DIR / "model_c_fusion.pth",
                                     map_location="cpu", weights_only=True))
    model.eval()
    norm = np.load(ML_DIR / "norm_params.npz")
    return model, norm


def collect_mses(model, norm, sim, hours_list):
    mean = norm["mean"]
    std = norm["std"] + 1e-8
    mses = []
    for h in hours_list:
        sim.advance_to(h)
        w, _ = sim.window(48)
        x = torch.from_numpy((w - mean) / std).float()
        with torch.no_grad():
            recon = model(x)
        mses.append(float(torch.mean((recon - x) ** 2)))
    return mses


def main():
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    model, norm = load_model()

    sim = Simulation()
    # 正常段: 48h起每12h一个滑窗, 到异常开始(a_start=2880h)为止
    normal_hours = list(range(48, sim.a_start + 1, 12))
    normal_mses = collect_mses(model, norm, sim, normal_hours)
    # 异常段(accel=×30): 窗口完全落入异常期后取样, 仅用于报告分离比
    anomaly_hours = list(range(sim.a_start + 48, sim.a_start + 336 + 1, 12))
    anomaly_mses = collect_mses(model, norm, sim, anomaly_hours)

    arr = np.array(normal_mses)
    p95, p99, p999 = (float(np.percentile(arr, q)) for q in (95, 99, 99.9))

    out = {
        "mse_p95": round(p95, 6),
        "mse_p99": round(p99, 6),
        "mse_p999": round(p999, 6),
        "mse_normal_mean": round(float(arr.mean()), 6),
        "mse_anomaly_mean": round(float(np.mean(anomaly_mses)), 6),
        "separation_ratio": round(float(np.mean(anomaly_mses) / arr.mean()), 2),
        "n_normal": len(normal_mses),
        "n_anomaly": len(anomaly_mses),
        "physics": {  # 统计时的物理口径 —— A或乘子变更必须重跑本脚本 (硬约束§4)
            "material": "T22",
            "A": MATERIAL_PARAMS["T22"].A,
            "Ea": MATERIAL_PARAMS["T22"].Ea,
            "anomaly_accel": ANOMALY_ACCEL,
        },
        "generated_by": f"ml/calc_thresholds.py (seed={SEED})",
        "note": ("realtime仿真正常段MSE分位 —— 三级预警阈值以此为准: "
                 "yellow>p95 / orange>p99且速率高 / red=壁厚危险或>p99.9且速率高"),
        "_disclaimer": _DISCLAIMER,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[OK] 阈值已写入 {OUT}")
    for k in ("mse_p95", "mse_p99", "mse_p999", "mse_normal_mean",
              "mse_anomaly_mean", "separation_ratio", "n_normal", "n_anomaly"):
        print(f"  {k}: {out[k]}")


if __name__ == "__main__":
    main()
