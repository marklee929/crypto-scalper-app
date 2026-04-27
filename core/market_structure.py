from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable, Mapping, Optional


class MarketState(str, Enum):
    NO_TRADE = "NO_TRADE"
    DEAD = "DEAD"
    FALLING = "FALLING"
    ACCUMULATION = "ACCUMULATION"
    HEARTBEAT = "HEARTBEAT"
    STRONG_HEARTBEAT = "STRONG_HEARTBEAT"


class SidewaysState(str, Enum):
    NONE = "NONE"
    ACCUMULATION_SIDEWAYS = "ACCUMULATION_SIDEWAYS"
    FALLING_SIDEWAYS = "FALLING_SIDEWAYS"


@dataclass(frozen=True)
class Candle:
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0
    timestamp: str | None = None


@dataclass(frozen=True)
class ScoreBreakdown:
    structure: int
    volume: int
    ma: int
    support_resistance: int

    @property
    def total(self) -> int:
        return self.structure + self.volume + self.ma + self.support_resistance

    def as_dict(self) -> dict[str, int]:
        return {
            "structure": self.structure,
            "volume": self.volume,
            "ma": self.ma,
            "support_resistance": self.support_resistance,
            "total": self.total,
        }


@dataclass(frozen=True)
class MarketDecision:
    state: MarketState
    sideways_state: SidewaysState
    score: ScoreBreakdown
    reasons: tuple[str, ...] = field(default_factory=tuple)
    no_trade_reasons: tuple[str, ...] = field(default_factory=tuple)
    current_price: Optional[float] = None
    previous_low: Optional[float] = None
    previous_high: Optional[float] = None
    support: Optional[float] = None
    resistance: Optional[float] = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "sideways_state": self.sideways_state.value,
            "score": self.score.as_dict(),
            "reasons": list(self.reasons),
            "no_trade_reasons": list(self.no_trade_reasons),
            "current_price": self.current_price,
            "previous_low": self.previous_low,
            "previous_high": self.previous_high,
            "support": self.support,
            "resistance": self.resistance,
        }


@dataclass(frozen=True)
class EntryDecision:
    allowed: bool
    state: MarketState
    score: ScoreBreakdown
    confirmations: tuple[str, ...]
    blocked_reasons: tuple[str, ...]
    market: MarketDecision


@dataclass(frozen=True)
class ExitDecision:
    should_exit: bool
    take_profit: bool
    reasons: tuple[str, ...]
    market: MarketDecision


@dataclass(frozen=True)
class PositionContext:
    entry_price: float
    entry_low: float | None = None
    entry_high: float | None = None
    peak: float | None = None


@dataclass(frozen=True)
class StructureConfig:
    min_candles: int = 8
    short_ma_window: int = 5
    trend_window: int = 6
    tolerance_pct: float = 0.002
    strong_hold_pct: float = 0.004
    big_red_body_pct: float = 0.025
    giant_green_body_pct: float = 0.06
    volume_dry_up_ratio: float = 0.55
    volume_increase_ratio: float = 1.2
    sell_volume_spike_ratio: float = 1.5
    max_spread_pct: float = 0.006
    min_avg_volume: float = 0.0
    amplitude_pct: float = 0.10


def candle_from_tick(price: float, timestamp: Any = None, volume: float = 1.0) -> Candle:
    ts = timestamp.isoformat() if hasattr(timestamp, "isoformat") else str(timestamp or "")
    return Candle(open=float(price), high=float(price), low=float(price), close=float(price), volume=float(volume), timestamp=ts or None)


