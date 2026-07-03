"""
Phase 10 — Performance Analytics.
"""

from __future__ import annotations

from typing import Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def calculate_performance(trades: pd.DataFrame) -> dict:
    """
    Compute summary performance statistics from a trades DataFrame
    (as returned by backtest.backtest()).

    Returns a dict with: total_trades, wins, losses, win_rate,
    average_r, net_r, profit_factor, expectancy, max_drawdown_r,
    longest_losing_streak, avg_trade_duration.
    """
    if trades.empty:
        return {
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "average_r": 0.0,
            "net_r": 0.0,
            "profit_factor": 0.0,
            "expectancy": 0.0,
            "max_drawdown_r": 0.0,
            "longest_losing_streak": 0,
            "avg_trade_duration": pd.Timedelta(0),
        }

    total_trades = len(trades)
    wins = int((trades["result"] == "WIN").sum())
    losses = int((trades["result"] == "LOSS").sum())
    win_rate = wins / total_trades if total_trades else 0.0

    net_r = float(trades["r_multiple"].sum())
    average_r = float(trades["r_multiple"].mean())

    gross_profit = trades.loc[trades["r_multiple"] > 0, "r_multiple"].sum()
    gross_loss = -trades.loc[trades["r_multiple"] < 0, "r_multiple"].sum()
    profit_factor = float(gross_profit / gross_loss) if gross_loss > 0 else float("inf")

    expectancy = average_r  # per-trade expected R, same basis as average_r

    equity_curve = trades["r_multiple"].cumsum()
    running_max = equity_curve.cummax()
    drawdown = equity_curve - running_max
    max_drawdown_r = float(drawdown.min()) if not drawdown.empty else 0.0

    longest_losing_streak = _longest_streak(trades["result"] == "LOSS")

    durations = pd.to_datetime(trades["exit_time"]) - pd.to_datetime(trades["entry_time"])
    avg_trade_duration = durations.mean()

    return {
        "total_trades": total_trades,
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate,
        "average_r": average_r,
        "net_r": net_r,
        "profit_factor": profit_factor,
        "expectancy": expectancy,
        "max_drawdown_r": max_drawdown_r,
        "longest_losing_streak": longest_losing_streak,
        "avg_trade_duration": avg_trade_duration,
    }


def monthly_returns(trades: pd.DataFrame) -> pd.Series:
    """Return net R-multiple grouped by calendar month."""
    if trades.empty:
        return pd.Series(dtype="float64")
    exit_times = pd.to_datetime(trades["exit_time"])
    return trades.groupby(exit_times.dt.to_period("M"))["r_multiple"].sum()


def _longest_streak(bool_series: pd.Series) -> int:
    longest = current = 0
    for val in bool_series:
        if val:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def plot_equity_curve(trades: pd.DataFrame, ax: Optional[plt.Axes] = None):
    """Plot cumulative R-multiple (equity curve) over trade sequence."""
    if ax is None:
        _, ax = plt.subplots(figsize=(10, 5))

    if trades.empty:
        ax.set_title("Equity Curve (no trades)")
        return ax

    equity = trades["r_multiple"].cumsum()
    ax.plot(range(1, len(equity) + 1), equity, label="Equity (R)")
    ax.set_xlabel("Trade #")
    ax.set_ylabel("Cumulative R")
    ax.set_title("Equity Curve")
    ax.axhline(0, color="grey", linewidth=0.8)
    ax.legend()
    return ax


def plot_drawdown_curve(trades: pd.DataFrame, ax: Optional[plt.Axes] = None):
    """Plot drawdown (in R) over trade sequence."""
    if ax is None:
        _, ax = plt.subplots(figsize=(10, 5))

    if trades.empty:
        ax.set_title("Drawdown Curve (no trades)")
        return ax

    equity = trades["r_multiple"].cumsum()
    running_max = equity.cummax()
    drawdown = equity - running_max

    ax.fill_between(range(1, len(drawdown) + 1), drawdown, 0, color="red", alpha=0.4)
    ax.set_xlabel("Trade #")
    ax.set_ylabel("Drawdown (R)")
    ax.set_title("Drawdown Curve")
    return ax


def plot_monthly_returns(trades: pd.DataFrame, ax: Optional[plt.Axes] = None):
    """Bar chart of net R-multiple by month."""
    if ax is None:
        _, ax = plt.subplots(figsize=(10, 5))

    monthly = monthly_returns(trades)
    if monthly.empty:
        ax.set_title("Monthly Returns (no trades)")
        return ax

    monthly.plot(kind="bar", ax=ax, color=np.where(monthly >= 0, "green", "red"))
    ax.set_xlabel("Month")
    ax.set_ylabel("Net R")
    ax.set_title("Monthly Returns")
    return ax


def plot_trade_distribution(trades: pd.DataFrame, ax: Optional[plt.Axes] = None):
    """Histogram of R-multiples across all trades."""
    if ax is None:
        _, ax = plt.subplots(figsize=(10, 5))

    if trades.empty:
        ax.set_title("Trade Distribution (no trades)")
        return ax

    ax.hist(trades["r_multiple"], bins=30, color="steelblue", edgecolor="black")
    ax.set_xlabel("R Multiple")
    ax.set_ylabel("Frequency")
    ax.set_title("Trade R-Multiple Distribution")
    return ax


def plot_win_loss_histogram(trades: pd.DataFrame, ax: Optional[plt.Axes] = None):
    """Bar chart of win vs. loss counts."""
    if ax is None:
        _, ax = plt.subplots(figsize=(6, 5))

    if trades.empty:
        ax.set_title("Win/Loss (no trades)")
        return ax

    counts = trades["result"].value_counts()
    counts.plot(kind="bar", ax=ax, color=["green", "red"])
    ax.set_xlabel("Result")
    ax.set_ylabel("Count")
    ax.set_title("Win/Loss Histogram")
    return ax
