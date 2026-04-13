# SOP Skill Forge

[中文](README.md) · [日本語](README_JA.md) · [한국어](README_KO.md) · [Español](README_ES.md)

> Turn scattered business documents into a reusable Claude Code Skill.

![How it works](sop-skill-factory.png)

**SOP Skill Forge** is a [Claude Code](https://docs.anthropic.com/en/docs/claude-code) meta-skill. Invoke it in any folder containing business materials, and the Python programmatic layer works alongside the LLM semantic layer to distill your documents into a structured, ready-to-use `SKILL.md`.

## What Problem Does It Solve

You have piles of SOP documents, operation manuals, and approval process sheets — but they just sit in folders, unusable by Claude Code. Skill Forge reads these materials, automatically identifies the business type, extracts key elements, validates completeness, and outputs a standard Skill file.

## How It Works

![How it works](Working-principle.png)

**Division of responsibility**: Python handles deterministic operations (file parsing, format rendering, structural validation), while the LLM handles semantic operations (content understanding, information extraction, type classification). Any Python module failure triggers automatic fallback to pure LLM mode.

## 9 Supported Skill Types

| Type        | Description         | Typical Scenarios                                       |
| ----------- | ------------------- | ------------------------------------------------------- |
| sequential  | Linear workflow     | Onboarding, expense reimbursement, procurement          |
| conditional | Branching logic     | IT configuration, customer tier handling                |
| checklist   | Checklist           | Code review, pre-release checks, security audits        |
| template    | Template generation | Emails, document generation, reports                    |
| knowledge   | Q&A / FAQ           | Product manuals, policy interpretation                  |
| decision    | Decision support    | Technology selection, proposal review, risk assessment  |
| monitoring  | Ops & monitoring    | System inspection, troubleshooting, performance tuning  |
| approval    | Approval workflow   | Leave requests, procurement approvals, contract signing |
| hybrid      | Mixed / composite   | Complex SOPs with multiple sub-processes                |

## Quick Start

### Prerequisites

- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) installed and logged in
- Python 3.9+ (for the programmatic layer; auto-degrades if unavailable)

### Installation

Clone this repository:

```bash
git clone https://github.com/suzibinjelly/sop-skill-factory.git
cd sop-skill-factory
```

Copy or link the `sop-skill/` directory to `.claude/skills/`:

```bash
# Option 1: Direct copy
cp -r sop-skill ~/.claude/skills/sop-skill

# Option 2: Symlink (easier to update later)
ln -s "$(pwd)/sop-skill" ~/.claude/skills/sop-skill
```

### Usage

Open Claude Code in a directory containing your business materials and type:

```
/sop-skill
```

Or in natural language:

```
Turn this folder's contents into a Skill
```

Skill Forge will guide you through the entire distillation process.

## Project Structure

```
sop-skill/
├── SKILL.md                   # Meta-skill instruction file
├── python/
│   ├── scanner.py             # File scanning + multi-format parsing
│   ├── classifier.py          # Keyword signals + type pre-classification
│   ├── schema.py              # Element registry + Pydantic data models
│   ├── validator.py           # JSON structural validation + conflict detection
│   ├── renderer.py            # Jinja2 template rendering
│   ├── quality.py             # Quality gate checks
│   └── requirements.txt       # Python dependencies
└── templates/                 # Jinja2 output templates for 9 types
    ├── sequential.md.j2
    ├── conditional.md.j2
    ├── checklist.md.j2
    ├── template.md.j2
    ├── knowledge.md.j2
    ├── decision.md.j2
    ├── monitoring.md.j2
    ├── approval.md.j2
    └── hybrid.md.j2
```

## Supported File Formats

`.md` `.txt` `.yaml` `.yml` `.json` `.csv` `.docx` `.pdf` `.xlsx` `.pptx` `.html` `.htm`

## Get in Touch

<img src="contact.jpg" width="20%" alt="Get in Touch" />

## License

[MIT](LICENSE)
