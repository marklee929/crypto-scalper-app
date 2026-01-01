from __future__ import annotations


class CoinoneRestClient:
    def __init__(self, api_key: str = "", api_secret: str = "") -> None:
        self.api_key = api_key
        self.api_secret = api_secret

    def get_ticker(self, symbol: str) -> dict:
        raise NotImplementedError("Coinone REST integration not implemented yet.")

    def place_order(self, symbol: str, side: str, qty: float, price: float) -> dict:
        raise NotImplementedError("Coinone REST integration not implemented yet.")
