from __future__ import annotations

from datetime import datetime
import unittest

from exchanges.binance.rest import format_quantity, normalize_symbol
from exchanges.binance.ws import parse_price_message


class BinanceExchangeTest(unittest.TestCase):
    def test_trade_event_maps_price_volume_timestamp(self) -> None:
        parsed = parse_price_message(
            {
                "e": "trade",
                "s": "ROBOUSDT",
                "p": "0.02010",
                "q": "100",
                "T": 1234567890000,
            },
            "ROBOUSDT",
        )

        self.assertIsNotNone(parsed)
        price, timestamp, volume = parsed
        self.assertEqual(price, 0.02010)
        self.assertEqual(volume, 100.0)
        self.assertIsInstance(timestamp, datetime)

    def test_ticker_event_maps_close_price(self) -> None:
        parsed = parse_price_message(
            {
                "e": "24hrTicker",
                "s": "ROBOUSDT",
                "c": "0.021",
                "v": "2500",
                "E": 1234567890000,
            },
            "ROBOUSDT",
        )

        self.assertIsNotNone(parsed)
        price, _, volume = parsed
        self.assertEqual(price, 0.021)
        self.assertEqual(volume, 0.0)

    def test_kline_event_maps_close_price(self) -> None:
        parsed = parse_price_message(
            {
                "e": "kline",
                "s": "ROBOUSDT",
                "E": 1234567890000,
                "k": {"c": "0.022", "v": "3000"},
            },
            "ROBOUSDT",
        )

        self.assertIsNotNone(parsed)
        price, _, volume = parsed
        self.assertEqual(price, 0.022)
        self.assertEqual(volume, 0.0)

    def test_symbol_mismatch_is_ignored(self) -> None:
        self.assertIsNone(parse_price_message({"e": "trade", "s": "BTCUSDT", "p": "1", "q": "1"}, "ROBOUSDT"))

    def test_normalize_symbol_compacts_binance_pair(self) -> None:
        self.assertEqual(normalize_symbol("robo/usdt"), "ROBOUSDT")
        self.assertEqual(normalize_symbol("robo-usdt"), "ROBOUSDT")

    def test_format_quantity_strips_trailing_zeroes(self) -> None:
        self.assertEqual(format_quantity(1.230000), "1.23")


if __name__ == "__main__":
    unittest.main()
