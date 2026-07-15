"""设备健康度接口 —— Demo阶段返回Demo数据, Pilot阶段接InfluxDB"""
from fastapi import APIRouter, Depends, Query
from typing import List
from backend.middleware.auth import require_role

router = APIRouter(prefix="/api/v1/health", tags=["设备健康度"])

# Demo阶段: 模型加载为可选项, 失败不影响API返回Demo数据
_MODEL_READY = False

# Demo设备列表 (Pilot阶段接MySQL equipment表)
_DEVICES = [
    {"id": 1, "name": "高温过热器入口段第1排", "type": "过热器",
     "health": "orange", "wall_thickness": 5.1, "original": 6.0,
     "corrosion_rate": 0.35, "rul_days": 45, "dcs_tag": "HAH10"},
    {"id": 2, "name": "高温过热器入口段第2排", "type": "过热器",
     "health": "yellow", "wall_thickness": 5.4, "original": 6.0,
     "corrosion_rate": 0.18, "rul_days": 200, "dcs_tag": "HAH10"},
    {"id": 3, "name": "中温过热器", "type": "过热器",
     "health": "green", "wall_thickness": 5.8, "original": 6.0,
     "corrosion_rate": 0.05, "rul_days": 800, "dcs_tag": "HAH20"},
    {"id": 4, "name": "低温过热器", "type": "过热器",
     "health": "green", "wall_thickness": 5.9, "original": 6.0,
     "corrosion_rate": 0.03, "rul_days": 1200, "dcs_tag": "HAH30"},
    {"id": 5, "name": "省煤器", "type": "省煤器",
     "health": "green", "wall_thickness": 5.5, "original": 6.0,
     "corrosion_rate": 0.02, "rul_days": 3000, "dcs_tag": "HAD10"},
    {"id": 6, "name": "引风机", "type": "引风机",
     "health": "green", "wall_thickness": 0, "original": 0,
     "corrosion_rate": 0, "rul_days": 9999, "dcs_tag": "HAC10"},
]


@router.get("/overview")
async def get_overview(
    plant_id: int = Query(1),
    user: dict = Depends(require_role(["admin", "值长", "检修班长", "厂长", "管理员"]))
) -> List[dict]:
    return _DEVICES


@router.get("/device/{device_id}")
async def get_device_detail(
    device_id: int,
    time_range: str = Query("7d"),
    user: dict = Depends(require_role(["admin", "值长", "检修班长", "厂长", "管理员"]))
) -> dict:
    dev = next((d for d in _DEVICES if d["id"] == device_id), None)
    if not dev:
        return {"error": "设备不存在"}
    # 生成壁厚历史趋势 (模拟)
    import random
    random.seed(device_id)
    history = []
    wall = dev["original"] if dev["original"] > 0 else 6.0
    for i in range(180):
        wall -= dev["corrosion_rate"] / 365 + random.uniform(-0.001, 0.003)
        history.append({"day": i + 1, "wall_thickness": round(max(wall, 0.1), 2)})
    return {**dev, "history": history}
