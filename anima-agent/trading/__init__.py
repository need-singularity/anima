"""Anima self-contained trading system.

Consciousness-aware backtesting, portfolio management, and risk control.
No external invest dependency — fully standalone.

Usage:
    from trading import BacktestEngine, MACDStrategy
    engine = BacktestEngine(symbol="BTCUSDT", timeframe="1h")
    result = engine.run(MACDStrategy(), days=30)
    print(result.total_return, result.sharpe)
"""

from trading.engine import BacktestEngine, BacktestResult
from trading.strategy import (
    Strategy,
    MACDStrategy,
    RSIStrategy,
    BollingerStrategy,
    ConsciousnessStrategy,
)
from trading.broker import Broker, BinanceBroker
from trading.data import MarketData, fetch_ohlcv
from trading.portfolio import Portfolio, Position
from trading.risk import RiskManager, ConsciousnessGate

__all__ = [
    "BacktestEngine",
    "BacktestResult",
    "Strategy",
    "MACDStrategy",
    "RSIStrategy",
    "BollingerStrategy",
    "ConsciousnessStrategy",
    "Broker",
    "BinanceBroker",
    "MarketData",
    "fetch_ohlcv",
    "Portfolio",
    "Position",
    "RiskManager",
    "ConsciousnessGate",
]
