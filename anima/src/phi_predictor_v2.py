#!/usr/bin/env python3
"""Phi Predictor v2 — N step 후 Phi 예측.

현재 Phi 궤적에서 미래 예측 → 막다른 길 조기 감지.
학습 중 탐색 자원을 유망한 경로에 집중.

Usage:
    from phi_predictor_v2 import PhiPredictor
    pred = PhiPredictor()
    pred.fit(phi_history)  # list of (step, phi) or list of phi values
    future = pred.predict(steps_ahead=100)
    print(f"Predicted Phi at step {current+100}: {future}")
    print(f"Dead end probability: {pred.dead_end_prob()}")
"""

import numpy as np
from typing import List, Tuple, Optional, Dict, Union


class PhiPredictor:
    """Predict Phi N steps ahead using exponential smoothing + trend extraction.

    Detects:
      - Dead ends:  predicted Phi < current * 0.9
      - Plateaus:   predicted growth < 0.1% over steps_ahead
      - Growth:     confident upward trend
    """

    def __init__(
        self,
        alpha: float = 0.3,          # exponential smoothing weight (0=slow, 1=fast)
        beta: float = 0.1,           # trend smoothing weight
        window: int = 20,            # recent window for trend extraction
        dead_end_threshold: float = 0.9,   # ratio: predicted/current < this → dead end
        plateau_threshold: float = 0.001,  # growth rate below this → plateau
        ci_sigma: float = 1.96,      # confidence interval z-score (95%)
    ):
        self.alpha = alpha
        self.beta = beta
        self.window = window
        self.dead_end_threshold = dead_end_threshold
        self.plateau_threshold = plateau_threshold
        self.ci_sigma = ci_sigma

        # State after fit()
        self._steps: Optional[np.ndarray] = None
        self._phis: Optional[np.ndarray] = None
        self._level: float = 0.0    # Holt's exponential smoothing: level
        self._trend: float = 0.0    # Holt's exponential smoothing: trend
        self._residuals: List[float] = []
        self._fitted = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fit(self, history: Union[List[float], List[Tuple[int, float]]]) -> "PhiPredictor":
        """Fit the predictor to Phi history.

        Args:
            history: Either list of phi values, or list of (step, phi) tuples.
        """
        if not history:
            raise ValueError("history must not be empty")

        # Normalise to arrays
        if isinstance(history[0], (tuple, list)):
            pairs = history
            steps = np.array([p[0] for p in pairs], dtype=float)
            phis = np.array([p[1] for p in pairs], dtype=float)
        else:
            phis = np.array(history, dtype=float)
            steps = np.arange(len(phis), dtype=float)

        self._steps = steps
        self._phis = phis

        # Holt's double exponential smoothing (level + trend)
        level = phis[0]
        trend = (phis[-1] - phis[0]) / max(len(phis) - 1, 1)

        smoothed = [level]
        for phi in phis[1:]:
            prev_level = level
            level = self.alpha * phi + (1 - self.alpha) * (level + trend)
            trend = self.beta * (level - prev_level) + (1 - self.beta) * trend
            smoothed.append(level)

        self._level = level
        self._trend = trend

        # Residuals for confidence interval estimation
        self._residuals = (phis - np.array(smoothed)).tolist()
        self._fitted = True
        return self

    def predict(self, steps_ahead: int = 50) -> float:
        """Extrapolate Phi `steps_ahead` steps into the future.

        Returns:
            Predicted Phi value (point estimate).
        """
        self._assert_fitted()
        return float(self._level + self._trend * steps_ahead)

    def predict_trajectory(self, steps_ahead: int = 50) -> Dict[str, np.ndarray]:
        """Return full predicted trajectory with confidence interval.

        Returns dict with keys:
            steps:   array of future step indices
            mean:    point estimate per step
            lower:   lower 95% CI bound
            upper:   upper 95% CI bound
        """
        self._assert_fitted()
        h = np.arange(1, steps_ahead + 1)
        base_step = self._steps[-1] if self._steps is not None else 0

        mean = self._level + self._trend * h

        # CI: residual std grows as sqrt(h) (random-walk uncertainty)
        res = np.array(self._residuals)
        std = np.std(res) if len(res) > 1 else 0.0
        margin = self.ci_sigma * std * np.sqrt(h)

        return {
            "steps": base_step + h,
            "mean": mean,
            "lower": mean - margin,
            "upper": mean + margin,
        }

    def dead_end_prob(self, steps_ahead: int = 50) -> float:
        """Probability that Phi enters a dead end within steps_ahead.

        Dead end: predicted Phi drops below current * dead_end_threshold.

        Uses residual std + Gaussian approximation.
        Returns probability in [0, 1].
        """
        self._assert_fitted()
        current = float(self._phis[-1]) if self._phis is not None else self._level
        threshold = current * self.dead_end_threshold

        predicted_mean = self.predict(steps_ahead)

        res = np.array(self._residuals)
        std = np.std(res) if len(res) > 1 else 1e-9
        # Scale uncertainty with sqrt(steps_ahead)
        total_std = std * float(np.sqrt(steps_ahead))

        if total_std < 1e-12:
            return 1.0 if predicted_mean < threshold else 0.0

        # P(X < threshold) where X ~ N(predicted_mean, total_std)
        z = (threshold - predicted_mean) / total_std
        prob = float(_normal_cdf(z))
        return max(0.0, min(1.0, prob))

    def plateau_prob(self, steps_ahead: int = 50) -> float:
        """Probability that Phi growth is below plateau_threshold * steps_ahead.

        Returns probability in [0, 1].
        """
        self._assert_fitted()
        current = float(self._phis[-1]) if self._phis is not None else self._level
        min_growth = self.plateau_threshold * abs(current) * steps_ahead

        predicted = self.predict(steps_ahead)
        growth = predicted - current

        res = np.array(self._residuals)
        std = np.std(res) if len(res) > 1 else 1e-9
        total_std = std * float(np.sqrt(steps_ahead))

        if total_std < 1e-12:
            return 1.0 if growth < min_growth else 0.0

        z = (min_growth - growth) / total_std
        prob = float(_normal_cdf(z))
        return max(0.0, min(1.0, prob))

    def status(self, steps_ahead: int = 50) -> Dict:
        """Return a summary status dict for logging/reporting.

        Keys:
            current_phi, predicted_phi, trend, dead_end_prob, plateau_prob,
            verdict ('GROWTH' | 'PLATEAU' | 'DEAD_END')
        """
        self._assert_fitted()
        current = float(self._phis[-1]) if self._phis is not None else self._level
        predicted = self.predict(steps_ahead)
        dp = self.dead_end_prob(steps_ahead)
        pp = self.plateau_prob(steps_ahead)

        if dp > 0.6:
            verdict = "DEAD_END"
        elif pp > 0.7:
            verdict = "PLATEAU"
        else:
            verdict = "GROWTH"

        return {
            "current_phi": current,
            "predicted_phi": predicted,
            "trend_per_step": self._trend,
            "steps_ahead": steps_ahead,
            "dead_end_prob": dp,
            "plateau_prob": pp,
            "verdict": verdict,
        }

    def reset(self) -> None:
        """Reset fitted state."""
        self._steps = None
        self._phis = None
        self._level = 0.0
        self._trend = 0.0
        self._residuals = []
        self._fitted = False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _assert_fitted(self) -> None:
        if not self._fitted:
            raise RuntimeError("PhiPredictor: call fit() before predict()")


