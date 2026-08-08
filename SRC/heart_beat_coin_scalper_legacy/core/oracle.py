from __future__ import annotations


class Oracle:
    def __init__(self) -> None:
        self._signal = "ENTER"

    def update(self, price: float) -> None:
        _ = price

    def signal(self) -> str:
        return self._signal
