# Work Area Registry and Module Harness Map

## Purpose

이 문서는 `heart_beat_coin_scalper`의 Codex 하네스 작업 영역을 정의한다.

각 work area는 모듈 하네스다. 모든 work area는 다음 문서를 상속한다.

- `00_PRODUCT_NORTH_STAR.md`
- `01_SYSTEM_GROWTH_WORKFLOW.md`
- `02_DATA_SOURCE_AND_QUALITY.md`
- `03_SYSTEM_ARCHITECTURE.md`
- `04_LOCAL_DEVELOPMENT_RUNTIME_GUIDE.md`
- `05_CODEX_HARNESS_GUIDE.md`

## Risk Levels

### LOW

문서, 읽기 전용 점검, 테스트 설명, 비런타임 정리.

### LOW-MEDIUM

표시/로그 포맷, 테스트 보강, 비실주문 parser 개선.

### MEDIUM

캔들 집계, 시장 구조 분류, state metadata, order guard의 비실주문 개선.

### MEDIUM-HIGH

전략 진입/청산 조건, hard exit, order sizing, stream reconnect 정책.

### HIGH

실주문, Binance REST, API key/secret, config live 설정, 기본 실행 모드, destructive state/log, 거래소 확장 주문 경로.

## Governance Inheritance Rule

어떤 work area도 거래 헌법을 무시할 수 없다.

수익 가능성이 있어 보여도 다음을 약화하면 중단한다.

- 손실 제한
- 실주문 경계
- secret 보호
- 닫힌 캔들 판단
- 장부/로그 정합성
- demo/paper/live 분리
- 테스트 기준선

## Module Harness Rule

작업 전 선택:

```text
PURPOSE FUNCTION
AREA
MODE
FOCUS
TIMEBOX
```

그 다음 확인:

- allowed files
- forbidden files
- protected areas
- live order risk
- secret exposure risk
- verification plan
- stop conditions

## Individual Request Default Rule

개별 이슈 확인 요청은 기본 `READ_ONLY_AUDIT`다.

구현은 명시적 트리거가 있을 때만 한다.

예:

- `!scalper-fix`
- "수정해"
- "적용해"
- "patch"
- "fix it"
- `AREA`, `MODE`, `FOCUS`가 포함된 bounded prompt

## Protected Areas

명시적 승인 없이는 변경 금지:

- `config.yaml`의 API key/secret/live order 설정
- Binance REST 주문 실행
- market order payload
- live order enablement
- order size live 영향
- 기본 실행 모드 위험 변경
- API key/secret handling
- exchange account/order external API behavior
- destructive state/log operation
- strategy hard exit 약화
- scheduler/loop 중복 주문 영향
- 신규 거래소 live order adapter

## Work Areas

### AREA: PRODUCT_DOCS

Purpose: 프로젝트 목적, 거래 헌법, 전략 정체성.

Allowed files:

```text
DOC/architecture/00_PRODUCT_NORTH_STAR.md
DOC/architecture/01_SYSTEM_GROWTH_WORKFLOW.md
DOC/architecture/02_DATA_SOURCE_AND_QUALITY.md
README.md when explicitly allowed
```

Allowed: documentation-only clarification.

Forbidden: runtime code, config secrets, live order, state/log deletion.

Risk: LOW.

### AREA: SYSTEM_ARCHITECTURE_DOCS

Purpose: 시스템 경계, 모듈 책임, 데이터 흐름, runtime boundary.

Allowed files:

```text
DOC/architecture/03_SYSTEM_ARCHITECTURE.md
DOC/architecture/04_LOCAL_DEVELOPMENT_RUNTIME_GUIDE.md
DOC/architecture/01_SYSTEM_GROWTH_WORKFLOW.md
```

Forbidden: runtime code, config, live order, external API.

Risk: LOW.

### AREA: CODEX_HARNESS_DOCS

Purpose: Codex 작업 규칙, trigger cards, report format, work area registry.

Allowed files:

```text
CODEX_BOOTSTRAP.md
DOC/architecture/05_CODEX_HARNESS_GUIDE.md
DOC/architecture/06_WORK_AREA_REGISTRY.md
DOC/walkthrough/
DOC/walkthrough/execution-history/
DOC/correction-loop/
```

Forbidden: runtime code, config/env/secrets, external API call, live order.

Risk: LOW.

### AREA: RUNTIME_ENTRYPOINT

