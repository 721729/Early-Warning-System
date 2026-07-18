"""实时预警接口 —— MySQL持久化"""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy.orm import Session
from typing import List

from backend.middleware.auth import require_role
from backend.models.database import get_db
from backend.models.tables import AlertLog, WorkOrder, ALL_ROLES, SUPERVISOR_ROLES, ADMIN_ONLY
from backend.routers.users import broadcast_notification

router = APIRouter(prefix="/api/v1/alert", tags=["实时预警"])

class AlertConfirm(BaseModel):
    confirm_by: str
    action: str

class AlertEdit(BaseModel):
    reason: str | None = None
    resolution: str | None = None

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
    user: dict = Depends(require_role(ALL_ROLES)),
    db: Session = Depends(get_db)
):
    """AI自动创建预警(由health router调用)"""
    return create_alert_internal(db, req)


@router.get("/active")
async def get_active_alerts(
    plant_id: int = Query(1),
    user: dict = Depends(require_role(ALL_ROLES)),
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
    user: dict = Depends(require_role(SUPERVISOR_ROLES)),
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


@router.put("/{alert_id}")
async def edit_alert(
    alert_id: int, body: AlertEdit,
    user: dict = Depends(require_role(SUPERVISOR_ROLES)),
    db: Session = Depends(get_db)
):
    """编辑预警: 修改原因说明/处理记录"""
    a = db.query(AlertLog).filter(AlertLog.id == alert_id).first()
    if not a: return {"error": "预警不存在"}
    if body.reason is not None: a.reason = body.reason
    if body.resolution is not None: a.resolution = body.resolution
    db.commit()
    return {"msg": f"预警{alert_id}已更新"}

@router.delete("/all")
async def delete_all_alerts(
    user: dict = Depends(require_role(ADMIN_ONLY)),
    db: Session = Depends(get_db)
):
    """管理员一键清空所有预警"""
    db.query(AlertLog).delete()
    db.query(WorkOrder).delete()
    db.commit()
    return {"msg": "所有预警和工单已清空"}

@router.delete("/{alert_id}")
async def delete_alert(
    alert_id: int,
    user: dict = Depends(require_role(ADMIN_ONLY)),
    db: Session = Depends(get_db)
):
    """管理员删除预警"""
    db.query(AlertLog).filter(AlertLog.id == alert_id).delete()
    # 同时删关联工单
    db.query(WorkOrder).filter(WorkOrder.alert_id == alert_id).delete()
    db.commit()
    return {"msg": f"预警{alert_id}及关联工单已删除"}


@router.put("/{alert_id}/status")
async def update_alert_status(
    alert_id: int,
    status: str = Query(..., regex="^(pending|confirmed|processing|resolved)$"),
    user: dict = Depends(require_role(SUPERVISOR_ROLES)),
    db: Session = Depends(get_db)
):
    """更新预警状态: pending/confirmed/processing/resolved"""
    a = db.query(AlertLog).filter(AlertLog.id == alert_id).first()
    if not a: return {"error": "预警不存在"}
    a.status = status
    if status == "resolved": a.close_time = datetime.now()
    db.commit()
    return {"msg": f"预警{alert_id}状态→{status}"}




@router.get("/history")
async def get_history(
    plant_id: int = Query(1),
    start: str = Query("2026-06-01"),
    end: str = Query("2026-07-31"),
    user: dict = Depends(require_role(ALL_ROLES)),
    db: Session = Depends(get_db)
) -> List[dict]:
    alerts = db.query(AlertLog).order_by(AlertLog.alert_time.desc()).limit(100).all()
    return [{"id": a.id, "device_id": a.device_id, "alert_level": a.alert_level,
             "alert_time": str(a.alert_time), "reason": a.reason,
             "predicted_loss": float(a.predicted_loss or 0), "status": a.status,
             "confirm_by": a.confirm_by or "", "resolution": a.resolution or ""} for a in alerts]