def classify_market(
    candles: Iterable[Candle | Mapping[str, Any]],
    btc_state: Any = None,
    config: StructureConfig | None = None,
) -> MarketDecision:
    cfg = config or StructureConfig()
    rows = _coerce_candles(candles)
    blocked = has_no_trade_condition(rows, btc_state, cfg, return_reasons=True)
    score = ScoreBreakdown(
        structure=calc_structure_score(rows, cfg),
        volume=calc_volume_score(rows, cfg),
        ma=calc_ma_score(rows, cfg),
        support_resistance=calc_support_resistance_score(rows, cfg),
    )
    sideways = classify_sideways(rows, cfg)
    levels = _levels(rows)
    reasons = _score_reasons(rows, cfg)

    if blocked:
        state = MarketState.NO_TRADE
    elif sideways == SidewaysState.FALLING_SIDEWAYS:
        state = MarketState.FALLING
    elif score.total <= -5:
        state = MarketState.DEAD
    elif score.total <= 0:
        state = MarketState.FALLING
    elif score.total <= 4:
        state = MarketState.ACCUMULATION
    elif score.total <= 8:
        state = MarketState.HEARTBEAT
    else:
        state = MarketState.STRONG_HEARTBEAT

    return MarketDecision(
        state=state,
        sideways_state=sideways,
        score=score,
        reasons=tuple(reasons),
        no_trade_reasons=tuple(blocked),
        current_price=rows[-1].close if rows else None,
        previous_low=levels["previous_low"],
        previous_high=levels["previous_high"],
        support=levels["support"],
        resistance=levels["resistance"],
    )


def calc_structure_score(candles: Iterable[Candle | Mapping[str, Any]], config: StructureConfig | None = None) -> int:
    cfg = config or StructureConfig()
    rows = _coerce_candles(candles)
    score = 0
    if higher_low(rows, cfg):
        score += 2
    elif strong_low_hold(rows, cfg):
        score += 1
    if higher_high(rows, cfg):
        score += 2
    if lower_high(rows, cfg):
        score -= 2
    if broke_previous_low(rows, cfg):
        score -= 4
    return score


def calc_volume_score(candles: Iterable[Candle | Mapping[str, Any]], config: StructureConfig | None = None) -> int:
    cfg = config or StructureConfig()
    rows = _coerce_candles(candles)
    score = 0
    if buy_volume_increasing(rows, cfg):
        score += 2
    if sell_volume_decreasing(rows, cfg):
        score += 2
    if sell_volume_spike(rows, cfg):
        score -= 3
    if volume_dry_up(rows, cfg):
        score -= 1
    return score


def calc_ma_score(candles: Iterable[Candle | Mapping[str, Any]], config: StructureConfig | None = None) -> int:
    cfg = config or StructureConfig()
    rows = _coerce_candles(candles)
    score = 0
    if recovered_short_ma(rows, cfg):
        score += 2
    elif holds_short_ma(rows, cfg):
        score += 1
    if below_short_ma(rows, cfg):
        score -= 2
    if dead_cross(rows, cfg):
        score -= 3
    return score


def calc_support_resistance_score(candles: Iterable[Candle | Mapping[str, Any]], config: StructureConfig | None = None) -> int:
    cfg = config or StructureConfig()
    rows = _coerce_candles(candles)
    score = 0
    if resistance_break_and_hold(rows, cfg):
        score += 3
    elif resistance_touch_hold(rows, cfg):
        score += 2
    if strong_rejection_at_resistance(rows, cfg):
        score -= 3
    if broke_previous_low(rows, cfg):
        score -= 4
    return score


def classify_sideways(candles: Iterable[Candle | Mapping[str, Any]], config: StructureConfig | None = None) -> SidewaysState:
    cfg = config or StructureConfig()
    rows = _coerce_candles(candles)
    accumulation = [
        not broke_previous_low(rows, cfg),
        higher_low(rows, cfg),
        higher_high(rows, cfg),
        sell_volume_decreasing(rows, cfg),
        buy_volume_increasing(rows, cfg),
        recovered_short_ma(rows, cfg) or holds_short_ma(rows, cfg),
        repeated_resistance_tests(rows, cfg),
    ]
    falling = [
        strong_low_hold(rows, cfg) and not higher_low(rows, cfg),
        lower_high(rows, cfg),
        weak_rebound_volume(rows, cfg),
        sell_volume_spike(rows, cfg),
        below_short_ma(rows, cfg),
        failed_resistance_retest(rows, cfg),
    ]
    if sum(accumulation) >= 3:
        return SidewaysState.ACCUMULATION_SIDEWAYS
    if sum(falling) >= 3:
        return SidewaysState.FALLING_SIDEWAYS
    return SidewaysState.NONE


