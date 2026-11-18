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


def test_parses_exam_point_and_truncates(monkeypatch):
    content = json.dumps(
        {"stem": "题干", "examPoint": "考点" * 150},
        ensure_ascii=False,
    )
    monkeypatch.setattr("httpx.post", lambda *a, **k: _FakeResponse(200, _payload(content)))

    outcome = VisionRecognizeService(_client()).recognize(b"img", "image/jpeg")
    assert len(outcome.exam_point) == 200


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
    assert "examPoint" in prompt
    assert "multiQuestion" in prompt
    # 修复整页多题漏判：提示词必须包含「宁可 true 也不猜测单题」的强约束
    assert "宁可" in prompt
    assert "严禁把" in prompt


# ---------- 多题判定 ----------

def test_model_multi_question_flag_is_trusted(monkeypatch):
    content = json.dumps(
        {"stem": "题干", "answer": "答案", "multiQuestion": True},
        ensure_ascii=False,
    )
    monkeypatch.setattr("httpx.post", lambda *a, **k: _FakeResponse(200, _payload(content)))
    outcome = VisionRecognizeService(_client()).recognize(b"img", "image/jpeg")
    assert outcome.multi_question is True


def test_question_count_ge_two_marks_multi(monkeypatch):
    content = json.dumps(
        {"stem": "题干", "questionCount": 3, "multiQuestion": False},
        ensure_ascii=False,
    )
    monkeypatch.setattr("httpx.post", lambda *a, **k: _FakeResponse(200, _payload(content)))
    outcome = VisionRecognizeService(_client()).recognize(b"img", "image/jpeg")
    assert outcome.multi_question is True


def test_long_stem_with_two_headings_falls_back_to_multi(monkeypatch):
    stem = "1. " + "甲" * 120 + "\n2. " + "乙" * 120
    content = json.dumps({"stem": stem, "answer": ""}, ensure_ascii=False)
    monkeypatch.setattr("httpx.post", lambda *a, **k: _FakeResponse(200, _payload(content)))
    outcome = VisionRecognizeService(_client()).recognize(b"img", "image/jpeg")
    assert outcome.multi_question is True


def test_single_question_with_sub_items_is_not_multi(monkeypatch):
    stem = "1. 已知函数 f(x)，回答下列问题：\n（1）求单调区间；\n（2）求最值。" + "说" * 200
    content = json.dumps({"stem": stem, "answer": "答案"}, ensure_ascii=False)
    monkeypatch.setattr("httpx.post", lambda *a, **k: _FakeResponse(200, _payload(content)))
    outcome = VisionRecognizeService(_client()).recognize(b"img", "image/jpeg")
    assert outcome.multi_question is False


def test_short_stem_numbering_is_not_multi(monkeypatch):
    content = json.dumps(
        {"stem": "1. 第一行\n2. 第二行", "answer": ""}, ensure_ascii=False
    )
    monkeypatch.setattr("httpx.post", lambda *a, **k: _FakeResponse(200, _payload(content)))
    outcome = VisionRecognizeService(_client()).recognize(b"img", "image/jpeg")
    assert outcome.multi_question is False


def test_meta_description_stem_triggers_multi(monkeypatch):
    """修复整页多题漏判：模型把场景描述塞进 stem 时（如用户截图），
    即便 multiQuestion=false + questionCount=1，也要判为多题。"""
    content = json.dumps(
        {
            "stem": "图片中包含多个数学问题，包括几何图形的计算和代数方程的求解。",
            "answer": "无法提供解答",
            "multiQuestion": False,
            "questionCount": 1,
        },
        ensure_ascii=False,
    )
    monkeypatch.setattr("httpx.post", lambda *a, **k: _FakeResponse(200, _payload(content)))
    outcome = VisionRecognizeService(_client()).recognize(b"img", "image/jpeg")
    assert outcome.multi_question is True


@pytest.mark.parametrize(
    "hint",
    [
        "有多道数学题",
        "几道数学题需要解答",
        "多道题目并排",
        "图片中有数道题目",
    ],
)
def test_meta_description_variants_trigger_multi(monkeypatch, hint):
    """覆盖 meta hint 表里的各类短语"""
    content = json.dumps(
        {"stem": hint, "multiQuestion": False, "questionCount": 1},
        ensure_ascii=False,
    )
    monkeypatch.setattr("httpx.post", lambda *a, **k: _FakeResponse(200, _payload(content)))
    outcome = VisionRecognizeService(_client()).recognize(b"img", "image/jpeg")
    assert outcome.multi_question is True


def test_normal_short_single_question_is_not_multi(monkeypatch):
    """修复不能误伤正常短单题"""
    content = json.dumps(
        {
            "stem": "已知 f(x)=x²+2x+1，求其最小值",
            "answer": "解...",
            "multiQuestion": False,
            "questionCount": 1,
        },
        ensure_ascii=False,
    )
    monkeypatch.setattr("httpx.post", lambda *a, **k: _FakeResponse(200, _payload(content)))
    outcome = VisionRecognizeService(_client()).recognize(b"img", "image/jpeg")
    assert outcome.multi_question is False


def test_question_count_propagated_from_parse():
    """_parse_content 第 8 元组位 question_count 正确透出"""
    from app.services import vision_recognize as vr

    stem, answer, subject, qtype, ep, pts, m_multi, qc = vr._parse_content(
        json.dumps(
            {
                "stem": "题干",
                "answer": "",
                "subject": "math",
                "questionType": "解答题",
                "examPoint": "",
                "knowledgePoints": [],
                "multiQuestion": False,
                "questionCount": 5,
            },
            ensure_ascii=False,
        )
    )
    assert stem == "题干"
    assert m_multi is False
    assert qc == 5


# ---------- 跨字段题号多题漏判修复 ----------

def test_cross_field_headings_trigger_multi(monkeypatch):
    """修复跨字段题号漏判：stem 有 "1."，answer 有 "2." → 多题命中。

    模型把两道题分别塞进 stem/answer 两个字段时，
    旧四步判定链里题号检测只在 stem 上做，answer 完全没参与 → 漏判。
    新规则 Step 4：stem 和 answer 各自都有行首题号 → 直接命中。
    """
    content = json.dumps(
        {
            "stem": "1. 已知函数 f(x)=x²+2x+1，求其最小值",
            "answer": "2. 计算定积分 ∫(0,1) x² dx",
            "multiQuestion": False,
            "questionCount": 1,
        },
        ensure_ascii=False,
    )
    monkeypatch.setattr(
        "httpx.post", lambda *a, **k: _FakeResponse(200, _payload(content))
    )
    outcome = VisionRecognizeService(_client()).recognize(b"img", "image/jpeg")
    assert outcome.multi_question is True


def test_cross_field_chinese_headings_trigger_multi(monkeypatch):
    """中文题号跨字段也能命中（一、 和 二、 分别在 stem 和 answer）。"""
    content = json.dumps(
        {
            "stem": "一、求函数极值",
            "answer": "二、解方程 x²-1=0",
            "multiQuestion": False,
            "questionCount": 1,
        },
        ensure_ascii=False,
    )
    monkeypatch.setattr(
        "httpx.post", lambda *a, **k: _FakeResponse(200, _payload(content))
    )
    outcome = VisionRecognizeService(_client()).recognize(b"img", "image/jpeg")
    assert outcome.multi_question is True
