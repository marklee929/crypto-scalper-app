# Harness Restructure Review

Status:

이 문서는 리뷰 참고 문서다. 활성 실행 규칙은 `DOC/architecture/00` through `DOC/architecture/06`에 있다.

PostgreSQL-first DB 기준은 `DOC/architecture/08_DATABASE_ARCHITECTURE.md`에 추가되었으며, 2026-06-22 Phase 1 이후 active harness 문서 세트에 연결된다.

## Purpose

이 리뷰는 기존 WorkConnect용 하네스 문서 세트를 `heart_beat_coin_scalper` 프로젝트에 맞게 바꾼 결과와 남은 보강 지점을 정리한다.

핵심 변환은 다음이다.

```text
source-backed content platform harness
-> live-order-safe trading runtime harness
```

즉, 보호해야 할 최종 외부 영향이 Facebook 게시물이 아니라 Binance REST 실주문으로 바뀌었다.

## 1. Current README-Derived Project Summary

README 기준 현재 프로젝트는 다음 구조다.

- Python 기반 Binance spot 스캘핑 런타임
- `run.py`가 전체 실행 진입점
- `demo`와 `live` 모드 존재
- 기본 실행이 `live`로 향할 수 있음
- `config.yaml`에 live 주문 및 민감정보 필드 존재 가능
- 가격 이벤트를 `CandleAggregator`가 OHLCV candle로 집계
- 닫힌 캔들만 `HeartbeatStrategy.on_candle()`로 전달
- 실제 진입 로직은 percentage rebound가 아니라 `core.market_structure` 중심
- `Ledger`가 paper 장부를 관리
- `BinanceRestClient`가 live 주문 전송 가능
- `state.json`, `strategy.log`, `trades.log`, `hourly_report.log`가 운영 산출물
- `crypto_scalper_app_legacy`는 현재 Python runtime과 별도 경로
- 기존 `DOC/architecture` 일부는 WorkConnect 문맥이라 그대로 쓰면 혼선 발생

## 2. Harness Interpretation for This Project

이 프로젝트에서 하네스는 코딩 에이전트가 다음을 함부로 하지 못하게 하는 제어 구조다.

- 실주문 경로 열기
- API key/secret 노출
- 기본 실행을 위험하게 바꾸기
- 손절 조건 약화
- 진행 중 캔들로 판단하기
- demo/live state 섞기
- 수익률만 보고 전략 파라미터 변경
- 거래소 어댑터 차이를 추정으로 처리

하네스의 목적은 완성보다 생존이다.

## 3. Document Set Control Role

### `00_PRODUCT_NORTH_STAR.md`

역할:

- 거래 헌법
- 프로젝트 정체성
- 수익 최대/손실 최소 목적 함수
- current active scope
- strategy identity
- what not to become
- exchange expansion rule

핵심 변화:

- WorkConnect product mission을 scalper trading mission으로 대체
- public content boundary를 live order boundary로 대체
- global country expansion을 exchange adapter expansion으로 대체

### `01_SYSTEM_GROWTH_WORKFLOW.md`

역할:

- 시장 가설부터 피드백까지의 생명주기
- correction loop before patching
- workflow trigger points
- representative signal rule

핵심 변화:

- source discovery lifecycle을 market hypothesis lifecycle로 대체
- content candidate를 order intent로 대체
- public delivery를 execution or skip으로 대체

### `02_DATA_SOURCE_AND_QUALITY.md`

역할:

- market data validation
- strategy classification worldview
- duplicate/mixed stream policy
- entry block and exit classification
- quality trigger cards

핵심 변화:

- source trust level을 market data trust level로 대체
- URL/body gate를 price/candle/mode gate로 대체
- content contamination을 secret/runtime contamination으로 대체

### `03_SYSTEM_ARCHITECTURE.md`

역할:

- system boundary
- module map
- data/decision/execution separation
- external impact boundary
- exchange boundary

핵심 변화:

- Facebook/Telegram boundary를 demo/paper/live/Binance REST boundary로 대체
- content management를 strategy/order/ledger/state로 대체

### `04_LOCAL_DEVELOPMENT_RUNTIME_GUIDE.md`

역할:

- local runtime safety
- safe execution defaults
- config safety
- runtime trigger cards
- actual order sent 여부 보고

핵심 변화:

