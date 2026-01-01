from __future__ import annotations


class CoinoneWebSocket:
    def __init__(self, symbol: str) -> None:
        self.symbol = symbol

    def connect(self) -> None:
        raise NotImplementedError("Coinone WebSocket integration not implemented yet.")
