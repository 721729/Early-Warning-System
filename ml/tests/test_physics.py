"""P0-4/P0-5 (CODE-001, BIZ-001/BIZ-002): 阿伦尼乌斯纯函数 + 三级阈值判定"""
import json
import math

import numpy as np
import pytest

from ml.config import MATERIAL_PARAMS
from ml.physics import (anomaly_score, arrhenius_rate, classify_alert,
                        corrosion_rate, load_thresholds)

T22 = MATERIAL_PARAMS["T22"]


def expected_rate(A, Ea, m, n, temp_k, hcl, h2s, R=8.314):
    """独立复算参考值 (math实现, 与被测numpy实现互为对照)"""
    return A * math.exp(-Ea / (R * temp_k)) * hcl ** m * h2s ** n


class TestArrhenius:
    def test_typical_value_t22(self):
        """正常工况: 575°C, HCl=1000, H2S=300 → ≈0.21 mm/年 (A=55 训练基准)"""
        r = float(corrosion_rate(575 + 273.15, 1000.0, 300.0, T22))
        assert r == pytest.approx(
            expected_rate(55.0, 85000, 0.65, 0.35, 848.15, 1000.0, 300.0), rel=1e-9)
        assert 0.15 < r < 0.30

    def test_temperature_monotonic_increasing(self):
        r1 = arrhenius_rate(800.0, 1000, 300, T22.A, T22.Ea, T22.m, T22.n)
        r2 = arrhenius_rate(900.0, 1000, 300, T22.A, T22.Ea, T22.m, T22.n)
        assert r2 > r1

    def test_hcl_monotonic_increasing(self):
        r1 = arrhenius_rate(848.15, 1000, 300, T22.A, T22.Ea, T22.m, T22.n)
        r2 = arrhenius_rate(848.15, 1800, 300, T22.A, T22.Ea, T22.m, T22.n)
        assert r2 > r1

    def test_low_concentration_clipped_to_one(self):
        """HCl/H2S ≤1 时截断为1: 不产生0速率或复数"""
        r_zero = arrhenius_rate(848.15, 0.0, -5.0, T22.A, T22.Ea, T22.m, T22.n)
        r_one = arrhenius_rate(848.15, 1.0, 1.0, T22.A, T22.Ea, T22.m, T22.n)
        assert float(r_zero) == pytest.approx(float(r_one))
        assert float(r_zero) > 0

    def test_vectorized_matches_scalar(self):
        temps = np.array([800.0, 848.15, 900.0])
        hcls = np.array([900.0, 1000.0, 1700.0])
        h2ss = np.array([250.0, 300.0, 350.0])
        vec = arrhenius_rate(temps, hcls, h2ss, T22.A, T22.Ea, T22.m, T22.n)
        for i in range(3):
            assert vec[i] == pytest.approx(
                expected_rate(T22.A, T22.Ea, T22.m, T22.n,
                              temps[i], hcls[i], h2ss[i]), rel=1e-9)

    def test_accel_multiplier_linear(self):
        """异常加速 = 同一物理参数 × 乘子 (BIZ-001), 而非另一套A值"""
        base = float(corrosion_rate(848.15, 1000, 300, T22))
        assert float(corrosion_rate(848.15, 1000, 300, T22, accel=30.0)) == \
            pytest.approx(30.0 * base, rel=1e-12)
        assert float(corrosion_rate(848.15, 1000, 300, T22, accel=45.0)) == \
            pytest.approx(45.0 * base, rel=1e-12)


THR = {"mse_p95": 1e-4, "mse_p99": 2e-4, "mse_p999": 4e-4}


class TestClassifyAlert:
    @pytest.mark.parametrize("mse,wall,expected", [
        (5e-5,   5.9,  "green"),    # 一切正常
        (1e-4,   5.9,  "green"),    # 恰好等于p95不触发 (严格大于)
        (1.5e-4, 5.9,  "yellow"),   # >p95 (5%误报带)
        (2.5e-4, 5.9,  "orange"),   # >p99 (1%误报带)
        (5e-4,   5.9,  "red"),      # >p99.9 (0.1%误报带)
        (5e-5,   3.8,  "red"),      # 壁厚 < 3.0×1.3=3.9 物理红线
        (5e-5,   3.9,  "red"),      # 压线即危险 (fail-safe, ≤语义)
        (5e-5,   3.91, "green"),    # 线上方安全侧
    ])
    def test_three_tier_matrix(self, mse, wall, expected):
        level, _ = classify_alert(mse, wall, THR)
        assert level == expected

    def test_flags_returned(self):
        level, flags = classify_alert(5e-4, 5.9, THR)
        assert level == "red"
        assert flags["mse_red"] and not flags["wall_danger"]


def test_anomaly_score_piecewise_quantile_anchored():
    """[0,p95)→[0,0.5) 正常带; [p95,p999]→[0.5,0.9] 预警带; >p999→(0.9,1.0] 危险带"""
    assert anomaly_score(0.0, THR) == 0.0
    assert anomaly_score(5e-5, THR) == pytest.approx(0.25)  # 正常带中点
    assert anomaly_score(1e-4, THR) == pytest.approx(0.5)   # p95 锚点
    assert anomaly_score(4e-4, THR) == pytest.approx(0.9)   # p999 锚点
    assert anomaly_score(8e-4, THR) == 1.0                  # 饱和
    xs = [0.0, 5e-5, 1.5e-4, 2.5e-4, 4e-4, 6e-4, 1e-3]
    ss = [anomaly_score(x, THR) for x in xs]
    assert ss == sorted(ss)  # 单调不减


def test_load_thresholds_missing_keys_raises(tmp_path):
    p = tmp_path / "t.json"
    p.write_text(json.dumps({"mse_normal_99pct": 0.0002}))
    with pytest.raises(KeyError):
        load_thresholds(p)


def test_load_thresholds_roundtrip(tmp_path):
    p = tmp_path / "t.json"
    p.write_text(json.dumps(THR))
    t = load_thresholds(p)
    assert t["mse_p95"] == 1e-4 and t["mse_p999"] == 4e-4
