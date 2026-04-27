from __future__ import annotations

from datetime import datetime, timedelta
import unittest

from core.candle_aggregator import CandleAggregator


class CandleAggregatorTest(unittest.TestCase):
    def test_first_tick_creates_current_without_closed(self) -> None:
        aggregator = CandleAggregator(interval_sec=60)
        update = aggregator.update(100.0, datetime(2026, 4, 28, 10, 0, 1), 2.0)

        self.assertIsNone(update.closed)
        self.assertEqual(update.current.open, 100.0)
        self.assertEqual(update.current.high, 100.0)
        self.assertEqual(update.current.low, 100.0)
        self.assertEqual(update.current.close, 100.0)
        self.assertEqual(update.current.volume, 2.0)

    def test_same_interval_updates_ohlcv(self) -> None:
        aggregator = CandleAggregator(interval_sec=60)
        ts = datetime(2026, 4, 28, 10, 0, 1)
        aggregator.update(100.0, ts, 2.0)
        update = aggregator.update(103.0, ts + timedelta(seconds=10), 3.0)
        update = aggregator.update(99.0, ts + timedelta(seconds=20), 4.0)

        self.assertIsNone(update.closed)
        self.assertEqual(update.current.open, 100.0)
        self.assertEqual(update.current.high, 103.0)
        self.assertEqual(update.current.low, 99.0)
        self.assertEqual(update.current.close, 99.0)
        self.assertEqual(update.current.volume, 9.0)

    def test_new_interval_returns_closed_previous_candle(self) -> None:
        aggregator = CandleAggregator(interval_sec=60)
        first = datetime(2026, 4, 28, 10, 0, 1)
        aggregator.update(100.0, first, 2.0)
        update = aggregator.update(101.0, first + timedelta(seconds=60), 1.5)

        self.assertIsNotNone(update.closed)
        self.assertEqual(update.closed.close, 100.0)
        self.assertEqual(update.current.open, 101.0)
        self.assertEqual(update.current.volume, 1.5)

    def test_invalid_price_raises(self) -> None:
        aggregator = CandleAggregator(interval_sec=60)
        with self.assertRaises(ValueError):
            aggregator.update(0.0, datetime(2026, 4, 28, 10, 0, 1))

    def test_invalid_interval_raises(self) -> None:
        with self.assertRaises(ValueError):
            CandleAggregator(interval_sec=0)


if __name__ == "__main__":
    unittest.main()
