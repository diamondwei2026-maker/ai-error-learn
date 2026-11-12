"""复习提醒接口单测：配置读取 / 订阅上报 / 额度上限 / 未配置降级。"""

from __future__ import annotations

from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from tests.conftest import login_headers

SUBSCRIPTION_URL = "/api/v1/reminder/subscription"


@pytest.fixture()
def reminder_client(settings, stub_wechat) -> TestClient:
    """返回已配置提醒能力的应用客户端。"""
    app = create_app(
        replace(settings, reminder_enabled=True, reminder_template_id="tpl-reminder")
    )
    with TestClient(app) as client:
        yield client


def test_config_is_public(reminder_client: TestClient) -> None:
    body = reminder_client.get("/api/v1/reminder/config").json()
    assert body["code"] == 0
    assert body["data"] == {
        "enabled": True,
        "templateId": "tpl-reminder",
        "page": "pages/quiz/index",
        "quietStart": 21,
        "quietEnd": 8,
    }


def test_config_disabled_when_not_configured(client: TestClient) -> None:
    data = client.get("/api/v1/reminder/config").json()["data"]
    assert data["enabled"] is False
    assert data["templateId"] == ""


def test_subscription_requires_auth(reminder_client: TestClient) -> None:
    resp = reminder_client.post(SUBSCRIPTION_URL, json={"accepted": 1, "enabled": True})
    assert resp.status_code == 401
    assert resp.json()["code"] == 2001


def test_subscription_not_ready_returns_4001(client: TestClient, auth_headers: dict) -> None:
    resp = client.post(
        SUBSCRIPTION_URL, json={"accepted": 1, "enabled": True}, headers=auth_headers
    )
    assert resp.json()["code"] == 4001


def test_subscription_accumulates_quota(reminder_client: TestClient) -> None:
    headers = login_headers(reminder_client)

    first = reminder_client.post(
        SUBSCRIPTION_URL, json={"accepted": 2, "enabled": True}, headers=headers
    ).json()["data"]
    assert first == {"enabled": True, "quota": 2}

    second = reminder_client.post(
        SUBSCRIPTION_URL, json={"accepted": 1, "enabled": True}, headers=headers
    ).json()["data"]
    assert second == {"enabled": True, "quota": 3}


def test_subscription_quota_is_capped(reminder_client: TestClient) -> None:
    headers = login_headers(reminder_client)
    data = reminder_client.post(
        SUBSCRIPTION_URL, json={"accepted": 9, "enabled": True}, headers=headers
    ).json()["data"]
    assert data["quota"] == 5


def test_subscription_disable_clears_quota(reminder_client: TestClient) -> None:
    headers = login_headers(reminder_client)
    reminder_client.post(
        SUBSCRIPTION_URL, json={"accepted": 3, "enabled": True}, headers=headers
    )

    data = reminder_client.post(
        SUBSCRIPTION_URL, json={"accepted": 0, "enabled": False}, headers=headers
    ).json()["data"]
    assert data == {"enabled": False, "quota": 0}


@pytest.mark.parametrize(
    "payload",
    [
        {"accepted": "1", "enabled": True},
        {"accepted": -1, "enabled": True},
        {"accepted": 1, "enabled": "yes"},
    ],
)
def test_subscription_invalid_param_returns_4002(
    reminder_client: TestClient, payload: dict
) -> None:
    headers = login_headers(reminder_client)
    resp = reminder_client.post(SUBSCRIPTION_URL, json=payload, headers=headers)
    assert resp.json()["code"] == 4002
