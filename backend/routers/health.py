"""设备健康度 & AI实时推理 —— 内存仿真+去重预警"""
from fastapi import APIRouter, Depends, Query
from typing import List
import numpy as np
from pathlib import Path
import datetime

from backend.middleware.auth import require_role
from backend.routers.alert import create_alert_internal, AutoAlertReq
from backend.models.database import SessionLocal
from backend.models.tables import AlertLog
from backend.services import realtime_sim as sim

router = APIRouter(prefix="/api/v1/health", tags=["设备健康度"])

_MODEL_READY = False
_predict_fn = None
_last_alert_hour = -999  # 去重: 同一小时内不重复报警

try:
    from backend.services.inference_service import load_model as _load_ml, predict as _ml_predict
    _load_ml()
    _predict_fn = _ml_predict
    _MODEL_READY = True
    print("[AI] PatchTST 模型加载成功")
except Exception as e:
    print(f"[AI] 模型未加载: {e}")

_DEVICES = [
    {"id": 1, "name": "高温过热器(入口)", "type": "过热器", "original": 6.0},
    {"id": 2, "name": "高温过热器(出口)", "type": "过热器", "original": 6.0},
    {"id": 3, "name": "中温过热器", "type": "过热器", "original": 6.0},
    {"id": 4, "name": "低温过热器", "type": "过热器", "original": 6.0},
    {"id": 5, "name": "省煤器", "type": "省煤器", "original": 6.0},
    {"id": 6, "name": "引风机", "type": "引风机", "original": 0},
]


@router.get("/ai-status")
async def ai_status():
    return {"ai_ready": _MODEL_READY, "model": "PatchTST (GitHub)", "params": 473907}


@router.get("/overview")
async def get_overview(
    plant_id: int = Query(1),
    time_offset: int = Query(0, description="时间偏移: 0=最新, 2880=异常段起始"),
    user: dict = Depends(require_role(["admin", "值长", "检修班长", "厂长", "管理员"]))
) -> List[dict]:
    global _last_alert_hour
    result = [dict(d) for d in _DEVICES]

    # 实时仿真: 推进到目标时间并生成数据
    target_hour = time_offset if time_offset > 0 else sim._state["hours"] + 1
    sim.advance_to(target_hour)
    window, history = sim.generate_window(48)

    anomaly_info = sim.current_anomaly_info()
    current_hour = sim._state["hours"]

    if _MODEL_READY and _predict_fn:
        # AI推理
        pred = _predict_fn(window)

        # 去重: 同一小时内已经报过警不再重复
        if current_hour != _last_alert_hour:
            _last_alert_hour = current_hour
            try:
                db = SessionLocal()
                create_alert_internal(db, AutoAlertReq(
                    device_id=1, device_name="高温过热器(入口)",
                    alert_level=pred["alert_level"],
                    reason=f"{'⚠' if pred['alert_level']!='green' else '✓'} "
                           f"AI实时推理: MSE={pred['reconstruction_error']:.4f}，"
                           f"腐蚀速率{pred['corrosion_rate']}mm/年，"
                           f"HCl={pred.get('hcl_conc',0):.0f}mg/m³，"
                           f"壁厚{pred['wall_thickness_pred']}mm，"
                           f"异常得分{pred['anomaly_score']:.2f}",
                    corrosion_rate=pred['corrosion_rate'],
                    wall_thickness=pred['wall_thickness_pred'],
                    rul_days=pred['rul_days'],
                    ai_score=pred['anomaly_score'],
                    predicted_loss=420000 if pred['alert_level'] != 'green' else 0
                ))
                db.close()
            except Exception as e:
                print(f"[Alert] {e}")

        # 更新设备1
        result[0].update({
            "health": pred["alert_level"],
            "corrosion_rate": pred["corrosion_rate"],
            "rul_days": pred["rul_days"],
            "ai_anomaly_score": pred["anomaly_score"],
            "ai_reconstruction_error": pred["reconstruction_error"],
            "wall_thickness_ai": pred["wall_thickness_pred"],
            "hcl_conc": pred.get("hcl_conc", 0),
            "flue_temp": pred.get("flue_temp", 0),
        })
    else:
        # 无模型时用纯阿伦尼乌斯
        last = history[-1] if history else {"wall": 5.9, "rate": 0.2, "hcl": 1000, "temp": 570}
        result[0].update({
            "health": "yellow" if last["rate"] > 0.30 else "green",
            "corrosion_rate": last["rate"],
            "rul_days": max((last["wall"] - 3.0) / max(last["rate"], 1e-8) * 365, 1),
            "ai_anomaly_score": 0.5,
            "wall_thickness_ai": last["wall"],
            "hcl_conc": last["hcl"],
            "flue_temp": last["temp"],
        })

    # 设备2-5共享相同趋势
    last = history[-1] if history else {"wall": 5.9, "rate": 0.2}
    for i in range(1, 5):
        result[i].update({
            "health": "green",
            "corrosion_rate": round(last["rate"] * (0.5 + i * 0.15), 4),
            "rul_days": 1000 + i * 500,
            "wall_thickness_ai": round(last["wall"] + i * 0.3, 2),
        })

    # 附上趋势历史
    result[0]["trend_history"] = [{"hour": h["hour"], "wall": h["wall"],
                                     "hcl": h["hcl"], "rate": h["rate"]}
                                  for h in history[-200:]]

    return result


@router.put("/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: int,
    user: dict = Depends(require_role(["admin", "检修班长", "厂长", "管理员"]))
):
    """标记预警为已处理"""
    db = SessionLocal()
    alert = db.query(AlertLog).filter(AlertLog.id == alert_id).first()
    if alert:
        alert.status = "resolved"
        alert.close_time = datetime.datetime.now()
        db.commit()
    db.close()
    return {"msg": f"预警{alert_id}已处理"}
