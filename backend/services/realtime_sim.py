"""
实时仿真引擎 —— 独立实例，每次API调用新建Simulation
"""
import numpy as np
from ml.config import MATERIAL_PARAMS

_params = MATERIAL_PARAMS["T22"]

class Simulation:
    def __init__(self):
        self.hours = 0; self.wall = 6.0; self.history = []
        self.a_start = 2880; self.a_spike = 2890

    def _hcl(self, h):
        if self.a_spike <= h < self.a_spike + 2: return np.random.uniform(1700, 1900)
        elif self.a_start <= h < self.a_start + 336: return np.random.uniform(1550, 1800)
        return 1000 + np.random.randn() * 80

    def _temp(self, h):
        b = 555 if (self.a_spike <= h < self.a_spike + 2) else 565 if (self.a_start <= h < self.a_start + 336) else 575
        return b + np.random.randn() * 8

    def advance_to(self, target):
        if target <= self.hours: return
        # 批量生成N小时数据（numpy向量化，10x加速）
        n = target - self.hours
        hours_arr = np.arange(self.hours, target)
        hcl_arr = np.array([self._hcl(h) for h in hours_arr])
        temp_arr = np.array([self._temp(h) for h in hours_arr])
        tk_arr = temp_arr + 273.15
        rate_arr = _params.A * np.exp(-_params.Ea/(_params.R*tk_arr)) * (np.clip(hcl_arr,1,None)**_params.m) * (300**_params.n)
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
        in_anomaly = self.hours >= self.a_start
        for i, r in enumerate(rec):
            t = r["t"]; hcl = r["hcl"]
            if in_anomaly:
                # 异常段: 参数关系改变——O2与温度脱钩, 壁温异常波动, 蒸汽不稳
                w[i,0]=t+np.random.randn()*5; w[i,1]=hcl; w[i,2]=hcl*.2
                w[i,3]=60+np.random.randn()*8     # CO偏高
                w[i,4]=6+np.random.randn()*.8     # O2偏低且与温度脱钩
                w[i,5]=25+np.random.randn()*4     # 颗粒物偏高
                w[i,6]=t-80+np.random.randn()*8   # 壁温大幅波动
                w[i,7]=t-100+np.random.randn()*8
                w[i,8]=t-130+np.random.randn()*8
                w[i,9]=t-10; w[i,10]=t-25; w[i,11]=t-55
                w[i,12]=38+np.random.randn()*2    # 蒸汽流量偏低
                w[i,13]=3.7+np.random.randn()*.15 # 蒸汽压力偏低
                w[i,14]=390+np.random.randn()*8   # 蒸汽温度偏低
            else:
                w[i,0]=t; w[i,1]=hcl; w[i,2]=hcl*.2
                w[i,3]=50+np.random.randn()*5; w[i,4]=8+np.random.randn()*.3; w[i,5]=20+np.random.randn()*2
                w[i,6]=t-90; w[i,7]=t-110; w[i,8]=t-140; w[i,9]=t-15; w[i,10]=t-30; w[i,11]=t-60
                w[i,12]=40+np.random.randn(); w[i,13]=4.0+np.random.randn()*.05; w[i,14]=400+np.random.randn()
        return w, rec
