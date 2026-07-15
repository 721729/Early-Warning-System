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
        # 回退到最新一条预警
        alert = db.query(AlertLog).order_by(AlertLog.id.desc()).first()
    if not alert:
        return {"alert_id": alert_id, "phenomenon": "暂无预警记录，请先在异常段触发预警"}

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

    # ── 交叉分析：腐蚀速率 × HCl × 壁厚 × 多参数 ──
    wall_pct = (wall - 3.0) / 3.0 * 100  # 壁厚剩余百分比
    rate_level = "严重" if rate > 3.0 else "偏高" if rate > 1.5 else "正常"
    hcl_level = "严重超标" if hcl > 1800 else "偏高" if hcl > 1500 else "正常"
    wall_level = "危险" if wall_pct < 50 else "预警" if wall_pct < 75 else "安全"

    # 根因分析: 根据HCl和腐蚀速率的组合判断
    if hcl > 1500 and rate > 1.5:
        root = (f"HCl浓度{hcl:.0f}mg/m³（{hcl_level}）与腐蚀速率{rate:.2f}mm/年（{rate_level}）"
                f"同时异常，高氯腐蚀正在加速管壁减薄。入炉垃圾含氯塑料比例偏高是主因，"
                f"炉膛温度处于HCl高温腐蚀活跃区间（500-650°C），"
                f"加剧了腐蚀进程。壁厚剩余{wall_pct:.0f}%（{wall_level}）。")
    elif hcl > 1500:
        root = (f"HCl浓度{hcl:.0f}mg/m³（{hcl_level}），但腐蚀速率{rate:.2f}mm/年尚在可控范围。"
                f"建议在腐蚀加速前采取预防措施，避免进入高氯-高温耦合腐蚀阶段。")
    elif rate > 1.5:
        root = (f"腐蚀速率{rate:.2f}mm/年（{rate_level}），HCl浓度{hcl:.0f}mg/m³正常。"
                f"腐蚀加速可能由其他因素驱动（管材老化、局部过热），建议停炉时取样做金相分析。")
    else:
        root = (f"HCl浓度{hcl:.0f}mg/m³（{hcl_level}），腐蚀速率{rate:.2f}mm/年（{rate_level}），"
                f"壁厚剩余{wall_pct:.0f}%（{wall_level}）。当前工况整体正常。")

    # 处理方案: 根据三个维度交叉生成
    actions = []
    if rate > 3.0:
        actions.append(f"🚨 紧急：腐蚀速率{rate:.2f}mm/年严重超标，建议3天内安排计划停炉")
        actions.append("重点检查高温过热器入口段第1-3排管子，准备T22管材替换")
    elif rate > 1.5:
        actions.append(f"⚠️ 腐蚀速率{rate:.2f}mm/年偏高，建议一周内安排巡检")
        actions.append("增加SNCR喷氨量至正常值1.3倍以抑制烟气HCl浓度")
    else:
        actions.append(f"腐蚀速率{rate:.2f}mm/年正常，保持常规巡检周期")

    if hcl > 1500:
        actions.append("检查入炉垃圾前端分拣质量，重点排查含氯塑料混入比例")
    if wall_pct < 60:
        actions.append(f"壁厚仅剩{wall_pct:.0f}%，提前采购备件并规划下月停炉窗口")
    if mse > 0.0005:
        actions.append("AI重建误差显著升高——多参数关联模式已偏离正常，即使单参数未超标也应关注")

    action = "。".join(actions) + "。"

    # 备件建议
    if rate > 1.5:
        parts = f"T22管材 φ51×5mm ×200m, 弯头×4, 焊接材料1套（壁厚剩余{wall_pct:.0f}%）"
    else:
        parts = "无需备件"

    # 排程建议
    if rate > 3.0:
        schedule = "建议3天内停炉，本次可合并执行月度计划检修，减少一次额外停炉损失"
    elif rate > 1.5:
        schedule = f"建议7-14天内安排停炉检查，壁厚剩余{wall_pct:.0f}%尚有安全裕度"
    else:
        schedule = ""

    # 历史案例
    if hcl > 1500 and rate > 1.5:
        cases = ("2024年8月新沂项目：HCl偏高持续10天后爆管，停炉11天，损失约280万元。"
                 "本次HCl浓度与腐蚀速率组合与新沂案例相似，建议重视。")
    elif hcl > 1500:
        cases = "2024年8月新沂项目类似HCl偏高工况，通过调整垃圾分拣和增加喷氨控制了腐蚀。"
    else:
        cases = "暂无高度相似案例"

    stock = check_stock("T22管材", 150) if rate > 1.5 else {"status":"无需","detail":""}

    return {
        "alert_id": alert_id, "work_order_id": wo.id if wo else None,
        "alert_level": alert.alert_level,
        "urgency": "紧急" if rate > 3.0 else "关注" if rate > 1.5 else "正常",
        "phenomenon": (f"AI检测异常: 重建MSE={mse:.4f}（阈值2.08×10⁻⁴），"
                       f"腐蚀速率{rate:.2f}mm/年（{rate_level}），"
                       f"HCl={hcl:.0f}mg/m³（{hcl_level}），"
                       f"壁厚预测{wall:.2f}mm（剩余{wall_pct:.0f}%）"),
        "root_cause": root,
        "action_plan": action,
        "spare_parts": parts,
        "stock_check": stock["detail"],
        "scheduling": schedule,
        "similar_cases": cases,
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