def has_no_trade_condition(
    candles: Iterable[Candle | Mapping[str, Any]],
    btc_state: Any = None,
    config: StructureConfig | None = None,
    *,
    return_reasons: bool = False,
) -> bool | list[str]:
    cfg = config or StructureConfig()
    rows = _coerce_candles(candles)
    reasons: list[str] = []
    context = _btc_context(btc_state)
    if len(rows) < cfg.min_candles:
        reasons.append("insufficient_data")
    if broke_previous_low(rows, cfg):
        reasons.append("broke_previous_low")
    if highs_keep_falling(rows, cfg):
        reasons.append("lower_high_sequence")
    if sideways_below_ma(rows, cfg):
        reasons.append("sideways_below_ma")
    if sell_volume_spike(rows, cfg):
        reasons.append("sell_volume_spike")
    if strong_rejection_at_resistance(rows, cfg):
        reasons.append("rejection_at_resistance")
    if context.get("state") == "DUMPING" or context.get("dumping"):
        reasons.append("btc_dumping")
    if float(context.get("spread_pct") or 0.0) > cfg.max_spread_pct:
        reasons.append("spread_too_wide")
    if avg_volume(rows[-cfg.trend_window :]) < cfg.min_avg_volume:
        reasons.append("low_liquidity")
    if context.get("new_listing") or context.get("first_listing_day"):
        reasons.append("new_listing_first_day")
    if context.get("news_spike") or context.get("narrative_chase"):
        reasons.append("news_spike_chase")
    if overheat_after_large_move(rows, cfg):
        reasons.append("overheated_chase")
    return reasons if return_reasons else bool(reasons)


def can_enter(
    candles: Iterable[Candle | Mapping[str, Any]],
    btc_state: Any = None,
    config: StructureConfig | None = None,
) -> EntryDecision:
    cfg = config or StructureConfig()
    rows = _coerce_candles(candles)
    market = classify_market(rows, btc_state, cfg)
    if market.no_trade_reasons:
        return EntryDecision(False, market.state, market.score, (), market.no_trade_reasons, market)
    if market.state not in {MarketState.HEARTBEAT, MarketState.STRONG_HEARTBEAT}:
        return EntryDecision(False, market.state, market.score, (), ("state_not_enterable",), market)

    confirmations: list[str] = []
    if higher_low(rows, cfg) or strong_low_hold(rows, cfg):
        confirmations.append("higher_low_or_strong_hold")
    if higher_high(rows, cfg):
        confirmations.append("higher_high")
    if recovered_short_ma(rows, cfg):
        confirmations.append("ma_reclaim")
    if sell_volume_decreasing(rows, cfg):
        confirmations.append("sell_volume_down")
    if buy_volume_increasing(rows, cfg):
        confirmations.append("buy_volume_up")
    if resistance_break_and_hold(rows, cfg):
        confirmations.append("resistance_break_hold")
    allowed = len(confirmations) >= 3
    return EntryDecision(
        allowed=allowed,
        state=market.state,
        score=market.score,
        confirmations=tuple(confirmations),
        blocked_reasons=() if allowed else ("not_enough_confirmations",),
        market=market,
    )


def should_exit(
    position: PositionContext | Mapping[str, Any],
    candles: Iterable[Candle | Mapping[str, Any]],
    btc_state: Any = None,
    config: StructureConfig | None = None,
) -> ExitDecision:
    cfg = config or StructureConfig()
    rows = _coerce_candles(candles)
    market = classify_market(rows, btc_state, cfg)
    pos = _coerce_position(position)
    reasons: list[str] = []
    take_profit_reasons: list[str] = []
    context = _btc_context(btc_state)

    if context.get("state") == "DUMPING" or context.get("dumping"):
        reasons.append("btc_dumping")
    if broke_entry_structure(pos, rows, cfg):
        reasons.append("entry_structure_break")
    if broke_previous_low(rows, cfg):
        reasons.append("broke_previous_low")
    if lost_short_ma(rows, cfg):
        reasons.append("lost_short_ma")
    if sell_volume_spike(rows, cfg):
        reasons.append("sell_volume_spike")
    if failed_to_make_new_high(rows, cfg):
        reasons.append("failed_new_high")
    if strong_rejection_at_resistance(rows, cfg):
        reasons.append("rejection_at_resistance")

    if resistance_touch(rows, cfg):
        take_profit_reasons.append("resistance_touch")
    if overheat_after_large_move(rows, cfg):
        take_profit_reasons.append("short_term_overheat")
    if upper_wicks_increasing(rows, cfg):
        take_profit_reasons.append("upper_wicks_increasing")
    if buy_volume_decreasing(rows, cfg):
        take_profit_reasons.append("buy_volume_down")
    if failed_to_make_new_high(rows, cfg):
        take_profit_reasons.append("failed_new_high")

    all_reasons = tuple(reasons or take_profit_reasons)
    return ExitDecision(
        should_exit=bool(reasons or take_profit_reasons),
        take_profit=bool(take_profit_reasons),
        reasons=all_reasons,
        market=market,
    )


