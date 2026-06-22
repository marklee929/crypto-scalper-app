# Heart Beat Coin Scalper – Database Architecture

작성일: 2026-06-22

## 0. 목적

이 문서는 `heart_beat_coin_scalper`의 DB 아키텍처 기준을 정의한다.

DB의 1차 목적은 매매 결정을 대신하는 것이 아니다.

DB의 목적은 다음이다.

```text
실행 기록
-> 캔들/볼륨 축적
-> 전략 판단 근거 보존
-> 주문 의도 기록
-> 체결 결과 기록
-> 실시간 마지막 자산 상태 추적
-> demo/fake asset 가상 매수·매도 추적
-> 사고 발생 시 복구·대조·복기
```

전략 엔진은 DB 없이도 판단 가능해야 한다. DB는 `run.py` 또는 future harness layer에서 관찰성, 복구성, 재현성을 높이기 위해 붙는다.

## 1. 핵심 결정

### 1.1 DB 선택

1차 DB는 `SQLite`로 시작한다.

이유:

- 로컬 단일 봇 운영에 적합하다.
- 설정과 배포가 단순하다.
- 파일 백업이 쉽다.
- 테스트와 demo/paper trading 추적이 쉽다.
- 나중에 PostgreSQL로 옮길 수 있는 구조를 먼저 잡을 수 있다.

PostgreSQL은 다음 조건이 생긴 뒤 검토한다.

- 여러 봇 동시 운영
- 여러 심볼 장기 수집
- 웹 대시보드 실시간 조회
- 원격 서버 운영
- 백테스트 서버 분리
- 다중 사용자 또는 다중 계정 관리

### 1.2 secrets 저장 정책

API key, API secret, Telegram token, exchange secret은 DB에 저장하지 않는다.

기본 정책:

```text
secret value = env only
secret fingerprint = DB 저장 가능
runtime config non-secret value = DB 저장 가능
```

DB에 저장 가능한 값:

- exchange
- market
- symbol
- mode
- timeframe list
- trade_size_cash
- min_trade_cash
- fee_rate
- slippage_rate
- strategy_version
- config_hash
- live_order_enabled 여부
- secret fingerprint, 예: key 마지막 4자리 hash 또는 존재 여부

DB에 저장 금지:

- `BINANCE_API_KEY` 원문
- `BINANCE_API_SECRET` 원문
- Coinone secret 원문
- Telegram bot token 원문
- private key
- access token 원문

향후 encrypted secret vault를 붙일 수는 있지만, 현재 로컬 스캘퍼 1차 설계에서는 env를 기준으로 한다.

### 1.3 저장할 캔들 단위

분당 raw tick 또는 1m candle은 1차 저장 대상에서 제외한다.

저장 기본 timeframe:

```text
15m
30m
1h
4h
```

이유:

- 전략 복기와 큰 흐름 판단에는 15m 이상이 우선이다.
- raw tick/1m 저장은 용량과 노이즈가 빠르게 증가한다.
- 현재 핵심 목표는 실시간 자산 추적과 판단 복기다.

단, future debug mode에서만 `raw_price_event` 또는 `1m_candle` 저장을 선택적으로 열 수 있다.

## 2. 데이터 흐름

```text
exchange price source
-> timeframe aggregator or exchange kline fetcher
-> market_candle_15m / 30m / 1h / 4h
-> strategy decision
-> order intent
-> execution result
-> asset snapshot
-> ledger snapshot
```

Demo 모드는 별도 fake asset 계층을 사용한다.

```text
demo price source
-> timeframe candle
-> strategy decision
-> fake order intent
-> fake execution
-> fake asset snapshot
-> fake ledger snapshot
```

Live와 demo는 같은 판단 구조를 공유하되, 자산 테이블은 분리한다.

## 3. 주요 테이블 개요

### 3.1 `runtime_run`

실행 단위를 기록한다.

