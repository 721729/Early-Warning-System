"""实时预警接口 —— MySQL持久化"""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy.orm import Session
from typing import List

from backend.middleware.auth import require_role
from backend.models.database import get_db
from backend.models.tables import AlertLog, WorkOrder
from backend.routers.users import broadcast_notification

router = APIRouter(prefix="/api/v1/alert", tags=["实时预警"])

class AlertConfirm(BaseModel):
    confirm_by: str
    action: str

class AutoAlertReq(BaseModel):
    device_id: int = 1
    device_name: str = "高温过热器入口段"
    alert_level: str  # yellow/orange/red
    reason: str
    corrosion_rate: float
    wall_thickness: float
    rul_days: float
    ai_score: float
    predicted_loss: float = 420000


def create_alert_internal(db: Session, req: AutoAlertReq) -> dict:
    """供其他模块调用——保存预警到MySQL并广播通知+生成工单"""
    alert = AlertLog(
        device_id=req.device_id,
        alert_level=req.alert_level,
        alert_time=datetime.now(),
        reason=req.reason,
        predicted_loss=req.predicted_loss,
        status="pending"
    )
    db.add(alert)
    db.flush()

    # 自动生成工单
    wo = WorkOrder(
        alert_id=alert.id,
        device_id=req.device_id,
        fault_desc=f"{req.device_name}触发{req.alert_level}级预警",
        root_cause=f"AI重建误差异常(AI得分{req.ai_score:.2f})，腐蚀速率{req.corrosion_rate}mm/年",
        action_plan="1.确认预警信息 2.安排现场巡检 3.检查受热面管壁 4.视情安排计划停炉",
        spare_parts="T22管材 φ51×5mm ×200m, 弯头×4, 焊接材料1套",
        similar_cases=f"2024年8月新沂项目类似工况，停炉11天，损失约280万元",
        status="draft"
    )
    db.add(wo)
    db.commit()
    db.refresh(alert)
    db.refresh(wo)

    # 广播通知
    broadcast_notification(
        f"⚠ {req.alert_level.upper()}预警: {req.device_name}腐蚀异常，"
        f"AI异常得分{req.ai_score:.2f}，预估剩余寿命{req.rul_days:.0f}天，工单#{wo.id}已生成",
        created_by="AI系统")

    return {"alert_id": alert.id, "work_order_id": wo.id, "rul_days": req.rul_days}


@router.post("/auto")
async def auto_create_alert(
    req: AutoAlertReq,
    user: dict = Depends(require_role(["admin", "值长", "检修班长", "厂长", "管理员"])),
    db: Session = Depends(get_db)
):
    """AI自动创建预警(由health router调用)"""
    return create_alert_internal(db, req)


@router.get("/active")
async def get_active_alerts(
    plant_id: int = Query(1),
    user: dict = Depends(require_role(["admin", "值长", "检修班长", "厂长", "管理员"])),
    db: Session = Depends(get_db)
) -> List[dict]:
    alerts = db.query(AlertLog).filter(AlertLog.status != "resolved").order_by(AlertLog.alert_time.desc()).limit(20).all()
    return [{"id": a.id, "device_id": a.device_id, "alert_level": a.alert_level,
             "alert_time": str(a.alert_time), "reason": a.reason,
             "predicted_loss": float(a.predicted_loss or 0), "status": a.status} for a in alerts]


@router.post("/{alert_id}/confirm")
async def confirm_alert(
    alert_id: int,
    body: AlertConfirm,
    user: dict = Depends(require_role(["admin", "检修班长", "厂长", "管理员"])),
    db: Session = Depends(get_db)
):
    alert = db.query(AlertLog).filter(AlertLog.id == alert_id).first()
    if not alert:
        return {"error": "预警不存在"}
    alert.status = "confirmed"
    alert.confirm_by = body.confirm_by
    alert.confirm_time = datetime.now()
    db.commit()
    return {"msg": f"预警{alert_id}已确认"}


@router.get("/history")
async def get_history(
    plant_id: int = Query(1),
    start: str = Query("2026-06-01"),
    end: str = Query("2026-07-31"),
    user: dict = Depends(require_role(["admin", "值长", "检修班长", "厂长", "管理员"])),
    db: Session = Depends(get_db)
) -> List[dict]:
    alerts = db.query(AlertLog).order_by(AlertLog.alert_time.desc()).limit(100).all()
    return [{"id": a.id, "device_id": a.device_id, "alert_level": a.alert_level,
             "alert_time": str(a.alert_time), "reason": a.reason,
             "predicted_loss": float(a.predicted_loss or 0), "status": a.status,
             "confirm_by": a.confirm_by or "", "resolution": a.resolution or ""} for a in alerts]
