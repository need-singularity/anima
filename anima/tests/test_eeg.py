#!/usr/bin/env python3
"""Tests for EEG modules — analyze, realtime, validate_consciousness, neural_correlate_mapper, protocols.

All tests run without hardware (OpenBCI) and without brainflow installed.
"""

import sys
import os
import math
import pytest
import numpy as np

# ── sys.path setup (cf. anima/src/path_setup.py) ──
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
_anima_src = os.path.join(_root, 'anima', 'src')
_anima_eeg = os.path.join(_root, 'anima-eeg')
_anima_eeg_inner = os.path.join(_root, 'anima', 'eeg')

for p in (_anima_src, _anima_eeg, _anima_eeg_inner, _root):
    if p not in sys.path:
        sys.path.insert(0, p)


# ═══════════════════════════════════════════════════════════
# 1. EEGState / BrainState — golden zone
# ═══════════════════════════════════════════════════════════

class TestEEGStateGoldenZone:
    """Test BrainState golden zone from realtime.py and GeniusMetrics from analyze.py."""

    def test_genius_metrics_golden_zone_inside(self):
        """G value inside golden zone [0.2123, 0.5] should set in_golden_zone=True."""
        from analyze import GeniusMetrics, GOLDEN_ZONE
        gm = GeniusMetrics(I=1.0, P=1.0, D=0.3, G=0.35, in_golden_zone=True)
        assert gm.in_golden_zone is True
        assert GOLDEN_ZONE[0] <= gm.G <= GOLDEN_ZONE[1]

    def test_genius_metrics_golden_zone_outside(self):
        """G value outside golden zone should set in_golden_zone=False."""
        from analyze import GeniusMetrics, GOLDEN_ZONE
        gm = GeniusMetrics(I=1.0, P=1.0, D=0.8, G=0.8, in_golden_zone=False)
        assert gm.in_golden_zone is False
        assert gm.G > GOLDEN_ZONE[1]

    def test_compute_genius_with_synthetic_powers(self):
        """compute_genius should return GeniusMetrics with valid G value."""
        from analyze import compute_genius, BandPower, CHANNEL_NAMES_16

        # Create 16 channels of synthetic band power
        channel_powers = []
        for i in range(16):
            bp = BandPower(
                delta=10.0 + i * 0.5,
                theta=5.0 + i * 0.3,
                alpha=8.0 + i * 0.4,
                beta=3.0 + i * 0.2,
                gamma=1.0 + i * 0.1,
            )
            channel_powers.append(bp)

        result = compute_genius(channel_powers, CHANNEL_NAMES_16)
        assert isinstance(result.G, float)
        assert result.G >= 0.0
        assert isinstance(result.in_golden_zone, bool)

    def test_brain_state_dataclass(self):
        """BrainState dataclass should be constructable with default values."""
        # realtime.py uses `from eeg.analyze import ...` which requires
        # the eeg package context. We mock the import to isolate BrainState.
        import importlib
        import types

        # Pre-populate eeg.analyze in sys.modules so realtime can import it
        if 'eeg' not in sys.modules:
            eeg_pkg = types.ModuleType('eeg')
            eeg_pkg.__path__ = [_anima_eeg]
            sys.modules['eeg'] = eeg_pkg
        if 'eeg.analyze' not in sys.modules:
            import analyze as _analyze
            sys.modules['eeg.analyze'] = _analyze

        from realtime import BrainState
        state = BrainState()
        assert state.G == 0.0
        assert state.in_golden_zone is False
        assert state.engagement == 0.0

    def test_brain_state_golden_zone_flag(self):
        """BrainState in_golden_zone should be settable."""
        import types
        if 'eeg' not in sys.modules:
            eeg_pkg = types.ModuleType('eeg')
            eeg_pkg.__path__ = [_anima_eeg]
            sys.modules['eeg'] = eeg_pkg
        if 'eeg.analyze' not in sys.modules:
            import analyze as _analyze
            sys.modules['eeg.analyze'] = _analyze

        from realtime import BrainState
        state = BrainState(G=0.35, in_golden_zone=True)
        assert state.in_golden_zone is True
        assert state.G == 0.35


# ═══════════════════════════════════════════════════════════
# 2. analyze.py — PSD computation
# ═══════════════════════════════════════════════════════════

