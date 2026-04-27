from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Deque, Optional

from core.market_structure import (
    Candle,
    EntryDecision,
    ExitDecision,
    MarketDecision,
    PositionContext,
    StructureConfig,
    can_enter,
    candle_from_tick,
    should_exit,
)


@dataclass
class HeartbeatSnapshot:
    state: str
    recent_low: Optional[float]
    entry_price: Optional[float]
    entry_low: Optional[float]
    entry_high: Optional[float]
    peak: Optional[float]
    armed: bool
    cooldown_until: Optional[str]
    cooldown_sec: int
    candles: list[dict[str, Any]]
    last_decision: dict[str, Any]


class HeartbeatStrategy:
    """Structure-based scalper state machine.

    The old percentage trigger is intentionally not used for entries. The
    configured 10% style amplitude is only passed into structure analysis as a
    volatility/overheat boundary.
    """

    def __init__(
        self,
        effective_gap: float,
        trailing_pct: float,
        cooldown_sec: int,
        *,
        symbol: str = "",
        max_candles: int = 80,
        structure_config: StructureConfig | None = None,
    ) -> None:
        self.effective_gap = effective_gap
        self.trailing_pct = trailing_pct
        self.arm_pct = effective_gap + trailing_pct
        self.cooldown_sec = cooldown_sec
        self.symbol = symbol
        self.structure_config = structure_config or StructureConfig(
            amplitude_pct=max(float(effective_gap), 0.10)
        )

        self.state = "IDLE"
        self.recent_low: Optional[float] = None
        self.entry_price: Optional[float] = None
        self.entry_low: Optional[float] = None
        self.entry_high: Optional[float] = None
        self.peak: Optional[float] = None
        self.armed = False
        self.cooldown_until: Optional[datetime] = None
        self._candles: Deque[Candle] = deque(maxlen=max_candles)
        self.last_decision: dict[str, Any] = {}

    def on_tick(
        self,
        price: float,
        timestamp: datetime,
        *,
        volume: float = 1.0,
        btc_state: Any = None,
    ) -> Optional[str]:
        # Legacy fallback for callers that still provide raw ticks. Runtime
        # paths aggregate ticks and call on_candle() with closed candles.
        candle = candle_from_tick(price, timestamp, volume)
        return self.on_candle(candle, btc_state=btc_state)

    def on_candle(
        self,
        candle: Candle,
        *,
        btc_state: Any = None,
    ) -> Optional[str]:
        self._candles.append(candle)
        candles = list(self._candles)
        price = candle.close
        timestamp = _parse_candle_timestamp(candle)

        if self.recent_low is None or price < self.recent_low:
            self.recent_low = price
        if self.peak is None or price > self.peak:
            self.peak = price

        if self.state == "COOLDOWN":
            if self.cooldown_until and timestamp >= self.cooldown_until:
                self.state = "IDLE"
                self.recent_low = price
            else:
                self._record_wait("cooldown", candles, btc_state)
                return None

        if self.state == "IDLE":
            entry = can_enter(candles, btc_state, self.structure_config)
            if not entry.allowed:
                self._record_entry_wait(entry)
                return None
            self.state = "IN_POSITION"
            self.entry_price = price
            self.entry_low = entry.market.previous_low or self.recent_low or price
            self.entry_high = entry.market.previous_high
            self.peak = price
            self.armed = True
            self._record_entry(entry)
            return "BUY"

        if self.state == "IN_POSITION" and self.entry_price:
            if self.peak is None or price > self.peak:
                self.peak = price
            exit_decision = should_exit(
                PositionContext(
                    entry_price=self.entry_price,
                    entry_low=self.entry_low,
                    entry_high=self.entry_high,
                    peak=self.peak,
                ),
                candles,
                btc_state,
                self.structure_config,
            )
            if exit_decision.should_exit:
                self.state = "COOLDOWN"
                self.cooldown_until = timestamp + timedelta(seconds=self.cooldown_sec)
                self._record_exit(exit_decision)
                return "SELL"
            self._record_hold(exit_decision.market)
        return None

    def snapshot(self) -> dict:
        return HeartbeatSnapshot(
            state=self.state,
            recent_low=self.recent_low,
            entry_price=self.entry_price,
            entry_low=self.entry_low,
            entry_high=self.entry_high,
            peak=self.peak,
            armed=self.armed,
            cooldown_until=self.cooldown_until.isoformat()
            if self.cooldown_until
            else None,
            cooldown_sec=self.cooldown_sec,
            candles=[c.__dict__ for c in self._candles],
            last_decision=self.last_decision,
        ).__dict__

    def restore(self, data: dict) -> None:
        self.state = data.get("state", self.state)
        self.recent_low = _to_optional_float(data.get("recent_low"))
        self.entry_price = _to_optional_float(data.get("entry_price"))
        self.entry_low = _to_optional_float(data.get("entry_low"))
        self.entry_high = _to_optional_float(data.get("entry_high"))
        self.peak = _to_optional_float(data.get("peak"))
        self.armed = bool(data.get("armed", self.armed))
        self.cooldown_sec = int(data.get("cooldown_sec", self.cooldown_sec))
        self.arm_pct = self.effective_gap + self.trailing_pct
        self.last_decision = dict(data.get("last_decision") or {})
        self._candles.clear()
        for row in data.get("candles") or []:
            try:
                self._candles.append(
                    Candle(
                        open=float(row["open"]),
                        high=float(row["high"]),
                        low=float(row["low"]),
                        close=float(row["close"]),
                        volume=float(row.get("volume", 0.0)),
                        timestamp=row.get("timestamp"),
                    )
                )
            except (KeyError, TypeError, ValueError):
                continue
        cooldown_until = data.get("cooldown_until")
        if cooldown_until:
            self.cooldown_until = datetime.fromisoformat(cooldown_until)
        else:
            self.cooldown_until = None

    def _record_wait(self, reason: str, candles: list[Candle], btc_state: Any) -> None:
        entry = can_enter(candles, btc_state, self.structure_config)
        self.last_decision = _base_log("WAIT", self.symbol, entry.market)
        self.last_decision["reason"] = reason

    def _record_entry_wait(self, entry: EntryDecision) -> None:
        event = "NO_TRADE" if entry.market.no_trade_reasons else "WAIT"
        reasons = entry.market.no_trade_reasons or entry.blocked_reasons
        self.last_decision = _base_log(event, self.symbol, entry.market)
        self.last_decision["reason"] = ",".join(reasons)
        self.last_decision["confirmations"] = list(entry.confirmations)

    def _record_entry(self, entry: EntryDecision) -> None:
        self.last_decision = _base_log("ENTER", self.symbol, entry.market)
        self.last_decision["reason"] = ",".join(entry.confirmations)
        self.last_decision["confirmations"] = list(entry.confirmations)
        self.last_decision["entry_price"] = self.entry_price
        self.last_decision["entry_low"] = self.entry_low

    def _record_hold(self, market: MarketDecision) -> None:
        self.last_decision = _base_log("SCAN", self.symbol, market)
        self.last_decision["reason"] = ",".join(market.reasons)
        self.last_decision["entry_price"] = self.entry_price
        self.last_decision["peak"] = self.peak

    def _record_exit(self, exit_decision: ExitDecision) -> None:
        event = "TAKE_PROFIT" if exit_decision.take_profit else "EXIT"
        self.last_decision = _base_log(event, self.symbol, exit_decision.market)
        self.last_decision["reason"] = ",".join(exit_decision.reasons)
        self.last_decision["entry_price"] = self.entry_price
        self.last_decision["entry_low"] = self.entry_low
        self.last_decision["peak"] = self.peak


