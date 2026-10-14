"""微信登录：code2Session 封装。

沿用既有 httpx 直连风格；client 可注入便于单测。
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

from app.errors import (
    CODE_LOGIN_NOT_CONFIGURED,
    CODE_WECHAT_CODE_INVALID,
    WechatLoginError,
)

JSCODE2SESSION_URL = "https://api.weixin.qq.com/sns/jscode2session"
DEFAULT_WECHAT_TIMEOUT = 10


class WechatService:
    """封装微信登录凭证换取。"""

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
