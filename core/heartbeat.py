from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional


@dataclass
class HeartbeatSnapshot:
    state: str
    recent_low: Optional[float]
    entry_price: Optional[float]
    peak: Optional[float]
    armed: bool
    cooldown_until: Optional[str]
    cooldown_sec: int


class HeartbeatStrategy:
    def __init__(self, effective_gap: float, trailing_pct: float, cooldown_sec: int) -> None:
        self.effective_gap = effective_gap
        self.trailing_pct = trailing_pct
        self.arm_pct = effective_gap + trailing_pct
        self.cooldown_sec = cooldown_sec

        self.state = "IDLE"
        self.recent_low: Optional[float] = None
        self.entry_price: Optional[float] = None
        self.peak: Optional[float] = None
        self.armed = False
        self.cooldown_until: Optional[datetime] = None

    def on_tick(self, price: float, timestamp: datetime) -> Optional[str]:
        if self.state == "COOLDOWN":
            if self.cooldown_until and timestamp >= self.cooldown_until:
                self.state = "IDLE"
                self.recent_low = price
            else:
                return None

        if self.state == "IDLE":
            if self.recent_low is None or price < self.recent_low:
                self.recent_low = price
            if self.recent_low and price >= self.recent_low * (1 + self.effective_gap):
                self.state = "IN_POSITION"
                self.entry_price = price
                self.peak = price
                self.armed = False
                return "BUY"
            return None

        if self.state == "IN_POSITION":
            if self.peak is None or price > self.peak:
                self.peak = price
            if not self.armed and self.entry_price:
                if price >= self.entry_price * (1 + self.arm_pct):
                    self.armed = True
            if self.armed and self.peak:
                if price <= self.peak * (1 - self.trailing_pct):
                    self.state = "COOLDOWN"
                    self.cooldown_until = timestamp + timedelta(
                        seconds=self.cooldown_sec
                    )
                    return "SELL"
        return None

    def snapshot(self) -> dict:
        return HeartbeatSnapshot(
            state=self.state,
            recent_low=self.recent_low,
            entry_price=self.entry_price,
            peak=self.peak,
            armed=self.armed,
            cooldown_until=self.cooldown_until.isoformat()
            if self.cooldown_until
            else None,
            cooldown_sec=self.cooldown_sec,
        ).__dict__

    def restore(self, data: dict) -> None:
        self.state = data.get("state", self.state)
        self.recent_low = _to_optional_float(data.get("recent_low"))
        self.entry_price = _to_optional_float(data.get("entry_price"))
        self.peak = _to_optional_float(data.get("peak"))
        self.armed = bool(data.get("armed", self.armed))
        self.cooldown_sec = int(data.get("cooldown_sec", self.cooldown_sec))
        self.arm_pct = self.effective_gap + self.trailing_pct
        cooldown_until = data.get("cooldown_until")
        if cooldown_until:
            self.cooldown_until = datetime.fromisoformat(cooldown_until)
        else:
            self.cooldown_until = None


def _to_optional_float(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    return float(value)
