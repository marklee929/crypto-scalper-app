from __future__ import annotations

import asyncio
from datetime import UTC, datetime
import json
import time
from typing import Any, Callable, Iterable, Optional

import websockets
from websockets.exceptions import ConnectionClosedOK


WS_URL = "wss://stream.binance.com:9443/ws"


class BinanceWebSocket:
    def __init__(
        self,
        symbol: str,
        streams: Optional[Iterable[str]] = None,
        ping_interval_sec: int = 20,
        no_data_timeout_sec: int = 60,
        status_interval_sec: int = 30,
        max_backoff_sec: int = 60,
    ) -> None:
        self.symbol = normalize_symbol(symbol)
        stream_symbol = self.symbol.lower()
        self.streams = tuple(streams or (f"{stream_symbol}@trade", f"{stream_symbol}@ticker", f"{stream_symbol}@kline_1m"))
        self.ping_interval_sec = int(ping_interval_sec)
        self.no_data_timeout_sec = int(no_data_timeout_sec)
        self.status_interval_sec = int(status_interval_sec)
        self.max_backoff_sec = int(max_backoff_sec)
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._last_message_at: float = 0.0
        self._last_price: float | None = None
        self._message_count = 0
        self._price_event_count = 0

    async def run_forever(
        self,
        on_price: Callable[[float, datetime, float], Any],
        on_message: Optional[Callable[[dict], Any]] = None,
    ) -> None:
        backoff = 1
        while True:
            try:
                print(f"[WS] connecting exchange=binance url={WS_URL} streams={','.join(self.streams)}", flush=True)
                async with websockets.connect(
                    WS_URL,
                    ping_interval=self.ping_interval_sec if self.ping_interval_sec > 0 else None,
                    ping_timeout=10,
                ) as ws:
                    self._ws = ws
                    self._last_message_at = time.time()
                    backoff = 1
                    await self._subscribe_all()
                    print("[WS] connected exchange=binance", flush=True)

                    recv_task = asyncio.create_task(self._recv_loop(on_price, on_message))
                    stale_task = asyncio.create_task(self._no_data_watch())
                    tasks = [recv_task, stale_task]
                    if self.status_interval_sec > 0:
                        tasks.append(asyncio.create_task(self._status_loop()))
                    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)
                    for task in pending:
                        task.cancel()
                    for task in done:
                        task.result()
            except Exception as exc:
                self._ws = None
                print(
                    f"[WS] disconnected exchange=binance error={type(exc).__name__}: {exc} retry_in={backoff}s",
                    flush=True,
                )
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, self.max_backoff_sec)

    async def _subscribe_all(self) -> None:
        if not self._ws:
            return
        payload = {
            "method": "SUBSCRIBE",
            "params": list(self.streams),
            "id": int(time.time()),
        }
        await self._ws.send(json.dumps(payload))
        print(f"[WS] subscribed exchange=binance streams={','.join(self.streams)}", flush=True)

    async def _recv_loop(
        self,
        on_price: Callable[[float, datetime, float], Any],
        on_message: Optional[Callable[[dict], Any]],
    ) -> None:
        if not self._ws:
            return
        while True:
            try:
                raw = await self._ws.recv()
            except ConnectionClosedOK:
                return
            self._last_message_at = time.time()
            self._message_count += 1
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                continue

            if on_message:
                result = on_message(message)
                if asyncio.iscoroutine(result):
                    await result

            parsed = parse_price_message(message, self.symbol)
            if parsed is None:
                continue
            price, timestamp, volume = parsed
            self._last_price = price
            self._price_event_count += 1
            result = on_price(price, timestamp, volume)
            if asyncio.iscoroutine(result):
                await result

    async def _no_data_watch(self) -> None:
        if self.no_data_timeout_sec <= 0:
            return
        while True:
            await asyncio.sleep(1)
            if self._last_message_at and time.time() - self._last_message_at > self.no_data_timeout_sec:
                raise TimeoutError(f"no Binance websocket data for {self.no_data_timeout_sec}s")

    async def _status_loop(self) -> None:
        while True:
            await asyncio.sleep(self.status_interval_sec)
            age = time.time() - self._last_message_at if self._last_message_at else 0.0
            print(
                "[WS_STATUS] "
                f"exchange=binance symbol={self.symbol} connected=True "
                f"messages={self._message_count} price_events={self._price_event_count} "
                f"last_price={_fmt(self._last_price)} last_msg_age={age:.1f}s "
                f"timeout={self.no_data_timeout_sec}s",
                flush=True,
            )


def normalize_symbol(symbol: str) -> str:
    raw = str(symbol or "").strip().upper().replace("/", "").replace("-", "")
    if not raw:
        raise ValueError("Binance symbol is required.")
    return raw


def parse_price_message(message: dict[str, Any], symbol: str) -> Optional[tuple[float, datetime, float]]:
    payload = message.get("data") if isinstance(message.get("data"), dict) else message
    if not isinstance(payload, dict):
        return None
    event_type = str(payload.get("e") or "").lower()
    payload_symbol = str(payload.get("s") or "").upper()
    target_symbol = normalize_symbol(symbol)
    if payload_symbol and payload_symbol != target_symbol:
        return None

    if event_type == "trade":
        price = _to_float(payload.get("p"))
        volume = _to_float(payload.get("q")) or 0.0
        timestamp = _to_datetime(payload.get("T") or payload.get("E"))
    elif event_type == "24hrticker" or "c" in payload:
        price = _to_float(payload.get("c"))
        volume = 0.0
        timestamp = _to_datetime(payload.get("E"))
    elif event_type == "kline":
        kline = payload.get("k") if isinstance(payload.get("k"), dict) else {}
        price = _to_float(kline.get("c"))
        volume = 0.0
        timestamp = _to_datetime(payload.get("E") or kline.get("T"))
    else:
        return None

    if price is None:
        return None
    return price, timestamp or datetime.utcnow(), volume


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
    try:
        ts = float(value)
    except (TypeError, ValueError):
        return None
    if ts > 1_000_000_000_000:
        ts /= 1000.0
    return datetime.fromtimestamp(ts, UTC).replace(tzinfo=None)


def _fmt(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:.12g}"
