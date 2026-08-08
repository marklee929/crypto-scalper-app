from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from core.market_structure import Candle


@dataclass
class CandleUpdate:
    closed: Optional[Candle]
    current: Candle


class CandleAggregator:
    def __init__(self, interval_sec: int = 60) -> None:
        if interval_sec <= 0:
            raise ValueError("interval_sec must be positive.")
        self.interval_sec = int(interval_sec)
        self._bucket_start: datetime | None = None
        self._current: Candle | None = None

    def update(
        self,
        price: float,
        timestamp: datetime,
        volume: float = 0.0,
    ) -> CandleUpdate:
        price = float(price)
        if price <= 0:
            raise ValueError("price must be positive.")
        bucket_start = self._bucket_start_for(timestamp)
        if self._current is None or self._bucket_start != bucket_start:
            closed = self._current
            self._bucket_start = bucket_start
            self._current = Candle(
                open=price,
                high=price,
                low=price,
                close=price,
                volume=float(volume),
                timestamp=bucket_start.isoformat(),
            )
            return CandleUpdate(closed=closed, current=self._current)

        current = self._current
        self._current = Candle(
            open=current.open,
            high=max(current.high, price),
            low=min(current.low, price),
            close=price,
            volume=current.volume + float(volume),
            timestamp=current.timestamp,
        )
        return CandleUpdate(closed=None, current=self._current)

    def _bucket_start_for(self, timestamp: datetime) -> datetime:
        seconds = int(timestamp.timestamp())
        bucket_seconds = seconds - (seconds % self.interval_sec)
        return datetime.fromtimestamp(bucket_seconds, tz=timestamp.tzinfo)
