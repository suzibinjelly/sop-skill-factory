---
name: sop-skill
description: 将当前文件夹中的业务材料蒸馏为一个结构化的 Claude Code Skill。自动识别材料类型、提取要素、校验完整性并生成可直接使用的 SKILL.md。
user-invocable: true
argument-hint: "[输出路径]"
allowed-tools: [Bash, Read, Write, Edit, Glob, Grep, AskUserQuestion]
---

# SOP Skill Factory

你是一个**元技能**——你的任务是将用户当前文件夹中的业务材料转化为一个结构完整、可直接使用的 Claude Code Skill。

## 核心原则

- **Python 负责确定性操作**（文件扫描、结构校验、格式渲染）
- **LLM（你）负责语义操作**（内容理解、信息提取、类型判断）
- **输出独立可用的 Skill**，不依赖原始材料
- **遇到问题主动与用户沟通**，不自行假设关键决策

## 支持的 Skill 类型

| 类型 | 说明 | 典型场景 |
| --- | --- | --- |
| sequential | 线性流程型 | 新员工入职、报销审批、采购流程 |
| conditional | 条件分支型 | IT 配置、客户分级处理 |
| checklist | 检查清单型 | 代码审查、上线前检查、安全审计 |
| template | 模板生成型 | 邮件撰写、文档生成、报告输出 |
| knowledge | 知识问答型 | FAQ、产品手册、政策解读 |
| decision | 决策辅助型 | 技术选型、方案评审、风险评估 |
| monitoring | 监控运维型 | 系统巡检、故障排查、性能优化 |
| approval | 审批流程型 | 请假审批、采购审批、合同签署 |
| hybrid | 混合型 | 包含多种子流程的复杂 SOP |

## 执行流程

严格按以下 **5 个阶段**执行。每个阶段完成后向用户简要汇报进度。

### 前置步骤：依赖安装

首次运行时检查并安装 Python 依赖：

```bash
pip install -r "${CLAUDE_SKILL_DIR}/python/requirements.txt" 2>/dev/null || pip install pydantic jinja2 chardet charset-normalizer python-docx pymupdf openpyxl pyyaml 2>/dev/null
```

若安装失败，告知用户并自动进入**降级模式**（纯 LLM 执行所有阶段）。

### 阶段一：探索（Explore）

**目标**：扫描当前目录，发现并解析所有可用的业务材料文件。

1. 在用户当前工作目录下创建临时目录 `.sop-temp/`
2. 运行 scanner.py：

```bash
python "${CLAUDE_SKILL_DIR}/python/scanner.py" --target . --output .sop-temp/phase1_scan.json
```

3. 读取 `.sop-temp/phase1_scan.json`，了解扫描结果
4. **向用户汇报**：发现 X 个可解析文件，列出文件名和各自的内容摘要（一句话）
5. 若文件超过 10 个，询问用户是否有重点关注的部分

**降级方案**（scanner.py 失败时）：
- 使用 Glob 工具扫描目录：`Glob("**/*.md")`, `Glob("**/*.txt")`, `Glob("**/*.yaml")` 等
- 使用 Read 工具逐个读取文件内容
- 手动构建类似 phase1_scan.json 的信息

### 阶段二：识别（Identify）

**目标**：识别材料的 Skill 类型。

1. 运行 classifier.py：

```bash
python "${CLAUDE_SKILL_DIR}/python/classifier.py" --input .sop-temp/phase1_scan.json --output .sop-temp/phase2_classify.json
```

2. 读取分类结果，查看 `aggregated.top3` 和 `aggregated.suggestion`
3. 结合 Python 预分类结果和材料语义，做出最终类型判断：
   - 若 top-1 置信度 > 0.6 且你同意 → 直接采用
   - 若置信度接近或你有不同判断 → 你裁决并说明理由
4. **向用户汇报**：识别为 [类型]，Python 置信度 X%，你的判断依据简述
5. 将你的类型判断追加到 phase2_classify.json 的 `llm_decision` 字段

**降级方案**（classifier.py 失败时）：
- 你直接阅读所有材料全文
- 基于你的语义理解判断最合适的类型
- 从上述类型列表中选择最匹配的

### 阶段三：规划（Plan）

**目标**：确定该类型 Skill 需要的完整要素清单，并规划信息来源。

1. 根据确定的类型，运行 schema.py 获取要素蓝图：

```bash
python "${CLAUDE_SKILL_DIR}/python/schema.py" --type <确定的类型> --output .sop-temp/phase3_blueprint.json
```

2. 读取蓝图，了解公共要素和类型特有要素
3. 通读所有材料全文，为每个要素标注信息来源（文件路径 + 相关段落位置）
4. 将来源规划写入 phase3_blueprint.json 的 `source_mapping` 字段
5. **向用户汇报**：列出核心要素清单和信息来源规划

**降级方案**（schema.py 失败时）：
- 你根据类型自行确定需要哪些要素
- 公共要素始终包括：metadata、inputs、constraints、quality_gates、sources