Purpose: `run.py`, `run.bat` 실행 흐름, mode selection, tick processing 연결.

Allowed:

- safe mode 명시
- dry-run/paper 분리 후보
- argument parsing 개선
- non-live smoke path 개선
- structured runtime context 추가

Forbidden without explicit approval:

- 기본 live order 위험 증가
- 실제 주문 호출 위치 변경
- API key/secret handling
- order size 증가
- state/log destructive rewrite

Required checks:

- selected mode 확인
- live order 미전송 확인
- `tests/test_run_guards.py`
- demo smoke if safe

Risk: MEDIUM-HIGH.

Stop: 기본 실행 모드 변경이 live behavior에 영향을 주면 사용자 승인 필요.

### AREA: CONFIG_AND_SECRETS

Purpose: 설정 구조, secret 분리, live order flags.

Allowed:

- read-only audit
- secret redaction 문서화
- env 분리 설계 문서
- sample config with fake placeholders

Forbidden without explicit approval:

- 실제 `config.yaml` secret 수정
- 실제 key 출력
- live_order_enabled 변경
- 주문 크기 live 영향 변경

Required checks:

- no raw secret in output
- sample만 사용
- real config diff 여부 보고

Risk: HIGH.

### AREA: DATA_STREAM_BINANCE_WS

Purpose: Binance WebSocket 수신, reconnect, message parsing.

Allowed:

- trade/ticker/kline parsing robustness
- stale data detection
- stream type tagging
- duplicate event audit
- tests for parsing

Forbidden:

- REST order
- API key/secret
- live order enablement
- strategy threshold 변경

Required checks:

- `tests/test_binance_exchange.py`
- no external order
- sample payload tests

Risk: MEDIUM.

### AREA: CANDLE_AGGREGATOR

Purpose: price event를 OHLCV candle로 집계.

Allowed:

- invalid price guard
- bucket boundary fix
- closed candle behavior
- volume handling
- tests

Forbidden:

- strategy threshold
- order execution
- live config
- ledger mutation outside caller

Required checks:

- `tests/test_candle_aggregator.py`
- closed candle only strategy path 확인

Risk: MEDIUM.

### AREA: MARKET_STRUCTURE_STRATEGY

Purpose: `core.market_structure`, `core.heartbeat` 전략 판단.

Allowed:

- reason logging
- classification clarity
- entry block reason 보강
- cooldown/state snapshot clarity
- tests

Forbidden without approval:

- hard exit 약화
- confirmation count 무단 완화
- 과열 차단 제거
- live order 연결
- order size 변경

Required checks:

- `tests/test_market_structure.py`
- existing behavior diff report
- 손실 제한 영향 보고

Risk: MEDIUM-HIGH.

### AREA: STRATEGY_ARCHETYPE

Purpose: 박스형(box-first), 추적형(tracking-first), hybrid/reference 전략 분류를 관리한다.

Current classification:

```text
current_strategy_archetype = tracking-first
box_reference = structural_support_resistance
```

Allowed:

- strategy archetype documentation
- READ_ONLY_AUDIT on current strategy identity
- report field naming
- test naming clarity
- separation proposal for future box strategy

Forbidden without approval:

- 기존 `MARKET_STRUCTURE_STRATEGY`를 박스형으로 재해석
- box lower/upper band logic을 기존 진입 로직에 직접 삽입
- hard exit 약화
- confirmation count 완화
- live order 연결
- order size 변경

Required checks:

- `README.md` 기준 current code summary와 일치
- `tests/test_market_structure.py` 기준선 유지
- box-first 후보와 tracking-first 현재 구현이 분리되어 보고됨

Risk: MEDIUM.

### AREA: ORDER_GUARD

Purpose: 주문 의도와 실행 사이의 방어선.

Allowed:

- min trade cash validation
- no-client guard
- paper/live separation
- BUY_SKIPPED reason clarity
- order intent logging
- tests

Forbidden without approval:

- 실제 REST 주문 전송
- live_order_enabled 변경
- API key/secret
- order size live 영향
- Binance REST payload 변경

Required checks:

- `tests/test_run_guards.py`
- live order 미전송 보고

Risk: MEDIUM-HIGH.

### AREA: BINANCE_REST_EXECUTION

Purpose: Binance REST 인증, market order 전송, 주문 수량 포맷.

Allowed: 명시적 승인 후에만.

Forbidden in unattended harness:

