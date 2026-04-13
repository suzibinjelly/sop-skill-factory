#!/usr/bin/env python3
"""
validator.py - Validates extracted JSON data against element schemas
and detects conflicts between sources.

CLI:
    python validator.py --input <phase4_extract.json> --output <phase4_validate.json>

Exit codes:
    0 = success
    1 = business error (validation failures)
    2 = JSON error
    3 = IO/permission error
"""

import argparse
import json
import os
import re
import sys

# Try to import sklearn for TF-IDF + cosine similarity
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity as sklearn_cosine_similarity

    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

ELEMENT_REGISTRY = {
    "common": {
        "metadata": {
            "required": True,
            "fields": ["name", "description"],
            "optional_fields": ["allowed_tools"],
        },
        "inputs": {
            "required": True,
            "fields": ["param_name", "type", "required", "description"],
        },
        "constraints": {"required": True, "fields": ["constraint", "reason"]},
        "quality_gates": {
            "required": True,
            "fields": ["check_item", "method", "pass_criteria"],
        },
        "sources": {
            "required": True,
            "fields": ["element", "source_file", "source_section"],
        },
    },
    "sequential": {
        "steps": {
            "required": True,
            "item_schema": {
                "step_id": "str",
                "name": "str",
                "description": "str",
                "preconditions": "list[str]",
                "inputs": "list[str]",
                "outputs": "list[str]",
                "on_failure": "str",
            },
        },
        "rollback_strategy": {"required": False},
        "estimated_duration": {"required": False},
    },
    "conditional": {
        "branches": {
            "required": True,
            "item_schema": {
                "condition": "str",
                "description": "str",
                "steps": {
                    "type": "list_of_step",
                    "item_schema": {
                        "step_id": "str",
                        "description": "str",
                        "on_failure": "str",
                    },
                },
            },
        },
        "merge_point": {"required": False},
        "default_branch": {"required": True},
    },
    "checklist": {
        "items": {
            "required": True,
            "item_schema": {
                "item_id": "str",
                "category": "str",
                "name": "str",
                "description": "str",
                "severity": "str",
                "check_method": "str",
                "pass_criteria": "str",
                "fix_suggestion": "str",
            },
        }
    },
    "template": {
        "template_raw": {"required": True},
        "variables": {
            "required": True,
            "item_schema": {
                "name": "str",
                "type": "str",
                "required": "bool",
                "default": "str",
                "source": "str",
            },
        },
        "format_requirements": {"required": False},
        "fill_example": {"required": True},
    },
    "knowledge": {
        "entries": {
            "required": True,
            "item_schema": {
                "topic": "str",
                "content": "str",
                "scope": "str",
                "related": "list[str]",
                "source": "str",
            },
        },
        "index_structure": {"required": False},
    },
    "decision": {
        "dimensions": {
            "required": True,
            "item_schema": {
                "name": "str",
                "weight": "number",
                "options": "list[str]",
            },
        },
        "scoring_rules": {"required": True},
        "recommendation_logic": {"required": True},
        "decision_example": {"required": False},
    },
    "monitoring": {
        "metrics": {
            "required": True,
            "item_schema": {
                "name": "str",
                "threshold_normal": "str",
                "threshold_warning": "str",
                "threshold_critical": "str",
            },
        },
        "actions": {"required": True},
        "escalation_path": {"required": True},
    },
    "approval": {
        "approvers": {
            "required": True,
            "item_schema": {
                "role": "str",
                "condition": "str",
                "is_required": "bool",
            },
        },
        "approval_chain": {
            "required": True,
            "item_schema": {
                "step_id": "str",
                "approver_role": "str",
                "action": "str",
                "sla": "str",
            },
        },
        "rejection_handling": {"required": True},
        "delegation_rules": {"required": False},
    },
    "hybrid": {
        "sub_skills": {
            "required": True,
            "item_schema": {
                "name": "str",
                "type": "str",
                "elements": "dict",
            },
        },
        "coordination_logic": {"required": True},
        "data_flow": {
            "required": False,
            "item_schema": {
                "from_sub": "str",
                "to_sub": "str",
                "from_output": "str",
                "to_input": "str",
            },
        },
    },
}


