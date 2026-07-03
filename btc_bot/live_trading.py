"""
Phase 12 — Live Trading.

IMPORTANT PLATFORM NOTE
------------------------
Exness is a forex/CFD broker traded via MetaTrader 4/5, not a crypto
exchange with a REST API like Binance. The standard way to automate
Exness from Python is the `MetaTrader5` package, which only works:
  - on Windows (or Wine on Linux, unofficially),
  - with the MetaTrader 5 terminal installed and logged in locally.
It will NOT run on Google Colab or Termux/Android, because both lack
a place to run the MT5 terminal itself. For a mobile-friendly setup,
plan to run this module on a small Windows VPS, or use a broker that
offers a real REST/WebSocket API instead.

This module defines a broker-agnostic interface (`BrokerClient`) so the
strategy/risk/backtest logic never needs to change when the execution
backend changes. `MT5Broker` is a best-effort implementation you can
run once you have a Windows environment; swap in a different
`BrokerClient` subclass for any other broker without touching the
rest of the bot.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal, Optional

from .config import BotConfig, DEFAULT_CONFIG
from .data import download_data
from .heikin_ashi import calculate_heikin_ashi
from .indicators import calculate_indicators
from .logger import TradeLogEntry, TradeLogger
from .risk import DailyLossTracker, calculate_position_size, calculate_stop_loss, calculate_take_profit
from .strategy import buy_signal, sell_signal
from .swings import detect_swings, last_swing_high, last_swing_low

Direction = Literal["BUY", "SELL"]


@dataclass
class OpenPosition:
    direction: Direction
    entry_price: float
    stop_loss: float
    take_profit: float
    size: float
    entry_time: datetime
    ticket: Optional[str] = None


class BrokerClient(ABC):
    """Minimal broker interface the live engine depends on."""

    @abstractmethod
    def connect(self) -> None:
        ...

    @abstractmethod
    def get_account_balance(self) -> float:
        ...

    @abstractmethod
    def has_open_position(self) -> bool:
        ...

    @abstractmethod
    def open_position(
        self, direction: Direction, size: float, stop_loss: float, take_profit: float
    ) -> str:
        """Open a position with SL/TP attached immediately. Returns a ticket id."""
        ...

    @abstractmethod
    def close_position(self, ticket: str) -> float:
        """Close a position. Returns the realized profit."""
        ...


class MT5Broker(BrokerClient):
    """
    MetaTrader5-backed broker client for Exness (or any MT5 broker).

    Requires: pip install MetaTrader5   (Windows only)
    and the MT5 terminal installed + logged into your Exness account.
    """

    def __init__(self, symbol: str = "BTCUSDm", login: int = None, password: str = None, server: str = None):
        self.symbol = symbol
        self.login = login
        self.password = password
        self.server = server
        self._mt5 = None

    def connect(self) -> None:
        try:
            import MetaTrader5 as mt5
        except ImportError as e:
            raise ImportError(
                "MetaTrader5 package not available. This broker only runs on "
                "Windows with the MT5 terminal installed. See module docstring."
            ) from e

        self._mt5 = mt5
        if not mt5.initialize(login=self.login, password=self.password, server=self.server):
            raise ConnectionError(f"MT5 initialize() failed: {mt5.last_error()}")

    def get_account_balance(self) -> float:
        info = self._mt5.account_info()
        if info is None:
            raise ConnectionError(f"Could not fetch account info: {self._mt5.last_error()}")
        return float(info.balance)

    def has_open_position(self) -> bool:
        positions = self._mt5.positions_get(symbol=self.symbol)
        return bool(positions)

    def open_position(
        self, direction: Direction, size: float, stop_loss: float, take_profit: float
    ) -> str:
        mt5 = self._mt5
        order_type = mt5.ORDER_TYPE_BUY if direction == "BUY" else mt5.ORDER_TYPE_SELL
        tick = mt5.symbol_info_tick(self.symbol)
        price = tick.ask if direction == "BUY" else tick.bid

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.symbol,
            "volume": size,
            "type": order_type,
            "price": price,
            "sl": stop_loss,
            "tp": take_profit,
            "deviation": 20,
            "magic": 20260702,
            "comment": "btc_m5_reversal_bot",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            raise RuntimeError(f"order_send failed: {result.retcode} {result.comment}")
        return str(result.order)

    def close_position(self, ticket: str) -> float:
        mt5 = self._mt5
        positions = mt5.positions_get(ticket=int(ticket))
        if not positions:
            raise ValueError(f"No open position found for ticket {ticket}")
        pos = positions[0]

        order_type = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
        tick = mt5.symbol_info_tick(pos.symbol)
        price = tick.bid if order_type == mt5.ORDER_TYPE_SELL else tick.ask

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": pos.symbol,
            "volume": pos.volume,
            "type": order_type,
            "position": pos.ticket,
            "price": price,
            "deviation": 20,
            "magic": 20260702,
            "comment": "btc_m5_reversal_bot_close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            raise RuntimeError(f"close order_send failed: {result.retcode} {result.comment}")
        return float(pos.profit)


class LiveTradingEngine:
    """
    Wires strategy + risk + broker together into an automated loop.
    Only one position at a time; halts for the day after the
    configured number of losses.
    """

    def __init__(
        self,
        broker: BrokerClient,
        cfg: BotConfig = None,
        csv_log_path: str = "trade_log.csv",
    ):
        self.broker = broker
        self.cfg = cfg or DEFAULT_CONFIG
        self.loss_tracker = DailyLossTracker(cfg=self.cfg.risk)
        self.logger = TradeLogger(csv_log_path)

    def run(self, poll_seconds: int = 300, max_iterations: int = None) -> None:
        self.broker.connect()
        iterations = 0

        while True:
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

            if not self.loss_tracker.can_trade():
                print(f"[{today}] Daily loss limit reached. Standing down for today.")
            elif self.broker.has_open_position():
                print(f"[{today}] Position already open. Waiting.")
            else:
                self._check_and_trade(today)

            iterations += 1
            if max_iterations is not None and iterations >= max_iterations:
                break
            time.sleep(poll_seconds)

    def _check_and_trade(self, today: str) -> None:
        df = download_data(
            symbol=self.cfg.data.symbol,
            timeframe=self.cfg.data.timeframe,
            limit=max(500, self.cfg.indicators.adx_period * 3),
            exchange_id=self.cfg.data.exchange_id,
        )
        df = calculate_heikin_ashi(df)
        df = calculate_indicators(df, self.cfg.indicators)
        df = detect_swings(df, self.cfg.swings)

        i = len(df) - 1
        direction: Optional[Direction] = None
        if buy_signal(df, i, self.cfg.strategy):
            direction = "BUY"
        elif sell_signal(df, i, self.cfg.strategy):
            direction = "SELL"

        if direction is None:
            print(f"[{today}] NO SIGNAL")
            return

        entry_price = float(df["close"].iloc[i])
        atr = float(df["ATR"].iloc[i])
        swing_low = last_swing_low(df, i)
        swing_high = last_swing_high(df, i)

        stop_loss = calculate_stop_loss(
            direction, entry_price, swing_low, swing_high, atr, self.cfg.risk
        )
        if stop_loss is None:
            print(f"[{today}] Signal fired but no confirmed swing point for SL yet.")
            return

        take_profit = calculate_take_profit(direction, entry_price, stop_loss, self.cfg.risk)
        balance = self.broker.get_account_balance()
        size = calculate_position_size(balance, entry_price, stop_loss, self.cfg.risk)

        print(f"[{today}] {direction} signal -> opening position: "
              f"entry={entry_price:.2f} sl={stop_loss:.2f} tp={take_profit:.2f} size={size:.6f}")

        ticket = self.broker.open_position(direction, size, stop_loss, take_profit)

        # Note: in a full implementation you'd track this position and
        # poll it until closed, then log the realized result via
        # self.loss_tracker.record_result(today, is_loss) and
        # self.logger.log_trade(...). Left as an exercise wired for
        # your specific broker's position-tracking API, since MT5's
        # position lifecycle differs from a simple synchronous close.
