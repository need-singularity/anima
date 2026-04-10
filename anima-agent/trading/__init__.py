"""Anima autonomous trading system.

Consciousness-aware trading with autonomous scanning, regime detection,
multi-strategy signal generation, and risk-gated execution.

No external invest dependency — fully standalone.

Quick start:
    from trading import AutonomousTrader, AutonomousConfig
    trader = AutonomousTrader()
    result = trader.run_cycle()        # single cycle
    trader.run_forever(interval=300)   # autonomous loop

Backtest:
    from trading import BacktestEngine, MACDStrategy
    engine = BacktestEngine(symbol="BTCUSDT", timeframe="1h")
    result = engine.run(MACDStrategy(), days=30)

Components:
    - autonomous.py:  Main autonomous loop (scan -> signal -> gate -> execute)
    - strategies.py:  13+ strategies (trend, mean-revert, momentum, vol, sentiment, ensemble)
    - regime.py:      Market regime detection (vol, return, trend, SOC)
    - scanner.py:     Market scanner (top movers, volume spikes, signal convergence)
    - executor.py:    Order execution with retry/fallback/TECS-L sizing
    - engine.py:      Backtest engine (event-driven)
    - strategy.py:    Base strategy class + core strategies (MACD, RSI, Bollinger, Consciousness)
    - broker.py:      Broker abstraction (Binance, paper)
    - data.py:        Market data fetching (Binance public API)
    - portfolio.py:   Portfolio management (positions, PnL, equity curve)
    - risk.py:        Risk management (VaR, drawdown, ConsciousnessGate)
"""

# Core data + portfolio
from trading.data import MarketData, fetch_ohlcv
from trading.portfolio import Portfolio, Position, Trade

# Broker
from trading.broker import Broker, BinanceBroker, PaperBroker, OrderResult

# Risk
from trading.risk import RiskManager, RiskLimits, ConsciousnessGate

# Strategy base + core strategies
from trading.strategy import (
    Strategy,
    Signal,
    StrategySignal,
    MACDStrategy,
    RSIStrategy,
    BollingerStrategy,
    ConsciousnessStrategy,
    ConsciousnessEnsembleStrategy,
)

# Extended strategies (from invest migration)
from trading.strategies import (
    EMAcrossStrategy,
    ADXTrendStrategy,
    MultiTimeframeStrategy,
    StochasticStrategy,
    VWAPReversionStrategy,
    MomentumFactorStrategy,
    OBVDivergenceStrategy,
    VolBreakoutStrategy,
    VolMeanRevertStrategy,
    FearGreedStrategy,
    VolumeSurgeStrategy,
    ATRBreakoutStrategy,
    EnsembleStrategy,
    ALL_STRATEGIES,
    get_all_strategies,
)

# Regime detection
from trading.regime import (
    MarketRegime,
    RegimePolicy,
    RegimeDetector,
    RegimeState,
    detect_vol_regime,
    detect_return_regime,
    detect_trend_regime,
    soc_criticality_score,
)

# Scanner
from trading.scanner import MarketScanner, ScanReport, ScanResult

# Executor
from trading.executor import OrderExecutor, ExecutionConfig, ExecutionResult

# Backtest engine
from trading.engine import BacktestEngine, BacktestResult, quick_backtest

# Autonomous loop
from trading.autonomous import AutonomousTrader, AutonomousConfig, CycleResult

__all__ = [
    # Data
    "MarketData", "fetch_ohlcv",
    # Portfolio
    "Portfolio", "Position", "Trade",
    # Broker
    "Broker", "BinanceBroker", "PaperBroker", "OrderResult",
    # Risk
    "RiskManager", "RiskLimits", "ConsciousnessGate",
    # Strategy base
    "Strategy", "Signal", "StrategySignal",
    # Core strategies
    "MACDStrategy", "RSIStrategy", "BollingerStrategy", "ConsciousnessStrategy",
    "ConsciousnessEnsembleStrategy",
    # Extended strategies
    "EMAcrossStrategy", "ADXTrendStrategy", "MultiTimeframeStrategy",
    "StochasticStrategy", "VWAPReversionStrategy", "MomentumFactorStrategy",
    "OBVDivergenceStrategy", "VolBreakoutStrategy", "VolMeanRevertStrategy",
    "FearGreedStrategy", "VolumeSurgeStrategy", "ATRBreakoutStrategy",
    "EnsembleStrategy", "ALL_STRATEGIES", "get_all_strategies",
    # Regime
    "MarketRegime", "RegimePolicy", "RegimeDetector", "RegimeState",
    "detect_vol_regime", "detect_return_regime", "detect_trend_regime",
    "soc_criticality_score",
    # Scanner
    "MarketScanner", "ScanReport", "ScanResult",
    # Executor
    "OrderExecutor", "ExecutionConfig", "ExecutionResult",
    # Backtest
    "BacktestEngine", "BacktestResult", "quick_backtest",
    # Autonomous
    "AutonomousTrader", "AutonomousConfig", "CycleResult",
]
