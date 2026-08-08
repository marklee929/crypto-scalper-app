from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
import os
from typing import Any, Mapping, Optional

from storage.fake_assets import build_demo_fake_asset_snapshots
from storage.postgres import connect, get_database_url_from_env
from storage.records import build_ledger_snapshot_record, build_strategy_decision_record


DB_ENABLED_ENV = "SCALPER_DB_ENABLED"
DEFAULT_STRATEGY_NAME = "heartbeat_market_structure"
DEFAULT_STRATEGY_VERSION = "market_structure_v1"
_SENSITIVE_KEY_PARTS = ("secret", "token", "password", "api_key", "apikey", "private_key")
_QUOTE_ASSETS = ("USDT", "USDC", "BUSD", "KRW", "BTC", "ETH")


@dataclass(frozen=True)
class RuntimeRunPayload:
    mode: str
    exchange: str
    market: str
    symbol: str
    quote_asset: Optional[str]
    base_asset: Optional[str]
    strategy_name: str
    strategy_version: str
    config_hash: str
    live_order_enabled: bool
    status: str = "RUNNING"


@dataclass(frozen=True)
class RuntimeStartResult:
    run_id: Optional[int]
    payload: RuntimeRunPayload
    db_enabled: bool
    disabled_reason: Optional[str] = None

    def as_state_metadata(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "mode": self.payload.mode,
            "exchange": self.payload.exchange,
            "market": self.payload.market,
            "symbol": self.payload.symbol,
            "strategy_name": self.payload.strategy_name,
            "strategy_version": self.payload.strategy_version,
            "config_hash": self.payload.config_hash,
            "db_enabled": self.db_enabled,
            "db_disabled_reason": self.disabled_reason,
        }


class DisabledRuntimeRecorder:
    def __init__(self, config: Mapping[str, Any], mode: str, reason: str) -> None:
        self._payload = build_runtime_run_payload(config, mode)
        self._reason = reason

    def start(self) -> RuntimeStartResult:
        return RuntimeStartResult(
            run_id=None,
            payload=self._payload,
            db_enabled=False,
            disabled_reason=self._reason,
        )

    def record_strategy_decision(self, *args, **kwargs) -> None:
        return None

    def record_ledger_snapshot(self, *args, **kwargs) -> None:
        return None

    def record_demo_execution_flow(self, *args, **kwargs) -> None:
        return None


