"""AI 举一反三接口单测：鉴权、参数校验、限流、内容安全与错误码映射。"""

from __future__ import annotations

import json
from typing import List, Optional

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.ai import create_ai_router
from app.db.base import Base
from app.errors import CODE_UNAUTHORIZED, ApiError
from app.models.question_sync import QuestionSync
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
        self.last_meta = {"subject": "", "question_type": "", "knowledge_points": None}

    def generate(
        self,
        stem: str,
        answer: str = "",
        count: int = 3,
        subject: str = "",
        question_type: str = "",
        knowledge_points: Optional[List[str]] = None,
    ) -> VariantResult:
        self.last_meta = {
            "subject": subject,
            "question_type": question_type,
            "knowledge_points": knowledge_points,
        }
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
    db_dep=None,
) -> TestClient:
    app = FastAPI()

    @app.exception_handler(ApiError)
    async def _handler(_request, exc: ApiError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.http_status,
            content={"code": exc.code, "message": exc.message},
        )

    app.include_router(
        create_ai_router(
            generator or FakeGenerator(), content_security, auth_dep, db_dep
        ),
        prefix="/api/v1",
    )
    return TestClient(app)


class FakeUser:
    """鉴权用户替身（查库按 id 定位）。"""

    def __init__(self, user_id: int = 7, openid: str = "openid-7"):
        self.id = user_id
        self.openid = openid


def _allow_user(user_id: int = 7):
    def _dep() -> FakeUser:
        return FakeUser(user_id)

    return _dep


def _meta_db(tmp_path):
    """独立临时 SQLite，避免污染全局数据库配置。"""
    engine = create_engine(
        f"sqlite:///{(tmp_path / 'ai-meta.db').as_posix()}", future=True
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, future=True)


def _db_dep(factory):
    def _dep():
        session = factory()
        try:
            yield session
        finally:
            session.close()

    return _dep


def _add_stored(
    factory,
    user_id: int = 7,
    item_id: str = "q1",
    subject: Optional[str] = None,
    question_type: Optional[str] = None,
    points: Optional[List[str]] = None,
    deleted: bool = False,
):
    session = factory()
    try:
        session.add(
            QuestionSync(
                user_id=user_id,
                item_id=item_id,
                content="题干",
                answer="",
                created_at=1,
                updated_at=1,
                deleted=deleted,
                synced_at=1,
                subject=subject,
                question_type=question_type,
                knowledge_points=json.dumps(points, ensure_ascii=False)
                if points
                else None,
            )
        )
        session.commit()
    finally:
        session.close()


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


def test_complete_meta_is_forwarded():
    generator = FakeGenerator()
    resp = _post(
        _client(generator),
        subject="math",
        questionType="解答题",
        knowledgePoints=["二次函数", "最值"],
    )
    assert resp.json()["code"] == 0
    assert generator.last_meta["subject"] == "math"
    assert generator.last_meta["question_type"] == "解答题"
    assert generator.last_meta["knowledge_points"] == ["二次函数", "最值"]


def test_subject_only_meta_is_forwarded():
    # 只有学科、没有知识点：学科已知即可复用，不再重新分类
    generator = FakeGenerator()
    resp = _post(_client(generator), subject="math")
    assert resp.json()["code"] == 0
    assert generator.last_meta["subject"] == "math"
    assert generator.last_meta["knowledge_points"] == []


def test_invalid_meta_is_dropped_without_error():
    generator = FakeGenerator()
    resp = _post(
        _client(generator),
        subject="not-a-subject",
        questionType="题型" * 20,
        knowledgePoints=["a", "b", "c", "d"],
    )
    assert resp.json()["code"] == 0
    assert generator.last_meta["subject"] == ""
    assert generator.last_meta["question_type"] == ""
    assert generator.last_meta["knowledge_points"] is None


def test_stored_meta_wins_over_payload(tmp_path):
    generator = FakeGenerator()
    factory = _meta_db(tmp_path)
    _add_stored(
        factory,
        subject="physics",
        question_type="选择题",
        points=["受力分析"],
    )
    client = _client(
        generator, auth_dep=_allow_user(), db_dep=_db_dep(factory)
    )
    resp = _post(
        client,
        questionId="q1",
        subject="math",
        questionType="解答题",
        knowledgePoints=["二次函数"],
    )
    assert resp.json()["code"] == 0
    assert generator.last_meta == {
        "subject": "physics",
        "question_type": "选择题",
        "knowledge_points": ["受力分析"],
    }


def test_stored_meta_fills_missing_fields_from_payload(tmp_path):
    generator = FakeGenerator()
    factory = _meta_db(tmp_path)
    _add_stored(factory, subject="physics")
    client = _client(
        generator, auth_dep=_allow_user(), db_dep=_db_dep(factory)
    )
    resp = _post(
        client,
        questionId="q1",
        questionType="解答题",
        knowledgePoints=["受力分析"],
    )
    assert resp.json()["code"] == 0
    assert generator.last_meta["subject"] == "physics"
    assert generator.last_meta["question_type"] == "解答题"
    assert generator.last_meta["knowledge_points"] == ["受力分析"]


def test_deleted_stored_row_is_ignored(tmp_path):
    generator = FakeGenerator()
    factory = _meta_db(tmp_path)
    _add_stored(factory, subject="math", deleted=True)
    client = _client(
        generator, auth_dep=_allow_user(), db_dep=_db_dep(factory)
    )
    resp = _post(client, questionId="q1")
    assert resp.json()["code"] == 0
    # 库内已删除且入参未携带 → 走分类兜底链路
    assert generator.last_meta["subject"] == ""


def test_anonymous_request_skips_db_lookup(tmp_path):
    generator = FakeGenerator()
    factory = _meta_db(tmp_path)
    _add_stored(factory, subject="physics", points=["受力分析"])
    client = _client(generator, db_dep=_db_dep(factory))
    resp = _post(
        client, questionId="q1", subject="math", knowledgePoints=["二次函数"]
    )
    assert resp.json()["code"] == 0
    assert generator.last_meta["subject"] == "math"
    assert generator.last_meta["knowledge_points"] == ["二次函数"]
