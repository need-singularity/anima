"""Portfolio management — positions, balance, PnL tracking."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class Position:
    """A single position in an asset."""

    symbol: str
    side: str  # "long" or "short"
    entry_price: float
    size: float  # quantity
    entry_time: float = 0.0  # timestamp ms
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

    @property
    def notional(self) -> float:
        """Position notional value at entry."""
        return self.entry_price * self.size

    def pnl(self, current_price: float) -> float:
        """Unrealized PnL at current price."""
        if self.side == "long":
            return (current_price - self.entry_price) * self.size
        else:
            return (self.entry_price - current_price) * self.size

    def pnl_pct(self, current_price: float) -> float:
        """Unrealized PnL as percentage of entry."""
        if self.entry_price == 0:
            return 0.0
        if self.side == "long":
            return (current_price - self.entry_price) / self.entry_price
        else:
            return (self.entry_price - current_price) / self.entry_price

    def should_stop(self, current_price: float) -> bool:
        """Check if stop loss is hit."""
        if self.stop_loss is None:
            return False
        if self.side == "long":
            return current_price <= self.stop_loss
        return current_price >= self.stop_loss

    def should_take_profit(self, current_price: float) -> bool:
        """Check if take profit is hit."""
        if self.take_profit is None:
            return False
        if self.side == "long":
            return current_price >= self.take_profit
        return current_price <= self.take_profit


@dataclass
class Trade:
    """A completed trade."""

    symbol: str
    side: str
    entry_price: float
    exit_price: float
    size: float
    entry_time: float = 0.0
    exit_time: float = 0.0

    @property
    def pnl(self) -> float:
        if self.side == "long":
            return (self.exit_price - self.entry_price) * self.size
        return (self.entry_price - self.exit_price) * self.size

    @property
    def pnl_pct(self) -> float:
        if self.entry_price == 0:
            return 0.0
        if self.side == "long":
            return (self.exit_price - self.entry_price) / self.entry_price
        return (self.entry_price - self.exit_price) / self.entry_price

    @property
    def is_win(self) -> bool:
        return self.pnl > 0


class Portfolio:
    """Portfolio manager with position tracking and PnL calculation.

    Tracks cash balance, open positions, completed trades, and equity curve.
    """

    def __init__(self, initial_balance: float = 10_000.0):
        self.initial_balance = initial_balance
        self.cash = initial_balance
        self.positions: dict[str, Position] = {}  # symbol -> Position
        self.trades: list[Trade] = []
        self.equity_curve: list[float] = [initial_balance]
        self._peak_equity: float = initial_balance

    @property
    def n_trades(self) -> int:
        return len(self.trades)

    @property
    def has_position(self) -> bool:
        return len(self.positions) > 0

    def open_position(
        self,
        symbol: str,
        side: str,
        price: float,
        size: float,
        timestamp: float = 0.0,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
    ) -> bool:
        """Open a new position. Returns True if successful."""
        cost = price * size
        if cost > self.cash:
            logger.debug("Insufficient cash: need %.2f, have %.2f", cost, self.cash)
            return False

        if symbol in self.positions:
            logger.debug("Already have position in %s", symbol)
            return False

        self.cash -= cost
        self.positions[symbol] = Position(
            symbol=symbol,
            side=side,
            entry_price=price,
            size=size,
            entry_time=timestamp,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )
        return True

    def close_position(
        self,
        symbol: str,
        price: float,
        timestamp: float = 0.0,
    ) -> Optional[Trade]:
        """Close an existing position. Returns the completed Trade."""
        pos = self.positions.pop(symbol, None)
        if pos is None:
            return None

        proceeds = price * pos.size
        self.cash += proceeds

        trade = Trade(
            symbol=symbol,
            side=pos.side,
            entry_price=pos.entry_price,
            exit_price=price,
            size=pos.size,
            entry_time=pos.entry_time,
            exit_time=timestamp,
        )
        self.trades.append(trade)
        return trade

    def equity(self, current_prices: dict[str, float] | None = None) -> float:
        """Total equity = cash + unrealized position value."""
        total = self.cash
        if current_prices:
            for sym, pos in self.positions.items():
                price = current_prices.get(sym, pos.entry_price)
                total += price * pos.size
        else:
            for pos in self.positions.values():
                total += pos.entry_price * pos.size
        return total

    def update_equity(self, current_prices: dict[str, float] | None = None):
        """Record equity snapshot."""
        eq = self.equity(current_prices)
        self.equity_curve.append(eq)
        if eq > self._peak_equity:
            self._peak_equity = eq

    def drawdown(self) -> float:
        """Current drawdown from peak."""
        if self._peak_equity == 0:
            return 0.0
        eq = self.equity_curve[-1] if self.equity_curve else self.initial_balance
        return (self._peak_equity - eq) / self._peak_equity

    def max_drawdown(self) -> float:
        """Maximum drawdown over equity curve."""
        if len(self.equity_curve) < 2:
            return 0.0
        curve = np.array(self.equity_curve)
        peak = np.maximum.accumulate(curve)
        dd = (peak - curve) / np.where(peak > 0, peak, 1.0)
        return float(np.max(dd))

    def total_return(self) -> float:
        """Total return as fraction (e.g. 0.15 = 15%)."""
        if self.initial_balance == 0:
            return 0.0
        final = self.equity_curve[-1] if self.equity_curve else self.initial_balance
        return (final - self.initial_balance) / self.initial_balance

    def win_rate(self) -> float:
        """Win rate of completed trades."""
        if not self.trades:
            return 0.0
        wins = sum(1 for t in self.trades if t.is_win)
        return wins / len(self.trades)

    def sharpe_ratio(self, risk_free_rate: float = 0.0, annualize: int = 252) -> float:
        """Sharpe ratio from equity curve returns.

        Args:
            risk_free_rate: Annual risk-free rate.
            annualize: Periods per year (252 for daily, 8760 for hourly).
        """
        if len(self.equity_curve) < 3:
            return 0.0
        curve = np.array(self.equity_curve)
        returns = np.diff(curve) / curve[:-1]
        returns = returns[np.isfinite(returns)]
        if len(returns) < 2:
            return 0.0
        mean_r = np.mean(returns)
        std_r = np.std(returns, ddof=1)
        if std_r < 1e-10:
            return 0.0
        rf_per_period = risk_free_rate / annualize
        return float((mean_r - rf_per_period) / std_r * np.sqrt(annualize))

    def sortino_ratio(self, risk_free_rate: float = 0.0, annualize: int = 252) -> float:
        """Sortino ratio (downside deviation only)."""
        if len(self.equity_curve) < 3:
            return 0.0
        curve = np.array(self.equity_curve)
        returns = np.diff(curve) / curve[:-1]
        returns = returns[np.isfinite(returns)]
        if len(returns) < 2:
            return 0.0
        mean_r = np.mean(returns)
        rf_per_period = risk_free_rate / annualize
        downside = returns[returns < rf_per_period]
        if len(downside) < 1:
            return float(mean_r * np.sqrt(annualize))  # no downside
        down_std = np.std(downside, ddof=1)
        if down_std < 1e-10:
            return 0.0
        return float((mean_r - rf_per_period) / down_std * np.sqrt(annualize))

    def summary(self) -> dict:
        """Summary statistics."""
        return {
            "initial_balance": self.initial_balance,
            "final_equity": round(self.equity_curve[-1], 2) if self.equity_curve else self.initial_balance,
            "total_return_pct": round(self.total_return() * 100, 2),
            "max_drawdown_pct": round(self.max_drawdown() * 100, 2),
            "sharpe": round(self.sharpe_ratio(), 3),
            "sortino": round(self.sortino_ratio(), 3),
            "total_trades": self.n_trades,
            "win_rate_pct": round(self.win_rate() * 100, 1),
            "open_positions": len(self.positions),
            "cash": round(self.cash, 2),
        }
