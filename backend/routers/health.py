"""设备健康度 & AI实时推理 —— 独立仿真实例"""
from fastapi import APIRouter, Depends, Query
from typing import List
import numpy as np
import datetime
from backend.middleware.auth import require_role
from backend.routers.alert import create_alert_internal, AutoAlertReq
from backend.models.database import SessionLocal
from backend.models.tables import AlertLog, ALL_ROLES, SUPERVISOR_ROLES
from backend.services.realtime_sim import Simulation
from ml.physics import calculate_rul

router = APIRouter(prefix="/api/v1/health", tags=["设备健康度"])

_MODEL_READY = False; _predict_fn = None
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
    danger: bool = Query(False, description="危险模式——延长异常期+提高A"),
    user: dict = Depends(require_role(ALL_ROLES))
) -> List[dict]:
    global _last_hour, _sim
    result = [dict(d) for d in _DEV]

    if reset: _sim = Simulation()
    _sim.danger = danger  # 危险模式标记
    if advance > 0: _sim.advance_to(_sim.hours + advance)
    elif _sim.hours < 48: _sim.advance_to(48)  # 首次自动初始化
    window, hist = _sim.window(48)
    h = _sim.hours; last = hist[-1]

    if _MODEL_READY and _predict_fn:
        pred = _predict_fn(window)
        # BIZ-008: DB 唯一约束 (device_id, alert_hour) 自动去重, 替代 _last_hour 全局变量
        # 同小时重复轮询时 IntegrityError 静默忽略, 重启后可继续推进
        try:
            db = SessionLocal()
            create_alert_internal(db, AutoAlertReq(
                device_id=1, device_name="高温过热器(入口)",
                alert_level=pred["alert_level"],
                reason=f"{'⚠' if pred['alert_level']!='green' else '✓'} AI: MSE={pred['reconstruction_error']:.4f} 腐蚀{pred['corrosion_rate']}mm/年 HCl={pred.get('hcl_conc',0):.0f}mg/m³ 壁厚{pred['wall_thickness_pred']}mm",
                corrosion_rate=pred['corrosion_rate'], wall_thickness=pred['wall_thickness_pred'],
                rul_days=pred['rul_days'], ai_score=pred['anomaly_score'],
                predicted_loss=420000 if pred['alert_level']!='green' else 0,
                alert_hour=_sim.hours))
            db.close()
        except Exception as e:
            if "Duplicate" not in str(e) and "duplicate" not in str(e):
                print(f"[Alert] {e}")
        # RUL 速率: 壁厚<4.5mm时用最近720h(30天)滑动窗口最高速率(保守),
        #           而非全历史max——全历史max在危险工况后永久锁定在峰值,
        #           导致RUL被冻住不再更新(每步变化<0.001天, round后不动)。
        #           正常运行时720h≈30天足够覆盖异常段; 超出30天则回到当前速率。
        rate_48h = np.mean([x["r"] for x in hist[-48:]] or [0.01])
        rate_720h = max((x["r"] for x in _sim.history[-720:]), default=rate_48h)
        rate_rul = rate_720h if _sim.wall < 4.5 else rate_48h
        rul_sim = calculate_rul(_sim.wall, rate_rul)
        # AI 推断的 RUL (基于基准A, 不含异常加速信息)
        rul_ai = {"rul_days": pred["rul_days"],
                  "rul_low_days": pred.get("rul_low_days", 0),
                  "rul_high_days": pred.get("rul_high_days", 0)}

        result[0].update({"health":pred["alert_level"],
            "ai_anomaly_score":pred["anomaly_score"],
            "ai_reconstruction_error":pred["reconstruction_error"],
            "corrosion_rate":last["r"],
            "wall_thickness_ai":round(_sim.wall, 2),  # 持久仿真实例的累计壁厚
            "sim_hours":_sim.hours,
            "rul_days":rul_sim["rul_days"],
            "rul_low_days":rul_sim["rul_low_days"],
            "rul_high_days":rul_sim["rul_high_days"],
            "rul_ai_days":rul_ai["rul_days"],           # AI推断RUL——对比参考
            "data_source":"ai_inference",               # BIZ-006: 数据来源标注
            "hcl_conc":last["hcl"],"flue_temp":last["t"]})
    else:
        rul_fallback = calculate_rul(_sim.wall, last["r"])
        result[0].update({"health":"yellow" if last["r"]>.3 else "green",
            "ai_anomaly_score":0.15,"corrosion_rate":last["r"],
            "wall_thickness_ai":round(_sim.wall,2),
            "rul_days":rul_fallback["rul_days"],
            "rul_low_days":rul_fallback["rul_low_days"],
            "rul_high_days":rul_fallback["rul_high_days"],
            "data_source":"physics_simulation",
            "hcl_conc":last["hcl"],"flue_temp":last["t"]})
    # 设备2-6: 以6.0mm原壁厚为基准减去各自位置的腐蚀量（越靠近炉膛腐蚀越快）
    base_wall = 6.0  # 原始壁厚基准
    corrosion_factors = [1.0, 0.85, 0.65, 0.45, 0.30, 0.15]  # 入口→出口→中→低→省→风机
    # 入口腐蚀量 = 6.0 - _sim.wall，其他按比例递减
    entry_loss = max(0, 6.0 - _sim.wall)
    health_levels = ["yellow","green","green","green","green","green"]
    if last["r"] > 2.0:
        health_levels = ["yellow","yellow","yellow","green","green","green"]
    for i in range(1,6):
        w = round(base_wall - entry_loss * corrosion_factors[i], 2)
        r = round(last["r"] * (1.0 - i*0.15), 4)
        result[i].update({"health":health_levels[i],
            "ai_anomaly_score":round(0.05+i*0.02,4),
            "corrosion_rate":r,
            "wall_thickness_ai":w,
            "hcl_conc":last["hcl"],"flue_temp":last["t"],
            "data_source":"heuristic_estimate",         # BIZ-006: 设备2-6为经验估算, 非AI推导
            "corrosion_factor":corrosion_factors[i]})
    result[0]["trend"] = [{"h":x["h"],"w":x["w"],"hcl":x["hcl"],"r":x["r"]} for x in hist[-200:]]
    return result

@router.put("/alerts/{alert_id}/resolve")
async def resolve(alert_id: int, user: dict = Depends(require_role(SUPERVISOR_ROLES))):
    db = SessionLocal(); a = db.query(AlertLog).filter(AlertLog.id==alert_id).first()
    if a: a.status="resolved"; a.close_time=datetime.datetime.now(); db.commit()
    db.close(); return {"msg":f"预警{alert_id}已处理"}
