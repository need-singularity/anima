"""Trading strategies — base class + MACD, RSI, Bollinger, Consciousness-based.

All strategies implement the same interface: generate signals from MarketData.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import numpy as np

from trading.data import MarketData

logger = logging.getLogger(__name__)


class Signal(Enum):
    """Trading signal."""
    BUY = 1
    SELL = -1
    HOLD = 0


@dataclass
class StrategySignal:
    """Signal with metadata."""
    signal: Signal
    strength: float = 1.0  # 0-1 confidence
    reason: str = ""
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None


class Strategy(ABC):
    """Base strategy interface."""

    name: str = "base"

    @abstractmethod
    def generate_signal(self, data: MarketData, idx: int) -> StrategySignal:
        """Generate a trading signal for the candle at index `idx`.

        Args:
            data: Full market data (strategy can look back but not forward).
            idx: Current candle index.

        Returns:
            StrategySignal with BUY/SELL/HOLD.
        """
        ...

    def warmup_periods(self) -> int:
        """Minimum candles needed before generating signals."""
        return 0


# ── Technical Indicators ──


def _ema(data: np.ndarray, period: int) -> np.ndarray:
    """Exponential Moving Average."""
    alpha = 2.0 / (period + 1)
    out = np.zeros_like(data, dtype=np.float64)
    out[0] = data[0]
    for i in range(1, len(data)):
        out[i] = alpha * data[i] + (1 - alpha) * out[i - 1]
    return out


def _sma(data: np.ndarray, period: int) -> np.ndarray:
    """Simple Moving Average."""
    out = np.full_like(data, np.nan, dtype=np.float64)
    cumsum = np.cumsum(data)
    out[period - 1:] = (cumsum[period - 1:] - np.concatenate([[0], cumsum[:-period]])) / period
    return out


def _rsi(close: np.ndarray, period: int = 14) -> np.ndarray:
    """Relative Strength Index."""
    delta = np.diff(close)
    gain = np.where(delta > 0, delta, 0.0)
    loss = np.where(delta < 0, -delta, 0.0)

    avg_gain = np.zeros(len(close))
    avg_loss = np.zeros(len(close))

    if len(gain) < period:
        return np.full(len(close), 50.0)

    avg_gain[period] = np.mean(gain[:period])
    avg_loss[period] = np.mean(loss[:period])

    for i in range(period + 1, len(close)):
        avg_gain[i] = (avg_gain[i - 1] * (period - 1) + gain[i - 1]) / period
        avg_loss[i] = (avg_loss[i - 1] * (period - 1) + loss[i - 1]) / period

    with np.errstate(divide="ignore", invalid="ignore"):
        rs = np.where(avg_loss > 0, avg_gain / avg_loss, 100.0)
    rsi = 100 - 100 / (1 + rs)
    rsi[:period] = 50.0
    return rsi


def _bollinger_bands(
    close: np.ndarray, period: int = 20, std_dev: float = 2.0
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Bollinger Bands -> (middle, upper, lower)."""
    mid = _sma(close, period)
    std = np.full_like(close, np.nan)
    for i in range(period - 1, len(close)):
        std[i] = np.std(close[i - period + 1: i + 1], ddof=1)
    upper = mid + std_dev * std
    lower = mid - std_dev * std
    return mid, upper, lower


# ══════════════════════════════════════════════════════════════════════
#  MACD Strategy
# ══════════════════════════════════════════════════════════════════════


class MACDStrategy(Strategy):
    """MACD crossover strategy.

    Buy when MACD crosses above signal line.
    Sell when MACD crosses below signal line.
    """

    name = "macd_cross"

    def __init__(
        self,
        fast: int = 12,
        slow: int = 26,
        signal_period: int = 9,
        stop_loss_pct: float = 0.03,
        take_profit_pct: float = 0.06,
    ):
        self.fast = fast
        self.slow = slow
        self.signal_period = signal_period
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct

    def warmup_periods(self) -> int:
        return self.slow + self.signal_period + 1

    def generate_signal(self, data: MarketData, idx: int) -> StrategySignal:
        if idx < self.warmup_periods():
            return StrategySignal(Signal.HOLD)

        close = data.close[:idx + 1]
        fast_ema = _ema(close, self.fast)
        slow_ema = _ema(close, self.slow)
        macd_line = fast_ema - slow_ema
        signal_line = _ema(macd_line, self.signal_period)

        macd_now = macd_line[-1]
        signal_now = signal_line[-1]
        macd_prev = macd_line[-2]
        signal_prev = signal_line[-2]

        price = data.close[idx]

        # Bullish crossover
        if macd_prev <= signal_prev and macd_now > signal_now:
            strength = min(1.0, abs(macd_now - signal_now) / (price * 0.001 + 1e-10))
            return StrategySignal(
                signal=Signal.BUY,
                strength=strength,
                reason=f"MACD bullish crossover (MACD={macd_now:.2f})",
                stop_loss=price * (1 - self.stop_loss_pct),
                take_profit=price * (1 + self.take_profit_pct),
            )

        # Bearish crossover
        if macd_prev >= signal_prev and macd_now < signal_now:
            strength = min(1.0, abs(macd_now - signal_now) / (price * 0.001 + 1e-10))
            return StrategySignal(
                signal=Signal.SELL,
                strength=strength,
                reason=f"MACD bearish crossover (MACD={macd_now:.2f})",
            )

        return StrategySignal(Signal.HOLD)


