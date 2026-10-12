"""应用配置：全部从环境变量读取，密钥不落盘、不进日志、不出现在 repr 中。"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Optional

# 多模态识别模型（OpenAI 兼容 /chat/completions）默认值：测试阶段 GLM-4V-Flash
DEFAULT_VISION_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"
DEFAULT_VISION_MODEL = "glm-4v-flash"
DEFAULT_VISION_TIMEOUT = 20
# 单张图片二进制上限：10MB
DEFAULT_MAX_IMAGE_BYTES = 10 * 1024 * 1024


@dataclass(frozen=True)
class Settings:
    """运行期配置。

    vision_api_key 使用 repr=False，确保日志/异常中打印 Settings 时不会泄露密钥。
    """

    # 多模态识别模型（OpenAI 兼容）
    vision_enabled: bool = False
    vision_api_key: str = field(default="", repr=False)
    vision_base_url: str = DEFAULT_VISION_BASE_URL
    vision_model: str = DEFAULT_VISION_MODEL
    vision_timeout: int = DEFAULT_VISION_TIMEOUT
    max_image_bytes: int = DEFAULT_MAX_IMAGE_BYTES
    ai_enabled: bool = False

    @property
    def vision_configured(self) -> bool:
        """是否已配置视觉模型访问密钥。"""
        return bool(self.vision_api_key and self.vision_base_url)


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


def _load_dotenv_override() -> None:
    """以 override=True 装载 server/.env，使其成为唯一权威来源。

    uvicorn 的 --env-file 内部使用 load_dotenv（默认 override=False），
    不会覆盖进程中已存在的环境变量，可能导致外部旧密钥静默遮蔽 .env。
    此处显式覆盖，确保应用始终使用项目配置。缺文件/未安装依赖时静默跳过。
    """
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if env_path.is_file():
        load_dotenv(env_path, override=True)


def load_settings(env: Optional[Mapping[str, str]] = None) -> Settings:
    """从环境变量装载配置。缺失密钥时不抛错，仅在真正调用识别服务时报错。"""
    if env is None:
        _load_dotenv_override()
        source: Mapping[str, str] = os.environ
    else:
        source = env
    return Settings(
        vision_enabled=_parse_bool(source.get("VISION_ENABLED"), False),
        vision_api_key=source.get("VISION_API_KEY", "") or "",
        vision_base_url=source.get("VISION_BASE_URL", DEFAULT_VISION_BASE_URL)
        or DEFAULT_VISION_BASE_URL,
        vision_model=source.get("VISION_MODEL", DEFAULT_VISION_MODEL) or DEFAULT_VISION_MODEL,
        vision_timeout=_parse_int(source.get("VISION_TIMEOUT"), DEFAULT_VISION_TIMEOUT),
        max_image_bytes=_parse_int(
            source.get("VISION_MAX_IMAGE_BYTES"), DEFAULT_MAX_IMAGE_BYTES
        ),
        ai_enabled=_parse_bool(source.get("AI_ENABLED"), False),
    )
