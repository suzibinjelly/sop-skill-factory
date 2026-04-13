#!/usr/bin/env python3
"""schema.py - 要素注册表 + 类型信号 + Pydantic 数据模型

提供所有 9 种 Skill 类型的要素定义和结构校验模型。
"""

import argparse
import json
import sys
from typing import Any, Optional

from pydantic import BaseModel, Field

# ── 类型识别信号 ──
TYPE_SIGNALS = {
    "sequential": {
        "keywords": [
            "第一步", "第二步", "步骤", "流程", "然后", "接着", "首先", "最后", "顺序",
            "step", "first", "then", "next", "finally", "procedure", "workflow"
        ],
        "patterns": [r"第[一二三四五六七八九十\d]+步", r"步骤\s*\d+"],
        "strong_signals": ["步骤", "流程", "step", "procedure"],
        "negative_signals": ["指标", "阈值", "告警", "metric", "threshold"]
    },
    "conditional": {
        "keywords": [
            "如果", "否则", "条件", "分支", "根据", "区分", "不同情况", "视...而定",
            "if", "else", "otherwise", "depending on", "branch", "case"
        ],
        "patterns": [r"如果.*则", r"若.*则", r"根据.*分为"],
        "strong_signals": ["分支", "条件", "branch", "case"],
        "negative_signals": []
    },
    "checklist": {
        "keywords": [
            "检查项", "通过标准", "核对", "审查", "验收", "是否", "合格",
            "check", "verify", "review", "acceptance criteria", "pass/fail"
        ],
        "patterns": [r"[☐☑✓✗]", r"是否.*\?"],
        "strong_signals": ["检查项", "通过标准", "checklist", "acceptance criteria"],
        "negative_signals": []
    },
    "template": {
        "keywords": [
            "模板", "变量", "填写", "占位", "格式",
            "template", "variable", "placeholder", "fill in"
        ],
        "patterns": [r"\{\{.*?\}\}", r"《.*?》"],
        "strong_signals": ["模板", "变量", "template", "variable"],
        "negative_signals": []
    },
    "knowledge": {
        "keywords": [
            "什么是", "定义", "含义", "解释", "常见问题", "FAQ", "问答",
            "what is", "definition", "Q&A", "guide", "FAQ"
        ],
        "patterns": [r"Q[：:]", r"问[：:]", r"什么是"],
        "strong_signals": ["FAQ", "常见问题", "问答"],
        "negative_signals": ["步骤", "流程", "step"]
    },
    "decision": {
        "keywords": [
            "选择", "评估", "对比", "打分", "权重", "推荐", "方案",
            "evaluate", "compare", "score", "weight", "recommend", "pros/cons"
        ],
        "patterns": [r"优缺点", r"对比表"],
        "strong_signals": ["权重", "评分", "weight", "score"],
        "negative_signals": []
    },
    "monitoring": {
        "keywords": [
            "指标", "阈值", "告警", "监控", "巡检", "故障", "排查", "性能",
            "metric", "threshold", "alert", "monitor", "incident", "troubleshoot"
        ],
        "patterns": [r"超过\s*\d+", r"低于\s*\d+"],
        "strong_signals": ["告警", "阈值", "alert", "threshold"],
        "negative_signals": ["步骤", "流程"]
    },
    "approval": {
        "keywords": [
            "审批", "核准", "签字", "授权", "审批人", "流程节点", "驳回", "同意",
            "approve", "approval", "authorize", "reject", "sign off"
        ],
        "patterns": [r"审批.*流", r"待.*审批", r"审批链"],
        "strong_signals": ["审批", "核准", "approve", "approval"],
        "negative_signals": []
    }
}

# hybrid 类型无独立信号，由其他类型组合判断
SUPPORTED_TYPES = list(TYPE_SIGNALS.keys()) + ["hybrid"]

