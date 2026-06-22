from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from paper.ledger import Ledger


@dataclass
class DemoFakeAssetLatestTracker:
    latest: dict[tuple[int, str], dict[str, Any]] = field(default_factory=dict)

    def apply(self, snapshots: list[dict[str, Any]]) -> list[dict[str, Any]]:
        applied: list[dict[str, Any]] = []
        for snapshot in snapshots:
            key = (int(snapshot["fake_account_id"]), str(snapshot["asset"]))
            previous = self.latest.get(key)
            if previous is not None:
                previous["is_latest"] = False
            current = dict(snapshot)
            current["is_latest"] = True
            self.latest[key] = current
            applied.append(current)
        return applied


def build_demo_fake_asset_snapshots(
    ledger: Ledger,
    *,
    fake_account_id: int,
    run_id: Optional[int],
    captured_at: datetime,
    base_asset: str,
    quote_asset: str,
    symbol: str,
    current_price: float,
) -> list[dict[str, Any]]:
    cash_snapshot = {
        "fake_account_id": fake_account_id,
        "run_id": run_id,
        "captured_at": captured_at,
        "asset": quote_asset,
        "free_amount": ledger.cash,
        "locked_amount": 0.0,
        "total_amount": ledger.cash,
        "valuation_symbol": quote_asset,
        "valuation_price": 1.0,
        "valuation_quote": ledger.cash,
        "is_latest": True,
    }
    position_value = ledger.position_qty * float(current_price)
    position_snapshot = {
        "fake_account_id": fake_account_id,
        "run_id": run_id,
        "captured_at": captured_at,
        "asset": base_asset,
        "free_amount": ledger.position_qty,
        "locked_amount": 0.0,
        "total_amount": ledger.position_qty,
        "valuation_symbol": symbol,
        "valuation_price": float(current_price),
        "valuation_quote": position_value,
        "is_latest": True,
    }
    return [cash_snapshot, position_snapshot]

