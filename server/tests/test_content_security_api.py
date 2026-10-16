"""内容安全接入单测（TDD）：昵称校验、文本预检、同步兜底、图片回调。"""

from __future__ import annotations

import hashlib

ITEM = {
    "id": "q1",
    "content": "题干",
    "answer": "答案",
    "createdAt": 1,
    "updatedAt": 1,
    "deleted": False,
}


def _sign(token: str, timestamp: str, nonce: str) -> str:
    joined = "".join(sorted([token, timestamp, nonce]))
    return hashlib.sha1(joined.encode("utf-8")).hexdigest()


def _callback_query(settings, timestamp: str = "1700000000", nonce: str = "abc") -> dict:
    return {
        "signature": _sign(settings.wechat_callback_token, timestamp, nonce),
        "timestamp": timestamp,
        "nonce": nonce,
    }


# ---------- 昵称 ----------


def test_nickname_risky_returns_2007(client, auth_headers, stub_content_security):
    stub_content_security["text"] = "risky"
    resp = client.patch("/api/v1/user/me", json={"nickname": "违规昵称"}, headers=auth_headers)
    assert resp.json()["code"] == 2007
    # 未写入
    me = client.get("/api/v1/user/me", headers=auth_headers).json()["data"]["user"]
    assert me["nickname"] is None


def test_nickname_review_passes(client, auth_headers, stub_content_security):
    stub_content_security["text"] = "review"
    resp = client.patch("/api/v1/user/me", json={"nickname": "待复审"}, headers=auth_headers)
    assert resp.json()["code"] == 0
    assert resp.json()["data"]["user"]["nickname"] == "待复审"


def test_nickname_check_skipped_degrades(client, auth_headers, stub_content_security):
    stub_content_security["text"] = "skipped"
    resp = client.patch("/api/v1/user/me", json={"nickname": "正常昵称"}, headers=auth_headers)
    assert resp.json()["code"] == 0
    assert resp.json()["data"]["user"]["nickname"] == "正常昵称"


def test_nickname_sent_with_profile_scene(client, auth_headers, stub_content_security):
    client.patch("/api/v1/user/me", json={"nickname": "小错"}, headers=auth_headers)
    text_calls = [call for call in stub_content_security["calls"] if call[0] == "text"]
    assert text_calls == [("text", "小错", 1)]


# ---------- 文本预检 ----------


def test_text_check_requires_auth(client):
    resp = client.post("/api/v1/security/text-check", json={"content": "题干"})
    assert resp.status_code == 401
    assert resp.json()["code"] == 2001


def test_text_check_risky_returns_3002(client, auth_headers, stub_content_security):
    stub_content_security["text"] = "risky"
    resp = client.post(
        "/api/v1/security/text-check",
        json={"content": "题干", "answer": "答案"},
        headers=auth_headers,
    )
    assert resp.json()["code"] == 3002


def test_text_check_passes_and_merges_fields(client, auth_headers, stub_content_security):
    resp = client.post(
        "/api/v1/security/text-check",
        json={"content": "  题干  ", "answer": "答案"},
        headers=auth_headers,
    )
    assert resp.json()["code"] == 0
    assert resp.json()["data"]["pass"] is True
    text_calls = [call for call in stub_content_security["calls"] if call[0] == "text"]
    assert text_calls == [("text", "题干\n答案", 3)]


def test_text_check_empty_text_skips_remote_call(client, auth_headers, stub_content_security):
    resp = client.post(
        "/api/v1/security/text-check", json={"content": "   ", "answer": ""}, headers=auth_headers
    )
    assert resp.json()["code"] == 0
    assert stub_content_security["calls"] == []


# ---------- 同步兜底 ----------


def test_sync_push_risky_item_rejected(client, auth_headers, stub_content_security):
    stub_content_security["text"] = "risky"
    resp = client.post("/api/v1/sync/push", json={"items": [ITEM]}, headers=auth_headers)
    body = resp.json()["data"]
    assert body["rejected"] == ["q1"]
    assert body["accepted"] == []
    # 未落库
    pull = client.get("/api/v1/sync/pull", headers=auth_headers).json()["data"]
    assert pull["items"] == []


def test_sync_push_pass_item_accepted(client, auth_headers, stub_content_security):
    resp = client.post("/api/v1/sync/push", json={"items": [ITEM]}, headers=auth_headers)
    body = resp.json()["data"]
    assert body["accepted"] == ["q1"]
    assert body["rejected"] == []
    pull = client.get("/api/v1/sync/pull", headers=auth_headers).json()["data"]
    assert [item["id"] for item in pull["items"]] == ["q1"]


def test_sync_push_tombstone_not_checked(client, auth_headers, stub_content_security):
    tombstone = {**ITEM, "id": "q9", "content": "", "answer": "", "deleted": True}
    resp = client.post("/api/v1/sync/push", json={"items": [tombstone]}, headers=auth_headers)
    assert resp.json()["data"]["accepted"] == ["q9"]
    assert [call for call in stub_content_security["calls"] if call[0] == "text"] == []


def test_sync_push_unchanged_item_not_rechecked(client, auth_headers, stub_content_security):
    client.post("/api/v1/sync/push", json={"items": [ITEM]}, headers=auth_headers)
    stub_content_security["calls"].clear()
    # 同一 updatedAt 再次上行：不应再次送检
    resp = client.post("/api/v1/sync/push", json={"items": [ITEM]}, headers=auth_headers)
    assert resp.json()["data"]["accepted"] == ["q1"]
    assert [call for call in stub_content_security["calls"] if call[0] == "text"] == []


# ---------- 图片回调 ----------


