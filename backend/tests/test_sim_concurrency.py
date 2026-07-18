"""P0-4 (CODE-001, CODE-004前置): Simulation.advance_to 并发安全"""
import threading

from backend.services.realtime_sim import Simulation


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