# ------------------------------------------------------------------
# Module-level helpers
# ------------------------------------------------------------------

def _normal_cdf(z: float) -> float:
    """Approximate standard normal CDF using Abramowitz & Stegun."""
    # Use error function: Phi(z) = 0.5 * (1 + erf(z / sqrt(2)))
    import math
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def fit_and_predict(
    history: Union[List[float], List[Tuple[int, float]]],
    steps_ahead: int = 100,
    **kwargs,
) -> Dict:
    """Convenience: fit + status in one call."""
    pred = PhiPredictor(**kwargs)
    pred.fit(history)
    return pred.status(steps_ahead)


# ------------------------------------------------------------------
# Demo / CLI
# ------------------------------------------------------------------

def main():
    import math

    print("=== PhiPredictor v2 Demo ===\n")

    # Simulate a growing Phi trajectory with noise
    rng = np.random.default_rng(42)
    steps = 100
    phi_history = []
    phi = 1.0
    for i in range(steps):
        phi += 0.05 + rng.normal(0, 0.02)
        phi_history.append((i, max(0.0, phi)))

    pred = PhiPredictor(alpha=0.3, beta=0.1)
    pred.fit(phi_history)

    s = pred.status(steps_ahead=50)
    print(f"Current Phi:   {s['current_phi']:.3f}")
    print(f"Predicted Phi: {s['predicted_phi']:.3f} (+50 steps)")
    print(f"Trend/step:    {s['trend_per_step']:.4f}")
    print(f"Dead-end prob: {s['dead_end_prob']:.2%}")
    print(f"Plateau prob:  {s['plateau_prob']:.2%}")
    print(f"Verdict:       {s['verdict']}")

    print()

    # Simulate a dead-end trajectory
    phi2 = [5.0 - i * 0.08 + rng.normal(0, 0.05) for i in range(50)]
    s2 = fit_and_predict(phi2, steps_ahead=30)
    print("-- Dead-end scenario --")
    print(f"Current Phi:   {s2['current_phi']:.3f}")
    print(f"Predicted Phi: {s2['predicted_phi']:.3f} (+30 steps)")
    print(f"Dead-end prob: {s2['dead_end_prob']:.2%}")
    print(f"Verdict:       {s2['verdict']}")

    print()

    # Simulate a plateau
    phi3 = [3.0 + rng.normal(0, 0.01) for _ in range(80)]
    s3 = fit_and_predict(phi3, steps_ahead=50)
    print("-- Plateau scenario --")
    print(f"Predicted Phi: {s3['predicted_phi']:.3f}")
    print(f"Plateau prob:  {s3['plateau_prob']:.2%}")
    print(f"Verdict:       {s3['verdict']}")


if __name__ == "__main__":
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()
