"""
Phase 3 — Heikin Ashi Module.
"""

from __future__ import annotations

import pandas as pd


def calculate_heikin_ashi(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute Heikin Ashi candles from standard OHLC data.

    Adds columns: HA_Open, HA_High, HA_Low, HA_Close, Bullish, Bearish.

    Args:
        df: DataFrame with columns ['open', 'high', 'low', 'close'].

    Returns:
        A copy of df with Heikin Ashi columns appended.
    """
    required = {"open", "high", "low", "close"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"df is missing required columns: {missing}")

    out = df.copy()

    ha_close = (out["open"] + out["high"] + out["low"] + out["close"]) / 4.0

    ha_open = pd.Series(index=out.index, dtype="float64")
    ha_open.iloc[0] = (out["open"].iloc[0] + out["close"].iloc[0]) / 2.0
    for i in range(1, len(out)):
        ha_open.iloc[i] = (ha_open.iloc[i - 1] + ha_close.iloc[i - 1]) / 2.0

    ha_high = pd.concat([out["high"], ha_open, ha_close], axis=1).max(axis=1)
    ha_low = pd.concat([out["low"], ha_open, ha_close], axis=1).min(axis=1)

    out["HA_Open"] = ha_open
    out["HA_High"] = ha_high
    out["HA_Low"] = ha_low
    out["HA_Close"] = ha_close
    out["Bullish"] = out["HA_Close"] > out["HA_Open"]
    out["Bearish"] = out["HA_Close"] < out["HA_Open"]

    return out
