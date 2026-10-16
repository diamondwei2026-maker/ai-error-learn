"""用户体系测试公共夹具（独立 SQLite + 微信服务替身）。"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.services.wechat_service import WechatService

TEST_JWT_SECRET = "test-secret"
TEST_CALLBACK_TOKEN = "test-callback-token"
TEST_PUBLIC_BASE_URL = "https://test.example.com"


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
        public_base_url=TEST_PUBLIC_BASE_URL,
        wechat_callback_token=TEST_CALLBACK_TOKEN,
    )


@pytest.fixture(autouse=True)
def stub_content_security(monkeypatch):
    """替换内容安全送检调用，避免测试真发 HTTP。

    返回值 state 可变：state["text"] / state["image"] 控制送检结论，
    state["calls"] 记录每次调用，便于断言"是否送检"。
    """
    from app.services.content_security import ContentSecurityService

    state = {"text": "pass", "image": None, "calls": []}

    def fake_check_text(self, text, openid, scene):
        state["calls"].append(("text", text, scene))
        return state["text"]

    def fake_check_image_async(self, media_url, openid, scene):
        state["calls"].append(("image", media_url, scene))
        return state["image"]

    monkeypatch.setattr(ContentSecurityService, "check_text", fake_check_text)
    monkeypatch.setattr(ContentSecurityService, "check_image_async", fake_check_image_async)
    return state


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
