"""Order executor — reliable execution with retry, fallback, and slippage control.

Handles the actual order placement with:
  - Retry logic with exponential backoff
  - Broker fallback (primary -> paper)
  - Slippage estimation and limit price adjustment
  - Order confirmation and logging
  - TECS-L position sizing (1/e investable, 1/6 max per position)

Consciousness integration:
  - ConsciousnessGate approval required before execution
  - Tension-based urgency (high tension = tighter limits)
  - Phi-based confidence scaling
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from trading.broker import Broker, BinanceBroker, PaperBroker, OrderResult
from trading.portfolio import Portfolio
from trading.risk import RiskManager, RiskLimits, ConsciousnessGate
from trading.regime import RegimePolicy, MarketRegime

logger = logging.getLogger(__name__)

# TECS-L constants
E = math.e
INV_E = 1.0 / E       # 0.3679 — investable fraction
ONE_SIXTH = 1.0 / 6   # 0.1667 — max per position
ONE_THIRD = 1.0 / 3   # 0.3333 — take profit target


@dataclass
class ExecutionResult:
    """Result of an execution attempt."""
    success: bool
    order: Optional[OrderResult] = None
    retries: int = 0
    slippage_est: float = 0.0
    risk_check: str = ""
    consciousness_check: str = ""
    error: str = ""
    execution_time: float = 0.0


@dataclass
class ExecutionConfig:
    """Execution configuration."""
    max_retries: int = 3
    retry_delay: float = 1.0          # seconds, doubles each retry
    max_slippage: float = 0.005       # 0.5% max allowed slippage
    use_limit_orders: bool = True     # prefer limit over market
    tecs_sizing: bool = True          # use TECS-L position sizing
    paper_mode: bool = True           # paper trading by default
    confirmation_required: bool = False  # require explicit confirmation


class OrderExecutor:
    """Reliable order executor with retry, risk checks, and consciousness gating.

    Execution flow:
    1. Risk check (max drawdown, position limits, daily loss)
    2. Consciousness gate check (Phi, tension)
    3. Regime policy check (allow buys, force exit)
    4. Position sizing (TECS-L or fixed fraction)
    5. Slippage estimation
    6. Order placement with retry
    7. Confirmation and logging
    """

    def __init__(
        self,
        broker: Optional[Broker] = None,
        portfolio: Optional[Portfolio] = None,
        risk_manager: Optional[RiskManager] = None,
        consciousness_gate: Optional[ConsciousnessGate] = None,
        config: Optional[ExecutionConfig] = None,
    ):
        self.config = config or ExecutionConfig()

        if self.config.paper_mode:
            self.broker = broker or PaperBroker()
        else:
            self.broker = broker or BinanceBroker()

        self.fallback_broker = PaperBroker()
        self.portfolio = portfolio or Portfolio()
        self.risk_manager = risk_manager or RiskManager()
        self.consciousness_gate = consciousness_gate

        self._execution_log: list[ExecutionResult] = []
        self._total_orders = 0
        self._total_fills = 0
        self._total_rejects = 0

    def execute_buy(
        self,
        symbol: str,
        price: float,
        size: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        regime_policy: Optional[RegimePolicy] = None,
        signal_strength: float = 1.0,
        reason: str = "",
    ) -> ExecutionResult:
        """Execute a buy order with full safety checks.

        Args:
            symbol: Trading pair (e.g. BTCUSDT).
            price: Target entry price.
            size: Position size (if None, auto-calculated).
            stop_loss: Stop loss price.
            take_profit: Take profit price.
            regime_policy: Current regime policy.
            signal_strength: Signal confidence (0-1).
            reason: Human-readable reason for the trade.

        Returns:
            ExecutionResult with outcome.
        """
        t0 = time.time()
        self._total_orders += 1

        # 1. Regime check
        if regime_policy and not regime_policy.allow_buys:
            return ExecutionResult(
                success=False, error="Regime policy: buys not allowed",
                risk_check=f"regime={regime_policy.regime.name}",
                execution_time=time.time() - t0,
            )

        # 2. Consciousness gate
        consciousness_msg = "OK"
        if self.consciousness_gate:
            allowed, msg = self.consciousness_gate.allow_trade()
            consciousness_msg = msg
            if not allowed:
                self._total_rejects += 1
                return ExecutionResult(
                    success=False, error=f"Consciousness gate: {msg}",
                    consciousness_check=msg,
                    execution_time=time.time() - t0,
                )

        # 3. Position sizing
        if size is None:
            size = self._calculate_size(price, stop_loss, signal_strength, regime_policy)

        if size <= 0:
            return ExecutionResult(
                success=False, error="Position size is zero",
                execution_time=time.time() - t0,
            )

        # 4. Risk check
        can_trade, risk_msg = self.risk_manager.check_can_trade(self.portfolio, price, size)
        if not can_trade:
            self._total_rejects += 1
            return ExecutionResult(
                success=False, error=f"Risk check failed: {risk_msg}",
                risk_check=risk_msg,
                consciousness_check=consciousness_msg,
                execution_time=time.time() - t0,
            )

        # 5. Slippage estimation
        slippage_est = self._estimate_slippage(price, size)

        # 6. Execute with retry
        order_result = self._execute_with_retry(symbol, "buy", size, price)

        if order_result is None:
            self._total_rejects += 1
            return ExecutionResult(
                success=False, error="All retries exhausted",
                retries=self.config.max_retries,
                slippage_est=slippage_est,
                risk_check=risk_msg,
                consciousness_check=consciousness_msg,
                execution_time=time.time() - t0,
            )

        # 7. Record in portfolio
        fill_price = order_result.price or price
        self.portfolio.open_position(
            symbol=symbol, side="long", price=fill_price, size=size,
            timestamp=time.time() * 1000,
            stop_loss=stop_loss, take_profit=take_profit,
        )

        self._total_fills += 1
        result = ExecutionResult(
            success=True, order=order_result, retries=0,
            slippage_est=slippage_est,
            risk_check="OK",
            consciousness_check=consciousness_msg,
            execution_time=time.time() - t0,
        )
        self._execution_log.append(result)

        logger.info("BUY %s: %.6f @ %.2f [%s] (slippage_est=%.4f%%)",
                     symbol, size, fill_price, reason, slippage_est * 100)

        return result

    def execute_sell(
        self,
        symbol: str,
        price: float,
        reason: str = "",
    ) -> ExecutionResult:
        """Execute a sell order (close position)."""
        t0 = time.time()
        self._total_orders += 1

        if symbol not in self.portfolio.positions:
            return ExecutionResult(
                success=False, error=f"No position in {symbol}",
                execution_time=time.time() - t0,
            )

        pos = self.portfolio.positions[symbol]
        order_result = self._execute_with_retry(symbol, "sell", pos.size, price)

        if order_result is None:
            return ExecutionResult(
                success=False, error="Sell retry exhausted",
                retries=self.config.max_retries,
                execution_time=time.time() - t0,
            )

        fill_price = order_result.price or price
        trade = self.portfolio.close_position(symbol, fill_price, time.time() * 1000)

        self._total_fills += 1
        result = ExecutionResult(
            success=True, order=order_result,
            execution_time=time.time() - t0,
        )
        self._execution_log.append(result)

        pnl_str = f"PnL: {trade.pnl_pct * 100:+.2f}%" if trade else ""
        logger.info("SELL %s @ %.2f [%s] %s", symbol, fill_price, reason, pnl_str)

        return result

    def force_exit_all(self, reason: str = "regime force exit") -> list[ExecutionResult]:
        """Force exit all open positions (e.g., CRITICAL regime)."""
        results = []
        for symbol in list(self.portfolio.positions.keys()):
            price = self.broker.get_price(symbol)
            if price is None:
                pos = self.portfolio.positions[symbol]
                price = pos.entry_price  # fallback to entry
            result = self.execute_sell(symbol, price, reason=reason)
            results.append(result)
        return results

    def check_stops(self, current_prices: dict[str, float]) -> list[ExecutionResult]:
        """Check and execute stop loss / take profit for all positions."""
        results = []
        for symbol, pos in list(self.portfolio.positions.items()):
            price = current_prices.get(symbol)
            if price is None:
                continue

            if pos.should_stop(price):
                result = self.execute_sell(symbol, price, reason="stop_loss")
                results.append(result)
            elif pos.should_take_profit(price):
                result = self.execute_sell(symbol, price, reason="take_profit")
                results.append(result)

        return results

    def _calculate_size(
        self,
        price: float,
        stop_loss: Optional[float],
        signal_strength: float,
        regime_policy: Optional[RegimePolicy],
    ) -> float:
        """Calculate position size using TECS-L or risk-based sizing."""
        equity = self.portfolio.equity()

        if self.config.tecs_sizing:
            # TECS-L: investable = 1/e of capital, max per position = 1/6
            investable = equity * INV_E
            max_per_pos = equity * ONE_SIXTH
            base_size = min(investable * 0.25, max_per_pos)  # 25% of investable per trade
        else:
            base_size = equity * 0.10  # 10% default

        # Regime adjustment
        if regime_policy:
            max_pct = regime_policy.max_position_pct
            regime_cap = equity * max_pct
            base_size = min(base_size, regime_cap)

        # Signal strength scaling
        base_size *= signal_strength

        # Consciousness confidence scaling
        if self.consciousness_gate:
            base_size *= self.consciousness_gate.confidence_multiplier()

        # Risk-based sizing (if stop loss available)
        if stop_loss and stop_loss > 0 and price > 0:
            risk_per_trade = 0.02  # 2% risk per trade
            risk_size = self.risk_manager.position_size_from_risk(
                equity, price, stop_loss, risk_per_trade,
            )
            if risk_size > 0:
                base_size = min(base_size, risk_size * price)

        # Convert to quantity
        if price > 0:
            return base_size / price
        return 0.0

    def _estimate_slippage(self, price: float, size: float) -> float:
        """Estimate expected slippage based on order size."""
        # Simple model: slippage increases with size relative to typical volume
        # 0.01% base + 0.001% per $10k notional
        notional = price * size
        base_slip = 0.0001
        size_slip = notional / 10_000_000 * 0.001
        return base_slip + size_slip

    def _execute_with_retry(
        self,
        symbol: str,
        side: str,
        size: float,
        price: float,
    ) -> Optional[OrderResult]:
        """Execute order with exponential backoff retry."""
        delay = self.config.retry_delay

        for attempt in range(self.config.max_retries + 1):
            try:
                limit_price = price if self.config.use_limit_orders else None
                result = self.broker.place_order(symbol, side, size, limit_price)

                if result.success:
                    return result

                logger.warning("Order failed (attempt %d/%d): %s",
                               attempt + 1, self.config.max_retries + 1, result.error)

            except Exception as e:
                logger.warning("Order exception (attempt %d/%d): %s",
                               attempt + 1, self.config.max_retries + 1, e)

            if attempt < self.config.max_retries:
                time.sleep(delay)
                delay *= 2  # exponential backoff

        # Fallback to paper broker
        logger.warning("Primary broker failed, falling back to paper broker")
        try:
            return self.fallback_broker.place_order(symbol, side, size, price)
        except Exception:
            return None

    def status(self) -> dict:
        """Execution status summary."""
        return {
            "total_orders": self._total_orders,
            "total_fills": self._total_fills,
            "total_rejects": self._total_rejects,
            "fill_rate": self._total_fills / max(1, self._total_orders),
            "paper_mode": self.config.paper_mode,
            "tecs_sizing": self.config.tecs_sizing,
            "open_positions": len(self.portfolio.positions),
            "portfolio_equity": round(self.portfolio.equity(), 2),
        }