def test_callback_bad_signature_returns_403(client):
    resp = client.post(
        "/api/v1/wechat/callback",
        json={"Event": "wxa_media_check", "trace_id": "t"},
        params={"signature": "bad", "timestamp": "1", "nonce": "2"},
    )
    assert resp.status_code == 403


def test_callback_get_url_verification_echoes_echostr(client, settings):
    res = client.get(
        "/api/v1/wechat/callback",
        params={**_callback_query(settings), "echostr": "hello-echo"},
    )
    assert res.status_code == 200
    assert res.text == "hello-echo"

    bad = client.get(
        "/api/v1/wechat/callback",
        params={"signature": "bad", "timestamp": "1", "nonce": "2", "echostr": "x"},
    )
    assert bad.status_code == 403


def _upload_avatar(
    client, auth_headers, stub_content_security, trace_id, name="a.png", content_type="image/png"
):
    stub_content_security["image"] = trace_id
    resp = client.post(
        "/api/v1/user/avatar",
        files={"file": (name, b"\x89PNG" + b"x" * 64, content_type)},
        headers=auth_headers,
    )
    assert resp.json()["code"] == 0
    return resp


def test_callback_risky_removes_avatar(client, auth_headers, settings, stub_content_security):
    _upload_avatar(client, auth_headers, stub_content_security, "trace-1")
    me = client.get("/api/v1/user/me", headers=auth_headers).json()["data"]["user"]
    file_name = me["avatarUrl"].split("/")[-1].split("?")[0]
    assert (settings.avatar_dir / file_name).is_file()

    resp = client.post(
        "/api/v1/wechat/callback",
        params=_callback_query(settings),
        json={
            "Event": "wxa_media_check",
            "trace_id": "trace-1",
            "errcode": 0,
            "result": {"suggest": "risky", "label": 20002},
        },
    )
    assert resp.status_code == 200
    assert resp.text == "success"

    after = client.get("/api/v1/user/me", headers=auth_headers).json()["data"]["user"]
    assert after["avatarUrl"] is None
    assert not (settings.avatar_dir / file_name).is_file()


def test_callback_pass_keeps_avatar(client, auth_headers, settings, stub_content_security):
    _upload_avatar(client, auth_headers, stub_content_security, "trace-ok")
    client.post(
        "/api/v1/wechat/callback",
        params=_callback_query(settings),
        json={
            "Event": "wxa_media_check",
            "trace_id": "trace-ok",
            "errcode": 0,
            "result": {"suggest": "pass", "label": 100},
        },
    )
    after = client.get("/api/v1/user/me", headers=auth_headers).json()["data"]["user"]
    assert after["avatarUrl"] is not None


def test_callback_late_result_does_not_remove_new_avatar(
    client, auth_headers, settings, stub_content_security
):
    """用户换头像后，旧头像的迟到回调不得误删新头像。"""
    _upload_avatar(client, auth_headers, stub_content_security, "trace-old", name="a.png")
    _upload_avatar(
        client,
        auth_headers,
        stub_content_security,
        "trace-new",
        name="a.jpg",
        content_type="image/jpeg",
    )
    # 换头像后当前 avatar 指向 .jpg（扩展名随 content-type 变化）
    me = client.get("/api/v1/user/me", headers=auth_headers).json()["data"]["user"]
    current = me["avatarUrl"]
    assert current.startswith("/static/avatars/")

    client.post(
        "/api/v1/wechat/callback",
        params=_callback_query(settings),
        json={
            "Event": "wxa_media_check",
            "trace_id": "trace-old",
            "errcode": 0,
            "result": {"suggest": "risky", "label": 20002},
        },
    )
    after = client.get("/api/v1/user/me", headers=auth_headers).json()["data"]["user"]
    assert after["avatarUrl"] == current


def test_callback_xml_payload_is_supported(client, auth_headers, settings, stub_content_security):
    _upload_avatar(client, auth_headers, stub_content_security, "trace-xml")
    xml_body = (
        "<xml><ToUserName>gh_x</ToUserName><Event>wxa_media_check</Event>"
        "<trace_id>trace-xml</trace_id><errcode>0</errcode>"
        "<result><suggest>risky</suggest><label>20002</label></result></xml>"
    )
    resp = client.post(
        "/api/v1/wechat/callback",
        params=_callback_query(settings),
        content=xml_body.encode("utf-8"),
        headers={"Content-Type": "text/xml"},
    )
    assert resp.status_code == 200
    assert resp.text == "success"
    after = client.get("/api/v1/user/me", headers=auth_headers).json()["data"]["user"]
    assert after["avatarUrl"] is None


def test_callback_unknown_trace_is_ignored(client, settings):
    resp = client.post(
        "/api/v1/wechat/callback",
        params=_callback_query(settings),
        json={
            "Event": "wxa_media_check",
            "trace_id": "not-recorded",
            "errcode": 0,
            "result": {"suggest": "risky"},
        },
    )
    assert resp.status_code == 200
    assert resp.text == "success"


def test_callback_other_events_are_ignored(client, settings):
    resp = client.post(
        "/api/v1/wechat/callback",
        params=_callback_query(settings),
        json={"Event": "some_other_event", "FromUserName": "o1"},
    )
    assert resp.status_code == 200
    assert resp.text == "success"


def test_callback_download_error_marks_error_without_removing_avatar(
    client, auth_headers, settings, stub_content_security
):
    _upload_avatar(client, auth_headers, stub_content_security, "trace-err")
    resp = client.post(
        "/api/v1/wechat/callback",
        params=_callback_query(settings),
        json={"Event": "wxa_media_check", "trace_id": "trace-err", "errcode": -1008},
    )
    assert resp.status_code == 200
    after = client.get("/api/v1/user/me", headers=auth_headers).json()["data"]["user"]
    assert after["avatarUrl"] is not None
