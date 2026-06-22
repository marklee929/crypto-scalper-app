from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import unittest

from core.candle_aggregator import CandleAggregator
from core.state import StateStore
from paper.ledger import Ledger
from run import _process_tick
from storage.runtime_repository import (
    build_runtime_run_payload,
    create_runtime_recorder,
    sanitize_config,
    secret_fingerprints,
    split_symbol_assets,
    stable_config_hash,
)


class BuyOnceStrategyStub:
    def __init__(self) -> None:
        self.last_decision = {
            "event": "ENTER",
            "symbol": "ROBOUSDT",
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


class RecordingStub:
    def __init__(self) -> None:
        self.decisions: list[dict] = []
        self.ledger_snapshots: list[dict] = []
        self.demo_execution_flows: list[dict] = []

    def record_strategy_decision(self, decision, timestamp):
        self.decisions.append({"decision": dict(decision), "timestamp": timestamp})
        return 42

    def record_ledger_snapshot(self, ledger, current_price, timestamp, *, decision_id=None):
        self.ledger_snapshots.append(
            {
                "current_price": current_price,
                "timestamp": timestamp,
                "decision_id": decision_id,
                "position_qty": ledger.position_qty,
            }
        )
        return 84

    def record_demo_execution_flow(self, event, ledger, current_price, timestamp, *, decision_id=None):
        self.demo_execution_flows.append(
            {
                "side": event.side,
                "qty": event.qty,
                "current_price": current_price,
                "timestamp": timestamp,
                "decision_id": decision_id,
                "position_qty": ledger.position_qty,
            }
        )
        return {"order_intent_id": 21, "execution_result_id": 22}

    def record_live_asset_snapshot(self, *args, **kwargs):
        raise AssertionError("demo flow must not call live_asset_snapshot")


class RuntimeRepositoryTest(unittest.TestCase):
    def test_sanitize_config_excludes_sensitive_values(self) -> None:
        config = {
            "symbol": "ROBOUSDT",
            "binance_api_key": "real-key",
            "binance_api_secret": "real-secret",
            "nested": {"telegram_token": "real-token", "safe": "ok"},
        }

        sanitized = sanitize_config(config)

        self.assertEqual(sanitized["symbol"], "ROBOUSDT")
        self.assertEqual(sanitized["nested"], {"safe": "ok"})
        self.assertNotIn("binance_api_key", sanitized)
        self.assertNotIn("real-key", str(sanitized))
        self.assertNotIn("real-secret", str(sanitized))
        self.assertNotIn("real-token", str(sanitized))

    def test_secret_fingerprint_does_not_store_raw_secret(self) -> None:
        fingerprints = secret_fingerprints({"binance_api_secret": "real-secret"})

        fingerprint = fingerprints["binance_api_secret"]["fingerprint"]
        self.assertTrue(fingerprints["binance_api_secret"]["present"])
        self.assertIsInstance(fingerprint, str)
        self.assertNotEqual(fingerprint, "real-secret")
        self.assertNotIn("real-secret", str(fingerprints))

    def test_stable_config_hash_is_order_independent(self) -> None:
        left = {"symbol": "ROBOUSDT", "trade_size_cash": 100, "binance_api_secret": "secret"}
        right = {"binance_api_secret": "secret", "trade_size_cash": 100, "symbol": "ROBOUSDT"}

        self.assertEqual(stable_config_hash(left), stable_config_hash(right))

    def test_build_runtime_payload_derives_symbol_context(self) -> None:
        payload = build_runtime_run_payload(
            {
                "exchange": "binance",
                "market": "spot",
                "symbol": "ROBOUSDT",
                "live_order_enabled": True,
            },
            "demo",
        )

        self.assertEqual(payload.mode, "demo")
        self.assertEqual(payload.exchange, "binance")
        self.assertEqual(payload.base_asset, "ROBO")
        self.assertEqual(payload.quote_asset, "USDT")
        self.assertTrue(payload.live_order_enabled)

    def test_create_runtime_recorder_without_database_url_is_disabled(self) -> None:
        recorder = create_runtime_recorder(
            {"symbol": "ROBOUSDT", "postgres_enabled": True},
            "demo",
            env={},
        )

        result = recorder.start()

        self.assertFalse(result.db_enabled)
        self.assertIsNone(result.run_id)
        self.assertEqual(result.disabled_reason, "DATABASE_URL_not_configured")

    def test_split_symbol_assets_handles_known_quote(self) -> None:
        self.assertEqual(split_symbol_assets("robo/usdt"), ("ROBO", "USDT"))

    def test_process_tick_saves_runtime_metadata_backward_compatibly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = {
                "state": str(root / "state.json"),
                "strategy": str(root / "strategy.log"),
                "trades": str(root / "trades.log"),
                "hourly": str(root / "hourly.log"),
            }
            config = {
                "trade_size_cash": 50.0,
                "min_trade_cash": 100.0,
                "fee_rate": 0.0,
                "slippage_rate": 0.0,
                "report_interval_sec": 3600,
                "strategy_log_path": paths["strategy"],
                "trades_log_path": paths["trades"],
                "hourly_report_path": paths["hourly"],
            }
            metadata = {
                "run_id": None,
                "mode": "demo",
                "exchange": "binance",
                "symbol": "ROBOUSDT",
                "strategy_version": "market_structure_v1",
            }
            state_store = StateStore(paths["state"])
            aggregator = CandleAggregator(interval_sec=60)
            start = datetime(2026, 6, 22, 10, 0, 0)

            _process_tick(
                config,
                Ledger(1_000.0),
                BuyOnceStrategyStub(),
                state_store,
                aggregator,
                None,
                100.0,
                start,
                1.0,
                runtime_metadata=metadata,
            )
            _process_tick(
                config,
                Ledger(1_000.0),
                BuyOnceStrategyStub(),
                state_store,
                aggregator,
                None,
                101.0,
                start + timedelta(seconds=60),
                1.0,
                runtime_metadata=metadata,
            )

            saved_state = state_store.load()

        self.assertEqual(saved_state["runtime"]["mode"], "demo")
        self.assertEqual(saved_state["runtime"]["symbol"], "ROBOUSDT")
        self.assertIn("ledger", saved_state)
        self.assertIn("strategy", saved_state)

    def test_process_tick_records_decision_and_ledger_only_on_closed_candle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = {
                "state": str(root / "state.json"),
                "strategy": str(root / "strategy.log"),
                "trades": str(root / "trades.log"),
                "hourly": str(root / "hourly.log"),
            }
            config = {
                "trade_size_cash": 50.0,
                "min_trade_cash": 100.0,
                "fee_rate": 0.0,
                "slippage_rate": 0.0,
                "report_interval_sec": 3600,
                "strategy_log_path": paths["strategy"],
                "trades_log_path": paths["trades"],
                "hourly_report_path": paths["hourly"],
            }
            recorder = RecordingStub()
            state_store = StateStore(paths["state"])
            aggregator = CandleAggregator(interval_sec=60)
            ledger = Ledger(1_000.0)
            strategy = BuyOnceStrategyStub()
            start = datetime(2026, 6, 22, 10, 0, 0)

            _process_tick(
                config,
                ledger,
                strategy,
                state_store,
                aggregator,
                None,
                100.0,
                start,
                1.0,
                db_recorder=recorder,
            )
            self.assertEqual(recorder.decisions, [])
            self.assertEqual(recorder.ledger_snapshots, [])

            _process_tick(
                config,
                ledger,
                strategy,
                state_store,
                aggregator,
                None,
                101.0,
                start + timedelta(seconds=60),
                1.0,
                db_recorder=recorder,
            )

        self.assertEqual(len(recorder.decisions), 1)
        self.assertEqual(len(recorder.ledger_snapshots), 1)
        self.assertEqual(recorder.ledger_snapshots[0]["decision_id"], 42)

    def test_process_tick_records_demo_fake_flow_after_demo_buy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = {
                "state": str(root / "state.json"),
                "strategy": str(root / "strategy.log"),
                "trades": str(root / "trades.log"),
                "hourly": str(root / "hourly.log"),
            }
            config = {
                "trade_size_cash": 100.0,
                "min_trade_cash": 1.0,
                "fee_rate": 0.0,
                "slippage_rate": 0.0,
                "report_interval_sec": 3600,
                "strategy_log_path": paths["strategy"],
                "trades_log_path": paths["trades"],
                "hourly_report_path": paths["hourly"],
            }
            metadata = {"mode": "demo", "run_id": 11, "symbol": "ROBOUSDT"}
            recorder = RecordingStub()
            state_store = StateStore(paths["state"])
            aggregator = CandleAggregator(interval_sec=60)
            ledger = Ledger(1_000.0)
            strategy = BuyOnceStrategyStub()
            start = datetime(2026, 6, 22, 10, 0, 0)

            _process_tick(
                config,
                ledger,
                strategy,
                state_store,
                aggregator,
                None,
                100.0,
                start,
                1.0,
                runtime_metadata=metadata,
                db_recorder=recorder,
            )
            _process_tick(
                config,
                ledger,
                strategy,
                state_store,
                aggregator,
                None,
                100.0,
                start + timedelta(seconds=60),
                1.0,
                runtime_metadata=metadata,
                db_recorder=recorder,
            )

        self.assertEqual(len(recorder.demo_execution_flows), 1)
        self.assertEqual(recorder.demo_execution_flows[0]["side"], "BUY")
        self.assertEqual(recorder.demo_execution_flows[0]["decision_id"], 42)
        self.assertGreater(recorder.demo_execution_flows[0]["position_qty"], 0.0)


if __name__ == "__main__":
    unittest.main()
