"""P0-5 (BIZ-002): 仓库内 thresholds.json 必须满足三级分位契约"""
from ml.physics import THRESHOLDS_PATH, load_thresholds


def test_repo_thresholds_file_valid():
    t = load_thresholds(THRESHOLDS_PATH)
    # 三级分位存在且严格有序
    assert 0 < t["mse_p95"] <= t["mse_p99"] <= t["mse_p999"]
    # 异常均值须显著高于正常均值 (分离度), 否则阈值无判别力
    assert t["mse_anomaly_mean"] > t["mse_normal_mean"] * 2
    # 统计口径可追溯: 记录了统计时的物理参数 (硬约束§4)
    assert t["physics"]["A"] == 55.0
    assert t["physics"]["anomaly_accel"]["anomaly"] == 30.0
    # 学术诚实性声明不得丢失 (项目亮点)
    assert "_disclaimer" in t and "校准" in t["_disclaimer"]
