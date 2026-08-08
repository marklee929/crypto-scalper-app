from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class TradeEvent:
    side: str
    price: float
    qty: float
    exec_price: float
    fee: float
    slippage: float
    timestamp: str
    cash: float
    position_qty: float
    avg_price: float
    realized_pnl: float


class Ledger:
    def __init__(self, initial_cash: float) -> None:
        self.initial_cash = float(initial_cash)
        self.cash = float(initial_cash)
        self.position_qty = 0.0
        self.avg_price = 0.0
        self.realized_pnl = 0.0
        self.fees_paid = 0.0
        self.slippage_paid = 0.0
        self.trades: List[TradeEvent] = []

    def buy(
        self,
        price: float,
        qty: float,
        fee_rate: float,
        slippage_rate: float,
        timestamp: Optional[str] = None,
    ) -> TradeEvent:
        self._validate_qty(qty)
        exec_price = price * (1 + slippage_rate)
        fee = exec_price * qty * fee_rate
        cost = exec_price * qty + fee
        if cost > self.cash:
            raise ValueError("Insufficient cash for buy.")

        new_qty = self.position_qty + qty
        if new_qty <= 0:
            raise ValueError("Position quantity must be positive after buy.")
        self.avg_price = (
            (self.avg_price * self.position_qty) + (exec_price * qty)
        ) / new_qty
        self.position_qty = new_qty
        self.cash -= cost
        self.fees_paid += fee
        self.slippage_paid += (exec_price - price) * qty

        event = self._record_trade(
            side="BUY",
            price=price,
            qty=qty,
            exec_price=exec_price,
            fee=fee,
            slippage=exec_price - price,
            timestamp=timestamp,
        )
        return event

    def sell(
        self,
        price: float,
        qty: float,
        fee_rate: float,
        slippage_rate: float,
        timestamp: Optional[str] = None,
    ) -> TradeEvent:
        self._validate_qty(qty)
        if qty > self.position_qty:
            raise ValueError("Sell quantity exceeds position.")

        exec_price = price * (1 - slippage_rate)
        fee = exec_price * qty * fee_rate
        proceeds = exec_price * qty - fee
        pnl = (exec_price - self.avg_price) * qty - fee

        self.position_qty -= qty
        if self.position_qty == 0:
            self.avg_price = 0.0
        self.cash += proceeds
        self.realized_pnl += pnl
        self.fees_paid += fee
        self.slippage_paid += (price - exec_price) * qty

        event = self._record_trade(
            side="SELL",
            price=price,
            qty=qty,
            exec_price=exec_price,
            fee=fee,
            slippage=price - exec_price,
            timestamp=timestamp,
        )
        return event

    def equity(self, current_price: float) -> float:
        return self.cash + self.position_qty * current_price

    def unrealized_pnl(self, current_price: float) -> float:
        if self.position_qty == 0:
            return 0.0
        return (current_price - self.avg_price) * self.position_qty

    def summary(self, current_price: float) -> dict:
        equity = self.equity(current_price)
        return {
            "cash": self.cash,
            "position_qty": self.position_qty,
            "avg_price": self.avg_price,
            "realized_pnl": self.realized_pnl,
            "unrealized_pnl": self.unrealized_pnl(current_price),
            "fees_paid": self.fees_paid,
            "slippage_paid": self.slippage_paid,
            "equity": equity,
            "net_pnl": equity - self.initial_cash,
        }

    def snapshot(self) -> dict:
        return {
            "initial_cash": self.initial_cash,
            "cash": self.cash,
            "position_qty": self.position_qty,
            "avg_price": self.avg_price,
            "realized_pnl": self.realized_pnl,
            "fees_paid": self.fees_paid,
            "slippage_paid": self.slippage_paid,
        }

    def restore(self, snapshot: dict) -> None:
        self.initial_cash = float(snapshot.get("initial_cash", self.initial_cash))
        self.cash = float(snapshot.get("cash", self.cash))
        self.position_qty = float(snapshot.get("position_qty", self.position_qty))
        self.avg_price = float(snapshot.get("avg_price", self.avg_price))
        self.realized_pnl = float(snapshot.get("realized_pnl", self.realized_pnl))
        self.fees_paid = float(snapshot.get("fees_paid", self.fees_paid))
        self.slippage_paid = float(snapshot.get("slippage_paid", self.slippage_paid))

    def _record_trade(
        self,
        side: str,
        price: float,
        qty: float,
        exec_price: float,
        fee: float,
        slippage: float,
        timestamp: Optional[str],
    ) -> TradeEvent:
        event = TradeEvent(
            side=side,
            price=price,
            qty=qty,
            exec_price=exec_price,
            fee=fee,
            slippage=slippage,
            timestamp=timestamp or datetime.utcnow().isoformat(),
            cash=self.cash,
            position_qty=self.position_qty,
            avg_price=self.avg_price,
            realized_pnl=self.realized_pnl,
        )
        self.trades.append(event)
        return event

    @staticmethod
    def _validate_qty(qty: float) -> None:
        if qty <= 0:
            raise ValueError("Quantity must be positive.")
