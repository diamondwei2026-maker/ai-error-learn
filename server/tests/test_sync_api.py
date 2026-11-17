"""错题同步接口单测（TDD）：新者优先 / 墓碑 / 增量 / 越权隔离。"""

from __future__ import annotations

import time

from tests.conftest import login_headers


def make_item(
    item_id="q1",
    content="题干",
    answer="答案",
    created=1,
    updated=1,
    deleted=False,
    schedule=None,
    meta=None,
):
    item = {
        "id": item_id,
        "content": content,
        "answer": answer,
        "createdAt": created,
        "updatedAt": updated,
        "deleted": deleted,
    }
    if schedule:
        item.update(schedule)
    if meta:
        item.update(meta)
    return item


def push(client, headers, items):
    return client.post("/api/v1/sync/push", json={"items": items}, headers=headers)


def pull(client, headers, since=None):
    url = "/api/v1/sync/pull" if since is None else f"/api/v1/sync/pull?since={since}"
    return client.get(url, headers=headers)


def test_push_requires_auth(client):
    resp = client.post("/api/v1/sync/push", json={"items": []})
    assert resp.status_code == 401
    assert resp.json()["code"] == 2001


def test_push_insert_and_pull(client, auth_headers):
    resp = push(client, auth_headers, [make_item()])
    assert resp.json()["code"] == 0
    assert resp.json()["data"]["accepted"] == ["q1"]

    items = pull(client, auth_headers).json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["id"] == "q1"
    assert items[0]["content"] == "题干"


def test_newer_update_overwrites(client, auth_headers):
    push(client, auth_headers, [make_item(content="v1", updated=10)])
    push(client, auth_headers, [make_item(content="v2", updated=20)])
    items = pull(client, auth_headers).json()["data"]["items"]
    assert items[0]["content"] == "v2"


def test_older_update_does_not_overwrite(client, auth_headers):
    push(client, auth_headers, [make_item(content="new", updated=20)])
    push(client, auth_headers, [make_item(content="old", updated=10)])
    items = pull(client, auth_headers).json()["data"]["items"]
    assert items[0]["content"] == "new"


def test_delete_tombstone_is_synced(client, auth_headers):
    push(client, auth_headers, [make_item(updated=1)])
    push(client, auth_headers, [make_item(updated=2, deleted=True)])
    items = pull(client, auth_headers).json()["data"]["items"]
    assert items[0]["deleted"] is True


def test_pull_since_returns_only_newer_changes(client, auth_headers):
    push(client, auth_headers, [make_item("q1", updated=1)])
    cursor = pull(client, auth_headers).json()["data"]["serverTime"]

    time.sleep(0.01)  # 规避同毫秒边界
    push(client, auth_headers, [make_item("q2", updated=2)])

    items = pull(client, auth_headers, since=cursor).json()["data"]["items"]
    assert [item["id"] for item in items] == ["q2"]


def test_cross_user_isolation(client, auth_headers, stub_wechat):
    push(client, auth_headers, [make_item("q1")])

    stub_wechat["openid"] = "openid-2"
    other_headers = login_headers(client)
    items = pull(client, other_headers).json()["data"]["items"]
    assert items == []


def test_invalid_items_returns_3001(client, auth_headers):
    resp = client.post("/api/v1/sync/push", json={"items": [{"id": "q1"}]}, headers=auth_headers)
    assert resp.json()["code"] == 3001


def test_invalid_item_type_returns_3001(client, auth_headers):
    resp = client.post(
        "/api/v1/sync/push",
        json={"items": [make_item(updated="not-int")]},
        headers=auth_headers,
    )
    assert resp.json()["code"] == 3001


def test_schedule_round_trip(client, auth_headers):
    schedule = {"reviewStage": 2, "nextReviewAt": 1700000000000, "lastReviewedAt": 1690000000000}
    resp = push(client, auth_headers, [make_item(schedule=schedule)])
    assert resp.json()["code"] == 0

    items = pull(client, auth_headers).json()["data"]["items"]
    assert items[0]["reviewStage"] == 2
    assert items[0]["nextReviewAt"] == 1700000000000
    assert items[0]["lastReviewedAt"] == 1690000000000


def test_old_format_push_keeps_schedule(client, auth_headers):
    push(client, auth_headers, [make_item(updated=1, schedule={"reviewStage": 3, "nextReviewAt": 111})])
    # 旧客户端不带排期字段，仅内容更新
    push(client, auth_headers, [make_item(updated=2, content="新题干")])

    items = pull(client, auth_headers).json()["data"]["items"]
    assert items[0]["content"] == "新题干"
    assert items[0]["reviewStage"] == 3
    assert items[0]["nextReviewAt"] == 111


