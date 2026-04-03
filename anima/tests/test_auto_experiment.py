#!/usr/bin/env python3
"""Tests for auto_experiment.py — automated hypothesis experiment pipeline."""

import os
import sys
import math
import json
import tempfile
import pytest
from unittest.mock import patch, MagicMock
from dataclasses import dataclass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


# ═══════════════════════════════════════════
# Test RepResult and ExperimentResult dataclasses
# ═══════════════════════════════════════════

class TestRepResult:
    def test_basic_creation(self):
        from auto_experiment import RepResult
        r = RepResult(
            rep=0,
            phi_baseline=1.0,
            phi_with_intervention=1.2,
            phi_retention_pct=120.0,
            phi_delta_pct=20.0,
            ce_baseline=0.5,
            ce_with_intervention=0.4,
        )
        assert r.rep == 0
        assert r.phi_baseline == 1.0
        assert r.phi_delta_pct == 20.0

    def test_negative_delta(self):
        from auto_experiment import RepResult
        r = RepResult(
            rep=1,
            phi_baseline=1.0,
            phi_with_intervention=0.8,
            phi_retention_pct=80.0,
            phi_delta_pct=-20.0,
            ce_baseline=0.5,
            ce_with_intervention=0.6,
        )
        assert r.phi_delta_pct == -20.0
        assert r.phi_retention_pct == 80.0


class TestExperimentResult:
    def test_verified_property(self):
        from auto_experiment import ExperimentResult
        r = ExperimentResult(
            hypothesis="test",
            intervention_name="test_iv",
            template="coupling",
            reps=[],
            phi_baseline_mean=1.0,
            phi_with_mean=1.5,
            phi_delta_pct_mean=50.0,
            phi_delta_pct_cv=0.1,
            direction_consistent=True,
            verdict="VERIFIED",
            verdict_reason="good",
            new_law_id=None,
            new_law_text=None,
            time_sec=1.0,
        )
        assert r.verified is True

    def test_not_verified(self):
        from auto_experiment import ExperimentResult
        r = ExperimentResult(
            hypothesis="test",
            intervention_name=None,
            template=None,
            reps=[],
            phi_baseline_mean=0.0,
            phi_with_mean=0.0,
            phi_delta_pct_mean=0.0,
            phi_delta_pct_cv=0.0,
            direction_consistent=False,
            verdict="REJECTED",
            verdict_reason="bad",
            new_law_id=None,
            new_law_text=None,
            time_sec=0.5,
        )
        assert r.verified is False

    def test_inconclusive_not_verified(self):
        from auto_experiment import ExperimentResult
        r = ExperimentResult(
            hypothesis="test",
            intervention_name=None,
            template=None,
            reps=[],
            phi_baseline_mean=0.0,
            phi_with_mean=0.0,
            phi_delta_pct_mean=0.0,
            phi_delta_pct_cv=0.0,
            direction_consistent=False,
            verdict="INCONCLUSIVE",
            verdict_reason="unclear",
            new_law_id=None,
            new_law_text=None,
            time_sec=0.5,
        )
        assert r.verified is False


# ═══════════════════════════════════════════
# Test _compute_verdict
# ═══════════════════════════════════════════

class TestComputeVerdict:
    def _make_rep(self, delta_pct):
        from auto_experiment import RepResult
        return RepResult(
            rep=0, phi_baseline=1.0,
            phi_with_intervention=1.0 + delta_pct / 100.0,
            phi_retention_pct=100 + delta_pct,
            phi_delta_pct=delta_pct,
            ce_baseline=0.5, ce_with_intervention=0.5,
        )

    def test_empty_reps(self):
        from auto_experiment import _compute_verdict
        verdict, reason = _compute_verdict([])
        assert verdict == "INCONCLUSIVE"

    def test_all_positive_large(self):
        from auto_experiment import _compute_verdict
        reps = [self._make_rep(20.0), self._make_rep(25.0), self._make_rep(22.0)]
        verdict, reason = _compute_verdict(reps)
        assert verdict == "VERIFIED"

    def test_all_negative(self):
        from auto_experiment import _compute_verdict
        reps = [self._make_rep(-10.0), self._make_rep(-12.0), self._make_rep(-11.0)]
        verdict, reason = _compute_verdict(reps)
        assert verdict == "REJECTED"

    def test_mixed_direction_inconclusive(self):
        from auto_experiment import _compute_verdict
        reps = [self._make_rep(10.0), self._make_rep(-5.0), self._make_rep(8.0)]
        verdict, reason = _compute_verdict(reps)
        assert verdict == "INCONCLUSIVE"
        assert "inconsistent" in reason.lower()

    def test_small_effect_inconclusive(self):
        from auto_experiment import _compute_verdict
        reps = [self._make_rep(1.0), self._make_rep(2.0), self._make_rep(1.5)]
        verdict, reason = _compute_verdict(reps)
        assert verdict == "INCONCLUSIVE"
        assert "threshold" in reason.lower()

    def test_high_variance_inconclusive(self):
        from auto_experiment import _compute_verdict
        reps = [self._make_rep(50.0), self._make_rep(5.0), self._make_rep(45.0)]
        # All positive but high CV
        verdict, reason = _compute_verdict(reps)
        # Could be VERIFIED or INCONCLUSIVE depending on CV threshold
        assert verdict in ("VERIFIED", "INCONCLUSIVE")


