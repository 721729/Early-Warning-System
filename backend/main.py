#!/usr/bin/env python3
"""
绿电哨兵 —— 焚烧炉设备健康度监测平台
FastAPI 应用入口
启动: uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from backend.routers import auth, health, alert, predict, maintenance, users
from backend.config import settings

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("green-power-sentinel")

app = FastAPI(
    title="绿电哨兵 - 焚烧炉设备健康度监测平台",
    description="AI设备故障预警系统 / 高能环境产业命题赛道",
    version="1.0.0",
)

# CORS —— 开发默认localhost, 公网部署时设环境变量 CORS_ORIGINS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

# 安全响应头 —— 防点击劫持、MIME嗅探、XSS
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

app.add_middleware(SecurityHeadersMiddleware)

# 注册路由
app.include_router(auth.router)
app.include_router(health.router)
app.include_router(alert.router)
app.include_router(predict.router)
app.include_router(maintenance.router)
app.include_router(users.router)


@app.get("/")
def root():
    return {"service": "绿电哨兵API", "version": "1.0.0", "status": "running"}


@app.get("/health")
def api_health():
    return {"status": "ok"}
