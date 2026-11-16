"""多模态识别服务单测：解析容错 / 错误码映射 / 编排（TDD）。

通过 monkeypatch 替换 httpx.post，避免真实网络调用。
"""

import base64
import json

import httpx
import pytest

from app.services.vision_recognize import (
    CODE_QUOTA_EXCEEDED,
    CODE_RECOGNIZE_FAILED,
    CODE_SERVICE_UNAVAILABLE,
    RecognizeError,
    RecognizeOutcome,
    VisionClient,
    VisionRecognizeService,
)

_BASE_URL = "https://api.example.com/v1"


class _FakeResponse:
    def __init__(self, status_code, payload, text=""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self):
        return self._payload


def _client(enabled=True, timeout=5) -> VisionClient:
    return VisionClient("k", _BASE_URL, "glm-4v-flash", enabled, timeout)


def _payload(content):
    return {"choices": [{"message": {"content": content}}]}


# ---------- 解析容错 ----------

def test_parses_json(monkeypatch):
    monkeypatch.setattr(
        "httpx.post", lambda *a, **k: _FakeResponse(200, _payload('{"stem": "题干", "answer": "答案"}'))
    )
    assert _client().recognize(b"img", "image/jpeg") == ("题干", "答案")


def test_strips_code_fence(monkeypatch):
    content = '```json\n{"stem": "题干", "answer": "42"}\n```'
    monkeypatch.setattr("httpx.post", lambda *a, **k: _FakeResponse(200, _payload(content)))
    assert _client().recognize(b"img", "image/jpeg") == ("题干", "42")


def test_tolerates_surrounding_text(monkeypatch):
    content = '识别结果如下：{"stem": "题干", "answer": "答案"} 完毕'
    monkeypatch.setattr("httpx.post", lambda *a, **k: _FakeResponse(200, _payload(content)))
    assert _client().recognize(b"img", "image/jpeg") == ("题干", "答案")


def test_answer_missing_defaults_empty(monkeypatch):
    monkeypatch.setattr(
        "httpx.post", lambda *a, **k: _FakeResponse(200, _payload('{"stem": "只有题干"}'))
    )
    assert _client().recognize(b"img", "image/jpeg") == ("只有题干", "")


def test_non_json_returns_full_text_as_stem(monkeypatch):
    monkeypatch.setattr("httpx.post", lambda *a, **k: _FakeResponse(200, _payload("这是一段纯文本")))
    assert _client().recognize(b"img", "image/jpeg") == ("这是一段纯文本", "")


def test_empty_content_returns_empty(monkeypatch):
    monkeypatch.setattr("httpx.post", lambda *a, **k: _FakeResponse(200, _payload("")))
    assert _client().recognize(b"img", "image/jpeg") == ("", "")


def test_list_content_is_joined(monkeypatch):
    parts = [{"text": '{"stem": "题干", '}, {"text": '"answer": "答案"}'}]
    monkeypatch.setattr("httpx.post", lambda *a, **k: _FakeResponse(200, _payload(parts)))
    assert _client().recognize(b"img", "image/jpeg") == ("题干", "答案")


def test_multiline_answer_is_preserved(monkeypatch):
    answer = "第一步：由题意得方程\n第二步：解得 x = 2\n所以答案是 2"
    content = json.dumps({"stem": "题干", "answer": answer}, ensure_ascii=False)
    monkeypatch.setattr("httpx.post", lambda *a, **k: _FakeResponse(200, _payload(content)))
    stem, parsed_answer = _client().recognize(b"img", "image/jpeg")
    assert stem == "题干"
    assert parsed_answer == answer


def test_parses_fenced_json_with_raw_newlines(monkeypatch):
    # 复刻多模态模型真实输出：```json 围栏内 answer 值含未转义的真实换行
    content = (
        "```json\n{\n"
        '    "stem": "一件商品按照30%的利润出售",\n'
        '    "answer": "解: 设成本价为x元。\n(1+30%)x×0.8-x=520\nx=13000"\n'
        "}\n```"
    )
    monkeypatch.setattr("httpx.post", lambda *a, **k: _FakeResponse(200, _payload(content)))
    stem, answer = _client().recognize(b"img", "image/jpeg")
    assert stem == "一件商品按照30%的利润出售"
    assert answer == "解: 设成本价为x元。\n(1+30%)x×0.8-x=520\nx=13000"


# ---------- 请求体 ----------

def test_request_carries_model_and_base64_image(monkeypatch):
    captured = {}

    def fake_post(url, json=None, headers=None, timeout=None):  # noqa: A002
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        return _FakeResponse(200, _payload('{"stem": "题干", "answer": "答案"}'))

    monkeypatch.setattr("httpx.post", fake_post)
    _client().recognize(b"abc", "image/png")

    assert captured["url"] == f"{_BASE_URL}/chat/completions"
    assert captured["json"]["model"] == "glm-4v-flash"
    assert captured["headers"]["Authorization"] == "Bearer k"
    content = captured["json"]["messages"][0]["content"]
    image_part = next(p for p in content if p["type"] == "image_url")
    expected = "data:image/png;base64," + base64.b64encode(b"abc").decode("ascii")
    assert image_part["image_url"]["url"] == expected