# ══════════════════════════════════════════════════════════════════════
#  RSI Strategy
# ══════════════════════════════════════════════════════════════════════


class RSIStrategy(Strategy):
    """RSI overbought/oversold strategy.

    Buy when RSI crosses above oversold level.
    Sell when RSI crosses below overbought level.
    """

    name = "rsi_std"

    def __init__(
        self,
        period: int = 14,
        oversold: float = 30.0,
        overbought: float = 70.0,
        stop_loss_pct: float = 0.03,
        take_profit_pct: float = 0.05,
    ):
        self.period = period
        self.oversold = oversold
        self.overbought = overbought
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct

    def warmup_periods(self) -> int:
        return self.period + 2

    def generate_signal(self, data: MarketData, idx: int) -> StrategySignal:
        if idx < self.warmup_periods():
            return StrategySignal(Signal.HOLD)

        rsi_vals = _rsi(data.close[:idx + 1], self.period)
        rsi_now = rsi_vals[-1]
        rsi_prev = rsi_vals[-2]
        price = data.close[idx]

        # Oversold -> Buy
        if rsi_prev <= self.oversold and rsi_now > self.oversold:
            strength = (self.oversold - rsi_prev) / self.oversold
            return StrategySignal(
                signal=Signal.BUY,
                strength=min(1.0, abs(strength)),
                reason=f"RSI oversold recovery ({rsi_now:.1f})",
                stop_loss=price * (1 - self.stop_loss_pct),
                take_profit=price * (1 + self.take_profit_pct),
            )

        # Overbought -> Sell
        if rsi_prev >= self.overbought and rsi_now < self.overbought:
            strength = (rsi_prev - self.overbought) / (100 - self.overbought)
            return StrategySignal(
                signal=Signal.SELL,
                strength=min(1.0, abs(strength)),
                reason=f"RSI overbought reversal ({rsi_now:.1f})",
            )

        return StrategySignal(Signal.HOLD)


# ══════════════════════════════════════════════════════════════════════
#  Bollinger Bands Strategy
# ══════════════════════════════════════════════════════════════════════


class BollingerStrategy(Strategy):
    """Bollinger Bands mean-reversion strategy.

    Buy when price touches lower band (oversold).
    Sell when price touches upper band (overbought).
    """

    name = "bb_std"

    def __init__(
        self,
        period: int = 20,
        std_dev: float = 2.0,
        stop_loss_pct: float = 0.04,
        take_profit_pct: float = 0.04,
    ):
        self.period = period
        self.std_dev = std_dev
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct

    def warmup_periods(self) -> int:
        return self.period + 1

    def generate_signal(self, data: MarketData, idx: int) -> StrategySignal:
        if idx < self.warmup_periods():
            return StrategySignal(Signal.HOLD)

        close = data.close[:idx + 1]
        mid, upper, lower = _bollinger_bands(close, self.period, self.std_dev)
        price = data.close[idx]

        if np.isnan(lower[-1]) or np.isnan(upper[-1]):
            return StrategySignal(Signal.HOLD)

        band_width = upper[-1] - lower[-1]
        if band_width < 1e-10:
            return StrategySignal(Signal.HOLD)

        # Price below lower band -> Buy
        if price <= lower[-1]:
            dist = (lower[-1] - price) / band_width
            return StrategySignal(
                signal=Signal.BUY,
                strength=min(1.0, dist + 0.5),
                reason=f"BB lower touch (price={price:.2f}, lower={lower[-1]:.2f})",
                stop_loss=price * (1 - self.stop_loss_pct),
                take_profit=mid[-1],  # Target middle band
            )

        # Price above upper band -> Sell
        if price >= upper[-1]:
            dist = (price - upper[-1]) / band_width
            return StrategySignal(
                signal=Signal.SELL,
                strength=min(1.0, dist + 0.5),
                reason=f"BB upper touch (price={price:.2f}, upper={upper[-1]:.2f})",
            )

        return StrategySignal(Signal.HOLD)