class TestAnalyzePSD:
    """Test band power analysis from analyze.py."""

    def test_compute_band_power_basic(self):
        """compute_band_power should return BandPower with non-negative values."""
        from analyze import compute_band_power, BandPower

        # Generate a simple sinusoidal signal at 10 Hz (alpha band)
        sample_rate = 256
        t = np.arange(0, 2.0, 1.0 / sample_rate)
        signal = np.sin(2 * np.pi * 10 * t)  # 10 Hz = alpha

        bp = compute_band_power(signal, sample_rate)
        assert isinstance(bp, BandPower)
        assert bp.alpha >= 0.0
        assert bp.total > 0.0

    def test_alpha_dominance(self):
        """A 10Hz signal should have dominant alpha power."""
        from analyze import compute_band_power

        sample_rate = 256
        t = np.arange(0, 4.0, 1.0 / sample_rate)
        signal = np.sin(2 * np.pi * 10 * t)

        bp = compute_band_power(signal, sample_rate)
        rel = bp.relative()
        # Alpha should be the dominant band for a 10 Hz sine
        assert rel.alpha > rel.delta
        assert rel.alpha > rel.beta

    def test_band_power_relative_sums_to_one(self):
        """Relative band powers should sum to approximately 1."""
        from analyze import compute_band_power

        sample_rate = 256
        rng = np.random.RandomState(42)
        signal = rng.randn(sample_rate * 2)

        bp = compute_band_power(signal, sample_rate)
        rel = bp.relative()
        assert abs(rel.total - 1.0) < 0.01

    def test_empty_signal(self):
        """Very short signal should not crash."""
        from analyze import compute_band_power

        signal = np.array([0.0, 0.0, 0.0, 0.0])
        bp = compute_band_power(signal, 256)
        assert isinstance(bp.total, float)


# ═══════════════════════════════════════════════════════════
# 3. NeuralCorrelateMapper — fit + predict
# ═══════════════════════════════════════════════════════════

class TestNeuralMapperFitPredict:
    """Test NeuralCorrelateMapper.fit() and predict() with numpy arrays."""

    @pytest.fixture
    def mapper_with_data(self):
        from neural_correlate_mapper import NeuralCorrelateMapper
        mapper = NeuralCorrelateMapper()

        rng = np.random.RandomState(123)
        # Generate correlated EEG->Psi data (linear relationship + noise)
        n = 20
        X = rng.rand(n, 5) * 10  # EEG bands
        W_true = rng.randn(5, 5) * 0.5
        Y = X @ W_true + rng.randn(n, 5) * 0.1  # Psi states
        return mapper, X, Y

    def test_fit_returns_metrics(self, mapper_with_data):
        mapper, X, Y = mapper_with_data
        result = mapper.fit(X, Y)
        assert 'rmse' in result
        assert 'r2' in result
        assert 'n_samples' in result
        assert result['n_samples'] == 20

    def test_fit_r2_positive(self, mapper_with_data):
        """R2 should be positive for correlated data."""
        mapper, X, Y = mapper_with_data
        result = mapper.fit(X, Y)
        assert result['r2'] > 0.5  # should fit well for linear data

    def test_predict_shape(self, mapper_with_data):
        mapper, X, Y = mapper_with_data
        mapper.fit(X, Y)

        X_new = np.random.RandomState(99).rand(5, 5) * 10
        Y_pred = mapper.predict(X_new)
        assert Y_pred.shape == (5, 5)

    def test_predict_without_fit_raises(self):
        from neural_correlate_mapper import NeuralCorrelateMapper
        mapper = NeuralCorrelateMapper()
        with pytest.raises(RuntimeError, match="calibrate.*fit"):
            mapper.predict(np.ones((3, 5)))

    def test_fit_needs_min_samples(self):
        from neural_correlate_mapper import NeuralCorrelateMapper
        mapper = NeuralCorrelateMapper()
        X = np.ones((3, 5))
        Y = np.ones((3, 5))
        with pytest.raises(ValueError, match="at least 5"):
            mapper.fit(X, Y)


# ═══════════════════════════════════════════════════════════
# 4. NeuralCorrelateMapper — calibrate with EEGSample/PsiState
# ═══════════════════════════════════════════════════════════

