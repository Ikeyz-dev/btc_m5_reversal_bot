"""
Phase 4 — Indicator Module.

Calculates Stochastic, ADX, and ATR and stores them in the DataFrame.
"""

from __future__ import annotations

import pandas as pd
from ta.trend import ADXIndicator
from ta.volatility import AverageTrueRange

from .config import IndicatorConfig


def calculate_indicators(
    df: pd.DataFrame, cfg: IndicatorConfig = None
) -> pd.DataFrame:
    """
    Calculate Stochastic (%K, %D), ADX, and ATR, appending them to df.

    The Stochastic is computed MT4-style (K period, Slowing, D period):
    raw %K -> smoothed by `slowing` -> %D is an SMA of the smoothed %K.
    This matches how "K=14, D=3, Slowing=3" is normally specified on
    trading platforms like Exness/MT4, rather than the simple %K/%D
    pair some libraries default to.

    Args:
        df: DataFrame with columns ['high', 'low', 'close'].
        cfg: IndicatorConfig with periods. Uses defaults (14/3/3, 14, 14)
            if not provided.

    Returns:
        A copy of df with columns: ['Stoch_K', 'Stoch_D', 'ADX', 'ATR'].
    """
    cfg = cfg or IndicatorConfig()
    out = df.copy()

    lowest_low = out["low"].rolling(window=cfg.stoch_k).min()
    highest_high = out["high"].rolling(window=cfg.stoch_k).max()
    raw_k = 100 * (out["close"] - lowest_low) / (highest_high - lowest_low)

    out["Stoch_K"] = raw_k.rolling(window=cfg.stoch_slowing).mean()
    out["Stoch_D"] = out["Stoch_K"].rolling(window=cfg.stoch_d).mean()

    adx = ADXIndicator(
        high=out["high"], low=out["low"], close=out["close"], window=cfg.adx_period
    )
    out["ADX"] = adx.adx()

    atr = AverageTrueRange(
        high=out["high"], low=out["low"], close=out["close"], window=cfg.atr_period
    )
    out["ATR"] = atr.average_true_range()

    return out
