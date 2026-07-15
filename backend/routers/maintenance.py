"""运维建议 & 工单 —— MySQL持久化"""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List

from backend.middleware.auth import require_role
from backend.models.database import get_db
from backend.models.tables import WorkOrder, AlertLog
from backend.routers.inventory import check_stock

router = APIRouter(prefix="/api/v1/maintenance", tags=["运维建议 & 工单"])

class AutoCreateWO(BaseModel):
    alert_id: int

class EditWO(BaseModel):
    assignee: str | None = None
    status: str | None = None
    action_plan: str | None = None
    spare_parts: str | None = None
    fault_desc: str | None = None
    root_cause: str | None = None


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
    """根据预警内容动态生成运维建议(AI推理结果驱动)"""
    alert = db.query(AlertLog).filter(AlertLog.id == alert_id).first()
    if not alert:
        return {"alert_id": alert_id, "phenomenon": "预警不存在"}

    wo = db.query(WorkOrder).filter(WorkOrder.alert_id == alert_id).first()

    # 从预警原因中提取参数动态生成建议
    reason = alert.reason or ""
    import re
    mse_match = re.search(r'MSE=([\d.]+)', reason)
    rate_match = re.search(r'腐蚀速率([\d.]+)', reason)
    hcl_match = re.search(r'HCl=([\d.]+)', reason)
    wall_match = re.search(r'壁厚([\d.]+)', reason)

    mse = float(mse_match.group(1)) if mse_match else 0
    rate = float(rate_match.group(1)) if rate_match else 0.2
    hcl = float(hcl_match.group(1)) if hcl_match else 1000
    wall = float(wall_match.group(1)) if wall_match else 5.9

    # 动态建议
    if rate > 0.40:
        action = f"⚠ 腐蚀速率{rate:.2f}mm/年严重超标。建议: 1.立即安排3天内计划停炉检查 2.重点检查高温过热器入口段第1-3排管子 3.准备T22管材替换"
        urgency = "紧急"
    elif rate > 0.30:
        action = f"⚡ 腐蚀速率{rate:.2f}mm/年偏高。建议: 1.增加SNCR喷氨量抑制HCl 2.加强入炉垃圾分拣 3.一周内安排巡检"
        urgency = "关注"
    else:
        action = f"✓ 腐蚀速率{rate:.2f}mm/年在正常范围。建议: 1.保持常规巡检 2.关注HCl浓度变化趋势"
        urgency = "正常"

    if hcl > 1500:
        hcl_advice = f"HCl浓度{hcl:.0f}mg/m³偏高(正常800-1200)，疑似入炉垃圾含氯塑料过多，建议检查前端分拣"
    else:
        hcl_advice = f"HCl浓度{hcl:.0f}mg/m³在正常范围"

    # 库存检查
    stock = check_stock("T22管材", 150) if rate > 0.30 else {"status":"无需","detail":""}
    schedule = "建议7天内安排停炉检修，可合并本月计划检修窗口，减少一次额外停炉" if rate > 0.30 else ""

    return {
        "alert_id": alert_id, "work_order_id": wo.id if wo else None,
        "alert_level": alert.alert_level, "urgency": urgency,
        "phenomenon": f"AI检测: MSE={mse:.4f}，腐蚀速率{rate:.2f}mm/年，HCl={hcl:.0f}mg/m³，壁厚预测{wall:.2f}mm",
        "root_cause": f"{hcl_advice}。AI异常得分上升表明多参数关联模式偏离正常工况。",
        "action_plan": action,
        "spare_parts": "T22管材 φ51×5mm ×200m, 弯头×4, 焊接材料1套" if rate > 0.30 else "无需备件",
        "stock_check": stock["detail"],
        "scheduling": schedule,
        "similar_cases": "2024年8月新沂项目类似HCl偏高工况，停炉11天，损失约280万元" if hcl > 1500 else "暂无相似案例",
        "status": wo.status if wo else "pending",
    }


@router.put("/workorders/{wo_id}")
async def edit_workorder(
    wo_id: int, body: EditWO,
    user: dict = Depends(require_role(["admin", "检修班长", "厂长", "管理员"])),
    db: Session = Depends(get_db)
):
    """编辑工单: 指派人员/修改状态/更新方案"""
    wo = db.query(WorkOrder).filter(WorkOrder.id == wo_id).first()
    if not wo: return {"error": "工单不存在"}
    if body.assignee is not None: wo.assignee = body.assignee
    if body.status is not None: wo.status = body.status
    if body.action_plan is not None: wo.action_plan = body.action_plan
    if body.spare_parts is not None: wo.spare_parts = body.spare_parts
    if body.fault_desc is not None: wo.fault_desc = body.fault_desc
    if body.root_cause is not None: wo.root_cause = body.root_cause
    db.commit()
    return {"msg": f"工单#{wo_id}已更新", "status": wo.status}


@router.delete("/workorders/all")
async def delete_all_workorders(
    user: dict = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    """管理员一键清空所有工单"""
    db.query(WorkOrder).delete()
    db.commit()
    return {"msg": "所有工单已清空"}


@router.delete("/workorders/{wo_id}")
async def delete_workorder(
    wo_id: int,
    user: dict = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    db.query(WorkOrder).filter(WorkOrder.id == wo_id).delete()
    db.commit()
    return {"msg": f"工单#{wo_id}已删除"}


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
