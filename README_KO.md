# SOP 스킬 공방

[中文](README.md) · [日本語](README_JA.md) · [Español](README_ES.md) · [English](README_EN.md)

> 흩어진 비즈니스 문서를 재사용 가능한 Claude Code Skill로 정제하세요.

![작동 원리](sop-skill-factory.png)

**SOP 스킬 공방**은 [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 메타 스킬입니다. 비즈니스 자료가 포함된 폴더에서 호출하면 Python 프로그래밍 레이어와 LLM 시맨틱 레이어가 협력하여 문서를 구조화되고 바로 사용할 수 있는 `SKILL.md`로 증류합니다.

## 어떤 문제를 해결하나요

SOP 문서, 운영 매뉴얼, 승인 프로세스 표가 산더미처럼 쌓여 있어도 Claude Code에서 직접 사용할 수 없습니다. 스킬 공방은 이러한 자료를 읽고 비즈니스 유형을 자동 식별, 핵심 요소를 추출, 완전성을 검증하여 표준 Skill 파일을 출력합니다.

## 작동 원리

![작동 원리](Working-principle.png)

**역할 분담**: Python은 결정론적 작업(파일 파싱, 포맷 렌더링, 구조 검증)을 담당하고, LLM은 시맨틱 작업(내용 이해, 정보 추출, 유형 분류)을 담당합니다. Python 모듈 실패 시 자동으로 순수 LLM 모드로 폴백됩니다.

## 지원하는 9가지 Skill 유형

| 유형        | 설명            | 대표 시나리오                         |
| ----------- | --------------- | ------------------------------------- |
| sequential  | 선형 워크플로우 | 온보딩, 경비 정산, 구매 프로세스      |
| conditional | 조건 분기형     | IT 설정, 고객 등급 처리               |
| checklist   | 체크리스트      | 코드 리뷰, 릴리스 전 체크, 보안 감사  |
| template    | 템플릿 생성     | 이메일 작성, 문서 생성, 보고서 출력   |
| knowledge   | 지식 Q&A        | FAQ, 제품 매뉴얼, 정책 해석           |
| decision    | 의사결정 지원   | 기술 선택, 제안 리뷰, 리스크 평가     |
| monitoring  | 운영 모니터링   | 시스템 점검, 장애 해결, 성능 최적화   |
| approval    | 승인 워크플로우 | 휴가 신청, 구매 승인, 계약 서명       |
| hybrid      | 복합형          | 여러 서브프로세스가 포함된 복잡한 SOP |

## 빠른 시작

### 필수 조건

- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) 설치 및 로그인 완료
- Python 3.9+ (프로그래밍 레이어용, 사용 불가 시 자동 폴백)

### 설치

```bash
git clone https://github.com/suzibinjelly/sop-skill-factory.git
cd sop-skill-factory
```

`sop-skill/` 디렉토리를 `.claude/skills/`에 복사 또는 링크:

```bash
# 방법 1: 직접 복사
cp -r sop-skill ~/.claude/skills/sop-skill

# 방법 2: 심볼릭 링크 (업데이트 용이)
ln -s "$(pwd)/sop-skill" ~/.claude/skills/sop-skill
```

### 사용법

비즈니스 자료가 포함된 디렉토리에서 Claude Code를 열고 입력:

```
/sop-skill
```

또는 자연어로:

```
이 폴더의 내용을 Skill로 만들어줘
```

스킬 공방이 전체 증류 프로세스를 안내합니다.

## 프로젝트 구조

```
sop-skill/
├── SKILL.md                   # 메타 스킬 지시 파일
├── python/
│   ├── scanner.py             # 파일 스캔 + 다중 포맷 파싱
│   ├── classifier.py          # 키워드 신호 + 유형 사전 분류
│   ├── schema.py              # 요소 레지스트리 + Pydantic 데이터 모델
│   ├── validator.py           # JSON 구조 검증 + 충돌 감지
│   ├── renderer.py            # Jinja2 템플릿 렌더링
│   ├── quality.py             # 품질 게이트 검사
│   └── requirements.txt       # Python 종속성
└── templates/                 # 9가지 유형의 Jinja2 출력 템플릿
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

## 지원 파일 형식

`.md` `.txt` `.yaml` `.yml` `.json` `.csv` `.docx` `.pdf` `.xlsx` `.pptx` `.html` `.htm`

## 연락처

<img src="contact.jpg" width="20%" alt="연락처" />

## 라이선스

[MIT](LICENSE)
