"""微信订阅消息单测：token 缓存 / 失效重取 / 失败原因。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from app.services.wechat_service import (
    STABLE_TOKEN_URL,
    SUBSCRIBE_SEND_URL,
    WechatService,
)


class FakeResponse:
    def __init__(self, payload: Dict[str, Any]) -> None:
        self._payload = payload

    def json(self) -> Dict[str, Any]:
        return self._payload


class FakeClient:
    """按顺序返回预设响应，并记录请求。"""

    def __init__(self, responses: List[Dict[str, Any]]) -> None:
        self._responses = list(responses)
        self.calls: List[Dict[str, Any]] = []

    def post(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
    ) -> FakeResponse:
        self.calls.append({"url": url, "params": params, "json": json})
        return FakeResponse(self._responses.pop(0))


def make_service(responses: List[Dict[str, Any]]) -> Tuple[WechatService, FakeClient]:
    client = FakeClient(responses)
    return WechatService("wx-test", "secret", client=client), client


def _urls(client: FakeClient, url: str) -> List[Dict[str, Any]]:
    return [call for call in client.calls if call["url"] == url]


def test_token_is_cached_between_sends() -> None:
    service, client = make_service(
        [
            {"access_token": "token-1", "expires_in": 7200},
            {"errcode": 0},
            {"errcode": 0},
        ]
    )
    assert service.send_subscribe_message("openid", "tpl", {}).ok is True
    assert service.send_subscribe_message("openid", "tpl", {}).ok is True

    assert len(_urls(client, STABLE_TOKEN_URL)) == 1
    assert len(_urls(client, SUBSCRIBE_SEND_URL)) == 2


def test_invalid_token_refreshes_once() -> None:
    service, client = make_service(
        [
            {"access_token": "token-1", "expires_in": 7200},
            {"errcode": 40001, "errmsg": "invalid credential"},
            {"access_token": "token-2", "expires_in": 7200},
            {"errcode": 0},
        ]
    )
    result = service.send_subscribe_message("openid", "tpl", {})
    assert result.ok is True

    assert len(_urls(client, STABLE_TOKEN_URL)) == 2
    assert service.get_access_token() == "token-2"


def test_send_failure_returns_reason() -> None:
    service, _client = make_service(
        [
            {"access_token": "token-1", "expires_in": 7200},
            {"errcode": 43101, "errmsg": "user refuse to accept the msg"},
        ]
    )
    result = service.send_subscribe_message("openid", "tpl", {})
    assert result.ok is False
    assert result.reason == "43101: user refuse to accept the msg"


def test_unconfigured_service_returns_reason() -> None:
    service = WechatService("", "")
    assert service.get_access_token() is None
    result = service.send_subscribe_message("openid", "tpl", {})
    assert result.ok is False
    assert result.reason == "服务端未配置微信密钥"
