from __future__ import annotations

import unittest

from core.market_structure import (
    Candle,
    MarketState,
    PositionContext,
    SidewaysState,
    StructureConfig,
    can_enter,
    classify_market,
    classify_sideways,
    should_exit,
)


CFG = StructureConfig(min_candles=6, short_ma_window=3, trend_window=6, tolerance_pct=0.001)


def c(open_: float, high: float, low: float, close: float, volume: float) -> Candle:
    return Candle(open=open_, high=high, low=low, close=close, volume=volume)


class MarketStructureTest(unittest.TestCase):
    def test_falling_sideways_blocks_entry(self) -> None:
        candles = [
            c(0.0245, 0.0250, 0.0230, 0.0234, 200),
            c(0.0234, 0.0238, 0.0220, 0.0225, 180),
            c(0.0225, 0.0232, 0.0220, 0.0224, 80),
            c(0.0224, 0.0230, 0.0220, 0.0223, 75),
            c(0.0223, 0.0228, 0.0220, 0.0222, 70),
            c(0.0222, 0.0226, 0.0220, 0.0221, 65),
            c(0.0221, 0.0224, 0.0220, 0.0221, 60),
        ]

        self.assertEqual(classify_sideways(candles, CFG), SidewaysState.FALLING_SIDEWAYS)
        self.assertFalse(can_enter(candles, config=CFG).allowed)

    def test_accumulation_sideways_is_watch_state(self) -> None:
        candles = [
            c(0.0240, 0.0242, 0.0218, 0.0221, 220),
            c(0.0221, 0.0227, 0.0219, 0.0224, 120),
            c(0.0224, 0.0229, 0.0220, 0.0226, 100),
            c(0.0226, 0.0232, 0.0222, 0.0229, 90),
            c(0.0229, 0.0235, 0.0224, 0.0232, 130),
            c(0.0232, 0.0237, 0.0226, 0.0234, 170),
            c(0.0234, 0.0239, 0.0228, 0.0236, 210),
        ]

        decision = classify_market(candles, config=CFG)

        self.assertEqual(decision.sideways_state, SidewaysState.ACCUMULATION_SIDEWAYS)
        self.assertIn(decision.state, {MarketState.ACCUMULATION, MarketState.HEARTBEAT})

    def test_heartbeat_allows_entry(self) -> None:
        candles = [
            c(0.0220, 0.0224, 0.0218, 0.0222, 90),
            c(0.0222, 0.0228, 0.0220, 0.0226, 95),
            c(0.0226, 0.0230, 0.0223, 0.0228, 110),
            c(0.0228, 0.0234, 0.0225, 0.0231, 125),
            c(0.0231, 0.0238, 0.0228, 0.0235, 160),
            c(0.0235, 0.0242, 0.0232, 0.0240, 210),
            c(0.0240, 0.0248, 0.0237, 0.0246, 260),
        ]

        entry = can_enter(candles, config=CFG)

        self.assertIn(entry.state, {MarketState.HEARTBEAT, MarketState.STRONG_HEARTBEAT})
        self.assertTrue(entry.allowed)

    def test_structure_break_exits_immediately(self) -> None:
        candles = [
            c(0.0230, 0.0235, 0.0228, 0.0233, 100),
            c(0.0233, 0.0238, 0.0230, 0.0236, 120),
            c(0.0236, 0.0240, 0.0232, 0.0238, 140),
            c(0.0238, 0.0241, 0.0234, 0.0239, 130),
            c(0.0239, 0.0240, 0.0225, 0.0226, 260),
            c(0.0226, 0.0228, 0.0219, 0.0220, 320),
        ]

        exit_decision = should_exit(
            PositionContext(entry_price=0.0235, entry_low=0.0228),
            candles,
            config=CFG,
        )

        self.assertTrue(exit_decision.should_exit)
        self.assertIn("entry_structure_break", exit_decision.reasons)

    def test_overheated_resistance_area_does_not_enter_and_prepares_take_profit(self) -> None:
        candles = [
            c(0.0200, 0.0210, 0.0198, 0.0208, 100),
            c(0.0208, 0.0225, 0.0207, 0.0223, 260),
            c(0.0223, 0.0248, 0.0222, 0.0244, 360),
            c(0.0244, 0.0252, 0.0238, 0.0246, 300),
            c(0.0246, 0.0254, 0.0240, 0.0247, 220),
            c(0.0247, 0.0255, 0.0241, 0.0246, 180),
        ]

        self.assertFalse(can_enter(candles, config=CFG).allowed)
        exit_decision = should_exit(
            PositionContext(entry_price=0.0225, entry_low=0.0207),
            candles,
            config=CFG,
        )
        self.assertTrue(exit_decision.should_exit)
        self.assertTrue(exit_decision.take_profit)


if __name__ == "__main__":
    unittest.main()
