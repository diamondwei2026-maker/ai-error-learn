"""AI 能力预留（本期不实现）。

LangChain 接入点：后续实现一个 `VariantGenerator` 协议的类
（如 `LangChainVariantGenerator(model, prompt_template)`），
在 `app/main.py` 中替换 `DisabledVariantGenerator` 即可，接口与前端无需改动。
"""

from __future__ import annotations

from typing import List, Protocol, TypedDict, runtime_checkable


class Variant(TypedDict):
    stem: str
    answer: str


class AiDisabledError(Exception):
    """AI 功能未启用。"""

    def __init__(self, message: str = "AI 功能未启用"):
        super().__init__(message)
        self.message = message


@runtime_checkable
class VariantGenerator(Protocol):
    """变式题生成器协议（预留）。"""

    def generate(self, stem: str, count: int = 1) -> List[Variant]:
        ...


class DisabledVariantGenerator:
    """默认实现：AI 未启用，直接抛出。"""

    def generate(self, stem: str, count: int = 1) -> List[Variant]:
        raise AiDisabledError()
