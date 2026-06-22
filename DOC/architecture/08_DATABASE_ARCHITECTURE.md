# Heart Beat Coin Scalper – Database Architecture

작성일: 2026-06-22
수정일: 2026-06-22

## 0. 목적

이 문서는 `heart_beat_coin_scalper`의 DB 아키텍처 기준을 정의한다.

DB의 1차 목적은 매매 결정을 대신하는 것이 아니다.

DB의 목적은 다음이다.

```text
실행 기록
-> 15m/30m/1h/4h 캔들·볼륨 축적
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

1차 DB는 `PostgreSQL`로 한다.

이유:

- 사용자는 이미 로컬 PostgreSQL 서버를 보유하고 있다.
- SQLite를 별도로 추가하면 DB 파일, migration, 백업, 운영 경로가 하나 더 늘어난다.
- 캔들/전략판단/체결/자산 snapshot이 쌓이면 SQLite 파일이 빠르게 커질 수 있다.
- PostgreSQL은 장기 저장, 인덱스, JSONB, upsert, partition, dashboard 연동에 유리하다.
- 향후 여러 심볼, 여러 exchange, backtest, dashboard로 확장하기 쉽다.

SQLite는 기본 아키텍처에서 제외한다.

SQLite를 쓸 수 있는 경우는 다음처럼 제한한다.

```text
unit test fixture
임시 offline replay
PostgreSQL 서버가 없는 외부 배포판
```

운영 기준은 PostgreSQL이다.

### 1.2 PostgreSQL DB 역할

PostgreSQL은 매매 판단의 필수 의존성이 아니라 runtime blackbox다.

```text
전략 판단 = Python runtime / market_structure
DB = 기록, 복기, asset tracking, reconciliation
```

원칙:

- DB 오류가 있어도 demo 전략 계산 자체는 가능해야 한다.
- live 주문 경로에서 DB 기록 실패가 발생하면 안전하게 stop 또는 degraded mode로 전환해야 한다.
- live 주문 성공 후 DB/ledger 반영 실패는 `RECONCILIATION_REQUIRED`로 기록하고 다음 자동 주문을 중단한다.

### 1.3 secrets 저장 정책

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
- `.env` dump

향후 encrypted secret vault를 붙일 수는 있지만, 현재 로컬 스캘퍼 1차 설계에서는 env를 기준으로 한다.

### 1.4 저장할 캔들 단위

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

## 2. PostgreSQL 스키마 운영 기준

권장 schema:

```text
scalper
```

권장 DB 이름:

```text
heart_beat_coin_scalper
```

권장 연결 방식:

```text
DATABASE_URL=postgresql://user:password@localhost:5432/heart_beat_coin_scalper
```

주의:

- `DATABASE_URL`은 env에 둔다.
- DB password 원문은 문서, 로그, config snapshot에 저장하지 않는다.
- migration은 destructive operation 없이 forward-only로 시작한다.

## 3. 데이터 흐름

```text
exchange price source
-> timeframe aggregator or exchange kline fetcher
-> market_candle 15m / 30m / 1h / 4h
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

## 4. 주요 테이블 개요

### 4.1 `scalper.runtime_run`

실행 단위를 기록한다.

