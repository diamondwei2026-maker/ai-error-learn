"""微信登录：code2Session 封装；订阅消息：access_token 缓存 + 发送。

沿用既有 httpx 直连风格；client 可注入便于单测。
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

import httpx

from app.errors import (
    CODE_LOGIN_NOT_CONFIGURED,
    CODE_WECHAT_CODE_INVALID,
    WechatLoginError,
)

JSCODE2SESSION_URL = "https://api.weixin.qq.com/sns/jscode2session"
STABLE_TOKEN_URL = "https://api.weixin.qq.com/cgi-bin/stable_token"
SUBSCRIBE_SEND_URL = "https://api.weixin.qq.com/cgi-bin/message/subscribe/send"
DEFAULT_WECHAT_TIMEOUT = 10
# access_token 提前刷新余量（秒）
TOKEN_REFRESH_MARGIN = 60
# token 失效/过期：清缓存后重试一次
INVALID_TOKEN_ERRCODES = (40001, 42001)
DEFAULT_TOKEN_TTL = 7200

_logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SendMessageResult:
    """订阅消息发送结果：失败只返回原因，不抛异常（调度器仅记日志）。"""

    ok: bool
    reason: str = ""


class WechatService:
    """封装微信登录凭证换取与订阅消息发送。"""

    def __init__(
        self,
        appid: str,
        secret: str,
        timeout: int = DEFAULT_WECHAT_TIMEOUT,
        client: Optional[Any] = None,
    ) -> None:
        self._appid = appid
        self._secret = secret
        self._timeout = timeout
        self._client = client
        # 进程内 access_token 缓存（stable_token 普通模式，多进程各自缓存安全）
        self._token: Optional[str] = None
        self._token_expire_at: float = 0.0

    @property
    def configured(self) -> bool:
        """是否已配置 appid/secret。"""
        return bool(self._appid and self._secret)

    def code2session(self, code: str) -> Dict[str, Any]:
        """用微信 code 换取 openid/unionid。失败抛 WechatLoginError。"""
        if not self._appid or not self._secret:
            raise WechatLoginError(CODE_LOGIN_NOT_CONFIGURED, "服务端未配置微信登录，请稍后再试")
        if not code:
            raise WechatLoginError(CODE_WECHAT_CODE_INVALID, "登录凭证无效，请重试")

        params = {
            "appid": self._appid,
            "secret": self._secret,
            "js_code": code,
            "grant_type": "authorization_code",
        }
        try:
            if self._client is not None:
                response = self._client.get(JSCODE2SESSION_URL, params=params, timeout=self._timeout)
            else:
                response = httpx.get(JSCODE2SESSION_URL, params=params, timeout=self._timeout)
            payload = response.json()
        except Exception as exc:  # 网络异常 / 响应非 JSON
            raise WechatLoginError(CODE_WECHAT_CODE_INVALID, "微信登录失败，请重试") from exc

        if not isinstance(payload, dict):
            raise WechatLoginError(CODE_WECHAT_CODE_INVALID, "微信登录失败，请重试")
        if payload.get("errcode"):
            raise WechatLoginError(CODE_WECHAT_CODE_INVALID, "微信登录凭证无效，请重试")

        openid = payload.get("openid")
        if not openid:
            raise WechatLoginError(CODE_WECHAT_CODE_INVALID, "微信登录失败，请重试")

        return {"openid": openid, "unionid": payload.get("unionid")}

    # ---------- 订阅消息 ----------

    def _request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """发一次请求并返回 JSON 对象；任何异常返回 None（不抛）。"""
        requester = self._client if self._client is not None else httpx
        try:
            call = getattr(requester, method.lower())
            response = call(url, params=params, json=json_body, timeout=self._timeout)
            payload = response.json()
        except Exception as exc:  # 网络异常 / 响应非 JSON
            _logger.warning("微信请求失败: %s %s (%s)", method, url, exc)
            return None
        if not isinstance(payload, dict):
            _logger.warning("微信响应非 JSON 对象: %s %s", method, url)
            return None
        return payload

    def get_access_token(self, force_refresh: bool = False) -> Optional[str]:
        """获取接口调用凭据（内存缓存，提前 60s 刷新）；失败返回 None。"""
        if not self.configured:
            return None

        now = time.time()
        if (
            not force_refresh
            and self._token
            and self._token_expire_at > now + TOKEN_REFRESH_MARGIN
        ):
            return self._token

        payload = self._request(
            "POST",
            STABLE_TOKEN_URL,
            json_body={
                "grant_type": "client_credential",
                "appid": self._appid,
                "secret": self._secret,
                "force_refresh": False,
            },
        )
        if not payload:
            return None
        token = payload.get("access_token")
        if not token:
            _logger.warning(
                "微信 access_token 获取失败: errcode=%s errmsg=%s",
                payload.get("errcode"),
                payload.get("errmsg"),
            )
            return None
        try:
            ttl = int(payload.get("expires_in") or DEFAULT_TOKEN_TTL)
        except (TypeError, ValueError):
            ttl = DEFAULT_TOKEN_TTL
        self._token = str(token)
        self._token_expire_at = now + ttl
        return self._token

    def send_subscribe_message(
        self,
        openid: str,
        template_id: str,
        data: Dict[str, Any],
        page: str = "",
    ) -> SendMessageResult:
        """发送一次性订阅消息。token 失效时刷新重试一次；失败返回原因。"""
        if not self.configured:
            return SendMessageResult(False, "服务端未配置微信密钥")
        if not openid or not template_id:
            return SendMessageResult(False, "缺少 openid 或模板 ID")

        body: Dict[str, Any] = {
            "touser": openid,
            "template_id": template_id,
            "data": data,
        }
        if page:
            body["page"] = page

        for attempt in (0, 1):
            token = self.get_access_token(force_refresh=attempt == 1)
            if not token:
                return SendMessageResult(False, "access_token 获取失败")
            payload = self._request(
                "POST", SUBSCRIBE_SEND_URL, params={"access_token": token}, json_body=body
            )
            if payload is None:
                return SendMessageResult(False, "网络异常")
            errcode = payload.get("errcode") or 0
            if errcode == 0:
                return SendMessageResult(True)
            if errcode in INVALID_TOKEN_ERRCODES and attempt == 0:
                self._token = None
                continue
            reason = f"{errcode}: {payload.get('errmsg') or '发送失败'}"
            _logger.warning("订阅消息发送失败: %s", reason)
            return SendMessageResult(False, reason)
        return SendMessageResult(False, "发送失败")
