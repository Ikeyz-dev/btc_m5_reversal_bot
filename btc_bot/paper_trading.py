"""
Phase 11 — Paper Trading.

Polls for the latest candle every 5 minutes, recalculates indicators,
checks the strategy, and prints BUY / SELL / NO SIGNAL along with the
entry/SL/TP/risk it would have used — without placing any real orders.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

import pandas as pd

from .config import BotConfig, DEFAULT_CONFIG
from .data import download_data
from .heikin_ashi import calculate_heikin_ashi
from .indicators import calculate_indicators
from .risk import calculate_position_size, calculate_stop_loss, calculate_take_profit
from .strategy import buy_signal, sell_signal
from .swings import detect_swings, last_swing_high, last_swing_low


def check_for_signal(df: pd.DataFrame, cfg: BotConfig, account_balance: float) -> dict:
    """
    Given a fully-prepared DataFrame (HA + indicators + swings already
    calculated), evaluate the most recently closed candle for a signal.

    Returns a dict describing the outcome — always includes 'signal'
    ("BUY", "SELL", or "NO SIGNAL"), and entry/sl/tp/risk details when
    a signal fires.
    """
    i = len(df) - 1  # most recently closed candle

    direction = None
    if buy_signal(df, i, cfg.strategy):
        direction = "BUY"
    elif sell_signal(df, i, cfg.strategy):
        direction = "SELL"

    if direction is None:
        return {"signal": "NO SIGNAL"}

    entry_price = float(df["close"].iloc[i])  # best available estimate pre-next-open
    atr = float(df["ATR"].iloc[i])
    swing_low = last_swing_low(df, i)
    swing_high = last_swing_high(df, i)

    stop_loss = calculate_stop_loss(
        direction, entry_price, swing_low, swing_high, atr, cfg.risk
    )
    if stop_loss is None:
        return {"signal": "NO SIGNAL", "note": "No confirmed swing point for SL yet."}

    take_profit = calculate_take_profit(direction, entry_price, stop_loss, cfg.risk)
    position_size = calculate_position_size(
        account_balance, entry_price, stop_loss, cfg.risk
    )
    risk_amount = account_balance * (cfg.risk.risk_per_trade_pct / 100.0)

    return {
        "signal": direction,
        "entry": entry_price,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "position_size": position_size,
        "risk_amount": risk_amount,
        "candle_time": df["timestamp"].iloc[i],
    }


def run_live(
    cfg: BotConfig = None,
    account_balance: float = 10_000.0,
    poll_seconds: int = 300,
    max_iterations: int = None,
) -> None:
    """
    Paper trading loop: every `poll_seconds` (default 300 = 5 minutes),
    downloads the latest candles, recalculates everything, and prints
    the current signal. Places no real orders.

    Args:
        cfg: BotConfig (defaults to DEFAULT_CONFIG).
        account_balance: Hypothetical balance used for position sizing.
        poll_seconds: Seconds between checks (300 = every 5-minute candle).
        max_iterations: If set, stop after this many checks (useful for
            testing so the loop doesn't run forever).
    """
    cfg = cfg or DEFAULT_CONFIG
    iterations = 0

    while True:
        now = datetime.now(timezone.utc)
        print(f"\n[{now.isoformat()}] Checking for signal...")

        df = download_data(
            symbol=cfg.data.symbol,
            timeframe=cfg.data.timeframe,
            limit=max(500, cfg.swings.lookback + cfg.indicators.adx_period * 3),
            exchange_id=cfg.data.exchange_id,
        )
        df = calculate_heikin_ashi(df)
        df = calculate_indicators(df, cfg.indicators)
        df = detect_swings(df, cfg.swings)

        outcome = check_for_signal(df, cfg, account_balance)

        if outcome["signal"] == "NO SIGNAL":
            print("NO SIGNAL", outcome.get("note", ""))
        else:
            print(f"{outcome['signal']} signal")
            print(f"  Entry:  {outcome['entry']:.2f}")
            print(f"  SL:     {outcome['stop_loss']:.2f}")
            print(f"  TP:     {outcome['take_profit']:.2f}")
            print(f"  Size:   {outcome['position_size']:.6f}")
            print(f"  Risk:   ${outcome['risk_amount']:.2f}")

        iterations += 1
        if max_iterations is not None and iterations >= max_iterations:
            break

        time.sleep(poll_seconds)
