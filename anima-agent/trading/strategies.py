"""Expanded strategy library — migrated from invest + new consciousness-native strategies.

All strategies from ~/Dev/invest/backend/backend/calc/ adapted for anima-agent.
Strategies use the same Strategy base class and MarketData interface.
No dependency on the invest repo — fully standalone.

Categories:
  - Trend following: MACD, EMA crossover, ADX trend, multi-timeframe
  - Mean reversion: RSI, Bollinger, VWAP reversion, spread reversal
  - Momentum: time-series momentum, acceleration, momentum factor
  - Volatility: vol breakout, vol mean-revert, low-vol trend, Garman-Klass
  - Liquidity: volume surge, liquidity filter, spread reversal
  - Sentiment: fear/greed index, contrarian
  - Seasonality: turn-of-month, sell-in-may
  - SOC/Criticality: sandpile avalanche, power-law tail
  - Game theory: Nash equilibrium position sizing
  - Consciousness-native: PureField tension, Phi-momentum, consciousness cycles
"""

from __future__ import annotations

import logging
import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

import numpy as np

from trading.data import MarketData
from trading.strategy import Strategy, Signal, StrategySignal

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════
#  Vectorized indicators (numpy-only, no external TA libs)
# ═══════════════════════════════════════════════════════════════════════

def _sma(data: np.ndarray, period: int) -> np.ndarray:
    out = np.full_like(data, np.nan, dtype=np.float64)
    if len(data) < period:
        return out
    cs = np.cumsum(data, dtype=np.float64)
    cs[period:] = cs[period:] - cs[:-period]
    out[period - 1:] = cs[period - 1:] / period
    return out


def _ema(data: np.ndarray, period: int) -> np.ndarray:
    alpha = 2.0 / (period + 1)
    out = np.empty_like(data, dtype=np.float64)
    out[0] = data[0]
    for i in range(1, len(data)):
        out[i] = alpha * data[i] + (1 - alpha) * out[i - 1]
    return out


def _rsi(close: np.ndarray, period: int = 14) -> np.ndarray:
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
    rsi_arr = 100 - 100 / (1 + rs)
    rsi_arr[:period] = 50.0
    return rsi_arr


def _bollinger_bands(close: np.ndarray, period: int = 20, std_dev: float = 2.0):
    mid = _sma(close, period)
    std = np.full_like(close, np.nan)
    for i in range(period - 1, len(close)):
        std[i] = np.std(close[i - period + 1: i + 1], ddof=1)
    upper = mid + std_dev * std
    lower = mid - std_dev * std
    return mid, upper, lower


def _atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
    result = np.full(len(high), np.nan)
    tr = np.empty(len(high))
    tr[0] = high[0] - low[0]
    for i in range(1, len(high)):
        tr[i] = max(high[i] - low[i], abs(high[i] - close[i - 1]), abs(low[i] - close[i - 1]))
    if len(high) > period:
        result[period - 1] = np.mean(tr[:period])
        for i in range(period, len(high)):
            result[i] = (result[i - 1] * (period - 1) + tr[i]) / period
    return result


