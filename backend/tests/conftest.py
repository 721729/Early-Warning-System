"""测试公共设施 —— 内存SQLite + FakeRedis + 四角色种子用户
不依赖外部 MySQL/Redis, 任何环境下 .venv/bin/python -m pytest backend/tests 直接运行
"""
import time

import pytest
from fastapi.testclient import TestClient
from passlib.context import CryptContext
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import backend.middleware.auth as auth_mw
from backend.main import app
from backend.models.database import Base, get_db
from backend.models.tables import User, UserRole

TEST_PASSWORD = "Test#Pass123"
_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
_TEST_HASH = _pwd_ctx.hash(TEST_PASSWORD)  # bcrypt(cost=12) 只算一次, 全部测试复用


class FakeRedis:
    """内存版异步Redis替身 —— 只实现黑名单用到的命令"""

    def __init__(self):
        self.store = {}  # key -> (value, expire_at)

    def _alive(self, key):
        v = self.store.get(key)
        if v is None:
            return None
        value, exp = v
        if exp is not None and exp <= time.time():
            del self.store[key]
            return None
        return value

    async def exists(self, key):
        return 1 if self._alive(key) is not None else 0

    async def setex(self, key, ttl, value):
        self.store[key] = (value, time.time() + int(ttl))
        return True

    async def get(self, key):
        return self._alive(key)

    async def close(self):
        pass

    def ttl_of(self, key):
        """测试断言用: 剩余TTL秒数"""
        v = self.store.get(key)
        if not v or v[1] is None:
            return -1
        return v[1] - time.time()


@pytest.fixture()
def fake_redis(monkeypatch):
    r = FakeRedis()
    monkeypatch.setattr(auth_mw, "_redis_client", r)
    return r


@pytest.fixture()
def db_session_factory():
    engine = create_engine("sqlite://",
                           connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    # 四角色种子用户 (用户名=角色值) + 一个停用账号
    with TestingSession() as db:
        for role in UserRole:
            db.add(User(username=role.value, password_hash=_TEST_HASH,
                        role=role.value, real_name=role.display_name, is_active=True))
        db.add(User(username="disabled_user", password_hash=_TEST_HASH,
                    role=UserRole.OPERATOR.value, real_name="停用账号", is_active=False))
        db.commit()
    yield TestingSession
    engine.dispose()


@pytest.fixture()
def client(db_session_factory, fake_redis):
    def override_get_db():
        db = db_session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def login(client, username, password=TEST_PASSWORD):
    return client.post("/api/v1/auth/login",
                       json={"username": username, "password": password})


def auth_header(client, role="admin"):
    resp = login(client, role)
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}