class PostgresRuntimeRecorder:
    def __init__(self, connection, config: Mapping[str, Any], mode: str) -> None:
        self._connection = connection
        self._config = dict(config)
        self._payload = build_runtime_run_payload(config, mode)
        self._run_id: Optional[int] = None
        self._demo_fake_account_id: Optional[int] = None

    def start(self) -> RuntimeStartResult:
        now = datetime.now(UTC)
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO scalper.runtime_run(
                    started_at, mode, exchange, market, symbol, quote_asset, base_asset,
                    strategy_name, strategy_version, config_hash, live_order_enabled, status
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    now,
                    self._payload.mode,
                    self._payload.exchange,
                    self._payload.market,
                    self._payload.symbol,
                    self._payload.quote_asset,
                    self._payload.base_asset,
                    self._payload.strategy_name,
                    self._payload.strategy_version,
                    self._payload.config_hash,
                    self._payload.live_order_enabled,
                    self._payload.status,
                ),
            )
            run_id = int(cursor.fetchone()[0])
            cursor.execute(
                """
                INSERT INTO scalper.runtime_config_snapshot(
                    run_id, config_hash, config_json, secret_fingerprint_json
                )
                VALUES (%s, %s, %s::jsonb, %s::jsonb)
                """,
                (
                    run_id,
                    self._payload.config_hash,
                    json.dumps(sanitize_config(self._config), sort_keys=True),
                    json.dumps(secret_fingerprints(self._config), sort_keys=True),
                ),
            )
        self._connection.commit()
        self._run_id = run_id
        return RuntimeStartResult(run_id=run_id, payload=self._payload, db_enabled=True)

    def record_strategy_decision(
        self,
        decision: Mapping[str, Any],
        decided_at: datetime,
        *,
        candle_id: Optional[int] = None,
    ) -> Optional[int]:
        if self._run_id is None:
            return None
        record = build_strategy_decision_record(
            decision,
            run_id=self._run_id,
            decided_at=decided_at,
            mode=self._payload.mode,
            exchange=self._payload.exchange,
            symbol=self._payload.symbol,
            candle_id=candle_id,
        )
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO scalper.strategy_decision(
                    run_id, candle_id, decided_at, mode, exchange, symbol, event,
                    market_state, sideways_state, score_total, score_structure,
                    score_volume, score_ma, score_support_resistance, reasons,
                    confirmations, current_price, previous_low, previous_high,
                    support, resistance, raw_decision_json
                )
                VALUES (
                    %(run_id)s, %(candle_id)s, %(decided_at)s, %(mode)s, %(exchange)s,
                    %(symbol)s, %(event)s, %(market_state)s, %(sideways_state)s,
                    %(score_total)s, %(score_structure)s, %(score_volume)s,
                    %(score_ma)s, %(score_support_resistance)s, %(reasons)s,
                    %(confirmations)s, %(current_price)s, %(previous_low)s,
                    %(previous_high)s, %(support)s, %(resistance)s,
                    %(raw_decision_json)s::jsonb
                )
                RETURNING id
                """,
                {**record, "raw_decision_json": json.dumps(record["raw_decision_json"], sort_keys=True)},
            )
            decision_id = int(cursor.fetchone()[0])
        self._connection.commit()
        return decision_id

    def record_ledger_snapshot(
        self,
        ledger,
        current_price: float,
        captured_at: datetime,
        *,
        decision_id: Optional[int] = None,
        execution_result_id: Optional[int] = None,
    ) -> Optional[int]:
        if self._run_id is None:
            return None
        record = build_ledger_snapshot_record(
            ledger,
            current_price=current_price,
            run_id=self._run_id,
            captured_at=captured_at,
            mode=self._payload.mode,
            decision_id=decision_id,
            execution_result_id=execution_result_id,
        )
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO scalper.ledger_snapshot(
                    run_id, decision_id, execution_result_id, captured_at, mode,
                    cash, position_qty, avg_price, realized_pnl, unrealized_pnl,
                    fees_paid, slippage_paid, equity
                )
                VALUES (
                    %(run_id)s, %(decision_id)s, %(execution_result_id)s,
                    %(captured_at)s, %(mode)s, %(cash)s, %(position_qty)s,
                    %(avg_price)s, %(realized_pnl)s, %(unrealized_pnl)s,
                    %(fees_paid)s, %(slippage_paid)s, %(equity)s
                )
                RETURNING id
                """,
                record,
            )
            snapshot_id = int(cursor.fetchone()[0])
        self._connection.commit()
        return snapshot_id

    def record_demo_execution_flow(
        self,
        trade_event,
        ledger,
        current_price: float,
        captured_at: datetime,
        *,
        decision_id: Optional[int] = None,
    ) -> Optional[dict[str, int]]:
        if self._run_id is None or self._payload.mode not in {"demo", "paper", "backtest"}:
            return None
        fake_account_id = self._ensure_demo_fake_account(float(getattr(ledger, "initial_cash", 0.0)))
        quote_asset = self._payload.quote_asset or "USDT"
        base_asset = self._payload.base_asset or self._payload.symbol.replace(quote_asset, "") or self._payload.symbol
        gross_amount = float(trade_event.exec_price) * float(trade_event.qty)
        cash_budget = gross_amount + float(trade_event.fee) if trade_event.side == "BUY" else None
        snapshots = build_demo_fake_asset_snapshots(
            ledger,
            fake_account_id=fake_account_id,
            run_id=self._run_id,
            captured_at=captured_at,
            base_asset=base_asset,
            quote_asset=quote_asset,
            symbol=self._payload.symbol,
            current_price=current_price,
        )
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO scalper.order_intent(
                    run_id, decision_id, created_at, mode, exchange, symbol, side,
                    order_type, cash_budget, qty_requested, price_reference,
                    min_trade_cash, status
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    self._run_id,
                    decision_id,
                    captured_at,
                    self._payload.mode,
                    self._payload.exchange,
                    self._payload.symbol,
                    trade_event.side,
                    "MARKET",
                    cash_budget,
                    float(trade_event.qty),
                    float(trade_event.price),
                    None,
                    "FAKE_FILLED",
                ),
            )
            order_intent_id = int(cursor.fetchone()[0])
            cursor.execute(
                """
                INSERT INTO scalper.execution_result(
                    order_intent_id, executed_at, exchange, symbol, side, qty_executed,
                    avg_exec_price, gross_amount, fee_amount, fee_asset,
                    slippage_amount, external_order_id, raw_response_json, status
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NULL, %s)
                RETURNING id
                """,
                (
                    order_intent_id,
                    captured_at,
                    self._payload.exchange,
                    self._payload.symbol,
                    trade_event.side,
                    float(trade_event.qty),
                    float(trade_event.exec_price),
                    gross_amount,
                    float(trade_event.fee),
                    quote_asset,
                    float(trade_event.slippage),
                    None,
                    "FAKE_FILLED",
                ),
            )
            execution_result_id = int(cursor.fetchone()[0])
            ledger_record = build_ledger_snapshot_record(
                ledger,
                current_price=current_price,
                run_id=self._run_id,
                captured_at=captured_at,
                mode=self._payload.mode,
                decision_id=decision_id,
                execution_result_id=execution_result_id,
            )
            cursor.execute(
                """
                INSERT INTO scalper.ledger_snapshot(
                    run_id, decision_id, execution_result_id, captured_at, mode,
                    cash, position_qty, avg_price, realized_pnl, unrealized_pnl,
                    fees_paid, slippage_paid, equity
                )
                VALUES (
                    %(run_id)s, %(decision_id)s, %(execution_result_id)s,
                    %(captured_at)s, %(mode)s, %(cash)s, %(position_qty)s,
                    %(avg_price)s, %(realized_pnl)s, %(unrealized_pnl)s,
                    %(fees_paid)s, %(slippage_paid)s, %(equity)s
                )
                RETURNING id
                """,
                ledger_record,
            )
            ledger_snapshot_id = int(cursor.fetchone()[0])
            for snapshot in snapshots:
                cursor.execute(
                    """
                    UPDATE scalper.demo_fake_asset_snapshot
                    SET is_latest = FALSE
                    WHERE fake_account_id = %s AND asset = %s AND is_latest = TRUE
                    """,
                    (fake_account_id, snapshot["asset"]),
                )
                cursor.execute(
                    """
                    INSERT INTO scalper.demo_fake_asset_snapshot(
                        fake_account_id, run_id, captured_at, asset, free_amount,
                        locked_amount, total_amount, valuation_symbol, valuation_price,
                        valuation_quote, is_latest
                    )
                    VALUES (
                        %(fake_account_id)s, %(run_id)s, %(captured_at)s, %(asset)s,
                        %(free_amount)s, %(locked_amount)s, %(total_amount)s,
                        %(valuation_symbol)s, %(valuation_price)s, %(valuation_quote)s,
                        %(is_latest)s
                    )
                    """,
                    snapshot,
                )
        self._connection.commit()
        return {
            "order_intent_id": order_intent_id,
            "execution_result_id": execution_result_id,
            "ledger_snapshot_id": ledger_snapshot_id,
            "fake_account_id": fake_account_id,
        }

    def _ensure_demo_fake_account(self, initial_cash: float) -> int:
        if self._demo_fake_account_id is not None:
            return self._demo_fake_account_id
        if self._payload.mode not in {"demo", "paper", "backtest"}:
            raise RuntimeError("demo fake account is only available for demo-like modes")
        quote_asset = self._payload.quote_asset or "USDT"
        name = f"default:{self._payload.mode}:{self._payload.exchange}:{self._payload.symbol}"
        configured_initial_cash = float(self._config.get("initial_cash", initial_cash))
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id
                FROM scalper.demo_fake_account
                WHERE name = %s AND mode = %s AND status = 'ACTIVE'
                ORDER BY id
                LIMIT 1
                """,
                (name, self._payload.mode),
            )
            row = cursor.fetchone()
            if row is None:
                cursor.execute(
                    """
                    INSERT INTO scalper.demo_fake_account(name, base_currency, initial_cash, mode)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                    """,
                    (name, quote_asset, configured_initial_cash, self._payload.mode),
                )
                row = cursor.fetchone()
        self._connection.commit()
        self._demo_fake_account_id = int(row[0])
        return self._demo_fake_account_id


def create_runtime_recorder(
    config: Mapping[str, Any],
    mode: str,
    env: Mapping[str, str] | None = None,
):
    source_env = env if env is not None else os.environ
    if not _db_enabled(config, source_env):
        return DisabledRuntimeRecorder(config, mode, "disabled")
    database_url = get_database_url_from_env(source_env)
    if not database_url:
        return DisabledRuntimeRecorder(config, mode, "DATABASE_URL_not_configured")
    try:
        connection = connect(database_url)
    except Exception as exc:
        return DisabledRuntimeRecorder(config, mode, f"connect_failed:{type(exc).__name__}")
    return PostgresRuntimeRecorder(connection, config, mode)


def build_runtime_run_payload(config: Mapping[str, Any], mode: str) -> RuntimeRunPayload:
    symbol = str(config.get("symbol", "")).strip().upper()
    base_asset, quote_asset = split_symbol_assets(symbol)
    return RuntimeRunPayload(
        mode=str(mode),
        exchange=str(config.get("exchange", "binance")),
        market=str(config.get("market", "spot")),
        symbol=symbol,
        quote_asset=quote_asset,
        base_asset=base_asset,
        strategy_name=str(config.get("strategy_name", DEFAULT_STRATEGY_NAME)),
        strategy_version=str(config.get("strategy_version", DEFAULT_STRATEGY_VERSION)),
        config_hash=stable_config_hash(config),
        live_order_enabled=bool(config.get("live_order_enabled", False)),
    )


def sanitize_config(config: Mapping[str, Any]) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}
    for key, value in config.items():
        if _is_sensitive_key(str(key)):
            continue
        sanitized[str(key)] = _sanitize_value(value)
    return sanitized


def secret_fingerprints(config: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    fingerprints: dict[str, dict[str, Any]] = {}
    for key, value in config.items():
        key_text = str(key)
        if not _is_sensitive_key(key_text):
            continue
        value_text = "" if value is None else str(value)
        fingerprints[key_text] = {
            "present": bool(value_text),
            "fingerprint": _fingerprint(value_text) if value_text else None,
        }
    return fingerprints


def stable_config_hash(config: Mapping[str, Any]) -> str:
    payload = {
        "config": sanitize_config(config),
        "secret_fingerprints": secret_fingerprints(config),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def split_symbol_assets(symbol: str) -> tuple[Optional[str], Optional[str]]:
    normalized = str(symbol or "").strip().upper().replace("/", "").replace("-", "")
    for quote in _QUOTE_ASSETS:
        if normalized.endswith(quote) and len(normalized) > len(quote):
            return normalized[: -len(quote)], quote
    return (normalized or None), None


def _db_enabled(config: Mapping[str, Any], env: Mapping[str, str]) -> bool:
    config_value = config.get("postgres_enabled", config.get("db_enabled", False))
    env_value = str(env.get(DB_ENABLED_ENV, "")).strip().lower()
    return bool(config_value) or env_value in {"1", "true", "yes", "on"}


def _sanitize_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return sanitize_config(value)
    if isinstance(value, list):
        return [_sanitize_value(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize_value(item) for item in value]
    return value


def _is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    return any(part in lowered for part in _SENSITIVE_KEY_PARTS)


def _fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