def test_prompt_requests_solution_process(monkeypatch):
    captured = {}

    def fake_post(url, json=None, headers=None, timeout=None):  # noqa: A002
        captured["json"] = json
        return _FakeResponse(200, _payload('{"stem": "题干", "answer": "解答"}'))

    monkeypatch.setattr("httpx.post", fake_post)
    _client().recognize(b"abc", "image/jpeg")

    content = captured["json"]["messages"][0]["content"]
    prompt = next(p["text"] for p in content if p["type"] == "text")
    assert "解题过程" in prompt


def test_non_image_mime_falls_back_to_jpeg(monkeypatch):
    captured = {}

    def fake_post(url, json=None, headers=None, timeout=None):  # noqa: A002
        captured["json"] = json
        return _FakeResponse(200, _payload('{"stem": "题干", "answer": "答案"}'))

    monkeypatch.setattr("httpx.post", fake_post)
    _client().recognize(b"abc", "application/octet-stream")
    content = captured["json"]["messages"][0]["content"]
    image_part = next(p for p in content if p["type"] == "image_url")
    assert image_part["image_url"]["url"].startswith("data:image/jpeg;base64,")


# ---------- 错误码映射 ----------

def test_quota_429_maps_to_1003(monkeypatch):
    monkeypatch.setattr("httpx.post", lambda *a, **k: _FakeResponse(429, {}))
    with pytest.raises(RecognizeError) as excinfo:
        _client().recognize(b"img", "image/jpeg")
    assert excinfo.value.code == CODE_QUOTA_EXCEEDED


def test_unauthorized_401_maps_to_1005(monkeypatch):
    monkeypatch.setattr("httpx.post", lambda *a, **k: _FakeResponse(401, {}))
    with pytest.raises(RecognizeError) as excinfo:
        _client().recognize(b"img", "image/jpeg")
    assert excinfo.value.code == CODE_SERVICE_UNAVAILABLE


def test_forbidden_403_maps_to_1005(monkeypatch):
    monkeypatch.setattr("httpx.post", lambda *a, **k: _FakeResponse(403, {}))
    with pytest.raises(RecognizeError) as excinfo:
        _client().recognize(b"img", "image/jpeg")
    assert excinfo.value.code == CODE_SERVICE_UNAVAILABLE


def test_server_error_500_maps_to_1002(monkeypatch):
    monkeypatch.setattr("httpx.post", lambda *a, **k: _FakeResponse(500, {}, "internal error"))
    with pytest.raises(RecognizeError) as excinfo:
        _client().recognize(b"img", "image/jpeg")
    assert excinfo.value.code == CODE_RECOGNIZE_FAILED


def test_invalid_model_400_maps_to_1005(monkeypatch):
    # 复刻百炼/智谱对「模型名不存在」的返回：400 + error.message
    body = '{"error": {"message": "model qwen-vl-flash not found"}}'
    monkeypatch.setattr(
        "httpx.post",
        lambda *a, **k: _FakeResponse(
            400, {"error": {"message": "model not found"}}, body
        ),
    )
    with pytest.raises(RecognizeError) as excinfo:
        _client().recognize(b"img", "image/jpeg")
    assert excinfo.value.code == CODE_SERVICE_UNAVAILABLE
    assert "VISION_MODEL" in excinfo.value.message


def test_server_error_503_message_is_explicit(monkeypatch):
    monkeypatch.setattr("httpx.post", lambda *a, **k: _FakeResponse(503, {}, "busy"))
    with pytest.raises(RecognizeError) as excinfo:
        _client().recognize(b"img", "image/jpeg")
    assert excinfo.value.code == CODE_RECOGNIZE_FAILED
    assert excinfo.value.message == "识别服务暂时不可用，请稍后重试"


def test_timeout_maps_to_1002_with_explicit_message(monkeypatch):
    def boom(*a, **k):
        raise httpx.ReadTimeout("timed out")

    monkeypatch.setattr("httpx.post", boom)
    with pytest.raises(RecognizeError) as excinfo:
        _client().recognize(b"img", "image/jpeg")
    assert excinfo.value.code == CODE_RECOGNIZE_FAILED
    assert excinfo.value.message == "识别超时，请重试"