def format_strategy_log(event: dict[str, Any], timestamp: str) -> str:
    score = event.get("score") or {}
    return (
        f"{timestamp} [{event.get('event', 'SCAN')}] symbol={event.get('symbol', '')} "
        f"state={event.get('state', '')} sideways={event.get('sideways_state', '')} "
        f"score={score.get('total', 0)} structure={score.get('structure', 0)} "
        f"volume={score.get('volume', 0)} ma={score.get('ma', 0)} "
        f"sr={score.get('support_resistance', 0)} reason={event.get('reason', '')} "
        f"price={_fmt(event.get('current_price'))} entry={_fmt(event.get('entry_price'))} "
        f"prev_low={_fmt(event.get('previous_low'))} prev_high={_fmt(event.get('previous_high'))} "
        f"support={_fmt(event.get('support'))} resistance={_fmt(event.get('resistance'))}"
    )


def _base_log(event: str, symbol: str, market: MarketDecision) -> dict[str, Any]:
    payload = market.as_dict()
    return {
        "event": event,
        "symbol": symbol,
        "state": payload["state"],
        "sideways_state": payload["sideways_state"],
        "score": payload["score"],
        "reason": ",".join(payload["no_trade_reasons"] or payload["reasons"]),
        "current_price": payload["current_price"],
        "previous_low": payload["previous_low"],
        "previous_high": payload["previous_high"],
        "support": payload["support"],
        "resistance": payload["resistance"],
    }


def _fmt(value: Any) -> str:
    if value is None:
        return ""
    try:
        return f"{float(value):.8f}"
    except (TypeError, ValueError):
        return str(value)


def _to_optional_float(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    return float(value)


def _parse_candle_timestamp(candle: Candle) -> datetime:
    if candle.timestamp:
        try:
            return datetime.fromisoformat(candle.timestamp)
        except ValueError:
            pass
    return datetime.utcnow()
