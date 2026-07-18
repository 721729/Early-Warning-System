"""P0-1 (SEC-002): RBAC 角色 × 接口 允许/拒绝矩阵"""
from datetime import datetime, timedelta

import pytest
from jose import jwt

from backend.config import settings
from backend.models.tables import ADMIN_ONLY, ALL_ROLES, SUPERVISOR_ROLES

ROLES = ["admin", "plant_manager", "maintenance_lead", "operator"]


def make_token(role: str) -> str:
    """直接签发JWT, 绕过登录 — 单独验证装饰器行为 (登录路径由 test_auth 覆盖)"""
    now = datetime.utcnow()
    return jwt.encode({"user_id": 999, "username": f"mx_{role}", "role": role,
                       "exp": now + timedelta(minutes=30), "iat": now},
                      settings.jwt_secret, algorithm=settings.jwt_algorithm)


def hdr(role):
    return {"Authorization": f"Bearer {make_token(role)}"}


# (method, path, json body, 允许角色) —— 与 backend/models/tables.py 角色组一一对应
MATRIX = [
    ("GET",    "/api/v1/health/overview",          None,                              ALL_ROLES),
    ("GET",    "/api/v1/alert/active",             None,                              ALL_ROLES),
    ("GET",    "/api/v1/alert/history",            None,                              ALL_ROLES),
    ("POST",   "/api/v1/alert/1/confirm",          {"confirm_by": "t", "action": "a"}, SUPERVISOR_ROLES),
    ("PUT",    "/api/v1/alert/1",                  {"reason": "r"},                   SUPERVISOR_ROLES),
    ("DELETE", "/api/v1/alert/all",                None,                              ADMIN_ONLY),
    ("GET",    "/api/v1/maintenance/workorders",   None,                              ADMIN_ONLY),
    ("GET",    "/api/v1/maintenance/advice/1",     None,                              ALL_ROLES),
    ("PUT",    "/api/v1/maintenance/workorders/1", {"assignee": "t"},                 SUPERVISOR_ROLES),
    ("GET",    "/api/v1/predict/trend/1",          None,                              ALL_ROLES),
    ("GET",    "/api/v1/inventory/list",           None,                              ALL_ROLES),
    ("PUT",    "/api/v1/inventory/1",              {"qty": 200},                      ADMIN_ONLY),
    ("GET",    "/api/v1/users",                    None,                              ADMIN_ONLY),
    ("POST",   "/api/v1/notifications",            {"content": "矩阵测试"},            ADMIN_ONLY),
    ("GET",    "/api/v1/notifications",            None,                              ALL_ROLES),
]


@pytest.mark.parametrize("method,path,body,allowed", MATRIX,
                         ids=[f"{m}:{p}" for m, p, *_ in MATRIX])
@pytest.mark.parametrize("role", ROLES)
def test_role_endpoint_matrix(client, role, method, path, body, allowed):
    resp = client.request(method, path, json=body, headers=hdr(role))
    if role in allowed:
        assert resp.status_code != 403, \
            f"{role} 应可访问 {method} {path}, 实际 {resp.status_code}: {resp.text[:120]}"
    else:
        assert resp.status_code == 403, \
            f"{role} 应被拒绝 {method} {path}, 实际 {resp.status_code}"


@pytest.mark.parametrize("legacy_role", ["管理员", "厂长", "检修班长", "值长"])
def test_legacy_chinese_role_token_rejected(client, legacy_role):
    """SEC-002 回归护栏: 旧中文角色token不再被任何接口接受"""
    assert client.get("/api/v1/inventory/list",
                      headers=hdr(legacy_role)).status_code == 403
