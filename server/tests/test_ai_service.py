"""变式题生成器单测：解析容错、数量截断、错误码映射。"""

from __future__ import annotations

import json
import re
import threading

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


# ---------- 元信息复用 ----------

def test_reuses_meta_and_skips_classification(monkeypatch):
    captured = {}

    def fake_post(url, json=None, headers=None, timeout=None):  # noqa: A002
        captured["prompt"] = json["messages"][0]["content"]
        return _chat_response('{"variants": [{"stem": "变式", "answer": "答"}]}')

    monkeypatch.setattr(httpx, "post", fake_post)

    result = _generator().generate(
        "原题", "原答", 2, subject="physics", question_type="解答题",
        knowledge_points=["受力分析"],
    )
    assert result.subject == "physics"
    assert result.question_type == "解答题"
    assert result.knowledge_points == ["受力分析"]
    assert "已知分类" in captured["prompt"]
    assert "受力分析" in captured["prompt"]


def test_reuses_meta_without_knowledge_points(monkeypatch):
    captured = {}

    def fake_post(url, json=None, headers=None, timeout=None):  # noqa: A002
        captured["prompt"] = json["messages"][0]["content"]
        return _chat_response('{"variants": [{"stem": "变式", "answer": "答"}]}')

    monkeypatch.setattr(httpx, "post", fake_post)

    result = _generator().generate(
        "原题", "", 1, subject="physics", question_type="解答题"
    )
    assert result.subject == "physics"
    assert result.question_type == "解答题"
    assert result.knowledge_points == []
    assert "已知分类" in captured["prompt"]
    assert "知识点：未提供" in captured["prompt"]


def test_reuse_meta_overrides_model_output(monkeypatch):
    content = (
        '{"subject": "math", "questionType": "选择题", '
        '"knowledgePoints": ["模型自判"], '
        '"variants": [{"stem": "变式", "answer": "答"}]}'
    )
    monkeypatch.setattr(httpx, "post", lambda *a, **k: _chat_response(content))

    result = _generator().generate(
        "原题", "", 1, subject="chemistry", question_type="填空题",
        knowledge_points=["化学平衡"],
    )
    assert result.subject == "chemistry"
    assert result.question_type == "填空题"
    assert result.knowledge_points == ["化学平衡"]


def test_missing_meta_falls_back_to_classification(monkeypatch):
    captured = {}

    def fake_post(url, json=None, headers=None, timeout=None):  # noqa: A002
        captured["prompt"] = json["messages"][0]["content"]
        return _chat_response('{"variants": [{"stem": "变式", "answer": "答"}]}')

    monkeypatch.setattr(httpx, "post", fake_post)

    _generator().generate("原题", "", 1)
    assert "已知分类" not in captured["prompt"]


def test_invalid_subject_normalized_before_reuse(monkeypatch):
    captured = {}

    def fake_post(url, json=None, headers=None, timeout=None):  # noqa: A002
        captured["prompt"] = json["messages"][0]["content"]
        return _chat_response('{"variants": [{"stem": "变式", "answer": "答"}]}')

    monkeypatch.setattr(httpx, "post", fake_post)

    result = _generator().generate(
        "原题", "", 1, subject="biology", knowledge_points=["细胞结构"]
    )
    assert result.subject == "other"
    assert "other" in captured["prompt"]


# ---------- 考点驱动命题 ----------

def test_prompt_asks_for_exam_point_and_variation_axes(monkeypatch):
    captured = {}

    def fake_post(url, json=None, headers=None, timeout=None):  # noqa: A002
        captured["prompt"] = json["messages"][0]["content"]
        captured["temperature"] = json["temperature"]
        return _chat_response('{"variants": [{"stem": "变式", "answer": "答"}]}')

    monkeypatch.setattr(httpx, "post", fake_post)

    _generator().generate(
        "原题", "", 3, subject="math", question_type="解答题",
        knowledge_points=["二次函数"],
    )
    prompt = captured["prompt"]
    # 任务重定义为“同考点重新命题”，不再要求同构改写
    assert "围绕同一个考点重新命题" in prompt
    assert "考点卡" in prompt
    assert "变化轴" in prompt
    assert "句式独立" in prompt
    assert "同构" not in prompt
    # 生成需要采样空间
    assert captured["temperature"] >= 0.7


def test_exam_point_uses_single_pass_with_original_question(monkeypatch):
    calls = []

    def fake_post(url, json=None, headers=None, timeout=None):  # noqa: A002
        calls.append(json)
        return _chat_response('{"variants": [{"stem": "变式", "answer": "答"}]}')

    monkeypatch.setattr(httpx, "post", fake_post)

    result = _generator().generate(
        "原题题干", "原答案", 2, subject="math", question_type="解答题",
        knowledge_points=["二次函数"], exam_point="二次函数在闭区间上的最值",
    )
    # 考点已知：跳过规划，单次命题
    assert len(calls) == 1
    prompt = calls[0]["messages"][0]["content"]
    assert "【考点】二次函数在闭区间上的最值" in prompt
    assert "原题题干" in prompt
    assert "已知分类" in prompt
    assert calls[0]["temperature"] == 0.7
    assert result.exam_point == "二次函数在闭区间上的最值"