def check_field_type(value, expected_type_str):
    """Check whether *value* matches the type described by *expected_type_str*.

    Supported type strings: ``str``, ``bool``, ``number``, ``dict``,
    ``list[str]``, ``list_of_step``.
    """
    if expected_type_str == "str":
        return isinstance(value, str)
    if expected_type_str == "bool":
        return isinstance(value, bool)
    if expected_type_str == "number":
        return isinstance(value, (int, float))
    if expected_type_str == "dict":
        return isinstance(value, dict)
    if expected_type_str == "list[str]":
        return isinstance(value, list) and all(isinstance(v, str) for v in value)
    if expected_type_str == "list_of_step":
        return isinstance(value, list)
    return True


def _is_empty(value):
    """Return True if *value* should be treated as missing/empty."""
    if value is None:
        return True
    if isinstance(value, (list, dict, str)) and len(value) == 0:
        return True
    return False


# ---------------------------------------------------------------------------
# Schema-based validation helpers
# ---------------------------------------------------------------------------

def validate_item_schema(items, schema, element_name, blocking_issues):
    """Validate each item in *items* against *schema*.

    Appends issues to *blocking_issues* in-place.
    """
    if not isinstance(items, list):
        blocking_issues.append(
            {"element": element_name, "field": None, "error": "type_error",
             "detail": "expected a list"}
        )
        return

    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            blocking_issues.append(
                {"element": element_name, "field": f"[{idx}]",
                 "error": "type_error", "detail": "expected a dict"}
            )
            continue

        for field_name, field_type in schema.items():
            # Nested schema (e.g. ``steps`` inside ``branches``)
            if isinstance(field_type, dict):
                nested = item.get(field_name)
                if nested is None:
                    continue  # handled as missing field below if required
                if field_type.get("type") == "list_of_step" and isinstance(nested, list):
                    inner_schema = field_type.get("item_schema", {})
                    validate_item_schema(nested, inner_schema, element_name, blocking_issues)
                continue

            if field_name not in item:
                blocking_issues.append(
                    {"element": element_name, "field": field_name, "error": "missing"}
                )
                continue

            value = item[field_name]
            if value is not None and not check_field_type(value, field_type):
                blocking_issues.append(
                    {"element": element_name, "field": field_name, "error": "type_error",
                     "detail": f"expected {field_type}, got {type(value).__name__}"}
                )


def validate_element(element_name, element_spec, data, blocking_issues):
    """Validate a single element against its spec.

    Returns True when the element is present and was validated, False when
    missing/empty.
    """
    value = data.get(element_name)

    if _is_empty(value):
        if element_spec.get("required", False):
            blocking_issues.append(
                {"element": element_name, "field": None, "error": "missing"}
            )
        return False

    # Validate ``item_schema`` if present
    item_schema = element_spec.get("item_schema")
    if item_schema:
        validate_item_schema(value, item_schema, element_name, blocking_issues)

    return True


def validate_fields_element(element_name, element_spec, data, blocking_issues):
    """Validate an element that uses ``fields`` instead of ``item_schema``.

    This covers ``metadata``, ``inputs``, ``constraints``, ``quality_gates``,
    ``sources`` -- all of which are lists of dicts with required field names.
    """
    value = data.get(element_name)

    if _is_empty(value):
        if element_spec.get("required", False):
            blocking_issues.append(
                {"element": element_name, "field": None, "error": "missing"}
            )
        return False

    required_fields = element_spec.get("fields", [])
    optional_fields = element_spec.get("optional_fields", [])

    # ``metadata`` is a single dict; others are lists of dicts.
    if isinstance(value, dict):
        items = [value]
    elif isinstance(value, list):
        items = value
    else:
        blocking_issues.append(
            {"element": element_name, "field": None, "error": "type_error",
             "detail": "expected dict or list"}
        )
        return True

    all_fields = required_fields  # only check required
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            blocking_issues.append(
                {"element": element_name, "field": f"[{idx}]",
                 "error": "type_error", "detail": "expected a dict"}
            )
            continue
        for field_name in all_fields:
            if field_name not in item or item[field_name] is None:
                blocking_issues.append(
                    {"element": element_name, "field": field_name, "error": "missing"}
                )

    return True


