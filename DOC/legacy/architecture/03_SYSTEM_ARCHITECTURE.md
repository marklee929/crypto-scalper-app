# System Boundary and Governance Map

## Purpose

이 문서는 `heart_beat_coin_scalper`의 시스템 경계, 책임 분리, 보호영역, 하네스 계층을 정의한다.

목표는 Python 스캘퍼가 단순 실주문 스크립트가 아니라, 데이터 입력부터 장부 기록까지 검증 가능한 런타임으로 유지되도록 하는 것이다.

## High-Level Architecture

현재 런타임은 다음 구조로 본다.

```text
config.yaml / CLI args
-> run.py
-> demo stream or Binance WebSocket
-> PriceEvent normalization
-> CandleAggregator
-> closed candle
-> HeartbeatStrategy.on_candle()
-> core.market_structure
-> StrategyDecision
-> OrderIntent
-> OrderGuard
-> Ledger or BinanceRestClient
-> state.json / trades.log / strategy.log / hourly_report.log
```

현재 핵심 의사결정은 닫힌 캔들 기준이다.

## Governance Layer

중앙 거버넌스는 전략 목적과 안전 경계를 정의한다.

```text
product constitution
-> strategy growth workflow
-> market data quality
-> system boundary
-> local runtime safety
-> Codex harness
-> work area registry
```

모듈 하네스는 이 경계 안에서만 실행한다.

전략 모듈이나 거래소 어댑터가 제품 목적을 재정의하면 안 된다.

## Document-to-Layer Control Map

- `00_PRODUCT_NORTH_STAR.md`: 전략 목적, 거래 헌법, 실주문 철학
- `01_SYSTEM_GROWTH_WORKFLOW.md`: 시장 가설부터 피드백까지의 성장 루프
- `02_DATA_SOURCE_AND_QUALITY.md`: 가격 데이터 검증, 시장 구조 분류, trigger cards
- `03_SYSTEM_ARCHITECTURE.md`: 시스템 책임과 경계
- `04_LOCAL_DEVELOPMENT_RUNTIME_GUIDE.md`: 로컬 실행 안전, live order 방어
- `05_CODEX_HARNESS_GUIDE.md`: Codex 작업 방식, mode, stop gates
- `06_WORK_AREA_REGISTRY.md`: 작업 영역별 허용/금지 경계
- `07_HARNESS_RESTRUCTURE_REVIEW.md`: 리뷰 참고 문서, 실행 규칙의 1차 권한자는 아님
- `08_DATABASE_ARCHITECTURE.md`: PostgreSQL-first 기록/복기/asset tracking/reconciliation 기준

## Runtime Component Map

### Runtime Entrypoint

- `run.py`
- `run.bat`

책임:

- config load
- mode selection
- stream selection
- tick processing
- strategy 연결
- order guard 연결
- state/log 연결

주의:

- 현재 기본 실행이 `live`로 향할 수 있으므로 보호영역이다.
- 기본값 변경은 실주문 안전에 영향을 줄 수 있다.

### Configuration

- `config.yaml`
- `core/config.py`

책임:

- exchange
- symbol
- fee/slippage
- order size
- min trade cash
- candle interval
- Binance API fields
- log/state paths

주의:

- `config.yaml`은 민감정보와 live 주문 설정을 포함할 수 있으므로 보호 대상으로 본다.
- 문서나 테스트에 실제 key 값을 복사하지 않는다.

### Data Stream

- `exchanges/binance/ws.py`
- demo stream in `run.py`

책임:

- Binance WebSocket 연결
- reconnect
- no-data watch
- trade/ticker/kline price extraction
- demo synthetic price generation

주의:

- stream type 혼합 정책이 필요하다.
- stale/duplicate event는 전략 입력 전 검증해야 한다.

### Candle Layer

- `core/candle_aggregator.py`

책임:

- raw tick을 OHLCV bucket으로 집계
- 새 bucket 시작 시 이전 candle을 closed로 반환

주의:

- 전략 판단은 closed candle에서만 실행한다.