def higher_low(candles: Iterable[Candle | Mapping[str, Any]], config: StructureConfig | None = None) -> bool:
    cfg = config or StructureConfig()
    prev, recent = _split_recent(_coerce_candles(candles), cfg.trend_window)
    return bool(prev and recent and min(c.low for c in recent) > min(c.low for c in prev) * (1 + cfg.tolerance_pct))


def strong_low_hold(candles: Iterable[Candle | Mapping[str, Any]], config: StructureConfig | None = None) -> bool:
    cfg = config or StructureConfig()
    prev, recent = _split_recent(_coerce_candles(candles), cfg.trend_window)
    if not prev or not recent:
        return False
    prev_low = min(c.low for c in prev)
    recent_low = min(c.low for c in recent)
    return recent_low >= prev_low * (1 - cfg.strong_hold_pct)


def higher_high(candles: Iterable[Candle | Mapping[str, Any]], config: StructureConfig | None = None) -> bool:
    cfg = config or StructureConfig()
    prev, recent = _split_recent(_coerce_candles(candles), cfg.trend_window)
    return bool(prev and recent and max(c.high for c in recent) > max(c.high for c in prev) * (1 + cfg.tolerance_pct))


def lower_high(candles: Iterable[Candle | Mapping[str, Any]], config: StructureConfig | None = None) -> bool:
    cfg = config or StructureConfig()
    prev, recent = _split_recent(_coerce_candles(candles), cfg.trend_window)
    return bool(prev and recent and max(c.high for c in recent) < max(c.high for c in prev) * (1 - cfg.tolerance_pct))


def broke_previous_low(candles: Iterable[Candle | Mapping[str, Any]], config: StructureConfig | None = None) -> bool:
    cfg = config or StructureConfig()
    rows = _coerce_candles(candles)
    if len(rows) < 2:
        return False
    lookback = rows[-(cfg.trend_window + 1) : -1]
    if not lookback:
        return False
    return rows[-1].close < min(c.low for c in lookback) * (1 - cfg.tolerance_pct)


def recovered_short_ma(candles: Iterable[Candle | Mapping[str, Any]], config: StructureConfig | None = None) -> bool:
    cfg = config or StructureConfig()
    rows = _coerce_candles(candles)
    if len(rows) <= cfg.short_ma_window:
        return False
    prev_ma = _sma(rows[:-1], cfg.short_ma_window)
    now_ma = _sma(rows, cfg.short_ma_window)
    return prev_ma is not None and now_ma is not None and rows[-2].close <= prev_ma and rows[-1].close > now_ma


def holds_short_ma(candles: Iterable[Candle | Mapping[str, Any]], config: StructureConfig | None = None) -> bool:
    cfg = config or StructureConfig()
    rows = _coerce_candles(candles)
    ma = _sma(rows, cfg.short_ma_window)
    return bool(ma is not None and rows and rows[-1].close >= ma)


def below_short_ma(candles: Iterable[Candle | Mapping[str, Any]], config: StructureConfig | None = None) -> bool:
    cfg = config or StructureConfig()
    rows = _coerce_candles(candles)
    ma = _sma(rows, cfg.short_ma_window)
    return bool(ma is not None and rows and rows[-1].close < ma)


def lost_short_ma(candles: Iterable[Candle | Mapping[str, Any]], config: StructureConfig | None = None) -> bool:
    cfg = config or StructureConfig()
    rows = _coerce_candles(candles)
    if len(rows) <= cfg.short_ma_window:
        return False
    prev_ma = _sma(rows[:-1], cfg.short_ma_window)
    now_ma = _sma(rows, cfg.short_ma_window)
    return bool(prev_ma is not None and now_ma is not None and rows[-2].close >= prev_ma and rows[-1].close < now_ma)


