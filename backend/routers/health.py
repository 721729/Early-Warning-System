"""设备健康度 & AI实时推理 —— 独立仿真实例"""
from fastapi import APIRouter, Depends, Query
from typing import List
import numpy as np
import datetime
from backend.middleware.auth import require_role
from backend.routers.alert import create_alert_internal, AutoAlertReq
from backend.models.database import SessionLocal
from backend.models.tables import AlertLog
from backend.services.realtime_sim import Simulation

router = APIRouter(prefix="/api/v1/health", tags=["设备健康度"])

_MODEL_READY = False; _predict_fn = None; _last_hour = -999
_sim = Simulation()  # 持久仿真实例，启动时创建

try:
    from backend.services.inference_service import load_model as _lm, predict as _pr
    _lm(); _predict_fn = _pr; _MODEL_READY = True; print("[AI] OK")
except Exception as e: print(f"[AI] {e}")

_DEV = [{"id":1,"name":"高温过热器(入口)","type":"过热器","original":6.0},
        {"id":2,"name":"高温过热器(出口)","type":"过热器","original":6.0},
        {"id":3,"name":"中温过热器","type":"过热器","original":6.0},
        {"id":4,"name":"低温过热器","type":"过热器","original":6.0},
        {"id":5,"name":"省煤器","type":"省煤器","original":6.0},
        {"id":6,"name":"引风机","type":"引风机","original":0}]

@router.get("/ai-status")
async def ai_status(): return {"ai_ready": _MODEL_READY}

@router.get("/overview")
async def overview(
    plant_id: int = Query(1), advance: int = Query(0, description="推进小时数，0=不推进"),
    reset: bool = Query(False, description="重置仿真"),
    user: dict = Depends(require_role(["admin","值长","检修班长","厂长","管理员"]))
) -> List[dict]:
    global _last_hour, _sim
    result = [dict(d) for d in _DEV]

    if reset: _sim = Simulation()  # 重置
    if advance > 0: _sim.advance_to(_sim.hours + advance)
    elif _sim.hours < 48: _sim.advance_to(48)  # 首次自动初始化
    window, hist = _sim.window(48)
    h = _sim.hours; last = hist[-1]

    if _MODEL_READY and _predict_fn:
        pred = _predict_fn(window)
        if h != _last_hour:
            _last_hour = h
            try:
                db = SessionLocal()
                create_alert_internal(db, AutoAlertReq(device_id=1, device_name="高温过热器(入口)",
                    alert_level=pred["alert_level"],
                    reason=f"{'⚠' if pred['alert_level']!='green' else '✓'} AI: MSE={pred['reconstruction_error']:.4f} 腐蚀{pred['corrosion_rate']}mm/年 HCl={pred.get('hcl_conc',0):.0f}mg/m³ 壁厚{pred['wall_thickness_pred']}mm",
                    corrosion_rate=pred['corrosion_rate'], wall_thickness=pred['wall_thickness_pred'],
                    rul_days=pred['rul_days'], ai_score=pred['anomaly_score'],
                    predicted_loss=420000 if pred['alert_level']!='green' else 0))
                db.close()
            except Exception as e: print(f"[Alert] {e}")
        result[0].update({"health":pred["alert_level"],
            "ai_anomaly_score":pred["anomaly_score"],
            "ai_reconstruction_error":pred["reconstruction_error"],
            "corrosion_rate":last["r"],
            "wall_thickness_ai":round(_sim.wall, 2),  // 持久仿真实例的累计壁厚
            "sim_hours":_sim.hours,
            "rul_days":max((_sim.wall-3.0)/max(last["r"],1e-8)*365,1),
            "hcl_conc":last["hcl"],"flue_temp":last["t"]})
    else:
        result[0].update({"health":"yellow" if last["r"]>.3 else "green",
            "ai_anomaly_score":0.15,"corrosion_rate":last["r"],
            "wall_thickness_ai":round(_sim.wall,2),"rul_days":5000,
            "hcl_conc":last["hcl"],"flue_temp":last["t"]})
    # 设备2-6
    for i in range(1,6):
        result[i].update({"health":"green","ai_anomaly_score":round(0.05+i*0.015,4),
            "corrosion_rate":round(last["r"]*(0.5+i*0.12),4),
            "wall_thickness_ai":round(_sim.wall+i*0.3,2),
            "hcl_conc":last["hcl"],"flue_temp":last["t"]})
    result[0]["trend"] = [{"h":x["h"],"w":x["w"],"hcl":x["hcl"],"r":x["r"]} for x in hist[-200:]]
    return result

@router.put("/alerts/{alert_id}/resolve")
async def resolve(alert_id: int, user: dict = Depends(require_role(["admin","检修班长","厂长","管理员"]))):
    db = SessionLocal(); a = db.query(AlertLog).filter(AlertLog.id==alert_id).first()
    if a: a.status="resolved"; a.close_time=datetime.datetime.now(); db.commit()
    db.close(); return {"msg":f"预警{alert_id}已处理"}
