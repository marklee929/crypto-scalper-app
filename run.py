from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime, timedelta
import os
from pathlib import Path
import random
import time
from typing import Any

from core.candle_aggregator import CandleAggregator
from core.config import load_config
from core.heartbeat import HeartbeatStrategy, format_strategy_log
from core.market_structure import StructureConfig
from core.state import StateStore
from paper.ledger import Ledger
from paper.report import write_hourly_report, write_trade


def demo_price_stream(config: dict, ticks: int | None = None, *, realtime: bool = False):
    rng = random.Random(config["demo_seed"])
    price = float(config["demo_price_start"])
    interval = int(config["demo_interval_sec"])
    now = datetime.now(UTC).replace(tzinfo=None)
    emitted = 0
    while ticks is None or emitted < ticks:
        yield now, price, 1.0
        shock = rng.uniform(-config["demo_price_volatility"], config["demo_price_volatility"])
        price = max(0.01, price * (1 + shock))
        now = now + timedelta(seconds=interval)
        emitted += 1
        if realtime:
            time.sleep(max(0, interval))


def _build_runtime(
    config: dict,
) -> tuple[Ledger, HeartbeatStrategy, StateStore, CandleAggregator, datetime | None]:
    ledger = Ledger(config["initial_cash"])
    strategy = HeartbeatStrategy(
        effective_gap=config["effective_gap"],
        trailing_pct=config["trailing_pct"],
        cooldown_sec=config["cooldown_sec"],
        symbol=str(config.get("symbol", "")),
        structure_config=_build_structure_config(config),
    )
    aggregator = CandleAggregator(interval_sec=int(config.get("candle_interval_sec", 60)))

    state_store = StateStore(config["state_path"])
    saved_state = state_store.load()
    if saved_state.get("ledger"):
        ledger.restore(saved_state["ledger"])
    if saved_state.get("strategy"):
        strategy.restore(saved_state["strategy"])

    last_report_at = None
    if saved_state.get("last_report_at"):
        last_report_at = datetime.fromisoformat(saved_state["last_report_at"])

    return ledger, strategy, state_store, aggregator, last_report_at


def _process_tick(
    config: dict,
    ledger: Ledger,
    strategy: HeartbeatStrategy,
    state_store: StateStore,
    aggregator: CandleAggregator,
    last_report_at: datetime | None,
    price: float,
    timestamp: datetime,
    volume: float = 0.0,
    order_client: Any = None,
) -> datetime | None:
    update = aggregator.update(price, timestamp, volume)
    action = None
    decision_evaluated = update.closed is not None
    if update.closed is not None:
        action = strategy.on_candle(update.closed)
    if decision_evaluated:
        _write_strategy_log(strategy.last_decision, config["strategy_log_path"], timestamp)
    if action == "BUY":
        trade_cash = min(float(config["trade_size_cash"]), float(ledger.cash))
        min_trade_cash = float(config.get("min_trade_cash", 0.0))
        if trade_cash < min_trade_cash:
            strategy.last_decision = {
                **strategy.last_decision,
                "event": "BUY_SKIPPED",
                "reason": (
                    f"below_min_trade_cash trade_cash={trade_cash:.2f} "
                    f"min_trade_cash={min_trade_cash:.2f}"
                ),
                "trade_cash": trade_cash,
                "min_trade_cash": min_trade_cash,
            }
            _write_strategy_log(strategy.last_decision, config["strategy_log_path"], timestamp)
        else:
            qty = trade_cash / price
            try:
                _place_live_order_if_enabled(config, order_client, "BUY", qty)
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
            _place_live_order_if_enabled(config, order_client, "SELL", ledger.position_qty)
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


def _place_live_order_if_enabled(config: dict, order_client: Any, side: str, qty: float) -> None:
    if not bool(config.get("live_order_enabled", False)):
        return
    if order_client is None:
        raise RuntimeError("live_order_enabled requires a configured BinanceRestClient.")
    order_client.place_market_order(str(config["symbol"]), side, qty)


