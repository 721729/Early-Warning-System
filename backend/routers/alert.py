"""实时预警接口"""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from datetime import datetime
from backend.middleware.auth import require_role

router = APIRouter(prefix="/api/v1/alert", tags=["实时预警"])


class AlertConfirm(BaseModel):
    confirm_by: str
    action: str


# 模拟活跃预警 (Demo数据)
_MOCK_ALERTS = [
    {"id": 1, "device_id": 1, "device_name": "高温过热器入口段第1排",
     "alert_level": "orange", "alert_time": "2026-07-14T08:15:00",
     "reason": "HCl浓度连续48小时超出正常基线30%，"
              "当前腐蚀速率0.35mm/年(正常0.15mm/年)，"
              "预测剩余寿命45天",
     "predicted_loss": 420000,
     "status": "pending"},
]


@router.get("/active")
async def get_active_alerts(
    plant_id: int = Query(1),
    user: dict = Depends(require_role(["值长", "检修班长", "厂长", "管理员"]))
):
    return _MOCK_ALERTS


@router.post("/{alert_id}/confirm")
async def confirm_alert(
    alert_id: int,
    body: AlertConfirm,
    user: dict = Depends(require_role(["检修班长", "厂长", "管理员"]))
):
    for a in _MOCK_ALERTS:
        if a["id"] == alert_id:
            a["status"] = "confirmed"
            return {"msg": f"预警{alert_id}已确认", "confirm_by": body.confirm_by}
    return {"error": "预警不存在"}


@router.get("/history")
async def get_history(
    plant_id: int = Query(1),
    start: str = Query("2026-06-01"),
    end: str = Query("2026-07-01"),
    user: dict = Depends(require_role(["值长", "检修班长", "厂长", "管理员"]))
):
    return _MOCK_ALERTS