### Strategy Layer

- `core/heartbeat.py`
- `core/market_structure.py`
- `core/volatility.py`
- `core/timeframe_guard.py`
- `core/oracle.py`

책임:

- 상태 머신
- 시장 구조 분류
- 진입/청산 판단
- 금지 조건 기록
- 향후 변동성/타임프레임/오라클 확장

주의:

- `volatility.py`, `timeframe_guard.py`, `oracle.py`는 현재 주 경로에 깊게 연결되지 않은 stub 성격이다.
- stub을 실제 신호처럼 취급하면 안 된다.

### Execution Layer

- `paper/ledger.py`
- `paper/report.py`
- `exchanges/binance/rest.py`

책임:

- paper 장부 반영
- live 주문 전송
- 체결 결과 기록
- 로그 리포트

주의:

- Binance REST 주문은 보호영역이다.
- live 주문 활성화, payload, 수량 포맷, API 인증 변경은 `PROTECTED_CHANGE`다.

### State and Logs

- `core/state.py`
- `state.json`
- `trades.log`
- `strategy.log`
- `hourly_report.log`

책임:

- 전략/장부 상태 저장
- 원자적 복구
- 거래 이벤트 로그
- 판단 로그
- 시간별 리포트

주의:

- 실행 모드별 산출물 분리가 필요하다.
- demo/live 상태가 섞이면 위험하다.

### PostgreSQL Storage Layer

- `DOC/architecture/08_DATABASE_ARCHITECTURE.md`
- future `storage/`
- future `storage/schema/`

책임:

- runtime_run 기록
- secret 제외 config snapshot 기록
- 15m / 30m / 1h / 4h closed candle 기록
- strategy decision 기록
- order intent와 execution result 분리 기록
- ledger snapshot 기록
- live asset snapshot과 demo fake asset snapshot 분리
- reconciliation event 기록

주의:

- 현재 코드의 핵심 실행 경로는 아직 DB에 의존하지 않는다.
- 하네스 기준 DB 아키텍처는 PostgreSQL-first다.
- PostgreSQL은 전략 판단 엔진이 아니라 기록, 복기, asset tracking, reconciliation 계층이다.
- `state.json`은 빠른 복구용 hot state이고, PostgreSQL은 장기 이력과 blackbox 기록용이다.
- DB password, API key, API secret, token 원문은 DB, 문서, 로그, 테스트에 저장하지 않는다.
- SQLite는 운영 기본 DB로 추가하지 않는다.
- destructive migration, live asset overwrite, demo fake asset/live asset mixing은 보호영역이다.

### Tests

- `tests/test_candle_aggregator.py`
- `tests/test_market_structure.py`
- `tests/test_binance_exchange.py`
- `tests/test_run_guards.py`

책임:

- 현재 동작 기준선 보존
- 캔들/전략/거래소 파싱/실행가드 회귀 방지

주의:

- 하네스가 런타임을 감싸더라도 이 테스트 기준선은 먼저 유지되어야 한다.

### Legacy App

- `crypto_scalper_app_legacy`

책임:

- 과거 Flutter/Dart 앱 참고자료

주의:

- 현재 Python 런타임과 같은 실행 단위로 취급하지 않는다.
- 레거시 앱 수정은 별도 AREA로 분리한다.

## Strategy Archetype Boundary

현재 아키텍처의 전략 계층은 박스 엔진이 아니라 추적 엔진이다.

```text
tracking engine ownership:
CandleAggregator closed candle
-> market_structure rolling classification
-> HeartbeatStrategy state transition
-> entry/exit reason
```

박스형 엔진을 추가하려면 다음 책임을 별도로 가진다.

```text
box engine ownership:
range discovery
-> box boundary state
-> box validity / breakout / breakdown
-> box-specific entry/exit
```

두 엔진은 같은 가격·캔들 데이터를 볼 수 있지만, 판단 책임은 섞지 않는다. 특히 `market_structure`의 지지/저항 반응을 이유로 현재 코드를 박스형으로 재분류하거나, 박스형 실험을 위해 기존 추적형 hard exit를 약화하지 않는다.

