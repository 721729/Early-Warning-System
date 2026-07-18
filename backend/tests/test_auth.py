"""P0-2 (SEC-001): 登录/登出 e2e —— 含token黑名单撤销验证"""
from backend.tests.conftest import login

PROTECTED = "/api/v1/notifications"  # 任意登录角色可访问的受保护接口 (无DB依赖)


def test_login_success(client):
    resp = login(client, "admin")
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"] and body["refresh_token"]
    assert body["user"]["role"] == "admin"


def test_login_wrong_password(client):
    assert login(client, "admin", "wrong-password").status_code == 401


def test_login_unknown_user(client):
    assert login(client, "ghost").status_code == 401


def test_login_inactive_user_rejected(client):
    assert login(client, "disabled_user").status_code == 401


def test_protected_route_requires_token(client):
    # HTTPBearer 无凭证 → 401 Not authenticated
    assert client.get(PROTECTED).status_code == 401


def test_logout_blacklists_token(client, fake_redis):
    """核心e2e: 登录 → 访问OK → 登出 → 同token再访问 → 401"""
    token = login(client, "admin").json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    assert client.get(PROTECTED, headers=headers).status_code == 200

    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 200

    # 黑名单已写入, TTL 不超过 access_token 剩余有效期 (120min)
    assert fake_redis.store.get(f"blacklist:{token}") is not None
    ttl = fake_redis.ttl_of(f"blacklist:{token}")
    assert 0 < ttl <= 120 * 60

    resp = client.get(PROTECTED, headers=headers)
    assert resp.status_code == 401
    assert "登出" in resp.json()["detail"]


def test_logout_twice_second_call_rejected(client):
    """重复登出: 第二次时token已在黑名单 → get_current_user 拦截 401"""
    token = login(client, "admin").json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 200
    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 401
