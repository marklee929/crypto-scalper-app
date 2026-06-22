# Codex Harness Engine

## Purpose

이 문서는 Codex 또는 자동 코딩 에이전트가 `heart_beat_coin_scalper` 안에서 어떻게 작업해야 하는지 정의한다.

목표는 더 오래 코딩하는 것이 아니다. 목표는 실주문 위험을 피하고, 전략 목적을 보존하고, 선언된 경계 안에서만 수정하고, 검증 가능한 변경만 남기는 것이다.

## Mandatory Architecture-First Rule

향후 Codex 작업은 먼저 다음을 읽고 시작한다.

```text
README.md
DOC/architecture/00_PRODUCT_NORTH_STAR.md
DOC/architecture/01_SYSTEM_GROWTH_WORKFLOW.md
DOC/architecture/02_DATA_SOURCE_AND_QUALITY.md
DOC/architecture/03_SYSTEM_ARCHITECTURE.md
DOC/architecture/04_LOCAL_DEVELOPMENT_RUNTIME_GUIDE.md
DOC/architecture/05_CODEX_HARNESS_GUIDE.md
DOC/architecture/06_WORK_AREA_REGISTRY.md
```

그 다음 반드시 선언한다.

```text
PURPOSE FUNCTION
AREA
MODE
```

아키텍처 경계가 잡히기 전에는 소스 코드부터 수정하지 않는다.

## Harness Definition

하네스는 긴 지시문이 아니다.

하네스는 코딩 에이전트의 사고 경로를 제어하는 인지·운영 구조다.

이 프로젝트에서 하네스는 다음을 제공한다.

- 실주문보다 목적 함수 우선
- 작업 AREA 라우팅
- mode별 허용/금지 경계
- trigger card 기반 중단
- execution card 기반 반복 절차
- correction loop before patching
- protected boundary
- verification and reporting

좋은 하네스는 봇이 실계좌를 건드리기 전에 멈추게 만든다.

## Required Input Format

모든 하네스 작업은 가능하면 다음 형식으로 시작한다.

```text
PURPOSE FUNCTION:
AREA:
MODE:
FOCUS:
TIMEBOX:
SUCCESS CRITERIA:
STOP CONDITIONS:
```

선택 항목:

- ALLOWED FILES
- FORBIDDEN FILES
- VERIFICATION PLAN
- REPORT TARGET

`PURPOSE FUNCTION`, `AREA`, `MODE` 중 하나라도 없으면 Codex는 파일을 수정하지 않는다.

허용:

- `README.md`와 `DOC/architecture` 읽기
- `READ_ONLY_AUDIT`
- clarification 질문
- stop/pre-review report 작성

금지:

- 파일 수정
- live 실행
- config/secrets 변경
- 주문 경로 변경
- runtime behavior 추측 수정

## Work Modes

### READ_ONLY_AUDIT

Allowed:

- 문서 읽기
- 코드 읽기
- 테스트 구조 확인
- safe read-only report 작성

Not allowed:

- 코드 수정
- config 수정
- state/log 삭제
- live 실행
- 외부 주문
- API key/secret 출력

### DOC_ONLY

Allowed:

- 문서 생성/수정
- 하네스 재구성
- future CODE_TASK_CANDIDATE 기록

Not allowed:

- runtime code 수정
- config/env/secrets 수정
- live 실행
- state/log 삭제
- 외부 API 호출

### LOW_RISK_FIX

Allowed:

- 주석/문구
- display-only formatting
- 테스트 fixture의 비민감 정리
- 로그 출력 포맷의 비위험 개선
- 문서 링크/경로 보정

Not allowed:

- live order
- API key/secret
- strategy threshold
- order size
- Binance REST behavior
- destructive state/log operation

### GUARDED_FIX

Allowed with pre-review and verification:

- candle validation
- strategy reason logging
- non-live order guard improvement
- parser robustness
- state metadata addition
- PostgreSQL foundation without live order connection
- forward-only migration scaffolding
- DB recorder disabled-mode behavior
- tests
- dry-run/paper 분리 로직

Requires:

- 영향 AREA 명시
- 테스트 실행
- live order 미전송 보고
- 보호영역 미접촉 보고

### PROTECTED_CHANGE

명시적 사용자 승인 전에는 금지.

Protected examples:

- `config.yaml` secret/live order 설정
- `exchanges/binance/rest.py`
- actual market order payload
- order size live 영향
- API key/secret handling
- 기본 실행 모드 변경
- Binance account/order external API behavior
- exchange adapter 추가/변경
- destructive state/log migration
- strategy hard exit 약화
- scheduler/loop가 중복 주문에 영향을 주는 변경

PostgreSQL protected examples:

- PostgreSQL migration
- destructive DB migration
- `DATABASE_URL` handling
- live asset overwrite
- demo fake asset / live asset mixing
- raw secret DB/config snapshot 저장
- SQLite operational default addition

## Quick Pre-Review Gate

