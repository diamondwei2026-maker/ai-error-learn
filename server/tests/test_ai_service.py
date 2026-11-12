"""变式题生成器单测：解析容错、数量截断、错误码映射。"""

from __future__ import annotations

import json

import httpx
import pytest

from app.services.ai_service import (
    CODE_AI_NOT_ENABLED,
    CODE_AI_PARSE_FAILED,
    CODE_AI_UNAVAILABLE,
    CODE_AI_UPSTREAM_BUSY,
    AiError,
    DisabledVariantGenerator,
    GlmVariantGenerator,
)


class FakeResponse:
    def __init__(self, status_code: int = 200, payload=None, text: str = ""):
        self.status_code = status_code
        self._payload = payload
        self.text = text or (json.dumps(payload) if payload is not None else "")

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


def _chat_response(content: str, status_code: int = 200) -> FakeResponse:
    return FakeResponse(
        status_code=status_code,
        payload={"choices": [{"message": {"content": content}}]},
    )


def _generator() -> GlmVariantGenerator:
    return GlmVariantGenerator("key", "https://api.example.com/v1", "glm-4-flash")


def test_parses_fenced_json_and_limits_count(monkeypatch):
    payload = {
        "subject": "math",
        "questionType": "解答题",
        "knowledgePoints": ["二次函数", "最值", "对称轴", "多余"],
        "variants": [
            {"stem": f"变式 {index}", "answer": f"答案 {index}"} for index in range(5)
        ],
    }
    content = "说明文字\n```json\n" + json.dumps(payload, ensure_ascii=False) + "\n```\n尾巴"
    monkeypatch.setattr(httpx, "post", lambda *a, **k: _chat_response(content))

    result = _generator().generate("原题", "原答案", 3)
    assert result.subject == "math"
    assert result.question_type == "解答题"
    assert result.knowledge_points == ["二次函数", "最值", "对称轴"]
    assert len(result.variants) == 3
    assert result.variants[0] == {"stem": "变式 0", "answer": "答案 0"}


def test_tolerates_unescaped_newline_in_answer(monkeypatch):
    content = (
        '{"subject": "physics", "questionType": "解答题", '
        '"knowledgePoints": ["受力分析"], '
        '"variants": [{"stem": "题", "answer": "第一行\n第二行"}]}'
    )
    monkeypatch.setattr(httpx, "post", lambda *a, **k: _chat_response(content))

    result = _generator().generate("原题")
    assert result.subject == "physics"
    assert result.variants[0]["answer"] == "第一行\n第二行"


def test_missing_answer_falls_back_to_empty(monkeypatch):
    content = '{"variants": [{"stem": "只有题干"}]}'
    monkeypatch.setattr(httpx, "post", lambda *a, **k: _chat_response(content))

    result = _generator().generate("原题")
    assert result.variants == [{"stem": "只有题干", "answer": ""}]
    assert result.subject == "other"
    assert result.knowledge_points == []


def test_empty_variants_is_valid(monkeypatch):
    monkeypatch.setattr(
        httpx, "post", lambda *a, **k: _chat_response('{"variants": []}')
    )
    assert _generator().generate("原题").variants == []


def test_non_json_raises_parse_error(monkeypatch):
    monkeypatch.setattr(httpx, "post", lambda *a, **k: _chat_response("抱歉，我无法完成"))
    with pytest.raises(AiError) as excinfo:
        _generator().generate("原题")
    assert excinfo.value.code == CODE_AI_PARSE_FAILED


def test_variants_not_list_raises_parse_error(monkeypatch):
    monkeypatch.setattr(
        httpx, "post", lambda *a, **k: _chat_response('{"variants": "bad"}')
    )
    with pytest.raises(AiError) as excinfo:
        _generator().generate("原题")
    assert excinfo.value.code == CODE_AI_PARSE_FAILED


def test_status_429_maps_to_upstream_busy(monkeypatch):
    monkeypatch.setattr(httpx, "post", lambda *a, **k: FakeResponse(status_code=429))
    with pytest.raises(AiError) as excinfo:
        _generator().generate("原题")
    assert excinfo.value.code == CODE_AI_UPSTREAM_BUSY


def test_status_401_maps_to_unavailable(monkeypatch):
    monkeypatch.setattr(httpx, "post", lambda *a, **k: FakeResponse(status_code=401))
    with pytest.raises(AiError) as excinfo:
        _generator().generate("原题")
    assert excinfo.value.code == CODE_AI_UNAVAILABLE


def test_status_500_maps_to_upstream_busy(monkeypatch):
    monkeypatch.setattr(httpx, "post", lambda *a, **k: FakeResponse(status_code=500))
    with pytest.raises(AiError) as excinfo:
        _generator().generate("原题")
    assert excinfo.value.code == CODE_AI_UPSTREAM_BUSY


def test_timeout_maps_to_upstream_busy(monkeypatch):
    def _raise(*_args, **_kwargs):
        raise httpx.ReadTimeout("timeout")

    monkeypatch.setattr(httpx, "post", _raise)
    with pytest.raises(AiError) as excinfo:
        _generator().generate("原题")
    assert excinfo.value.code == CODE_AI_UPSTREAM_BUSY


def test_not_configured_raises_unavailable():
    generator = GlmVariantGenerator("", "https://api.example.com/v1", "glm-4-flash")
    with pytest.raises(AiError) as excinfo:
        generator.generate("原题")
    assert excinfo.value.code == CODE_AI_UNAVAILABLE


def test_disabled_generator_raises_9001():
    with pytest.raises(AiError) as excinfo:
        DisabledVariantGenerator().generate("原题")
    assert excinfo.value.code == CODE_AI_NOT_ENABLED
