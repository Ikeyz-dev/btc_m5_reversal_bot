"""
main.py — Example entry point for the BTC M5 Reversal Bot.

Run modes (edit MODE below or pass as a CLI arg):
    backtest  — download data, run backtest, print stats, save dashboard PNG
    paper     — run the paper-trading loop (Binance data, no real orders)
    live      — run the live-trading loop against Exness via MT5
                (Windows only — see btc_bot/live_trading.py docstring)

Usage:
    python main.py backtest
    python main.py paper
    python main.py live
"""

from __future__ import annotations

import sys

from btc_bot.analytics import calculate_performance
from btc_bot.config import DEFAULT_CONFIG
from btc_bot.logger import TradeLogger
from btc_bot.paper_trading import run_live
from btc_bot.pipeline import run_backtest_pipeline
from btc_bot.visualization import build_dashboard


def run_backtest_mode():
    print(f"Downloading {DEFAULT_CONFIG.data.candles_to_fetch} candles of "
          f"{DEFAULT_CONFIG.data.symbol} {DEFAULT_CONFIG.data.timeframe} from "
          f"{DEFAULT_CONFIG.data.exchange_id}...")

    df, trades = run_backtest_pipeline(DEFAULT_CONFIG)

    print(f"\n{len(trades)} trades generated.")
    stats = calculate_performance(trades)
    print("\n--- Performance Summary ---")
    for k, v in stats.items():
        print(f"{k}: {v}")

    logger = TradeLogger("trade_log.csv")
    logger.log_backtest_trades(trades)
    print("\nTrades logged to trade_log.csv")

    fig = build_dashboard(df, trades)
    fig.savefig("dashboard.png", dpi=150)
    print("Dashboard saved to dashboard.png")


def run_paper_mode():
    print("Starting paper trading loop (Ctrl+C to stop)...")
    run_live(cfg=DEFAULT_CONFIG, account_balance=10_000.0, poll_seconds=300)


def run_live_mode():
    from btc_bot.live_trading import LiveTradingEngine, MT5Broker

    # Fill in your Exness MT5 account details before running for real.
    broker = MT5Broker(
        symbol="BTCUSDm",
        login=None,       # your MT5 login number
        password=None,    # your MT5 password
        server=None,      # your Exness server name, e.g. "Exness-MT5Trial9"
    )
    engine = LiveTradingEngine(broker, cfg=DEFAULT_CONFIG, csv_log_path="live_trade_log.csv")
    print("Starting LIVE trading loop (Ctrl+C to stop)...")
    engine.run(poll_seconds=300)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "backtest"

    if mode == "backtest":
        run_backtest_mode()
    elif mode == "paper":
        run_paper_mode()
    elif mode == "live":
        run_live_mode()
    else:
        print(f"Unknown mode: {mode}. Use backtest | paper | live")
