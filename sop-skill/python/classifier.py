#!/usr/bin/env python3
"""Pre-classify documents by analyzing keyword and pattern signals.

Produces type scores and recommendations from phase-1 scan output.

CLI:
    python classifier.py --input <phase1_scan.json> --output <phase2_classify.json>

Exit codes: 0=success, 1=business error, 2=JSON error, 3=IO/permission error.
"""

import argparse
import json
import re
import sys

# ---------------------------------------------------------------------------
# Type signal definitions (embedded directly as per specification)
# ---------------------------------------------------------------------------

TYPE_SIGNALS = {
    "sequential": {
        "keywords": [
            "第一步", "第二步", "步骤", "流程", "然后", "接着", "首先", "最后",
            "顺序", "step", "first", "then", "next", "finally", "procedure",
            "workflow",
        ],
        "patterns": [r"第[一二三四五六七八九十\d]+步", r"步骤\s*\d+"],
        "strong_signals": ["步骤", "流程", "step", "procedure"],
        "negative_signals": ["指标", "阈值", "告警", "metric", "threshold"],
    },
    "conditional": {
        "keywords": [
            "如果", "否则", "条件", "分支", "根据", "区分", "不同情况",
            "视...而定", "if", "else", "otherwise", "depending on", "branch",
            "case",
        ],
        "patterns": [r"如果.*则", r"若.*则", r"根据.*分为"],
        "strong_signals": ["分支", "条件", "branch", "case"],
        "negative_signals": [],
    },
    "checklist": {
        "keywords": [
            "检查项", "通过标准", "核对", "审查", "验收", "是否", "合格",
            "check", "verify", "review", "acceptance criteria", "pass/fail",
        ],
        "patterns": [r"[☐☑✓✗]", r"是否.*\?"],
        "strong_signals": ["检查项", "通过标准", "checklist", "acceptance criteria"],
        "negative_signals": [],
    },
    "template": {
        "keywords": [
            "模板", "变量", "填写", "占位", "格式", "template", "variable",
            "placeholder", "fill in",
        ],
        "patterns": [r"\{\{.*?\}\}", r"《.*?》"],
        "strong_signals": ["模板", "变量", "template", "variable"],
        "negative_signals": [],
    },
    "knowledge": {
        "keywords": [
            "什么是", "定义", "含义", "解释", "常见问题", "FAQ", "问答",
            "what is", "definition", "Q&A", "guide", "FAQ",
        ],
        "patterns": [r"Q[：:]", r"问[：:]", r"什么是"],
        "strong_signals": ["FAQ", "常见问题", "问答"],
        "negative_signals": ["步骤", "流程", "step"],
    },
    "decision": {
        "keywords": [
            "选择", "评估", "对比", "打分", "权重", "推荐", "方案",
            "evaluate", "compare", "score", "weight", "recommend", "pros/cons",
        ],
        "patterns": [r"优缺点", r"对比表"],
        "strong_signals": ["权重", "评分", "weight", "score"],
        "negative_signals": [],
    },
    "monitoring": {
        "keywords": [
            "指标", "阈值", "告警", "监控", "巡检", "故障", "排查", "性能",
            "metric", "threshold", "alert", "monitor", "incident",
            "troubleshoot",
        ],
        "patterns": [r"超过\s*\d+", r"低于\s*\d+"],
        "strong_signals": ["告警", "阈值", "alert", "threshold"],
        "negative_signals": ["步骤", "流程"],
    },
    "approval": {
        "keywords": [
            "审批", "核准", "签字", "授权", "审批人", "流程节点", "驳回",
            "同意", "approve", "approval", "authorize", "reject", "sign off",
        ],
        "patterns": [r"审批.*流", r"待.*审批", r"审批链"],
        "strong_signals": ["审批", "核准", "approve", "approval"],
        "negative_signals": [],
    },
}


def _count_keyword(text: str, keyword: str, limit: int) -> int:
    """Return the number of occurrences of *keyword* in *text* (case-insensitive), capped at *limit*."""
    if not keyword:
        return 0
    count = text.lower().count(keyword.lower())
    return min(count, limit)


def _score_file_for_type(text: str, type_name: str) -> float:
    """Compute the raw signal score for a single file / single type."""
    signals = TYPE_SIGNALS[type_name]
    score = 0.0

    # Normal keywords: +1 each, max 5 per keyword
    for kw in signals["keywords"]:
        score += _count_keyword(text, kw, limit=5) * 1

    # Strong signals: +2 each, max 5 per keyword
    for kw in signals["strong_signals"]:
        score += _count_keyword(text, kw, limit=5) * 2

    # Negative signals: -1 each, max 3 per keyword
    for kw in signals["negative_signals"]:
        score += _count_keyword(text, kw, limit=3) * (-1)

    # Pattern matches: +3 per unique match
    for pat in signals["patterns"]:
        matches = re.findall(pat, text)
        score += len(matches) * 3

    return score


