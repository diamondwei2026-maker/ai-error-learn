"""配置装载单测：缺省值、环境变量覆盖、非法值兜底、密钥不泄露（TDD）。"""

from app.config import DEFAULT_ENDPOINT, DEFAULT_MAX_IMAGE_BYTES, load_settings


def test_defaults_without_env():
    settings = load_settings(env={})
    assert settings.access_key_id == ""
    assert settings.access_key_secret == ""
    assert settings.ocr_endpoint == DEFAULT_ENDPOINT
    assert settings.max_image_bytes == DEFAULT_MAX_IMAGE_BYTES
    assert settings.ocr_configured is False
    assert settings.ai_enabled is False


def test_reads_env_values():
    settings = load_settings(
        env={
            "ALIBABA_CLOUD_ACCESS_KEY_ID": "id-123",
            "ALIBABA_CLOUD_ACCESS_KEY_SECRET": "secret-456",
            "OCR_ENDPOINT": "ocr-api.cn-shanghai.aliyuncs.com",
            "OCR_MAX_IMAGE_BYTES": "123",
            "AI_ENABLED": "true",
        }
    )
    assert settings.ocr_configured is True
    assert settings.ocr_endpoint == "ocr-api.cn-shanghai.aliyuncs.com"
    assert settings.max_image_bytes == 123
    assert settings.ai_enabled is True


def test_invalid_max_bytes_falls_back_to_default():
    settings = load_settings(env={"OCR_MAX_IMAGE_BYTES": "abc"})
    assert settings.max_image_bytes == DEFAULT_MAX_IMAGE_BYTES


def test_secret_is_not_exposed_in_repr():
    settings = load_settings(
        env={
            "ALIBABA_CLOUD_ACCESS_KEY_ID": "id-123",
            "ALIBABA_CLOUD_ACCESS_KEY_SECRET": "topsecret-value",
        }
    )
    assert "topsecret-value" not in repr(settings)