def _build_structure_config(config: dict) -> StructureConfig:
    return StructureConfig(
        min_candles=int(config["structure_min_candles"]),
        short_ma_window=int(config["structure_short_ma_window"]),
        trend_window=int(config["structure_trend_window"]),
        tolerance_pct=float(config["structure_tolerance_pct"]),
        min_avg_volume=float(config["structure_min_avg_volume"]),
        max_spread_pct=float(config["structure_max_spread_pct"]),
        amplitude_pct=float(config["structure_amplitude_pct"]),
    )


def _write_strategy_log(event: dict, log_path: str, timestamp: datetime) -> None:
    if not event:
        return
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(format_strategy_log(event, timestamp.isoformat()) + "\n")


def run_demo(config: dict, ticks: int, *, continuous: bool = False) -> None:
    ledger, strategy, state_store, aggregator, last_report_at = _build_runtime(config)
    closed_candles = 0
    trade_count_before = len(ledger.trades)

    print(
        f"[RUN] mode=demo symbol={config.get('symbol')} ticks={ticks} "
        f"continuous={continuous} "
        f"candle_interval_sec={config.get('candle_interval_sec')} "
        f"min_trade_cash={config.get('min_trade_cash')}"
    )

    processed_ticks = 0
    try:
        stream_ticks = None if continuous else ticks
        for timestamp, price, volume in demo_price_stream(config, stream_ticks, realtime=continuous):
            before_decision = dict(strategy.last_decision)
            last_report_at = _process_tick(
                config, ledger, strategy, state_store, aggregator, last_report_at, price, timestamp, volume
            )
            processed_ticks += 1
            if strategy.last_decision and strategy.last_decision != before_decision:
                closed_candles += 1
            if continuous and ticks > 0 and processed_ticks % ticks == 0:
                _print_run_summary(
                    "STATUS",
                    config,
                    ledger,
                    strategy,
                    processed_ticks,
                    closed_candles,
                    trade_count_before,
                )
    except KeyboardInterrupt:
        _print_run_summary(
            "STOP",
            config,
            ledger,
            strategy,
            processed_ticks,
            closed_candles,
            trade_count_before,
        )
        return

    _print_run_summary(
        "DONE",
        config,
        ledger,
        strategy,
        processed_ticks,
        closed_candles,
        trade_count_before,
    )


def _print_run_summary(
    label: str,
    config: dict,
    ledger: Ledger,
    strategy: HeartbeatStrategy,
    processed_ticks: int,
    closed_candles: int,
    trade_count_before: int,
) -> None:
    summary = ledger.summary(float(strategy.last_decision.get("current_price") or config["demo_price_start"]))
    print(
        f"[{label}] mode=demo processed_ticks={processed_ticks} closed_candles={closed_candles} "
        f"new_trades={len(ledger.trades) - trade_count_before} "
        f"state={strategy.state} last_event={strategy.last_decision.get('event', '')} "
        f"last_market={strategy.last_decision.get('state', '')} equity={summary['equity']:.2f}"
    )
    print(
        f"[LOG] strategy={config['strategy_log_path']} trades={config['trades_log_path']} "
        f"state_file={config['state_path']}"
    )


async def run_live(config: dict) -> None:
    _validate_live_config(config)
    ledger, strategy, state_store, aggregator, last_report_at = _build_runtime(config)

    from exchanges.binance.rest import BinanceRestClient
    from exchanges.binance.ws import BinanceWebSocket

    order_client = BinanceRestClient(
        api_key=str(config.get("binance_api_key") or os.getenv("BINANCE_API_KEY", "")),
        api_secret=str(config.get("binance_api_secret") or os.getenv("BINANCE_API_SECRET", "")),
        base_url=str(config.get("binance_rest_url") or "https://api.binance.com"),
    )
    ws = BinanceWebSocket(
        symbol=config["symbol"],
        ping_interval_sec=int(config.get("ws_ping_interval_sec", 30)),
        no_data_timeout_sec=int(config.get("ws_no_data_timeout_sec", 5)),
        status_interval_sec=int(config.get("ws_status_interval_sec", 30)),
        max_backoff_sec=int(config.get("ws_max_backoff_sec", 60)),
    )

    async def handle_price(price: float, timestamp: datetime, volume: float = 0.0) -> None:
        nonlocal last_report_at
        before_decision = dict(strategy.last_decision)
        last_report_at = _process_tick(
            config, ledger, strategy, state_store, aggregator, last_report_at, price, timestamp, volume, order_client
        )
        if strategy.last_decision and strategy.last_decision != before_decision:
            _print_live_decision(strategy, ledger, price, timestamp)

    _log_runtime_config(config, "live")
    print(f"[RUN] mode=live symbol={config.get('symbol')}")
    await ws.run_forever(handle_price)