## Public Output vs Real Order Boundary

이 프로젝트에서 가장 중요한 외부 영향은 게시물이 아니라 실계좌 주문이다.

```text
demo log = 안전한 내부 출력
paper ledger = 모의 결과
strategy report = 운영 판단 자료
Binance REST market order = 실제 외부 영향
```

실주문은 보호영역이다.

로그가 성공했다고 해서 실주문이 안전하다는 뜻은 아니다.

paper 수익이 live 수익을 보장하지 않는다.

## Data vs Decision vs Execution Boundary

각 계층은 섞이면 안 된다.

```text
PriceEvent = 시장 입력
Candle = 집계 데이터
MarketState = 구조 분류
StrategyDecision = 판단
OrderIntent = 주문 후보
ExecutionResult = 실행 결과
LedgerSnapshot = 장부 상태
```

전략 판단이 곧 주문 실행이 되어서는 안 된다.

`OrderIntent`는 반드시 order guard를 통과해야 한다.

PostgreSQL 기록은 각 계층을 대체하지 않는다. DB 기록은 이미 발생한 입력, 판단, 주문 의도, 실행 결과, 장부 상태를 재현 가능하게 남기는 append 계층이다.

DB record 계층은 다음 책임을 가진다.

```text
DBRecord = PostgreSQL append 기록
AssetSnapshot = live asset 또는 demo fake asset 상태
ReconciliationEvent = 실행/장부/자산 불일치 기록
```

Demo fake asset과 live asset은 같은 테이블이나 같은 복구 기준으로 섞으면 안 된다.

## Local LLM Boundary

Local LLM 또는 외부 LLM은 선택적 보조 도구다.

허용:

- 로그 요약
- 실패 원인 분류
- 문서 정리
- 테스트 후보 제안

금지:

- 실주문 결정
- API key 처리
- 손절 조건 임의 완화
- 거래소 필터 추정 후 live 적용
- 수익 보장 표현

## Exchange Boundary

현재 거래소는 Binance spot이다.

향후 거래소 확장은 어댑터 단위로 분리한다.

```text
exchange adapter
-> stream adapter
-> order adapter
-> filter/precision adapter
-> account adapter
```

Coinone 확장 시 최신 API 기준은 `2.1`로 둔다.

거래소 확장은 인증, 주문, 수량 포맷, 최소 주문금액, 체결 응답이 모두 다르므로 보호영역으로 취급한다.

## Target Architecture Direction

프로젝트는 다음 방향으로 진화하는 것이 안전하다.

```text
explicit mode selection
-> separated runtime outputs
-> unified PriceEvent model
-> unified CandleUpdate model
-> StrategyDecision record
-> OrderIntent / OrderGuard separation
-> paper/live execution separation
-> LedgerSnapshot / StateSnapshot versioning
-> backtest/paper report comparison
-> exchange adapter expansion
```

PostgreSQL-first target은 다음을 추가한다.

```text
-> PostgreSQL append records
-> demo fake asset / live asset separation
-> reconciliation event and stop state
```

## Success Criteria

시스템 경계가 건강하면 다음이 가능하다.

- `run.py`가 모든 책임을 삼키지 않는다
- config, stream, candle, strategy, order, ledger, state가 분리된다
- live order는 명시적 보호영역으로 남는다
- API key/secret은 문서와 로그에 노출되지 않는다
- demo/paper/live 산출물이 섞이지 않는다
- PostgreSQL 기록과 `state.json`의 역할이 구분된다
- secret 원문이 DB/config snapshot/log/test에 저장되지 않는다
- live asset과 demo fake asset이 분리된다
- order/execution/ledger 불일치가 `RECONCILIATION_REQUIRED`로 드러난다
- stub 모듈을 실전 신호로 오해하지 않는다
- 레거시 앱은 참고자료로만 분리된다
- 테스트가 하네스 변경 후에도 기준선 역할을 한다
