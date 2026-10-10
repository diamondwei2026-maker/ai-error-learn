"""OCR 服务单测：通过注入 FakeClient 覆盖成功 / 降级 / 错误码映射（TDD）。"""

import json

import pytest

from app.services.aliyun_ocr import (
    CODE_OCR_FAILED,
    CODE_QUOTA_EXCEEDED,
    CODE_SERVICE_UNAVAILABLE,
    OcrError,
    OcrService,
    extract_text,
)

_DATA = json.dumps({"content": "hello world", "height": 100, "width": 100}, ensure_ascii=False)


class FakeSdkError(Exception):
    """模拟阿里云 SDK 抛出的 TeaException（含 code 属性）。"""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class FakeClient:
    """可编排的 OCR 客户端替身。"""

    def __init__(self, responses=None, errors=None):
        self.responses = responses or {}
        self.errors = errors or {}
        self.calls = []

    def recognize(self, image_bytes, mode):
        self.calls.append(mode)
        if mode in self.errors:
            raise self.errors[mode]
        return self.responses.get(mode, "")


def test_success_uses_advanced_first():
    client = FakeClient(responses={"advanced": _DATA})
    outcome = OcrService(client).recognize(b"img")
    assert outcome.text == "hello world"
    assert outcome.words_count == 10
    assert client.calls == ["advanced"]


def test_falls_back_to_general_when_advanced_fails():
    client = FakeClient(
        responses={"general": json.dumps({"content": "fallback"}, ensure_ascii=False)},
        errors={"advanced": FakeSdkError("InvalidImage", "advanced unavailable")},
    )
    outcome = OcrService(client).recognize(b"img")
    assert outcome.text == "fallback"
    assert client.calls == ["advanced", "general"]


def test_quota_error_maps_to_1003_without_fallback():
    throttling = FakeSdkError("Throttling.User", "request flow control exceeded")
    client = FakeClient(errors={"advanced": throttling, "general": throttling})
    with pytest.raises(OcrError) as excinfo:
        OcrService(client).recognize(b"img")
    assert excinfo.value.code == CODE_QUOTA_EXCEEDED
    assert client.calls == ["advanced"]


def test_generic_error_maps_to_1002():
    err = FakeSdkError("InvalidParameter", "bad image")
    client = FakeClient(errors={"advanced": err, "general": err})
    with pytest.raises(OcrError) as excinfo:
        OcrService(client).recognize(b"img")
    assert excinfo.value.code == CODE_OCR_FAILED
    assert client.calls == ["advanced", "general"]


def test_service_not_open_maps_to_1005_without_fallback():
    err = FakeSdkError("ocrServiceNotOpen", "You have not activated the OCR service.")
    client = FakeClient(errors={"advanced": err, "general": err})
    with pytest.raises(OcrError) as excinfo:
        OcrService(client).recognize(b"img")
    assert excinfo.value.code == CODE_SERVICE_UNAVAILABLE
    assert client.calls == ["advanced"]


def test_unconfigured_client_reports_1002():
    service = OcrService(None)
    with pytest.raises(OcrError) as excinfo:
        service.recognize(b"img")
    assert excinfo.value.code == CODE_OCR_FAILED


def test_empty_data_returns_empty_text():
    client = FakeClient(responses={"advanced": ""})
    outcome = OcrService(client).recognize(b"img")
    assert outcome.text == ""
    assert outcome.words_count == 0


def test_extract_text_handles_shapes():
    assert extract_text("") == ""
    assert extract_text("not-json") == "not-json"
    assert extract_text(json.dumps({"content": "x"})) == "x"
    assert extract_text(json.dumps({"Content": "y"})) == "y"
    assert extract_text(b'{"content":"z"}') == "z"
