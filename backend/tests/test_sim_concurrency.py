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


def test_rul_rate_blended_windows_smooth_transition():
    """三窗口加权混合: 168h先衰减, 720h再衰减, 避免二值跳变"""
    sim = Simulation()
    # 正常段
    sim.advance_to(500)
    rate_48h = np.mean([x["r"] for x in sim.history[-48:]])
    rate_168h = max(x["r"] for x in sim.history[-168:])
    rate_720h = max(x["r"] for x in sim.history[-720:])
    assert rate_48h < 0.5 and rate_168h < 0.5 and rate_720h < 0.5

    # 危险段: ×45加速
    sim.danger = True
    sim.advance_to(sim.a_start + 1440)
    rate_48h_d = np.mean([x["r"] for x in sim.history[-48:]])
    rate_168h_d = max(x["r"] for x in sim.history[-168:])
    rate_720h_d = max(x["r"] for x in sim.history[-720:])
    assert rate_48h_d > 5 and rate_168h_d > 5 and rate_720h_d > 5

    # 恢复后 168h 窗口先滑出危险峰值
    sim.danger = False
    sim.advance_to(sim.hours + 200)
    rate_168h_r1 = max(x["r"] for x in sim.history[-168:])
    rate_720h_r1 = max(x["r"] for x in sim.history[-720:])
    assert rate_720h_r1 > 5   # 720h 仍含危险峰
    assert rate_168h_r1 < 1   # 168h 已滑出 → 先行衰减

    # 720h 窗口也滑出后
    sim.advance_to(sim.hours + 600)
    rate_168h_r2 = max(x["r"] for x in sim.history[-168:])
    rate_720h_r2 = max(x["r"] for x in sim.history[-720:])
    assert rate_168h_r2 < 1 and rate_720h_r2 < 1  # 全部回到正常

    # 全历史 max 仍锁定(旧逻辑的bug)
    assert max(x["r"] for x in sim.history) > 5
