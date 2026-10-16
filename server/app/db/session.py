"""数据库引擎与会话管理。

开发期使用 SQLite；上线切换阿里云 RDS 时仅需改 DATABASE_URL，
业务代码与 ORM 模型不动。
"""

from __future__ import annotations

from typing import Generator, Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_current_settings
from app.db.base import Base

_engine: Optional[Engine] = None
_session_factory: Optional[sessionmaker[Session]] = None


def configure_database(url: Optional[str] = None) -> Engine:
    """（重新）装配引擎与会话工厂。url 缺省时读取当前配置。"""
    global _engine, _session_factory
    database_url = url or get_current_settings().database_url
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    _engine = create_engine(database_url, connect_args=connect_args, future=True)
    _session_factory = sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True)
    return _engine


def get_engine() -> Engine:
    if _engine is None:
        return configure_database()
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    if _session_factory is None:
        configure_database()
    assert _session_factory is not None
    return _session_factory


def init_db() -> None:
    """建表（幂等）。导入模型以确保元数据已注册。"""
    from app.models import media_check as _media_check  # noqa: F401
    from app.models import question_sync as _question_sync  # noqa: F401
    from app.models import user as _user  # noqa: F401

    Base.metadata.create_all(bind=get_engine())


def get_db() -> Generator[Session, None, None]:
    """FastAPI 依赖：请求级会话。"""
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()
