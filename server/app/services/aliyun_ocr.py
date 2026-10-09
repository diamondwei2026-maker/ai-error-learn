"""OCR 服务：阿里云文字识别（ocr-api 2021-07-07）适配与业务编排。

分层：
- AliyunOcrClient：真实 SDK 适配器（延迟导入 SDK，便于测试环境不安装依赖）
- OcrService：编排「高精版优先 → 通用版降级」，并把 SDK 异常映射为业务错误码
"""

from __future__ import annotations

import io
import json
from dataclasses import dataclass
from typing import Any, Optional

from app.utils.text_clean import clean_ocr_text, count_words

# 业务错误码（对齐方案设计文档 §7.1）
CODE_DOWNLOAD_FAILED = 1001
CODE_OCR_FAILED = 1002
CODE_QUOTA_EXCEEDED = 1003
CODE_IMAGE_TOO_LARGE = 1004

# 触发「配额/限流」判定的关键字（命中即视为 1003）
_QUOTA_HINTS = ("throttl", "quota", "flow control", "exceed", "limit")


class OcrError(Exception):
    """带业务错误码的 OCR 异常。"""

    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class OcrOutcome:
    """OCR 结果（已清洗）。"""

    text: str
    words_count: int


def extract_text(raw_data: Any) -> str:
    """从阿里云返回的 Data 字段中取出识别文本。

    Data 为 JSON 字符串，形如 {"content": "...", ...}；解析失败时按原文返回。
    """
    if not raw_data:
        return ""
    if isinstance(raw_data, (bytes, bytearray)):
        raw_data = bytes(raw_data).decode("utf-8", "ignore")
    if isinstance(raw_data, dict):
        for key in ("content", "Content"):
            value = raw_data.get(key)
            if isinstance(value, str):
                return value
        return ""
    if not isinstance(raw_data, str):
        return str(raw_data)
    try:
        parsed = json.loads(raw_data)
    except (TypeError, ValueError):
        return raw_data
    return extract_text(parsed)


def _map_to_ocr_error(exc: Exception) -> OcrError:
    """把 SDK 异常映射为业务错误码。"""
    code = str(getattr(exc, "code", "") or "")
    message = str(getattr(exc, "message", "") or str(exc))
    haystack = f"{code} {message}".lower()
    if any(hint in haystack for hint in _QUOTA_HINTS):
        return OcrError(CODE_QUOTA_EXCEEDED, "OCR 调用额度受限，请稍后再试")
    return OcrError(CODE_OCR_FAILED, "OCR 识别失败，请重试或手动输入")


def _extract_data(response: Any) -> str:
    """从 SDK 响应对象中取出 body.data。"""
    body = getattr(response, "body", None)
    data = getattr(body, "data", None)
    if data is None:
        return ""
    if isinstance(data, (bytes, bytearray)):
        return bytes(data).decode("utf-8", "ignore")
    return str(data)


class AliyunOcrClient:
    """阿里云 OCR 客户端适配器（SDK 延迟导入，未配置密钥时快速失败）。"""

    def __init__(self, access_key_id: str, access_key_secret: str, endpoint: str):
        self._access_key_id = access_key_id
        self._access_key_secret = access_key_secret
        self._endpoint = endpoint
        self._client: Optional[Any] = None

    @property
    def is_configured(self) -> bool:
        return bool(self._access_key_id and self._access_key_secret)

    def _ensure_client(self) -> Any:
        if self._client is None:
            from alibabacloud_ocr_api20210707.client import Client
            from alibabacloud_tea_openapi import models as open_api_models

            config = open_api_models.Config(
                access_key_id=self._access_key_id,
                access_key_secret=self._access_key_secret,
            )
            config.endpoint = self._endpoint
            self._client = Client(config)
        return self._client

    def recognize(self, image_bytes: bytes, mode: str) -> str:
        """调用 OCR，返回原始 Data 字符串。mode ∈ {advanced, general}。"""
        if not self.is_configured:
            raise OcrError(CODE_OCR_FAILED, "OCR 服务未配置访问密钥")

        # 延迟导入，保证测试环境无需安装阿里云 SDK
        from alibabacloud_ocr_api20210707 import models as ocr_models
        from alibabacloud_tea_util import models as util_models

        client = self._ensure_client()
        stream = io.BytesIO(image_bytes)
        runtime = util_models.RuntimeOptions()
        if mode == "advanced":
            request = ocr_models.RecognizeAdvancedRequest(body=stream)
            response = client.recognize_advanced_with_options(request, runtime)
        else:
            request = ocr_models.RecognizeGeneralRequest(body=stream)
            response = client.recognize_general_with_options(request, runtime)
        return _extract_data(response)


class OcrService:
    """OCR 业务编排：高精版优先，失败降级通用版；配额错误立即上抛。"""

    def __init__(self, client: Optional[Any]):
        self._client = client

    def recognize(self, image_bytes: bytes) -> OcrOutcome:
        if self._client is None:
            raise OcrError(CODE_OCR_FAILED, "OCR 服务未配置访问密钥")

        last_error: Optional[OcrError] = None
        for mode in ("advanced", "general"):
            try:
                raw = self._client.recognize(image_bytes, mode)
            except OcrError:
                raise
            except Exception as exc:  # noqa: BLE001 - 统一映射为业务错误码
                mapped = _map_to_ocr_error(exc)
                if mapped.code == CODE_QUOTA_EXCEEDED:
                    raise mapped
                last_error = mapped
                continue
            text = clean_ocr_text(extract_text(raw))
            return OcrOutcome(text=text, words_count=count_words(text))

        raise last_error or OcrError(CODE_OCR_FAILED, "OCR 识别失败，请重试或手动输入")
