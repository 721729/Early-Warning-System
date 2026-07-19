"""趋势预测接口"""
from fastapi import APIRouter, Depends, Query

from backend.middleware.auth import require_role
from backend.models.tables import ALL_ROLES
from ml.physics import calculate_rul

router = APIRouter(prefix="/api/v1/predict", tags=["趋势预测"])


@router.get("/trend/{device_id}")
async def get_param_trend(
    device_id: int,
    horizon: str = Query("24h"),
    user: dict = Depends(require_role(ALL_ROLES))
):
    # Demo数据, 生产调用 ml/inference.py
    hours = 24 if horizon == "24h" else 168
    import math
    data = []
    for h in range(hours):
        data.append({
            "hour": h + 1,
            "furnace_temp": 570 + 10 * math.sin(h / 4),
            "hcl_conc": 1100 + 50 * math.sin(h / 6),
        })
    return {"device_id": device_id, "horizon": horizon, "data": data}


@router.get("/wall/{device_id}")
async def get_wall_prediction(
    device_id: int,
    horizon: str = Query("14d"),
    user: dict = Depends(require_role(ALL_ROLES))
):
    days = 14 if horizon == "14d" else 7
    data = []
    wall = 5.1
    for d in range(days):
        wall -= 0.35 / 365
        data.append({
            "day": d + 1,
            "wall_thickness": round(wall, 2),
            "upper_bound": round(wall + 0.15, 2),
            "lower_bound": round(wall - 0.10, 2),
        })
    return {"device_id": device_id, "horizon": horizon, "data": data,
            "message": f"按当前腐蚀速率, 预计12天后壁厚进入危险区, 建议7天内安排停炉检查"}


@router.get("/rul/{device_id}")
async def get_rul(
    device_id: int,
    user: dict = Depends(require_role(ALL_ROLES))
):
    """剩余寿命估算 (BIZ-003: 统一走 ml/physics.calculate_rul, 不再硬编码)"""
    # Demo: 从全局仿真实例取当前状态 → 共享RUL函数
    from backend.routers.health import _sim
    rate = _sim.history[-1]["r"] if _sim.history else 0.01
    wall = _sim.wall
    rul = calculate_rul(wall, rate)
    return {
        "device_id": device_id,
        "wall_mm": round(wall, 2),
        "rate_mm_per_year": round(rate, 4),
        **rul,
    }