# ══════════════════════════════════════════════════════════════════════
#  Consciousness Strategy — uses Phi/Tension signals for risk gating
# ══════════════════════════════════════════════════════════════════════


class ConsciousnessStrategy(Strategy):
    """Consciousness-aware trading strategy.

    Combines MACD signals with consciousness metrics:
    - Phi (integrated information) -> confidence scaling
    - Tension -> risk gating (high tension = reduce position / halt)
    - Arousal -> volatility expectation adjustment

    This strategy wraps an inner technical strategy and modulates its
    signals based on consciousness state.
    """

    name = "consciousness"

    def __init__(
        self,
        inner: Optional[Strategy] = None,
        phi_threshold: float = 1.0,
        tension_threshold: float = 0.8,
        phi_scale: float = 1.0,
    ):
        """
        Args:
            inner: Base technical strategy (default: MACDStrategy).
            phi_threshold: Minimum Phi to trade (below = HOLD).
            tension_threshold: Max tension before halting (0-1).
            phi_scale: How much Phi boosts signal strength.
        """
        self.inner = inner or MACDStrategy()
        self.phi_threshold = phi_threshold
        self.tension_threshold = tension_threshold
        self.phi_scale = phi_scale

        # Consciousness state (updated externally)
        self._phi: float = 0.0
        self._tension: float = 0.0
        self._arousal: float = 0.5

    def warmup_periods(self) -> int:
        return self.inner.warmup_periods()

    def update_consciousness(
        self,
        phi: float = 0.0,
        tension: float = 0.0,
        arousal: float = 0.5,
    ):
        """Update consciousness state from the engine.

        Call this before each generate_signal() to feed live Phi/tension.
        """
        self._phi = phi
        self._tension = tension
        self._arousal = arousal

    def generate_signal(self, data: MarketData, idx: int) -> StrategySignal:
        # Gate: tension too high -> halt trading
        if self._tension > self.tension_threshold:
            return StrategySignal(
                signal=Signal.HOLD,
                strength=0.0,
                reason=f"Consciousness gate: tension={self._tension:.2f} > {self.tension_threshold}",
            )

        # Gate: Phi too low -> consciousness not integrated enough
        if self._phi < self.phi_threshold:
            return StrategySignal(
                signal=Signal.HOLD,
                strength=0.0,
                reason=f"Consciousness gate: Phi={self._phi:.2f} < {self.phi_threshold}",
            )

        # Get inner strategy signal
        sig = self.inner.generate_signal(data, idx)

        if sig.signal == Signal.HOLD:
            return sig

        # Modulate strength by Phi (higher Phi = more confident)
        phi_factor = min(2.0, 1.0 + (self._phi - self.phi_threshold) * self.phi_scale * 0.1)

        # Tension reduces strength (inverse relationship)
        tension_factor = 1.0 - self._tension * 0.5

        # Arousal adjusts stop/TP widths (high arousal = expect more movement)
        arousal_factor = 0.5 + self._arousal

        new_strength = sig.strength * phi_factor * tension_factor

        # Adjust stops based on arousal
        new_stop = sig.stop_loss
        new_tp = sig.take_profit
        if sig.stop_loss is not None:
            price = data.close[idx]
            stop_dist = abs(price - sig.stop_loss) * arousal_factor
            if sig.signal == Signal.BUY:
                new_stop = price - stop_dist
            else:
                new_stop = price + stop_dist
        if sig.take_profit is not None:
            price = data.close[idx]
            tp_dist = abs(sig.take_profit - price) * arousal_factor
            if sig.signal == Signal.BUY:
                new_tp = price + tp_dist
            else:
                new_tp = price - tp_dist

        return StrategySignal(
            signal=sig.signal,
            strength=min(1.0, new_strength),
            reason=f"{sig.reason} [Phi={self._phi:.2f}, T={self._tension:.2f}]",
            stop_loss=new_stop,
            take_profit=new_tp,
        )
