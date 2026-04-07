"""Backtest engine — event-driven candle iteration with strategy + risk.

Simple but functional: iterate candles, apply strategy signals,
manage positions via Portfolio, enforce risk limits.

Usage:
    from trading import BacktestEngine, MACDStrategy
    engine = BacktestEngine(symbol="BTCUSDT", timeframe="1h")
    result = engine.run(MACDStrategy(), days=30)
    print(result.total_return, result.sharpe)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from trading.data import MarketData, fetch_ohlcv
from trading.portfolio import Portfolio, Trade
from trading.strategy import Strategy, Signal, StrategySignal
from trading.risk import RiskManager, RiskLimits, ConsciousnessGate
from trading.broker import PaperBroker

logger = logging.getLogger(__name__)


@dataclass
class BacktestResult:
    """Backtest output with all key metrics."""

    symbol: str
    timeframe: str
    strategy_name: str
    n_candles: int
    duration_days: float

    # Performance
    total_return: float        # as fraction (0.15 = 15%)
    total_return_pct: float    # as percentage (15.0)
    sharpe: float
    sortino: float
    max_drawdown: float        # as fraction
    max_drawdown_pct: float    # as percentage

    # Trades
    total_trades: int
    win_rate: float            # as fraction
    win_rate_pct: float

    # Details
    initial_balance: float
    final_equity: float
    trades: list[Trade] = field(default_factory=list)
    equity_curve: list[float] = field(default_factory=list)
    elapsed_seconds: float = 0.0

    # Risk
    risk_halts: int = 0
    consciousness_halts: int = 0

    def summary(self) -> str:
        """Human-readable summary."""
        lines = [
            f"=== Backtest: {self.strategy_name} on {self.symbol} ({self.timeframe}) ===",
            f"Period: {self.duration_days:.0f} days, {self.n_candles} candles",
            f"Return: {self.total_return_pct:+.2f}%",
            f"Sharpe: {self.sharpe:.3f}",
            f"Sortino: {self.sortino:.3f}",
            f"Max DD: {self.max_drawdown_pct:.2f}%",
            f"Trades: {self.total_trades} (win rate: {self.win_rate_pct:.1f}%)",
            f"Equity: ${self.initial_balance:,.0f} -> ${self.final_equity:,.2f}",
        ]
        if self.risk_halts > 0:
            lines.append(f"Risk halts: {self.risk_halts}")
        if self.consciousness_halts > 0:
            lines.append(f"Consciousness halts: {self.consciousness_halts}")
        lines.append(f"Elapsed: {self.elapsed_seconds:.2f}s")
        return "\n".join(lines)


class BacktestEngine:
    """Event-driven backtest engine.

    Iterates through candles, applies strategy, manages positions
    with risk limits and optional consciousness gating.
    """

    def __init__(
        self,
        symbol: str = "BTCUSDT",
        timeframe: str = "1h",
        initial_balance: float = 10_000.0,
        risk_limits: Optional[RiskLimits] = None,
        consciousness_gate: Optional[ConsciousnessGate] = None,
        position_size_pct: float = 0.10,
    ):
        """
        Args:
            symbol: Trading pair.
            timeframe: Candle interval.
            initial_balance: Starting balance.
            risk_limits: Risk management limits.
            consciousness_gate: Optional consciousness-based gating.
            position_size_pct: Default position size as % of equity.
        """
        self.symbol = symbol
        self.timeframe = timeframe
        self.initial_balance = initial_balance
        self.risk_manager = RiskManager(risk_limits)
        self.consciousness_gate = consciousness_gate
        self.position_size_pct = position_size_pct

    def run(
        self,
        strategy: Strategy,
        days: int = 30,
        data: Optional[MarketData] = None,
        verbose: bool = False,
    ) -> BacktestResult:
        """Run a backtest.

        Args:
            strategy: Strategy instance to test.
            days: Days of historical data to test on.
            data: Pre-fetched MarketData (if None, fetches from Binance).
            verbose: Print trade-by-trade output.

        Returns:
            BacktestResult with all metrics.
        """
        t0 = time.time()

        # Fetch data
        if data is None:
            data = fetch_ohlcv(
                symbol=self.symbol,
                timeframe=self.timeframe,
                days=days,
            )

        portfolio = Portfolio(self.initial_balance)
        broker = PaperBroker(data)
        self.risk_manager.reset_daily(self.initial_balance)

        risk_halts = 0
        consciousness_halts = 0
        warmup = strategy.warmup_periods()

        # Main loop: iterate candles
        for idx in range(warmup, data.n_candles):
            broker.set_index(idx)
            price = data.close[idx]
            timestamp = data.timestamps[idx]

            # Check stop loss / take profit on open positions
            for sym in list(portfolio.positions.keys()):
                pos = portfolio.positions[sym]
                if pos.should_stop(price):
                    trade = portfolio.close_position(sym, price, timestamp)
                    if verbose and trade:
                        logger.info("STOP LOSS: %s @ %.2f (PnL: %.2f)",
                                    sym, price, trade.pnl)
                elif pos.should_take_profit(price):
                    trade = portfolio.close_position(sym, price, timestamp)
                    if verbose and trade:
                        logger.info("TAKE PROFIT: %s @ %.2f (PnL: %.2f)",
                                    sym, price, trade.pnl)

            # Generate signal
            sig = strategy.generate_signal(data, idx)

            if sig.signal != Signal.HOLD:
                # Consciousness gate check
                if self.consciousness_gate is not None:
                    allowed, reason = self.consciousness_gate.allow_trade()
                    if not allowed:
                        consciousness_halts += 1
                        if verbose:
                            logger.info("CONSCIOUSNESS HALT: %s", reason)
                        sig = StrategySignal(Signal.HOLD, reason=reason)

            # Execute signal
            if sig.signal == Signal.BUY and self.symbol not in portfolio.positions:
                # Calculate position size
                eq = portfolio.equity({self.symbol: price})
                size = (eq * self.position_size_pct) / price

                if sig.stop_loss:
                    from trading.risk import RiskManager
                    risk_size = self.risk_manager.position_size_from_risk(
                        eq, price, sig.stop_loss, risk_per_trade=0.02,
                    )
                    size = min(size, risk_size) if risk_size > 0 else size

                # Risk check
                can_trade, reason = self.risk_manager.check_can_trade(
                    portfolio, price, size,
                )
                if not can_trade:
                    risk_halts += 1
                    if verbose:
                        logger.info("RISK HALT: %s", reason)
                else:
                    opened = portfolio.open_position(
                        self.symbol, "long", price, size, timestamp,
                        stop_loss=sig.stop_loss,
                        take_profit=sig.take_profit,
                    )
                    if verbose and opened:
                        logger.info("BUY %s: %.4f @ %.2f [%s]",
                                    self.symbol, size, price, sig.reason)

            elif sig.signal == Signal.SELL and self.symbol in portfolio.positions:
                trade = portfolio.close_position(self.symbol, price, timestamp)
                if verbose and trade:
                    logger.info("SELL %s @ %.2f (PnL: %+.2f / %+.1f%%) [%s]",
                                self.symbol, price, trade.pnl,
                                trade.pnl_pct * 100, sig.reason)

            # Update equity tracking
            portfolio.update_equity({self.symbol: price})

        # Close any remaining positions at last price
        last_price = data.close[-1]
        last_ts = data.timestamps[-1]
        for sym in list(portfolio.positions.keys()):
            portfolio.close_position(sym, last_price, last_ts)
            portfolio.update_equity({self.symbol: last_price})

        elapsed = time.time() - t0

        # Calculate annualization factor
        tf_hours = {
            "1m": 1/60, "5m": 5/60, "15m": 0.25, "30m": 0.5,
            "1h": 1, "4h": 4, "1d": 24, "1w": 168,
        }
        hours_per_candle = tf_hours.get(self.timeframe, 1)
        periods_per_year = int(8760 / hours_per_candle)

        total_ret = portfolio.total_return()
        mdd = portfolio.max_drawdown()

        return BacktestResult(
            symbol=self.symbol,
            timeframe=self.timeframe,
            strategy_name=strategy.name,
            n_candles=data.n_candles,
            duration_days=days,
            total_return=total_ret,
            total_return_pct=round(total_ret * 100, 2),
            sharpe=portfolio.sharpe_ratio(annualize=periods_per_year),
            sortino=portfolio.sortino_ratio(annualize=periods_per_year),
            max_drawdown=mdd,
            max_drawdown_pct=round(mdd * 100, 2),
            total_trades=portfolio.n_trades,
            win_rate=portfolio.win_rate(),
            win_rate_pct=round(portfolio.win_rate() * 100, 1),
            initial_balance=self.initial_balance,
            final_equity=portfolio.equity_curve[-1] if portfolio.equity_curve else self.initial_balance,
            trades=portfolio.trades,
            equity_curve=portfolio.equity_curve,
            elapsed_seconds=elapsed,
            risk_halts=risk_halts,
            consciousness_halts=consciousness_halts,
        )

    def compare_strategies(
        self,
        strategies: list[Strategy],
        days: int = 30,
        data: Optional[MarketData] = None,
    ) -> list[BacktestResult]:
        """Run multiple strategies on the same data and compare.

        Returns results sorted by Sharpe ratio (descending).
        """
        if data is None:
            data = fetch_ohlcv(
                symbol=self.symbol,
                timeframe=self.timeframe,
                days=days,
            )

        results = []
        for strat in strategies:
            result = self.run(strat, days=days, data=data)
            results.append(result)

        results.sort(key=lambda r: r.sharpe, reverse=True)
        return results


def quick_backtest(
    symbol: str = "BTCUSDT",
    timeframe: str = "1h",
    strategy: Optional[Strategy] = None,
    days: int = 30,
) -> BacktestResult:
    """One-liner convenience function for quick backtesting."""
    from trading.strategy import MACDStrategy
    engine = BacktestEngine(symbol=symbol, timeframe=timeframe)
    return engine.run(strategy or MACDStrategy(), days=days)
