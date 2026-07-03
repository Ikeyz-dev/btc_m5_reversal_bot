"""
Pipeline helper — runs Phases 1-10 end to end (download -> HA ->
indicators -> swings -> backtest -> stats) in one call.
"""

from __future__ import annotations

import pandas as pd

from .backtest import backtest
from .config import BotConfig, DEFAULT_CONFIG
from .data import download_data_from_config
from .heikin_ashi import calculate_heikin_ashi
from .indicators import calculate_indicators
from .swings import detect_swings


def prepare_data(cfg: BotConfig = None) -> pd.DataFrame:
    """Download data and compute HA/indicators/swings. Requires network access."""
    cfg = cfg or DEFAULT_CONFIG
    df = download_data_from_config(cfg.data)
    df = calculate_heikin_ashi(df)
    df = calculate_indicators(df, cfg.indicators)
    df = detect_swings(df, cfg.swings)
    return df


def run_backtest_pipeline(cfg: BotConfig = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Full pipeline: download data, prepare indicators, run the backtest.

    Returns:
        (prepared_df, trades_df)
    """
    cfg = cfg or DEFAULT_CONFIG
    df = prepare_data(cfg)
    trades = backtest(df, cfg)
    return df, trades
