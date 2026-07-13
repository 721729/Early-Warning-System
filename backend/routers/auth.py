"""认证路由: 登录 / 登出"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import redis.asyncio as aioredis

from backend.config import settings
from backend.models.database import get_db
from backend.models.tables import User
from backend.middleware.auth import get_current_user

router = APIRouter(prefix="/api/v1/auth", tags=["认证"])
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    user: dict


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(
        User.username == req.username,
        User.is_active == True
    ).first()
    if not user or not pwd_ctx.verify(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    now = datetime.utcnow()
    access_payload = {
        "user_id": user.id,
        "username": user.username,
        "role": user.role.value if hasattr(user.role, "value") else user.role,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
        "iat": now,
    }
    refresh_payload = {**access_payload,
                       "exp": now + timedelta(minutes=settings.refresh_token_expire_minutes)}

    access_token = jwt.encode(access_payload, settings.jwt_secret,
                              algorithm=settings.jwt_algorithm)
    refresh_token = jwt.encode(refresh_payload, settings.jwt_secret,
                               algorithm=settings.jwt_algorithm)

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user={"id": user.id, "username": user.username,
              "role": access_payload["role"], "real_name": user.real_name}
    )


@router.post("/logout")
async def logout(user: dict = Depends(get_current_user)):
    return {"msg": "登出成功"}
