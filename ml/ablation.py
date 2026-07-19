#!/usr/bin/env python3
"""消融实验完整指标 — 训练→测试→汇总"""
import numpy as np, pandas as pd, torch, torch.nn as nn, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from train import PatchTST_Orig, PhysicsLoss, make_config
from config import MATERIAL_PARAMS, SIMULATION

def main():
    DEVICE = 'cpu'; pm = MATERIAL_PARAMS['T22']
    df = pd.read_csv(Path(__file__).parent / 'simulation_data.csv')
    cols = [c for c in df.columns if c not in
            ('timestamp', '管壁超声厚度', '实际壁厚', '实际腐蚀速率', '标签')]
    X = df[cols].values[::60].astype(np.float32)
    Y = df['标签'].values[::60]
    WALL = df['实际壁厚'].values[::60]
    RATE = df['实际腐蚀速率'].values[::60]

    # 训练切片
    cut = int(len(X) * 0.8)
    Xtr = X[:cut][Y[:cut] == 0]
    # 窗口化
    SL = 48
    windows = np.array([Xtr[i:i+SL] for i in range(0, len(Xtr)-SL, 5)])
    mean_ = windows.mean(axis=(0,1), keepdims=True)
    std_ = windows.std(axis=(0,1), keepdims=True) + 1e-8
    W_norm = (windows - mean_) / std_

    from torch.utils.data import DataLoader, TensorDataset
    loader = DataLoader(TensorDataset(torch.from_numpy(W_norm).float()),
                        batch_size=16, shuffle=True)

    def train_one(lam, epochs=30):
        model = PatchTST_Orig(make_config()).to(DEVICE)
        opt = torch.optim.AdamW(model.parameters(), lr=1e-4)
        mse = nn.MSELoss()
        phys = PhysicsLoss('T22') if lam > 0 else None
        for ep in range(epochs):
            model.train()
            total = 0.0
            for (batch,) in loader:
                opt.zero_grad()
                out = model(batch)
                loss = mse(out, batch)
                if phys is not None:
                    loss = loss + lam * phys(out, batch)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                opt.step()
                total += loss.item()
            if ep % 5 == 0:
                print(f'  lam={lam} E{ep}: {total/len(loader):.6f}', flush=True)
        model.eval()
        return model

    print('=== 消融实验训练 ===', flush=True)
    mB = train_one(lam=0.0)
    mC = train_one(lam=0.1)

    torch.save(mB.state_dict(), Path(__file__).parent / 'final_model_b.pth')
    torch.save(mC.state_dict(), Path(__file__).parent / 'final_model_c.pth')
    np.savez(Path(__file__).parent / 'final_norm.npz', mean=mean_, std=std_)

    # 基线MSE
    def mse_of(model, arr):
        w = (arr - mean_) / std_
        t = torch.from_numpy(w).float()
        with torch.no_grad():
            r = model(t)
        return float(torch.mean((r - t) ** 2))

    bl_B = np.mean([mse_of(mB, windows[i]) for i in range(max(0,len(windows)-10), len(windows))])
    bl_C = np.mean([mse_of(mC, windows[i]) for i in range(max(0,len(windows)-10), len(windows))])
    threshold = max(bl_B, bl_C) * 3
    print(f'  基线: B={bl_B:.6f} C={bl_C:.6f} threshold={threshold:.6f}', flush=True)

    # 测试集评估
    Xts = X[cut:]; Yts = Y[cut:]; Wts = WALL[cut:]; Rts = RATE[cut:]
    r = {'B': {'tp':0,'fp':0,'tn':0,'fn':0,'re':[],'rd':[],'po':0,'pt':0},
         'C': {'tp':0,'fp':0,'tn':0,'fn':0,'re':[],'rd':[],'po':0,'pt':0}}
    nw = 0

    for i in range(0, len(Xts) - SL, 6):
        w = Xts[i:i+SL]
        yt = 1 if Yts[i:i+SL].any() else 0
        mb = mse_of(mB, w)
        mc = mse_of(mC, w)
        for key, mse_val in [('B', mb), ('C', mc)]:
            pred = 1 if mse_val > threshold else 0
            if pred and yt: r[key]['tp'] += 1
            elif pred and not yt: r[key]['fp'] += 1
            elif not pred and not yt: r[key]['tn'] += 1
            else: r[key]['fn'] += 1

        # 腐蚀速率 & RUL 误差
        hcl, tk = max(float(w[-1,1]), 1), float(w[-1,0]) + 273.15
        rp = pm.A * np.exp(-pm.Ea/(pm.R*tk)) * (hcl**pm.m) * (300**pm.n)
        ra = Rts[i+SL-1] if i+SL-1 < len(Rts) else rp
        re = abs(rp - ra) / max(abs(ra), 1e-8)
        wp = SIMULATION['original_wall_thickness_mm'] - rp*SL/(365*24)
        rul_p = max(wp - SIMULATION['min_allowable_thickness_mm'], 0) / max(rp, 1e-8) * 365
        wa = Wts[i+SL-1] if i+SL-1 < len(Wts) else wp
        rul_a = max(wa - SIMULATION['min_allowable_thickness_mm'], 0) / max(ra, 1e-8) * 365
        rd = abs(rul_p - rul_a)
        for key in ['B', 'C']:
            r[key]['re'].append(re)
            r[key]['rd'].append(rd)

        # 物理一致性
        for key, model in [('B', mB), ('C', mC)]:
            r[key]['pt'] += 1
            with torch.no_grad():
                recon = model(torch.from_numpy((w-mean_)/std_).float()).numpy()
            if np.all((recon[0,:,0] > 50) & (recon[0,:,0] < 900)) and np.all(recon[0,:,1] >= 0):
                r[key]['po'] += 1
        nw += 1

    def summary(d):
        tp, fp, tn, fn = d['tp'], d['fp'], d['tn'], d['fn']
        total = tp + fp + tn + fn
        return {
            'accuracy': round((tp+tn)/max(total,1), 4),
            'precision': round(tp/max(tp+fp,1), 4),
            'recall': round(tp/max(tp+fn,1), 4),
            'f1': round(2*tp/max(2*tp+fp+fn,1), 4),
            'FPR(false_alarm)': round(fp/max(fp+tn,1), 4),
            'FNR(miss_rate)': round(fn/max(fn+tp,1), 4),
            'corrosion_err_%': round(np.mean(d['re'])*100, 2),
            'RUL_dev_days': round(np.mean(d['rd']), 1),
            'physical_consistency': round(d['po']/max(d['pt'],1), 4),
            'tp': tp, 'fp': fp, 'tn': tn, 'fn': fn
        }

    sB, sC = summary(r['B']), summary(r['C'])

    print('\n' + '=' * 68)
    print('  消融实验完整指标')
    print('=' * 68)
    print(f'  测试窗口: {nw}  |  threshold = {threshold:.4f}')
    print()
    header = f'  {"指标":<24} {"模型B(纯AI)":>12} {"模型C(融合)":>12} {"目标":>10}'
    print(header)
    print(f'  {"-"*58}')
    for label, key in [('准确率', 'accuracy'), ('F1分数', 'f1'),
                        ('误报率(FPR)', 'FPR(false_alarm)'), ('漏报率(FNR)', 'FNR(miss_rate)'),
                        ('腐蚀速率误差', 'corrosion_err_%'), ('RUL偏差(天)', 'RUL_dev_days'),
                        ('物理一致性', 'physical_consistency')]:
        print(f'  {label:<24} {sB[key]:>12.4f} {sC[key]:>12.4f} {"—":>10}')
    print(f'  {"-"*58}')
    print(f'  {"TP/FP/TN/FN":<24} {sB["tp"]:>2}/{sB["fp"]:>2}/{sB["tn"]:>2}/{sB["fn"]:>8} {sC["tp"]:>2}/{sC["fp"]:>2}/{sC["tn"]:>2}/{sC["fn"]:>8}')

    out_path = Path(__file__).parent / 'ablation_metrics.json'
    with open(out_path, 'w') as f:
        json.dump({'B': sB, 'C': sC, 'n_windows': nw, 'threshold': threshold}, f, indent=2, ensure_ascii=False)
    print(f'\n  [OK] {out_path}')

if __name__ == '__main__':
    main()
