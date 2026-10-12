"""识别结果文本清洗（纯函数，便于单测）。"""

from __future__ import annotations

import re

# 行内连续空白（含全角空格、制表符）压缩为单个半角空格
_INLINE_SPACE_RE = re.compile(r"[ \t\u3000]+")
_WHITESPACE_RE = re.compile(r"\s")


def clean_text(raw: str) -> str:
    """清洗识别原始文本。

    - 统一换行为 \\n（兼容 \\r\\n / \\r）
    - 去除每行首尾空白，压缩行内连续空白
    - 丢弃空行，合并多余换行
    - 空/全空白输入返回空字符串
    """
    if not raw:
        return ""
    text = raw.replace("\r\n", "\n").replace("\r", "\n")
    lines = []
    for line in text.split("\n"):
        cleaned = _INLINE_SPACE_RE.sub(" ", line).strip()
        if cleaned:
            lines.append(cleaned)
    return "\n".join(lines)


def count_words(text: str) -> int:
    """统计有效字数：忽略所有空白字符。"""
    if not text:
        return 0
    return len(_WHITESPACE_RE.sub("", text))
