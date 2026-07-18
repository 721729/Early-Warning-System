"""P0-5 (BIZ-001): 实时仿真必须与统一物理实现一致 —— A单一来源+乘子回归护栏"""
import numpy as np

from backend.services.realtime_sim import Simulation
from ml.config import ANOMALY_ACCEL, DEFAULT_H2S_MG_M3, MATERIAL_PARAMS
from ml.physics import corrosion_rate

T22 = MATERIAL_PARAMS["T22"]


def _recomputed_rate(rec, accel):
    """由history存储的温度/HCl反算速率 (与仿真内部同一实现)"""
    return float(corrosion_rate(rec["t"] + 273.15, rec["hcl"],
                                DEFAULT_H2S_MG_M3, T22, accel=accel))


def test_normal_period_uses_base_A():
    """正常段: accel=×1, 速率可由 (t,hcl,A=55) 精确复算 (存储值保留4位小数)"""
    sim = Simulation()
    sim.advance_to(100)
    for rec in sim.history[:100]:
        expected = _recomputed_rate(rec, ANOMALY_ACCEL["normal"])
        assert abs(rec["r"] - expected) < 5e-3, rec
    # 正常速率量级 ≈0.21 mm/年 (A=55基准, 不再是旧A=200的0.76)
    rates = [r["r"] for r in sim.history[:100]]
    assert 0.10 < np.mean(rates) < 0.35


def test_anomaly_period_uses_x30_multiplier():
    """异常段: 同一A × ANOMALY_ACCEL['anomaly']=30, 不存在第二套A值"""
    sim = Simulation()
    sim.advance_to(sim.a_start + 100)
    anomaly_recs = [r for r in sim.history if sim.a_start + 10 <= r["h"] < sim.a_start + 100]
    assert anomaly_recs
    for rec in anomaly_recs:
        expected = _recomputed_rate(rec, ANOMALY_ACCEL["anomaly"])
        assert abs(rec["r"] - expected) < 5e-2, rec


def test_danger_mode_uses_x45_multiplier():
    sim = Simulation()
    sim.danger = True
    sim.advance_to(sim.a_start + 50)
    danger_recs = [r for r in sim.history if r["h"] >= sim.a_start]
    assert danger_recs
    for rec in danger_recs:
        expected = _recomputed_rate(rec, ANOMALY_ACCEL["danger"])
        assert abs(rec["r"] - expected) < 5e-2, rec