- local server/public posting risk를 local Python/live order risk로 대체
- DB safety를 처음에는 state/log safety로 축소했으나, PostgreSQL-first 기준 추가 이후 DB safety를 PostgreSQL migration, `DATABASE_URL`, state/log 역할 분리, reconciliation 안전 규칙으로 다시 확장해야 한다.

### `05_CODEX_HARNESS_GUIDE.md`

역할:

- Codex 작업 규칙
- required input format
- work modes
- risk decision
- trigger/execution card format
- Scalper command lexicon
- stop/report format

핵심 변화:

- WorkConnect commands를 `!scalper-*` 명령으로 대체
- `[WC_EXECUTION_COMPLETE]`를 `[SCALPER_EXECUTION_COMPLETE]`로 대체
- publisher/auth protected examples를 live order/secret/config protected examples로 대체

### `06_WORK_AREA_REGISTRY.md`

역할:

- work area별 허용/금지/검증/위험도
- protected areas
- high-frequency execution cards
- future audit targets

핵심 변화:

- WorkConnect modules를 trading runtime modules로 대체
- `FACEBOOK_PUBLISHER` 고위험을 `BINANCE_REST_EXECUTION` 고위험으로 대체
- `CONTENT_QUEUE`를 `ORDER_GUARD`, `STATE_RECOVERY`, `LOGGING_REPORTING` 등으로 대체

## 4. Main Protected Boundary Shift

이전 WorkConnect 하네스의 핵심 보호영역:

```text
Facebook publisher
Telegram reporting
admin auth
scheduler
DB migration
content publisher
```

현재 Scalper 하네스의 핵심 보호영역:

```text
live order execution
API key/secret
config.yaml live settings
Binance REST behavior
order size
default live mode
strategy hard exit
state/log destructive operation
exchange adapter live path
```

PostgreSQL-first 추가 이후 현재 Scalper 하네스의 DB 보호영역:

```text
PostgreSQL migration
DATABASE_URL raw exposure
live asset overwrite
demo fake asset / live asset mixing
destructive DB migration
SQLite operational default addition
raw secret DB/config snapshot
```

DB migration은 더 이상 WorkConnect 잔재로만 취급하지 않는다. 현재 프로젝트에서는 PostgreSQL-first 기록 계층을 위한 active AREA가 될 수 있지만, destructive migration과 secret 저장 위험 때문에 `DB_MIGRATION` 보호 경계 안에서만 다룬다.

## 5. Remaining Ambiguities to Preserve

### Default Live Mode

README는 현재 `run.py`와 `run.bat`가 인자 없이 live 경로로 들어갈 수 있다고 설명한다.

하네스 관점에서는 안전 기본값을 `demo` 또는 `paper`로 바꾸고 싶지만, 이것은 현재 동작 기준선을 바꾸는 작업이다.

따라서 즉시 구현하지 말고 먼저 audit가 필요하다.

```text
AREA: RUNTIME_ENTRYPOINT + ORDER_GUARD
MODE: READ_ONLY_AUDIT
```

### Paper Mode Absence

README는 현재 모드를 `demo`와 `live` 중심으로 설명한다.

하지만 하네스는 `paper`를 독립 모드로 분리하는 것이 안전하다고 본다.

이것도 설계 후보이지, 현재 코드가 이미 가진 기능으로 단정하면 안 된다.

### Market Structure vs Heartbeat Name

프로젝트명은 `heartbeat`지만 현재 전략은 `market_structure` 중심이다.

문서와 코드 작업은 이 차이를 계속 보존해야 한다.

### Box-First vs Tracking-First Strategy Identity

1차 재작성에서 실주문 보호영역은 잘 잡았지만, 전략의 형태를 박스형과 추적형으로 명확히 구분하는 설명이 부족했다.

현재 README 기준 코드는 추적형에 가깝다.

근거:

- 가격 이벤트를 캔들로 집계한다
- 닫힌 캔들에서만 판단한다
- `market_structure`가 최근 저점/고점, 이동평균, 거래량, 지지/저항 반응을 합산한다
- `HeartbeatStrategy`가 `IDLE`, `IN_POSITION`, `COOLDOWN` 상태를 추적한다
- 청산도 고정 박스 상단이 아니라 구조 붕괴, 이동평균 이탈, 매도 거래량, 저항 거절, 과열 등을 본다

따라서 현재 전략은 다음으로 분류한다.

```text
tracking-first heartbeat scalper
with structural box reference
```

