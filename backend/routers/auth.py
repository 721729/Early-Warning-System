"""认证路由: 登录 / 登出"""
import time

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import redis.asyncio as aioredis

from backend.config import settings
from backend.models.database import get_db
from backend.models.tables import User
from backend.middleware.auth import get_current_user, get_redis, security

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
        "role": str(user.role),
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
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    user: dict = Depends(get_current_user),
    r: aioredis.Redis = Depends(get_redis),
):
    """登出: 当前token写入Redis黑名单, 剩余有效期内拒绝复用 (SEC-001)
    key带TTL自动过期, 不会在Redis中无限堆积"""
    token = credentials.credentials
    ttl = int(user["exp"]) - int(time.time())
    if ttl > 0:
        await r.setex(f"blacklist:{token}", ttl, "1")
    return {"msg": "登出成功"}
