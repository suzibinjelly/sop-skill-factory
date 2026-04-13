#!/usr/bin/env python3
"""Quality gate checks on the final rendered SKILL.md output."""

import argparse
import json
import re
import sys

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Type-specific required keywords
# ---------------------------------------------------------------------------
TYPE_REQUIRED: dict[str, list[str]] = {
    "sequential": ["执行步骤"],
    "conditional": ["分支"],
    "checklist": ["检查项"],
    "template": ["模板变量", "模板原文"],
    "knowledge": ["知识条目"],
    "decision": ["决策维度"],
    "monitoring": ["监控指标"],
    "approval": ["审批人", "审批链路"],
    "hybrid": ["子技能"],
}

# ---------------------------------------------------------------------------
# Check helpers – each returns (blocking: list[dict], warnings: list[dict])
# ---------------------------------------------------------------------------

def check_frontmatter(content: str) -> tuple[list[dict], list[dict]]:
    """Check 1: YAML frontmatter completeness."""
    blocking: list[dict] = []
    warnings: list[dict] = []

    if yaml is None:
        blocking.append({
            "check": "frontmatter",
            "message": "yaml 模块不可用，无法解析 frontmatter",
        })
        return blocking, warnings

    m = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if not m:
        blocking.append({
            "check": "frontmatter",
            "message": "frontmatter 缺失或格式不正确",
        })
        return blocking, warnings

    raw = m.group(1)
    try:
        fm = yaml.safe_load(raw)
    except yaml.YAMLError:
        blocking.append({
            "check": "frontmatter",
            "message": "frontmatter YAML 解析失败",
        })
        return blocking, warnings

    if not isinstance(fm, dict):
        blocking.append({
            "check": "frontmatter",
            "message": "frontmatter 不是有效的 YAML 映射",
        })
        return blocking, warnings

    required_fields = ["name", "description"]
    missing = [f for f in required_fields if f not in fm or fm[f] is None]
    if missing:
        blocking.append({
            "check": "frontmatter",
            "message": f"frontmatter 缺少必填字段: {', '.join(missing)}",
        })
        return blocking, warnings

    name = str(fm["name"])
    if not re.match(r"^[a-z0-9-]{1,64}$", name):
        warnings.append({
            "check": "frontmatter",
            "message": f"name '{name}' 不匹配模式 ^[a-z0-9-]{{1,64}}$",
        })

    return blocking, warnings


def check_no_empty_placeholders(content: str) -> tuple[list[dict], list[dict]]:
    """Check 2: No empty placeholders like [ ], [TODO], [FIXME], [待补充], []."""
    blocking: list[dict] = []
    warnings: list[dict] = []

    # Remove markdown links [text](url) — they are NOT placeholders.
    cleaned = re.sub(r"\[([^\]]*)\]\([^)]*\)", "", content)

    patterns = [
        (r"\[\s*\]", "空占位符 []"),
        (r"\[\s*TODO\s*\]", "TODO 占位符"),
        (r"\[\s*FIXME\s*\]", "FIXME 占位符"),
        (r"\[\s*待补充\s*\]", "待补充 占位符"),
    ]

    for pat, desc in patterns:
        matches = re.findall(pat, cleaned, re.IGNORECASE)
        if matches:
            blocking.append({
                "check": "empty_placeholders",
                "message": f"发现未填充的{desc}",
            })
            break  # one hit is enough to block

    return blocking, warnings


def check_required_sections(content: str) -> tuple[list[dict], list[dict]]:
    """Check 3: Required ## sections exist."""
    blocking: list[dict] = []
    warnings: list[dict] = []

    required = ["概述", "约束条件", "质量验证", "参考来源"]
    headers = re.findall(r"^##\s+(.+)$", content, re.MULTILINE)

    missing = [s for s in required if not any(s in h for h in headers)]
    if missing:
        blocking.append({
            "check": "required_sections",
            "message": f"缺少必要章节: {', '.join(missing)}",
        })

    return blocking, warnings


