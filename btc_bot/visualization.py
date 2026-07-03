"""
Phase 14 — Visualization.

Builds a single dashboard figure combining the individual analytics
plots (equity curve, drawdown, monthly returns, distribution, win/loss)
plus a price/HA chart with trade entry/exit markers.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd

from .analytics import (
    plot_drawdown_curve,
    plot_equity_curve,
    plot_monthly_returns,
    plot_trade_distribution,
    plot_win_loss_histogram,
)


def plot_price_with_trades(
    df: pd.DataFrame, trades: pd.DataFrame, ax: plt.Axes = None, lookback: int = None
):
    """
    Plot close price (optionally just the last `lookback` candles) with
    BUY/SELL entry markers and exit markers overlaid.
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(14, 6))

    plot_df = df if lookback is None else df.tail(lookback)
    ax.plot(plot_df["timestamp"], plot_df["close"], color="black", linewidth=0.8, label="Close")

    if not trades.empty:
        visible_trades = trades
        if lookback is not None:
            min_time = plot_df["timestamp"].iloc[0]
            visible_trades = trades[trades["entry_time"] >= min_time]

        buys = visible_trades[visible_trades["direction"] == "BUY"]
        sells = visible_trades[visible_trades["direction"] == "SELL"]

        ax.scatter(buys["entry_time"], buys["entry_price"], marker="^", color="green", s=60, label="BUY entry", zorder=5)
        ax.scatter(sells["entry_time"], sells["entry_price"], marker="v", color="red", s=60, label="SELL entry", zorder=5)
        ax.scatter(visible_trades["exit_time"], visible_trades["exit_price"], marker="x", color="blue", s=40, label="Exit", zorder=5)

    ax.set_title("Price with Trade Entries/Exits")
    ax.set_xlabel("Time")
    ax.set_ylabel("Price")
    ax.legend()
    return ax


def build_dashboard(df: pd.DataFrame, trades: pd.DataFrame, price_lookback: int = 2000):
    """
    Build a single figure with 6 panels summarizing the backtest:
    price+trades, equity curve, drawdown, monthly returns,
    R-multiple distribution, and win/loss counts.

    Returns the matplotlib Figure (call .savefig(...) or plt.show()).
    """
    fig = plt.figure(figsize=(16, 18))
    gs = fig.add_gridspec(4, 2)

    ax_price = fig.add_subplot(gs[0, :])
    plot_price_with_trades(df, trades, ax=ax_price, lookback=price_lookback)

    ax_equity = fig.add_subplot(gs[1, 0])
    plot_equity_curve(trades, ax=ax_equity)

    ax_dd = fig.add_subplot(gs[1, 1])
    plot_drawdown_curve(trades, ax=ax_dd)

    ax_monthly = fig.add_subplot(gs[2, :])
    plot_monthly_returns(trades, ax=ax_monthly)

    ax_dist = fig.add_subplot(gs[3, 0])
    plot_trade_distribution(trades, ax=ax_dist)

    ax_wl = fig.add_subplot(gs[3, 1])
    plot_win_loss_histogram(trades, ax=ax_wl)

    fig.tight_layout()
    return fig
