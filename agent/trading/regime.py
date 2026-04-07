"""Market regime detection — adapted from invest/scalper orchestrator.

Detects market conditions and maps them to trading policies.
Combines volatility regime, trend regime, and SOC criticality
into a unified regime that the autonomous loop uses for decision-making.

Regime hierarchy:
  CALM     -> full strategies, leverage allowed, momentum preferred
  NORMAL   -> standard strategies, no leverage, balanced
  ELEVATED -> defensive only, SOC filter active, reduced position size
  CRITICAL -> no new buys, force exit, SOC filter active

Consciousness integration:
  Phi and tension from the consciousness engine modulate regime sensitivity.
  High tension = shift regime one level more cautious.
  Low Phi = reduce max position size.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from enum import IntEnum
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# TECS-L constants
E = math.e
INV_E = 1.0 / E
ONE_SIXTH = 1.0 / 6


class MarketRegime(IntEnum):
    """Market regime levels (matches scalper/src/orchestrator/regime.rs)."""
    CALM = 0
    NORMAL = 1
    ELEVATED = 2
    CRITICAL = 3


@dataclass
class RegimePolicy:
    """Trading policy for a given regime."""
    regime: MarketRegime
    allow_buys: bool
    allow_leverage: bool
    preferred_type: str       # momentum, balanced, defensive, none
    soc_filter: bool          # require SOC criticality check
    force_exit: bool          # force close all positions
    max_position_pct: float   # max position size as % of equity


REGIME_POLICIES: dict[MarketRegime, RegimePolicy] = {
    MarketRegime.CALM: RegimePolicy(
        regime=MarketRegime.CALM,
        allow_buys=True, allow_leverage=True,
        preferred_type="momentum", soc_filter=False, force_exit=False,
        max_position_pct=0.20,
    ),
    MarketRegime.NORMAL: RegimePolicy(
        regime=MarketRegime.NORMAL,
        allow_buys=True, allow_leverage=False,
        preferred_type="balanced", soc_filter=False, force_exit=False,
        max_position_pct=0.15,
    ),
    MarketRegime.ELEVATED: RegimePolicy(
        regime=MarketRegime.ELEVATED,
        allow_buys=True, allow_leverage=False,
        preferred_type="defensive", soc_filter=True, force_exit=False,
        max_position_pct=0.10,
    ),
    MarketRegime.CRITICAL: RegimePolicy(
        regime=MarketRegime.CRITICAL,
        allow_buys=False, allow_leverage=False,
        preferred_type="none", soc_filter=True, force_exit=True,
        max_position_pct=0.0,
    ),
}


# ═══════════════════════════════════════════════════════════════════════
#  Volatility-based regime detection
# ═══════════════════════════════════════════════════════════════════════

def _std_dev(data: np.ndarray) -> float:
    if len(data) < 2:
        return 0.0
    return float(np.std(data))


def detect_vol_regime(prices: np.ndarray, recent_window: int = 10, hist_window: int = 60) -> MarketRegime:
    """Detect regime from price volatility ratio (recent vs historical).

    Adapted from scalper/src/orchestrator/regime.rs detect_regime_from_prices.
    """
    n = len(prices)
    if n < recent_window + hist_window:
        return MarketRegime.NORMAL

    recent = prices[-recent_window:]
    historical = prices[:-recent_window]

    recent_vol = _std_dev(recent)
    hist_vol = _std_dev(historical)

    if hist_vol <= 0:
        return MarketRegime.NORMAL

    # Criticality index: how much recent vol exceeds historical
    ci = max(0.0, min(1.0, recent_vol / hist_vol - 1.0))

    if ci < 0.1:
        return MarketRegime.CALM
    elif ci < 0.2:
        return MarketRegime.NORMAL
    elif ci < 0.3:
        return MarketRegime.ELEVATED
    else:
        return MarketRegime.CRITICAL


# ═══════════════════════════════════════════════════════════════════════
#  Return-based regime detection
# ═══════════════════════════════════════════════════════════════════════

def detect_return_regime(prices: np.ndarray, window: int = 20) -> MarketRegime:
    """Detect regime from return distribution (kurtosis + tail risk)."""
    if len(prices) < window + 1:
        return MarketRegime.NORMAL

    returns = np.diff(prices[-window - 1:]) / prices[-window - 1:-1]

    if len(returns) < 10:
        return MarketRegime.NORMAL

    # Kurtosis (excess): normal = 0, fat tails > 0
    mean_r = np.mean(returns)
    std_r = np.std(returns)
    if std_r < 1e-10:
        return MarketRegime.CALM

    kurtosis = np.mean(((returns - mean_r) / std_r) ** 4) - 3.0

    # Max daily loss
    max_loss = abs(np.min(returns))

    if kurtosis > 5.0 or max_loss > 0.10:
        return MarketRegime.CRITICAL
    elif kurtosis > 2.0 or max_loss > 0.05:
        return MarketRegime.ELEVATED
    elif kurtosis > 0.5:
        return MarketRegime.NORMAL
    else:
        return MarketRegime.CALM


# ═══════════════════════════════════════════════════════════════════════
#  Trend regime detection
# ═══════════════════════════════════════════════════════════════════════

def detect_trend_regime(prices: np.ndarray) -> str:
    """Detect trend: 'uptrend', 'downtrend', or 'range'.

    Uses SMA(20) vs SMA(50) relative positioning.
    """
    n = len(prices)
    if n < 55:
        return "range"

    sma20 = np.mean(prices[-20:])
    sma50 = np.mean(prices[-50:])
    price = prices[-1]

    if price > sma20 > sma50:
        return "uptrend"
    elif price < sma20 < sma50:
        return "downtrend"
    else:
        return "range"


# ═══════════════════════════════════════════════════════════════════════
#  SOC (Self-Organized Criticality) filter
# ═══════════════════════════════════════════════════════════════════════

def soc_criticality_score(prices: np.ndarray, window: int = 50) -> float:
    """SOC criticality score (0-1) based on avalanche-like return cascades.

    Adapted from invest/backend/calc/soc.py market_sandpile concept.
    High score = market near critical point, caution needed.
    """
    if len(prices) < window + 1:
        return 0.0

    returns = np.abs(np.diff(prices[-window - 1:])) / prices[-window - 1:-1]

    # Count cascades: sequences of increasingly large moves
    cascade_count = 0
    cascade_size = 0
    for i in range(1, len(returns)):
        if returns[i] > returns[i - 1] * 1.5:  # amplifying
            cascade_size += 1
        else:
            if cascade_size >= 3:
                cascade_count += 1
            cascade_size = 0

    # Large tail moves
    p95 = np.percentile(returns, 95)
    tail_count = np.sum(returns > p95 * 2)

    score = min(1.0, cascade_count * 0.2 + tail_count * 0.15)
    return score


# ═══════════════════════════════════════════════════════════════════════
#  Unified Regime Detector
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class RegimeState:
    """Full regime state with all components."""
    regime: MarketRegime
    policy: RegimePolicy
    vol_regime: MarketRegime
    return_regime: MarketRegime
    trend: str                  # uptrend, downtrend, range
    soc_score: float            # 0-1 criticality
    consciousness_shift: int    # -1, 0, +1 regime shift from consciousness


class RegimeDetector:
    """Unified market regime detector.

    Combines volatility, return distribution, trend, and SOC analysis.
    Optionally integrates consciousness state (Phi + tension).

    The worst regime across all detectors is used (conservative approach),
    matching the scalper's orchestrator pattern.
    """

    def __init__(
        self,
        phi_threshold: float = 1.0,
        tension_threshold: float = 0.7,
    ):
        self.phi_threshold = phi_threshold
        self.tension_threshold = tension_threshold
        self._history: list[RegimeState] = []

    def detect(
        self,
        prices: np.ndarray,
        phi: float = 0.0,
        tension: float = 0.0,
    ) -> RegimeState:
        """Detect current market regime.

        Args:
            prices: Price array (at least 60 elements recommended).
            phi: Current consciousness Phi value.
            tension: Current consciousness tension value.

        Returns:
            RegimeState with full analysis.
        """
        vol_regime = detect_vol_regime(prices)
        ret_regime = detect_return_regime(prices)
        trend = detect_trend_regime(prices)
        soc_score = soc_criticality_score(prices)

        # Take worst regime across detectors
        combined = MarketRegime(max(int(vol_regime), int(ret_regime)))

        # SOC filter: if criticality high, bump up one level
        if soc_score > 0.6 and combined < MarketRegime.CRITICAL:
            combined = MarketRegime(int(combined) + 1)

        # Consciousness modulation
        consciousness_shift = 0
        if tension > self.tension_threshold and combined < MarketRegime.CRITICAL:
            combined = MarketRegime(int(combined) + 1)
            consciousness_shift = 1
        elif phi > self.phi_threshold * 2 and combined > MarketRegime.CALM:
            # Very high Phi = high integration = can handle more risk
            combined = MarketRegime(int(combined) - 1)
            consciousness_shift = -1

        policy = REGIME_POLICIES[combined]

        state = RegimeState(
            regime=combined,
            policy=policy,
            vol_regime=vol_regime,
            return_regime=ret_regime,
            trend=trend,
            soc_score=soc_score,
            consciousness_shift=consciousness_shift,
        )

        self._history.append(state)
        if len(self._history) > 1000:
            self._history = self._history[-500:]

        return state

    def regime_changed(self) -> bool:
        """Check if regime changed from previous detection."""
        if len(self._history) < 2:
            return False
        return self._history[-1].regime != self._history[-2].regime

    def status(self) -> dict:
        """Current regime status as dict."""
        if not self._history:
            return {"regime": "UNKNOWN", "detections": 0}
        s = self._history[-1]
        return {
            "regime": s.regime.name,
            "policy": s.policy.preferred_type,
            "allow_buys": s.policy.allow_buys,
            "force_exit": s.policy.force_exit,
            "max_position_pct": s.policy.max_position_pct,
            "trend": s.trend,
            "soc_score": round(s.soc_score, 3),
            "consciousness_shift": s.consciousness_shift,
            "vol_regime": s.vol_regime.name,
            "return_regime": s.return_regime.name,
            "detections": len(self._history),
        }
