from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Mapping, Optional

from core.market_structure import Candle
from paper.ledger import Ledger


ALLOWED_CANDLE_TIMEFRAMES = {
    "15m": timedelta(minutes=15),
    "30m": timedelta(minutes=30),
    "1h": timedelta(hours=1),
    "4h": timedelta(hours=4),
}


def build_market_candle_record(
    candle: Candle,
    *,
    exchange: str,
    symbol: str,
    timeframe: str,
    source: str,
) -> dict[str, Any]:
    if timeframe not in ALLOWED_CANDLE_TIMEFRAMES:
        raise ValueError(f"unsupported storage timeframe: {timeframe}")
    open_time = _parse_timestamp(candle.timestamp)
    return {
        "exchange": exchange,
        "symbol": symbol,
        "timeframe": timeframe,
        "open_time": open_time,
        "close_time": open_time + ALLOWED_CANDLE_TIMEFRAMES[timeframe],
        "open": candle.open,
        "high": candle.high,
        "low": candle.low,
        "close": candle.close,
        "volume_base": candle.volume,
        "volume_quote": 0.0,
        "source": source,
        "is_closed": True,
        "raw_json": {
            "open": candle.open,
            "high": candle.high,
            "low": candle.low,
            "close": candle.close,
            "volume": candle.volume,
            "timestamp": candle.timestamp,
        },
    }


def build_strategy_decision_record(
    decision: Mapping[str, Any],
    *,
    run_id: Optional[int],
    decided_at: datetime,
    mode: str,
    exchange: str,
    symbol: str,
    candle_id: Optional[int] = None,
) -> dict[str, Any]:
    score = decision.get("score") if isinstance(decision.get("score"), Mapping) else {}
    return {
        "run_id": run_id,
        "candle_id": candle_id,
        "decided_at": decided_at,
        "mode": mode,
        "exchange": exchange,
        "symbol": str(decision.get("symbol") or symbol),
        "event": str(decision.get("event") or "SCAN"),
        "market_state": decision.get("state"),
        "sideways_state": decision.get("sideways_state"),
        "score_total": score.get("total"),
        "score_structure": score.get("structure"),
        "score_volume": score.get("volume"),
        "score_ma": score.get("ma"),
        "score_support_resistance": score.get("support_resistance"),
        "reasons": _split_reasons(decision.get("reason")),
        "confirmations": list(decision.get("confirmations") or []),
        "current_price": decision.get("current_price"),
        "previous_low": decision.get("previous_low"),
        "previous_high": decision.get("previous_high"),
        "support": decision.get("support"),
        "resistance": decision.get("resistance"),
        "raw_decision_json": dict(decision),
    }


def build_ledger_snapshot_record(
    ledger: Ledger,
    *,
    current_price: float,
    run_id: Optional[int],
    captured_at: datetime,
    mode: str,
    decision_id: Optional[int] = None,
    execution_result_id: Optional[int] = None,
) -> dict[str, Any]:
    summary = ledger.summary(current_price)
    return {
        "run_id": run_id,
        "decision_id": decision_id,
        "execution_result_id": execution_result_id,
        "captured_at": captured_at,
        "mode": mode,
        "cash": summary["cash"],
        "position_qty": summary["position_qty"],
        "avg_price": summary["avg_price"],
        "realized_pnl": summary["realized_pnl"],
        "unrealized_pnl": summary["unrealized_pnl"],
        "fees_paid": summary["fees_paid"],
        "slippage_paid": summary["slippage_paid"],
        "equity": summary["equity"],
    }


def _split_reasons(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value if str(item)]
    return [item.strip() for item in str(value).split(",") if item.strip()]


def _parse_timestamp(value: str | None) -> datetime:
    if not value:
        raise ValueError("candle timestamp is required for storage record.")
    return datetime.fromisoformat(value)

