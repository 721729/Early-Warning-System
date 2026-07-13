"""JWT认证 + RBAC权限校验中间件"""
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from typing import List
import redis.asyncio as aioredis

from backend.config import settings

security = HTTPBearer()


async def get_redis():
    """Redis连接 (用于token黑名单)"""
    r = aioredis.from_url(settings.redis_url, decode_responses=True)
    try:
        yield r
    finally:
        await r.close()


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
    """从请求中提取当前用户信息 (所有受保护路由自动调用)"""
    token = credentials.credentials

    # 检查Redis黑名单
    r = aioredis.from_url(settings.redis_url, decode_responses=True)
    try:
        if await r.exists(f"blacklist:{token}"):
            raise HTTPException(status_code=401, detail="token已被登出")
    finally:
        await r.close()

    return await decode_token(token)


def require_role(allowed_roles: List[str]):
    """
    RBAC权限检查装饰器工厂
    用法: @require_role(["值长", "检修班长", "厂长", "管理员"])
    """
    async def role_checker(user: dict = Depends(get_current_user)):
        if user.get("role") not in allowed_roles:
            raise HTTPException(status_code=403,
                                detail=f"角色'{user.get('role')}'无权执行此操作")
        return user
    return role_checker