```sql
CREATE SCHEMA IF NOT EXISTS scalper;

CREATE TABLE IF NOT EXISTS scalper.runtime_run (
    id BIGSERIAL PRIMARY KEY,
    started_at TIMESTAMPTZ NOT NULL,
    ended_at TIMESTAMPTZ,
    mode TEXT NOT NULL CHECK (mode IN ('demo', 'paper', 'live', 'backtest')),
    exchange TEXT NOT NULL,
    market TEXT NOT NULL,
    symbol TEXT NOT NULL,
    quote_asset TEXT,
    base_asset TEXT,
    strategy_name TEXT NOT NULL,
    strategy_version TEXT NOT NULL,
    config_hash TEXT NOT NULL,
    live_order_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    status TEXT NOT NULL,
    stop_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

역할:

- 실행별 데이터 묶음 기준
- demo/live state 혼선 방지
- config 변경 후 결과 비교
- 장애 발생 시 어떤 실행에서 생긴 문제인지 추적

### 4.2 `scalper.runtime_config_snapshot`

secret을 제외한 설정 스냅샷을 저장한다.

```sql
CREATE TABLE IF NOT EXISTS scalper.runtime_config_snapshot (
    id BIGSERIAL PRIMARY KEY,
    run_id BIGINT NOT NULL REFERENCES scalper.runtime_run(id),
    config_hash TEXT NOT NULL,
    config_json JSONB NOT NULL,
    secret_fingerprint_json JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

금지:

- API key/secret 원문 저장 금지
- env dump 저장 금지

### 4.3 `scalper.market_candle`

15m/30m/1h/4h 캔들을 저장한다.

```sql
CREATE TABLE IF NOT EXISTS scalper.market_candle (
    id BIGSERIAL PRIMARY KEY,
    exchange TEXT NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL CHECK (timeframe IN ('15m', '30m', '1h', '4h')),
    open_time TIMESTAMPTZ NOT NULL,
    close_time TIMESTAMPTZ NOT NULL,
    open NUMERIC(28, 12) NOT NULL,
    high NUMERIC(28, 12) NOT NULL,
    low NUMERIC(28, 12) NOT NULL,
    close NUMERIC(28, 12) NOT NULL,
    volume_base NUMERIC(38, 12) NOT NULL DEFAULT 0,
    volume_quote NUMERIC(38, 12) NOT NULL DEFAULT 0,
    buy_volume_base NUMERIC(38, 12) DEFAULT 0,
    buy_volume_quote NUMERIC(38, 12) DEFAULT 0,
    sell_volume_base NUMERIC(38, 12) DEFAULT 0,
    sell_volume_quote NUMERIC(38, 12) DEFAULT 0,
    trade_count BIGINT DEFAULT 0,
    source TEXT NOT NULL,
    is_closed BOOLEAN NOT NULL DEFAULT TRUE,
    raw_json JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(exchange, symbol, timeframe, open_time)
);
```

저장 원칙:

- 기본 저장은 closed candle만 한다.
- 진행 중 candle 저장은 future dashboard 옵션으로 둔다.
- 매수/매도 볼륨이 거래소에서 직접 제공되지 않으면 추정값임을 `source` 또는 `raw_json`에 표시한다.
- 같은 `(exchange, symbol, timeframe, open_time)`은 upsert한다.

### 4.4 `scalper.strategy_decision`

전략 판단 근거를 저장한다.

```sql
CREATE TABLE IF NOT EXISTS scalper.strategy_decision (
    id BIGSERIAL PRIMARY KEY,
    run_id BIGINT NOT NULL REFERENCES scalper.runtime_run(id),
    candle_id BIGINT REFERENCES scalper.market_candle(id),
    decided_at TIMESTAMPTZ NOT NULL,
    mode TEXT NOT NULL,
    exchange TEXT NOT NULL,
    symbol TEXT NOT NULL,
    event TEXT NOT NULL,
    market_state TEXT,
    sideways_state TEXT,
    score_total INTEGER,
    score_structure INTEGER,
    score_volume INTEGER,
    score_ma INTEGER,
    score_support_resistance INTEGER,
    reasons TEXT[],
    confirmations TEXT[],
    current_price NUMERIC(28, 12),
    previous_low NUMERIC(28, 12),
    previous_high NUMERIC(28, 12),
    support NUMERIC(28, 12),
    resistance NUMERIC(28, 12),
    raw_decision_json JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

역할:

- 왜 진입했는지 기록
- 왜 진입하지 않았는지 기록
- 청산 사유 복기
- 전략 개선 전후 비교

### 4.5 `scalper.order_intent`

전략이 생성한 주문 의도를 저장한다.

```sql
CREATE TABLE IF NOT EXISTS scalper.order_intent (
    id BIGSERIAL PRIMARY KEY,
    run_id BIGINT NOT NULL REFERENCES scalper.runtime_run(id),
    decision_id BIGINT REFERENCES scalper.strategy_decision(id),
    created_at TIMESTAMPTZ NOT NULL,
    mode TEXT NOT NULL,
    exchange TEXT NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL CHECK (side IN ('BUY', 'SELL')),
    order_type TEXT NOT NULL DEFAULT 'MARKET',
    cash_budget NUMERIC(28, 12),
    qty_requested NUMERIC(38, 12),
    price_reference NUMERIC(28, 12),
    min_trade_cash NUMERIC(28, 12),
    status TEXT NOT NULL,
    skip_reason TEXT,
    error_message TEXT
);
```

역할:

- 전략이 실제로 주문하려 했는지 기록
- 최소 주문 금액 미달로 skip된 경우 기록
- live 주문 전후 상태 추적

### 4.6 `scalper.execution_result`

실제 또는 가상 체결 결과를 저장한다.

```sql
CREATE TABLE IF NOT EXISTS scalper.execution_result (
    id BIGSERIAL PRIMARY KEY,
    order_intent_id BIGINT NOT NULL REFERENCES scalper.order_intent(id),
    executed_at TIMESTAMPTZ NOT NULL,
    exchange TEXT NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL CHECK (side IN ('BUY', 'SELL')),
    qty_executed NUMERIC(38, 12) NOT NULL,
    avg_exec_price NUMERIC(28, 12) NOT NULL,
    gross_amount NUMERIC(38, 12),
    fee_amount NUMERIC(38, 12) DEFAULT 0,
    fee_asset TEXT,
    slippage_amount NUMERIC(38, 12) DEFAULT 0,
    external_order_id TEXT,
    raw_response_json JSONB,
    status TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

역할:

- live 주문 결과와 local ledger를 대조
- demo/fake 체결도 같은 구조로 기록
- 주문 성공 후 ledger 반영 실패 시 reconciliation 근거 제공

### 4.7 `scalper.live_asset_snapshot`

실시간 마지막 자산 상태를 저장한다.

```sql
CREATE TABLE IF NOT EXISTS scalper.live_asset_snapshot (
    id BIGSERIAL PRIMARY KEY,
    run_id BIGINT REFERENCES scalper.runtime_run(id),
    exchange TEXT NOT NULL,
    account_label TEXT NOT NULL DEFAULT 'default',
    captured_at TIMESTAMPTZ NOT NULL,
    asset TEXT NOT NULL,
    free_amount NUMERIC(38, 12) NOT NULL DEFAULT 0,
    locked_amount NUMERIC(38, 12) NOT NULL DEFAULT 0,
    total_amount NUMERIC(38, 12) NOT NULL DEFAULT 0,
    valuation_symbol TEXT,
    valuation_price NUMERIC(28, 12),
    valuation_quote NUMERIC(38, 12),
    source TEXT NOT NULL,
    is_latest BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

운영 원칙:

- 이 테이블은 “마지막으로 확인된 실자산 상태”를 저장한다.
- `is_latest=true`는 asset/account별 하나만 유지하는 것을 목표로 한다.
- live 주문 후 반드시 snapshot을 갱신하거나 `ASSET_REFRESH_REQUIRED` 상태를 남긴다.

### 4.8 `scalper.ledger_snapshot`

로컬 장부 상태를 저장한다.

```sql
CREATE TABLE IF NOT EXISTS scalper.ledger_snapshot (
    id BIGSERIAL PRIMARY KEY,
    run_id BIGINT NOT NULL REFERENCES scalper.runtime_run(id),
    decision_id BIGINT REFERENCES scalper.strategy_decision(id),
    execution_result_id BIGINT REFERENCES scalper.execution_result(id),
    captured_at TIMESTAMPTZ NOT NULL,
    mode TEXT NOT NULL,
    cash NUMERIC(38, 12) NOT NULL,
    position_qty NUMERIC(38, 12) NOT NULL,
    avg_price NUMERIC(28, 12) NOT NULL,
    realized_pnl NUMERIC(38, 12) NOT NULL,
    unrealized_pnl NUMERIC(38, 12) NOT NULL DEFAULT 0,
    fees_paid NUMERIC(38, 12) NOT NULL DEFAULT 0,
    slippage_paid NUMERIC(38, 12) NOT NULL DEFAULT 0,
    equity NUMERIC(38, 12) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

역할:

- `state.json`보다 긴 기간의 장부 이력 제공
- 장애 후 복기
- 수익률/손실률 추적

### 4.9 `scalper.demo_fake_account`

Demo/paper용 가상 계좌를 정의한다.

```sql
CREATE TABLE IF NOT EXISTS scalper.demo_fake_account (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    base_currency TEXT NOT NULL DEFAULT 'USDT',
    initial_cash NUMERIC(38, 12) NOT NULL,
    mode TEXT NOT NULL CHECK (mode IN ('demo', 'paper', 'backtest')),
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 4.10 `scalper.demo_fake_asset_snapshot`

Demo/paper fake asset의 마지막 상태를 저장한다.

```sql
CREATE TABLE IF NOT EXISTS scalper.demo_fake_asset_snapshot (
    id BIGSERIAL PRIMARY KEY,
    fake_account_id BIGINT NOT NULL REFERENCES scalper.demo_fake_account(id),
    run_id BIGINT REFERENCES scalper.runtime_run(id),
    captured_at TIMESTAMPTZ NOT NULL,
    asset TEXT NOT NULL,
    free_amount NUMERIC(38, 12) NOT NULL DEFAULT 0,
    locked_amount NUMERIC(38, 12) NOT NULL DEFAULT 0,
    total_amount NUMERIC(38, 12) NOT NULL DEFAULT 0,
    valuation_symbol TEXT,
    valuation_price NUMERIC(28, 12),
    valuation_quote NUMERIC(38, 12),
    is_latest BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

역할:

- demo에서 실제 계좌 없이 가상 보유량 추적
- 가상 매수/매도 후 fake balance 갱신
- paper/live 결과 비교의 기준점 제공

### 4.11 `scalper.asset_reconciliation_event`

실계좌/로컬 장부/fake asset 불일치 이벤트를 저장한다.

```sql
CREATE TABLE IF NOT EXISTS scalper.asset_reconciliation_event (
    id BIGSERIAL PRIMARY KEY,
    run_id BIGINT REFERENCES scalper.runtime_run(id),
    detected_at TIMESTAMPTZ NOT NULL,
    mode TEXT NOT NULL,
    exchange TEXT NOT NULL,
    symbol TEXT NOT NULL,
    severity TEXT NOT NULL,
    event_type TEXT NOT NULL,
    expected_json JSONB,
    actual_json JSONB,
    action_required TEXT,
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

역할:

- 실주문 성공 후 로컬 장부 반영 실패 감지
- state 복구 시 mode/symbol mismatch 감지
- live asset과 ledger 차이 감지

## 5. 인덱스 기준

```sql
CREATE INDEX IF NOT EXISTS idx_market_candle_symbol_tf_time
ON scalper.market_candle(exchange, symbol, timeframe, open_time);

CREATE INDEX IF NOT EXISTS idx_strategy_decision_run_time
ON scalper.strategy_decision(run_id, decided_at);

CREATE INDEX IF NOT EXISTS idx_order_intent_run_status
ON scalper.order_intent(run_id, status);

CREATE INDEX IF NOT EXISTS idx_execution_result_order
ON scalper.execution_result(order_intent_id);

CREATE INDEX IF NOT EXISTS idx_live_asset_latest
ON scalper.live_asset_snapshot(exchange, account_label, asset, is_latest);

CREATE INDEX IF NOT EXISTS idx_demo_fake_asset_latest
ON scalper.demo_fake_asset_snapshot(fake_account_id, asset, is_latest);
```

## 6. DB와 `state.json`의 관계

`state.json`은 빠른 복구용 latest state다.

PostgreSQL은 이력과 복기용이다.

```text
state.json = 현재 상태 복구용 hot state
PostgreSQL = 실행 이력, 판단 근거, 주문/체결/자산 추적용 blackbox
```

1차 구현에서는 `state.json`을 제거하지 않는다.

대신 DB 도입 후 다음 순서로 이동한다.

```text
현재 구조 유지
-> PostgreSQL append 기록 추가
-> state.json에 run_id / mode / exchange / symbol / strategy_version 추가
-> state mismatch guard 추가
-> 안정화 후 DB latest snapshot 기반 복구 검토
```

## 7. live 주문과 DB 기록 순서

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

## 8. demo/fake asset 처리 원칙

Demo 모드는 live 자산 테이블을 건드리지 않는다.

Demo 매수/매도는 다음 테이블에 기록한다.

```text
scalper.demo_fake_account
scalper.demo_fake_asset_snapshot
scalper.order_intent(mode=demo)
scalper.execution_result(status=FAKE_FILLED)
scalper.ledger_snapshot(mode=demo)
```

Fake asset은 실제 거래소 잔고가 아니라 시뮬레이션 잔고다.

주의:

- demo fake asset과 live asset을 같은 테이블에서 섞지 않는다.
- fake asset에는 exchange API 결과를 넣지 않는다.
- demo 결과를 live 복구 기준으로 쓰지 않는다.

## 9. timeframe candle 저장 정책

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
- buy/sell volume이 추정이면 `source` 또는 `raw_json`에 추정 표시

Future option:

```text
1m candle = DEBUG 또는 BACKTEST_BUILD 모드에서만 저장
raw tick = 기본 OFF
```

## 10. Coinone 확장 기준

현재 runtime은 Binance 중심이다.

Coinone은 future exchange adapter로 분리한다.

Coinone 관련 기준:

- Coinone 최신 API 기준은 `2.1`로 둔다.
- DB schema는 exchange 값을 통해 Binance/Coinone을 모두 수용한다.
- exchange별 raw response는 `raw_response_json` 또는 future `exchange_raw_event`에 저장한다.
- Coinone key/secret도 DB에 저장하지 않는다.

## 11. 1차 구현 우선순위

### Phase 1: PostgreSQL foundation

- PostgreSQL 연결 모듈 추가
- `DATABASE_URL` env 로더 추가
- migration runner 추가
- `scalper.runtime_run`, `scalper.runtime_config_snapshot` 생성
- secret 제외 config snapshot 저장

### Phase 2: market candle storage

- `scalper.market_candle` 생성
- 15m/30m/1h/4h candle 저장
- 1m/raw tick은 제외

### Phase 3: decision/order/execution storage

- `scalper.strategy_decision` 저장
- `scalper.order_intent` 저장
- `scalper.execution_result` 저장
- `scalper.ledger_snapshot` 저장

### Phase 4: asset tracking

- `scalper.live_asset_snapshot` 생성
- `scalper.demo_fake_account` 생성
- `scalper.demo_fake_asset_snapshot` 생성
- fake buy/sell tracing 추가

### Phase 5: reconciliation guard

- `scalper.asset_reconciliation_event` 생성
- order success + ledger failure 감지
- state mode/symbol mismatch 감지
- `RECONCILIATION_REQUIRED`면 다음 주문 중단

## 12. 하네스 보호 규칙

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
SQLite를 운영 기본 DB로 추가
```

## 13. 결론

DB는 매매 판단 엔진이 아니라 스캘퍼의 블랙박스다.

현재 1차 DB 목적은 다음 네 가지다.

```text
PostgreSQL에 15m/30m/1h/4h 시장 데이터 축적
전략 판단 근거 저장
실시간 마지막 자산 상태 추적
데모 fake asset 매수·매도 추적
```

이 기준으로 시작하면, 전략 개선보다 먼저 운영 안정성, 복기 가능성, 실계좌/로컬 장부 대조 능력을 확보할 수 있다.
