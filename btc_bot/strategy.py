"""
Phase 6 — Strategy Module.

Signal indexing convention (matches the spec's [0]/[1]/[2] notation):
    [0] = current/most recently closed candle (row i)
    [1] = one candle back (row i-1)
    [2] = two candles back (row i-2)

Entry for any confirmed signal is the OPEN of the NEXT candle (i+1),
which the caller is responsible for using — these functions only
confirm whether a signal fired at row i.
"""

from __future__ import annotations

import pandas as pd

from .config import StrategyConfig

REQUIRED_COLUMNS = {"Stoch_K", "ADX", "Bullish", "Bearish"}


def _validate(df: pd.DataFrame) -> None:
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(
            f"df is missing required columns for strategy signals: {missing}"
        )


def buy_signal(df: pd.DataFrame, i: int, cfg: StrategyConfig = None) -> bool:
    """
    Evaluate the BUY rule at row index i (positional index, not label).

    Conditions (all must hold):
        Stochastic: K[1] < oversold AND K[0] > K[1]
        ADX: ADX[2] < ADX[1] AND ADX[0] < ADX[1] AND ADX[1] > threshold
        Heikin Ashi: HA[1] bullish AND HA[0] bullish

    Returns False (instead of raising) if there isn't enough history
    at row i to evaluate all three lookback periods.
    """
    _validate(df)
    cfg = cfg or StrategyConfig()
    if i < 2:
        return False

    k0, k1 = df["Stoch_K"].iloc[i], df["Stoch_K"].iloc[i - 1]
    adx0, adx1, adx2 = df["ADX"].iloc[i], df["ADX"].iloc[i - 1], df["ADX"].iloc[i - 2]
    ha1_bull, ha0_bull = df["Bullish"].iloc[i - 1], df["Bullish"].iloc[i]

    if pd.isna([k0, k1, adx0, adx1, adx2]).any():
        return False

    stoch_ok = (k1 < cfg.stoch_oversold) and (k0 > k1)
    adx_ok = (adx2 < adx1) and (adx0 < adx1) and (cfg.adx_threshold < adx1 <= cfg.adx_threshold_max)
    ha_ok = bool(ha1_bull) and bool(ha0_bull)

    return bool(stoch_ok and adx_ok and ha_ok)


def sell_signal(df: pd.DataFrame, i: int, cfg: StrategyConfig = None) -> bool:
    """
    Evaluate the SELL rule at row index i (positional index, not label).

    Conditions (all must hold):
        Stochastic: K[1] > overbought AND K[0] < K[1]
        ADX: ADX[2] < ADX[1] AND ADX[0] < ADX[1] AND ADX[1] > threshold
        Heikin Ashi: HA[1] bearish AND HA[0] bearish

    Returns False (instead of raising) if there isn't enough history
    at row i to evaluate all three lookback periods.
    """
    _validate(df)
    cfg = cfg or StrategyConfig()
    if i < 2:
        return False

    k0, k1 = df["Stoch_K"].iloc[i], df["Stoch_K"].iloc[i - 1]
    adx0, adx1, adx2 = df["ADX"].iloc[i], df["ADX"].iloc[i - 1], df["ADX"].iloc[i - 2]
    ha1_bear, ha0_bear = df["Bearish"].iloc[i - 1], df["Bearish"].iloc[i]

    if pd.isna([k0, k1, adx0, adx1, adx2]).any():
        return False

    stoch_ok = (k1 > cfg.stoch_overbought) and (k0 < k1)
    adx_ok = (adx2 < adx1) and (adx0 < adx1) and (cfg.adx_threshold < adx1 <= cfg.adx_threshold_max)
    ha_ok = bool(ha1_bear) and bool(ha0_bear)

    return bool(stoch_ok and adx_ok and ha_ok)
