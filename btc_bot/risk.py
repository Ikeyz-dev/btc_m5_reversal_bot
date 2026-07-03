"""
Phase 7 — Risk Management.

Stop Loss:
    BUY  = last swing low  - 0.2 * ATR
    SELL = last swing high + 0.2 * ATR

Take Profit: fixed 2R.

Position sizing: risk 1% of account balance per trade, one trade at a
time, stop trading after 3 losses in a day.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

from .config import RiskConfig

Direction = Literal["BUY", "SELL"]


def calculate_stop_loss(
    direction: Direction,
    entry_price: float,
    last_swing_low: Optional[float],
    last_swing_high: Optional[float],
    atr: float,
    cfg: RiskConfig = None,
) -> Optional[float]:
    """
    Calculate the stop loss price for a trade, enforcing a minimum
    distance that is the LARGER of:
      - min_sl_atr_multiple * ATR (adapts to recent volatility)
      - min_sl_pct * entry_price (a hard floor for quiet periods when
        ATR itself is too small to produce a realistically tradeable
        stop — e.g. 0.02% ATR-based stops that are tighter than
        typical spread + fees).
    """
    cfg = cfg or RiskConfig()
    min_distance = max(
        cfg.min_sl_atr_multiple * atr,
        cfg.min_sl_pct / 100.0 * entry_price,
    )

    if direction == "BUY":
        if last_swing_low is None:
            return None
        sl = last_swing_low - cfg.sl_atr_multiplier * atr
        if entry_price - sl < min_distance:
            sl = entry_price - min_distance
        return sl

    if direction == "SELL":
        if last_swing_high is None:
            return None
        sl = last_swing_high + cfg.sl_atr_multiplier * atr
        if sl - entry_price < min_distance:
            sl = entry_price + min_distance
        return sl

    raise ValueError(f"Unknown direction: {direction}")

def calculate_take_profit(
    direction: Direction,
    entry_price: float,
    stop_loss: float,
    cfg: RiskConfig = None,
) -> float:
    """Calculate a fixed-R take profit price given entry and stop loss."""
    cfg = cfg or RiskConfig()
    risk_distance = abs(entry_price - stop_loss)
    reward_distance = risk_distance * cfg.take_profit_r_multiple

    if direction == "BUY":
        return entry_price + reward_distance
    if direction == "SELL":
        return entry_price - reward_distance
    raise ValueError(f"Unknown direction: {direction}")


def calculate_position_size(
    account_balance: float,
    entry_price: float,
    stop_loss: float,
    cfg: RiskConfig = None,
) -> float:
    """
    Calculate position size (in units of the base asset, e.g. BTC) so
    that a stop-loss hit loses exactly `risk_per_trade_pct` of the
    account balance.
    """
    cfg = cfg or RiskConfig()
    risk_amount = account_balance * (cfg.risk_per_trade_pct / 100.0)
    risk_distance = abs(entry_price - stop_loss)

    if risk_distance <= 0:
        raise ValueError("Stop loss distance must be greater than zero.")

    return risk_amount / risk_distance


@dataclass
class DailyLossTracker:
    """
    Tracks consecutive/daily losses so trading can be halted after the
    configured daily loss limit is hit. Reset at the start of each
    trading day.
    """

    cfg: RiskConfig = None
    current_date: Optional[str] = None
    losses_today: int = 0

    def __post_init__(self):
        self.cfg = self.cfg or RiskConfig()

    def record_result(self, trade_date: str, is_loss: bool) -> None:
        if trade_date != self.current_date:
            self.current_date = trade_date
            self.losses_today = 0
        if is_loss:
            self.losses_today += 1

    def can_trade(self) -> bool:
        return self.losses_today < self.cfg.daily_loss_limit
