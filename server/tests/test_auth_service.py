"""JWT 签发/校验单测（TDD）。"""

from __future__ import annotations

import pytest

from app.config import Settings
from app.errors import TokenError
from app.services import auth_service


def make_settings(**overrides) -> Settings:
    base = {"jwt_secret": "unit-secret", "jwt_access_ttl": 60, "jwt_refresh_ttl": 600}
    base.update(overrides)
    return Settings(**base)


def test_access_token_roundtrip():
    settings = make_settings()
    token, expire_at = auth_service.create_access_token(7, settings)
    assert isinstance(token, str) and token
    assert expire_at > 0
    assert auth_service.decode_token(token, settings, expected_type="access") == 7


def test_refresh_token_roundtrip():
    settings = make_settings()
    token, _ = auth_service.create_refresh_token(9, settings)
    assert auth_service.decode_token(token, settings, expected_type="refresh") == 9


def test_token_type_mismatch_rejected():
    settings = make_settings()
    access_token, _ = auth_service.create_access_token(7, settings)
    with pytest.raises(TokenError):
        auth_service.decode_token(access_token, settings, expected_type="refresh")


def test_expired_token_rejected():
    settings = make_settings(jwt_access_ttl=-1)
    token, _ = auth_service.create_access_token(7, settings)
    with pytest.raises(TokenError):
        auth_service.decode_token(token, settings, expected_type="access")


def test_garbage_token_rejected():
    with pytest.raises(TokenError):
        auth_service.decode_token("not-a-jwt", make_settings(), expected_type="access")


def test_decode_without_secret_raises():
    with pytest.raises(TokenError):
        auth_service.decode_token("anything", Settings(jwt_secret=""), expected_type="access")