def test_schedule_only_change_skips_content_check(client, auth_headers, stub_content_security):
    push(client, auth_headers, [make_item(updated=1, schedule={"reviewStage": 1})])
    calls_after_insert = len(stub_content_security["calls"])

    # 仅排期变化（内容未变），不应重复送检
    push(
        client,
        auth_headers,
        [make_item(updated=2, schedule={"reviewStage": 2, "lastReviewedAt": 222})],
    )

    assert len(stub_content_security["calls"]) == calls_after_insert
    items = pull(client, auth_headers).json()["data"]["items"]
    assert items[0]["reviewStage"] == 2
    assert items[0]["lastReviewedAt"] == 222


def test_mastered_schedule_null_round_trip(client, auth_headers):
    push(client, auth_headers, [make_item(updated=1, schedule={"reviewStage": 7, "nextReviewAt": None})])
    items = pull(client, auth_headers).json()["data"]["items"]
    assert items[0]["reviewStage"] == 7
    assert items[0]["nextReviewAt"] is None


def test_invalid_schedule_type_returns_3001(client, auth_headers):
    resp = client.post(
        "/api/v1/sync/push",
        json={"items": [make_item(schedule={"nextReviewAt": "tomorrow"})]},
        headers=auth_headers,
    )
    assert resp.json()["code"] == 3001


# ---------- 识题元信息 ----------

def test_meta_round_trip(client, auth_headers):
    meta = {
        "subject": "math",
        "questionType": "解答题",
        "knowledgePoints": ["二次函数", "最值"],
    }
    push(client, auth_headers, [make_item(meta=meta)])

    items = pull(client, auth_headers).json()["data"]["items"]
    assert items[0]["subject"] == "math"
    assert items[0]["questionType"] == "解答题"
    assert items[0]["knowledgePoints"] == ["二次函数", "最值"]


def test_old_format_push_keeps_meta(client, auth_headers):
    meta = {"subject": "physics", "questionType": "选择题", "knowledgePoints": ["受力分析"]}
    push(client, auth_headers, [make_item(updated=1, meta=meta)])
    # 旧客户端不带元信息，仅更新内容
    push(client, auth_headers, [make_item(updated=2, content="新题干")])

    items = pull(client, auth_headers).json()["data"]["items"]
    assert items[0]["content"] == "新题干"
    assert items[0]["subject"] == "physics"
    assert items[0]["questionType"] == "选择题"
    assert items[0]["knowledgePoints"] == ["受力分析"]


def test_exam_point_round_trip(client, auth_headers):
    meta = {"examPoint": "二次函数在闭区间上的最值"}
    push(client, auth_headers, [make_item(meta=meta)])

    items = pull(client, auth_headers).json()["data"]["items"]
    assert items[0]["examPoint"] == "二次函数在闭区间上的最值"


def test_old_format_push_keeps_exam_point(client, auth_headers):
    push(client, auth_headers, [make_item(updated=1, meta={"examPoint": "根的判别式"})])
    push(client, auth_headers, [make_item(updated=2, content="新题干")])

    items = pull(client, auth_headers).json()["data"]["items"]
    assert items[0]["examPoint"] == "根的判别式"


def test_empty_meta_explicitly_clears(client, auth_headers):
    meta = {"subject": "math", "questionType": "解答题", "knowledgePoints": ["二次函数"]}
    push(client, auth_headers, [make_item(updated=1, meta=meta)])
    push(
        client,
        auth_headers,
        [make_item(updated=2, meta={"subject": "", "questionType": "", "knowledgePoints": []})],
    )

    items = pull(client, auth_headers).json()["data"]["items"]
    assert items[0]["subject"] is None
    assert items[0]["questionType"] is None
    assert items[0]["knowledgePoints"] == []


def test_meta_is_deduped(client, auth_headers):
    meta = {"knowledgePoints": ["二次函数", "二次函数", "最值"]}
    push(client, auth_headers, [make_item(meta=meta)])

    items = pull(client, auth_headers).json()["data"]["items"]
    assert items[0]["knowledgePoints"] == ["二次函数", "最值"]


def test_invalid_meta_returns_3001(client, auth_headers):
    cases = [
        {"subject": "这是一个超长超长超长超长超长的学科名称"},
        {"knowledgePoints": ["a", "b", "c", "d"]},
        {"knowledgePoints": ["知识点" * 20]},
        {"knowledgePoints": [1, 2]},
        {"examPoint": "考点" * 101},
    ]
    for meta in cases:
        resp = push(client, auth_headers, [make_item(meta=meta)])
        assert resp.json()["code"] == 3001


def test_legacy_item_returns_empty_meta(client, auth_headers):
    push(client, auth_headers, [make_item()])

    items = pull(client, auth_headers).json()["data"]["items"]
    assert items[0]["subject"] is None
    assert items[0]["questionType"] is None
    assert items[0]["knowledgePoints"] == []
