"""应用配置：全部从环境变量读取，密钥不落盘、不进日志、不出现在 repr 中。"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Mapping, Optional

# 多模态识别模型（OpenAI 兼容 /chat/completions）默认值：测试阶段 GLM-4V-Flash
DEFAULT_VISION_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"
DEFAULT_VISION_MODEL = "glm-4v-flash"
DEFAULT_VISION_TIMEOUT = 20
# 单张图片二进制上限：10MB
DEFAULT_MAX_IMAGE_BYTES = 10 * 1024 * 1024

# 微信登录
DEFAULT_WECHAT_APPID = "wxf7fbaf8d9a6f7296"
# JWT
DEFAULT_JWT_ACCESS_TTL = 7200  # 2 小时
DEFAULT_JWT_REFRESH_TTL = 2592000  # 30 天
# 数据库：开发期 SQLite，上线改阿里云 RDS 连接串
DEFAULT_DATABASE_URL = "sqlite:///./app.db"
# 头像上限：2MB
DEFAULT_AVATAR_MAX_BYTES = 2 * 1024 * 1024


@dataclass(frozen=True)
class Settings:
    """运行期配置。

    密钥字段使用 repr=False，确保日志/异常中打印 Settings 时不会泄露。
    """

    # 多模态识别模型（OpenAI 兼容）
    vision_enabled: bool = False
    vision_api_key: str = field(default="", repr=False)
    vision_base_url: str = DEFAULT_VISION_BASE_URL
    vision_model: str = DEFAULT_VISION_MODEL
    vision_timeout: int = DEFAULT_VISION_TIMEOUT
    max_image_bytes: int = DEFAULT_MAX_IMAGE_BYTES
    ai_enabled: bool = False

    # 微信登录
    wechat_appid: str = DEFAULT_WECHAT_APPID
    wechat_app_secret: str = field(default="", repr=False)

    # JWT
    jwt_secret: str = field(default="", repr=False)
    jwt_access_ttl: int = DEFAULT_JWT_ACCESS_TTL
    jwt_refresh_ttl: int = DEFAULT_JWT_REFRESH_TTL

    # 数据库与鉴权
    database_url: str = DEFAULT_DATABASE_URL
    auth_required: bool = True
    avatar_max_bytes: int = DEFAULT_AVATAR_MAX_BYTES

    # CORS：逗号分隔的白名单；"*" 表示放开（开发期）
    cors_origins: str = "*"

    # 静态资源根目录；为空时使用 server/uploads（测试可覆盖）
    uploads_root: str = ""

    @property
    def vision_configured(self) -> bool:
        """是否已配置视觉模型访问密钥。"""
        return bool(self.vision_api_key and self.vision_base_url)

    @property
    def wechat_configured(self) -> bool:
        """是否已配置微信登录密钥。"""
        return bool(self.wechat_appid and self.wechat_app_secret)

    @property
    def cors_origin_list(self) -> List[str]:
        raw = (self.cors_origins or "*").strip()
        if raw == "*" or not raw:
            return ["*"]
        return [item.strip() for item in raw.split(",") if item.strip()]

    @property
    def uploads_dir(self) -> Path:
        """静态资源根目录（默认 server/uploads）。"""
        if self.uploads_root:
            return Path(self.uploads_root)
        return Path(__file__).resolve().parents[1] / "uploads"

    @property
    def avatar_dir(self) -> Path:
        return self.uploads_dir / "avatars"


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
    """从环境变量装载配置。缺失密钥时不抛错，仅在真正调用相关服务时报错。"""
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
        wechat_appid=source.get("WECHAT_APPID", DEFAULT_WECHAT_APPID) or DEFAULT_WECHAT_APPID,
        wechat_app_secret=source.get("WECHAT_APP_SECRET", "") or "",
        jwt_secret=source.get("JWT_SECRET", "") or "",
        jwt_access_ttl=_parse_int(source.get("JWT_ACCESS_TTL"), DEFAULT_JWT_ACCESS_TTL),
        jwt_refresh_ttl=_parse_int(source.get("JWT_REFRESH_TTL"), DEFAULT_JWT_REFRESH_TTL),
        database_url=source.get("DATABASE_URL", DEFAULT_DATABASE_URL) or DEFAULT_DATABASE_URL,
        auth_required=_parse_bool(source.get("AUTH_REQUIRED"), True),
        avatar_max_bytes=_parse_int(source.get("AVATAR_MAX_BYTES"), DEFAULT_AVATAR_MAX_BYTES),
        cors_origins=source.get("CORS_ORIGINS", "*") or "*",
        uploads_root=source.get("UPLOADS_DIR", "") or "",
    )


# ---- 运行期当前配置（由 create_app 注入，供依赖注入读取） ----

_current_settings: Optional[Settings] = None


def set_current_settings(settings: Settings) -> None:
    global _current_settings
    _current_settings = settings


def get_current_settings() -> Settings:
    global _current_settings
    if _current_settings is None:
        _current_settings = load_settings()
    return _current_settings