def dead_cross(candles: Iterable[Candle | Mapping[str, Any]], config: StructureConfig | None = None) -> bool:
    rows = _coerce_candles(candles)
    if len(rows) < 10:
        return False
    short_prev = _sma(rows[:-1], 3)
    long_prev = _sma(rows[:-1], 8)
    short_now = _sma(rows, 3)
    long_now = _sma(rows, 8)
    return bool(short_prev and long_prev and short_now and long_now and short_prev >= long_prev and short_now < long_now)


def buy_volume_increasing(candles: Iterable[Candle | Mapping[str, Any]], config: StructureConfig | None = None) -> bool:
    cfg = config or StructureConfig()
    prev, recent = _split_recent(_green_candles(_coerce_candles(candles)), cfg.trend_window)
    return bool(prev and recent and avg_volume(recent) > avg_volume(prev) * cfg.volume_increase_ratio)


def buy_volume_decreasing(candles: Iterable[Candle | Mapping[str, Any]], config: StructureConfig | None = None) -> bool:
    cfg = config or StructureConfig()
    prev, recent = _split_recent(_green_candles(_coerce_candles(candles)), cfg.trend_window)
    return bool(prev and recent and avg_volume(recent) < avg_volume(prev) / cfg.volume_increase_ratio)


def sell_volume_decreasing(candles: Iterable[Candle | Mapping[str, Any]], config: StructureConfig | None = None) -> bool:
    cfg = config or StructureConfig()
    prev, recent = _split_recent(_red_candles(_coerce_candles(candles)), cfg.trend_window)
    return bool(prev and recent and avg_volume(recent) < avg_volume(prev) / cfg.volume_increase_ratio)


def sell_volume_spike(candles: Iterable[Candle | Mapping[str, Any]], config: StructureConfig | None = None) -> bool:
    cfg = config or StructureConfig()
    rows = _coerce_candles(candles)
    red = _red_candles(rows)
    if len(red) < 2 or not rows or rows[-1].close >= rows[-1].open:
        return False
    baseline = avg_volume(red[:-1])
    return baseline > 0 and rows[-1].volume >= baseline * cfg.sell_volume_spike_ratio


def volume_dry_up(candles: Iterable[Candle | Mapping[str, Any]], config: StructureConfig | None = None) -> bool:
    cfg = config or StructureConfig()
    prev, recent = _split_recent(_coerce_candles(candles), cfg.trend_window)
    return bool(prev and recent and avg_volume(recent) < avg_volume(prev) * cfg.volume_dry_up_ratio)


def weak_rebound_volume(candles: Iterable[Candle | Mapping[str, Any]], config: StructureConfig | None = None) -> bool:
    return buy_volume_decreasing(candles, config) or not buy_volume_increasing(candles, config)


def resistance_break_and_hold(candles: Iterable[Candle | Mapping[str, Any]], config: StructureConfig | None = None) -> bool:
    cfg = config or StructureConfig()
    rows = _coerce_candles(candles)
    resistance = _previous_high(rows, cfg.trend_window)
    return bool(resistance and rows and rows[-1].close > resistance * (1 + cfg.tolerance_pct))


def resistance_touch_hold(candles: Iterable[Candle | Mapping[str, Any]], config: StructureConfig | None = None) -> bool:
    cfg = config or StructureConfig()
    rows = _coerce_candles(candles)
    resistance = _previous_high(rows, cfg.trend_window)
    return bool(resistance and rows and rows[-1].high >= resistance * (1 - cfg.tolerance_pct) and rows[-1].close >= resistance * (1 - cfg.strong_hold_pct))


def resistance_touch(candles: Iterable[Candle | Mapping[str, Any]], config: StructureConfig | None = None) -> bool:
    cfg = config or StructureConfig()
    rows = _coerce_candles(candles)
    resistance = _previous_high(rows, cfg.trend_window)
    return bool(resistance and rows and rows[-1].high >= resistance * (1 - cfg.tolerance_pct))