파일 수정 전 Codex는 답해야 한다.

- PURPOSE FUNCTION은 무엇인가?
- AREA는 무엇인가?
- MODE는 무엇인가?
- 어떤 문서가 이 작업을 통제하는가?
- 수정 가능한 파일은 무엇인가?
- 금지 파일/섹션은 무엇인가?
- protected areas가 있는가?
- live order risk가 있는가?
- API key/secret 노출 위험이 있는가?
- 어떻게 검증할 것인가?

## Risk Decision

모든 작업은 다음 중 하나로 분류한다.

- `SAFE_TO_PROCEED`
- `PROCEED_WITH_LIMITS`
- `STOP_REQUIRES_USER_REVIEW`

### SAFE_TO_PROCEED

문서나 테스트 등 낮은 위험 영역에서 보호영역 없이 완료 가능하다.

### PROCEED_WITH_LIMITS

명확한 제한 안에서만 가능하다.

예:

- `core/candle_aggregator.py`만 수정
- live order path 금지
- config 수정 금지
- 테스트만 실행

### STOP_REQUIRES_USER_REVIEW

실주문, secret, 기본 실행 모드, 주문 크기, REST order, destructive state/log, 불명확한 전략 손실 영향이 있으면 멈춘다.

## Trigger Card Format

```text
TRIGGER CARD: [Name]
Condition:
Action:
Do not touch:
Verify:
Stop if:
```

기본 trigger examples:

- live order path touched
- API key/secret exposure
- default mode changes
- strategy hard exit weakened
- order size changed
- Binance REST behavior changed
- DB migration touched
- `DATABASE_URL` exposure risk
- live asset overwrite risk
- fake/live asset mixing risk
- PostgreSQL failure hidden as success
- SQLite proposed as operational default
- closed candle boundary broken
- state/log destructive operation
- legacy app boundary unclear
- tests fail outside declared AREA

### TRIGGER CARD: Strategy Archetype Confusion

Condition:

- 작업 설명이 현재 전략을 박스형으로 전제한다
- 지지/저항 사용을 이유로 `market_structure`를 box range engine으로 취급한다
- 박스형 신규 로직을 기존 `MARKET_STRUCTURE_STRATEGY`에 섞으려 한다
- percentage heartbeat, box heartbeat, tracking heartbeat가 문서나 코드에서 혼동된다

Action:

- 현재 기본 구현을 `tracking-first heartbeat scalper with structural box reference`로 분류한다
- 박스형 변경은 별도 `BOX_RANGE_STRATEGY` 후보로 분리한다
- 기존 closed candle, confirmation, hard exit, cooldown 기준선을 보존한다
- 필요한 경우 먼저 `READ_ONLY_AUDIT`로 strategy archetype report를 작성한다

Do not touch:

- live order execution
- API key/secret
- `config.yaml` live settings
- hard exit 약화
- order size
- Binance REST payload

Verify:

- `tests/test_market_structure.py` 기준선 유지
- `strategy_archetype`이 리포트에 명확히 남음
- 박스형 후보가 추적형 현재 구현으로 오해되지 않음

Stop if:

- 박스형/추적형 구분 없이 전략 threshold나 exit를 바꿔야 한다
- 변경이 실주문이나 주문 크기에 영향을 준다

## Execution Card Format

```text
EXECUTION CARD: [Name]
Use when:
Steps:
Allowed files/areas:
Forbidden files/areas:
Verification:
Report:
```

execution card는 길게 설명하기보다 pre-review 중 바로 적용 가능해야 한다.

## Correction Loop Rule

잘못된 결과가 나오면 먼저 실패 계층을 분류한다.

```text
config / mode selection
-> price event ingestion
-> candle aggregation
-> market structure classification
-> strategy decision
-> order guard
-> execution
-> ledger update
-> PostgreSQL append record
-> asset snapshot / reconciliation event
-> state snapshot
-> logging/reporting
-> tests
```

가장 이른 실패 계층을 고친다.

금지:

- 손실이 났다고 entry threshold만 임의 조정
- 주문 실패를 ledger success로 처리
- live 위험을 로그 문구로만 숨김
- WebSocket 중복을 strategy 문제로 오해
- test 실패를 삭제로 해결

- DB insert 실패를 성공처럼 숨김
- demo fake asset을 live asset snapshot에 기록
- SQLite를 운영 기본 DB로 우회 도입

## Multi-Responsibility File Boundary Rule

같은 파일이 같은 책임을 의미하지 않는다.

예:

- `run.py`에는 config, mode, stream, strategy, order guard, ledger, state, log가 같이 있을 수 있다.
- `config.yaml`에는 일반 전략 파라미터와 secret/live order 설정이 같이 있을 수 있다.
- `core/heartbeat.py`에는 상태 머신과 판단 기록이 같이 있을 수 있다.

Codex는 선언된 AREA의 책임 섹션만 건드린다.

경계가 불명확하면 멈춘다.