# ═══════════════════════════════════════════
# Test _make_engine
# ═══════════════════════════════════════════

class TestMakeEngine:
    def test_creates_engine(self):
        from auto_experiment import _make_engine
        engine = _make_engine(max_cells=8)
        assert engine is not None
        assert hasattr(engine, 'step')
        assert hasattr(engine, 'n_cells')

    def test_engine_steps(self):
        from auto_experiment import _make_engine
        engine = _make_engine(max_cells=8)
        result = engine.step()
        assert isinstance(result, dict)


# ═══════════════════════════════════════════
# Test AutoExperiment class initialization
# ═══════════════════════════════════════════

class TestAutoExperimentInit:
    def test_default_init(self):
        from auto_experiment import AutoExperiment
        ae = AutoExperiment(max_cells=8, steps=10, reps=1)
        assert ae.max_cells == 8
        assert ae.steps == 10
        assert ae.reps == 1
        assert ae.history == []

    def test_custom_thresholds(self):
        from auto_experiment import AutoExperiment
        ae = AutoExperiment(
            max_cells=8, steps=10, reps=1,
            phi_threshold=0.10,
            cv_threshold=0.30,
        )
        assert ae.phi_threshold == 0.10
        assert ae.cv_threshold == 0.30

    def test_find_laws_path(self):
        from auto_experiment import AutoExperiment
        ae = AutoExperiment(max_cells=8, steps=10, reps=1)
        # Should find the laws path (or None if not present)
        # The constructor calls _find_laws_path internally
        # Just verify no crash
        assert ae._laws_path is None or os.path.exists(ae._laws_path)


# ═══════════════════════════════════════════
# Test _phi_fast fallback
# ═══════════════════════════════════════════

class TestPhiFast:
    def test_phi_fast_computes(self):
        from auto_experiment import _phi_fast, _make_engine
        engine = _make_engine(max_cells=8)
        # Run a few steps to get cells populated
        for _ in range(10):
            engine.step()
        phi = _phi_fast(engine)
        assert isinstance(phi, float)
        assert phi >= 0.0


# ═══════════════════════════════════════════
# Test _run_one_rep
# ═══════════════════════════════════════════

class TestRunOneRep:
    def test_run_without_intervention(self):
        from auto_experiment import _run_one_rep
        phi_b, phi_w, ce_b, ce_w = _run_one_rep(
            intervention=None, steps=20, max_cells=8,
        )
        assert isinstance(phi_b, float)
        assert isinstance(phi_w, float)
        # Both should be similar since no intervention
        assert phi_b >= 0.0
        assert phi_w >= 0.0

    def test_run_with_noop_intervention(self):
        from auto_experiment import _run_one_rep, Intervention
        noop = Intervention(
            name="noop",
            description="does nothing",
            apply_fn=lambda engine, step: None,
        )
        phi_b, phi_w, ce_b, ce_w = _run_one_rep(
            intervention=noop, steps=20, max_cells=8,
        )
        assert isinstance(phi_b, float)
        assert isinstance(phi_w, float)


# ═══════════════════════════════════════════
# Test AutoExperiment.design_and_run (no intervention match)
# ═══════════════════════════════════════════

class TestDesignAndRun:
    def test_no_intervention_returns_no_intervention(self):
        from auto_experiment import AutoExperiment
        ae = AutoExperiment(max_cells=8, steps=10, reps=1, auto_register=False)
        # If InterventionGenerator is not available, should return NO_INTERVENTION
        if ae._gen is None:
            result = ae.design_and_run("some random hypothesis", verbose=False)
            assert result.verdict == "NO_INTERVENTION"
            assert len(ae.history) == 1

    def test_format_law_text(self):
        from auto_experiment import AutoExperiment, ExperimentResult
        ae = AutoExperiment(max_cells=8, steps=10, reps=1, auto_register=False)
        mock_result = ExperimentResult(
            hypothesis="test",
            intervention_name="test_iv",
            template="coupling",
            reps=[],
            phi_baseline_mean=1.0,
            phi_with_mean=1.2,
            phi_delta_pct_mean=20.0,
            phi_delta_pct_cv=0.15,
            direction_consistent=True,
            verdict="VERIFIED",
            verdict_reason="good",
            new_law_id=None,
            new_law_text=None,
            time_sec=1.0,
        )
        text = ae._format_law_text("Phi increases with coupling", mock_result)
        assert "Phi increases with coupling" in text
        assert "+20.0%" in text
        assert "AutoExperiment" in text


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