def check_source_traceability(content: str) -> tuple[list[dict], list[dict]]:
    """Check 4: Source traceability markers present."""
    blocking: list[dict] = []
    warnings: list[dict] = []

    has_marker = "来源文件" in content
    has_table = bool(re.search(r"\|\s*要素\s*\|\s*来源文件", content))

    if not has_marker and not has_table:
        warnings.append({
            "check": "source_traceability",
            "message": "建议在参考来源中标注具体段落",
        })

    return blocking, warnings


def check_type_specific(content: str, skill_type: str) -> tuple[list[dict], list[dict]]:
    """Check 5: Type-specific required keywords."""
    blocking: list[dict] = []
    warnings: list[dict] = []

    if skill_type not in TYPE_REQUIRED:
        warnings.append({
            "check": "type_specific",
            "message": f"未知的技能类型 '{skill_type}'，跳过类型检查",
        })
        return blocking, warnings

    missing = [kw for kw in TYPE_REQUIRED[skill_type] if kw not in content]
    if missing:
        blocking.append({
            "check": "type_specific",
            "message": f"类型 '{skill_type}' 缺少必要关键字: {', '.join(missing)}",
        })

    return blocking, warnings


def check_table_format(content: str) -> tuple[list[dict], list[dict]]:
    """Check 6: Table rows are not empty."""
    blocking: list[dict] = []
    warnings: list[dict] = []

    table_lines = [line for line in content.splitlines() if line.startswith("|")]
    for line in table_lines:
        cells = [c.strip() for c in line.split("|")]
        # filter out empty strings from leading/trailing |
        non_empty = [c for c in cells if c]
        if not non_empty:
            warnings.append({
                "check": "table_format",
                "message": f"发现空表格行: {line}",
            })

    return blocking, warnings


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_checks(content: str, skill_type: str) -> dict:
    """Run all six quality gate checks and return the result dict."""
    all_blocking: list[dict] = []
    all_warnings: list[dict] = []

    checks = [
        check_frontmatter(content),
        check_no_empty_placeholders(content),
        check_required_sections(content),
        check_source_traceability(content),
        check_type_specific(content, skill_type),
        check_table_format(content),
    ]

    for b, w in checks:
        all_blocking.extend(b)
        all_warnings.extend(w)

    return {
        "passed": len(all_blocking) == 0,
        "blocking": all_blocking,
        "warnings": all_warnings,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Quality gate checks on the final rendered SKILL.md output"
    )
    parser.add_argument("--input", required=True, help="Path to phase5 output markdown")
    parser.add_argument("--type", required=True, help="Skill type identifier")
    parser.add_argument("--output", required=True, help="Path to write quality JSON result")
    args = parser.parse_args()

    # -- read input -----------------------------------------------------------
    try:
        with open(args.input, "r", encoding="utf-8") as fh:
            content = fh.read()
    except (OSError, IOError) as exc:
        print(f"IO error reading input: {exc}", file=sys.stderr)
        sys.exit(3)

    # -- run checks -----------------------------------------------------------
    result = run_checks(content, args.type)

    # -- write output ---------------------------------------------------------
    try:
        with open(args.output, "w", encoding="utf-8") as fh:
            json.dump(result, fh, ensure_ascii=False, indent=2)
    except (OSError, IOError, TypeError, ValueError) as exc:
        print(f"Error writing output: {exc}", file=sys.stderr)
        if isinstance(exc, (TypeError, ValueError)):
            sys.exit(2)
        sys.exit(3)

    # -- summary to stdout ----------------------------------------------------
    if result["passed"]:
        print("Quality gate PASSED")
        if result["warnings"]:
            print(f"  {len(result['warnings'])} warning(s)")
    else:
        print("Quality gate FAILED")
        for item in result["blocking"]:
            print(f"  BLOCKING: [{item['check']}] {item['message']}")


if __name__ == "__main__":
    main()