박스형은 다음 조건이 있을 때 별도 후보로 본다.

```text
range low/high explicit definition
-> lower band entry
-> upper band exit
-> range invalidation
```

현재 구현의 지지/저항 사용은 box reference이지 box-first engine은 아니다.

### Binance vs Future Coinone

현재 구현은 Binance spot이다.

프로젝트 지향상 KRW/Coinone 확장 가능성이 있어도, Coinone은 별도 adapter로 다뤄야 한다.

Coinone API 기준은 `2.1`로 두되, 현재 Binance 경로에 섞지 않는다.

### State File Ownership

`state.json`이 어떤 mode/symbol/exchange 상태인지 명확히 표시되지 않으면 복구 위험이 있다.

즉시 삭제나 rewrite가 아니라 metadata audit부터 필요하다.

### PostgreSQL-First Storage Ownership

`08_DATABASE_ARCHITECTURE.md`는 PostgreSQL을 1차 DB로 정의한다.

핵심 방향:

- DB는 전략 판단 엔진이 아니라 runtime blackbox다.
- `state.json`은 hot state이고 PostgreSQL은 장기 이력과 복기용이다.
- `DATABASE_URL`은 env에 두며 원문을 출력하지 않는다.
- SQLite는 운영 기본 DB로 추가하지 않는다.
- live asset과 demo fake asset은 분리한다.
- live 주문 성공 후 ledger/DB 불일치는 `RECONCILIATION_REQUIRED`로 드러나야 한다.

남은 보강점:

- 03/04/05/06 문서에 `08_DATABASE_ARCHITECTURE.md`를 active control map으로 연결
- `DATABASE_ARCHITECTURE`, `POSTGRES_STORAGE`, `DB_MIGRATION`, `ASSET_TRACKING` AREA 등록
- migration과 DB recorder는 live order path와 분리해 단계적으로 추가
- SQLite 일반론은 unit test fixture나 임시 offline replay 후보로만 제한

## 6. Recommended First Codex Tasks

### CODE_TASK_CANDIDATE 1

```text
AREA: SYSTEM_ARCHITECTURE_DOCS + CODEX_HARNESS_DOCS + DATABASE_ARCHITECTURE
MODE: DOC_ONLY
PURPOSE FUNCTION:
08_DATABASE_ARCHITECTURE.md를 active harness 문서 세트에 연결하고 PostgreSQL-first 기준을 03/04/05/06에 반영한다.
FOCUS:
PostgreSQL-first, DATABASE_URL env protection, migration safety, demo fake asset/live asset separation, SQLite operational default ban.
STOP CONDITIONS:
runtime code, DB 접속, config.yaml secret 수정, live order.
```

### CODE_TASK_CANDIDATE 2

```text
AREA: POSTGRES_STORAGE + DB_MIGRATION + CONFIG_AND_SECRETS + TESTS
MODE: GUARDED_FIX
PURPOSE FUNCTION:
PostgreSQL foundation과 forward-only migration scaffold를 추가하되 live order 경로에는 연결하지 않는다.
FOCUS:
storage package, psycopg v3 candidate, DATABASE_URL redaction, scalper schema migration SQL, no-DB unit tests.
STOP CONDITIONS:
raw secret 출력, actual DB migration 실행, DROP/TRUNCATE, SQLite 운영 기본 DB 도입, Binance REST 변경.
```

### CODE_TASK_CANDIDATE 3

```text
AREA: RUNTIME_ENTRYPOINT + ORDER_GUARD
MODE: READ_ONLY_AUDIT
PURPOSE FUNCTION:
현재 기본 실행이 live로 향하는 위험을 분석하고, safe default 또는 explicit live confirmation 설계를 제안한다.
FOCUS:
run.py / run.bat / tests/test_run_guards.py 기준으로 현재 동작을 확인한다.
STOP CONDITIONS:
실제 주문 실행 금지, config secret 출력 금지.
```

### CODE_TASK_CANDIDATE 4

```text
AREA: CONFIG_AND_SECRETS
MODE: READ_ONLY_AUDIT
PURPOSE FUNCTION:
config.yaml의 민감정보와 일반 전략 설정을 분리하는 방안을 설계한다.
FOCUS:
real config 값은 출력하지 않고 key 존재 여부와 구조만 점검한다.
STOP CONDITIONS:
raw secret 노출 위험이 있으면 즉시 중단.
```

