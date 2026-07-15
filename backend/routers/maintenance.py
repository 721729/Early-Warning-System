"""运维建议 & 工单 —— MySQL持久化"""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List

from backend.middleware.auth import require_role
from backend.models.database import get_db
from backend.models.tables import WorkOrder, AlertLog

router = APIRouter(prefix="/api/v1/maintenance", tags=["运维建议 & 工单"])

class AutoCreateWO(BaseModel):
    alert_id: int


@router.get("/workorders")
async def list_workorders(
    user: dict = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
) -> List[dict]:
    """所有工单列表"""
    wos = db.query(WorkOrder).order_by(WorkOrder.create_time.desc()).limit(50).all()
    return [{"id": wo.id, "alert_id": wo.alert_id, "device_id": wo.device_id,
             "fault_desc": wo.fault_desc or "", "root_cause": wo.root_cause or "",
             "action_plan": wo.action_plan or "", "spare_parts": wo.spare_parts or "",
             "similar_cases": wo.similar_cases or "", "assignee": wo.assignee or "",
             "status": wo.status,
             "create_time": str(wo.create_time) if wo.create_time else "",
             "complete_time": str(wo.complete_time) if wo.complete_time else ""}
            for wo in wos]


@router.get("/advice/{alert_id}")
async def get_advice(
    alert_id: int,
    user: dict = Depends(require_role(["admin", "值长", "检修班长", "厂长", "管理员"])),
    db: Session = Depends(get_db)
) -> dict:
    """根据预警ID获取关联工单(运维建议)"""
    wo = db.query(WorkOrder).filter(WorkOrder.alert_id == alert_id).first()
    if not wo:
        # 回退到模拟数据
        return {
            "alert_id": alert_id,
            "phenomenon": "未找到关联工单，请手动创建",
            "root_cause": "",
            "action_plan": "",
            "spare_parts": "",
            "similar_cases": ""
        }
    # 取关联预警信息
    alert = db.query(AlertLog).filter(AlertLog.id == alert_id).first()
    return {
        "alert_id": alert_id,
        "work_order_id": wo.id,
        "phenomenon": wo.fault_desc or "",
        "root_cause": wo.root_cause or "",
        "action_plan": wo.action_plan or "",
        "spare_parts": wo.spare_parts or "",
        "similar_cases": wo.similar_cases or "",
        "alert_level": alert.alert_level if alert else "unknown",
        "alert_reason": alert.reason if alert else "",
        "status": wo.status,
    }


@router.post("/workorder/auto_create")
async def auto_create_workorder(
    body: AutoCreateWO,
    user: dict = Depends(require_role(["admin", "检修班长", "厂长", "管理员"])),
    db: Session = Depends(get_db)
):
    """手动为已有预警创建工单"""
    alert = db.query(AlertLog).filter(AlertLog.id == body.alert_id).first()
    if not alert:
        return {"error": "预警不存在"}
    wo = WorkOrder(
        alert_id=body.alert_id, device_id=alert.device_id,
        fault_desc=f"{alert.reason}",
        root_cause="待人工确认",
        action_plan="1.确认预警 2.现场巡检 3.视情停炉检查",
        spare_parts="待确认",
        status="draft"
    )
    db.add(wo)
    db.commit()
    db.refresh(wo)
    return {"work_order_id": wo.id, "status": "draft", "message": "工单已生成"}
