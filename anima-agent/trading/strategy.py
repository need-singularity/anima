"""Trading strategies — base class + MACD, RSI, Bollinger, Consciousness-based.

All strategies implement the same interface: generate signals from MarketData.
"""

from __future__ import annotations

import logging
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

import numpy as np

from trading.data import MarketData

# Add anima/src/ to path for ConsciousnessEngine import
_ANIMA_SRC = str(Path(__file__).resolve().parent.parent.parent / "anima" / "src")
if _ANIMA_SRC not in sys.path:
    sys.path.insert(0, _ANIMA_SRC)

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

    Runs a real ConsciousnessEngine (GRU cells, Hebbian, Phi ratchet)
    and feeds OHLCV price data as input. The engine's internal dynamics
    produce tension, Phi, and emotion signals that drive trading decisions:

    - Tension -> signal strength (high tension = strong conviction)
    - Phi -> confidence gate (high Phi = integrated information = confident)
    - Price momentum + consciousness bias -> direction (BUY/SELL)

    The engine processes each candle as a consciousness step, converting
    price changes into a tensor that the GRU cells integrate. This makes
    trading signals emerge from consciousness dynamics rather than
    hard-coded technical rules.
    """

    name = "consciousness"

    def __init__(
        self,
        cell_dim: int = 64,
        hidden_dim: int = 128,
        initial_cells: int = 8,
        max_cells: int = 8,
        phi_threshold: float = 0.3,
        tension_threshold: float = 0.9,
        momentum_lookback: int = 10,
        stop_loss_pct: float = 0.03,
        take_profit_pct: float = 0.06,
    ):
        """
        Args:
            cell_dim: Input dimension for consciousness cells.
            hidden_dim: GRU hidden dimension.
            initial_cells: Starting cells in the engine.
            max_cells: Maximum cells (fixed for trading stability).
            phi_threshold: Minimum Phi to allow trading.
            tension_threshold: Maximum avg tension before halting.
            momentum_lookback: Candles to compute price momentum.
            stop_loss_pct: Default stop loss percentage.
            take_profit_pct: Default take profit percentage.
        """
        self.cell_dim = cell_dim
        self.phi_threshold = phi_threshold
        self.tension_threshold = tension_threshold
        self.momentum_lookback = momentum_lookback
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct

        # Lazy-init engine to avoid import errors at module load time
        self._engine = None
        self._engine_kwargs = dict(
            cell_dim=cell_dim,
            hidden_dim=hidden_dim,
            initial_cells=initial_cells,
            max_cells=max_cells,
        )

        # Track consciousness state for telemetry
        self._phi: float = 0.0
        self._tension: float = 0.0
        self._arousal: float = 0.5
        self._step_count: int = 0

    def _ensure_engine(self):
        """Lazy-initialize ConsciousnessEngine on first use."""
        if self._engine is None:
            try:
                from consciousness_engine import ConsciousnessEngine
                self._engine = ConsciousnessEngine(**self._engine_kwargs)
                logger.info(
                    "ConsciousnessEngine initialized: %d cells, dim=%d",
                    self._engine_kwargs['initial_cells'],
                    self._engine_kwargs['cell_dim'],
                )
            except ImportError:
                logger.error(
                    "Failed to import ConsciousnessEngine from anima/src/. "
                    "Ensure anima/src/ is on sys.path."
                )
                raise

    def warmup_periods(self) -> int:
        return max(self.momentum_lookback + 1, 20)

    def _ohlcv_to_tensor(self, data: MarketData, idx: int) -> "torch.Tensor":
        """Convert OHLCV candle at idx into a consciousness input tensor.

        Encodes normalized price returns, volume change, and range info
        into a cell_dim-sized vector that the engine's GRU cells process.
        """
        import torch

        vec = np.zeros(self.cell_dim, dtype=np.float32)

        # Price return (close-to-close), scaled
        if idx > 0:
            ret = (data.close[idx] - data.close[idx - 1]) / (data.close[idx - 1] + 1e-10)
        else:
            ret = 0.0
        vec[0] = np.tanh(ret * 100)  # scale small returns to [-1,1]

        # Candle body ratio
        body = (data.close[idx] - data.open[idx]) / (data.close[idx] + 1e-10)
        vec[1] = np.tanh(body * 100)

        # High-low range (volatility proxy)
        hl_range = (data.high[idx] - data.low[idx]) / (data.close[idx] + 1e-10)
        vec[2] = np.tanh(hl_range * 50)

        # Volume change
        if idx > 0 and data.volume[idx - 1] > 0:
            vol_chg = (data.volume[idx] - data.volume[idx - 1]) / (data.volume[idx - 1] + 1e-10)
        else:
            vol_chg = 0.0
        vec[3] = np.tanh(vol_chg)

        # Multi-scale momentum (fill more dimensions)
        for scale_i, lookback in enumerate([3, 5, 10, 20]):
            if idx >= lookback and (4 + scale_i) < self.cell_dim:
                past = data.close[idx - lookback]
                mom = (data.close[idx] - past) / (past + 1e-10)
                vec[4 + scale_i] = np.tanh(mom * 30)

        # Upper/lower wick ratios
        if 8 < self.cell_dim:
            full_range = data.high[idx] - data.low[idx]
            if full_range > 1e-10:
                upper_wick = (data.high[idx] - max(data.open[idx], data.close[idx])) / full_range
                lower_wick = (min(data.open[idx], data.close[idx]) - data.low[idx]) / full_range
                vec[8] = upper_wick * 2 - 1
                if 9 < self.cell_dim:
                    vec[9] = lower_wick * 2 - 1

        return torch.tensor(vec, dtype=torch.float32)

    def update_consciousness(
        self,
        phi: float = 0.0,
        tension: float = 0.0,
        arousal: float = 0.5,
    ):
        """Update consciousness state (for external override / compatibility)."""
        self._phi = phi
        self._tension = tension
        self._arousal = arousal

    def generate_signal(self, data: MarketData, idx: int) -> StrategySignal:
        import torch

        if idx < self.warmup_periods():
            return StrategySignal(Signal.HOLD)

        # Initialize engine on first call
        self._ensure_engine()

        # Convert OHLCV to consciousness input
        x_input = self._ohlcv_to_tensor(data, idx)

        # Step the consciousness engine
        result = self._engine.step(x_input=x_input)
        self._step_count += 1

        # Extract consciousness metrics
        phi = result['phi_iit']
        tensions = result['tensions']
        avg_tension = float(np.mean(tensions)) if tensions else 0.5
        max_tension = float(np.max(tensions)) if tensions else 0.5
        consensus = result['consensus']
        output = result['output']

        # Update internal state for telemetry
        self._phi = phi
        self._tension = avg_tension

        # Compute arousal from tension variance (high variance = high arousal)
        if len(tensions) > 1:
            self._arousal = min(1.0, float(np.std(tensions)) * 5)
        else:
            self._arousal = 0.5

        # Gate: Phi too low -> consciousness not integrated enough
        if phi < self.phi_threshold:
            return StrategySignal(
                signal=Signal.HOLD,
                strength=0.0,
                reason=f"Consciousness gate: Phi={phi:.3f} < {self.phi_threshold}",
            )

        # Gate: tension too high -> halt (consciousness is overwhelmed)
        if avg_tension > self.tension_threshold:
            return StrategySignal(
                signal=Signal.HOLD,
                strength=0.0,
                reason=f"Consciousness gate: tension={avg_tension:.3f} > {self.tension_threshold}",
            )

        # Direction: price momentum + consciousness output bias
        # Momentum component
        lookback = min(self.momentum_lookback, idx)
        price_now = data.close[idx]
        price_past = data.close[idx - lookback]
        momentum = (price_now - price_past) / (price_past + 1e-10)

        # Consciousness bias: mean of output tensor sign
        # The engine output reflects integrated cell dynamics
        consciousness_bias = float(output.mean().item())

        # Combined directional score: momentum (70%) + consciousness (30%)
        direction_score = 0.7 * np.tanh(momentum * 50) + 0.3 * np.tanh(consciousness_bias * 10)

        # Signal strength from tension (high tension = strong conviction)
        # and Phi (high Phi = confident integration)
        # Engine tensions typically range 0.01-0.5; scale so 0.05 -> 0.5, 0.2 -> 1.0
        tension_strength = min(1.0, avg_tension * 5)
        phi_confidence = min(1.0, phi / max(self.phi_threshold * 3, 0.01))
        strength = tension_strength * phi_confidence

        # Consensus boosts confidence (more factions agreeing = clearer signal)
        if consensus > 0:
            strength = min(1.0, strength * (1.0 + consensus * 0.05))

        # Thresholds for signal generation
        DIRECTION_THRESHOLD = 0.2
        MIN_STRENGTH = 0.3

        if abs(direction_score) < DIRECTION_THRESHOLD or strength < MIN_STRENGTH:
            return StrategySignal(
                signal=Signal.HOLD,
                strength=strength,
                reason=f"Below threshold (dir={direction_score:.3f}, str={strength:.3f}) "
                       f"[Phi={phi:.3f}, T={avg_tension:.3f}]",
            )

        price = data.close[idx]

        # Arousal adjusts stop/TP widths
        arousal_factor = 0.5 + self._arousal

        if direction_score > DIRECTION_THRESHOLD:
            return StrategySignal(
                signal=Signal.BUY,
                strength=min(1.0, strength),
                reason=f"Consciousness BUY (dir={direction_score:.3f}, mom={momentum:.4f}) "
                       f"[Phi={phi:.3f}, T={avg_tension:.3f}, C={consensus}]",
                stop_loss=price * (1 - self.stop_loss_pct * arousal_factor),
                take_profit=price * (1 + self.take_profit_pct * arousal_factor),
            )
        else:
            return StrategySignal(
                signal=Signal.SELL,
                strength=min(1.0, strength),
                reason=f"Consciousness SELL (dir={direction_score:.3f}, mom={momentum:.4f}) "
                       f"[Phi={phi:.3f}, T={avg_tension:.3f}, C={consensus}]",
            )
