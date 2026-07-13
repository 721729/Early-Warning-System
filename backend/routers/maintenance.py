"""运维建议 & 工单接口"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from backend.middleware.auth import require_role

router = APIRouter(prefix="/api/v1/maintenance", tags=["运维建议"])


class AutoCreateWO(BaseModel):
    alert_id: int


@router.get("/advice/{alert_id}")
async def get_advice(
    alert_id: int,
    user: dict = Depends(require_role(["值长", "检修班长", "厂长", "管理员"]))
):
    return {
        "alert_id": alert_id,
        "phenomenon": "高温过热器入口段第1排HCl浓度连续48小时超出正常基线30%, "
                      "壁温波动增大, 腐蚀速率从0.15mm/年加速至0.35mm/年",
        "root_cause": "近期入炉垃圾氯含量偏高, 导致烟气HCl浓度持续上升。"
                      "高温过热器入口段烟温560°C, 处于HCl高温腐蚀活跃区间",
        "action_plan": "1. 检查入炉垃圾分拣质量, 减少含氯塑料比例\n"
                       "2. 增加SNCR喷氨量至正常值的1.3倍, 抑制烟气HCl浓度\n"
                       "3. 安排下周停炉, 检查过热器入口段管壁, 视情更换第1-3排管子",
        "spare_parts": "T22管材 φ51×5mm × 200m, 弯头 ×4, 焊接材料1套",
        "similar_cases": "2024年8月新沂项目类似工况, HCl偏高持续10天后爆管, "
                         "停炉11天, 更换过热器入口段2排管子, 损失约280万元"
    }


@router.post("/workorder/auto_create")
async def auto_create_workorder(
    body: AutoCreateWO,
    user: dict = Depends(require_role(["检修班长", "厂长", "管理员"]))
):
    return {
        "work_order_id": 2026001,
        "status": "draft",
        "message": "工单已自动生成, 请确认后下发",
        "fault_desc": "高温过热器入口段第1排腐蚀加速",
        "assignee": "待指派",
    }
