"""
Phase 9 — Backtester.

Scans all candles, generates signals, computes SL/TP, simulates each
trade, and skips forward until the trade exits (no overlapping trades).
"""

from __future__ import annotations

import pandas as pd

from .config import BotConfig, DEFAULT_CONFIG
from .risk import calculate_stop_loss, calculate_take_profit
from .simulate import simulate_trade
from .strategy import buy_signal, sell_signal
from .swings import last_swing_high, last_swing_low


def backtest(df: pd.DataFrame, cfg: BotConfig = None) -> pd.DataFrame:
    """
    Run a full backtest over df, which must already have Heikin Ashi,
    indicator, and swing columns calculated (see heikin_ashi.py,
    indicators.py, swings.py).

    Avoids look-ahead bias: signals are evaluated on closed candle i,
    and the SL/TP reference swing points are only ones already
    confirmed by candle i (see swings.last_swing_high/low).

    Returns:
        DataFrame of completed trades with columns:
        ['entry_index', 'entry_time', 'direction', 'entry_price',
         'stop_loss', 'take_profit', 'exit_index', 'exit_time',
         'exit_price', 'result', 'r_multiple', 'reason'].
    """
    cfg = cfg or DEFAULT_CONFIG
    trades = []

    i = 2  # strategy signals need at least 2 rows of history
    n = len(df)

    while i < n - 1:  # need a next candle to enter on
        entry_index = i + 1
        row_signal_idx = i

        direction = None
        if buy_signal(df, row_signal_idx, cfg.strategy):
            direction = "BUY"
        elif sell_signal(df, row_signal_idx, cfg.strategy):
            direction = "SELL"

        if direction is None:
            i += 1
            continue

        entry_price = float(df["open"].iloc[entry_index])
        atr = float(df["ATR"].iloc[row_signal_idx])

        swing_low = last_swing_low(df, row_signal_idx)
        swing_high = last_swing_high(df, row_signal_idx)

        stop_loss = calculate_stop_loss(
            direction, entry_price, swing_low, swing_high, atr, cfg.risk
        )
        if stop_loss is None:
            i += 1
            continue  # no confirmed swing point yet to base SL on

        take_profit = calculate_take_profit(direction, entry_price, stop_loss, cfg.risk)

        result = simulate_trade(
            df,
            entry_index=entry_index,
            direction=direction,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )

        if result is None:
            # Trade never closed within available data; stop scanning
            # (nothing meaningful left to backtest past this point).
            break

        trades.append(
            {
                "entry_index": entry_index,
                "entry_time": df["timestamp"].iloc[entry_index],
                "direction": direction,
                "entry_price": entry_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "exit_index": result.exit_index,
                "exit_time": result.exit_time,
                "exit_price": result.exit_price,
                "result": result.result,
                "r_multiple": result.r_multiple,
                "reason": result.reason,
            }
        )

        # No overlapping trades: resume scanning after this trade exits.
        i = result.exit_index + 1

    return pd.DataFrame(trades)