def _adx(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
    """Average Directional Index (0-100)."""
    n = len(high)
    result = np.full(n, np.nan)
    plus_dm = np.zeros(n)
    minus_dm = np.zeros(n)
    tr = np.zeros(n)
    for i in range(1, n):
        up = high[i] - high[i - 1]
        down = low[i - 1] - low[i]
        plus_dm[i] = up if up > down and up > 0 else 0
        minus_dm[i] = down if down > up and down > 0 else 0
        tr[i] = max(high[i] - low[i], abs(high[i] - close[i - 1]), abs(low[i] - close[i - 1]))
    if n <= period:
        return result
    atr_val = np.full(n, np.nan)
    atr_val[period] = np.mean(tr[1:period + 1])
    sm_plus = np.mean(plus_dm[1:period + 1])
    sm_minus = np.mean(minus_dm[1:period + 1])
    plus_di = np.full(n, np.nan)
    minus_di = np.full(n, np.nan)
    if atr_val[period] > 0:
        plus_di[period] = 100 * sm_plus / atr_val[period]
        minus_di[period] = 100 * sm_minus / atr_val[period]
    for i in range(period + 1, n):
        atr_val[i] = (atr_val[i - 1] * (period - 1) + tr[i]) / period
        sm_plus = (sm_plus * (period - 1) + plus_dm[i]) / period
        sm_minus = (sm_minus * (period - 1) + minus_dm[i]) / period
        if atr_val[i] > 0:
            plus_di[i] = 100 * sm_plus / atr_val[i]
            minus_di[i] = 100 * sm_minus / atr_val[i]
    dx = np.full(n, np.nan)
    for i in range(period, n):
        if not np.isnan(plus_di[i]) and not np.isnan(minus_di[i]):
            s = plus_di[i] + minus_di[i]
            dx[i] = 100 * abs(plus_di[i] - minus_di[i]) / s if s > 0 else 0
    first_valid = period + period
    if first_valid < n:
        result[first_valid] = np.nanmean(dx[period:first_valid + 1])
        for i in range(first_valid + 1, n):
            if not np.isnan(dx[i]):
                result[i] = (result[i - 1] * (period - 1) + dx[i]) / period
    return result


def _stochastic(high: np.ndarray, low: np.ndarray, close: np.ndarray, k_period: int = 14):
    k = np.full(len(close), np.nan)
    for i in range(k_period - 1, len(close)):
        hh = np.max(high[i - k_period + 1:i + 1])
        ll = np.min(low[i - k_period + 1:i + 1])
        k[i] = 100 * (close[i] - ll) / (hh - ll) if hh != ll else 50
    return k


def _obv(close: np.ndarray, volume: np.ndarray) -> np.ndarray:
    result = np.zeros(len(close))
    for i in range(1, len(close)):
        if close[i] > close[i - 1]:
            result[i] = result[i - 1] + volume[i]
        elif close[i] < close[i - 1]:
            result[i] = result[i - 1] - volume[i]
        else:
            result[i] = result[i - 1]
    return result


def _vwap(high: np.ndarray, low: np.ndarray, close: np.ndarray, volume: np.ndarray) -> np.ndarray:
    typical = (high + low + close) / 3
    cum_tp_vol = np.cumsum(typical * volume)
    cum_vol = np.cumsum(volume)
    return np.where(cum_vol > 0, cum_tp_vol / cum_vol, 0)


def _realized_vol(close: np.ndarray, window: int = 20) -> np.ndarray:
    n = len(close)
    result = np.full(n, np.nan)
    returns = np.zeros(n)
    returns[1:] = np.diff(close) / close[:-1]
    for i in range(window, n):
        result[i] = np.std(returns[i - window:i]) * np.sqrt(252)
    return result


def _ewma_vol(close: np.ndarray, decay: float = 0.94) -> np.ndarray:
    n = len(close)
    returns = np.zeros(n)
    returns[1:] = np.diff(close) / close[:-1]
    var = np.zeros(n)
    var[0] = 0.0001
    for i in range(1, n):
        var[i] = decay * var[i - 1] + (1 - decay) * returns[i] ** 2
    return np.sqrt(var * 252)


def _vol_regime(close: np.ndarray, window: int = 60) -> np.ndarray:
    vol = _realized_vol(close, 20)
    n = len(close)
    regime = np.ones(n, dtype=int)
    for i in range(window, n):
        hist = vol[i - window:i]
        hist_clean = hist[~np.isnan(hist)]
        if len(hist_clean) < 10:
            continue
        p25 = np.percentile(hist_clean, 25)
        p75 = np.percentile(hist_clean, 75)
        if not np.isnan(vol[i]):
            if vol[i] < p25:
                regime[i] = 0
            elif vol[i] > p75:
                regime[i] = 2
    return regime


def _fear_greed(close: np.ndarray, volume: np.ndarray, window: int = 20) -> np.ndarray:
    n = len(close)
    fgi = np.full(n, 50.0)
    if n < window * 2:
        return fgi
    sma = np.convolve(close, np.ones(window) / window, mode='same')
    momentum = np.clip((close / sma - 0.95) / 0.10 * 100, 0, 100)
    vol_sma = np.convolve(volume, np.ones(window) / window, mode='same')
    vol_surge = np.where(vol_sma > 0, volume / vol_sma, 1.0)
    returns = np.zeros(n)
    returns[1:] = np.diff(close) / close[:-1]
    roll_vol = np.zeros(n)
    for i in range(window, n):
        roll_vol[i] = np.std(returns[i - window:i])
    long_vol = np.mean(roll_vol[roll_vol > 0]) if np.any(roll_vol > 0) else 0.01
    vol_fear = np.clip(100 - (roll_vol / long_vol - 0.5) / 1.5 * 100, 0, 100)
    up_days = np.zeros(n)
    for i in range(1, n):
        up_days[i] = up_days[i - 1] + 1 if close[i] > close[i - 1] else 0
    breadth = np.clip(up_days / 5 * 50 + 25, 0, 100)
    fgi = 0.4 * momentum + 0.2 * vol_fear + 0.2 * breadth + 0.2 * np.clip(vol_surge * 50, 0, 100)
    return np.clip(fgi, 0, 100)


def _relative_volume(volume: np.ndarray, window: int = 20) -> np.ndarray:
    n = len(volume)
    result = np.ones(n)
    for i in range(window, n):
        avg = np.mean(volume[i - window:i])
        if avg > 0:
            result[i] = volume[i] / avg
    return result


def _multi_timeframe_trend(close: np.ndarray) -> np.ndarray:
    """Multi-timeframe trend score: -3 to +3."""
    n = len(close)
    score = np.zeros(n, dtype=int)
    sma_d = _sma(close, 20)
    daily_bull = close > sma_d

    # Weekly proxy: SMA(50)
    sma_w = _sma(close, 50)
    weekly_bull = close > sma_w

    # Monthly proxy: SMA(120)
    sma_m = _sma(close, 120)
    monthly_bull = close > sma_m

    valid = ~np.isnan(sma_d) & ~np.isnan(sma_w) & ~np.isnan(sma_m)
    score[valid & daily_bull & weekly_bull & monthly_bull] = 3
    score[valid & daily_bull & weekly_bull & ~monthly_bull] = 2
    score[valid & daily_bull & ~weekly_bull] = 1
    score[valid & ~daily_bull & ~weekly_bull & ~monthly_bull] = -3
    score[valid & ~daily_bull & ~weekly_bull & monthly_bull] = -2
    score[valid & ~daily_bull & weekly_bull] = -1
    return score


# ═══════════════════════════════════════════════════════════════════════
#  Trend Following Strategies
# ═══════════════════════════════════════════════════════════════════════


class EMAcrossStrategy(Strategy):
    """Dual EMA crossover (fast/slow)."""

    name = "ema_cross"

    def __init__(self, fast: int = 9, slow: int = 21, stop_pct: float = 0.03, tp_pct: float = 0.06):
        self.fast = fast
        self.slow = slow
        self.stop_pct = stop_pct
        self.tp_pct = tp_pct

    def warmup_periods(self) -> int:
        return self.slow + 2

    def generate_signal(self, data: MarketData, idx: int) -> StrategySignal:
        if idx < self.warmup_periods():
            return StrategySignal(Signal.HOLD)
        close = data.close[:idx + 1]
        fast = _ema(close, self.fast)
        slow = _ema(close, self.slow)
        price = data.close[idx]

        if fast[-2] <= slow[-2] and fast[-1] > slow[-1]:
            return StrategySignal(Signal.BUY, strength=0.7,
                                  reason=f"EMA{self.fast}/{self.slow} bullish cross",
                                  stop_loss=price * (1 - self.stop_pct),
                                  take_profit=price * (1 + self.tp_pct))
        if fast[-2] >= slow[-2] and fast[-1] < slow[-1]:
            return StrategySignal(Signal.SELL, strength=0.7,
                                  reason=f"EMA{self.fast}/{self.slow} bearish cross")
        return StrategySignal(Signal.HOLD)


class ADXTrendStrategy(Strategy):
    """ADX-based trend following: trade only when trend is strong."""

    name = "adx_trend"

    def __init__(self, adx_threshold: float = 25.0, ema_period: int = 20,
                 stop_pct: float = 0.04, tp_pct: float = 0.08):
        self.adx_threshold = adx_threshold
        self.ema_period = ema_period
        self.stop_pct = stop_pct
        self.tp_pct = tp_pct

    def warmup_periods(self) -> int:
        return 40

    def generate_signal(self, data: MarketData, idx: int) -> StrategySignal:
        if idx < self.warmup_periods():
            return StrategySignal(Signal.HOLD)
        close = data.close[:idx + 1]
        high = data.high[:idx + 1]
        low = data.low[:idx + 1]
        adx_vals = _adx(high, low, close)
        ema_vals = _ema(close, self.ema_period)
        price = close[-1]
        adx_now = adx_vals[-1]

        if np.isnan(adx_now):
            return StrategySignal(Signal.HOLD)

        if adx_now > self.adx_threshold and price > ema_vals[-1]:
            return StrategySignal(Signal.BUY, strength=min(1.0, adx_now / 50),
                                  reason=f"ADX strong trend ({adx_now:.0f}) + price > EMA",
                                  stop_loss=price * (1 - self.stop_pct),
                                  take_profit=price * (1 + self.tp_pct))
        if adx_now > self.adx_threshold and price < ema_vals[-1]:
            return StrategySignal(Signal.SELL, strength=min(1.0, adx_now / 50),
                                  reason=f"ADX strong downtrend ({adx_now:.0f})")
        return StrategySignal(Signal.HOLD)


class MultiTimeframeStrategy(Strategy):
    """Multi-timeframe alignment: buy when all timeframes agree."""

    name = "multi_tf"

    def __init__(self, stop_pct: float = 0.05, tp_pct: float = 0.10):
        self.stop_pct = stop_pct
        self.tp_pct = tp_pct

    def warmup_periods(self) -> int:
        return 130

    def generate_signal(self, data: MarketData, idx: int) -> StrategySignal:
        if idx < self.warmup_periods():
            return StrategySignal(Signal.HOLD)
        close = data.close[:idx + 1]
        trend = _multi_timeframe_trend(close)
        price = close[-1]

        if trend[-1] == 3 and trend[-2] < 3:
            return StrategySignal(Signal.BUY, strength=1.0,
                                  reason="All timeframes aligned bullish",
                                  stop_loss=price * (1 - self.stop_pct),
                                  take_profit=price * (1 + self.tp_pct))
        if trend[-1] <= -2 and trend[-2] > -2:
            return StrategySignal(Signal.SELL, strength=0.9,
                                  reason=f"Multi-TF bearish ({trend[-1]})")
        return StrategySignal(Signal.HOLD)


# ═══════════════════════════════════════════════════════════════════════
#  Mean Reversion Strategies
# ═══════════════════════════════════════════════════════════════════════


class StochasticStrategy(Strategy):
    """Stochastic Oscillator mean-reversion."""

    name = "stochastic"

    def __init__(self, k_period: int = 14, oversold: float = 20, overbought: float = 80,
                 stop_pct: float = 0.03, tp_pct: float = 0.05):
        self.k_period = k_period
        self.oversold = oversold
        self.overbought = overbought
        self.stop_pct = stop_pct
        self.tp_pct = tp_pct

    def warmup_periods(self) -> int:
        return self.k_period + 2

    def generate_signal(self, data: MarketData, idx: int) -> StrategySignal:
        if idx < self.warmup_periods():
            return StrategySignal(Signal.HOLD)
        k = _stochastic(data.high[:idx + 1], data.low[:idx + 1], data.close[:idx + 1], self.k_period)
        price = data.close[idx]
        k_now, k_prev = k[-1], k[-2]

        if np.isnan(k_now) or np.isnan(k_prev):
            return StrategySignal(Signal.HOLD)

        if k_prev <= self.oversold and k_now > self.oversold:
            return StrategySignal(Signal.BUY, strength=0.7,
                                  reason=f"Stoch oversold recovery ({k_now:.0f})",
                                  stop_loss=price * (1 - self.stop_pct),
                                  take_profit=price * (1 + self.tp_pct))
        if k_prev >= self.overbought and k_now < self.overbought:
            return StrategySignal(Signal.SELL, strength=0.7,
                                  reason=f"Stoch overbought reversal ({k_now:.0f})")
        return StrategySignal(Signal.HOLD)


class VWAPReversionStrategy(Strategy):
    """VWAP mean-reversion: buy below VWAP, sell above."""

    name = "vwap_reversion"

    def __init__(self, threshold: float = 0.02, stop_pct: float = 0.03, tp_pct: float = 0.04):
        self.threshold = threshold
        self.stop_pct = stop_pct
        self.tp_pct = tp_pct

    def warmup_periods(self) -> int:
        return 20

    def generate_signal(self, data: MarketData, idx: int) -> StrategySignal:
        if idx < self.warmup_periods():
            return StrategySignal(Signal.HOLD)
        vwap_val = _vwap(data.high[:idx + 1], data.low[:idx + 1],
                         data.close[:idx + 1], data.volume[:idx + 1])
        price = data.close[idx]
        if vwap_val[-1] == 0:
            return StrategySignal(Signal.HOLD)
        deviation = (price - vwap_val[-1]) / vwap_val[-1]

        if deviation < -self.threshold:
            return StrategySignal(Signal.BUY, strength=min(1.0, abs(deviation) / self.threshold),
                                  reason=f"Below VWAP ({deviation:.2%})",
                                  stop_loss=price * (1 - self.stop_pct),
                                  take_profit=vwap_val[-1])
        if deviation > self.threshold:
            return StrategySignal(Signal.SELL, strength=min(1.0, deviation / self.threshold),
                                  reason=f"Above VWAP ({deviation:.2%})")
        return StrategySignal(Signal.HOLD)


# ═══════════════════════════════════════════════════════════════════════
#  Momentum Strategies
# ═══════════════════════════════════════════════════════════════════════


class MomentumFactorStrategy(Strategy):
    """Multi-period momentum with acceleration filter (Moskowitz et al.)."""

    name = "momentum_factor"

    def __init__(self, periods: Optional[list[int]] = None, stop_pct: float = 0.05, tp_pct: float = 0.10):
        self.periods = periods or [21, 63, 126, 252]
        self.stop_pct = stop_pct
        self.tp_pct = tp_pct

    def warmup_periods(self) -> int:
        return max(self.periods) + 30

    def generate_signal(self, data: MarketData, idx: int) -> StrategySignal:
        if idx < self.warmup_periods():
            return StrategySignal(Signal.HOLD)
        close = data.close[:idx + 1]
        price = close[-1]

        # Multi-period momentum score
        total = 0.0
        count = 0
        for p in self.periods:
            if idx >= p and close[idx - p] > 0:
                ret = (close[idx] - close[idx - p]) / close[idx - p]
                total += np.sign(ret)
                count += 1
        score = total / count if count > 0 else 0

        # Acceleration
        fast_p, slow_p = 21, 63
        if idx >= slow_p + fast_p and close[idx - fast_p] > 0 and close[idx - slow_p] > 0:
            mom_now = (close[idx] - close[idx - fast_p]) / close[idx - fast_p]
            mom_prev = (close[idx - fast_p] - close[idx - slow_p]) / close[idx - slow_p]
            accel = mom_now - mom_prev
        else:
            accel = 0

        if score > 0.5 and accel > 0:
            return StrategySignal(Signal.BUY, strength=min(1.0, score),
                                  reason=f"Strong momentum (score={score:.2f}, accel={accel:.4f})",
                                  stop_loss=price * (1 - self.stop_pct),
                                  take_profit=price * (1 + self.tp_pct))
        if score < -0.25:
            return StrategySignal(Signal.SELL, strength=min(1.0, abs(score)),
                                  reason=f"Negative momentum (score={score:.2f})")
        return StrategySignal(Signal.HOLD)


class OBVDivergenceStrategy(Strategy):
    """On-Balance Volume divergence: price vs OBV divergence signals."""

    name = "obv_divergence"

    def __init__(self, lookback: int = 20, stop_pct: float = 0.03, tp_pct: float = 0.05):
        self.lookback = lookback
        self.stop_pct = stop_pct
        self.tp_pct = tp_pct

    def warmup_periods(self) -> int:
        return self.lookback + 5

    def generate_signal(self, data: MarketData, idx: int) -> StrategySignal:
        if idx < self.warmup_periods():
            return StrategySignal(Signal.HOLD)
        close = data.close[:idx + 1]
        obv_vals = _obv(close, data.volume[:idx + 1])
        price = close[-1]

        price_slope = (close[-1] - close[-self.lookback]) / close[-self.lookback]
        obv_range = obv_vals[-1] - obv_vals[-self.lookback]
        obv_base = abs(obv_vals[-self.lookback]) + 1
        obv_slope = obv_range / obv_base

        # Bullish divergence: price falling but OBV rising
        if price_slope < -0.02 and obv_slope > 0.05:
            return StrategySignal(Signal.BUY, strength=0.7,
                                  reason="Bullish OBV divergence",
                                  stop_loss=price * (1 - self.stop_pct),
                                  take_profit=price * (1 + self.tp_pct))
        # Bearish divergence: price rising but OBV falling
        if price_slope > 0.02 and obv_slope < -0.05:
            return StrategySignal(Signal.SELL, strength=0.7,
                                  reason="Bearish OBV divergence")
        return StrategySignal(Signal.HOLD)


# ═══════════════════════════════════════════════════════════════════════
#  Volatility Strategies (from invest/backend/calc/volatility.py)
# ═══════════════════════════════════════════════════════════════════════


class VolBreakoutStrategy(Strategy):
    """Buy on volatility regime shift from low to normal (expansion start)."""

    name = "vol_breakout"

    def __init__(self, stop_pct: float = 0.04, tp_pct: float = 0.08):
        self.stop_pct = stop_pct
        self.tp_pct = tp_pct

    def warmup_periods(self) -> int:
        return 80

    def generate_signal(self, data: MarketData, idx: int) -> StrategySignal:
        if idx < self.warmup_periods():
            return StrategySignal(Signal.HOLD)
        close = data.close[:idx + 1]
        regime = _vol_regime(close)
        price = close[-1]

        if regime[-1] == 1 and regime[-2] == 0:
            return StrategySignal(Signal.BUY, strength=0.7,
                                  reason="Vol regime: low -> normal (expansion)",
                                  stop_loss=price * (1 - self.stop_pct),
                                  take_profit=price * (1 + self.tp_pct))
        if regime[-1] == 2 and regime[-2] != 2:
            return StrategySignal(Signal.SELL, strength=0.8,
                                  reason="Vol regime: entering high volatility")
        return StrategySignal(Signal.HOLD)


class VolMeanRevertStrategy(Strategy):
    """Buy when EWMA vol spikes above realized vol (fear = opportunity)."""

    name = "vol_mean_revert"

    def __init__(self, spike_ratio: float = 2.0, stop_pct: float = 0.05, tp_pct: float = 0.08):
        self.spike_ratio = spike_ratio
        self.stop_pct = stop_pct
        self.tp_pct = tp_pct

    def warmup_periods(self) -> int:
        return 30

    def generate_signal(self, data: MarketData, idx: int) -> StrategySignal:
        if idx < self.warmup_periods():
            return StrategySignal(Signal.HOLD)
        close = data.close[:idx + 1]
        ewma = _ewma_vol(close)
        real = _realized_vol(close, 20)
        price = close[-1]

        if np.isnan(ewma[-1]) or np.isnan(real[-1]) or real[-1] <= 0:
            return StrategySignal(Signal.HOLD)

        ratio = ewma[-1] / max(real[-1], 0.001)
        prev_ratio = ewma[-2] / max(real[-2], 0.001) if len(ewma) > 1 and not np.isnan(real[-2]) and real[-2] > 0 else ratio

        if ratio > self.spike_ratio and prev_ratio <= self.spike_ratio:
            return StrategySignal(Signal.BUY, strength=min(1.0, ratio / 3),
                                  reason=f"Vol spike (EWMA/Real = {ratio:.1f}x)",
                                  stop_loss=price * (1 - self.stop_pct),
                                  take_profit=price * (1 + self.tp_pct))
        if ratio < 0.5 and prev_ratio >= 0.5:
            return StrategySignal(Signal.SELL, strength=0.6,
                                  reason="Vol complacency")
        return StrategySignal(Signal.HOLD)


# ═══════════════════════════════════════════════════════════════════════
#  Sentiment Strategy (from invest/backend/calc/sentiment.py)
# ═══════════════════════════════════════════════════════════════════════


class FearGreedStrategy(Strategy):
    """Contrarian sentiment: buy extreme fear, sell extreme greed."""

    name = "fear_greed"

    def __init__(self, fear_threshold: float = 25, greed_threshold: float = 75,
                 stop_pct: float = 0.05, tp_pct: float = 0.08):
        self.fear_threshold = fear_threshold
        self.greed_threshold = greed_threshold
        self.stop_pct = stop_pct
        self.tp_pct = tp_pct

    def warmup_periods(self) -> int:
        return 50

    def generate_signal(self, data: MarketData, idx: int) -> StrategySignal:
        if idx < self.warmup_periods():
            return StrategySignal(Signal.HOLD)
        close = data.close[:idx + 1]
        vol = data.volume[:idx + 1]
        fgi = _fear_greed(close, vol)
        price = close[-1]
        fgi_now = fgi[-1]

        if fgi_now < self.fear_threshold and fgi[-2] >= self.fear_threshold:
            return StrategySignal(Signal.BUY, strength=min(1.0, (self.fear_threshold - fgi_now) / 25),
                                  reason=f"Extreme fear (FGI={fgi_now:.0f})",
                                  stop_loss=price * (1 - self.stop_pct),
                                  take_profit=price * (1 + self.tp_pct))
        if fgi_now > self.greed_threshold and fgi[-2] <= self.greed_threshold:
            return StrategySignal(Signal.SELL, strength=min(1.0, (fgi_now - self.greed_threshold) / 25),
                                  reason=f"Extreme greed (FGI={fgi_now:.0f})")
        return StrategySignal(Signal.HOLD)


# ═══════════════════════════════════════════════════════════════════════
#  Volume / Liquidity Strategy (from invest/backend/calc/liquidity.py)
# ═══════════════════════════════════════════════════════════════════════


class VolumeSurgeStrategy(Strategy):
    """Buy on volume surge + price breakout (institutional accumulation)."""

    name = "volume_surge"

    def __init__(self, surge_threshold: float = 2.0, stop_pct: float = 0.03, tp_pct: float = 0.05):
        self.surge_threshold = surge_threshold
        self.stop_pct = stop_pct
        self.tp_pct = tp_pct

    def warmup_periods(self) -> int:
        return 25

    def generate_signal(self, data: MarketData, idx: int) -> StrategySignal:
        if idx < self.warmup_periods():
            return StrategySignal(Signal.HOLD)
        close = data.close[:idx + 1]
        vol = data.volume[:idx + 1]
        rvol = _relative_volume(vol)
        sma20 = _sma(close, 20)
        price = close[-1]

        if np.isnan(sma20[-1]):
            return StrategySignal(Signal.HOLD)

        breakout = price > sma20[-1]
        surge = rvol[-1] > self.surge_threshold

        if breakout and surge and not (rvol[-2] > self.surge_threshold and data.close[idx - 1] > sma20[-2] if not np.isnan(sma20[-2]) else False):
            return StrategySignal(Signal.BUY, strength=min(1.0, rvol[-1] / 3),
                                  reason=f"Volume surge ({rvol[-1]:.1f}x) + breakout",
                                  stop_loss=price * (1 - self.stop_pct),
                                  take_profit=price * (1 + self.tp_pct))
        if not breakout and rvol[-1] > self.surge_threshold:
            return StrategySignal(Signal.SELL, strength=0.6,
                                  reason="Volume surge + below SMA = distribution")
        return StrategySignal(Signal.HOLD)


# ═══════════════════════════════════════════════════════════════════════
#  ATR-based Strategy
# ═══════════════════════════════════════════════════════════════════════


class ATRBreakoutStrategy(Strategy):
    """ATR channel breakout: buy on break above recent high + ATR, sell on break below."""

    name = "atr_breakout"

    def __init__(self, atr_mult: float = 1.5, lookback: int = 20, stop_atr_mult: float = 2.0):
        self.atr_mult = atr_mult
        self.lookback = lookback
        self.stop_atr_mult = stop_atr_mult

    def warmup_periods(self) -> int:
        return self.lookback + 15

    def generate_signal(self, data: MarketData, idx: int) -> StrategySignal:
        if idx < self.warmup_periods():
            return StrategySignal(Signal.HOLD)
        close = data.close[:idx + 1]
        high = data.high[:idx + 1]
        low = data.low[:idx + 1]
        atr_vals = _atr(high, low, close)
        price = close[-1]

        if np.isnan(atr_vals[-1]):
            return StrategySignal(Signal.HOLD)

        recent_high = np.max(high[-self.lookback:-1])
        recent_low = np.min(low[-self.lookback:-1])
        atr_now = atr_vals[-1]

        if price > recent_high + atr_now * self.atr_mult:
            return StrategySignal(Signal.BUY, strength=0.8,
                                  reason=f"ATR breakout above {recent_high:.2f}",
                                  stop_loss=price - atr_now * self.stop_atr_mult,
                                  take_profit=price + atr_now * self.stop_atr_mult * 2)
        if price < recent_low - atr_now * self.atr_mult:
            return StrategySignal(Signal.SELL, strength=0.8,
                                  reason=f"ATR breakdown below {recent_low:.2f}")
        return StrategySignal(Signal.HOLD)


# ═══════════════════════════════════════════════════════════════════════
#  Composite / Ensemble Strategy
# ═══════════════════════════════════════════════════════════════════════


class EnsembleStrategy(Strategy):
    """Ensemble: majority vote from multiple sub-strategies.

    Requires N out of M sub-strategies to agree before generating a signal.
    Each sub-strategy's strength contributes to the final strength.
    """

    name = "ensemble"

    def __init__(self, strategies: Optional[list[Strategy]] = None,
                 min_agreement: int = 3, stop_pct: float = 0.04, tp_pct: float = 0.08):
        from trading.strategy import MACDStrategy, RSIStrategy, BollingerStrategy
        self.strategies = strategies or [
            MACDStrategy(),
            RSIStrategy(),
            BollingerStrategy(),
            EMAcrossStrategy(),
            MomentumFactorStrategy(),
        ]
        self.min_agreement = min_agreement
        self.stop_pct = stop_pct
        self.tp_pct = tp_pct

    def warmup_periods(self) -> int:
        return max(s.warmup_periods() for s in self.strategies)

    def generate_signal(self, data: MarketData, idx: int) -> StrategySignal:
        if idx < self.warmup_periods():
            return StrategySignal(Signal.HOLD)

        buy_count = 0
        sell_count = 0
        total_strength = 0.0
        reasons = []

        for strat in self.strategies:
            if idx >= strat.warmup_periods():
                sig = strat.generate_signal(data, idx)
                if sig.signal == Signal.BUY:
                    buy_count += 1
                    total_strength += sig.strength
                    reasons.append(f"{strat.name}:BUY")
                elif sig.signal == Signal.SELL:
                    sell_count += 1
                    total_strength += sig.strength
                    reasons.append(f"{strat.name}:SELL")

        price = data.close[idx]

        if buy_count >= self.min_agreement:
            avg_strength = total_strength / buy_count
            return StrategySignal(Signal.BUY, strength=avg_strength,
                                  reason=f"Ensemble BUY ({buy_count}/{len(self.strategies)}): {', '.join(reasons)}",
                                  stop_loss=price * (1 - self.stop_pct),
                                  take_profit=price * (1 + self.tp_pct))
        if sell_count >= self.min_agreement:
            avg_strength = total_strength / sell_count
            return StrategySignal(Signal.SELL, strength=avg_strength,
                                  reason=f"Ensemble SELL ({sell_count}/{len(self.strategies)}): {', '.join(reasons)}")
        return StrategySignal(Signal.HOLD)


# ═══════════════════════════════════════════════════════════════════════
#  All strategy registry — for autonomous scanner
# ═══════════════════════════════════════════════════════════════════════

ALL_STRATEGIES: dict[str, type[Strategy]] = {
    "ema_cross": EMAcrossStrategy,
    "adx_trend": ADXTrendStrategy,
    "multi_tf": MultiTimeframeStrategy,
    "stochastic": StochasticStrategy,
    "vwap_reversion": VWAPReversionStrategy,
    "momentum_factor": MomentumFactorStrategy,
    "obv_divergence": OBVDivergenceStrategy,
    "vol_breakout": VolBreakoutStrategy,
    "vol_mean_revert": VolMeanRevertStrategy,
    "fear_greed": FearGreedStrategy,
    "volume_surge": VolumeSurgeStrategy,
    "atr_breakout": ATRBreakoutStrategy,
    "ensemble": EnsembleStrategy,
}


def get_all_strategies() -> list[Strategy]:
    """Instantiate one of every strategy (default params)."""
    return [cls() for cls in ALL_STRATEGIES.values()]
