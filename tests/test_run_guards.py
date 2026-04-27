from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from core.candle_aggregator import CandleAggregator
from core.state import StateStore
from paper.ledger import Ledger
from run import _process_tick, parse_args


class BuyStrategyStub:
    def __init__(self) -> None:
        self.last_decision = {
            "event": "ENTER",
            "symbol": "TST",
            "state": "HEARTBEAT",
            "sideways_state": "NONE",
            "score": {"total": 7, "structure": 2, "volume": 2, "ma": 1, "support_resistance": 2},
            "reason": "test_buy",
            "current_price": 100.0,
            "previous_low": 99.0,
            "previous_high": 101.0,
            "support": 99.0,
            "resistance": 101.0,
        }

    def on_candle(self, candle) -> str:
        self.last_decision["current_price"] = candle.close
        return "BUY"

    def snapshot(self) -> dict:
        return {"state": "IDLE"}


class RunGuardTest(unittest.TestCase):
    def test_trade_size_below_min_trade_cash_skips_buy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = _paths(tmp)
            ledger = Ledger(1_000.0)
            strategy = BuyStrategyStub()
            aggregator = CandleAggregator(interval_sec=60)
            config = _config(paths, trade_size_cash=50.0, min_trade_cash=100.0)
            start = datetime(2026, 4, 28, 10, 0, 0)

            _process_tick(config, ledger, strategy, StateStore(paths["state"]), aggregator, None, 100.0, start, 1.0)
            _process_tick(config, ledger, strategy, StateStore(paths["state"]), aggregator, None, 101.0, start + timedelta(seconds=60), 1.0)

            self.assertEqual(ledger.position_qty, 0.0)
            self.assertEqual(strategy.last_decision["event"], "BUY_SKIPPED")
            self.assertIn("below_min_trade_cash", strategy.last_decision["reason"])

    def test_cash_below_min_trade_cash_skips_buy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = _paths(tmp)
            ledger = Ledger(80.0)
            strategy = BuyStrategyStub()
            aggregator = CandleAggregator(interval_sec=60)
            config = _config(paths, trade_size_cash=1_000.0, min_trade_cash=100.0)
            start = datetime(2026, 4, 28, 10, 0, 0)

            _process_tick(config, ledger, strategy, StateStore(paths["state"]), aggregator, None, 100.0, start, 1.0)
            _process_tick(config, ledger, strategy, StateStore(paths["state"]), aggregator, None, 101.0, start + timedelta(seconds=60), 1.0)

            self.assertEqual(ledger.position_qty, 0.0)
            self.assertEqual(strategy.last_decision["event"], "BUY_SKIPPED")

    def test_min_trade_cash_cli_aliases_parse(self) -> None:
        with patch.object(sys, "argv", ["run.py", "--mode", "demo", "--min", "123"]):
            self.assertEqual(parse_args().min_trade_cash, 123.0)
        with patch.object(sys, "argv", ["run.py", "--mode", "demo", "--min-trade-cash", "456"]):
            self.assertEqual(parse_args().min_trade_cash, 456.0)


def _paths(tmp: str) -> dict[str, str]:
    root = Path(tmp)
    return {
        "state": str(root / "state.json"),
        "strategy": str(root / "strategy.log"),
        "trades": str(root / "trades.log"),
        "hourly": str(root / "hourly.log"),
    }


def _config(paths: dict[str, str], *, trade_size_cash: float, min_trade_cash: float) -> dict:
    return {
        "trade_size_cash": trade_size_cash,
        "min_trade_cash": min_trade_cash,
        "fee_rate": 0.0,
        "slippage_rate": 0.0,
        "report_interval_sec": 3600,
        "strategy_log_path": paths["strategy"],
        "trades_log_path": paths["trades"],
        "hourly_report_path": paths["hourly"],
    }


if __name__ == "__main__":
    unittest.main()
