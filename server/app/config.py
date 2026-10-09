"""应用配置：全部从环境变量读取，密钥不落盘、不进日志、不出现在 repr 中。"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Mapping, Optional

# 阿里云文字识别（ocr-api 2021-07-07）默认服务地址：华东1（杭州）
DEFAULT_ENDPOINT = "ocr-api.cn-hangzhou.aliyuncs.com"
# 阿里云 OCR 单张图片二进制上限：10MB
DEFAULT_MAX_IMAGE_BYTES = 10 * 1024 * 1024


@dataclass(frozen=True)
class Settings:
    """运行期配置。

    access_key_secret 使用 repr=False，确保日志/异常中打印 Settings 时不会泄露密钥。
    """

    access_key_id: str = ""
    access_key_secret: str = field(default="", repr=False)
    ocr_endpoint: str = DEFAULT_ENDPOINT
    max_image_bytes: int = DEFAULT_MAX_IMAGE_BYTES
    ai_enabled: bool = False

    @property
    def ocr_configured(self) -> bool:
        """是否已配置 OCR 访问密钥。"""
        return bool(self.access_key_id and self.access_key_secret)


def _parse_int(raw: Optional[str], default: int) -> int:
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def _parse_bool(raw: Optional[str], default: bool = False) -> bool:
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def load_settings(env: Optional[Mapping[str, str]] = None) -> Settings:
    """从环境变量装载配置。缺失密钥时不抛错，仅在真正调用 OCR 时报错。"""
    source = os.environ if env is None else env
    return Settings(
        access_key_id=source.get("ALIBABA_CLOUD_ACCESS_KEY_ID", "") or "",
        access_key_secret=source.get("ALIBABA_CLOUD_ACCESS_KEY_SECRET", "") or "",
        ocr_endpoint=source.get("OCR_ENDPOINT", DEFAULT_ENDPOINT) or DEFAULT_ENDPOINT,
        max_image_bytes=_parse_int(source.get("OCR_MAX_IMAGE_BYTES"), DEFAULT_MAX_IMAGE_BYTES),
        ai_enabled=_parse_bool(source.get("AI_ENABLED"), False),
    )