```sql
CREATE TABLE runtime_run (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    mode TEXT NOT NULL,              -- demo / paper / live / backtest
    exchange TEXT NOT NULL,          -- binance / coinone
    market TEXT NOT NULL,            -- spot
    symbol TEXT NOT NULL,
    quote_asset TEXT,
    base_asset TEXT,
    strategy_name TEXT NOT NULL,
    strategy_version TEXT NOT NULL,
    config_hash TEXT NOT NULL,
    live_order_enabled INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL,            -- RUNNING / STOPPED / FAILED / RECONCILIATION_REQUIRED
    stop_reason TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

역할:

- 실행별 데이터 묶음 기준
- demo/live state 혼선 방지
- config 변경 후 결과 비교
- 장애 발생 시 어떤 실행에서 생긴 문제인지 추적

### 3.2 `runtime_config_snapshot`

secret을 제외한 설정 스냅샷을 저장한다.

```sql
CREATE TABLE runtime_config_snapshot (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    config_hash TEXT NOT NULL,
    config_json TEXT NOT NULL,
    secret_fingerprint_json TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES runtime_run(id)
);
```

금지:

- API key/secret 원문 저장 금지
- env dump 저장 금지

### 3.3 `market_candle`

15m/30m/1h/4h 캔들을 저장한다.

```sql
CREATE TABLE market_candle (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exchange TEXT NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,         -- 15m / 30m / 1h / 4h
    open_time TEXT NOT NULL,
    close_time TEXT NOT NULL,
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    volume_base REAL NOT NULL DEFAULT 0,
    volume_quote REAL NOT NULL DEFAULT 0,
    buy_volume_base REAL DEFAULT 0,
    buy_volume_quote REAL DEFAULT 0,
    sell_volume_base REAL DEFAULT 0,
    sell_volume_quote REAL DEFAULT 0,
    trade_count INTEGER DEFAULT 0,
    source TEXT NOT NULL,            -- websocket_aggregated / exchange_kline / demo_generated
    is_closed INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(exchange, symbol, timeframe, open_time)
);
```

저장 원칙:

- 기본 저장은 closed candle만 한다.
- 진행 중 candle 저장은 future dashboard 옵션으로 둔다.
- 매수/매도 볼륨이 거래소에서 직접 제공되지 않으면 추정값임을 표시해야 한다.

### 3.4 `strategy_decision`

전략 판단 근거를 저장한다.

```sql
CREATE TABLE strategy_decision (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    candle_id INTEGER,
    decided_at TEXT NOT NULL,
    mode TEXT NOT NULL,
    exchange TEXT NOT NULL,
    symbol TEXT NOT NULL,
    event TEXT NOT NULL,             -- WAIT / NO_TRADE / ENTER / SCAN / EXIT / TAKE_PROFIT / BUY_SKIPPED
    market_state TEXT,
    sideways_state TEXT,
    score_total INTEGER,
    score_structure INTEGER,
    score_volume INTEGER,
    score_ma INTEGER,
    score_support_resistance INTEGER,
    reasons TEXT,
    confirmations TEXT,
    current_price REAL,
    previous_low REAL,
    previous_high REAL,
    support REAL,
    resistance REAL,
    raw_decision_json TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES runtime_run(id),
    FOREIGN KEY (candle_id) REFERENCES market_candle(id)
);
```

역할:

- 왜 진입했는지 기록
- 왜 진입하지 않았는지 기록
- 청산 사유 복기
- 전략 개선 전후 비교

### 3.5 `order_intent`

전략이 생성한 주문 의도를 저장한다.

```sql
CREATE TABLE order_intent (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    decision_id INTEGER,
    created_at TEXT NOT NULL,
    mode TEXT NOT NULL,              -- demo / paper / live
    exchange TEXT NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,              -- BUY / SELL
    order_type TEXT NOT NULL,        -- MARKET
    cash_budget REAL,
    qty_requested REAL,
    price_reference REAL,
    min_trade_cash REAL,
    status TEXT NOT NULL,            -- CREATED / SKIPPED / SENT / FAILED / FILLED / PARTIAL / RECONCILIATION_REQUIRED
    skip_reason TEXT,
    error_message TEXT,
    FOREIGN KEY (run_id) REFERENCES runtime_run(id),
    FOREIGN KEY (decision_id) REFERENCES strategy_decision(id)
);
```

역할:

- 전략이 실제로 주문하려 했는지 기록
- 최소 주문 금액 미달로 skip된 경우 기록
- live 주문 전후 상태 추적

### 3.6 `execution_result`

실제 또는 가상 체결 결과를 저장한다.

```sql
CREATE TABLE execution_result (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_intent_id INTEGER NOT NULL,
    executed_at TEXT NOT NULL,
    exchange TEXT NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    qty_executed REAL NOT NULL,
    avg_exec_price REAL NOT NULL,
    gross_amount REAL,
    fee_amount REAL DEFAULT 0,
    fee_asset TEXT,
    slippage_amount REAL DEFAULT 0,
    external_order_id TEXT,
    raw_response_json TEXT,
    status TEXT NOT NULL,            -- FILLED / PARTIAL / FAILED / FAKE_FILLED
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_intent_id) REFERENCES order_intent(id)
);
```

역할:

- live 주문 결과와 local ledger를 대조
- demo/fake 체결도 같은 구조로 기록
- 주문 성공 후 ledger 반영 실패 시 reconciliation 근거 제공

### 3.7 `live_asset_snapshot`

실시간 마지막 자산 상태를 저장한다.

```sql
CREATE TABLE live_asset_snapshot (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER,
    exchange TEXT NOT NULL,
    account_label TEXT NOT NULL DEFAULT 'default',
    captured_at TEXT NOT NULL,
    asset TEXT NOT NULL,             -- USDT / ROBO / BTC etc.
    free_amount REAL NOT NULL DEFAULT 0,
    locked_amount REAL NOT NULL DEFAULT 0,
    total_amount REAL NOT NULL DEFAULT 0,
    valuation_symbol TEXT,
    valuation_price REAL,
    valuation_quote REAL,
    source TEXT NOT NULL,            -- exchange_account / local_ledger / manual_import
    is_latest INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES runtime_run(id)
);
```

운영 원칙:

- 이 테이블은 “마지막으로 확인된 실자산 상태”를 저장한다.
- `is_latest=1`은 asset/account별 하나만 유지하는 것을 목표로 한다.
- live 주문 후 반드시 snapshot을 갱신하거나 `ASSET_REFRESH_REQUIRED` 상태를 남긴다.

### 3.8 `ledger_snapshot`

로컬 장부 상태를 저장한다.

```sql
CREATE TABLE ledger_snapshot (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    decision_id INTEGER,
    execution_result_id INTEGER,
    captured_at TEXT NOT NULL,
    mode TEXT NOT NULL,
    cash REAL NOT NULL,
    position_qty REAL NOT NULL,
    avg_price REAL NOT NULL,
    realized_pnl REAL NOT NULL,
    unrealized_pnl REAL NOT NULL DEFAULT 0,
    fees_paid REAL NOT NULL DEFAULT 0,
    slippage_paid REAL NOT NULL DEFAULT 0,
    equity REAL NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES runtime_run(id),
    FOREIGN KEY (decision_id) REFERENCES strategy_decision(id),
    FOREIGN KEY (execution_result_id) REFERENCES execution_result(id)
);
```

역할:

- `state.json`보다 긴 기간의 장부 이력 제공
- 장애 후 복기
- 수익률/손실률 추적

### 3.9 `demo_fake_account`

Demo/paper용 가상 계좌를 정의한다.

```sql
CREATE TABLE demo_fake_account (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    base_currency TEXT NOT NULL DEFAULT 'USDT',
    initial_cash REAL NOT NULL,
    mode TEXT NOT NULL,              -- demo / paper / backtest
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### 3.10 `demo_fake_asset_snapshot`

Demo/paper fake asset의 마지막 상태를 저장한다.

```sql
CREATE TABLE demo_fake_asset_snapshot (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fake_account_id INTEGER NOT NULL,
    run_id INTEGER,
    captured_at TEXT NOT NULL,
    asset TEXT NOT NULL,
    free_amount REAL NOT NULL DEFAULT 0,
    locked_amount REAL NOT NULL DEFAULT 0,
    total_amount REAL NOT NULL DEFAULT 0,
    valuation_symbol TEXT,
    valuation_price REAL,
    valuation_quote REAL,
    is_latest INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (fake_account_id) REFERENCES demo_fake_account(id),
    FOREIGN KEY (run_id) REFERENCES runtime_run(id)
);
```

역할:

- demo에서 실제 계좌 없이 가상 보유량 추적
- 가상 매수/매도 후 fake balance 갱신
- paper/live 결과 비교의 기준점 제공

### 3.11 `asset_reconciliation_event`

실계좌/로컬 장부/fake asset 불일치 이벤트를 저장한다.

```sql
CREATE TABLE asset_reconciliation_event (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER,
    detected_at TEXT NOT NULL,
    mode TEXT NOT NULL,
    exchange TEXT NOT NULL,
    symbol TEXT NOT NULL,
    severity TEXT NOT NULL,          -- INFO / WARNING / CRITICAL
    event_type TEXT NOT NULL,        -- LEDGER_MISMATCH / LIVE_ASSET_REFRESH_REQUIRED / ORDER_FILLED_LEDGER_FAILED
    expected_json TEXT,
    actual_json TEXT,
    action_required TEXT,
    resolved_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES runtime_run(id)
);
```

역할:

- 실주문 성공 후 로컬 장부 반영 실패 감지
- state 복구 시 mode/symbol mismatch 감지
- live asset과 ledger 차이 감지

## 4. 인덱스 기준

```sql
CREATE INDEX idx_market_candle_symbol_tf_time
ON market_candle(exchange, symbol, timeframe, open_time);

CREATE INDEX idx_strategy_decision_run_time
ON strategy_decision(run_id, decided_at);

CREATE INDEX idx_order_intent_run_status
ON order_intent(run_id, status);

CREATE INDEX idx_execution_result_order
ON execution_result(order_intent_id);

CREATE INDEX idx_live_asset_latest
ON live_asset_snapshot(exchange, account_label, asset, is_latest);

CREATE INDEX idx_demo_fake_asset_latest
ON demo_fake_asset_snapshot(fake_account_id, asset, is_latest);
```

## 5. DB와 `state.json`의 관계

`state.json`은 빠른 복구용 latest state다.

DB는 이력과 복기용이다.

```text
state.json = 현재 상태 복구용 hot state
SQLite DB = 실행 이력, 판단 근거, 주문/체결/자산 추적용 blackbox
```

1차 구현에서는 `state.json`을 제거하지 않는다.

대신 DB 도입 후 다음 순서로 이동한다.

```text
현재 구조 유지
-> DB append 기록 추가
-> state.json에 run_id / mode / exchange / symbol / strategy_version 추가
-> state mismatch guard 추가
-> 안정화 후 DB latest snapshot 기반 복구 검토
```

## 6. live 주문과 DB 기록 순서

Live 주문은 반드시 intent-first로 기록한다.

권장 순서:

```text
strategy decision 저장
-> order_intent CREATED 저장
-> 주문 전 local affordability check
-> live_order_enabled guard
-> exchange REST 주문 전송
-> execution_result 저장
-> ledger 반영
-> ledger_snapshot 저장
-> live_asset_snapshot 갱신 또는 ASSET_REFRESH_REQUIRED 기록
```

중요 stop condition:

```text
exchange 주문 성공
+ ledger 반영 실패
= RECONCILIATION_REQUIRED
```

이 경우 봇은 다음 자동 주문을 중단해야 한다.

## 7. demo/fake asset 처리 원칙

Demo 모드는 live 자산 테이블을 건드리지 않는다.

Demo 매수/매도는 다음 테이블에 기록한다.

```text
demo_fake_account
demo_fake_asset_snapshot
order_intent(mode=demo)
execution_result(status=FAKE_FILLED)
ledger_snapshot(mode=demo)
```

Fake asset은 실제 거래소 잔고가 아니라 시뮬레이션 잔고다.

주의:

- demo fake asset과 live asset을 같은 테이블에서 섞지 않는다.
- fake asset에는 exchange API 결과를 넣지 않는다.
- demo 결과를 live 복구 기준으로 쓰지 않는다.

## 8. timeframe candle 저장 정책

기본 수집/저장 대상:

```text
15m: 단기 박동 구조 확인
30m: 진입 방향 안정성 확인
1h: 중기 구조 확인
4h: 큰 흐름/위험 구간 확인
```

저장 원칙:

- closed candle만 기본 저장
- 같은 `(exchange, symbol, timeframe, open_time)`은 upsert
- volume 관련 필드는 가능한 한 원천 값을 보존
- buy/sell volume이 추정이면 source 또는 raw_json에 추정 표시

Future option:

```text
1m candle = DEBUG 또는 BACKTEST_BUILD 모드에서만 저장
raw tick = 기본 OFF
```

## 9. Coinone 확장 기준

현재 runtime은 Binance 중심이다.

Coinone은 future exchange adapter로 분리한다.

Coinone 관련 기준:

- Coinone 최신 API 기준은 `2.1`로 둔다.
- DB schema는 exchange 값을 통해 Binance/Coinone을 모두 수용한다.
- exchange별 raw response는 `raw_response_json` 또는 future `exchange_raw_event`에 저장한다.
- Coinone key/secret도 DB에 저장하지 않는다.

## 10. 1차 구현 우선순위

### Phase 1: DB foundation

- SQLite 연결 모듈 추가
- migration runner 추가
- `runtime_run`, `runtime_config_snapshot` 생성
- secret 제외 config snapshot 저장

### Phase 2: market candle storage

- `market_candle` 생성
- 15m/30m/1h/4h candle 저장
- 1m/raw tick은 제외

### Phase 3: decision/order/execution storage

- `strategy_decision` 저장
- `order_intent` 저장
- `execution_result` 저장
- `ledger_snapshot` 저장

### Phase 4: asset tracking

- `live_asset_snapshot` 생성
- `demo_fake_account` 생성
- `demo_fake_asset_snapshot` 생성
- fake buy/sell tracing 추가

### Phase 5: reconciliation guard

- `asset_reconciliation_event` 생성
- order success + ledger failure 감지
- state mode/symbol mismatch 감지
- `RECONCILIATION_REQUIRED`면 다음 주문 중단

## 11. 하네스 보호 규칙

DB 작업은 기본적으로 `DOC_ONLY` 또는 `GUARDED_FIX`로 처리한다.

보호영역:

- live order behavior
- API key/secret handling
- `config.yaml` secret 값
- destructive migration
- live asset overwrite
- fake asset/live asset 혼합

금지:

```text
DROP TABLE
TRUNCATE
secret 원문 DB 저장
live asset을 demo 결과로 갱신
DB 오류를 무시하고 live 주문 지속
```

## 12. 결론

DB는 매매 판단 엔진이 아니라 스캘퍼의 블랙박스다.

현재 1차 DB 목적은 다음 네 가지다.

```text
15m/30m/1h/4h 시장 데이터 축적
전략 판단 근거 저장
실시간 마지막 자산 상태 추적
데모 fake asset 매수·매도 추적
```

이 기준으로 시작하면, 전략 개선보다 먼저 운영 안정성, 복기 가능성, 실계좌/로컬 장부 대조 능력을 확보할 수 있다.
