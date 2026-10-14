"""用户资料接口单测（TDD）。"""

from __future__ import annotations


def test_me_requires_auth(client):
    resp = client.get("/api/v1/user/me")
    assert resp.status_code == 401
    assert resp.json()["code"] == 2001


def test_me_returns_current_user(client, auth_headers):
    resp = client.get("/api/v1/user/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["user"]["openid"] == "openid-1"


def test_update_nickname_persists(client, auth_headers):
    resp = client.patch("/api/v1/user/me", json={"nickname": "  小错  "}, headers=auth_headers)
    assert resp.json()["data"]["user"]["nickname"] == "小错"
    again = client.get("/api/v1/user/me", headers=auth_headers)
    assert again.json()["data"]["user"]["nickname"] == "小错"


def test_update_nickname_too_long_returns_2005(client, auth_headers):
    resp = client.patch("/api/v1/user/me", json={"nickname": "x" * 33}, headers=auth_headers)
    assert resp.json()["code"] == 2005


def test_avatar_upload_success(client, auth_headers):
    resp = client.post(
        "/api/v1/user/avatar",
        files={"file": ("a.png", b"\x89PNG" + b"x" * 64, "image/png")},
        headers=auth_headers,
    )
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["user"]["avatarUrl"].startswith("/static/avatars/")


def test_avatar_non_image_returns_2006(client, auth_headers):
    resp = client.post(
        "/api/v1/user/avatar",
        files={"file": ("a.txt", b"hello", "text/plain")},
        headers=auth_headers,
    )
    assert resp.json()["code"] == 2006


def test_avatar_too_large_returns_2006(client, auth_headers):
    # 夹具中 avatar_max_bytes=1024
    resp = client.post(
        "/api/v1/user/avatar",
        files={"file": ("a.png", b"x" * 2048, "image/png")},
        headers=auth_headers,
    )
    assert resp.json()["code"] == 2006


def test_delete_account_clears_cloud_data(client, auth_headers, stub_wechat):
    item = {
        "id": "q1",
        "content": "题干",
        "answer": "答案",
        "createdAt": 1,
        "updatedAt": 1,
        "deleted": False,
    }
    client.post("/api/v1/sync/push", json={"items": [item]}, headers=auth_headers)

    resp = client.post("/api/v1/user/delete", headers=auth_headers)
    assert resp.json()["data"]["deleted"] is True

    # 用户已删除 → 旧 token 失效
    assert client.get("/api/v1/user/me", headers=auth_headers).json()["code"] == 2002

    # 重新登录（同一 openid）后为全新账号，同步数据为空
    session = client.post("/api/v1/auth/login", json={"code": "c"}).json()["data"]
    new_headers = {"Authorization": f"Bearer {session['accessToken']}"}
    pull = client.get("/api/v1/sync/pull", headers=new_headers).json()["data"]
    assert pull["items"] == []
