"""Growth Lenses — acceleration-focused analysis for consciousness states.

Three lenses for growth maximization:
1. GrowthRateLens: Phi trajectory slope/acceleration
2. AccelEfficiencyLens: Phi gained per compute unit
3. SaturationLens: detect diminishing returns / plateau

Usage:
    from growth_lenses import scan_growth
    report = scan_growth(phi_history, compute_history)
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Tuple


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _linear_regression(x: List[float], y: List[float]) -> Tuple[float, float, float]:
    """Return (slope, intercept, r_squared)."""
    n = len(x)
    if n < 2:
        return 0.0, y[0] if y else 0.0, 0.0
    sx = sum(x)
    sy = sum(y)
    sxx = sum(xi ** 2 for xi in x)
    sxy = sum(xi * yi for xi, yi in zip(x, y))
    denom = n * sxx - sx * sx
    if denom == 0:
        return 0.0, sy / n, 0.0
    slope = (n * sxy - sx * sy) / denom
    intercept = (sy - slope * sx) / n
    y_mean = sy / n
    ss_tot = sum((yi - y_mean) ** 2 for yi in y)
    if ss_tot == 0:
        r2 = 1.0
    else:
        y_pred = [slope * xi + intercept for xi in x]
        ss_res = sum((yi - yp) ** 2 for yi, yp in zip(y, y_pred))
        r2 = 1.0 - ss_res / ss_tot
    return slope, intercept, r2


# ---------------------------------------------------------------------------
# Lens 1: GrowthRateLens
# ---------------------------------------------------------------------------

@dataclass
class GrowthRateResult:
    growth_rate: float          # phi/step (linear slope)
    acceleration: float         # 2nd derivative approximation
    r_squared: float            # goodness of fit
    is_growing: bool            # growth_rate > 0.001/step
    is_accelerating: bool       # acceleration > 0
    status: str                 # "growing" | "stalling" | "decaying" | "exploding"


def GrowthRateLens(phi_history: List[Tuple[float, float]]) -> GrowthRateResult:
    """Analyse Phi trajectory slope and acceleration.

    Args:
        phi_history: list of (step, phi) tuples, at least 2 points.

    Returns:
        GrowthRateResult with slope, acceleration and status flags.
    """
    if len(phi_history) < 2:
        return GrowthRateResult(
            growth_rate=0.0,
            acceleration=0.0,
            r_squared=0.0,
            is_growing=False,
            is_accelerating=False,
            status="stalling",
        )

    steps = [p[0] for p in phi_history]
    phis = [p[1] for p in phi_history]

    slope, _, r2 = _linear_regression(steps, phis)

    # Acceleration: compare slope of first half vs second half
    mid = len(phi_history) // 2
    if mid >= 2 and len(phi_history) - mid >= 2:
        s1, _, _ = _linear_regression(steps[:mid], phis[:mid])
        s2, _, _ = _linear_regression(steps[mid:], phis[mid:])
        acceleration = s2 - s1
    else:
        # Fallback: simple finite difference on slope
        n = len(phis)
        if n >= 3:
            d = [phis[i + 1] - phis[i] for i in range(n - 1)]
            acceleration = d[-1] - d[0]
        else:
            acceleration = 0.0

    STALL_THRESHOLD = 0.001
    EXPLODE_THRESHOLD = 10.0

    is_growing = slope > STALL_THRESHOLD
    is_accelerating = acceleration > 0

    if slope < 0:
        status = "decaying"
    elif abs(slope) < STALL_THRESHOLD:
        status = "stalling"
    elif slope > EXPLODE_THRESHOLD:
        status = "exploding"
    else:
        status = "growing"

    return GrowthRateResult(
        growth_rate=slope,
        acceleration=acceleration,
        r_squared=r2,
        is_growing=is_growing,
        is_accelerating=is_accelerating,
        status=status,
    )


# ---------------------------------------------------------------------------
# Lens 2: AccelEfficiencyLens
# ---------------------------------------------------------------------------

@dataclass
class AccelEfficiencyResult:
    phi_per_compute: float      # total delta_phi / total_compute_used
    efficiency_ratio: float     # phi_per_compute vs baseline (compute_fraction=1.0)
    is_efficient: bool          # efficiency_ratio > 1.0
    total_delta_phi: float
    total_compute: float


def AccelEfficiencyLens(
    compute_history: List[Tuple[float, float, float]],
) -> AccelEfficiencyResult:
    """Measure Phi gained per compute unit.

    Args:
        compute_history: list of (step, phi, compute_fraction) tuples.
            compute_fraction=1.0 is the baseline (no acceleration).

    Returns:
        AccelEfficiencyResult comparing actual vs baseline efficiency.
    """
    if len(compute_history) < 2:
        return AccelEfficiencyResult(
            phi_per_compute=0.0,
            efficiency_ratio=1.0,
            is_efficient=False,
            total_delta_phi=0.0,
            total_compute=0.0,
        )

    phis = [p[1] for p in compute_history]
    computes = [p[2] for p in compute_history]

    total_delta_phi = phis[-1] - phis[0]
    total_compute = sum(computes)

    if total_compute == 0:
        phi_per_compute = 0.0
        efficiency_ratio = 1.0
    else:
        phi_per_compute = total_delta_phi / total_compute

        # Baseline: same delta_phi but compute_fraction=1.0 for every step
        n_steps = len(compute_history)
        baseline_compute = float(n_steps)  # all steps at fraction=1.0
        baseline_phi_per_compute = total_delta_phi / baseline_compute if baseline_compute > 0 else 0.0

        if baseline_phi_per_compute == 0:
            efficiency_ratio = 1.0
        else:
            efficiency_ratio = phi_per_compute / baseline_phi_per_compute

    is_efficient = efficiency_ratio > 1.0

    return AccelEfficiencyResult(
        phi_per_compute=phi_per_compute,
        efficiency_ratio=efficiency_ratio,
        is_efficient=is_efficient,
        total_delta_phi=total_delta_phi,
        total_compute=total_compute,
    )


# ---------------------------------------------------------------------------
# Lens 3: SaturationLens
# ---------------------------------------------------------------------------

@dataclass
class SaturationResult:
    saturation_pct: float           # 0=growing freely, 100=fully saturated
    time_to_saturation_est: float   # estimated steps until saturation (inf if not plateauing)
    is_plateau: bool                # recent growth < 10% of early growth
    is_overshoot: bool              # phi dropping after peak
    early_growth_rate: float
    recent_growth_rate: float


def SaturationLens(phi_history: List[Tuple[float, float]]) -> SaturationResult:
    """Detect diminishing returns and plateau in Phi trajectory.

    Args:
        phi_history: list of (step, phi) tuples, at least 4 points recommended.

    Returns:
        SaturationResult with saturation percentage and diagnostics.
    """
    if len(phi_history) < 4:
        return SaturationResult(
            saturation_pct=0.0,
            time_to_saturation_est=float("inf"),
            is_plateau=False,
            is_overshoot=False,
            early_growth_rate=0.0,
            recent_growth_rate=0.0,
        )

    steps = [p[0] for p in phi_history]
    phis = [p[1] for p in phi_history]
    n = len(phi_history)

    window = max(1, int(n * 0.2))
    early = phi_history[:window]
    recent = phi_history[-window:]

    early_slope, _, _ = _linear_regression(
        [p[0] for p in early], [p[1] for p in early]
    )
    recent_slope, _, _ = _linear_regression(
        [p[0] for p in recent], [p[1] for p in recent]
    )

    # Saturation: ratio of recent growth to early growth (clamped 0-100)
    if abs(early_slope) < 1e-9:
        if abs(recent_slope) < 1e-9:
            saturation_pct = 100.0
        else:
            saturation_pct = 0.0
    else:
        ratio = recent_slope / early_slope
        # 1.0 ratio = no saturation (0%), 0.0 or negative = fully saturated (100%)
        saturation_pct = max(0.0, min(100.0, (1.0 - ratio) * 100.0))

    PLATEAU_THRESHOLD = 1e-4
    if early_slope > PLATEAU_THRESHOLD:
        is_plateau = recent_slope < 0.1 * early_slope
    else:
        # Early growth was already negligible — flat from the start counts as plateau
        is_plateau = abs(recent_slope) < PLATEAU_THRESHOLD

    # Overshoot: current phi is below the peak
    peak_phi = max(phis)
    current_phi = phis[-1]
    is_overshoot = current_phi < peak_phi * 0.99  # 1% tolerance

    # Time to saturation estimate: at current deceleration rate, when does growth → 0?
    deceleration = early_slope - recent_slope  # positive means slowing
    steps_elapsed = steps[-1] - steps[0]
    if deceleration > 0 and steps_elapsed > 0:
        # simple linear extrapolation of the deceleration trend
        steps_per_unit_decel = steps_elapsed / deceleration if deceleration else float("inf")
        remaining_slope = recent_slope
        if remaining_slope > 0:
            time_to_saturation_est = remaining_slope * steps_per_unit_decel
        else:
            time_to_saturation_est = 0.0
    else:
        time_to_saturation_est = float("inf")

    return SaturationResult(
        saturation_pct=saturation_pct,
        time_to_saturation_est=time_to_saturation_est,
        is_plateau=is_plateau,
        is_overshoot=is_overshoot,
        early_growth_rate=early_slope,
        recent_growth_rate=recent_slope,
    )


# ---------------------------------------------------------------------------
# Combined scan
# ---------------------------------------------------------------------------

def scan_growth(
    phi_history: List[Tuple[float, float]],
    compute_history: Optional[List[Tuple[float, float, float]]] = None,
) -> dict:
    """Run all 3 growth lenses and return a unified report dict.

    Args:
        phi_history: list of (step, phi) tuples.
        compute_history: optional list of (step, phi, compute_fraction) tuples.
            If None, a baseline compute_fraction=1.0 is assumed for each step.

    Returns:
        dict with keys: growth_rate, accel_efficiency, saturation.
    """
    gr = GrowthRateLens(phi_history)

    if compute_history is None:
        # Build default compute history from phi_history with fraction=1.0
        compute_history = [(s, p, 1.0) for s, p in phi_history]
    ae = AccelEfficiencyLens(compute_history)

    sat = SaturationLens(phi_history)

    return {
        "growth_rate": asdict(gr),
        "accel_efficiency": asdict(ae),
        "saturation": asdict(sat),
    }
