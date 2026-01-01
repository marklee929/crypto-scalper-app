from __future__ import annotations

from pathlib import Path
from typing import Any, Dict


DEFAULT_CONFIG: Dict[str, Any] = {
    "symbol": "BTC",
    "initial_cash": 1_000_000.0,
    "fee_rate": 0.0005,
    "slippage_rate": 0.0002,
    "effective_gap": 0.01,
    "trailing_pct": 0.01,
    "cooldown_sec": 300,
    "trade_size_cash": 100_000.0,
    "report_interval_sec": 3600,
    "state_path": "state.json",
    "trades_log_path": "trades.log",
    "hourly_report_path": "hourly_report.log",
    "demo_price_start": 50_000.0,
    "demo_price_volatility": 0.003,
    "demo_interval_sec": 5,
    "demo_seed": 42,
    "demo_ticks": 720,
}


def load_config(path: str | Path) -> Dict[str, Any]:
    config_path = Path(path)
    if not config_path.exists():
        return DEFAULT_CONFIG.copy()

    text = config_path.read_text(encoding="utf-8")
    data: Dict[str, Any]
    try:
        import yaml  # type: ignore
    except Exception:
        data = _parse_simple_yaml(text)
    else:
        loaded = yaml.safe_load(text)
        data = loaded if isinstance(loaded, dict) else {}

    merged = DEFAULT_CONFIG.copy()
    merged.update(data)
    return merged


def _parse_simple_yaml(text: str) -> Dict[str, Any]:
    data: Dict[str, Any] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in stripped:
            continue
        key, raw_value = stripped.split(":", 1)
        value = raw_value.split("#", 1)[0].strip()
        if not key.strip():
            continue
        data[key.strip()] = _coerce_scalar(value)
    return data


def _coerce_scalar(value: str) -> Any:
    if value == "":
        return ""
    lower = value.lower()
    if lower in {"true", "false"}:
        return lower == "true"
    if lower in {"null", "none"}:
        return None
    if value.startswith(("'", '"')) and value.endswith(("'", '"')) and len(value) >= 2:
        return value[1:-1]
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value
