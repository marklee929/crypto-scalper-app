from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


BINANCE_REST_URL = "https://api.binance.com"


class BinanceRestClient:
    def __init__(
        self,
        api_key: str = "",
        api_secret: str = "",
        *,
        base_url: str = BINANCE_REST_URL,
        recv_window: int = 5000,
    ) -> None:
        self.api_key = str(api_key or "").strip()
        self.api_secret = str(api_secret or "").strip()
        self.base_url = str(base_url or BINANCE_REST_URL).rstrip("/")
        self.recv_window = int(recv_window or 5000)

    @property
    def enabled(self) -> bool:
        return bool(self.api_key and self.api_secret)

    def place_market_order(self, symbol: str, side: str, quantity: float) -> dict[str, Any]:
        if not self.enabled:
            raise ValueError("Binance API key and secret are required for live orders.")
        if quantity <= 0:
            raise ValueError("Binance market order quantity must be positive.")
        params = {
            "symbol": normalize_symbol(symbol),
            "side": str(side or "").upper(),
            "type": "MARKET",
            "quantity": format_quantity(quantity),
            "recvWindow": self.recv_window,
            "timestamp": int(time.time() * 1000),
        }
        return self._signed_request("POST", "/api/v3/order", params)

    def _signed_request(self, method: str, path: str, params: dict[str, Any]) -> dict[str, Any]:
        query = urlencode(params)
        signature = hmac.new(self.api_secret.encode("utf-8"), query.encode("utf-8"), hashlib.sha256).hexdigest()
        signed_query = f"{query}&signature={signature}"
        method_upper = method.upper()
        body = None if method_upper == "GET" else signed_query.encode("utf-8")
        url = f"{self.base_url}{path}"
        if method_upper == "GET":
            url = f"{url}?{signed_query}"
        request = Request(
            url,
            data=body,
            headers={
                "X-MBX-APIKEY": self.api_key,
                "Content-Type": "application/x-www-form-urlencoded",
            },
            method=method_upper,
        )
        with urlopen(request, timeout=10) as response:
            payload = response.read().decode("utf-8")
        return json.loads(payload) if payload else {}


def normalize_symbol(symbol: str) -> str:
    raw = str(symbol or "").strip().upper().replace("/", "").replace("-", "")
    if not raw:
        raise ValueError("Binance symbol is required.")
    return raw


def format_quantity(quantity: float) -> str:
    text = f"{float(quantity):.12f}".rstrip("0").rstrip(".")
    return text or "0"