# ---------------------------------------------------------------------------
# Hybrid sub-skill dispatch
# ---------------------------------------------------------------------------

def validate_hybrid_sub_skills(data, blocking_issues, warnings):
    """For hybrid types, dispatch each sub_skill to its own type validation."""
    sub_skills = data.get("sub_skills")
    if not isinstance(sub_skills, list):
        return

    for sub in sub_skills:
        if not isinstance(sub, dict):
            continue
        sub_type = sub.get("type", "")
        sub_elements = sub.get("elements", {})
        if not isinstance(sub_elements, dict):
            continue

        type_specific = ELEMENT_REGISTRY.get(sub_type, {})
        _validate_with_registry(sub_elements, type_specific, blocking_issues, warnings)


# ---------------------------------------------------------------------------
# Core registry-driven validation
# ---------------------------------------------------------------------------

def _validate_with_registry(data, registry, blocking_issues, warnings):
    """Validate *data* against every element definition in *registry*."""
    for element_name, element_spec in registry.items():
        has_item_schema = "item_schema" in element_spec
        has_fields = "fields" in element_spec

        if has_item_schema:
            present = validate_element(
                element_name, element_spec, data, blocking_issues
            )
        elif has_fields:
            present = validate_fields_element(
                element_name, element_spec, data, blocking_issues
            )
        else:
            # Simple presence check
            value = data.get(element_name)
            present = not _is_empty(value)
            if not present and element_spec.get("required", False):
                blocking_issues.append(
                    {"element": element_name, "field": None, "error": "missing"}
                )

        if not present and not element_spec.get("required", False):
            warnings.append(
                {
                    "element": element_name,
                    "message": "\u9009\u586b\u8981\u7d20\u672a\u586b\u5199\uff0c\u5efa\u8bae\u8865\u5145",
                }
            )


def validate_data(skill_type, data):
    """Top-level validation entry point.

    Returns ``(blocking_issues, warnings)``.
    """
    blocking_issues = []
    warnings = []

    # 1. Common elements
    common_registry = ELEMENT_REGISTRY.get("common", {})
    _validate_with_registry(data, common_registry, blocking_issues, warnings)

    # 2. Type-specific elements
    type_registry = ELEMENT_REGISTRY.get(skill_type, {})
    _validate_with_registry(data, type_registry, blocking_issues, warnings)

    # 3. Hybrid sub-skill dispatch
    if skill_type == "hybrid":
        validate_hybrid_sub_skills(data, blocking_issues, warnings)

    return blocking_issues, warnings


# ---------------------------------------------------------------------------
# Conflict detection
# ---------------------------------------------------------------------------