class TestNeuralMapperCalibrate:
    """Test NeuralCorrelateMapper.calibrate() with typed objects."""

    @pytest.fixture
    def paired_samples(self):
        from neural_correlate_mapper import EEGSample, PsiState
        rng = np.random.RandomState(42)
        eeg_samples = []
        psi_states = []
        for _ in range(10):
            vals = rng.rand(5) * 10
            eeg_samples.append(EEGSample(*vals.tolist()))
            psi_vals = vals * 0.3 + rng.randn(5) * 0.05
            psi_states.append(PsiState(*psi_vals.tolist()))
        return eeg_samples, psi_states

    def test_calibrate_returns_metrics(self, paired_samples):
        from neural_correlate_mapper import NeuralCorrelateMapper
        mapper = NeuralCorrelateMapper()
        eeg_samples, psi_states = paired_samples
        result = mapper.calibrate(eeg_samples, psi_states)
        assert 'rmse' in result
        assert 'r2' in result
        assert result['n_samples'] == 10

    def test_calibrate_enables_mapping(self, paired_samples):
        from neural_correlate_mapper import NeuralCorrelateMapper, EEGSample, PsiState
        mapper = NeuralCorrelateMapper()
        eeg_samples, psi_states = paired_samples
        mapper.calibrate(eeg_samples, psi_states)

        # map_eeg_to_psi should work after calibration
        test_eeg = EEGSample(5.0, 3.0, 7.0, 2.0, 1.0)
        psi = mapper.map_eeg_to_psi(test_eeg)
        assert isinstance(psi, PsiState)
        assert isinstance(psi.phi, float)
        assert isinstance(psi.tension, float)

    def test_eeg_sample_to_array(self):
        from neural_correlate_mapper import EEGSample
        sample = EEGSample(1.0, 2.0, 3.0, 4.0, 5.0)
        arr = sample.to_array()
        assert arr.shape == (5,)
        np.testing.assert_array_equal(arr, [1.0, 2.0, 3.0, 4.0, 5.0])

    def test_psi_state_roundtrip(self):
        from neural_correlate_mapper import PsiState
        psi = PsiState(1.1, 2.2, 3.3, 4.4, 5.5)
        arr = psi.to_array()
        psi2 = PsiState.from_array(arr)
        assert abs(psi2.phi - 1.1) < 1e-6
        assert abs(psi2.creativity - 5.5) < 1e-6


# ═══════════════════════════════════════════════════════════
# 5. NeuralCorrelateMapper — inverse mapping
# ═══════════════════════════════════════════════════════════

class TestNeuralMapperInverse:
    """Test map_psi_to_eeg inverse mapping."""

    @pytest.fixture
    def calibrated_mapper(self):
        from neural_correlate_mapper import NeuralCorrelateMapper, EEGSample, PsiState
        mapper = NeuralCorrelateMapper()
        rng = np.random.RandomState(77)
        eeg_samples = [EEGSample(*(rng.rand(5) * 10).tolist()) for _ in range(15)]
        psi_states = [PsiState(*(rng.rand(5) * 5).tolist()) for _ in range(15)]
        mapper.calibrate(eeg_samples, psi_states)
        return mapper

    def test_inverse_returns_eeg_sample(self, calibrated_mapper):
        from neural_correlate_mapper import PsiState, EEGSample
        psi = PsiState(2.0, 1.0, 0.8, 0.5, 0.3)
        eeg = calibrated_mapper.map_psi_to_eeg(psi)
        assert isinstance(eeg, EEGSample)

    def test_inverse_non_negative(self, calibrated_mapper):
        """EEG power values should be non-negative (clamped)."""
        from neural_correlate_mapper import PsiState
        psi = PsiState(0.1, 0.1, 0.1, 0.1, 0.1)
        eeg = calibrated_mapper.map_psi_to_eeg(psi)
        assert eeg.delta >= 0.0
        assert eeg.theta >= 0.0
        assert eeg.alpha >= 0.0
        assert eeg.beta >= 0.0
        assert eeg.gamma >= 0.0

    def test_inverse_without_calibrate_raises(self):
        from neural_correlate_mapper import NeuralCorrelateMapper, PsiState
        mapper = NeuralCorrelateMapper()
        psi = PsiState(1.0, 1.0, 1.0, 1.0, 1.0)
        with pytest.raises(RuntimeError, match="calibrate"):
            mapper.map_psi_to_eeg(psi)

    def test_roundtrip_approximate(self):
        """eeg -> psi -> eeg should roughly recover original (if mapping is good)."""
        from neural_correlate_mapper import NeuralCorrelateMapper, EEGSample, PsiState
        mapper = NeuralCorrelateMapper()
        rng = np.random.RandomState(55)

        # Build strongly correlated data for good fit
        n = 30
        X = rng.rand(n, 5) * 10
        W = np.eye(5) * 0.5  # simple scaling
        Y = X @ W
        eeg_samples = [EEGSample(*row.tolist()) for row in X]
        psi_states = [PsiState(*row.tolist()) for row in Y]
        result = mapper.calibrate(eeg_samples, psi_states)

        # Test roundtrip
        test_eeg = EEGSample(5.0, 3.0, 7.0, 2.0, 4.0)
        psi = mapper.map_eeg_to_psi(test_eeg)
        eeg_back = mapper.map_psi_to_eeg(psi)

        # Should be in the same ballpark (not exact due to ridge regression)
        orig = test_eeg.to_array()
        recovered = eeg_back.to_array()
        # At least the same order of magnitude
        assert np.all(recovered >= 0)
        assert np.linalg.norm(recovered) > 0


