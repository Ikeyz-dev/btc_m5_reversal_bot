"""
Phase 5 — Swing Detection Module.

Swing High at i: High[i] > High[i-1], High[i-2], High[i-3]
Swing Low  at i: Low[i]  < Low[i-1],  Low[i-2],  Low[i-3]
"""

from __future__ import annotations

from typing import Optional

import pandas as pd

from .config import SwingConfig


def detect_swings(df: pd.DataFrame, cfg: SwingConfig = None) -> pd.DataFrame:
    """
    Mark SwingHigh and SwingLow boolean columns on df.

    Args:
        df: DataFrame with columns ['high', 'low'].
        cfg: SwingConfig controlling the lookback window (default 3).

    Returns:
        A copy of df with boolean columns 'SwingHigh' and 'SwingLow'.
    """
    cfg = cfg or SwingConfig()
    n = cfg.lookback
    out = df.copy()

    high = out["high"]
    low = out["low"]

    swing_high = pd.Series(True, index=out.index)
    swing_low = pd.Series(True, index=out.index)
    for k in range(1, n + 1):
        swing_high &= high > high.shift(k)
        swing_low &= low < low.shift(k)

    # Not enough history in the first `n` rows to evaluate.
    swing_high.iloc[:n] = False
    swing_low.iloc[:n] = False

    out["SwingHigh"] = swing_high.fillna(False)
    out["SwingLow"] = swing_low.fillna(False)

    return out


def last_swing_high(df: pd.DataFrame, before_index: int) -> Optional[float]:
    """
    Return the most recent confirmed swing high price at or before
    `before_index`. Returns None if no swing high exists yet.
    """
    subset = df.loc[:before_index]
    highs = subset[subset["SwingHigh"]]
    if highs.empty:
        return None
    return float(highs["high"].iloc[-1])


def last_swing_low(df: pd.DataFrame, before_index: int) -> Optional[float]:
    """
    Return the most recent confirmed swing low price at or before
    `before_index`. Returns None if no swing low exists yet.
    """
    subset = df.loc[:before_index]
    lows = subset[subset["SwingLow"]]
    if lows.empty:
        return None
    return float(lows["low"].iloc[-1])