- market order payload 변경
- API key/secret handling 변경
- account/order endpoint 호출
- live 주문 테스트
- 주문 성공/실패 장부 순서 변경

Required checks:

- mock tests
- no real order unless explicitly approved
- error detail preservation

Risk: HIGH.

### AREA: PAPER_LEDGER

Purpose: 현금, 포지션, 평균단가, 실현손익, 수수료/슬리피지 장부.

Allowed:

- paper ledger calculation fix
- event logging
- fee/slippage calculation tests
- snapshot formatting

Forbidden:

- live REST order
- actual account balance assumption
- state destructive rewrite without backup

Required checks:

- ledger unit tests if available
- trade event consistency

Risk: MEDIUM.

### AREA: STATE_RECOVERY

Purpose: `state.json` 저장/복구, snapshot versioning, mode tagging.

Allowed:

- atomic save fix
- metadata addition
- read-only migration report
- backup-first safe change

Forbidden without approval:

- existing state deletion
- destructive rewrite
- live state overwrite
- mode-mismatched restore

Required checks:

- restore test or smoke
- backup strategy report

Risk: MEDIUM-HIGH.

### AREA: LOGGING_REPORTING

Purpose: `strategy.log`, `trades.log`, `hourly_report.log`, logger/notifier.

Allowed:

- reason visibility
- structured log field addition
- no-secret redaction
- report formatting
- rotating logger safety

Forbidden:

- raw API key logging
- full stack trace with secrets
- live order behavior
- hiding failures as success

Required checks:

- no raw secret in logs
- skip/block/fail events visible

Risk: LOW-MEDIUM.

### AREA: TESTS

Purpose: 현재 동작 기준선과 하네스 회귀 방지.

Allowed:

- unit tests
- parser tests
- strategy behavior tests
- order guard tests
- fixture with fake data only
- no-network tests

Forbidden:

- real API key fixture
- actual Binance order call
- live external dependency test by default
- deleting tests to pass

Required checks:

- relevant pytest subset
- no secrets
- no external order

Risk: LOW-MEDIUM.

### AREA: LEGACY_APP

Purpose: `crypto_scalper_app_legacy` 참고 또는 별도 앱 작업.

Allowed:

- read-only audit
- documentation of boundary
- migration candidate report

Forbidden:

- 현행 Python runtime과 무단 병합
- live order logic 복사
- secrets transfer
- runtime 기준선으로 삼기

Risk: MEDIUM.

### AREA: EXCHANGE_ADAPTER_COINONE

Purpose: 향후 Coinone/KRW 거래소 확장.

Current rule:

- Coinone 최신 API 기준은 `2.1`
- Binance adapter와 분리
- 인증/주문/수량/최소주문/응답 형식 별도 검증

Allowed:

- DOC_ONLY 설계
- READ_ONLY_AUDIT
- sample interface with no secrets
- mock tests

Forbidden without explicit approval:

- 실제 Coinone 주문
- 실제 API key/secret
- live adapter 연결
- Binance path와 섞기

Risk: HIGH if live, MEDIUM if doc/mock only.

## High-Frequency Execution Cards

### EXECUTION CARD: Strategy Archetype Review

Use when:

- 현재 전략이 박스형인지 추적형인지 판단해야 한다
- 새 전략 문서가 current code와 맞는지 점검해야 한다
- box/range 개념을 추가하려는 작업이 있다

Steps:

```text
read README current-code summary
-> inspect closed candle / market_structure / heartbeat state path
-> classify as tracking-first, box-first, or separated future candidate
-> preserve current tests as baseline
-> report whether code change is needed or docs-only correction is enough
```

Allowed files/areas:

- `DOC/architecture/00_PRODUCT_NORTH_STAR.md`
- `DOC/architecture/01_SYSTEM_GROWTH_WORKFLOW.md`
- `DOC/architecture/02_DATA_SOURCE_AND_QUALITY.md`
- `DOC/architecture/03_SYSTEM_ARCHITECTURE.md`
- `DOC/architecture/05_CODEX_HARNESS_GUIDE.md`
- `DOC/architecture/06_WORK_AREA_REGISTRY.md`
- `DOC/architecture/07_HARNESS_RESTRUCTURE_REVIEW.md`
- `STRATEGY_ARCHETYPE`
- `MARKET_STRUCTURE_STRATEGY` read-only unless implementation is approved

Forbidden files/areas:

