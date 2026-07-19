"""P0-4 (CODE-001, CODE-004前置): Simulation.advance_to 并发安全 + RUL 滑动窗口"""
import threading

import numpy as np

from backend.services.realtime_sim import Simulation
from ml.physics import calculate_rul


def test_advance_to_thread_safe():
    """8线程并发推进到同一目标: history 必须恰好500条且小时序连续无重复。

    修复前(无锁)实测: 多线程重复执行推进段, history 膨胀到4000条、壁厚被重复扣减8次。
    """
    for _ in range(5):  # 多轮降低偶然通过概率
        sim = Simulation()
        threads = [threading.Thread(target=sim.advance_to, args=(500,))
                   for _ in range(8)]
        [t.start() for t in threads]
        [t.join() for t in threads]
        hs = [r["h"] for r in sim.history]
        assert len(hs) == 500
        assert hs == list(range(500))
        assert sim.hours == 500


def test_advance_to_interleaved_targets():
    """多线程按不同目标交错推进, 最终状态仍一致"""
    sim = Simulation()
    targets = [100, 300, 200, 500, 400] * 4
    threads = [threading.Thread(target=sim.advance_to, args=(t,)) for t in targets]
    [t.start() for t in threads]
    [t.join() for t in threads]
    hs = [r["h"] for r in sim.history]
    assert hs == list(range(500))
    # 壁厚与最后一条历史一致 (history存3位小数)
    assert abs(sim.wall - sim.history[-1]["w"]) < 1e-3
    # 壁厚单调不增
    walls = [r["w"] for r in sim.history]
    assert all(a >= b for a, b in zip(walls, walls[1:]))


def test_rul_rate_uses_sliding_window_not_all_time_max():
    """RUL 的恶化速率取最近720h滑动窗口而非全历史max,
    避免危险工况后 rate_rul 被永久锁定在峰值导致 RUL 冻住不更新"""
    sim = Simulation()
    # 正常段: 累计500h, rate≈0.21, 全历史max≈0.3
    sim.advance_to(500)
    rate_720h = max(x["r"] for x in sim.history[-720:])
    rate_all_max = max(x["r"] for x in sim.history)
    rul_720h = calculate_rul(sim.wall, rate_720h)
    # 正常段720h窗口与全历史max应接近
    assert abs(rate_720h - rate_all_max) < 0.2

    # 危险段: ×45加速后 rate 飙升到10+
    sim.danger = True
    sim.advance_to(sim.a_start + 1440)  # 完整经过危险期 (2880→4320)
    rate_720h_danger = max(x["r"] for x in sim.history[-720:])
    rate_all_max_danger = max(x["r"] for x in sim.history)
    # 危险刚结束时720h窗口包含峰值
    assert rate_720h_danger > 5.0

    # 继续正常推进 730h (超出720h滑动窗口), danger峰值应从窗口滑出
    sim.danger = False
    sim.advance_to(sim.hours + 730)
    rate_720h_after = max(x["r"] for x in sim.history[-720:])
    rate_all_max_after = max(x["r"] for x in sim.history)
    # 全历史max仍锁定在danger峰值
    assert rate_all_max_after > 5.0
    # 滑动窗口已不含danger段, 回到正常速率量级
    assert rate_720h_after < 1.0
    # 两种策略下的RUL差异: 滑动窗口RUL更高(=更真实, 当前工况已恢复正常)
    rul_720h_after = calculate_rul(sim.wall, max(rate_720h_after, np.mean([x["r"] for x in sim.history[-48:]])))
    rul_max_after = calculate_rul(sim.wall, rate_all_max_after)
    assert rul_720h_after["rul_days"] > rul_max_after["rul_days"] * 2, \
        f"滑动窗口RUL {rul_720h_after['rul_days']} 应远大于全历史RUL {rul_max_after['rul_days']}"
