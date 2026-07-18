"""备件库存管理 —— admin可编辑"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from typing import List
import html

router = APIRouter(prefix="/api/v1/inventory", tags=["备件库存"])

from backend.middleware.auth import require_role
from backend.models.tables import ALL_ROLES, ADMIN_ONLY

# Demo库存数据（Pilot阶段接MySQL）
_stock = [
    {"id":1,"name":"T22管材 φ51×5mm","type":"管材","qty":200,"unit":"m","min_stock":50,"location":"A区-3架"},
    {"id":2,"name":"TP347H管材 φ51×5mm","type":"管材","qty":80,"unit":"m","min_stock":30,"location":"A区-4架"},
    {"id":3,"name":"过热器弯头 90°","type":"配件","qty":12,"unit":"个","min_stock":4,"location":"B区-1架"},
    {"id":4,"name":"焊接材料套装","type":"耗材","qty":5,"unit":"套","min_stock":2,"location":"C区-2架"},
    {"id":5,"name":"超声壁厚探头","type":"仪表","qty":3,"unit":"个","min_stock":1,"location":"D区-1架"},
    {"id":6,"name":"密封垫片 DN50","type":"配件","qty":40,"unit":"片","min_stock":20,"location":"B区-3架"},
]

class StockEdit(BaseModel):
    qty: int | None = None
    min_stock: int | None = None
    location: str | None = None

    @field_validator('qty','min_stock')
    @classmethod
    def check_positive(cls,v):
        if v is not None and v < 0: raise HTTPException(422,"数量不能为负")
        return v


@router.get("/list")
async def list_inventory(
    user: dict = Depends(require_role(ALL_ROLES))
) -> List[dict]:
    """所有用户可查看"""
    return _stock


@router.put("/{item_id}")
async def edit_inventory(
    item_id: int, body: StockEdit,
    user: dict = Depends(require_role(ADMIN_ONLY))
):
    """仅admin可编辑"""
    for s in _stock:
        if s["id"] == item_id:
            if body.qty is not None: s["qty"] = body.qty
            if body.min_stock is not None: s["min_stock"] = body.min_stock
            if body.location is not None: s["location"] = html.escape(str(body.location)[:32])
            return {"msg":"更新成功","item":s}
    raise HTTPException(404,"备件不存在")


def check_stock(part_name: str, need_qty: float = 150) -> dict:
    """供运维建议调用——检查库存是否充足"""
    for s in _stock:
        if part_name in s["name"]:
            if s["qty"] >= need_qty:
                return {"status":"充足","detail":f"{s['name']}库存{s['qty']}{s['unit']}，本次需{need_qty}{s['unit']}，库存充足"}
            else:
                shortage = need_qty - s["qty"]
                return {"status":"不足","detail":f"{s['name']}库存仅{s['qty']}{s['unit']}，本次需{need_qty}{s['unit']}，短缺{shortage}{s['unit']}，请提前采购"}
    return {"status":"未知","detail":f"未找到{part_name}库存记录"}
