"""登录/续期接口单测（TDD）。"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from tests.conftest import login_headers


def _app_with(tmp_path, **overrides):
    base = dict(
        jwt_secret="test-secret",
        wechat_appid="wx-test",
        wechat_app_secret="test-app-secret",
        database_url=f"sqlite:///{(tmp_path / 'auth.db').as_posix()}",
        uploads_root=str(tmp_path / "uploads"),
    )
    base.update(overrides)
    return create_app(Settings(**base))


def test_login_success_returns_tokens_and_user(client, stub_wechat):
    resp = client.post("/api/v1/auth/login", json={"code": "ok-code"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    data = body["data"]
    assert data["accessToken"]
    assert data["refreshToken"]
    assert data["accessExpireAt"] > 0
    assert data["user"]["openid"] == "openid-1"
    assert data["user"]["nickname"] is None


def test_login_reuses_same_user_for_same_openid(client, stub_wechat):
    first = client.post("/api/v1/auth/login", json={"code": "c"}).json()["data"]["user"]["id"]
    second = client.post("/api/v1/auth/login", json={"code": "c"}).json()["data"]["user"]["id"]
    assert first == second


def test_login_without_wechat_secret_returns_2003(tmp_path):
    app = _app_with(tmp_path, wechat_app_secret="")
    with TestClient(app) as test_client:
        resp = test_client.post("/api/v1/auth/login", json={"code": "c"})
    assert resp.json()["code"] == 2003


def test_login_without_jwt_secret_returns_2003(tmp_path):
    app = _app_with(tmp_path, jwt_secret="")
    with TestClient(app) as test_client:
        resp = test_client.post("/api/v1/auth/login", json={"code": "c"})
    assert resp.json()["code"] == 2003


def test_login_with_invalid_wechat_code_returns_2004(client, stub_wechat):
    resp = client.post("/api/v1/auth/login", json={"code": "bad-code"})
    assert resp.json()["code"] == 2004


def test_refresh_returns_new_tokens(client, stub_wechat):
    session = client.post("/api/v1/auth/login", json={"code": "c"}).json()["data"]
    resp = client.post("/api/v1/auth/refresh", json={"refreshToken": session["refreshToken"]})
    assert resp.status_code == 200
    assert resp.json()["data"]["accessToken"]


def test_refresh_with_access_token_rejected(client, stub_wechat):
    session = client.post("/api/v1/auth/login", json={"code": "c"}).json()["data"]
    resp = client.post("/api/v1/auth/refresh", json={"refreshToken": session["accessToken"]})
    assert resp.status_code == 401
    assert resp.json()["code"] == 2002


def test_refresh_with_garbage_rejected(client):
    resp = client.post("/api/v1/auth/refresh", json={"refreshToken": "garbage"})
    assert resp.status_code == 401
    assert resp.json()["code"] == 2002


def test_login_headers_helper_works(client, stub_wechat):
    headers = login_headers(client)
    assert headers["Authorization"].startswith("Bearer ")
