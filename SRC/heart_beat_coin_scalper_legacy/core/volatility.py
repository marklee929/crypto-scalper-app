from __future__ import annotations

from collections import deque
from typing import Deque, Optional


class VolatilityFilter:
    def __init__(self, window: int, vol_ok: float) -> None:
        self.window = window
        self.vol_ok = vol_ok
        self._prices: Deque[float] = deque(maxlen=window)

    def update(self, price: float) -> None:
        self._prices.append(price)

    def allowed(self) -> bool:
        vol = self._volatility()
        if vol is None:
            return True
        return vol <= self.vol_ok

    def _volatility(self) -> Optional[float]:
        if len(self._prices) < 2:
            return None
        first = self._prices[0]
        last = self._prices[-1]
        if first <= 0:
            return None
        return abs(last - first) / first