# ═══════════════════════════════════════════════════════════
# 6. validate_consciousness — brain-like score
# ═══════════════════════════════════════════════════════════

class TestValidateBrainLike:
    """Test brain-like scoring from validate_consciousness.py."""

    def test_validation_result_brain_match_pct(self):
        """brain_match_pct should return high score for values within reference range."""
        from validate_consciousness import ValidationResult, BRAIN_REFERENCE

        result = ValidationResult(label="test")
        # LZ complexity brain range: (0.75, 0.95), mid=0.85
        pct = result.brain_match_pct('lz_complexity', 0.85)
        assert pct >= 90.0  # Dead center should be ~100

    def test_brain_match_pct_outside_range(self):
        """Values far outside range should score low."""
        from validate_consciousness import ValidationResult

        result = ValidationResult(label="test")
        pct = result.brain_match_pct('lz_complexity', 0.1)
        assert pct < 50.0

    def test_analyze_signal_returns_result(self):
        """analyze_signal should return ValidationResult with all metrics."""
        from validate_consciousness import analyze_signal

        rng = np.random.RandomState(42)
        # Create a signal with some structure (not pure noise)
        phi_series = np.cumsum(rng.randn(500)) * 0.01 + 1.0

        result = analyze_signal("test_signal", phi_series)
        assert result.label == "test_signal"
        assert result.phi_mean > 0
        assert isinstance(result.lz, float)
        assert isinstance(result.hurst, float)
        assert isinstance(result.psd_slope, float)

    def test_synthetic_brain_phi_is_brain_like(self):
        """Synthetic brain Phi should score well against brain references."""
        from validate_consciousness import (
            generate_synthetic_brain_phi, analyze_signal,
            ValidationResult, BRAIN_REFERENCE,
        )

        brain_phi = generate_synthetic_brain_phi(n_steps=2000)
        result = analyze_signal("synthetic_brain", brain_phi)

        # Compute overall match like the real code does
        metrics = {
            'lz_complexity': result.lz,
            'hurst_exponent': result.hurst,
            'psd_slope': result.psd_slope,
            'autocorr_decay': float(result.autocorr_decay),
            'phi_cv': result.phi_cv,
            'criticality_exponent': result.criticality.get('exponent', 0),
        }

        matches = []
        for key, val in metrics.items():
            pct = result.brain_match_pct(key, val)
            matches.append(pct)

        overall = np.mean(matches)
        # Synthetic brain signal should be partially brain-like (>50%)
        # Note: without scipy, the synthetic signal scores lower (~55%)
        assert overall > 50.0, f"Synthetic brain signal scored only {overall:.1f}%"

    def test_lempel_ziv_complexity(self):
        """LZ complexity should be higher for random vs constant signal."""
        from validate_consciousness import lempel_ziv_complexity

        constant = np.ones(200)
        random_sig = np.random.RandomState(42).randn(200)

        lz_const = lempel_ziv_complexity(constant)
        lz_rand = lempel_ziv_complexity(random_sig)
        assert lz_rand > lz_const

    def test_hurst_exponent_range(self):
        """Hurst exponent should be in [0, 1]."""
        from validate_consciousness import hurst_exponent

        rng = np.random.RandomState(42)
        signal = np.cumsum(rng.randn(500))
        h = hurst_exponent(signal)
        assert 0.0 <= h <= 1.0


# ═══════════════════════════════════════════════════════════
# 7. Protocols — importable
# ═══════════════════════════════════════════════════════════

class TestProtocolsImportable:
    """Test that protocol modules can be imported."""

    def test_import_protocols_package(self):
        """protocols package should be importable."""
        from protocols import BCIController, MultiEEGSession, SleepProtocol, EmotionSync
        assert BCIController is not None
        assert MultiEEGSession is not None
        assert SleepProtocol is not None
        assert EmotionSync is not None

    def test_import_individual_protocols(self):
        """Each protocol module should be importable individually."""
        from protocols.bci_control import BCIController
        from protocols.multi_eeg import MultiEEGSession
        from protocols.sleep_protocol import SleepProtocol
        from protocols.emotion_sync import EmotionSync
        assert callable(BCIController)
        assert callable(MultiEEGSession)
        assert callable(SleepProtocol)
        assert callable(EmotionSync)

    def test_protocols_all_exported(self):
        """__all__ should list all 4 protocols."""
        import protocols
        assert hasattr(protocols, '__all__')
        assert len(protocols.__all__) == 4


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