def classify_file(text: str) -> dict[str, float]:
    """Return {type_name: raw_score} for a single file."""
    scores: dict[str, float] = {}
    for type_name in TYPE_SIGNALS:
        scores[type_name] = _score_file_for_type(text, type_name)
    return scores


def normalize_scores(raw: dict[str, float]) -> dict[str, float]:
    """Normalize per-file raw scores so they sum to 1 (or all zero)."""
    total = sum(raw.values())
    if total == 0:
        return {k: 0.0 for k in raw}
    return {k: v / total for k, v in raw.items()}


def aggregate_per_file(
    per_file_data: list[tuple[dict[str, float], int]],
) -> dict[str, float]:
    """Weighted-average of per-file normalized scores, weighted by char_count.

    *per_file_data* is a list of (normalized_scores, char_count).
    """
    if not per_file_data:
        return {t: 0.0 for t in TYPE_SIGNALS}

    total_chars = sum(cc for _, cc in per_file_data)
    if total_chars == 0:
        return {t: 0.0 for t in TYPE_SIGNALS}

    aggregated: dict[str, float] = {t: 0.0 for t in TYPE_SIGNALS}
    for norm_scores, char_count in per_file_data:
        weight = char_count / total_chars
        for t in TYPE_SIGNALS:
            aggregated[t] += norm_scores.get(t, 0.0) * weight
    return aggregated


def build_top3(aggregated: dict[str, float]) -> list[dict]:
    """Return top-3 types sorted by score descending."""
    sorted_types = sorted(aggregated.items(), key=lambda x: x[1], reverse=True)
    return [{"type": t, "score": round(s, 2)} for t, s in sorted_types[:3]]


def build_suggestion(top3: list[dict]) -> tuple:
    """Return (suggestion, confidence) from the top-3 list.

    If nothing scored, default to 'sequential' with confidence 0.
    """
    if not top3 or top3[0]["score"] == 0:
        return "sequential", 0.0
    return top3[0]["type"], top3[0]["score"]


def process_scan(scan_data: dict) -> dict:
    """Run classification over a phase-1 scan payload and return the output dict."""
    files = scan_data.get("files", [])
    per_file_results: list[dict] = []
    per_file_weighted: list[tuple[dict[str, float], int]] = []
    classified_count = 0

    for entry in files:
        rel_path = entry.get("file", entry.get("path", ""))
        full_text = entry.get("full_text")
        preview = entry.get("preview")
        error = entry.get("error")

        # Choose text source
        text = full_text if full_text is not None else preview
        if text is None:
            # Skip files with no usable text
            per_file_results.append({
                "file": rel_path,
                "signals": {},
                "error": error or "no text available",
            })
            continue

        char_count = len(text)
        raw_scores = classify_file(text)
        norm = normalize_scores(raw_scores)

        # Only keep types with non-zero normalized scores for per-file output
        signals = {t: round(v, 2) for t, v in norm.items() if v > 0}

        per_file_results.append({
            "file": rel_path,
            "signals": signals,
            "error": None,
        })
        per_file_weighted.append((norm, char_count))
        classified_count += 1

    aggregated = aggregate_per_file(per_file_weighted)
    # Round aggregated scores
    aggregated = {t: round(v, 2) for t, v in aggregated.items()}

    top3 = build_top3(aggregated)
    suggestion, confidence = build_suggestion(top3)

    # Build the aggregated section in the exact output order
    output = {
        "meta": {
            "scan_ref": scan_data.get("meta", {}).get("input_path", ""),
            "classified_files": classified_count,
        },
        "per_file": per_file_results,
        "aggregated": {
            "type_scores": aggregated,
            "top3": top3,
            "confidence": confidence,
            "suggestion": suggestion,
        },
    }
    return output


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pre-classify documents by analyzing keyword and pattern signals.",
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to phase1_scan.json",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path to write phase2_classify.json",
    )
    args = parser.parse_args()

    # Read input ------------------------------------------------------------------
    try:
        with open(args.input, "r", encoding="utf-8") as fh:
            raw = fh.read()
    except (OSError, PermissionError) as exc:
        print(f"IO error reading input: {exc}", file=sys.stderr)
        sys.exit(3)

    try:
        scan_data = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"JSON parse error: {exc}", file=sys.stderr)
        sys.exit(2)

    # Classify --------------------------------------------------------------------
    try:
        result = process_scan(scan_data)
    except Exception as exc:
        print(f"Business error during classification: {exc}", file=sys.stderr)
        sys.exit(1)

    # Write output ----------------------------------------------------------------
    try:
        with open(args.output, "w", encoding="utf-8") as fh:
            json.dump(result, fh, ensure_ascii=False, indent=2)
    except (OSError, PermissionError) as exc:
        print(f"IO error writing output: {exc}", file=sys.stderr)
        sys.exit(3)

    print(f"Classification complete. {result['meta']['classified_files']} files classified.")
    sys.exit(0)


if __name__ == "__main__":
    main()