def _read_source_section(source_file, source_section):
    """Best-effort read of a section from a source file.

    Returns the raw text of the section or an empty string.
    """
    if not os.path.isfile(source_file):
        return ""
    try:
        with open(source_file, "r", encoding="utf-8") as fh:
            content = fh.read()
    except OSError:
        return ""

    # Try to locate a markdown heading matching *source_section*.
    pattern = re.compile(
        r"^#+\s*" + re.escape(source_section) + r"\s*\n(.*?)(?=\n#|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(content)
    if match:
        return match.group(1).strip()
    return content


def _compute_similarity(text_a, text_b):
    """Return a similarity score between *text_a* and *text_b*.

    Uses TF-IDF + cosine similarity when sklearn is available; falls back to
    an exact-match heuristic otherwise.
    """
    if HAS_SKLEARN:
        try:
            vectorizer = TfidfVectorizer()
            tfidf_matrix = vectorizer.fit_transform([text_a, text_b])
            score = sklearn_cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            return float(score)
        except ValueError:
            # Vocabulary may be empty
            return 1.0 if text_a == text_b else 0.0
    else:
        # Simple fallback: normalised longest common subsequence ratio via
        # difflib, but to keep imports minimal we do exact-match check.
        if text_a.strip() == text_b.strip():
            return 1.0
        return 0.0


def detect_conflicts(sources_data):
    """Detect conflicts among sources.

    *sources_data* is the value of the ``sources`` element (a list of dicts
    with keys ``element``, ``source_file``, ``source_section``).

    Returns a list of conflict dicts.
    """
    if not isinstance(sources_data, list):
        return []

    # Group by element name
    element_sources = {}
    for entry in sources_data:
        element_name = entry.get("element", "")
        source_file = entry.get("source_file", "")
        source_section = entry.get("source_section", "")
        if element_name not in element_sources:
            element_sources[element_name] = []
        element_sources[element_name].append(
            {"file": source_file, "section": source_section}
        )

    conflicts = []
    for element_name, src_list in element_sources.items():
        # Only care about elements sourced from multiple distinct files
        unique_files = {s["file"] for s in src_list}
        if len(unique_files) < 2:
            continue

        # Extract text from each source
        source_texts = []
        for src in src_list:
            text = _read_source_section(src["file"], src.get("section", ""))
            source_texts.append(
                {"file": src["file"], "section": src.get("section", ""), "text": text}
            )

        # Pairwise comparison
        for i in range(len(source_texts)):
            for j in range(i + 1, len(source_texts)):
                sim = _compute_similarity(
                    source_texts[i]["text"], source_texts[j]["text"]
                )
                if sim < 0.7:
                    conflicts.append(
                        {
                            "element": element_name,
                            "sources": [
                                {
                                    "file": source_texts[i]["file"],
                                    "text": source_texts[i]["text"][:500],
                                },
                                {
                                    "file": source_texts[j]["file"],
                                    "text": source_texts[j]["text"][:500],
                                },
                            ],
                            "similarity": round(sim, 4),
                        }
                    )

    return conflicts


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Validate extracted JSON data against element schemas"
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to phase4_extract.json",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path to write phase4_validate.json",
    )
    args = parser.parse_args()

    # ---- Read input -------------------------------------------------------
    try:
        with open(args.input, "r", encoding="utf-8") as fh:
            input_data = json.load(fh)
    except json.JSONDecodeError as exc:
        print(f"JSON parse error: {exc}", file=sys.stderr)
        sys.exit(2)
    except (OSError, PermissionError) as exc:
        print(f"IO/permission error: {exc}", file=sys.stderr)
        sys.exit(3)

    # ---- Extract meta & data ----------------------------------------------
    meta = input_data.get("meta", {})
    skill_type = meta.get("skill_type", "")
    data = input_data.get("data", {})

    if not skill_type:
        print("Missing meta.skill_type in input", file=sys.stderr)
        sys.exit(2)

    # ---- Validate ---------------------------------------------------------
    blocking_issues, warnings = validate_data(skill_type, data)

    # ---- Conflict detection -----------------------------------------------
    sources_element = data.get("sources")
    conflicts = detect_conflicts(sources_element) if sources_element else []

    # ---- Build output -----------------------------------------------------
    result = "pass" if not blocking_issues else "fail"

    output = {
        "meta": {"round": 1, "skill_type": skill_type},
        "result": result,
        "blocking_issues": blocking_issues,
        "warnings": warnings,
        "conflicts": conflicts,
    }

    # ---- Write output -----------------------------------------------------
    try:
        with open(args.output, "w", encoding="utf-8") as fh:
            json.dump(output, fh, ensure_ascii=False, indent=2)
    except (OSError, PermissionError) as exc:
        print(f"IO/permission error writing output: {exc}", file=sys.stderr)
        sys.exit(3)

    print(json.dumps(output, ensure_ascii=False, indent=2))

    if result == "fail":
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