def test_network_exception_maps_to_1002(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("network down")

    monkeypatch.setattr("httpx.post", boom)
    with pytest.raises(RecognizeError) as excinfo:
        _client().recognize(b"img", "image/jpeg")
    assert excinfo.value.code == CODE_RECOGNIZE_FAILED


def test_bad_response_shape_maps_to_1002(monkeypatch):
    monkeypatch.setattr("httpx.post", lambda *a, **k: _FakeResponse(200, {"unexpected": True}))
    with pytest.raises(RecognizeError) as excinfo:
        _client().recognize(b"img", "image/jpeg")
    assert excinfo.value.code == CODE_RECOGNIZE_FAILED


def test_empty_image_maps_to_1002(monkeypatch):
    called = {"n": 0}

    def fake_post(*a, **k):
        called["n"] += 1
        return _FakeResponse(200, _payload(""))

    monkeypatch.setattr("httpx.post", fake_post)
    with pytest.raises(RecognizeError) as excinfo:
        _client().recognize(b"", "image/jpeg")
    assert excinfo.value.code == CODE_RECOGNIZE_FAILED
    assert called["n"] == 0


# ---------- 配置 / 编排 ----------

def test_unconfigured_client_raises():
    with pytest.raises(RecognizeError) as excinfo:
        VisionClient("", _BASE_URL, "m", True).recognize(b"img", "image/jpeg")
    assert excinfo.value.code == CODE_RECOGNIZE_FAILED


def test_disabled_client_raises_without_calling(monkeypatch):
    called = {"n": 0}

    def fake_post(*a, **k):
        called["n"] += 1
        return _FakeResponse(200, _payload(""))

    monkeypatch.setattr("httpx.post", fake_post)
    client = VisionClient("k", _BASE_URL, "m", False)
    assert client.is_configured is False
    with pytest.raises(RecognizeError):
        client.recognize(b"img", "image/jpeg")
    assert called["n"] == 0


def test_service_none_client_raises():
    with pytest.raises(RecognizeError) as excinfo:
        VisionRecognizeService(None).recognize(b"img", "image/jpeg")
    assert excinfo.value.code == CODE_RECOGNIZE_FAILED


def test_service_success(monkeypatch):
    monkeypatch.setattr(
        "httpx.post", lambda *a, **k: _FakeResponse(200, _payload('{"stem": "题干", "answer": "答案"}'))
    )
    outcome = VisionRecognizeService(_client()).recognize(b"img", "image/jpeg")
    assert outcome == RecognizeOutcome(stem="题干", answer="答案")


# ---------- 元信息 ----------

def test_parses_meta_and_limits_knowledge_points(monkeypatch):
    content = json.dumps(
        {
            "stem": "题干",
            "answer": "答案",
            "subject": "physics",
            "questionType": "解答题",
            "knowledgePoints": ["受力分析", "牛顿第二定律", "多余1", "多余2"],
        },
        ensure_ascii=False,
    )
    monkeypatch.setattr("httpx.post", lambda *a, **k: _FakeResponse(200, _payload(content)))

    outcome = VisionRecognizeService(_client()).recognize(b"img", "image/jpeg")
    assert outcome.subject == "physics"
    assert outcome.question_type == "解答题"
    assert outcome.knowledge_points == ("受力分析", "牛顿第二定律", "多余1")


def test_invalid_subject_falls_back_to_other(monkeypatch):
    monkeypatch.setattr(
        "httpx.post",
        lambda *a, **k: _FakeResponse(
            200, _payload('{"stem": "题干", "subject": "biology"}')
        ),
    )
    outcome = VisionRecognizeService(_client()).recognize(b"img", "image/jpeg")
    assert outcome.subject == "other"


def test_unknown_question_type_is_dropped(monkeypatch):
    monkeypatch.setattr(
        "httpx.post",
        lambda *a, **k: _FakeResponse(
            200, _payload('{"stem": "题干", "questionType": "未知题型"}')
        ),
    )
    outcome = VisionRecognizeService(_client()).recognize(b"img", "image/jpeg")
    assert outcome.question_type == ""


def test_missing_meta_keeps_legacy_behaviour(monkeypatch):
    monkeypatch.setattr(
        "httpx.post", lambda *a, **k: _FakeResponse(200, _payload('{"stem": "题干", "answer": "答案"}'))
    )
    outcome = VisionRecognizeService(_client()).recognize(b"img", "image/jpeg")
    assert outcome.subject == ""
    assert outcome.question_type == ""
    assert outcome.knowledge_points == ()


def test_prompt_requests_meta(monkeypatch):
    captured = {}

    def fake_post(url, json=None, headers=None, timeout=None):  # noqa: A002
        captured["json"] = json
        return _FakeResponse(200, _payload('{"stem": "题干"}'))

    monkeypatch.setattr("httpx.post", fake_post)
    _client().recognize(b"abc", "image/jpeg")

    content = captured["json"]["messages"][0]["content"]
    prompt = next(p["text"] for p in content if p["type"] == "text")
    assert "subject" in prompt
    assert "knowledgePoints" in prompt
