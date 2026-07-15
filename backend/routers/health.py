"""设备健康度 & AI推理接口"""
from fastapi import APIRouter, Depends, Query
from typing import List
import numpy as np
import pandas as pd
from pathlib import Path

from backend.middleware.auth import require_role
from backend.routers.users import broadcast_notification
from backend.routers.alert import create_alert_internal, AutoAlertReq
from backend.models.database import SessionLocal

router = APIRouter(prefix="/api/v1/health", tags=["设备健康度"])

# ---- AI 模型加载 (启动时尝试) ----
_MODEL_READY = False
_predict_fn = None

try:
    from backend.services.inference_service import load_model as _load_ml, predict as _ml_predict
    _load_ml()
    _predict_fn = _ml_predict
    _MODEL_READY = True
    print("[AI] PatchTST 模型加载成功")
except Exception as e:
    print(f"[AI] 模型未加载(将使用Demo数据): {e}")


# ---- 设备列表 ----
_DEVICES = [
    {"id": 1, "name": "高温过热器入口段第1排", "type": "过热器",
     "health": "orange", "wall_thickness": 5.1, "original": 6.0,
     "corrosion_rate": 0.35, "rul_days": 45, "dcs_tag": "HAH10"},
    {"id": 2, "name": "高温过热器入口段第2排", "type": "过热器",
     "health": "yellow", "wall_thickness": 5.4, "original": 6.0,
     "corrosion_rate": 0.18, "rul_days": 200, "dcs_tag": "HAH10"},
    {"id": 3, "name": "中温过热器", "type": "过热器",
     "health": "green", "wall_thickness": 5.8, "original": 6.0,
     "corrosion_rate": 0.05, "rul_days": 800, "dcs_tag": "HAH20"},
    {"id": 4, "name": "低温过热器", "type": "过热器",
     "health": "green", "wall_thickness": 5.9, "original": 6.0,
     "corrosion_rate": 0.03, "rul_days": 1200, "dcs_tag": "HAH30"},
    {"id": 5, "name": "省煤器", "type": "省煤器",
     "health": "green", "wall_thickness": 5.5, "original": 6.0,
     "corrosion_rate": 0.02, "rul_days": 3000, "dcs_tag": "HAD10"},
    {"id": 6, "name": "引风机", "type": "引风机",
     "health": "green", "wall_thickness": 0, "original": 0,
     "corrosion_rate": 0, "rul_days": 9999, "dcs_tag": "HAC10"},
]


@router.get("/ai-status")
async def ai_status():
    """前端检查AI是否在线"""
    return {"ai_ready": _MODEL_READY, "model": "PatchTST (GitHub)", "params": 473907}


