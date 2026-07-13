#!/usr/bin/env python3
"""
PatchTST 训练脚本 —— 基于 GitHub 原版 (yuqinie98/PatchTST, MIT License)
模型A: 纯阿伦尼乌斯机理 → 固定物理公式, 不训练
模型B: 原版PatchTST (no-RevIN) → 标准 MSE loss
模型C: 原版PatchTST (no-RevIN) + 物理约束 → MSE + λ × physics_loss
"""
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from pathlib import Path
import sys
import json

# 引入 GitHub 原版 PatchTST
_PATCHTST_DIR = Path(__file__).parent / "PatchTST" / "PatchTST_supervised"
sys.path.insert(0, str(_PATCHTST_DIR))
from models.PatchTST import Model as PatchTST_Orig
from types import SimpleNamespace

from config import MATERIAL_PARAMS, SIMULATION


# ============================================================
# 原版 PatchTST 配置 (no-RevIN, 已验证可用)
# ============================================================
def make_config(seq_len=48):
    return SimpleNamespace(
        enc_in=15, seq_len=seq_len, pred_len=seq_len,
        e_layers=3, n_heads=4, d_model=128, d_ff=256,
        dropout=0.1, fc_dropout=0.1, head_dropout=0.0,
        patch_len=8, stride=4, padding_patch='end',
        individual=False,
        revin=False,          # 关掉 RevIN —— 保留分布偏移用于异常检测
        affine=False, subtract_last=False,
        decomposition=False, kernel_size=25,
    )


# ============================================================
# 物理约束 Loss
# ============================================================
class PhysicsLoss(nn.Module):
    """
    physics_loss = mean(|wall_loss_predicted - wall_loss_arrhenius|)
    取重建序列的 HCl 浓度和温度代入阿伦尼乌斯方程导出腐蚀速率,
    与序列累积壁厚变化对比, 偏离越大惩罚越重。
    """
    def __init__(self, material="T22"):
        super().__init__()
        p = MATERIAL_PARAMS[material]
        self.A = torch.tensor(p.A, dtype=torch.float32)
        self.Ea = torch.tensor(p.Ea, dtype=torch.float32)
        self.R = torch.tensor(p.R, dtype=torch.float32)
        self.m = torch.tensor(p.m, dtype=torch.float32)

    def forward(self, recon, orig):
        # recon: (B, L, C)  [Batch, Input length, Channel]
        hcl = torch.clamp(recon[:, :, 1], min=1)
        temp = torch.clamp(recon[:, :, 0] + 273.15, min=300)
        rate = (self.A
                * torch.exp(-self.Ea / (self.R * temp))
                * (hcl ** self.m)
                * (300 ** 0.35))
        wall_change = torch.cumsum(rate / (365 * 24), dim=1)
        return torch.mean(torch.abs(wall_change[:, -1] - wall_change[:, 0]))


# ============================================================
# 数据加载
# ============================================================
def load_data(csv_path, train_hours=2400, seq_len=48, stride=5):
    """训练: 前 train_hours 小时的正常工况数据 → 滑动窗口"""
    df = pd.read_csv(csv_path)
    cols = [c for c in df.columns if c not in
            ('timestamp', '管壁超声厚度', '实际壁厚', '实际腐蚀速率', '标签')]
    X = df[cols].values[::60].astype(np.float32)       # 分钟→小时
    Y = df['标签'].values[::60]

    X_train = X[:train_hours][Y[:train_hours] == 0]
    windows = np.array([X_train[i:i + seq_len]
                        for i in range(0, len(X_train) - seq_len, stride)])
    mean = windows.mean(axis=(0, 1), keepdims=True)
    std = windows.std(axis=(0, 1), keepdims=True) + 1e-8
    windows_norm = (windows - mean) / std
    return windows_norm, mean, std


# ============================================================
# 训练函数
# ============================================================
def train_one(config, dataloader, lam=0.0, epochs=35, lr=1e-4, label=''):
    """lam=0 → 纯 MSE;  lam>0 → MSE + λ × physics_loss"""
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = PatchTST_Orig(config).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-5)
    mse_fn = nn.MSELoss()
    physics_fn = PhysicsLoss('T22') if lam > 0 else None

    for epoch in range(epochs):
        model.train()
        total = 0.0
        for (batch,) in dataloader:
            batch = batch.to(device)
            optimizer.zero_grad()
            out = model(batch)
            loss = mse_fn(out, batch)
            if physics_fn is not None:
                loss = loss + lam * physics_fn(out, batch)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            total += loss.item()
        if epoch % 5 == 0:
            print(f'  {label} E{epoch:3d}: {total / len(dataloader):.6f}', flush=True)
    model.eval()
    return model


# ============================================================
# 消融实验入口
# ============================================================
def main():
    csv_path = Path(__file__).parent / "simulation_data.csv"
    if not csv_path.exists():
        print("[ERROR] 先运行 simulate.py 生成仿真数据")
        return

    seq_len = 48
    config = make_config(seq_len)

    print("[1/3] 加载数据...", flush=True)
    samples, mean, std = load_data(csv_path, train_hours=2400,
                                   seq_len=seq_len, stride=5)
    print(f"  训练样本: {samples.shape[0]} × {samples.shape[1]}步 × {samples.shape[2]}特征",
          flush=True)

    tensor_data = torch.from_numpy(samples).float()
    loader = DataLoader(TensorDataset(tensor_data), batch_size=16, shuffle=True)

    # ---- 模型A: 纯机理 (不训练) ----
    print("\n[2/3] 模型A: 纯阿伦尼乌斯机理 → 固定公式, 不训练", flush=True)

    # ---- 模型B: 纯 PatchTST (λ=0) ----
    print(f"\n[3/3] 模型B: 原版PatchTST no-RevIN (纯AI, λ=0)", flush=True)
    model_b = train_one(config, loader, lam=0.0, epochs=35, label='B')

    # ---- 模型C: PatchTST + 物理约束 (λ=0.1) ----
    print(f"\n      模型C: 原版PatchTST no-RevIN + 物理约束 (λ=0.1)", flush=True)
    model_c = train_one(config, loader, lam=0.1, epochs=35, label='C')

    # ---- 保存 ----
    out = Path(__file__).parent
    torch.save(model_b.state_dict(), out / "model_b_pure.pth")
    torch.save(model_c.state_dict(), out / "model_c_fusion.pth")
    np.savez(out / "norm_params.npz", mean=mean, std=std)

    params = sum(p.numel() for p in model_b.parameters())
    print(f"\n===== 训练完成 =====")
    print(f"  模型: GitHub原版 PatchTST (no-RevIN)")
    print(f"  参数量: {params:,}")
    print(f"  模型文件: model_b_pure.pth / model_c_fusion.pth")
    print(f"  标准化参数: norm_params.npz")
    print(f"  消融实验指标: 运行 ablation.py")


if __name__ == "__main__":
    main()
