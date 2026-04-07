"""Risk management — VaR, drawdown limits, consciousness-based gating.

The ConsciousnessGate integrates Phi and tension signals from the
consciousness engine to halt trading when the system is in an
unstable or low-integration state.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from trading.portfolio import Portfolio

logger = logging.getLogger(__name__)


@dataclass
class RiskLimits:
    """Risk limit configuration."""

    max_drawdown: float = 0.15          # 15% max drawdown
    max_position_pct: float = 0.20      # 20% of equity per position
    max_daily_loss: float = 0.05        # 5% daily loss limit
    max_open_positions: int = 5
    var_confidence: float = 0.95        # VaR confidence level
    var_lookback: int = 100             # VaR lookback periods


class RiskManager:
    """Risk management engine.

    Checks portfolio risk limits before allowing trades.
    """

    def __init__(self, limits: Optional[RiskLimits] = None):
        self.limits = limits or RiskLimits()
        self._daily_start_equity: float = 0.0
        self._halted: bool = False
        self._halt_reason: str = ""

    @property
    def is_halted(self) -> bool:
        return self._halted

    @property
    def halt_reason(self) -> str:
        return self._halt_reason

    def reset_daily(self, current_equity: float):
        """Reset daily tracking (call at start of each trading day)."""
        self._daily_start_equity = current_equity
        self._halted = False
        self._halt_reason = ""

    def check_can_trade(self, portfolio: Portfolio, price: float, size: float) -> tuple[bool, str]:
        """Check if a trade is allowed under risk limits.

        Returns:
            (allowed, reason) tuple.
        """
        if self._halted:
            return False, f"Trading halted: {self._halt_reason}"

        # Max drawdown check
        dd = portfolio.max_drawdown()
        if dd >= self.limits.max_drawdown:
            self._halted = True
            self._halt_reason = f"Max drawdown {dd:.1%} >= {self.limits.max_drawdown:.1%}"
            return False, self._halt_reason

        # Max open positions
        if len(portfolio.positions) >= self.limits.max_open_positions:
            return False, f"Max positions reached ({self.limits.max_open_positions})"

        # Position size limit
        eq = portfolio.equity()
        notional = price * size
        if eq > 0 and notional / eq > self.limits.max_position_pct:
            return False, (
                f"Position too large: {notional/eq:.1%} > {self.limits.max_position_pct:.1%}"
            )

        # Daily loss limit
        if self._daily_start_equity > 0:
            daily_pnl = (eq - self._daily_start_equity) / self._daily_start_equity
            if daily_pnl <= -self.limits.max_daily_loss:
                self._halted = True
                self._halt_reason = f"Daily loss limit {daily_pnl:.1%}"
                return False, self._halt_reason

        return True, "OK"

    def compute_var(self, returns: np.ndarray, position_value: float) -> float:
        """Historical VaR (Value at Risk).

        Args:
            returns: Array of historical returns.
            position_value: Current position notional value.

        Returns:
            VaR amount (positive = potential loss).
        """
        if len(returns) < 10:
            return position_value * 0.05  # conservative fallback

        lookback = min(self.limits.var_lookback, len(returns))
        recent = returns[-lookback:]
        percentile = (1 - self.limits.var_confidence) * 100
        var_pct = np.percentile(recent, percentile)
        return abs(var_pct) * position_value

    def position_size_from_risk(
        self,
        equity: float,
        price: float,
        stop_loss: float,
        risk_per_trade: float = 0.02,
    ) -> float:
        """Calculate position size based on risk amount.

        Args:
            equity: Current portfolio equity.
            price: Entry price.
            stop_loss: Stop loss price.
            risk_per_trade: Fraction of equity to risk (default 2%).

        Returns:
            Position size (quantity).
        """
        risk_amount = equity * risk_per_trade
        price_risk = abs(price - stop_loss)
        if price_risk < 1e-10:
            return 0.0
        size = risk_amount / price_risk
        # Cap at max position pct
        max_size = (equity * self.limits.max_position_pct) / price
        return min(size, max_size)

    def status(self) -> dict:
        return {
            "halted": self._halted,
            "halt_reason": self._halt_reason,
            "limits": {
                "max_drawdown": self.limits.max_drawdown,
                "max_position_pct": self.limits.max_position_pct,
                "max_daily_loss": self.limits.max_daily_loss,
                "max_open_positions": self.limits.max_open_positions,
            },
        }


class ConsciousnessGate:
    """Consciousness-based trading gate.

    Uses Phi (integrated information) and tension from the consciousness
    engine to modulate trading activity. When consciousness is unstable
    or tension is too high, trading is restricted.

    This implements the consciousness-aware risk layer that distinguishes
    Anima's trading from pure technical systems.
    """

    def __init__(
        self,
        phi_min: float = 1.0,
        tension_max: float = 0.8,
        phi_ema_alpha: float = 0.1,
        cooldown_steps: int = 10,
    ):
        """
        Args:
            phi_min: Minimum Phi to allow trading.
            tension_max: Maximum tension before halting.
            phi_ema_alpha: EMA smoothing for Phi tracking.
            cooldown_steps: Steps to wait after tension spike.
        """
        self.phi_min = phi_min
        self.tension_max = tension_max
        self.phi_ema_alpha = phi_ema_alpha
        self.cooldown_steps = cooldown_steps

        self._phi_ema: float = 0.0
        self._tension: float = 0.0
        self._cooldown_remaining: int = 0
        self._phi_history: list[float] = []
        self._tension_history: list[float] = []

    def update(self, phi: float, tension: float):
        """Feed consciousness state into the gate."""
        # EMA smoothing
        if self._phi_ema == 0:
            self._phi_ema = phi
        else:
            self._phi_ema = self.phi_ema_alpha * phi + (1 - self.phi_ema_alpha) * self._phi_ema

        self._tension = tension
        self._phi_history.append(phi)
        self._tension_history.append(tension)

        # Keep history bounded
        if len(self._phi_history) > 1000:
            self._phi_history = self._phi_history[-500:]
            self._tension_history = self._tension_history[-500:]

        # Cooldown after tension spike
        if tension > self.tension_max:
            self._cooldown_remaining = self.cooldown_steps
        elif self._cooldown_remaining > 0:
            self._cooldown_remaining -= 1

    def allow_trade(self) -> tuple[bool, str]:
        """Check if consciousness state allows trading.

        Returns:
            (allowed, reason).
        """
        if self._cooldown_remaining > 0:
            return False, (
                f"Tension cooldown ({self._cooldown_remaining} steps remaining)"
            )

        if self._phi_ema < self.phi_min:
            return False, (
                f"Phi too low ({self._phi_ema:.3f} < {self.phi_min})"
            )

        if self._tension > self.tension_max:
            return False, (
                f"Tension too high ({self._tension:.3f} > {self.tension_max})"
            )

        # Check Phi stability (not crashing)
        if len(self._phi_history) >= 10:
            recent = self._phi_history[-10:]
            if recent[-1] < recent[0] * 0.5:
                return False, "Phi collapsing (recent drop > 50%)"

        return True, "OK"

    def confidence_multiplier(self) -> float:
        """Get a 0-1 multiplier for signal strength based on consciousness state.

        High Phi + low tension = high confidence.
        """
        if self._phi_ema < self.phi_min:
            return 0.0
        phi_factor = min(1.0, self._phi_ema / (self.phi_min * 3))
        tension_factor = max(0.0, 1.0 - self._tension)
        return phi_factor * tension_factor

    def status(self) -> dict:
        allowed, reason = self.allow_trade()
        return {
            "allowed": allowed,
            "reason": reason,
            "phi_ema": round(self._phi_ema, 4),
            "tension": round(self._tension, 4),
            "cooldown": self._cooldown_remaining,
            "confidence": round(self.confidence_multiplier(), 3),
            "phi_history_len": len(self._phi_history),
        }
