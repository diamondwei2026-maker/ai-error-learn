"""识别 HTTP 接口单测：通过注入服务替身覆盖成功与各错误码（TDD）。"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.recognize import create_recognize_router
from app.services.vision_recognize import (
    CODE_IMAGE_TOO_LARGE,
    CODE_RECOGNIZE_FAILED,
    RecognizeError,
    RecognizeOutcome,
)

MAX_BYTES = 10 * 1024 * 1024


class StubService:
    def __init__(self, outcome=None, error=None):
        self.outcome = outcome
        self.error = error
        self.received = None
        self.received_mime = None

    def recognize(self, image_bytes, mime_type):
        self.received = image_bytes
        self.received_mime = mime_type
        if self.error is not None:
            raise self.error
        return self.outcome


def make_client(service, max_bytes=MAX_BYTES):
    app = FastAPI()
    app.include_router(create_recognize_router(service, max_bytes), prefix="/api/v1")
    return TestClient(app)


def test_recognize_success_returns_stem_and_answer():
    service = StubService(outcome=RecognizeOutcome(stem="题干", answer="42"))
    resp = make_client(service).post(
        "/api/v1/recognize", files={"file": ("q.jpg", b"fake-image-bytes", "image/jpeg")}
    )
    assert resp.status_code == 200
    assert resp.json() == {
        "code": 0,
        "text": "题干",
        "answer": "42",
        "splitMethod": "vlm",
        "wordsCount": 2,
    }
    assert service.received == b"fake-image-bytes"
    assert service.received_mime == "image/jpeg"


def test_recognize_success_without_answer():
    service = StubService(outcome=RecognizeOutcome(stem="题干文本", answer=""))
    resp = make_client(service).post(
        "/api/v1/recognize", files={"file": ("q.jpg", b"fake-image-bytes", "image/jpeg")}
    )
    assert resp.status_code == 200
    assert resp.json() == {
        "code": 0,
        "text": "题干文本",
        "answer": "",
        "splitMethod": "none",
        "wordsCount": 4,
    }


def test_recognize_empty_file_returns_1004():
    service = StubService(outcome=RecognizeOutcome(stem="", answer=""))
    resp = make_client(service).post(
        "/api/v1/recognize", files={"file": ("q.jpg", b"", "image/jpeg")}
    )
    assert resp.status_code == 200
    assert resp.json()["code"] == CODE_IMAGE_TOO_LARGE


def test_recognize_oversized_file_returns_1004():
    service = StubService(outcome=RecognizeOutcome(stem="", answer=""))
    resp = make_client(service, max_bytes=10).post(
        "/api/v1/recognize", files={"file": ("q.jpg", b"x" * 50, "image/jpeg")}
    )
    assert resp.json()["code"] == CODE_IMAGE_TOO_LARGE


def test_recognize_non_image_returns_1004():
    service = StubService(outcome=RecognizeOutcome(stem="", answer=""))
    resp = make_client(service).post(
        "/api/v1/recognize", files={"file": ("q.txt", b"hello", "text/plain")}
    )
    assert resp.json()["code"] == CODE_IMAGE_TOO_LARGE


def test_recognize_service_error_returns_code():
    service = StubService(error=RecognizeError(CODE_RECOGNIZE_FAILED, "识别失败"))
    resp = make_client(service).post(
        "/api/v1/recognize", files={"file": ("q.jpg", b"bytes", "image/jpeg")}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == CODE_RECOGNIZE_FAILED
    assert body["message"] == "识别失败"


def test_health_endpoint_of_full_app():
    from app.main import create_app

    client = TestClient(create_app())
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
