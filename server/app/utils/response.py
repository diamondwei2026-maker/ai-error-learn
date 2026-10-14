"""统一成功响应信封。"""

from __future__ import annotations

from typing import Any, Dict


def ok(data: Any = None) -> Dict[str, Any]:
    """构造成功响应：{ code: 0, message: 'ok', data: {...} }。"""
    return {"code": 0, "message": "ok", "data": data if data is not None else {}}
