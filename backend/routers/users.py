"""用户管理 & 通知 API —— 管理员专属 + XSS防护"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session
from typing import List
import html
import re

from backend.models.database import get_db
from backend.models.tables import User
from backend.middleware.auth import get_current_user, require_role
from backend.config import settings

router = APIRouter(prefix="/api/v1", tags=["用户管理 & 通知"])


# ============================================================
# XSS 输入清洗
# ============================================================
def sanitize(s: str) -> str:
    """转义HTML特殊字符, 防止XSS"""
    return html.escape(s.strip())


def safe_str(s: str, max_len: int = 64) -> str:
    """限制长度 + XSS清洗"""
    s = sanitize(s)
    if len(s) > max_len:
        raise HTTPException(status_code=422, detail=f"字段长度不能超过{max_len}个字符")
    return s


# ============================================================
# Pydantic Models
# ============================================================
class CreateUserReq(BaseModel):
    username: str
    password: str
    role: str = "operator"   # admin/plant_manager/maintenance_lead/operator
    real_name: str = ""

    @field_validator('username')
    @classmethod
    def clean_username(cls, v):
        if not re.match(r'^[a-zA-Z0-9_]{2,32}$', v.strip()):
            raise HTTPException(status_code=422, detail="工号只能包含字母、数字和下划线，长度2-32")
        return v.strip()

    @field_validator('password')
    @classmethod
    def check_password(cls, v):
        if len(v) < 6:
            raise HTTPException(status_code=422, detail="密码长度不能少于6位")
        return v

    @field_validator('role')
    @classmethod
    def clean_role(cls, v):
        allowed = {"admin", "plant_manager", "maintenance_lead", "operator"}
        if v not in allowed:
            raise HTTPException(status_code=422, detail=f"无效角色: {v}")
        return v


class UpdateUserReq(BaseModel):
    role: str | None = None
    real_name: str | None = None
    is_active: bool | None = None

    @field_validator('role')
    @classmethod
    def clean_role(cls, v):
        if v is None:
            return v
        allowed = {"admin", "plant_manager", "maintenance_lead", "operator"}
        if v not in allowed:
            raise HTTPException(status_code=422, detail=f"无效角色: {v}")
        return v


class ChangePasswordReq(BaseModel):
    old_password: str
    new_password: str

    @field_validator('new_password')
    @classmethod
    def check_new_password(cls, v):
        if len(v) < 6:
            raise HTTPException(status_code=422, detail="新密码长度不能少于6位")
        return v


class NotificationReq(BaseModel):
    content: str

    @field_validator('content')
    @classmethod
    def clean_content(cls, v):
        s = v.strip()
        if not s or len(s) > 500:
            raise HTTPException(status_code=422, detail="通知内容不能为空且不超过500字符")
        return html.escape(s)


# ============================================================
# 通知模块（内存存储, 重启清空 Demo）
# ============================================================
import datetime
_notifications: list[dict] = []


def broadcast_notification(content: str, created_by: str = "system"):
    """供其他模块调用——将预警/工单事件推送为通知"""
    n = {
        "id": len(_notifications) + 1,
        "content": html.escape(content.strip()),
        "created_by": created_by,
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    _notifications.append(n)
    return n


# 默认系统通知
_notifications = [
    {"id": 1, "content": "系统上线通知：绿电哨兵 v1.0 已部署，设备健康度监测平台正常运行。",
     "created_by": "admin", "created_at": "2026-07-15 09:00:00"},
]


@router.get("/notifications")
async def get_notifications(
    user: dict = Depends(get_current_user)
):
    """所有登录用户均可查看"""
    return sorted(_notifications, key=lambda x: x["id"], reverse=True)


@router.post("/notifications")
async def create_notification(
    req: NotificationReq,
    user: dict = Depends(require_role(["admin"]))
):
    """仅管理员可发布通知"""
    n = {
        "id": len(_notifications) + 1,
        "content": req.content,
        "created_by": user["username"],
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    _notifications.append(n)
    return n


@router.put("/notifications/{nid}")
async def edit_notification(
    nid: int,
    req: NotificationReq,
    user: dict = Depends(require_role(["admin"]))
):
    """管理员编辑通知内容"""
    for n in _notifications:
        if n["id"] == nid:
            n["content"] = req.content
            n["created_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " (已编辑)"
            return n
    raise HTTPException(status_code=404, detail="通知不存在")


@router.delete("/notifications/{nid}")
async def delete_notification(
    nid: int,
    user: dict = Depends(require_role(["admin"]))
):
    global _notifications
    _notifications = [n for n in _notifications if n["id"] != nid]
    return {"msg": "已删除"}


# ============================================================
# 用户管理（仅管理员）
# ============================================================
@router.get("/users")
async def list_users(
    user: dict = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    users = db.query(User).all()
    return [{
        "id": u.id, "username": u.username, "role": u.role,
        "real_name": u.real_name, "is_active": u.is_active,
        "created_at": str(u.created_at) if u.created_at else ""
    } for u in users]


@router.post("/users")
async def create_user(
    req: CreateUserReq,
    user: dict = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    """管理员创建新用户"""
    # 检查是否已存在
    existing = db.query(User).filter(User.username == req.username).first()
    if existing:
        raise HTTPException(status_code=409, detail="工号已存在")

    from passlib.context import CryptContext
    pwd_ctx = CryptContext(schemes=['bcrypt'], deprecated='auto')

    new_user = User(
        username=req.username,
        password_hash=pwd_ctx.hash(req.password),
        role=req.role,
        real_name=req.real_name or req.username,
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"id": new_user.id, "username": new_user.username, "msg": "创建成功"}


@router.put("/users/{uid}")
async def update_user(
    uid: int,
    req: UpdateUserReq,
    user: dict = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    """管理员编辑用户（角色、状态、姓名）"""
    target = db.query(User).filter(User.id == uid).first()
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 禁止修改自己的角色（防止把自己降级后无法管理）
    if uid == user["user_id"] and req.role is not None and req.role != "admin":
        raise HTTPException(status_code=403, detail="不能修改自己的管理员角色")

    if req.role is not None:
        target.role = req.role
    if req.real_name is not None:
        target.real_name = safe_str(req.real_name, 32)
    if req.is_active is not None:
        # 禁止禁用自己
        if uid == user["user_id"] and not req.is_active:
            raise HTTPException(status_code=403, detail="不能禁用自己的账号")
        target.is_active = req.is_active

    db.commit()
    return {"msg": "更新成功"}


@router.put("/users/{uid}/password")
async def change_user_password(
    uid: int,
    req: ChangePasswordReq,
    user: dict = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    """管理员重置任意用户密码，或用户修改自己的密码"""
    target = db.query(User).filter(User.id == uid).first()
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")

    from passlib.context import CryptContext
    pwd_ctx = CryptContext(schemes=['bcrypt'], deprecated='auto')

    # 非管理员用户只能改自己的密码，且需验证旧密码
    if user["role"] != "admin":
        if uid != user["user_id"]:
            raise HTTPException(status_code=403, detail="只能修改自己的密码")
        if not pwd_ctx.verify(req.old_password, target.password_hash):
            raise HTTPException(status_code=403, detail="旧密码错误")

    target.password_hash = pwd_ctx.hash(req.new_password)
    db.commit()
    return {"msg": "密码修改成功"}
