from __future__ import annotations


class MultiTimeframeGuard:
    def __init__(self) -> None:
        self._blocked = False

    def update(self, price: float) -> None:
        _ = price

    def allow_entry(self) -> bool:
        return not self._blocked
