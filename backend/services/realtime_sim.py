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
        while self.hours < target:
            hcl = self._hcl(self.hours); temp = self._temp(self.hours)
            tk = temp + 273.15
            rate = _params.A * np.exp(-_params.Ea/(_params.R*tk)) * (max(hcl,1)**_params.m) * (300**_params.n)
            self.wall -= rate / (365*24)
            self.history.append({"h": self.hours, "w": round(self.wall,3), "hcl": round(hcl,1), "t": round(temp,1), "r": round(rate,4)})
            self.hours += 1

    def window(self, sz=48):
        if self.hours < sz: self.advance_to(sz)
        rec = self.history[-sz:]
        w = np.zeros((sz, 15), dtype=np.float32)
        for i, r in enumerate(rec):
            t = r["t"]; w[i,0]=t; w[i,1]=r["hcl"]; w[i,2]=r["hcl"]*.2
            w[i,3]=50+np.random.randn()*5; w[i,4]=8+np.random.randn()*.3; w[i,5]=20+np.random.randn()*2
            w[i,6]=t-90; w[i,7]=t-110; w[i,8]=t-140; w[i,9]=t-15; w[i,10]=t-30; w[i,11]=t-60
            w[i,12]=40+np.random.randn(); w[i,13]=4.0+np.random.randn()*.05; w[i,14]=400+np.random.randn()
        return w, rec
