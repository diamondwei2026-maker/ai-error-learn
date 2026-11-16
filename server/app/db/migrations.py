"""轻量列迁移：为存量表补齐新增列。

项目未引入 Alembic，`Base.metadata.create_all` 不会给已存在的表补列，
因此对存量库（开发 SQLite / 生产 MySQL）做幂等的 `ALTER TABLE ADD COLUMN`。
"""

from __future__ import annotations

from typing import Dict, List

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

# question_sync 复习排期列：列名 -> DDL 类型
QUESTION_SYNC_REVIEW_COLUMNS: Dict[str, str] = {
    "review_stage": "INTEGER NULL",
    "next_review_at": "BIGINT NULL",
    "last_reviewed_at": "BIGINT NULL",
}

# question_sync 内容哈希列（去重用）
QUESTION_SYNC_HASH_COLUMNS: Dict[str, str] = {
    "content_hash": "VARCHAR(64) NULL",
}

# question_sync 识题元信息列（学科 / 题型 / 知识点 JSON）
QUESTION_SYNC_META_COLUMNS: Dict[str, str] = {
    "subject": "VARCHAR(16) NULL",
    "question_type": "VARCHAR(16) NULL",
    "knowledge_points": "VARCHAR(255) NULL",
}


def _missing_columns(engine: Engine, table: str, columns: Dict[str, str]) -> List[str]:
    inspector = inspect(engine)
    if table not in inspector.get_table_names():
        return []
    existing = {column["name"] for column in inspector.get_columns(table)}
    return [name for name in columns if name not in existing]


def ensure_review_columns(engine: Engine) -> List[str]:
    """补齐 question_sync 的排期列，返回本次新增的列名（幂等）。"""
    missing = _missing_columns(engine, "question_sync", QUESTION_SYNC_REVIEW_COLUMNS)
    if not missing:
        return []

    with engine.begin() as conn:
        for name in missing:
            conn.execute(
                text(
                    f"ALTER TABLE question_sync ADD COLUMN {name} "
                    f"{QUESTION_SYNC_REVIEW_COLUMNS[name]}"
                )
            )
    return missing


def ensure_content_hash_column(engine: Engine) -> List[str]:
    """补齐 question_sync 的 content_hash 列（幂等）。"""
    missing = _missing_columns(engine, "question_sync", QUESTION_SYNC_HASH_COLUMNS)
    if not missing:
        return []

    with engine.begin() as conn:
        for name in missing:
            conn.execute(
                text(
                    f"ALTER TABLE question_sync ADD COLUMN {name} "
                    f"{QUESTION_SYNC_HASH_COLUMNS[name]}"
                )
            )
    return missing


def ensure_question_meta_columns(engine: Engine) -> List[str]:
    """补齐 question_sync 的识题元信息列（幂等，已有行保持 NULL）。"""
    missing = _missing_columns(engine, "question_sync", QUESTION_SYNC_META_COLUMNS)
    if not missing:
        return []

    with engine.begin() as conn:
        for name in missing:
            conn.execute(
                text(
                    f"ALTER TABLE question_sync ADD COLUMN {name} "
                    f"{QUESTION_SYNC_META_COLUMNS[name]}"
                )
            )
    return missing