### CODE_TASK_CANDIDATE 5

```text
AREA: DATA_STREAM_BINANCE_WS + CANDLE_AGGREGATOR
MODE: READ_ONLY_AUDIT
PURPOSE FUNCTION:
trade/ticker/kline 혼합 이벤트가 candle aggregation에 중복 영향을 주는지 확인한다.
FOCUS:
message parsing, stream type tagging, closed candle processing once.
STOP CONDITIONS:
Binance REST 주문 경로 접근 금지.
```

### CODE_TASK_CANDIDATE 6

```text
AREA: STATE_RECOVERY
MODE: READ_ONLY_AUDIT
PURPOSE FUNCTION:
state.json이 mode/symbol/exchange 정보를 보존하지 않아 demo/live 복구가 섞일 위험이 있는지 확인한다.
FOCUS:
state snapshot fields, restore path, output file separation.
STOP CONDITIONS:
state 삭제 또는 rewrite 금지.
```

### CODE_TASK_CANDIDATE 7

```text
AREA: TESTS
MODE: GUARDED_FIX
PURPOSE FUNCTION:
live order 사고를 막는 회귀 테스트를 보강한다.
FOCUS:
real API call 없는 mock 기반 테스트만 추가한다.
STOP CONDITIONS:
실제 API key, Binance REST order call, live config 사용 금지.
```

### CODE_TASK_CANDIDATE 8

```text
AREA: STRATEGY_ARCHETYPE + MARKET_STRUCTURE_STRATEGY
MODE: READ_ONLY_AUDIT
PURPOSE FUNCTION:
현재 전략을 박스형, 추적형, 또는 hybrid/reference형으로 분류하고 README/테스트/코드 흐름과 문서가 일치하는지 점검한다.
FOCUS:
`CandleAggregator`, `market_structure`, `HeartbeatStrategy`, `tests/test_market_structure.py` 기준으로 current strategy archetype을 확정한다.
EXPECTED CURRENT CLASSIFICATION:
tracking-first heartbeat scalper with structural box reference.
STOP CONDITIONS:
실제 전략 threshold 변경 금지, hard exit 변경 금지, live order 실행 금지, config secret 출력 금지.
```

## 7. Risk Analysis

### Risk: 수익률 욕심이 하네스보다 앞서는 경우

위험:

- confirmation count 완화
- hard exit 제거
- cooldown 단축
- order size 증가
- 급등 추격 허용

완화:

- `MARKET_STRUCTURE_STRATEGY`는 MEDIUM-HIGH
- hard exit 약화는 보호 또는 최소 guarded
- 테스트와 behavior diff report 필수

### Risk: 기본 live mode 사고

위험:

- 인자 없이 실행
- `live_order_enabled=true`
- API key/secret 존재
- REST client 생성

완화:

- `RUNTIME_ENTRYPOINT` audit 우선
- safe command 문서화
- explicit live confirmation 설계

### Risk: secret contamination

위험:

- config 내용을 문서화하면서 key 노출
- 테스트 fixture에 실제 key 복사
- 에러 로그에 header/signature 출력

완화:

- `CONFIG_AND_SECRETS` HIGH
- sample에는 placeholder만
- report에는 raw secret 금지

### Risk: mixed stream candle distortion

위험:

- trade/ticker/kline을 같은 tick처럼 처리
- 같은 closed candle 재처리
- volume 왜곡

완화:

- stream type tagging
- duplicate policy
- parser/candle tests

### Risk: paper/live result confusion

위험:

- paper 수익을 live 수익으로 착각
- demo state를 live restore
- 같은 log file 공유

완화:

- mode/symbol/exchange output directory
- state metadata
- report에 mode 명시

## 8. Review Conclusion

기존 00~07 문서는 WorkConnect용으로 잘 만들어진 하네스였지만, 이 프로젝트에서는 외부 영향의 종류가 완전히 다르다.

핵심 변환은 다음이다.

```text
wrong public post prevention
-> wrong live order prevention
```

새 하네스의 중심 구조는 다음이어야 한다.

```text
Purpose Function
-> Trading Constitution
-> Market Data Quality
-> Mode / Order Boundary
-> Module Harnesses
-> Trigger Cards
-> Correction Loop
-> Verification Report
```

이 구조가 유지되면 Codex가 코드를 고치더라도 실주문, secret, 손절 약화, 상태 혼선을 먼저 막을 수 있다.
