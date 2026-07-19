"""
实时仿真引擎 —— 独立实例，每次API调用新建Simulation
物理: A 单一来源 ml/config.py MATERIAL_PARAMS, 异常=同一A×工况乘子 (BIZ-001)
"""
import threading

import numpy as np

from ml.config import ANOMALY_ACCEL, DEFAULT_H2S_MG_M3, MATERIAL_PARAMS
from ml.physics import corrosion_rate

_params = MATERIAL_PARAMS["T22"]

class Simulation:
    def __init__(self):
        self.hours = 0; self.wall = 6.0; self.history = []
        self.a_start = 2880; self.a_spike = 2890
        self.danger = False  # 危险模式: 延长异常期+提高加速乘子
        # 并发安全 (CODE-004前置): 无锁时多线程重复执行推进段, 实测history错乱(500小时膨胀成4000条)
        self._lock = threading.Lock()

    def _hcl(self, h):
        if self.a_spike <= h < self.a_spike + 2: return np.random.uniform(1700, 2000)
        elif self.danger and self.a_start <= h < self.a_start + 1440: return np.random.uniform(1600, 2000)
        elif self.a_start <= h < self.a_start + 336: return np.random.uniform(1500, 1900)
        return 1000 + np.random.randn() * 80

    def _temp(self, h):
        if self.a_spike <= h < self.a_spike + 2: b = 545; s = 15
        elif self.danger and self.a_start <= h < self.a_start + 1440: b = 555; s = 14
        elif self.a_start <= h < self.a_start + 336: b = 560; s = 12
        else: b = 575; s = 8
        return b + np.random.randn() * s

    def _accel_for_hour(self, h):
        """异常加速乘子 (BIZ-001): 正常×1, 异常14天×30, 危险模式60天×45
        同一 A=MATERIAL_PARAMS['T22'].A, 不再造第二套A值; 乘子定义见 ml.config.ANOMALY_ACCEL"""
        if self.danger:
            if self.a_start <= h < self.a_start + 1440: return ANOMALY_ACCEL["danger"]
        else:
            if self.a_start <= h < self.a_start + 336: return ANOMALY_ACCEL["anomaly"]
        return ANOMALY_ACCEL["normal"]

    def advance_to(self, target):
        with self._lock:
            if target <= self.hours: return
            n = target - self.hours
            hours_arr = np.arange(self.hours, target)
            hcl_arr = np.array([self._hcl(h) for h in hours_arr])
            temp_arr = np.array([self._temp(h) for h in hours_arr])
            tk_arr = temp_arr + 273.15
            accel_arr = np.array([self._accel_for_hour(h) for h in hours_arr])
            # 统一物理实现 (ml/physics.py); H2S 用名义浓度300, 与训练数据均值一致
            rate_arr = corrosion_rate(tk_arr, hcl_arr, DEFAULT_H2S_MG_M3, _params, accel=accel_arr)
            wall_arr = self.wall - np.cumsum(rate_arr / (365*24))
            for i in range(n):
                self.history.append({"h": int(hours_arr[i]), "w": round(float(wall_arr[i]),3),
                    "hcl": round(float(hcl_arr[i]),1), "t": round(float(temp_arr[i]),1),
                    "r": round(float(rate_arr[i]),4)})
            self.wall = float(wall_arr[-1])
            self.hours = target

    def window(self, sz=48):
        if self.hours < sz: self.advance_to(sz)
        rec = self.history[-sz:]
        w = np.zeros((sz, 15), dtype=np.float32)
        # 检查当前小时是否在异常加速窗口内 (而非 >=a_start 永久true)
        anomaly_end = self.a_start + (1440 if self.danger else 336)
        in_anomaly = self.a_start <= self.hours <= anomaly_end
        for i, r in enumerate(rec):
            t = r["t"]; hcl = r["hcl"]
            # 统一传感器噪声——异常/正常只是基值偏移, 噪声量级一致
            w[i,0]=t+np.random.randn()*5          # 炉膛温度
            w[i,1]=hcl                             # HCl
            w[i,2]=hcl*.2+np.random.randn()*10     # SO2
            w[i,3]=(60 if in_anomaly else 50)+np.random.randn()*5   # CO
            w[i,4]=(6 if in_anomaly else 8)+np.random.randn()*.3    # O2
            w[i,5]=(25 if in_anomaly else 20)+np.random.randn()*2   # 颗粒物
            w[i,6]=t-90+np.random.randn()*5        # 高过壁温
            w[i,7]=t-110+np.random.randn()*5       # 中过壁温
            w[i,8]=t-140+np.random.randn()*5       # 低过壁温
            w[i,9]=t-15+np.random.randn()*5        # 高过烟温
            w[i,10]=t-30+np.random.randn()*5       # 中过烟温
            w[i,11]=t-60+np.random.randn()*5       # 低过烟温
            w[i,12]=(38 if in_anomaly else 40)+np.random.randn()     # 蒸汽流量
            w[i,13]=(3.7 if in_anomaly else 4.0)+np.random.randn()*.05  # 蒸汽压力
            w[i,14]=(390 if in_anomaly else 400)+np.random.randn()   # 蒸汽温度
        return w, rec
