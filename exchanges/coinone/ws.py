from __future__ import annotations

import asyncio
from datetime import datetime
import json
import time
from typing import Any, Callable, Iterable, Optional

import websockets

WS_URL = "wss://stream.coinone.co.kr"
PING_PAYLOAD = {"request_type": "PING"}


class CoinoneWebSocket:
    def __init__(
        self,
        symbol: str,
        quote_currency: str = "KRW",
        channels: Optional[Iterable[str]] = None,
        ping_interval_sec: int = 30,
        force_reconnect_sec: int = 6 * 60 * 60,
        max_backoff_sec: int = 60,
    ) -> None:
        target, quote = _normalize_symbol(symbol, quote_currency)
        self.symbol = target
        self.quote_currency = quote
        self.channels = tuple(channels or ("TICKER", "TRADE"))
        self.ping_interval_sec = int(ping_interval_sec)
        self.force_reconnect_sec = int(force_reconnect_sec)
        self.max_backoff_sec = int(max_backoff_sec)
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._connected_at: float = 0.0

    async def run_forever(
        self,
        on_price: Callable[[float, datetime, float], Any],
        on_message: Optional[Callable[[dict], Any]] = None,
    ) -> None:
        backoff = 1
        while True:
            try:
                async with websockets.connect(WS_URL, ping_interval=None) as ws:
                    self._ws = ws
                    self._connected_at = time.time()
                    backoff = 1
                    await self._subscribe_all()

                    recv_task = asyncio.create_task(self._recv_loop(on_price, on_message))
                    tasks = [recv_task]
                    if self.ping_interval_sec > 0:
                        tasks.append(asyncio.create_task(self._ping_loop()))
                    if self.force_reconnect_sec > 0:
                        tasks.append(asyncio.create_task(self._force_reconnect_watch()))

                    done, pending = await asyncio.wait(
                        tasks,
                        return_when=asyncio.FIRST_EXCEPTION,
                    )
                    for task in pending:
                        task.cancel()
                    for task in done:
                        task.result()
            except Exception:
                self._ws = None
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, self.max_backoff_sec)

    async def _subscribe_all(self) -> None:
        if not self._ws:
            return
        for channel in self.channels:
            payload = {
                "request_type": "SUBSCRIBE",
                "channel": channel,
                "topic": {
                    "quote_currency": self.quote_currency,
                    "target_currency": self.symbol,
                },
                "format": "DEFAULT",
            }
            await self._ws.send(json.dumps(payload))

    async def _ping_loop(self) -> None:
        if self.ping_interval_sec <= 0:
            return
        while True:
            await asyncio.sleep(self.ping_interval_sec)
            if not self._ws:
                continue
            await self._ws.send(json.dumps(PING_PAYLOAD))

    async def _recv_loop(
        self,
        on_price: Callable[[float, datetime, float], Any],
        on_message: Optional[Callable[[dict], Any]],
    ) -> None:
        if not self._ws:
            return
        while True:
            raw = await self._ws.recv()
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                continue

            if on_message:
                result = on_message(message)
                if asyncio.iscoroutine(result):
                    await result

            parsed = _parse_price_message(message, self.symbol, self.quote_currency)
            if parsed is None:
                continue
            price, timestamp, volume = parsed
            result = on_price(price, timestamp, volume)
            if asyncio.iscoroutine(result):
                await result

    async def _force_reconnect_watch(self) -> None:
        if self.force_reconnect_sec <= 0:
            return
        while True:
            await asyncio.sleep(1)
            if not self._connected_at:
                continue
            if time.time() - self._connected_at >= self.force_reconnect_sec:
                raise ConnectionError("forced reconnect")


def _normalize_symbol(symbol: str, quote_currency: str) -> tuple[str, str]:
    raw = symbol.upper()
    quote = quote_currency.upper()
    if "-" in raw:
        left, right = raw.split("-", 1)
        if left and right:
            return right, left
    if "/" in raw:
        left, right = raw.split("/", 1)
        if left and right:
            return left, right
    return raw, quote


def _parse_price_message(
    message: dict, target_symbol: str, quote_currency: str
) -> Optional[tuple[float, datetime, float]]:
    payload = message.get("data") or message.get("payload") or message
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                parsed = _parse_price_message(item, target_symbol, quote_currency)
                if parsed:
                    return parsed
        return None
    if not isinstance(payload, dict):
        return None

    if not _matches_symbol(payload, target_symbol, quote_currency):
        return None

    price = _extract_price(payload)
    if price is None:
        return None
    timestamp = _extract_timestamp(payload) or _extract_timestamp(message) or datetime.utcnow()
    volume = _extract_volume(payload)
    return price, timestamp, volume


def _matches_symbol(payload: dict, target_symbol: str, quote_currency: str) -> bool:
    symbol = payload.get("symbol") or payload.get("target_currency") or payload.get("target")
    quote = payload.get("quote_currency") or payload.get("quote")
    if symbol and str(symbol).upper() != target_symbol.upper():
        return False
    if quote and str(quote).upper() != quote_currency.upper():
        return False
    return True


def _extract_price(payload: dict) -> Optional[float]:
    for key in ("price", "last", "last_price", "trade_price", "close", "close_price"):
        if key in payload:
            return _to_float(payload.get(key))
    return None


def _extract_volume(payload: dict) -> float:
    for key in (
        "volume",
        "qty",
        "quantity",
        "amount",
        "trade_volume",
        "trade_qty",
        "target_volume",
    ):
        if key in payload:
            value = _to_float(payload.get(key))
            if value is not None:
                return value
    return 0.0


def _extract_timestamp(payload: dict) -> Optional[datetime]:
    for key in ("timestamp", "trade_timestamp", "time", "created_at"):
        if key in payload:
            return _to_datetime(payload.get(key))
    return None


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_datetime(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        ts = float(value)
        if ts > 1_000_000_000_000:
            ts = ts / 1000.0
        return datetime.utcfromtimestamp(ts)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            ts = float(stripped)
            if ts > 1_000_000_000_000:
                ts = ts / 1000.0
            return datetime.utcfromtimestamp(ts)
        try:
            return datetime.fromisoformat(stripped)
        except ValueError:
            return None
    return None
