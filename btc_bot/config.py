"""
Central configuration for the BTC M5 Reversal Trading Bot.

Keeping every tunable parameter in one place makes it easy to run
walk-forward tests or parameter sweeps later (see Phase 15).
"""

from dataclasses import dataclass


@dataclass
class DataConfig:
    exchange_id: str = "binance"
    symbol: str = "BTC/USDT"
    timeframe: str = "5m"
    candles_to_fetch: int = 100000  # supports "thousands of candles"


@dataclass
class IndicatorConfig:
    stoch_k: int = 14
    stoch_d: int = 3
    stoch_slowing: int = 3
    adx_period: int = 14
    atr_period: int = 14


@dataclass
class SwingConfig:
    lookback: int = 3  # compares against i-1, i-2, i-3


@dataclass
class StrategyConfig:
    stoch_oversold: float = 20.0
    stoch_overbought: float = 80.0
    adx_threshold: float = 25.0
    adx_threshold_max: float = 40.0   # skip trades above this — see backtest findings


@dataclass
class RiskConfig:
    risk_per_trade_pct: float = 1.0
    max_simultaneous_trades: int = 1
    daily_loss_limit: int = 3
    sl_atr_multiplier: float = 0.2
    take_profit_r_multiple: float = 2.0
    fee_pct: float = 0.05      # per-side taker fee, e.g. 0.05% = 0.0005
    slippage_pct: float = 0.02  # per-side estimated slippage, e.g. 0.02%
    min_sl_atr_multiple: float = 0.5  # never let SL be tighter than this many ATRs

@dataclass
class BotConfig:
    data: DataConfig = None
    indicators: IndicatorConfig = None
    swings: SwingConfig = None
    strategy: StrategyConfig = None
    risk: RiskConfig = None

    def __post_init__(self):
        self.data = self.data or DataConfig()
        self.indicators = self.indicators or IndicatorConfig()
        self.swings = self.swings or SwingConfig()
        self.strategy = self.strategy or StrategyConfig()
        self.risk = self.risk or RiskConfig()


DEFAULT_CONFIG = BotConfig()