def strong_rejection_at_resistance(candles: Iterable[Candle | Mapping[str, Any]], config: StructureConfig | None = None) -> bool:
    cfg = config or StructureConfig()
    rows = _coerce_candles(candles)
    if not rows:
        return False
    resistance = _previous_high(rows, cfg.trend_window)
    last = rows[-1]
    body_pct = (last.open - last.close) / last.open if last.open > 0 else 0.0
    upper_wick = last.high - max(last.open, last.close)
    candle_range = max(last.high - last.low, 0.0)
    wick_ratio = upper_wick / candle_range if candle_range > 0 else 0.0
    return bool(resistance and last.high >= resistance * (1 - cfg.tolerance_pct) and (body_pct >= cfg.big_red_body_pct or wick_ratio >= 0.45))


def failed_to_make_new_high(candles: Iterable[Candle | Mapping[str, Any]], config: StructureConfig | None = None) -> bool:
    cfg = config or StructureConfig()
    rows = _coerce_candles(candles)
    if len(rows) < cfg.trend_window:
        return False
    resistance = _previous_high(rows, cfg.trend_window)
    return bool(resistance and rows[-1].high < resistance * (1 - cfg.tolerance_pct) and lower_high(rows, cfg))


def repeated_resistance_tests(candles: Iterable[Candle | Mapping[str, Any]], config: StructureConfig | None = None) -> bool:
    cfg = config or StructureConfig()
    rows = _coerce_candles(candles)
    resistance = _previous_high(rows, cfg.trend_window)
    if not resistance:
        return False
    return sum(1 for c in rows[-cfg.trend_window :] if c.high >= resistance * (1 - cfg.strong_hold_pct)) >= 2


def failed_resistance_retest(candles: Iterable[Candle | Mapping[str, Any]], config: StructureConfig | None = None) -> bool:
    cfg = config or StructureConfig()
    rows = _coerce_candles(candles)
    resistance = _previous_high(rows, cfg.trend_window)
    return bool(resistance and rows and max(c.high for c in rows[-3:]) < resistance * (1 - cfg.tolerance_pct))


def highs_keep_falling(candles: Iterable[Candle | Mapping[str, Any]], config: StructureConfig | None = None) -> bool:
    rows = _coerce_candles(candles)
    if len(rows) < 4:
        return False
    highs = [c.high for c in rows[-4:]]
    return all(left > right for left, right in zip(highs, highs[1:]))


def sideways_below_ma(candles: Iterable[Candle | Mapping[str, Any]], config: StructureConfig | None = None) -> bool:
    cfg = config or StructureConfig()
    rows = _coerce_candles(candles)
    if len(rows) < cfg.short_ma_window:
        return False
    recent = rows[-cfg.short_ma_window :]
    width = max(c.high for c in recent) - min(c.low for c in recent)
    base = recent[-1].close
    return bool(base > 0 and width / base <= cfg.strong_hold_pct * 2 and below_short_ma(rows, cfg))


def overheat_after_large_move(candles: Iterable[Candle | Mapping[str, Any]], config: StructureConfig | None = None) -> bool:
    cfg = config or StructureConfig()
    rows = _coerce_candles(candles)
    if len(rows) < 3:
        return False
    recent = rows[-3:]
    first = recent[0].open
    if first <= 0:
        return False
    move = (recent[-1].close - first) / first
    giant_green = any(c.close > c.open and (c.close - c.open) / c.open >= cfg.giant_green_body_pct for c in recent if c.open > 0)
    return move >= cfg.amplitude_pct or giant_green


def upper_wicks_increasing(candles: Iterable[Candle | Mapping[str, Any]], config: StructureConfig | None = None) -> bool:
    rows = _coerce_candles(candles)
    if len(rows) < 3:
        return False
    ratios = [_upper_wick_ratio(c) for c in rows[-3:]]
    return ratios[0] < ratios[1] < ratios[2]


def broke_entry_structure(position: PositionContext | Mapping[str, Any], candles: Iterable[Candle | Mapping[str, Any]], config: StructureConfig | None = None) -> bool:
    cfg = config or StructureConfig()
    pos = _coerce_position(position)
    rows = _coerce_candles(candles)
    if not rows:
        return False
    reference_low = pos.entry_low if pos.entry_low is not None else pos.entry_price
    return rows[-1].close < reference_low * (1 - cfg.tolerance_pct)


def avg_volume(candles: Iterable[Candle]) -> float:
    rows = list(candles)
    if not rows:
        return 0.0
    return sum(c.volume for c in rows) / len(rows)


