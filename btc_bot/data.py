"""
Phase 2 — Data Module.

Downloads OHLCV candles from an exchange (Binance by default) via ccxt.
"""

from __future__ import annotations

import time
from typing import Optional

import pandas as pd

try:
    import ccxt
except ImportError:  # pragma: no cover
    ccxt = None

from .config import DataConfig


def download_data(
    symbol: str = "BTC/USDT",
    timeframe: str = "5m",
    limit: int = 5000,
    exchange_id: str = "binance",
    since: Optional[int] = None,
) -> pd.DataFrame:
    """
    Download historical OHLCV candles and return them as a DataFrame.

    Handles pagination so more than the exchange's single-request limit
    (Binance caps at 1000 candles per call) can be downloaded in one go.

    Args:
        symbol: Trading pair, e.g. "BTC/USDT".
        timeframe: Candle timeframe, e.g. "5m".
        limit: Total number of candles to fetch.
        exchange_id: ccxt exchange id (default "binance").
        since: Optional starting timestamp in ms. If None, fetches the
            most recent `limit` candles.

    Returns:
        DataFrame indexed by UTC timestamp with columns:
        ['open', 'high', 'low', 'close', 'volume'].
    """
    if ccxt is None:
        raise ImportError("ccxt is required: pip install ccxt")

    exchange_class = getattr(ccxt, exchange_id)
    exchange = exchange_class({"enableRateLimit": True})

    all_candles = []
    per_request = 1000  # Binance's max per call
    remaining = limit

    fetch_since = since
    if fetch_since is None and limit > per_request:
        # Walk backwards: estimate a start time far enough back to cover `limit` candles.
        tf_minutes = _timeframe_to_minutes(timeframe)
        ms_back = tf_minutes * 60 * 1000 * limit
        fetch_since = exchange.milliseconds() - ms_back

    while remaining > 0:
        batch_limit = min(per_request, remaining)
        batch = exchange.fetch_ohlcv(
            symbol, timeframe=timeframe, since=fetch_since, limit=batch_limit
        )
        if not batch:
            break

        all_candles.extend(batch)
        remaining -= len(batch)

        last_ts = batch[-1][0]
        tf_ms = _timeframe_to_minutes(timeframe) * 60 * 1000
        next_since = last_ts + tf_ms

        if fetch_since is not None and next_since <= fetch_since:
            break
        fetch_since = next_since

        if len(batch) < batch_limit:
            break  # exchange ran out of history

        time.sleep(exchange.rateLimit / 1000)

    df = pd.DataFrame(
        all_candles, columns=["timestamp", "open", "high", "low", "close", "volume"]
    )
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    df = df.drop_duplicates(subset="timestamp").sort_values("timestamp")
    df = df.set_index("timestamp")

    if limit and len(df) > limit:
        df = df.iloc[-limit:]

    return df.reset_index()


def _timeframe_to_minutes(timeframe: str) -> int:
    """Convert a ccxt-style timeframe string (e.g. '5m', '1h') to minutes."""
    unit = timeframe[-1]
    value = int(timeframe[:-1])
    if unit == "m":
        return value
    if unit == "h":
        return value * 60
    if unit == "d":
        return value * 60 * 24
    raise ValueError(f"Unsupported timeframe: {timeframe}")


def download_data_from_config(cfg: DataConfig) -> pd.DataFrame:
    """Convenience wrapper that reads parameters from a DataConfig."""
    return download_data(
        symbol=cfg.symbol,
        timeframe=cfg.timeframe,
        limit=cfg.candles_to_fetch,
        exchange_id=cfg.exchange_id,
    )
