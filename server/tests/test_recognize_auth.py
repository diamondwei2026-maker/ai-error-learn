"""识别接口鉴权单测（AUTH_REQUIRED 开关）。"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def _post_recognize(client: TestClient, headers=None):
    return client.post(
        "/api/v1/recognize",
        files={"file": ("q.jpg", b"fake-image-bytes", "image/jpeg")},
        headers=headers or {},
    )


def test_recognize_requires_auth_when_enabled(client):
    resp = _post_recognize(client)
    assert resp.status_code == 401
    assert resp.json()["code"] == 2001


def test_recognize_with_token_passes_auth_layer(client, auth_headers):
    resp = _post_recognize(client, headers=auth_headers)
    # 已通过鉴权层：未配置视觉模型时返回识别失败码，而非 2001
    assert resp.status_code == 200
    assert resp.json()["code"] != 2001


def test_recognize_without_auth_when_disabled(tmp_path):
    settings = Settings(
        jwt_secret="test-secret",
        wechat_app_secret="x",
        auth_required=False,
        database_url=f"sqlite:///{(tmp_path / 'no-auth.db').as_posix()}",
        uploads_root=str(tmp_path / "uploads"),
    )
    app = create_app(settings)
    with TestClient(app) as test_client:
        resp = _post_recognize(test_client)
    assert resp.status_code == 200
    assert resp.json()["code"] != 2001
