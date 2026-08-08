from __future__ import annotations

from datetime import datetime
import unittest

from paper.ledger import Ledger
from storage.fake_assets import DemoFakeAssetLatestTracker, build_demo_fake_asset_snapshots


class FakeAssetTest(unittest.TestCase):
    def test_fake_buy_decreases_cash_and_increases_asset(self) -> None:
        ledger = Ledger(1_000.0)
        ledger.buy(price=10.0, qty=10.0, fee_rate=0.0, slippage_rate=0.0, timestamp="2026-06-22T10:00:00")

        snapshots = build_demo_fake_asset_snapshots(
            ledger,
            fake_account_id=7,
            run_id=11,
            captured_at=datetime(2026, 6, 22, 10, 0, 0),
            base_asset="ROBO",
            quote_asset="USDT",
            symbol="ROBOUSDT",
            current_price=11.0,
        )

        by_asset = {snapshot["asset"]: snapshot for snapshot in snapshots}
        self.assertEqual(by_asset["USDT"]["total_amount"], 900.0)
        self.assertEqual(by_asset["ROBO"]["total_amount"], 10.0)
        self.assertEqual(by_asset["ROBO"]["valuation_quote"], 110.0)

    def test_fake_sell_increases_cash_and_decreases_asset(self) -> None:
        ledger = Ledger(1_000.0)
        ledger.buy(price=10.0, qty=10.0, fee_rate=0.0, slippage_rate=0.0, timestamp="2026-06-22T10:00:00")
        ledger.sell(price=12.0, qty=4.0, fee_rate=0.0, slippage_rate=0.0, timestamp="2026-06-22T10:01:00")

        snapshots = build_demo_fake_asset_snapshots(
            ledger,
            fake_account_id=7,
            run_id=11,
            captured_at=datetime(2026, 6, 22, 10, 1, 0),
            base_asset="ROBO",
            quote_asset="USDT",
            symbol="ROBOUSDT",
            current_price=12.0,
        )

        by_asset = {snapshot["asset"]: snapshot for snapshot in snapshots}
        self.assertEqual(by_asset["USDT"]["total_amount"], 948.0)
        self.assertEqual(by_asset["ROBO"]["total_amount"], 6.0)
        self.assertEqual(by_asset["ROBO"]["valuation_quote"], 72.0)

    def test_latest_tracker_keeps_one_latest_snapshot_per_fake_account_asset(self) -> None:
        tracker = DemoFakeAssetLatestTracker()
        first = tracker.apply(
            [
                {
                    "fake_account_id": 7,
                    "asset": "USDT",
                    "total_amount": 1_000.0,
                    "is_latest": True,
                }
            ]
        )[0]
        second = tracker.apply(
            [
                {
                    "fake_account_id": 7,
                    "asset": "USDT",
                    "total_amount": 900.0,
                    "is_latest": True,
                }
            ]
        )[0]

        self.assertFalse(first["is_latest"])
        self.assertTrue(second["is_latest"])
        self.assertEqual(tracker.latest[(7, "USDT")], second)


if __name__ == "__main__":
    unittest.main()
