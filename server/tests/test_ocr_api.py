"""OCR HTTP 接口单测：通过注入服务替身覆盖成功与各错误码（TDD）。"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.ocr import create_ocr_router
from app.services.aliyun_ocr import (
    CODE_IMAGE_TOO_LARGE,
    CODE_OCR_FAILED,
    OcrError,
    OcrOutcome,
)

MAX_BYTES = 10 * 1024 * 1024


class StubService:
    def __init__(self, outcome=None, error=None):
        self.outcome = outcome
        self.error = error
        self.received = None

    def recognize(self, image_bytes):
        self.received = image_bytes
        if self.error is not None:
            raise self.error
        return self.outcome


def make_client(service, max_bytes=MAX_BYTES):
    app = FastAPI()
    app.include_router(create_ocr_router(service, max_bytes), prefix="/api/v1")
    return TestClient(app)


def test_ocr_success():
    service = StubService(outcome=OcrOutcome(text="题干文本", words_count=4))
    resp = make_client(service).post(
        "/api/v1/ocr", files={"file": ("q.jpg", b"fake-image-bytes", "image/jpeg")}
    )
    assert resp.status_code == 200
    assert resp.json() == {"code": 0, "text": "题干文本", "wordsCount": 4}
    assert service.received == b"fake-image-bytes"


def test_ocr_empty_file_returns_1004():
    service = StubService(outcome=OcrOutcome(text="", words_count=0))
    resp = make_client(service).post(
        "/api/v1/ocr", files={"file": ("q.jpg", b"", "image/jpeg")}
    )
    assert resp.status_code == 200
    assert resp.json()["code"] == CODE_IMAGE_TOO_LARGE


def test_ocr_oversized_file_returns_1004():
    service = StubService(outcome=OcrOutcome(text="", words_count=0))
    resp = make_client(service, max_bytes=10).post(
        "/api/v1/ocr", files={"file": ("q.jpg", b"x" * 50, "image/jpeg")}
    )
    assert resp.json()["code"] == CODE_IMAGE_TOO_LARGE


def test_ocr_non_image_returns_1004():
    service = StubService(outcome=OcrOutcome(text="", words_count=0))
    resp = make_client(service).post(
        "/api/v1/ocr", files={"file": ("q.txt", b"hello", "text/plain")}
    )
    assert resp.json()["code"] == CODE_IMAGE_TOO_LARGE


def test_ocr_service_error_returns_1002():
    service = StubService(error=OcrError(CODE_OCR_FAILED, "识别失败"))
    resp = make_client(service).post(
        "/api/v1/ocr", files={"file": ("q.jpg", b"bytes", "image/jpeg")}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == CODE_OCR_FAILED
    assert body["message"] == "识别失败"


def test_health_endpoint_of_full_app():
    from app.main import create_app

    client = TestClient(create_app())
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
