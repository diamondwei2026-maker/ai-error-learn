"""变式题离线评测：句式相似度、变化轴覆盖、答案完整性与可选语义相似度。

用途：对比提示词改造前后的生成质量，为“考点驱动命题”提供可回归的量化依据。

用法（在 server 目录执行）：
    python scripts/eval_variants.py                 # 调用真实模型，评测默认数据集
    python scripts/eval_variants.py --count 3       # 每道原题生成 3 道变式
    python scripts/eval_variants.py --mock          # 不调用模型，仅自检脚本可运行
    python scripts/eval_variants.py --semantic      # 额外计算句向量语义相似度
    python scripts/eval_variants.py --strict        # 指标不达标时退出码为 1

输出：控制台汇总 + JSON 结果文件（默认 scripts/out/variant-eval.json）。

指标说明：
- surface_sim_original：变式与原题的字符 3-gram Jaccard 最大值，越低越不像照抄
- surface_sim_pairwise：变式两两之间的字符 3-gram Jaccard 最大值，越低越互异
- opening_echo_rate：开头 10 字与原题完全相同的变式占比
- too_similar_rate：触发服务端相似度门禁（开头照抄或重合度超阈值）的变式占比
- axis_coverage：本组变式覆盖的不同变化轴数量（A-F）
- answer_rate：变式带答案的比例
- semantic_sim_original：与原题的句向量余弦最大值（--semantic，依赖 sentence_transformers）

阈值仅为初始建议值，应先用现有提示词的评测结果校准后再设定回归红线。
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import load_settings  # noqa: E402
from app.services.ai_service import (  # noqa: E402
    OPENING_ECHO_LEN,
    SIMILARITY_THRESHOLD,
    GlmVariantGenerator,
    VariantResult,
    char_ngram_jaccard,
    is_too_similar,
    normalize_axis,
    opening_echo,
)

DEFAULT_DATASET = Path(__file__).resolve().parent / "data" / "variant_eval_dataset.json"
DEFAULT_OUTPUT = Path(__file__).resolve().parent / "out" / "variant-eval.json"

# 初始建议阈值（用基线结果校准后再固定）
THRESHOLDS = {
    "surface_sim_original": 0.50,  # 均值不高于此值
    "surface_sim_pairwise": 0.75,  # 均值不高于此值
    "axis_coverage": 3.0,  # 均值不低于此值
    "answer_rate": 0.95,  # 均值不低于此值
    "opening_echo_rate": 0.20,  # 开头照抄比例不高于此值
    "too_similar_rate": 0.20,  # 超过服务端相似度阈值的比例不高于此值
}


def entropy(values: Iterable[str]) -> float:
    labels = [item for item in values if item]
    if len(labels) <= 1:
        return 0.0
    total = len(labels)
    counts = Counter(labels)
    return -sum(
        (count / total) * math.log2(count / total) for count in counts.values()
    )


def _max_pairwise(values: List[str]) -> float:
    best = 0.0
    for i in range(len(values)):
        for j in range(i + 1, len(values)):
            best = max(best, char_ngram_jaccard(values[i], values[j]))
    return best


def score_sample(item: Dict[str, Any], result: VariantResult) -> Dict[str, Any]:
    original = item.get("stem", "")
    stems = [variant["stem"] for variant in result.variants]
    axes = [normalize_axis(variant.get("axis", "")) for variant in result.variants]
    answered = [variant for variant in result.variants if variant.get("answer", "").strip()]
    echo_count = sum(1 for stem in stems if opening_echo(stem, original))
    too_similar_count = sum(1 for stem in stems if is_too_similar(stem, original)[0])
    total = len(stems)

    return {
        "id": item.get("id", ""),
        "variantCount": total,
        "surfaceSimOriginal": round(
            max((char_ngram_jaccard(original, stem) for stem in stems), default=0.0), 4
        ),
        "surfaceSimPairwise": round(_max_pairwise(stems), 4),
        "openingEchoRate": round(echo_count / total, 4) if total else 0.0,
        "tooSimilarRate": round(too_similar_count / total, 4) if total else 0.0,
        "axisCount": len({axis for axis in axes if axis}),
        "axisEntropy": round(entropy(axes), 4),
        "axes": axes,
        "answerRate": round(len(answered) / total, 4) if total else 0.0,
        "knowledgePoints": result.knowledge_points,
        "variants": [
            {
                "axis": variant.get("axis", ""),
                "stem": variant.get("stem", ""),
                "answer": variant.get("answer", ""),
            }
            for variant in result.variants
        ],
    }


def summarize(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not rows:
        return {}

    def mean(key: str) -> float:
        return round(sum(row[key] for row in rows) / len(rows), 4)

    summary = {
        "samples": len(rows),
        "surfaceSimOriginal": mean("surfaceSimOriginal"),
        "surfaceSimPairwise": mean("surfaceSimPairwise"),
        "openingEchoRate": mean("openingEchoRate"),
        "tooSimilarRate": mean("tooSimilarRate"),
        "axisCoverage": mean("axisCount"),
        "axisEntropy": mean("axisEntropy"),
        "answerRate": mean("answerRate"),
        "variantsPerSample": mean("variantCount"),
    }
    summary["checks"] = {
        "surfaceSimOriginal": summary["surfaceSimOriginal"]
        <= THRESHOLDS["surface_sim_original"],
        "surfaceSimPairwise": summary["surfaceSimPairwise"]
        <= THRESHOLDS["surface_sim_pairwise"],
        "openingEchoRate": summary["openingEchoRate"]
        <= THRESHOLDS["opening_echo_rate"],
        "tooSimilarRate": summary["tooSimilarRate"] <= THRESHOLDS["too_similar_rate"],
        "axisCoverage": summary["axisCoverage"] >= THRESHOLDS["axis_coverage"],
        "answerRate": summary["answerRate"] >= THRESHOLDS["answer_rate"],
    }
    summary["passed"] = all(summary["checks"].values())
    return summary


def semantic_scores(items: List[Dict[str, Any]], rows: List[Dict[str, Any]]) -> Tuple[Optional[List[float]], str]:
    """可选：计算变式与原题的句向量余弦最大值。缺少依赖时返回跳过原因。"""
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore
    except ImportError:
        return None, "未安装 sentence_transformers，跳过语义相似度"

    model_name = "paraphrase-multilingual-MiniLM-L12-v2"
    try:
        model = SentenceTransformer(model_name)
    except Exception as exc:  # noqa: BLE001 - 模型下载失败不阻断评测
        return None, f"加载 {model_name} 失败，跳过语义相似度：{exc}"

    scores: List[float] = []
    for item, row in zip(items, rows):
        stems = [variant["stem"] for variant in row["variants"]]
        if not stems:
            scores.append(0.0)
            continue
        embeddings = model.encode([item.get("stem", "")] + stems, normalize_embeddings=True)
        base, others = embeddings[0], embeddings[1:]
        scores.append(round(float(max(float(base @ vector) for vector in others)), 4))
        row["semanticSimOriginal"] = scores[-1]
    return scores, ""


class _MockGenerator:
    """仅用于脚本自检：返回可预期的模拟变式，不调用任何网络。"""

    def generate(
        self,
        stem: str,
        answer: str = "",
        count: int = 3,
        subject: str = "",
        question_type: str = "",
        knowledge_points: Optional[List[str]] = None,
    ) -> VariantResult:
        changed = re.sub(r"\d+", lambda match: str(int(match.group()) + 1), stem)
        variants = [
            {"axis": "B", "stem": changed, "answer": answer or "（模拟答案）"},
            {"axis": "A", "stem": f"某校开展实践活动时遇到问题：{stem}", "answer": answer or "（模拟答案）"},
            {"axis": "E", "stem": f"{stem}\n（2）若把条件中的数量翻倍，结论如何变化？", "answer": answer or "（模拟答案）"},
        ][: max(1, count)]
        return VariantResult(
            subject=subject or "other",
            question_type=question_type or "",
            knowledge_points=list(knowledge_points or []),
            variants=variants,
        )


def build_generator(mock: bool) -> Any:
    if mock:
        return _MockGenerator()
    settings = load_settings()
    if not settings.ai_configured:
        raise SystemExit(
            "AI 未配置：请在 server/.env 设置 AI_ENABLED=true、AI_API_KEY、AI_BASE_URL、AI_MODEL"
        )
    return GlmVariantGenerator(
        api_key=settings.ai_api_key,
        base_url=settings.ai_base_url,
        model=settings.ai_model,
        enabled=settings.ai_enabled,
        timeout=settings.ai_timeout,
    )


def load_dataset(path: Path) -> List[Dict[str, Any]]:
    if not path.is_file():
        raise SystemExit(f"数据集不存在：{path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not data:
        raise SystemExit("数据集必须是非空 JSON 数组")
    return data


def print_table(rows: List[Dict[str, Any]]) -> None:
    header = (
        f"{'ID':<14}{'题数':<6}{'原题相似':<10}{'互异相似':<10}"
        f"{'开头照抄':<10}{'过像率':<9}{'轴数':<6}{'答案率':<8}"
    )
    print(header)
    print("-" * len(header))
    for row in rows:
        print(
            f"{row['id']:<14}{row['variantCount']:<6}{row['surfaceSimOriginal']:<10}"
            f"{row['surfaceSimPairwise']:<10}{row['openingEchoRate']:<10}"
            f"{row['tooSimilarRate']:<9}{row['axisCount']:<6}{row['answerRate']:<8}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="变式题离线评测")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--count", type=int, default=3, help="每道原题生成数量")
    parser.add_argument("--mock", action="store_true", help="使用模拟生成器自检脚本")
    parser.add_argument("--semantic", action="store_true", help="计算句向量语义相似度")
    parser.add_argument("--strict", action="store_true", help="指标不达标时退出码为 1")
    args = parser.parse_args()

    items = load_dataset(args.dataset)
    generator = build_generator(args.mock)

    rows: List[Dict[str, Any]] = []
    for item in items:
        try:
            result = generator.generate(
                item.get("stem", ""),
                item.get("answer", ""),
                max(1, args.count),
                subject=item.get("subject", ""),
                question_type=item.get("questionType", ""),
                knowledge_points=item.get("knowledgePoints") or [],
            )
        except Exception as exc:  # noqa: BLE001 - 单题失败不影响整体评测
            print(f"[失败] {item.get('id', '')}: {type(exc).__name__}: {exc}", file=sys.stderr)
            rows.append(
                {
                    "id": item.get("id", ""),
                    "variantCount": 0,
                    "surfaceSimOriginal": 1.0,
                    "surfaceSimPairwise": 1.0,
                    "openingEchoRate": 0.0,
                    "tooSimilarRate": 0.0,
                    "axisCount": 0,
                    "axisEntropy": 0.0,
                    "axes": [],
                    "answerRate": 0.0,
                    "knowledgePoints": [],
                    "variants": [],
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
            continue
        rows.append(score_sample(item, result))

    semantic_note = ""
    if args.semantic:
        scores, semantic_note = semantic_scores(items, rows)
        if scores:
            avg = round(sum(scores) / len(scores), 4)
            print(f"语义相似度均值（与原题余弦最大值）：{avg}")
        else:
            print(semantic_note)

    summary = summarize([row for row in rows if not row.get("error")])
    print_table(rows)
    print()
    print(
        "汇总："
        f"样本 {summary.get('samples', 0)}；"
        f"原题句式相似 {summary.get('surfaceSimOriginal', 0)}；"
        f"变式互异相似 {summary.get('surfaceSimPairwise', 0)}；"
        f"开头照抄 {summary.get('openingEchoRate', 0)}；"
        f"过像率 {summary.get('tooSimilarRate', 0)}；"
        f"轴覆盖 {summary.get('axisCoverage', 0)}；"
        f"答案率 {summary.get('answerRate', 0)}"
    )
    for name, ok in (summary.get("checks") or {}).items():
        print(f"  {'通过' if ok else '未达标'}：{name}")
    print("阈值：", json.dumps(THRESHOLDS, ensure_ascii=False))

    report = {
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "mode": "mock" if args.mock else "live",
        "dataset": str(args.dataset),
        "count": args.count,
        "thresholds": THRESHOLDS,
        "similarityThreshold": SIMILARITY_THRESHOLD,
        "openingEchoLength": OPENING_ECHO_LEN,
        "semanticNote": semantic_note or ("已计算" if args.semantic else "未启用"),
        "summary": summary,
        "samples": rows,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"结果已写入：{args.out}")

    if args.strict and not summary.get("passed"):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
