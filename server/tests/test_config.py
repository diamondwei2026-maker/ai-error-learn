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
