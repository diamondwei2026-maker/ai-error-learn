"""微信内容安全：access_token 缓存 + 文本/图片送检。

沿用既有 httpx 直连风格；client 可注入便于单测。

降级原则（全局一致）：未配置密钥、接口报错、无权限、IP 未白名单等任何异常，
一律**放行 + 记日志**（文本返回 ``skipped``、图片返回 ``None``），绝不上抛，
不阻塞用户写入。
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional, Tuple

import httpx

from app.config import DEFAULT_CONTENT_SECURITY_TIMEOUT

STABLE_TOKEN_URL = "https://api.weixin.qq.com/cgi-bin/stable_token"
MSG_SEC_CHECK_URL = "https://api.weixin.qq.com/wxa/msg_sec_check"
MEDIA_CHECK_ASYNC_URL = "https://api.weixin.qq.com/wxa/media_check_async"

# 场景枚举：1 资料；2 评论；3 论坛；4 社交日志
SCENE_PROFILE = 1  # 昵称 / 头像
SCENE_FORUM = 3  # 错题题干与答案等 UGC 内容

VERDICT_PASS = "pass"
VERDICT_RISKY = "risky"
VERDICT_REVIEW = "review"
VERDICT_SKIPPED = "skipped"

# 文本上限：2500 字（超出微信会报错，此处截断兜底）
TEXT_MAX_LENGTH = 2500
# access_token 提前失效余量
TOKEN_REFRESH_MARGIN = 300
INVALID_TOKEN_ERRCODE = 40001
DEFAULT_TOKEN_TTL = 7200

_logger = logging.getLogger(__name__)

# appid -> (access_token, expire_at)。stable_token 普通模式不会互相失效，多进程各自缓存安全。
_token_cache: Dict[str, Tuple[str, float]] = {}


def _clear_token_cache(appid: str) -> None:
    _token_cache.pop(appid, None)


def merge_check_text(content: str, answer: str = "") -> str:
    """把题干与答案合并为一次送检文本（预检与同步兜底共用同一口径）。"""
    return "\n".join(
        part for part in ((content or "").strip(), (answer or "").strip()) if part
    )


class ContentSecurityService:
    """封装微信内容安全接口（msgSecCheck / mediaCheckAsync）。"""

    def __init__(
        self,
        appid: str,
        secret: str,
        enabled: bool = True,
        timeout: int = DEFAULT_CONTENT_SECURITY_TIMEOUT,
        client: Optional[Any] = None,
    ) -> None:
        self._appid = appid
        self._secret = secret
        self._enabled = enabled
        self._timeout = timeout
        self._client = client

    @property
    def ready(self) -> bool:
        """是否具备调用条件（开关打开且已配置 appid/secret）。"""
        return bool(self._enabled and self._appid and self._secret)

    # ---------- 内部：HTTP ----------

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
            _logger.warning("微信内容安全请求失败: %s %s (%s)", method, url, exc)
            return None
        if not isinstance(payload, dict):
            _logger.warning("微信内容安全响应非 JSON 对象: %s %s", method, url)
            return None
        return payload

    def _access_token(self, use_cache: bool = True) -> Optional[str]:
        """获取接口调用凭据（stable_token 普通模式），带内存缓存。"""
        if not self.ready:
            return None
        now = time.time()
        if use_cache:
            cached = _token_cache.get(self._appid)
            if cached and cached[1] > now + TOKEN_REFRESH_MARGIN:
                return cached[0]

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
        _token_cache[self._appid] = (str(token), now + ttl)
        return str(token)

    def _post_with_token(self, url: str, body: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """带 token 的 POST；遇 40001（token 失效）清缓存重试一次。"""
        for attempt in (0, 1):
            token = self._access_token(use_cache=attempt == 0)
            if not token:
                return None
            payload = self._request(
                "POST", url, params={"access_token": token}, json_body=body
            )
            if payload is None:
                return None
            if payload.get("errcode") == INVALID_TOKEN_ERRCODE and attempt == 0:
                _clear_token_cache(self._appid)
                continue
            return payload
        return None

    # ---------- 对外：文本 ----------

    def check_text(self, text: str, openid: str, scene: int) -> str:
        """文本送检。返回 pass / risky / review / skipped（skipped 表示降级放行）。"""
        content = (text or "").strip()
        if not content or not self.ready or not openid:
            return VERDICT_SKIPPED

        payload = self._post_with_token(
            MSG_SEC_CHECK_URL,
            {
                "content": content[:TEXT_MAX_LENGTH],
                "version": 2,
                "scene": scene,
                "openid": openid,
            },
        )
        if payload is None:
            return VERDICT_SKIPPED

        result = payload.get("result")
        suggest = result.get("suggest") if isinstance(result, dict) else None
        if suggest not in (VERDICT_PASS, VERDICT_RISKY, VERDICT_REVIEW):
            _logger.warning(
                "微信文本检查结果异常，降级放行: errcode=%s errmsg=%s",
                payload.get("errcode"),
                payload.get("errmsg"),
            )
            return VERDICT_SKIPPED

        if suggest != VERDICT_PASS:
            label = result.get("label") if isinstance(result, dict) else None
            _logger.warning(
                "微信文本检查命中: suggest=%s label=%s trace_id=%s",
                suggest,
                label,
                payload.get("trace_id"),
            )
        return suggest

    # ---------- 对外：图片 ----------

    def check_image_async(self, media_url: str, openid: str, scene: int) -> Optional[str]:
        """图片异步送检。成功返回 trace_id（用于匹配回调），失败/降级返回 None。"""
        if not self.ready or not media_url or not openid:
            return None

        payload = self._post_with_token(
            MEDIA_CHECK_ASYNC_URL,
            {
                "media_url": media_url,
                "media_type": 2,
                "version": 2,
                "scene": scene,
                "openid": openid,
            },
        )
        if payload is None:
            return None

        trace_id = payload.get("trace_id")
        if not trace_id:
            _logger.warning(
                "微信图片送检失败，降级放行: errcode=%s errmsg=%s",
                payload.get("errcode"),
                payload.get("errmsg"),
            )
            return None
        return str(trace_id)