# ── 要素注册表 ──
ELEMENT_REGISTRY = {
    "common": {
        "metadata": {
            "required": True,
            "fields": ["name", "description"],
            "optional_fields": ["allowed_tools"],
            "notes": "frontmatter 只支持 name/description/allowed-tools"
        },
        "inputs": {
            "required": True,
            "fields": ["param_name", "type", "required", "description"]
        },
        "constraints": {
            "required": True,
            "fields": ["constraint", "reason"]
        },
        "quality_gates": {
            "required": True,
            "fields": ["check_item", "method", "pass_criteria"]
        },
        "sources": {
            "required": True,
            "fields": ["element", "source_file", "source_section"]
        }
    },
    "sequential": {
        "steps": {
            "required": True,
            "item_schema": {
                "step_id": "str", "name": "str", "description": "str",
                "preconditions": "list[str]", "inputs": "list[str]",
                "outputs": "list[str]", "on_failure": "str"
            }
        },
        "rollback_strategy": {"required": False},
        "estimated_duration": {"required": False}
    },
    "conditional": {
        "branches": {
            "required": True,
            "item_schema": {
                "condition": "str", "description": "str",
                "steps": {
                    "type": "list_of_step",
                    "item_schema": {
                        "step_id": "str", "description": "str", "on_failure": "str"
                    }
                }
            }
        },
        "merge_point": {"required": False},
        "default_branch": {"required": True}
    },
    "checklist": {
        "items": {
            "required": True,
            "item_schema": {
                "item_id": "str", "category": "str", "name": "str",
                "description": "str", "severity": "str", "check_method": "str",
                "pass_criteria": "str", "fix_suggestion": "str"
            }
        }
    },
    "template": {
        "template_raw": {"required": True},
        "variables": {
            "required": True,
            "item_schema": {
                "name": "str", "type": "str", "required": "bool",
                "default": "str", "source": "str"
            }
        },
        "format_requirements": {"required": False},
        "fill_example": {"required": True}
    },
    "knowledge": {
        "entries": {
            "required": True,
            "item_schema": {
                "topic": "str", "content": "str", "scope": "str",
                "related": "list[str]", "source": "str"
            }
        },
        "index_structure": {"required": False}
    },
    "decision": {
        "dimensions": {
            "required": True,
            "item_schema": {
                "name": "str", "weight": "number", "options": "list[str]"
            }
        },
        "scoring_rules": {"required": True},
        "recommendation_logic": {"required": True},
        "decision_example": {"required": False}
    },
    "monitoring": {
        "metrics": {
            "required": True,
            "item_schema": {
                "name": "str", "threshold_normal": "str",
                "threshold_warning": "str", "threshold_critical": "str"
            }
        },
        "actions": {"required": True},
        "escalation_path": {"required": True}
    },
    "approval": {
        "approvers": {
            "required": True,
            "item_schema": {
                "role": "str", "condition": "str", "is_required": "bool"
            }
        },
        "approval_chain": {
            "required": True,
            "item_schema": {
                "step_id": "str", "approver_role": "str",
                "action": "str", "sla": "str"
            }
        },
        "rejection_handling": {"required": True},
        "delegation_rules": {"required": False}
    },
    "hybrid": {
        "sub_skills": {
            "required": True,
            "item_schema": {
                "name": "str", "type": "str", "elements": "dict"
            },
            "validation_rule": "validator.py 根据 sub_skill.type 分发到对应类型 schema 校验"
        },
        "coordination_logic": {"required": True},
        "data_flow": {
            "required": False,
            "item_schema": {
                "from_sub": "str", "to_sub": "str",
                "from_output": "str", "to_input": "str"
            }
        }
    }
}

# ── Pydantic 数据模型 ──

class StepModel(BaseModel):
    step_id: str
    name: str = ""
    description: str
    preconditions: list[str] = Field(default_factory=list)
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    on_failure: str = ""

class BranchStepModel(BaseModel):
    step_id: str
    description: str
    on_failure: str = ""

class BranchModel(BaseModel):
    condition: str
    description: str
    steps: list[BranchStepModel] = Field(default_factory=list)

class CheckItemModel(BaseModel):
    item_id: str
    category: str
    name: str
    description: str
    severity: str
    check_method: str
    pass_criteria: str
    fix_suggestion: str

class TemplateVariableModel(BaseModel):
    name: str
    type: str
    required: bool
    default: str = ""
    source: str = ""

class KnowledgeEntryModel(BaseModel):
    topic: str
    content: str
    scope: str = ""
    related: list[str] = Field(default_factory=list)
    source: str = ""

class DecisionDimensionModel(BaseModel):
    name: str
    weight: float
    options: list[str] = Field(default_factory=list)

class MetricModel(BaseModel):
    name: str
    threshold_normal: str
    threshold_warning: str
    threshold_critical: str

class ApproverModel(BaseModel):
    role: str
    condition: str = ""
    is_required: bool = True

class ApprovalChainStepModel(BaseModel):
    step_id: str
    approver_role: str
    action: str
    sla: str = ""

class SubSkillModel(BaseModel):
    name: str
    type: str
    elements: dict = Field(default_factory=dict)

class DataFlowModel(BaseModel):
    from_sub: str
    to_sub: str
    from_output: str
    to_input: str

class InputParamModel(BaseModel):
    param_name: str
    type: str
    required: bool
    description: str

class ConstraintModel(BaseModel):
    constraint: str
    reason: str

class QualityGateModel(BaseModel):
    check_item: str
    method: str
    pass_criteria: str

class SourceModel(BaseModel):
    element: str
    source_file: str
    source_section: str


def get_blueprint(skill_type: str) -> dict:
    """根据类型返回要素蓝图（公共 + 类型特有）"""
    if skill_type not in ELEMENT_REGISTRY:
        raise ValueError(f"Unknown skill type: {skill_type}. Supported: {SUPPORTED_TYPES}")

    common = ELEMENT_REGISTRY["common"]
    type_specific = ELEMENT_REGISTRY.get(skill_type, {})

    return {
        "meta": {
            "skill_type": skill_type,
            "generated_by": "schema.py"
        },
        "common_elements": common,
        "type_specific_elements": type_specific
    }


def main():
    parser = argparse.ArgumentParser(description="Schema blueprint generator")
    parser.add_argument("--type", required=True, help="Skill type name")
    parser.add_argument("--output", required=True, help="Output JSON file path")
    args = parser.parse_args()

    try:
        blueprint = get_blueprint(args.type)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    try:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(blueprint, f, ensure_ascii=False, indent=2)
        print(f"Blueprint written to {args.output}")
    except (IOError, PermissionError) as e:
        print(f"IO error: {e}", file=sys.stderr)
        sys.exit(3)


if __name__ == "__main__":
    main()