- `BINANCE_REST_EXECUTION`
- `ORDER_GUARD` behavior changes
- `CONFIG_AND_SECRETS`
- live order config
- order size

Verification:

- current strategy remains `tracking-first heartbeat scalper with structural box reference`
- future box strategy is not described as already implemented
- no runtime behavior changes unless explicitly approved

Report:

- strategy archetype
- evidence from README/code/tests
- docs changed or code task candidate
- protected areas untouched

### EXECUTION CARD: Safe Demo Verification

Use when: runtime 변경 후 안전 smoke가 필요하다.

Steps:

```text
confirm mode=demo
-> confirm live_order_enabled irrelevant or false
-> run bounded demo
-> inspect logs/state output
-> report no real order
```

Forbidden:

- Binance REST order
- real API key use

Verification:

- command
- generated files
- actual order sent: NO

### EXECUTION CARD: Strategy Change Review

Use when: entry/exit classification changes.

Steps:

```text
identify changed condition
-> classify entry vs exit vs block reason
-> check hard exit impact
-> run market_structure tests
-> report behavioral diff
```

Forbidden:

- live order path
- order size
- API key/secret

Verification:

- `tests/test_market_structure.py`
- reason log sample

### EXECUTION CARD: Order Guard Review

Use when: BUY/SELL execution path changes.

Steps:

```text
separate OrderIntent from Execution
-> check min_trade_cash
-> check live_order_enabled
-> check client existence
-> run run_guards tests
-> report live order risk
```

Forbidden:

- real market order
- secret handling change

Verification:

- `tests/test_run_guards.py`
- actual order sent: NO

### EXECUTION CARD: Secret Safety Review

Use when: config, logs, tests, docs mention key/secret.

Steps:

```text
scan output for key/secret patterns
-> replace with placeholders in docs/tests
-> do not print actual values
-> report redaction
```

Forbidden:

- reading secrets aloud
- copying real config into artifacts

Verification:

- no raw secret in modified files

## Future Audit Targets

### CODE_TASK_CANDIDATE

```text
AREA: RUNTIME_ENTRYPOINT + ORDER_GUARD
MODE: READ_ONLY_AUDIT
PURPOSE FUNCTION:
현재 기본 실행 모드가 live로 향하는 위험을 분석하고, safe default/paper mode 분리 설계를 제안한다.
TIMEBOX: 60m
```

Risk: MEDIUM-HIGH.

### CODE_TASK_CANDIDATE

```text
AREA: CONFIG_AND_SECRETS
MODE: READ_ONLY_AUDIT
PURPOSE FUNCTION:
config.yaml에서 민감정보와 일반 전략 설정을 분리하는 설계를 제안한다.
TIMEBOX: 45m
```

Risk: HIGH if implementation.

### CODE_TASK_CANDIDATE

```text
AREA: DATA_STREAM_BINANCE_WS + CANDLE_AGGREGATOR
MODE: READ_ONLY_AUDIT
PURPOSE FUNCTION:
trade/ticker/kline 혼합 이벤트가 캔들 집계에 중복 영향을 주는지 확인한다.
TIMEBOX: 60m
```

Risk: MEDIUM.

### CODE_TASK_CANDIDATE

```text
AREA: STATE_RECOVERY
MODE: READ_ONLY_AUDIT
PURPOSE FUNCTION:
state.json에 mode/symbol/exchange metadata가 없어 demo/live 복구가 섞일 위험이 있는지 확인한다.
TIMEBOX: 45m
```

Risk: MEDIUM-HIGH.

## Required Checks

AREA와 MODE에 맞춰 선택한다.

- architecture/doc consistency
- no forbidden files touched
- no raw secret
- no real order sent
- relevant pytest subset
- safe demo smoke
- order guard behavior
- closed candle boundary
- state/log path impact
- live order risk report
- protected area untouched

## Stop Conditions

다음이면 멈춘다.

- 실주문 가능성이 승인 없이 보인다
- API key/secret 노출 위험이 있다
- `config.yaml` 실제 secret 변경이 필요하다
- Binance REST order path를 건드려야 한다
- order size/live_order_enabled 변경이 필요하다
- hard exit 약화가 필요하다
- state/log destructive operation이 필요하다
- 테스트 실패 원인이 현재 AREA 밖이다
- 레거시 앱 경계가 불명확하다
- fix가 추측에 의존한다

위험한 완료보다 명확한 stop report가 낫다.
