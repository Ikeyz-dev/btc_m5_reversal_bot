"""
Phase 13 — Logging.

Logs every trade to a CSV file with a fixed schema.
"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass, fields
from typing import Optional

CSV_FIELDS = [
    "entry_time",
    "exit_time",
    "type",
    "entry",
    "sl",
    "tp",
    "exit",
    "profit",
    "r_multiple",
    "reason_for_exit",
    "stoch_k",
    "stoch_d",
    "adx",
    "atr",
    "swing_low",
    "swing_high",
]


@dataclass
class TradeLogEntry:
    entry_time: str
    exit_time: str
    type: str  # "BUY" or "SELL"
    entry: float
    sl: float
    tp: float
    exit: float
    profit: float
    r_multiple: float
    reason_for_exit: str


class TradeLogger:
    """Appends completed trades to a CSV file, creating it with a
    header row if it doesn't exist yet."""

    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self._ensure_file()

    def _ensure_file(self) -> None:
        directory = os.path.dirname(self.csv_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        if not os.path.exists(self.csv_path):
            with open(self.csv_path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
                writer.writeheader()

    def log_trade(self, entry: TradeLogEntry) -> None:
        with open(self.csv_path, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            writer.writerow(
                {field.name: getattr(entry, field.name) for field in fields(entry)}
            )

    def log_backtest_trades(self, trades_df) -> None:
        """Bulk-log every row of a backtest.backtest() output DataFrame."""
        for _, row in trades_df.iterrows():
            profit = row["r_multiple"]  # in R; convert to $ externally if needed
            entry = TradeLogEntry(
                entry_time=str(row["entry_time"]),
                exit_time=str(row["exit_time"]),
                type=row["direction"],
                entry=row["entry_price"],
                sl=row["stop_loss"],
                tp=row["take_profit"],
                exit=row["exit_price"],
                profit=profit,
                r_multiple=row["r_multiple"],
                reason_for_exit=row["reason"],
            )
            self.log_trade(entry)
