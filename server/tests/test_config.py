"""配置装载单测：缺省值、环境变量覆盖、非法值兜底、密钥不泄露（TDD）。"""

from app.config import (
    DEFAULT_MAX_IMAGE_BYTES,
    DEFAULT_VISION_BASE_URL,
    DEFAULT_VISION_MODEL,
    DEFAULT_VISION_TIMEOUT,
    load_settings,
)


def test_defaults_without_env():
    settings = load_settings(env={})
    assert settings.vision_enabled is False
    assert settings.vision_api_key == ""
    assert settings.vision_base_url == DEFAULT_VISION_BASE_URL
    assert settings.vision_model == DEFAULT_VISION_MODEL
    assert settings.vision_timeout == DEFAULT_VISION_TIMEOUT
    assert settings.max_image_bytes == DEFAULT_MAX_IMAGE_BYTES
    assert settings.vision_configured is False
    assert settings.ai_enabled is False


def test_reads_env_values():
    settings = load_settings(
        env={
            "VISION_ENABLED": "true",
            "VISION_API_KEY": "key-123",
            "VISION_BASE_URL": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "VISION_MODEL": "qwen-vl-flash",
            "VISION_TIMEOUT": "25",
            "VISION_MAX_IMAGE_BYTES": "123",
            "AI_ENABLED": "true",
        }
    )
    assert settings.vision_enabled is True
    assert settings.vision_api_key == "key-123"
    assert settings.vision_base_url == "https://dashscope.aliyuncs.com/compatible-mode/v1"
    assert settings.vision_model == "qwen-vl-flash"
    assert settings.vision_timeout == 25
    assert settings.vision_configured is True
    assert settings.max_image_bytes == 123
    assert settings.ai_enabled is True


def test_invalid_max_bytes_falls_back_to_default():
    settings = load_settings(env={"VISION_MAX_IMAGE_BYTES": "abc"})
    assert settings.max_image_bytes == DEFAULT_MAX_IMAGE_BYTES


def test_vision_key_is_not_exposed_in_repr():
    settings = load_settings(env={"VISION_API_KEY": "vision-topsecret"})
    assert "vision-topsecret" not in repr(settings)


# ---------- 用户体系配置 ----------


def test_user_system_defaults():
    settings = load_settings(env={})
    assert settings.wechat_appid == "wx683110d829c1f0f9"
    assert settings.wechat_app_secret == ""
    assert settings.jwt_secret == ""
    assert settings.jwt_access_ttl == 7200
    assert settings.jwt_refresh_ttl == 2592000
    assert settings.database_url == "sqlite:///./app.db"
    assert settings.auth_required is True
    assert settings.avatar_max_bytes == 2 * 1024 * 1024
    assert settings.wechat_configured is False
    assert settings.cors_origin_list == ["*"]


def test_user_system_env_overrides():
    settings = load_settings(
        env={
            "WECHAT_APPID": "wx-1",
            "WECHAT_APP_SECRET": "sec",
            "JWT_SECRET": "jwt",
            "JWT_ACCESS_TTL": "10",
            "JWT_REFRESH_TTL": "20",
            "DATABASE_URL": "sqlite:///./x.db",
            "AUTH_REQUIRED": "false",
            "AVATAR_MAX_BYTES": "123",
            "CORS_ORIGINS": "https://a.com, https://b.com",
        }
    )
    assert settings.wechat_configured is True
    assert settings.jwt_access_ttl == 10
    assert settings.jwt_refresh_ttl == 20
    assert settings.database_url == "sqlite:///./x.db"
    assert settings.auth_required is False
    assert settings.avatar_max_bytes == 123
    assert settings.cors_origin_list == ["https://a.com", "https://b.com"]


def test_user_system_secrets_not_exposed_in_repr():
    settings = load_settings(env={"WECHAT_APP_SECRET": "wechat-secret", "JWT_SECRET": "jwt-secret"})
    dumped = repr(settings)
    assert "wechat-secret" not in dumped
    assert "jwt-secret" not in dumped
