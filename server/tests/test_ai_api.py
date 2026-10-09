"""AI 预留接口单测：本期不启用，固定返回 501 / code 9001（TDD）。"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.ai import create_ai_router


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(create_ai_router(), prefix="/api/v1")
    return TestClient(app)


def test_ai_variants_reserved_returns_501():
    resp = _client().post("/api/v1/ai/variants", json={"stem": "求 f(x) 的最值"})
    assert resp.status_code == 501
    assert resp.json() == {"code": 9001, "message": "AI 功能未启用"}


def test_disabled_generator_raises():
    import pytest

    from app.services.ai_service import AiDisabledError, DisabledVariantGenerator

    with pytest.raises(AiDisabledError):
        DisabledVariantGenerator().generate("题干")
