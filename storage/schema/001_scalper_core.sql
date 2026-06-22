CREATE SCHEMA IF NOT EXISTS scalper;

CREATE TABLE IF NOT EXISTS scalper.schema_migration (
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    checksum TEXT NOT NULL,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

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

CREATE TABLE IF NOT EXISTS scalper.runtime_config_snapshot (
    id BIGSERIAL PRIMARY KEY,
    run_id BIGINT NOT NULL REFERENCES scalper.runtime_run(id),
    config_hash TEXT NOT NULL,
    config_json JSONB NOT NULL,
    secret_fingerprint_json JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

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

CREATE TABLE IF NOT EXISTS scalper.demo_fake_account (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    base_currency TEXT NOT NULL DEFAULT 'USDT',
    initial_cash NUMERIC(38, 12) NOT NULL,
    mode TEXT NOT NULL CHECK (mode IN ('demo', 'paper', 'backtest')),
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

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