def test_axis_is_kept_in_variants(monkeypatch):
    content = (
        '{"variants": [{"axis": "C", "axisNote": "条件与结论互换", '
        '"stem": "变式", "answer": "答"}]}'
    )
    monkeypatch.setattr(httpx, "post", lambda *a, **k: _chat_response(content))

    result = _generator().generate("原题", "", 1)
    assert result.variants[0]["axis"] == "C"
    assert result.variants[0]["stem"] == "变式"


# ---------- 规划 → 逐题成题 流程 ----------

_ORIGINAL = "已知二次函数 y = x² - 4x + 3，求它在区间 [0, 3] 上的最大值和最小值。"

_PLAN_JSON = json.dumps(
    {
        "examPoint": "二次函数在闭区间上的最值",
        "invariants": ["二次函数解析式", "闭区间"],
        "ideas": [
            {"axis": "A", "scenario": "工厂日利润", "focus": "求最大利润", "entry": "顶点式"},
            {"axis": "B", "scenario": "商品定价", "focus": "求最值", "entry": "配方"},
            {"axis": "C", "scenario": "已知最值反求参数", "focus": "求参数范围", "entry": "端点与顶点"},
            {"axis": "D", "scenario": "图像读最值", "focus": "读图", "entry": "图像"},
        ],
    },
    ensure_ascii=False,
)

_DRAFTS = {
    "A": "某工厂生产一种零件的日利润 P（元）与日产量 x（件）满足 P = -2x² + 80x - 600，且 0 ≤ x ≤ 30，求日利润的最大值。",
    "B": "某商品每件进价 20 元，售价为 x 元时每天可卖出（60 - x）件，且售价不低于 25 元、不高于 40 元，问售价定为多少元时每天利润最大。",
    "C": "某二次函数在闭区间上的最大值为 5、最小值为 -4，请写出一个满足条件的函数解析式，并说明取到最值的位置。",
    "D": "下图是某商品日利润随售价变化的图像，请根据图像回答：售价为多少时利润最高，最高利润是多少。",
}


def _axis_from_prompt(prompt: str) -> str:
    match = re.search(r"变化轴：([A-F])", prompt)
    return match.group(1) if match else ""


def _routed_post(record, lock):
    """按提示词内容分流：规划请求返回规划 JSON，成题请求返回对应轴的题目。"""

    def fake_post(url, **kwargs):
        prompt = kwargs["json"]["messages"][0]["content"]
        with lock:
            record.append(prompt)
        if "命题规划师" in prompt:
            return _chat_response(_PLAN_JSON)
        axis = _axis_from_prompt(prompt)
        return _chat_response(
            json.dumps({"stem": _DRAFTS[axis], "answer": "答案"}, ensure_ascii=False)
        )

    return fake_post


def test_pipeline_calls_plan_then_drafts(monkeypatch):
    record: list = []
    lock = threading.Lock()
    monkeypatch.setattr(httpx, "post", _routed_post(record, lock))

    result = _generator().generate(
        _ORIGINAL,
        "",
        3,
        subject="math",
        question_type="解答题",
        knowledge_points=["二次函数"],
    )

    plan_prompts = [prompt for prompt in record if "命题规划师" in prompt]
    draft_prompts = [prompt for prompt in record if "命题规划师" not in prompt]
    assert len(plan_prompts) == 1
    assert len(draft_prompts) == 3
    # 成题阶段不携带原题，避免句式锚点
    assert all(_ORIGINAL not in prompt for prompt in draft_prompts)
    assert [variant["axis"] for variant in result.variants] == ["A", "B", "C"]
    assert result.exam_point == "二次函数在闭区间上的最值"


def test_similar_variant_is_rewritten(monkeypatch):
    record: list = []
    lock = threading.Lock()

    def fake_post(url, **kwargs):
        prompt = kwargs["json"]["messages"][0]["content"]
        with lock:
            record.append(prompt)
        if "命题规划师" in prompt:
            return _chat_response(_PLAN_JSON)
        if "上一版" in prompt:
            return _chat_response(
                json.dumps({"stem": _DRAFTS["B"], "answer": "答案"}, ensure_ascii=False)
            )
        return _chat_response(
            json.dumps({"stem": _ORIGINAL, "answer": "答案"}, ensure_ascii=False)
        )

    monkeypatch.setattr(httpx, "post", fake_post)

    result = _generator().generate(_ORIGINAL, "", 1, subject="math")
    assert len(result.variants) == 1
    assert result.variants[0]["stem"] == _DRAFTS["B"]
    assert any("上一版" in prompt for prompt in record)


def test_plan_parse_failure_falls_back(monkeypatch):
    record: list = []
    lock = threading.Lock()

    def fake_post(url, **kwargs):
        prompt = kwargs["json"]["messages"][0]["content"]
        with lock:
            record.append(prompt)
        if "命题规划师" in prompt:
            return _chat_response("这不是 JSON")
        return _chat_response(
            json.dumps(
                {"variants": [{"stem": _DRAFTS["C"], "answer": "答案"}]},
                ensure_ascii=False,
            )
        )

    monkeypatch.setattr(httpx, "post", fake_post)

    result = _generator().generate(_ORIGINAL, "", 1, subject="math")
    assert len(result.variants) == 1
    assert result.variants[0]["stem"] == _DRAFTS["C"]
    assert len([prompt for prompt in record if "命题规划师" in prompt]) == 1
