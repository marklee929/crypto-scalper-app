from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timedelta
import random

from core.config import load_config
from core.heartbeat import HeartbeatStrategy
from core.state import StateStore
from paper.ledger import Ledger
from paper.report import write_hourly_report, write_trade


def demo_price_stream(config: dict, ticks: int):
    rng = random.Random(config["demo_seed"])
    price = float(config["demo_price_start"])
    interval = int(config["demo_interval_sec"])
    now = datetime.utcnow()
    for _ in range(ticks):
        yield now, price
        shock = rng.uniform(-config["demo_price_volatility"], config["demo_price_volatility"])
        price = max(0.01, price * (1 + shock))
        now = now + timedelta(seconds=interval)


def _build_runtime(config: dict) -> tuple[Ledger, HeartbeatStrategy, StateStore, datetime | None]:
    ledger = Ledger(config["initial_cash"])
    strategy = HeartbeatStrategy(
        effective_gap=config["effective_gap"],
        trailing_pct=config["trailing_pct"],
        cooldown_sec=config["cooldown_sec"],
    )

    state_store = StateStore(config["state_path"])
    saved_state = state_store.load()
    if saved_state.get("ledger"):
        ledger.restore(saved_state["ledger"])
    if saved_state.get("strategy"):
        strategy.restore(saved_state["strategy"])

    last_report_at = None
    if saved_state.get("last_report_at"):
        last_report_at = datetime.fromisoformat(saved_state["last_report_at"])

    return ledger, strategy, state_store, last_report_at


def _process_tick(
    config: dict,
    ledger: Ledger,
    strategy: HeartbeatStrategy,
    state_store: StateStore,
    last_report_at: datetime | None,
    price: float,
    timestamp: datetime,
) -> datetime | None:
    action = strategy.on_tick(price, timestamp)
    if action == "BUY":
        qty = config["trade_size_cash"] / price
        try:
            event = ledger.buy(
                price=price,
                qty=qty,
                fee_rate=config["fee_rate"],
                slippage_rate=config["slippage_rate"],
                timestamp=timestamp.isoformat(),
            )
            write_trade(event, config["trades_log_path"])
        except ValueError:
            pass
    elif action == "SELL" and ledger.position_qty > 0:
        try:
            event = ledger.sell(
                price=price,
                qty=ledger.position_qty,
                fee_rate=config["fee_rate"],
                slippage_rate=config["slippage_rate"],
                timestamp=timestamp.isoformat(),
            )
            write_trade(event, config["trades_log_path"])
        except ValueError:
            pass

    if last_report_at is None or (
        timestamp - last_report_at
    ).total_seconds() >= config["report_interval_sec"]:
        write_hourly_report(
            ledger, price, config["hourly_report_path"], timestamp.isoformat()
        )
        last_report_at = timestamp

    state_store.save(
        {
            "ledger": ledger.snapshot(),
            "strategy": strategy.snapshot(),
            "last_report_at": last_report_at.isoformat() if last_report_at else None,
        }
    )
    return last_report_at


def run_demo(config: dict, ticks: int) -> None:
    ledger, strategy, state_store, last_report_at = _build_runtime(config)

    for timestamp, price in demo_price_stream(config, ticks):
        last_report_at = _process_tick(
            config, ledger, strategy, state_store, last_report_at, price, timestamp
        )


async def run_live(config: dict) -> None:
    ledger, strategy, state_store, last_report_at = _build_runtime(config)

    from exchanges.coinone.ws import CoinoneWebSocket

    ws = CoinoneWebSocket(
        symbol=config["symbol"],
        quote_currency=config.get("quote_currency", "KRW"),
        ping_interval_sec=int(config.get("ws_ping_interval_sec", 30)),
        force_reconnect_sec=int(config.get("ws_force_reconnect_sec", 6 * 60 * 60)),
        max_backoff_sec=int(config.get("ws_max_backoff_sec", 60)),
    )

    async def handle_price(price: float, timestamp: datetime) -> None:
        nonlocal last_report_at
        last_report_at = _process_tick(
            config, ledger, strategy, state_store, last_report_at, price, timestamp
        )

    await ws.run_forever(handle_price)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Heart Beat Coin Scalper (demo).")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--mode", choices=["demo", "live"], default="demo")
    parser.add_argument("--ticks", type=int, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    if args.mode == "live":
        asyncio.run(run_live(config))
    else:
        ticks = args.ticks if args.ticks is not None else int(config["demo_ticks"])
        run_demo(config, ticks)


if __name__ == "__main__":
    main()
