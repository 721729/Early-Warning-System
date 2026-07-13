"""
腐蚀参数配置 & 模型超参数
参考: 补充材料二-数据分析样本, 补充材料一-研究笔记
"""
from dataclasses import dataclass
from typing import Dict

# ============================================================
# 阿伦尼乌斯腐蚀方程参数 (Arrhenius: rate = A * exp(-Ea/(R*T)) * [HCl]^m * [H2S]^n)
# T22管材在垃圾焚烧炉烟气环境下的参考值（需Pilot阶段用实测壁厚校准）
# ============================================================
@dataclass
class CorrosionParams:
    A: float = 2.5e6         # 频率因子 (mm/年)
    Ea: float = 85000        # 活化能 (J/mol)
    R: float = 8.314         # 气体常数 (J/mol·K)
    m: float = 0.65          # HCl浓度指数
    n: float = 0.35          # H2S浓度指数
    T_ref: float = 823.15    # 参考温度 550°C → Kelvin


# 管材参数
MATERIAL_PARAMS: Dict[str, CorrosionParams] = {
    "T22": CorrosionParams(A=55.0, Ea=85000, m=0.65, n=0.35),
    "TP347H": CorrosionParams(A=42.0, Ea=92000, m=0.55, n=0.30),
}

# ============================================================
# 仿真数据参数
# ============================================================
SIMULATION = {
    "duration_days": 180,              # 模拟6个月
    "interval_minutes": 1,             # 1分钟采样
    "original_wall_thickness_mm": 6.0, # 原始壁厚
    "min_allowable_thickness_mm": 3.0, # 最小允许壁厚
    "material": "T22",
    "anomaly_start_day": 120,          # 异常工况开始日(第5个月初)
    "anomaly_duration_days": 14,       # 异常持续2周
    "noise_std_pct": 0.03,             # 3%测量噪声
    "hcl_normal_range": (800, 1200),   # 正常HCl浓度范围 mg/m³
    "hcl_anomaly_range": (1600, 1800), # 异常HCl浓度范围
    "flue_temp_range": (550, 600),     # 烟温范围 °C
    "wall_temp_range": (450, 520),     # 壁温范围 °C
}

# ============================================================
# PatchTST 模型配置 (GitHub 原版, no-RevIN, 已验证可用)
# ============================================================
ORIG_PATCHTST = {
    "enc_in": 15,
    "seq_len": 48,
    "pred_len": 48,
    "e_layers": 3,            # Transformer编码层数
    "n_heads": 4,             # 多头注意力头数
    "d_model": 128,           # 模型维度
    "d_ff": 256,              # 前馈网络维度
    "dropout": 0.1,
    "fc_dropout": 0.1,
    "head_dropout": 0.0,
    "patch_len": 8,           # Patch长度
    "stride": 4,              # Patch步长
    "padding_patch": "end",
    "individual": False,
    "revin": False,           # ★ 关掉 — 保留分布偏移用于异常检测
    "affine": False,
    "subtract_last": False,
    "decomposition": False,
    "kernel_size": 25,
    # 训练
    "lambda_physics": 0.1,
    "batch_size": 16,
    "epochs": 35,
    "learning_rate": 1e-4,
    "weight_decay": 1e-5,
    "train_hours": 2400,      # 前100天正常数据训练
}