## Multi-Responsibility File Section Map Execution Card

Use when:

- 대상 파일에 여러 책임이 섞여 있다
- protected section이 근처에 있다
- 같은 수정이 live behavior에 영향을 줄 수 있다

Steps:

```text
identify file responsibilities
-> mark protected sections
-> mark allowed section
-> mark forbidden adjacent sections
-> define verification only for selected section
-> stop if section boundary is unclear
```

Do not:

- 파일 접근 권한을 전체 수정 권한으로 착각
- nearby protected code를 같이 정리
- 하나의 테스트 통과를 전체 안정성으로 과장

## Session Cycle

긴 작업은 고정 사이클을 따른다.

```text
00:00-00:10  Quick pre-review
00:10-00:40  Limited execution
00:40-00:50  Verification
00:50-01:00  Final check, report
```

마지막에 큰 새 작업을 시작하지 않는다.

## Command Lexicon

추천 명령:

- `!scalper-next`: 다음 하네스 큐 작업 실행
- `!scalper-audit`: 읽기 전용 점검
- `!scalper-fix`: 승인된 범위의 수정
- `!scalper-close`: 보고서 저장/마커 정리
- `!scalper-report`: 누락 보고서 저장/복구

WorkConnect 전용 명령은 이 프로젝트에서 사용하지 않는다.

## Individual Request Default Rule

사용자가 “이거 맞아?”, “왜 이럼?”, “확인해줘”, “위험해 보여?”처럼 말하고 구현을 명시하지 않으면 기본은 `READ_ONLY_AUDIT`다.

구현 트리거:

- `!scalper-fix`
- "implement"
- "patch"
- "fix it"
- "apply the fix"
- "수정해"
- "적용해"
- bounded prompt with `AREA`, `MODE`, `FOCUS`

애매하면 수정하지 않는다.

## Walkthrough Execution Rule

큐 기반 실행을 사용할 경우 다음을 따른다.

- root bootstrap 문서가 있으면 먼저 읽는다
- 오늘 KST 기준 execute prompt를 읽는다
- completion marker는 `[SCALPER_EXECUTION_COMPLETE]`를 사용한다
- marker는 정확히 1개만 존재해야 한다
- marker는 execute prompt 문서의 맨 마지막 줄에 둔다
- 완료 보고서, audit 결과, pending queue가 있으면 모두 marker 위에 둔다
- 보호영역은 명시적 승인 없이 실행하지 않는다
- 실행 결과는 `DOC/walkthrough/execution-history/YYYY-MM-DD/`에 저장한다

## Completion Marker Rule

Scalper completion marker:

```text
[SCALPER_EXECUTION_COMPLETE]
```

Rules:

- 정확히 한 줄에 단독으로 존재
- 정확히 1개만 존재
- 예시에는 `[COMPLETION_MARKER_EXAMPLE_DO_NOT_COPY]` 사용
- execute prompt 문서 맨 마지막에 위치
- 완료한 phase 보고서뿐 아니라 확인한 audit/pending section 아래에 위치
- marker 상태가 애매하면 stop report

## Stop Report Format

```text
# Stop Report: [AREA]

## Requested Task
## Pre-Review Result
Status: STOP_REQUIRES_USER_REVIEW
## Why Codex Stopped
## Files Inspected
## Files That Would Need Changes
## Protected Areas Involved
## Live Order Risk
## Secret Exposure Risk
## Recommended Next Step
## User Decision Needed
```

## Reporting Policy

보고서는 한국어로 작성한다.

기술 식별자는 번역하지 않는다.

번역하지 않을 것:

- file path
- class/function name
- enum/status
- AREA
- MODE
- PURPOSE FUNCTION
- exchange name
- API endpoint
- raw error message
- test name

## Pre-Review Report

수정 전 보고:

```text
AREA:
MODE:
PURPOSE FUNCTION:
Risk:
Decision:
Files inspected:
Files planned to touch:
Forbidden areas:
Protected areas involved:
Live order risk:
Secret exposure risk:
Verification plan:
```

## Completion Report

최종 보고는 다음을 포함한다.

- AREA
- MODE
- PURPOSE FUNCTION
- pre-review result
- files inspected
- files modified
- tests/checks run
- command run
- DB touched 여부
- migration touched 여부
- external API touched 여부
- actual order sent 여부
- protected areas touched 여부
- state/log impact
- stop conditions encountered
- remaining risks
- next CODE_TASK_CANDIDATE

## Conditional Commit/Push Rule

commit/push는 명시적으로 요청받았을 때만 한다.

조건:

- 선언 AREA 안에 머물렀다
- 보호영역을 승인 없이 건드리지 않았다
- 테스트 또는 skip reason이 명확하다
- secret이 없다
- live order가 전송되지 않았다
- diff가 검토되었다

## Completion Principle

완료보다 생존이 먼저다.

실계좌 주문 위험, secret 노출, 손절 약화, 모드 혼선이 보이면 멈추는 것이 성공이다.
