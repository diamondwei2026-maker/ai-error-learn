"""AI 举一反三接口单测：鉴权、参数校验、限流、内容安全与错误码映射。"""

from __future__ import annotations

from typing import List, Optional

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from app.api.ai import create_ai_router
from app.errors import CODE_UNAUTHORIZED, ApiError
from app.services.ai_service import (
    CODE_AI_NOT_ENABLED,
    CODE_AI_RATE_LIMITED,
    CODE_AI_UPSTREAM_BUSY,
    AiError,
    DisabledVariantGenerator,
    VariantResult,
)


class FakeGenerator:
    """可控生成器替身。"""

    def __init__(self, variants: Optional[List[dict]] = None, error: Optional[AiError] = None):
        self._variants = variants if variants is not None else [
            {"stem": "变式题 1", "answer": "答案 1"},
            {"stem": "变式题 2", "answer": "答案 2"},
            {"stem": "变式题 3", "answer": "答案 3"},
        ]
        self._error = error

    def generate(self, stem: str, answer: str = "", count: int = 3) -> VariantResult:
        if self._error is not None:
            raise self._error
        return VariantResult(
            subject="math",
            question_type="解答题",
            knowledge_points=["二次函数", "最值"],
            variants=self._variants[:count],
        )


class FakeContentSecurity:
    """内容安全替身：ready 固定为 True，结论可配置。"""

    ready = True

    def __init__(self, verdict: str = "pass"):
        self._verdict = verdict
        self.calls = []

    def check_text(self, text: str, openid: str, scene: int) -> str:
        self.calls.append((text, openid, scene))
        return self._verdict


def _client(
    generator=None,
    content_security=None,
    auth_dep=None,
) -> TestClient:
    app = FastAPI()

    @app.exception_handler(ApiError)
    async def _handler(_request, exc: ApiError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.http_status,
            content={"code": exc.code, "message": exc.message},
        )

    app.include_router(
        create_ai_router(generator or FakeGenerator(), content_security, auth_dep),
        prefix="/api/v1",
    )
    return TestClient(app)


def _post(client: TestClient, **overrides):
    body = {"content": "已知函数 f(x) = x² - 2x + 3，求最值", "answer": "最小值 2"}
    body.update(overrides)
    return client.post("/api/v1/ai/variants", json=body)


def test_disabled_generator_returns_9001():
    resp = _post(_client(DisabledVariantGenerator()))
    assert resp.status_code == 200
    assert resp.json()["code"] == CODE_AI_NOT_ENABLED


def test_generate_success_returns_variants():
    resp = _post(_client())
    body = resp.json()
    assert resp.status_code == 200
    assert body["code"] == 0
    data = body["data"]
    assert data["subject"] == "math"
    assert data["questionType"] == "解答题"
    assert data["knowledgePoints"] == ["二次函数", "最值"]
    assert len(data["variants"]) == 3
    assert data["variants"][0]["stem"] == "变式题 1"
    assert data["traceId"]


def test_empty_variants_is_success():
    resp = _post(_client(FakeGenerator(variants=[])))
    assert resp.json()["code"] == 0
    assert resp.json()["data"]["variants"] == []


def test_blank_content_returns_2005():
    resp = _post(_client(), content="   ")
    assert resp.status_code == 200
    assert resp.json()["code"] == 2005


def test_too_long_content_returns_2005():
    resp = _post(_client(), content="题" * 2001)
    assert resp.json()["code"] == 2005


def test_too_long_answer_returns_2005():
    resp = _post(_client(), answer="答" * 4001)
    assert resp.json()["code"] == 2005


def test_rate_limit_returns_9006():
    client = _client()
    for _ in range(3):
        assert _post(client).json()["code"] == 0
    resp = _post(client)
    assert resp.json()["code"] == CODE_AI_RATE_LIMITED


def test_upstream_error_is_propagated():
    client = _client(FakeGenerator(error=AiError(CODE_AI_UPSTREAM_BUSY, "AI 太忙了")))
    resp = _post(client)
    assert resp.json()["code"] == CODE_AI_UPSTREAM_BUSY


def test_content_risky_returns_9005():
    security = FakeContentSecurity(verdict="risky")
    client = _client(content_security=security)
    resp = _post(client)
    assert resp.json()["code"] == 9005
    # 所有变式合并为一次送检
    assert len(security.calls) == 1
    assert "变式题 1" in security.calls[0][0]


def test_requires_login_when_auth_dep_injected():
    def _deny() -> None:
        raise ApiError(CODE_UNAUTHORIZED, "未登录", http_status=401)

    resp = _post(_client(auth_dep=_deny))
    assert resp.status_code == 401
    assert resp.json()["code"] == CODE_UNAUTHORIZED


def test_authenticated_user_passes_openid_to_content_security():
    class FakeUser:
        id = 7
        openid = "openid-7"

    def _allow() -> FakeUser:
        return FakeUser()

    security = FakeContentSecurity()
    resp = _post(_client(content_security=security, auth_dep=_allow))
    assert resp.json()["code"] == 0
    assert security.calls[0][1] == "openid-7"
