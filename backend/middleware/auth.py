"""JWT认证 + RBAC权限校验中间件"""
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from typing import List
import redis.asyncio as aioredis

from backend.config import settings

security = HTTPBearer()

# 模块级共享客户端 —— redis-py 内置连接池, 全应用复用而非每请求新建 (SEC-015)
_redis_client: aioredis.Redis | None = None


def get_redis_client() -> aioredis.Redis:
    """懒加载共享 Redis 客户端 (测试中可替换此模块变量注入 FakeRedis)"""
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


async def get_redis():
    """FastAPI 依赖: 注入共享 Redis 客户端 (勿在调用方 close, 由应用生命周期管理)"""
    yield get_redis_client()


async def decode_token(token: str) -> dict:
    """解码JWT, 验证签名和过期"""
    try:
        payload = jwt.decode(token, settings.jwt_secret,
                             algorithms=[settings.jwt_algorithm])
        return payload  # { user_id, username, role, exp, iat }
    except JWTError:
        raise HTTPException(status_code=401, detail="无效或已过期的token")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """从请求中提取当前用户信息 (所有受保护路由自动调用)
    先验签再查黑名单: 无效token直接401, 不浪费Redis往返 (SEC-001)"""
    token = credentials.credentials
    payload = await decode_token(token)

    if await get_redis_client().exists(f"blacklist:{token}"):
        raise HTTPException(status_code=401, detail="token已被登出")

    return payload


def require_role(allowed_roles: List[str]):
    """
    RBAC权限检查装饰器工厂
    用法: require_role(ALL_ROLES) / require_role(SUPERVISOR_ROLES) / require_role(ADMIN_ONLY)
    角色组常量统一定义在 backend/models/tables.py (SEC-002: 全英文enum, 禁止硬编码中文角色)
    """
    async def role_checker(user: dict = Depends(get_current_user)):
        if user.get("role") not in allowed_roles:
            raise HTTPException(status_code=403,
                                detail=f"角色'{user.get('role')}'无权执行此操作")
        return user
    return role_checker
