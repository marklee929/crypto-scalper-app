from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from paper.ledger import Ledger, TradeEvent


def write_trade(event: TradeEvent, log_path: str | Path) -> None:
    line = format_trade(event)
    _append_line(log_path, line)


def write_hourly_report(
    ledger: Ledger,
    current_price: float,
    log_path: str | Path,
    timestamp: Optional[str] = None,
) -> None:
    ts = timestamp or datetime.utcnow().isoformat()
    summary = ledger.summary(current_price)
    line = (
        f"{ts} | price={current_price:.2f} | qty={summary['position_qty']:.6f} "
        f"| avg={summary['avg_price']:.2f} | unrealized={summary['unrealized_pnl']:.2f} "
        f"| realized={summary['realized_pnl']:.2f} | fees={summary['fees_paid']:.2f} "
        f"| slippage={summary['slippage_paid']:.2f} | net={summary['net_pnl']:.2f} "
        f"| equity={summary['equity']:.2f}"
    )
    _append_line(log_path, line)


def format_trade(event: TradeEvent) -> str:
    return (
        f"{event.timestamp} | {event.side} | price={event.price:.2f} "
        f"| exec={event.exec_price:.2f} | qty={event.qty:.6f} | fee={event.fee:.2f} "
        f"| slippage={event.slippage:.4f} | cash={event.cash:.2f} "
        f"| pos={event.position_qty:.6f} | avg={event.avg_price:.2f} "
        f"| realized={event.realized_pnl:.2f}"
    )


def _append_line(path: str | Path, line: str) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
