# SOP スキル工房

[中文](README.md) · [한국어](README_KO.md) · [Español](README_ES.md) · [English](README_EN.md)

> 散らばった業務ドキュメントを、再利用可能な Claude Code Skill に精製。

![仕組み](sop-skill-factory.png)

**SOP スキル工房**は [Claude Code](https://docs.anthropic.com/en/docs/claude-code) のメタスキルです。業務素材が含まれるフォルダで呼び出すと、Python プログラム層と LLM セマンティック層が協働して、ドキュメントを構造化されたすぐに使える `SKILL.md` に蒸留します。

## どんな問題を解決するか

SOP ドキュメント、操作マニュアル、承認フロー表が山積みになっていても、Claude Code から直接利用できません。スキル工房はこれらの素材を読み込み、業務タイプを自動識別、主要要素を抽出、完全性を検証し、標準的な Skill ファイルを出力します。

## 仕組み

![仕組み](Working-principle.png)

**役割分担**：Python は確定的な操作（ファイル解析、フォーマット描画、構造検証）を担当し、LLM はセマンティックな操作（内容理解、情報抽出、タイプ分類）を担当します。Python モジュールが失敗した場合は、自動的に純粋な LLM モードにフォールバックします。

## 対応する 9 種類の Skill タイプ

| タイプ      | 説明             | 典型的なシナリオ                                           |
| ----------- | ---------------- | ---------------------------------------------------------- |
| sequential  | 線形ワークフロー | オンボーディング、経費精算、調達プロセス                   |
| conditional | 条件分岐型       | IT 設定、顧客階層処理                                      |
| checklist   | チェックリスト   | コードレビュー、リリース前チェック、セキュリティ監査       |
| template    | テンプレート生成 | メール作成、ドキュメント生成、レポート出力                 |
| knowledge   | ナレッジ Q&A     | FAQ、製品マニュアル、ポリシー解釈                          |
| decision    | 意思決定支援     | 技術選定、提案レビュー、リスク評価                         |
| monitoring  | 運用監視型       | システム点検、トラブルシューティング、パフォーマンス最適化 |
| approval    | 承認ワークフロー | 休暇申請、調達承認、契約署名                               |
| hybrid      | 複合型           | 複数サブプロセスを含む複雑な SOP                           |

## クイックスタート

### 前提条件

- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) がインストール済みでログイン済み
- Python 3.9+（プログラム層用。利用不可の場合は自動フォールバック）

### インストール

```bash
git clone https://github.com/suzibinjelly/sop-skill-factory.git
cd sop-skill-factory
```

`sop-skill/` ディレクトリを `.claude/skills/` にコピーまたはリンク：

```bash
# 方法1：直接コピー
cp -r sop-skill ~/.claude/skills/sop-skill

# 方法2：シンボリックリンク（更新が容易）
ln -s "$(pwd)/sop-skill" ~/.claude/skills/sop-skill
```

### 使い方

業務素材が含まれるディレクトリで Claude Code を開き、入力：

```
/sop-skill
```

または自然言語で：

```
このフォルダの内容を Skill にして
```

スキル工房が蒸留プロセス全体をガイドします。

## プロジェクト構成

```
sop-skill/
├── SKILL.md                   # メタスキル指示ファイル
├── python/
│   ├── scanner.py             # ファイルスキャン + 多フォーマット解析
│   ├── classifier.py          # キーワード信号 + タイプ事前分類
│   ├── schema.py              # 要素レジストリ + Pydantic データモデル
│   ├── validator.py           # JSON 構造検証 + 競合検出
│   ├── renderer.py            # Jinja2 テンプレート描画
│   ├── quality.py             # 品質ゲートチェック
│   └── requirements.txt       # Python 依存パッケージ
└── templates/                 # 9 種類の Jinja2 出力テンプレート
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

## 対応ファイル形式

`.md` `.txt` `.yaml` `.yml` `.json` `.csv` `.docx` `.pdf` `.xlsx` `.pptx` `.html` `.htm`

## お問い合わせ

<img src="contact.jpg" width="20%" alt="お問い合わせ" />

## ライセンス

[MIT](LICENSE)