def _validate_live_config(config: dict) -> None:
    exchange = str(config.get("exchange", "binance")).strip().lower()
    if exchange != "binance":
        raise ValueError("live mode now supports Binance only. Set exchange=binance.")
    symbol = str(config.get("symbol", "")).strip().upper()
    if not symbol:
        raise ValueError("live mode requires explicit symbol in config.")
    if symbol == "BTC":
        raise ValueError(
            "live mode is using fallback/default symbol BTC. "
            "Use an explicit Binance symbol such as ROBOUSDT."
        )
    if "/" in symbol or "-" in symbol:
        raise ValueError("Binance live mode requires compact symbols such as ROBOUSDT.")
    if bool(config.get("live_order_enabled", False)):
        api_key = str(config.get("binance_api_key") or os.getenv("BINANCE_API_KEY", "")).strip()
        api_secret = str(config.get("binance_api_secret") or os.getenv("BINANCE_API_SECRET", "")).strip()
        if not api_key or not api_secret:
            raise ValueError("live_order_enabled requires BINANCE_API_KEY and BINANCE_API_SECRET.")


def _log_runtime_config(config: dict, mode: str) -> None:
    print(
        "[RUNTIME_CONFIG] "
        f"mode={mode} "
        f"exchange={config.get('exchange')} "
        f"symbol={config.get('symbol')} "
        f"market={config.get('market')} "
        f"trade_size={config.get('trade_size_cash')} "
        f"min_trade={config.get('min_trade_cash')} "
        f"candle={config.get('candle_interval_sec')}s "
        f"ws_status={config.get('ws_status_interval_sec')}s "
        f"live_order_enabled={config.get('live_order_enabled')} "
        f"state_path={config.get('state_path')} "
        f"strategy_log={config.get('strategy_log_path')}"
    )


def _print_live_decision(strategy: HeartbeatStrategy, ledger: Ledger, price: float, timestamp: datetime) -> None:
    decision = strategy.last_decision or {}
    score = decision.get("score") or {}
    summary = ledger.summary(price)
    print(
        "[LIVE_DECISION] "
        f"ts={timestamp.isoformat()} symbol={decision.get('symbol', '')} "
        f"event={decision.get('event', '')} market={decision.get('state', '')} "
        f"score={score.get('total', 0)} reason={decision.get('reason', '')} "
        f"price={price:.12g} cash={summary['cash']:.2f} "
        f"position={summary['position_qty']:.12g} equity={summary['equity']:.2f}",
        flush=True,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Heart Beat Coin Scalper.")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--mode", choices=["demo", "live"], default="live")
    parser.add_argument("--ticks", type=int, default=None)
    parser.add_argument(
        "--continuous",
        action="store_true",
        help="Keep demo running continuously. Without this, demo exits after --ticks.",
    )
    parser.add_argument(
        "--min-trade-cash",
        "--min",
        dest="min_trade_cash",
        type=float,
        default=None,
        help="Override minimum trade cash for this run.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    if args.min_trade_cash is not None:
        config["min_trade_cash"] = args.min_trade_cash
    if args.mode == "demo":
        ticks = args.ticks if args.ticks is not None else int(config["demo_ticks"])
        _log_runtime_config(config, "demo")
        run_demo(config, ticks, continuous=bool(args.continuous))
    else:
        asyncio.run(run_live(config))


if __name__ == "__main__":
    main()