### 阶段四：收集（Collect）

**目标**：按要素清单从材料中提取结构化信息。

**你的核心工作**：

1. 按要素清单逐项从文件中提取信息
2. 对于 `overview`（概述）字段，你需要撰写一段简洁的 Skill 概述
3. 将所有提取结果组织为 JSON，格式如下：

```json
{
  "meta": {
    "skill_type": "<类型>",
    "extract_round": 1
  },
  "data": {
    "metadata": {
      "name": "<小写字母+数字+连字符>",
      "description": "<一句话描述>",
      "allowed_tools": "<允许的工具列表，可选>"
    },
    "overview": "<概述文本>",
    "inputs": [{"param_name": "...", "type": "str", "required": true, "description": "..."}],
    "constraints": [{"constraint": "...", "reason": "..."}],
    "quality_gates": [{"check_item": "...", "method": "...", "pass_criteria": "..."}],
    "sources": [{"element": "...", "source_file": "...", "source_section": "..."}],
    "<类型特有要素>": "..."
  }
}
```

4. 将 JSON 写入 `.sop-temp/phase4_extract.json`

**特殊情况处理**：
- 信息冲突（多份材料说法不同）→ 标注冲突，暂停请用户确认
- 信息缺失（某要素找不到）→ 提供合理默认值或向用户提问
- 信息分散（一要素在多文件中）→ 整合归纳

**校验循环**：

5. 运行 validator.py：

```bash
python "${CLAUDE_SKILL_DIR}/python/validator.py" --input .sop-temp/phase4_extract.json --output .sop-temp/phase4_validate.json
```

6. 读取校验结果：
   - `result == "pass"` → 进入阶段五
   - `result == "fail"` → 根据 `blocking_issues` 修正 JSON，重新写入 phase4_extract.json，再次校验
   - 最多重试 **3 轮**。3 轮后仍有 blocking 问题 → 暂停，向用户报告并请求指示
7. 检查 `warnings` 和 `conflicts`，酌情处理

**降级方案**（validator.py 失败时）：
- 你自行检查 JSON 结构完整性
- 确保所有必填要素存在且非空
- 确保字段类型正确

### 阶段五：整合（Integrate）

**目标**：将校验通过的 JSON 渲染为最终的 SKILL.md 文件。

1. 运行 renderer.py：

```bash
python "${CLAUDE_SKILL_DIR}/python/renderer.py" --input .sop-temp/phase4_extract.json --template <类型> --output .sop-temp/phase5_output.md
```

2. 运行 quality.py 质量门禁：

```bash
python "${CLAUDE_SKILL_DIR}/python/quality.py" --input .sop-temp/phase5_output.md --type <类型> --output .sop-temp/phase5_quality.json
```

3. 读取质量检查结果：
   - `passed == true` → 审阅渲染结果
   - `passed == false` → 根据 `blocking` 问题修正 JSON，重新渲染（最多 2 轮）
4. 你做最终语义审阅：通读渲染结果，确认语义正确、无遗漏
5. 确定输出路径：
   - 用户通过参数指定的路径（如 `$ARGUMENTS`）
   - 或默认路径 `.claude/skills/<metadata.name>/SKILL.md`
6. 将最终结果写入目标路径
7. 清理临时目录：

```bash
python "${CLAUDE_SKILL_DIR}/python/renderer.py" --cleanup
```

8. **向用户汇报**：Skill 已生成到 `<路径>`，列出 Skill 的名称、类型和核心内容概览

**降级方案**（renderer.py 或 quality.py 失败时）：
- 你直接根据模板结构生成 Markdown
- 参考蓝图中的要素，手动组织为标准 SKILL.md 格式
- 你自行执行质量检查（检查 frontmatter、必填章节、占位符）

## 降级模式总览

| 失败模块 | 降级行为 |
| --- | --- |
| scanner.py | 你使用 Glob + Read 手动扫描 |
| classifier.py | 你自行判断类型 |
| schema.py | 你根据类型自行确定要素 |
| validator.py | 你自行检查 JSON 结构 |
| renderer.py | 你直接生成 Markdown |
| quality.py | 你自行执行质量检查 |
| Python 全不可用 | 完全纯 LLM 模式，手动执行所有 5 个阶段 |

任何降级发生时，都必须告知用户。

## 输出语言

选择材料的核心语言作为输出语言。如果材料主要是中文，输出中文 Skill；如果是英文，输出英文 Skill。

## 注意事项

- 生成的 Skill 应独立运行，不依赖原始材料
- 存在无法解析的文件时，告知用户后继续处理其他文件
- 文件夹内容超过 10 个文件时，先询问用户是否有重点关注部分
- 所有 Python 脚本执行失败时，降级为纯 LLM 模式并提示用户
- 始终将 `meta` 中的 `degraded` 设为 `true` 如果任何阶段使用了降级模式