def _coerce_candles(candles: Iterable[Candle | Mapping[str, Any]]) -> list[Candle]:
    rows: list[Candle] = []
    for row in candles:
        if isinstance(row, Candle):
            rows.append(row)
        else:
            rows.append(
                Candle(
                    open=float(row.get("open", row.get("close", 0.0))),
                    high=float(row.get("high", row.get("close", 0.0))),
                    low=float(row.get("low", row.get("close", 0.0))),
                    close=float(row.get("close", row.get("price", 0.0))),
                    volume=float(row.get("volume", 0.0)),
                    timestamp=str(row.get("timestamp")) if row.get("timestamp") is not None else None,
                )
            )
    return rows


def _coerce_position(position: PositionContext | Mapping[str, Any]) -> PositionContext:
    if isinstance(position, PositionContext):
        return position
    return PositionContext(
        entry_price=float(position.get("entry_price", 0.0)),
        entry_low=_optional_float(position.get("entry_low")),
        entry_high=_optional_float(position.get("entry_high")),
        peak=_optional_float(position.get("peak")),
    )


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _split_recent(rows: list[Candle], window: int) -> tuple[list[Candle], list[Candle]]:
    if len(rows) < window:
        return [], []
    half = max(1, window // 2)
    recent = rows[-half:]
    prev = rows[-window:-half]
    return prev, recent


def _green_candles(rows: list[Candle]) -> list[Candle]:
    return [c for c in rows if c.close >= c.open]


def _red_candles(rows: list[Candle]) -> list[Candle]:
    return [c for c in rows if c.close < c.open]


def _sma(rows: list[Candle], window: int) -> float | None:
    if len(rows) < window:
        return None
    selected = rows[-window:]
    return sum(c.close for c in selected) / window


def _previous_high(rows: list[Candle], window: int) -> float | None:
    lookback = rows[-(window + 1) : -1]
    if not lookback:
        return None
    return max(c.high for c in lookback)


def _previous_low(rows: list[Candle], window: int) -> float | None:
    lookback = rows[-(window + 1) : -1]
    if not lookback:
        return None
    return min(c.low for c in lookback)


def _levels(rows: list[Candle]) -> dict[str, float | None]:
    cfg = StructureConfig()
    return {
        "previous_low": _previous_low(rows, cfg.trend_window),
        "previous_high": _previous_high(rows, cfg.trend_window),
        "support": _previous_low(rows, cfg.trend_window),
        "resistance": _previous_high(rows, cfg.trend_window),
    }


def _score_reasons(rows: list[Candle], cfg: StructureConfig) -> list[str]:
    checks = [
        ("higher_low", higher_low(rows, cfg)),
        ("strong_low_hold", strong_low_hold(rows, cfg)),
        ("higher_high", higher_high(rows, cfg)),
        ("lower_high", lower_high(rows, cfg)),
        ("broke_previous_low", broke_previous_low(rows, cfg)),
        ("buy_volume_up", buy_volume_increasing(rows, cfg)),
        ("sell_volume_down", sell_volume_decreasing(rows, cfg)),
        ("sell_volume_spike", sell_volume_spike(rows, cfg)),
        ("ma_reclaim", recovered_short_ma(rows, cfg)),
        ("ma_hold", holds_short_ma(rows, cfg)),
        ("below_ma", below_short_ma(rows, cfg)),
        ("resistance_break_hold", resistance_break_and_hold(rows, cfg)),
        ("resistance_touch_hold", resistance_touch_hold(rows, cfg)),
        ("rejection_at_resistance", strong_rejection_at_resistance(rows, cfg)),
    ]
    return [name for name, enabled in checks if enabled]


def _btc_context(btc_state: Any) -> dict[str, Any]:
    if btc_state is None:
        return {}
    if isinstance(btc_state, str):
        return {"state": btc_state}
    if isinstance(btc_state, Mapping):
        return dict(btc_state)
    return {"state": str(btc_state)}


def _upper_wick_ratio(candle: Candle) -> float:
    candle_range = max(candle.high - candle.low, 0.0)
    if candle_range <= 0:
        return 0.0
    return (candle.high - max(candle.open, candle.close)) / candle_range
