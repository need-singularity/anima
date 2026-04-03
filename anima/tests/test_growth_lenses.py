"""Tests for growth_lenses.py — GrowthRateLens, AccelEfficiencyLens, SaturationLens."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest
from growth_lenses import (
    GrowthRateLens,
    AccelEfficiencyLens,
    SaturationLens,
    scan_growth,
)


# ---------------------------------------------------------------------------
# GrowthRateLens
# ---------------------------------------------------------------------------

def test_growth_rate_positive_slope():
    history = [(i, i * 2.0) for i in range(20)]  # slope = 2.0
    result = GrowthRateLens(history)
    assert result.growth_rate > 0.001
    assert result.is_growing is True
    assert result.status == "growing"
    assert result.r_squared > 0.99


def test_growth_rate_negative_slope():
    history = [(i, 100.0 - i * 3.0) for i in range(20)]  # slope = -3.0
    result = GrowthRateLens(history)
    assert result.growth_rate < 0
    assert result.is_growing is False
    assert result.status == "decaying"


def test_growth_rate_stalling():
    history = [(i, 5.0 + i * 0.0005) for i in range(30)]  # tiny slope
    result = GrowthRateLens(history)
    assert result.is_growing is False
    assert result.status == "stalling"


def test_growth_rate_exploding():
    history = [(i, i * 50.0) for i in range(10)]  # slope = 50, > 10
    result = GrowthRateLens(history)
    assert result.status == "exploding"


def test_growth_rate_acceleration_positive():
    # Second half grows faster than first half
    first = [(i, i * 1.0) for i in range(10)]
    second = [(10 + i, 10.0 + i * 5.0) for i in range(10)]
    history = first + second
    result = GrowthRateLens(history)
    assert result.is_accelerating is True


def test_growth_rate_single_point_no_crash():
    result = GrowthRateLens([(0, 1.0)])
    assert result.growth_rate == 0.0
    assert result.status == "stalling"


# ---------------------------------------------------------------------------
# AccelEfficiencyLens
# ---------------------------------------------------------------------------

def test_accel_efficiency_above_baseline():
    # Using 0.5 compute fraction → efficiency_ratio should be ~2x baseline
    history = [(i, float(i), 0.5) for i in range(10)]
    result = AccelEfficiencyLens(history)
    assert result.is_efficient is True
    assert result.efficiency_ratio > 1.0


def test_accel_efficiency_below_baseline():
    # Using 2.0 compute fraction → less efficient
    history = [(i, float(i), 2.0) for i in range(10)]
    result = AccelEfficiencyLens(history)
    assert result.is_efficient is False
    assert result.efficiency_ratio < 1.0


def test_accel_efficiency_baseline():
    # compute_fraction=1.0 for all → efficiency_ratio == 1.0
    history = [(i, float(i), 1.0) for i in range(10)]
    result = AccelEfficiencyLens(history)
    assert abs(result.efficiency_ratio - 1.0) < 1e-6


def test_accel_efficiency_total_compute():
    history = [(i, float(i), 0.5) for i in range(4)]
    result = AccelEfficiencyLens(history)
    assert abs(result.total_compute - 2.0) < 1e-6  # 4 * 0.5


def test_accel_efficiency_single_point_no_crash():
    result = AccelEfficiencyLens([(0, 5.0, 1.0)])
    assert result.efficiency_ratio == 1.0


# ---------------------------------------------------------------------------
# SaturationLens
# ---------------------------------------------------------------------------

def test_saturation_not_saturated():
    # Linearly growing phi — not saturated
    history = [(i, i * 3.0) for i in range(40)]
    result = SaturationLens(history)
    assert result.saturation_pct < 50.0
    assert result.is_plateau is False


def test_saturation_fully_saturated():
    # Flat phi — fully saturated
    history = [(i, 42.0) for i in range(40)]
    result = SaturationLens(history)
    assert result.saturation_pct >= 90.0
    assert result.is_plateau is True


def test_saturation_overshoot():
    # Phi rises then falls
    history = [(i, float(i) if i <= 15 else 15.0 - (i - 15) * 0.5) for i in range(30)]
    result = SaturationLens(history)
    assert result.is_overshoot is True


def test_saturation_not_overshoot():
    # Strictly increasing
    history = [(i, float(i)) for i in range(30)]
    result = SaturationLens(history)
    assert result.is_overshoot is False


def test_saturation_too_few_points():
    result = SaturationLens([(0, 1.0), (1, 2.0)])
    assert result.saturation_pct == 0.0
    assert result.time_to_saturation_est == float("inf")


# ---------------------------------------------------------------------------
# scan_growth (combined)
# ---------------------------------------------------------------------------

def test_scan_growth_returns_all_keys():
    history = [(i, float(i)) for i in range(20)]
    report = scan_growth(history)
    assert "growth_rate" in report
    assert "accel_efficiency" in report
    assert "saturation" in report


def test_scan_growth_growth_rate_keys():
    history = [(i, float(i)) for i in range(20)]
    report = scan_growth(history)
    gr = report["growth_rate"]
    for key in ("growth_rate", "acceleration", "r_squared", "is_growing", "is_accelerating", "status"):
        assert key in gr, f"Missing key: {key}"


def test_scan_growth_with_compute_history():
    phi_hist = [(i, float(i)) for i in range(20)]
    compute_hist = [(i, float(i), 0.5) for i in range(20)]
    report = scan_growth(phi_hist, compute_hist)
    ae = report["accel_efficiency"]
    assert ae["is_efficient"] is True
    assert ae["efficiency_ratio"] > 1.0


def test_scan_growth_without_compute_history_defaults():
    history = [(i, float(i)) for i in range(20)]
    report = scan_growth(history)
    ae = report["accel_efficiency"]
    # baseline compute_fraction=1.0 → efficiency_ratio == 1.0
    assert abs(ae["efficiency_ratio"] - 1.0) < 1e-6


def test_scan_growth_saturation_keys():
    history = [(i, float(i)) for i in range(20)]
    report = scan_growth(history)
    sat = report["saturation"]
    for key in ("saturation_pct", "time_to_saturation_est", "is_plateau", "is_overshoot"):
        assert key in sat, f"Missing key: {key}"
