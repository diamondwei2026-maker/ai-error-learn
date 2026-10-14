"""用户体系测试公共夹具（独立 SQLite + 微信服务替身）。"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.services.wechat_service import WechatService

TEST_JWT_SECRET = "test-secret"


@pytest.fixture()
def settings(tmp_path) -> Settings:
    return Settings(
        jwt_secret=TEST_JWT_SECRET,
        wechat_appid="wx-test",
        wechat_app_secret="test-app-secret",
        database_url=f"sqlite:///{(tmp_path / 'test.db').as_posix()}",
        avatar_max_bytes=1024,
        auth_required=True,
        uploads_root=str(tmp_path / "uploads"),
    )


@pytest.fixture()
def client(settings) -> TestClient:
    app = create_app(settings)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def stub_wechat(monkeypatch):
    """替换 WechatService.code2session，避免真实网络请求。"""
    state = {"openid": "openid-1", "unionid": None}

    def fake_code2session(self, code):
        if code == "bad-code":
            from app.errors import CODE_WECHAT_CODE_INVALID, WechatLoginError

            raise WechatLoginError(CODE_WECHAT_CODE_INVALID, "微信登录凭证无效，请重试")
        return {"openid": state["openid"], "unionid": state["unionid"]}

    monkeypatch.setattr(WechatService, "code2session", fake_code2session)
    return state


def login_headers(client: TestClient, code: str = "ok-code") -> dict:
    resp = client.post("/api/v1/auth/login", json={"code": code})
    assert resp.status_code == 200, resp.text
    token = resp.json()["data"]["accessToken"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def auth_headers(client, stub_wechat) -> dict:
    return login_headers(client)
