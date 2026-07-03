# BTC/USD M5 Reversal Bot

A Heikin Ashi + Stochastic + ADX confluence reversal strategy for
5-minute BTC candles, built as a modular Python package so it moves
cleanly from research notebook → backtest → paper trading → live
execution without rewriting logic.

## Why Google Colab instead of Termux

You mentioned getting stuck building `pandas` from source in Termux.
That's expected — Termux runs on Android's ARM architecture, and
pandas/numpy often don't have prebuilt wheels for that target, so pip
falls back to compiling C extensions on-device, which is slow and
error-prone on a phone.

**Google Colab sidesteps this completely**: it's a cloud Linux VM with
pandas, numpy, and most scientific packages preinstalled with
prebuilt wheels, accessed entirely through your phone's browser. You
never compile anything locally. This is the recommended way to run
this project from mobile.

## Quickstart on Google Colab (recommended)

1. Go to colab.research.google.com in your phone's browser.
2. New notebook → in the first cell, upload the project zip via the
   Colab file browser, then:
   ```python
   !unzip btc_bot.zip
   %cd btc_bot
   !pip install -q -r requirements.txt
   ```
3. Run a backtest:
   ```python
   !python main.py backtest
   ```
4. View the results:
   ```python
   from IPython.display import Image
   Image("dashboard.png")
   ```
   ```python
   import pandas as pd
   pd.read_csv("trade_log.csv")
   ```

Paper trading (`!python main.py paper`) works the same way in Colab,
but note Colab disconnects idle sessions after a while — it's fine for
testing signal generation, not for a 24/7 unattended loop.

## Project layout

```
btc_bot/
  config.py           Phase 1  - central tunable parameters
  data.py              Phase 2  - download OHLCV via ccxt (Binance default)
  heikin_ashi.py        Phase 3  - Heikin Ashi candle calculation
  indicators.py          Phase 4  - Stochastic (K/D/Slowing), ADX, ATR
  swings.py                Phase 5  - swing high/low detection
  strategy.py                Phase 6  - buy_signal() / sell_signal() rules
  risk.py                      Phase 7  - SL/TP calc, position sizing, daily loss limit
  simulate.py                    Phase 8  - walks a single trade forward to SL/TP
  backtest.py                      Phase 9  - full backtest loop over historical data
  analytics.py                       Phase 10 - win rate, R stats, equity/drawdown plots
  paper_trading.py                     Phase 11 - polling loop, no real orders
  live_trading.py                        Phase 12 - broker interface + MT5/Exness impl
  logger.py                                Phase 13 - CSV trade logging
  visualization.py                           Phase 14 - combined dashboard figure
  pipeline.py             helper - chains phases 1-10 into one call
main.py                 run backtest / paper / live from the command line
requirements.txt
```

## Strategy rules (as implemented)

**BUY** when, on the most recently closed candle:
- Stochastic: `%K` was below 20 one candle ago and has since turned up
- ADX: rising over the last 2 candles and above 25 (trend strengthening)
- Heikin Ashi: last two candles both bullish

**SELL** is the mirror image (K above 80 turning down, HA bearish).

**Stop Loss**: last confirmed swing low/high +/- `0.2 x ATR`.
**Take Profit**: fixed 2R.
**Position size**: sized so a stop-out loses exactly 1% of account balance.
**Risk controls**: one open trade at a time, halt after 3 losing trades in a day.

All of these are tunable in `btc_bot/config.py` without touching any
other file.

## Important caveats

- **Phase 12 (live trading) only runs on Windows.** Exness is traded
  through MetaTrader 5, and the `MetaTrader5` Python package requires
  the actual MT5 terminal running locally - it cannot run on Colab,
  Termux, or any Android device. Realistic setups: a cheap Windows VPS,
  or switch execution to a broker with a real REST/WebSocket API.
- Backtest SL/TP simulation assumes **stop loss wins ties** when a
  single candle's range touches both SL and TP - a deliberately
  conservative assumption, since OHLC data alone can't tell you which
  was hit first intrabar.
- No look-ahead bias: signals only ever reference already-closed
  candles, and swing points used for SL are only ones confirmed at or
  before the signal candle.
- This is research/education code, not financial advice. Backtest
  results (especially on a strategy this specific) can look good on
  historical data and still lose money live - validate extensively
  with paper trading before risking real funds, and understand you
  can lose money trading.

## Running locally (non-mobile)

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py backtest
```
