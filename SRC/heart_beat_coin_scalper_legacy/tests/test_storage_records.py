from __future__ import annotations

from datetime import datetime
import unittest

from core.market_structure import Candle
from paper.ledger import Ledger
from storage.records import (
    build_ledger_snapshot_record,
    build_market_candle_record,
    build_strategy_decision_record,
)


class StorageRecordsTest(unittest.TestCase):
    def test_strategy_decision_payload_maps_scores_and_reasons(self) -> None:
        record = build_strategy_decision_record(
            {
                "event": "ENTER",
                "symbol": "ROBOUSDT",
                "state": "HEARTBEAT",
                "sideways_state": "NONE",
                "score": {
                    "total": 7,
                    "structure": 2,
                    "volume": 2,
                    "ma": 1,
                    "support_resistance": 2,
                },
                "reason": "higher_high,ma_reclaim",
                "confirmations": ["higher_high", "ma_reclaim"],
                "current_price": 0.02,
                "previous_low": 0.019,
                "previous_high": 0.021,
                "support": 0.019,
                "resistance": 0.021,
            },
            run_id=1,
            decided_at=datetime(2026, 6, 22, 10, 0, 0),
            mode="demo",
            exchange="binance",
            symbol="ROBOUSDT",
        )

        self.assertEqual(record["event"], "ENTER")
        self.assertEqual(record["market_state"], "HEARTBEAT")
        self.assertEqual(record["score_total"], 7)
        self.assertEqual(record["reasons"], ["higher_high", "ma_reclaim"])
        self.assertEqual(record["confirmations"], ["higher_high", "ma_reclaim"])

    def test_ledger_snapshot_payload_uses_ledger_summary(self) -> None:
        ledger = Ledger(1_000.0)
        ledger.buy(price=10.0, qty=10.0, fee_rate=0.0, slippage_rate=0.0)

        record = build_ledger_snapshot_record(
            ledger,
            current_price=11.0,
            run_id=1,
            captured_at=datetime(2026, 6, 22, 10, 1, 0),
            mode="demo",
            decision_id=2,
        )

        self.assertEqual(record["run_id"], 1)
        self.assertEqual(record["decision_id"], 2)
        self.assertEqual(record["cash"], 900.0)
        self.assertEqual(record["position_qty"], 10.0)
        self.assertEqual(record["equity"], 1_010.0)

    def test_market_candle_payload_accepts_storage_timeframes_only(self) -> None:
        candle = Candle(
            open=1.0,
            high=1.2,
            low=0.9,
            close=1.1,
            volume=100.0,
            timestamp="2026-06-22T10:00:00",
        )

        record = build_market_candle_record(
            candle,
            exchange="binance",
            symbol="ROBOUSDT",
            timeframe="15m",
            source="unit_test",
        )

        self.assertEqual(record["timeframe"], "15m")
        self.assertEqual(record["volume_base"], 100.0)
        with self.assertRaises(ValueError):
            build_market_candle_record(
                candle,
                exchange="binance",
                symbol="ROBOUSDT",
                timeframe="1m",
                source="unit_test",
            )


if __name__ == "__main__":
    unittest.main()