@router.get("/overview")
async def get_overview(
    plant_id: int = Query(1),
    time_offset: int = Query(0, description="时间偏移(小时), 0=最新, 2900=异常段"),
    user: dict = Depends(require_role(["admin", "值长", "检修班长", "厂长", "管理员"]))
) -> List[dict]:
    """设备列表 + AI推理结果(time_offset可快进到异常时段)"""
    result = [dict(d) for d in _DEVICES]

    if _MODEL_READY and _predict_fn:
        try:
            csv_path = Path(__file__).parent.parent.parent / "ml" / "simulation_data.csv"
            df = pd.read_csv(csv_path)
            cols = [c for c in df.columns if c not in
                    ('timestamp', '管壁超声厚度', '实际壁厚', '实际腐蚀速率', '标签')]
            X = df[cols].values[::60].astype(np.float32)
            total_hours = len(X)

            # time_offset: 0=最新, 正数=往前偏移
            if time_offset > 0 and time_offset + 48 < total_hours:
                idx = min(time_offset, total_hours - 48)
            else:
                idx = max(0, total_hours - 48)

            pred_main = _predict_fn(X[idx:idx+48])
            pred_normal = _predict_fn(X[100:148])

            # Demo模式: 每次请求都生成一条预警记录（time_offset!=0时模拟检测）
            if time_offset != 0:
                try:
                    db = SessionLocal()
                    create_alert_internal(db, AutoAlertReq(
                        device_id=1, device_name="高温过热器入口段",
                        alert_level=pred_main["alert_level"],
                        reason=f"{'⚠' if pred_main['alert_level']!='green' else '✓'} "
                               f"AI推理: MSE={pred_main['reconstruction_error']:.4f}(阈值0.0015)，"
                               f"腐蚀速率{pred_main['corrosion_rate']}mm/年，"
                               f"HCl={pred_main.get('hcl_conc',0):.0f}mg/m³，"
                               f"壁厚预测{pred_main['wall_thickness_pred']}mm",
                        corrosion_rate=pred_main['corrosion_rate'],
                        wall_thickness=pred_main['wall_thickness_pred'],
                        rul_days=pred_main['rul_days'],
                        ai_score=pred_main['anomaly_score'],
                        predicted_loss=420000 if pred_main['alert_level']!='green' else 0
                    ))
                    db.close()
                except Exception as e:
                    print(f"[Alert] 保存失败: {e}")
            result[0].update({
                "health": pred_main["alert_level"],
                "corrosion_rate": pred_main["corrosion_rate"],
                "rul_days": pred_main["rul_days"],
                "ai_anomaly_score": pred_main["anomaly_score"],
                "ai_reconstruction_error": pred_main["reconstruction_error"],
                "wall_thickness_ai": pred_main["wall_thickness_pred"],
                "hcl_conc": pred_main.get("hcl_conc", 0),
                "flue_temp": pred_main.get("flue_temp", 0),
                "time_offset": time_offset,
                "total_hours": total_hours,
            })

            # 设备2: 高温过热器出口段 —— 正常工况(对比参考)
            result[1]["health"] = pred_normal["alert_level"]
            result[1]["corrosion_rate"] = pred_normal["corrosion_rate"]
            result[1]["rul_days"] = pred_normal["rul_days"]
            result[1]["ai_anomaly_score"] = pred_normal["anomaly_score"]
            result[1]["wall_thickness_ai"] = pred_normal["wall_thickness_pred"]
            result[1]["hcl_conc"] = pred_normal.get("hcl_conc", 0)

            # 设备3〜6也用正常工况基线
            for i in range(2, 6):
                result[i]["ai_anomaly_score"] = pred_normal["anomaly_score"]
                result[i]["corrosion_rate"] = pred_normal["corrosion_rate"] * (0.3 + i * 0.1)
        except Exception as e:
            print(f"[AI] 推理失败: {e}")

    return result


@router.get("/device/{device_id}")
async def get_device_detail(
    device_id: int,
    time_range: str = Query("7d"),
    user: dict = Depends(require_role(["admin", "值长", "检修班长", "厂长", "管理员"]))
) -> dict:
    dev = next((d for d in _DEVICES if d["id"] == device_id), None)
    if not dev:
        return {"error": "设备不存在"}
    import random
    random.seed(device_id)
    history = []
    wall = dev["original"] if dev["original"] > 0 else 6.0
    for i in range(180):
        wall -= dev["corrosion_rate"] / 365 + random.uniform(-0.001, 0.003)
        history.append({"day": i + 1, "wall_thickness": round(max(wall, 0.1), 2)})
    return {**dev, "history": history}


@router.post("/ai/predict")
async def ai_predict_endpoint(
    user: dict = Depends(require_role(["admin", "值长", "检修班长", "厂长", "管理员"]))
) -> dict:
    """手动触发AI推理 —— 返回最新预测结果"""
    if not _MODEL_READY or not _predict_fn:
        return {"error": "AI模型未加载, 请确保已运行 ml/train.py"}

    csv_path = Path(__file__).parent.parent.parent / "ml" / "simulation_data.csv"
    df = pd.read_csv(csv_path)
    cols = [c for c in df.columns if c not in
            ('timestamp', '管壁超声厚度', '实际壁厚', '实际腐蚀速率', '标签')]
    X = df[cols].values[::60].astype(np.float32)
    window = X[-48:]
    return _predict_fn(window)
