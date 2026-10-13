"""多模态识别服务单测：解析容错 / 错误码映射 / 编排（TDD）。

通过 monkeypatch 替换 httpx.post，避免真实网络调用。
"""

import base64
import json

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
