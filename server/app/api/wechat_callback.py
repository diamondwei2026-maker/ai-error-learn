"""微信消息推送回调：接收 mediaCheckAsync 异步检测结果（明文模式）。

- GET：URL 有效性验证（验签通过后原样返回 echostr）
- POST：事件接收（仅处理 wxa_media_check），始终返回 success 以避免微信重试

生产环境需在 MP 后台「消息推送」配置：
  URL=https://<域名>/api/v1/wechat/callback、Token=WECHAT_CALLBACK_TOKEN、明文模式。
"""

from __future__ import annotations

import hashlib
import json
import logging
import xml.etree.ElementTree as ET
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.config import Settings
from app.db import get_db
from app.models.media_check import (
    VERDICT_ERROR,
    VERDICT_PASS,
    VERDICT_REVIEW,
    VERDICT_RISKY,
    MediaCheckRecord,
)
from app.models.user import User
from app.services import auth_service

_logger = logging.getLogger(__name__)

MEDIA_CHECK_EVENT = "wxa_media_check"
DOWNLOAD_FAILED_ERRCODE = -1008
SUCCESS_BODY = "success"


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _signature(token: str, timestamp: str, nonce: str) -> str:
    """明文模式验签：sha1(sorted(token, timestamp, nonce))。"""
    joined = "".join(sorted([token or "", timestamp or "", nonce or ""]))
    return hashlib.sha1(joined.encode("utf-8")).hexdigest()


def _verify(token: str, signature: str, timestamp: str, nonce: str) -> bool:
    if not token or not signature or not timestamp or not nonce:
        return False
    return _signature(token, timestamp, nonce) == signature


def _parse_payload(raw: bytes) -> Optional[Dict[str, Any]]:
    """解析回调体：优先 JSON，失败回退 XML（两种格式都可能出现）。"""
    text = (raw or b"").decode("utf-8", errors="ignore").strip()
    if not text:
        return None

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except (ValueError, TypeError):
        pass

    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        _logger.warning("消息推送回调体无法解析（非 JSON 也非 XML）")
        return None

    payload: Dict[str, Any] = {child.tag: child.text for child in root}
    result = root.find("result")
    if result is not None:
        payload["result"] = {child.tag: child.text for child in result}
    detail = root.find("detail")
    if detail is not None:
        payload["detail"] = [
            {child.tag: child.text for child in item} for item in detail
        ]
    return payload


def _remove_risky_avatar(db: Session, settings: Settings, record: MediaCheckRecord) -> None:
    """命中违规：仅当用户当前头像仍指向被检文件时才删除，避免误删新换的头像。"""
    user = db.get(User, record.user_id)
    if user is None:
        return
    if not (user.avatar_url or "").startswith(f"/static/avatars/{record.file_name}"):
        _logger.info(
            "图片违规但用户头像已变更，跳过删除: user_id=%s file=%s",
            record.user_id,
            record.file_name,
        )
        return

    target = settings.avatar_dir / record.file_name
    try:
        if target.is_file():
            target.unlink()
    except OSError as exc:
        _logger.warning("删除违规头像失败: %s (%s)", target, exc)
    user.avatar_url = None
    user.updated_at = auth_service.now_ms()


def _apply_media_result(db: Session, settings: Settings, payload: Dict[str, Any]) -> None:
    """落库异步检测结果；命中违规时清理头像。"""
    trace_id = payload.get("trace_id")
    if not trace_id:
        _logger.warning("媒体检测回调缺少 trace_id，已忽略")
        return

    record = (
        db.query(MediaCheckRecord)
        .filter(MediaCheckRecord.trace_id == str(trace_id))
        .one_or_none()
    )
    if record is None:
        _logger.warning("媒体检测回调未匹配到记录: trace_id=%s", trace_id)
        return

    errcode = _to_int(payload.get("errcode"), 0)
    result = payload.get("result")
    suggest = result.get("suggest") if isinstance(result, dict) else None

    if errcode == DOWNLOAD_FAILED_ERRCODE:
        verdict = VERDICT_ERROR
    elif suggest == VERDICT_RISKY or _to_int(payload.get("isrisky"), 0) == 1:
        verdict = VERDICT_RISKY
    elif suggest == VERDICT_REVIEW:
        verdict = VERDICT_REVIEW
    elif suggest == VERDICT_PASS:
        verdict = VERDICT_PASS
    else:
        verdict = VERDICT_ERROR

    record.verdict = verdict
    record.checked_at = auth_service.now_ms()
    if verdict == VERDICT_ERROR:
        _logger.warning(
            "媒体检测结果异常: trace_id=%s errcode=%s errmsg=%s",
            trace_id,
            payload.get("errcode"),
            payload.get("errmsg"),
        )
    elif verdict == VERDICT_RISKY:
        _logger.warning("图片内容命中违规: trace_id=%s user_id=%s", trace_id, record.user_id)
        _remove_risky_avatar(db, settings, record)
    db.commit()


def create_wechat_callback_router(settings: Settings) -> APIRouter:
    """构造消息推送回调路由（无需登录，走验签）。"""
    router = APIRouter()

    @router.get("/wechat/callback")
    async def verify_url(
        signature: str = Query(default=""),
        timestamp: str = Query(default=""),
        nonce: str = Query(default=""),
        echostr: str = Query(default=""),
    ) -> Response:
        if not _verify(settings.wechat_callback_token, signature, timestamp, nonce):
            _logger.warning("消息推送 URL 校验验签失败（请检查 WECHAT_CALLBACK_TOKEN）")
            return Response(status_code=403)
        return PlainTextResponse(echostr)

    @router.post("/wechat/callback")
    async def receive_event(
        request: Request,
        signature: str = Query(default=""),
        timestamp: str = Query(default=""),
        nonce: str = Query(default=""),
        db: Session = Depends(get_db),
    ) -> Response:
        if not _verify(settings.wechat_callback_token, signature, timestamp, nonce):
            _logger.warning("消息推送验签失败")
            return Response(status_code=403)

        payload = _parse_payload(await request.body())
        if payload and payload.get("Event") == MEDIA_CHECK_EVENT:
            try:
                _apply_media_result(db, settings, payload)
            except Exception as exc:  # 回调处理失败不影响应答，避免微信重试风暴
                _logger.warning("处理媒体检测回调失败: %s", exc)
        return PlainTextResponse(SUCCESS_BODY)

    return router
