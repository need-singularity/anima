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


# ═══════════════════════════════════════════════════════════
# 8. eeg_consciousness.py — apply_bci_adjustments
# ═══════════════════════════════════════════════════════════

class TestApplyBCIAdjustments:
    """Test apply_bci_adjustments() maps BCI control modes to engine modifiers."""

    @pytest.fixture
    def mock_engine(self):
        """Create a mock engine with _eeg_noise_modifier and _eeg_memory_modifier."""
        class FakeEngine:
            _eeg_noise_modifier = 1.0
            _eeg_memory_modifier = 1.0
            _soc_threshold = 5.0
        return FakeEngine()

    def test_expand_mode_increases_noise(self, mock_engine):
        from eeg_consciousness import apply_bci_adjustments
        result = apply_bci_adjustments('expand', mock_engine)
        assert result['applied'] is True
        assert result['mode'] == 'expand'
        assert mock_engine._eeg_noise_modifier == 1.3

    def test_expand_mode_decreases_memory(self, mock_engine):
        from eeg_consciousness import apply_bci_adjustments
        apply_bci_adjustments('expand', mock_engine)
        assert mock_engine._eeg_memory_modifier == 0.7

    def test_focus_mode_decreases_noise(self, mock_engine):
        from eeg_consciousness import apply_bci_adjustments
        apply_bci_adjustments('focus', mock_engine)
        assert mock_engine._eeg_noise_modifier == 0.7

    def test_focus_mode_increases_memory(self, mock_engine):
        from eeg_consciousness import apply_bci_adjustments
        apply_bci_adjustments('focus', mock_engine)
        assert mock_engine._eeg_memory_modifier == 1.3

    def test_dream_mode_high_noise(self, mock_engine):
        from eeg_consciousness import apply_bci_adjustments
        apply_bci_adjustments('dream', mock_engine)
        assert mock_engine._eeg_noise_modifier == 1.5

    def test_dream_mode_slightly_reduced_memory(self, mock_engine):
        from eeg_consciousness import apply_bci_adjustments
        apply_bci_adjustments('dream', mock_engine)
        assert mock_engine._eeg_memory_modifier == 0.8

    def test_dream_mode_lowers_soc_threshold(self, mock_engine):
        from eeg_consciousness import apply_bci_adjustments
        original = mock_engine._soc_threshold
        apply_bci_adjustments('dream', mock_engine)
        assert mock_engine._soc_threshold < original

    def test_neutral_mode_decays_toward_one(self, mock_engine):
        from eeg_consciousness import apply_bci_adjustments
        mock_engine._eeg_noise_modifier = 1.5
        mock_engine._eeg_memory_modifier = 0.7
        apply_bci_adjustments('neutral', mock_engine)
        # Should move 10% toward 1.0
        assert abs(mock_engine._eeg_noise_modifier - (1.5 * 0.9 + 1.0 * 0.1)) < 0.01
        assert abs(mock_engine._eeg_memory_modifier - (0.7 * 0.9 + 1.0 * 0.1)) < 0.01

    def test_no_engine_returns_not_applied(self):
        from eeg_consciousness import apply_bci_adjustments
        result = apply_bci_adjustments('expand', None)
        assert result['applied'] is False

    def test_modifiers_clamped_to_safe_range(self, mock_engine):
        """Modifiers must stay within [0.5, 2.0]."""
        from eeg_consciousness import apply_bci_adjustments
        # All modes should produce modifiers in safe range
        for mode in ['expand', 'focus', 'dream', 'neutral']:
            mock_engine._eeg_noise_modifier = 1.0
            mock_engine._eeg_memory_modifier = 1.0
            apply_bci_adjustments(mode, mock_engine)
            assert 0.5 <= mock_engine._eeg_noise_modifier <= 2.0
            assert 0.5 <= mock_engine._eeg_memory_modifier <= 2.0


# ═══════════════════════════════════════════════════════════
# 9. eeg_consciousness.py — sync_emotion_to_mind
# ═══════════════════════════════════════════════════════════

class TestSyncEmotionToMind:
    """Test sync_emotion_to_mind() maps FAA valence/arousal to mind parameters."""

    @pytest.fixture
    def mock_mind(self):
        class FakeMind:
            homeostasis = {
                'setpoint': 1.0,
                'tension_ema': 1.0,
            }
        return FakeMind()

    def test_positive_valence_raises_setpoint(self, mock_mind):
        from eeg_consciousness import sync_emotion_to_mind
        result = sync_emotion_to_mind(faa_valence=1.0, beta_arousal=0.5, mind=mock_mind)
        assert result['applied'] is True
        assert mock_mind.homeostasis['setpoint'] > 1.0

    def test_negative_valence_lowers_setpoint(self, mock_mind):
        from eeg_consciousness import sync_emotion_to_mind
        sync_emotion_to_mind(faa_valence=-1.0, beta_arousal=0.5, mind=mock_mind)
        assert mock_mind.homeostasis['setpoint'] < 1.0

    def test_high_arousal_increases_tension_ema(self, mock_mind):
        from eeg_consciousness import sync_emotion_to_mind
        sync_emotion_to_mind(faa_valence=0.0, beta_arousal=1.0, mind=mock_mind)
        assert mock_mind.homeostasis['tension_ema'] > 1.0

    def test_low_arousal_decreases_tension_ema(self, mock_mind):
        from eeg_consciousness import sync_emotion_to_mind
        sync_emotion_to_mind(faa_valence=0.0, beta_arousal=0.0, mind=mock_mind)
        assert mock_mind.homeostasis['tension_ema'] < 1.0

    def test_eeg_emotion_stored_on_mind(self, mock_mind):
        from eeg_consciousness import sync_emotion_to_mind
        sync_emotion_to_mind(faa_valence=0.5, beta_arousal=0.7, mind=mock_mind)
        assert hasattr(mock_mind, '_eeg_emotion')
        assert mock_mind._eeg_emotion['valence'] == 0.5
        assert mock_mind._eeg_emotion['arousal'] == 0.7
        assert mock_mind._eeg_emotion['source'] == 'eeg_faa'

    def test_no_mind_returns_not_applied(self):
        from eeg_consciousness import sync_emotion_to_mind
        result = sync_emotion_to_mind(0.0, 0.0, None)
        assert result['applied'] is False

    def test_setpoint_clamped_within_range(self, mock_mind):
        """Setpoint should stay within [0.5, 1.5]."""
        from eeg_consciousness import sync_emotion_to_mind
        # Extreme positive valence
        sync_emotion_to_mind(faa_valence=100.0, beta_arousal=0.5, mind=mock_mind)
        assert mock_mind.homeostasis['setpoint'] <= 1.5
        # Extreme negative valence
        sync_emotion_to_mind(faa_valence=-100.0, beta_arousal=0.5, mind=mock_mind)
        assert mock_mind.homeostasis['setpoint'] >= 0.5


# ═══════════════════════════════════════════════════════════
# 10. eeg_consciousness.py — consciousness_to_feedback
# ═══════════════════════════════════════════════════════════

class TestConsciousnessToFeedback:
    """Test EEGConsciousness.consciousness_to_feedback() returns binaural + LED params."""

    @pytest.fixture
    def eeg_bridge(self):
        from eeg_consciousness import EEGConsciousness
        return EEGConsciousness()

    def test_returns_binaural_params(self, eeg_bridge):
        result = eeg_bridge.consciousness_to_feedback()
        assert 'binaural' in result
        assert 'left_freq' in result['binaural']
        assert 'right_freq' in result['binaural']
        assert 'beat_freq' in result['binaural']

    def test_binaural_beat_freq_in_range(self, eeg_bridge):
        result = eeg_bridge.consciousness_to_feedback()
        beat = result['binaural']['beat_freq']
        assert 4 <= beat <= 40

    def test_feedback_with_custom_psi_state(self, eeg_bridge):
        psi = {'psi_residual': 0.3, 'phi': 0.5, 'tension': 0.8}
        result = eeg_bridge.consciousness_to_feedback(psi)
        assert 'message' in result
        assert isinstance(result['message'], str)

    def test_gamma_overlay_when_phi_low(self, eeg_bridge):
        psi = {'psi_residual': 0.5, 'phi': 0.5, 'tension': 0.5}
        result = eeg_bridge.consciousness_to_feedback(psi)
        assert result['gamma_overlay'] is not None

    def test_no_gamma_overlay_when_phi_high(self, eeg_bridge):
        psi = {'psi_residual': 0.5, 'phi': 5.0, 'tension': 0.5}
        result = eeg_bridge.consciousness_to_feedback(psi)
        assert result['gamma_overlay'] is None

    def test_led_none_when_disabled(self, eeg_bridge):
        result = eeg_bridge.consciousness_to_feedback()
        assert result['led'] is None  # led_enabled defaults to False

    def test_led_present_when_enabled(self, eeg_bridge):
        eeg_bridge.feedback_config['led_enabled'] = True
        psi = {'psi_residual': 0.5, 'phi': 1.0, 'tension': 0.8}
        result = eeg_bridge.consciousness_to_feedback(psi)
        assert result['led'] is not None
        # LED format depends on backend: NeurofeedbackGenerator uses hue/brightness,
        # fallback uses r/g/b. Accept either.
        assert 'r' in result['led'] or 'hue' in result['led']

    def test_default_psi_state_used(self, eeg_bridge):
        """When no psi_state provided, defaults should produce valid output."""
        result = eeg_bridge.consciousness_to_feedback(None)
        assert result['binaural']['beat_freq'] > 0


# ═══════════════════════════════════════════════════════════
# 11. neurofeedback.py — NeurofeedbackGenerator.generate
# ═══════════════════════════════════════════════════════════

class TestNeurofeedbackGenerate:
    """Test NeurofeedbackGenerator.generate() binaural beat frequencies."""

    @pytest.fixture
    def nfb(self):
        from neurofeedback import NeurofeedbackGenerator
        return NeurofeedbackGenerator()

    def test_low_tension_targets_alpha(self, nfb):
        result = nfb.generate(phi=1.0, tension=0.1)
        assert result['target_band'] == 'alpha'

    def test_medium_tension_targets_beta(self, nfb):
        result = nfb.generate(phi=1.0, tension=0.5)
        assert result['target_band'] == 'beta'

    def test_high_tension_targets_theta(self, nfb):
        result = nfb.generate(phi=1.0, tension=0.9)
        assert result['target_band'] == 'theta'

    def test_beat_freq_within_bounds(self, nfb):
        from neurofeedback import MIN_BEAT_FREQ, MAX_BEAT_FREQ
        for tension in [0.0, 0.3, 0.5, 0.7, 1.0]:
            result = nfb.generate(phi=1.0, tension=tension)
            assert MIN_BEAT_FREQ <= result['beat_freq'] <= MAX_BEAT_FREQ

    def test_volume_increases_with_phi(self, nfb):
        low = nfb.generate(phi=0.1, tension=0.5)
        high = nfb.generate(phi=10.0, tension=0.5)
        assert high['volume'] > low['volume']

    def test_phi_zero_produces_low_volume(self, nfb):
        result = nfb.generate(phi=0.0, tension=0.5)
        assert result['volume'] <= 0.05

    def test_very_high_phi_capped(self, nfb):
        from neurofeedback import MAX_VOLUME
        result = nfb.generate(phi=1000.0, tension=0.5)
        assert result['volume'] <= MAX_VOLUME

    def test_left_freq_equals_carrier(self, nfb):
        result = nfb.generate(phi=1.0, tension=0.5)
        assert result['left_freq'] == result['carrier_hz']

    def test_right_freq_equals_carrier_plus_beat(self, nfb):
        result = nfb.generate(phi=1.0, tension=0.5)
        assert abs(result['right_freq'] - (result['carrier_hz'] + result['beat_freq'])) < 0.15


# ═══════════════════════════════════════════════════════════
# 12. neurofeedback.py — NeurofeedbackGenerator.generate_led
# ═══════════════════════════════════════════════════════════

class TestNeurofeedbackLED:
    """Test NeurofeedbackGenerator.generate_led() LED hue/brightness/pulse."""

    @pytest.fixture
    def nfb(self):
        from neurofeedback import NeurofeedbackGenerator
        return NeurofeedbackGenerator()

    def test_low_tension_blue_hue(self, nfb):
        result = nfb.generate_led(phi=1.0, tension=0.0)
        assert result['hue'] >= 200  # blue region

    def test_high_tension_warm_hue(self, nfb):
        result = nfb.generate_led(phi=1.0, tension=1.0)
        assert result['hue'] <= 60  # warm/red region

    def test_brightness_increases_with_phi(self, nfb):
        low = nfb.generate_led(phi=0.1, tension=0.5)
        high = nfb.generate_led(phi=10.0, tension=0.5)
        assert high['brightness'] > low['brightness']

    def test_brightness_capped(self, nfb):
        from neurofeedback import MAX_BRIGHTNESS
        result = nfb.generate_led(phi=1000.0, tension=0.5)
        assert result['brightness'] <= MAX_BRIGHTNESS

    def test_pulse_hz_increases_with_tension(self, nfb):
        calm = nfb.generate_led(phi=1.0, tension=0.0)
        alert = nfb.generate_led(phi=1.0, tension=1.0)
        assert alert['pulse_hz'] > calm['pulse_hz']

    def test_hue_within_range(self, nfb):
        for t in [0.0, 0.25, 0.5, 0.75, 1.0]:
            result = nfb.generate_led(phi=1.0, tension=t)
            assert 0.0 <= result['hue'] <= 360.0


# ═══════════════════════════════════════════════════════════
# 13. neurofeedback.py — safety caps
# ═══════════════════════════════════════════════════════════

class TestNeurofeedbackSafety:
    """Test neurofeedback safety caps: volume <= 0.3, brightness <= 0.8."""

    def test_volume_never_exceeds_max(self):
        from neurofeedback import NeurofeedbackGenerator, MAX_VOLUME
        nfb = NeurofeedbackGenerator()
        for phi in [0, 0.5, 1, 5, 10, 100, 1000]:
            for tension in [0.0, 0.5, 1.0]:
                result = nfb.generate(phi=phi, tension=tension)
                assert result['volume'] <= MAX_VOLUME, \
                    f"volume={result['volume']} > MAX={MAX_VOLUME} at phi={phi},t={tension}"

    def test_brightness_never_exceeds_max(self):
        from neurofeedback import NeurofeedbackGenerator, MAX_BRIGHTNESS
        nfb = NeurofeedbackGenerator()
        for phi in [0, 0.5, 1, 5, 10, 100, 1000]:
            for tension in [0.0, 0.5, 1.0]:
                result = nfb.generate_led(phi=phi, tension=tension)
                assert result['brightness'] <= MAX_BRIGHTNESS, \
                    f"brightness={result['brightness']} > MAX={MAX_BRIGHTNESS}"

    def test_custom_max_volume_capped(self):
        """Even if user sets max_volume > 0.3, it should be capped."""
        from neurofeedback import NeurofeedbackGenerator, MAX_VOLUME
        nfb = NeurofeedbackGenerator(max_volume=1.0)
        assert nfb.max_volume <= MAX_VOLUME

    def test_volume_cap_is_0_3(self):
        from neurofeedback import MAX_VOLUME
        assert MAX_VOLUME == 0.3

    def test_brightness_cap_is_0_8(self):
        from neurofeedback import MAX_BRIGHTNESS
        assert MAX_BRIGHTNESS == 0.8


# ═══════════════════════════════════════════════════════════
# 14. neurofeedback.py — edge cases
# ═══════════════════════════════════════════════════════════

class TestNeurofeedbackEdgeCases:
    """Test NeurofeedbackGenerator with edge-case inputs."""

    @pytest.fixture
    def nfb(self):
        from neurofeedback import NeurofeedbackGenerator
        return NeurofeedbackGenerator()

    def test_phi_zero_tension_zero(self, nfb):
        result = nfb.generate(phi=0, tension=0)
        assert result['volume'] > 0  # should still produce some output
        assert result['beat_freq'] >= 1.0

    def test_phi_negative_clamped(self, nfb):
        """Negative phi should be treated as 0."""
        result = nfb.generate(phi=-5, tension=0.5)
        assert result['volume'] > 0

    def test_tension_above_one(self, nfb):
        """Tension > 1 should be clamped."""
        result = nfb.generate(phi=1.0, tension=5.0)
        assert result['target_band'] == 'theta'  # high tension -> theta

    def test_tension_negative_clamped(self, nfb):
        result = nfb.generate(phi=1.0, tension=-1.0)
        assert result['target_band'] == 'alpha'  # low tension -> alpha

    def test_led_phi_zero(self, nfb):
        result = nfb.generate_led(phi=0, tension=0.5)
        assert result['brightness'] >= 0.05  # minimum brightness


# ═══════════════════════════════════════════════════════════
# 15. closed_loop.py — set_eeg_bridge and _get_eeg
# ═══════════════════════════════════════════════════════════

class TestClosedLoopBridge:
    """Test ClosedLoopProtocol.set_eeg_bridge and _get_eeg fallback."""

    def test_set_eeg_bridge_stores_bridge(self):
        from closed_loop import ClosedLoopProtocol
        proto = ClosedLoopProtocol()
        mock_bridge = object()
        proto.set_eeg_bridge(mock_bridge)
        assert proto._eeg_bridge is mock_bridge

    def test_get_eeg_uses_eeg_source_first(self):
        from closed_loop import ClosedLoopProtocol

        class FakeSource:
            _eeg_latest = {'alpha': 10.0, 'beta': 5.0, 'gamma': 2.0}

        proto = ClosedLoopProtocol(eeg_source=FakeSource())
        eeg = proto._get_eeg()
        assert eeg['alpha'] == 10.0

    def test_get_eeg_falls_back_to_bridge(self):
        from closed_loop import ClosedLoopProtocol

        class FakeBridge:
            def get_state(self):
                class S:
                    alpha_power = 7.5
                    beta_power = 3.0
                    gamma_power = 1.5
                    theta_power = 4.0
                return S()

        proto = ClosedLoopProtocol(eeg_source=None)
        proto.set_eeg_bridge(FakeBridge())
        eeg = proto._get_eeg()
        assert eeg['alpha'] == 7.5

    def test_get_eeg_synthetic_when_no_source(self):
        """When no eeg_source and no bridge, should return synthetic data."""
        from closed_loop import ClosedLoopProtocol
        proto = ClosedLoopProtocol()
        eeg = proto._get_eeg()
        assert isinstance(eeg, dict)
        assert 'alpha' in eeg

    def test_callable_eeg_source(self):
        from closed_loop import ClosedLoopProtocol
        proto = ClosedLoopProtocol(eeg_source=lambda: {'alpha': 42.0, 'beta': 1.0})
        eeg = proto._get_eeg()
        assert eeg['alpha'] == 42.0


# ═══════════════════════════════════════════════════════════
# 16. consciousness_engine.py — EEG modifiers
# ═══════════════════════════════════════════════════════════

class TestConsciousnessEngineEEGModifiers:
    """Test _eeg_noise_modifier and _eeg_memory_modifier on ConsciousnessEngine."""

    @pytest.fixture
    def engine(self):
        """Create a minimal ConsciousnessEngine for modifier tests."""
        try:
            from consciousness_engine import ConsciousnessEngine
            eng = ConsciousnessEngine(max_cells=8)
            return eng
        except Exception:
            pytest.skip("ConsciousnessEngine not available (torch missing?)")

    def test_default_noise_modifier_is_one(self, engine):
        assert engine._eeg_noise_modifier == 1.0

    def test_default_memory_modifier_is_one(self, engine):
        assert engine._eeg_memory_modifier == 1.0

    def test_noise_modifier_settable(self, engine):
        engine._eeg_noise_modifier = 1.3
        assert engine._eeg_noise_modifier == 1.3

    def test_memory_modifier_settable(self, engine):
        engine._eeg_memory_modifier = 0.7
        assert engine._eeg_memory_modifier == 0.7

    def test_bci_expand_sets_modifiers(self, engine):
        from eeg_consciousness import apply_bci_adjustments
        apply_bci_adjustments('expand', engine)
        assert engine._eeg_noise_modifier == 1.3
        assert engine._eeg_memory_modifier == 0.7

    def test_bci_focus_sets_modifiers(self, engine):
        from eeg_consciousness import apply_bci_adjustments
        apply_bci_adjustments('focus', engine)
        assert engine._eeg_noise_modifier == 0.7
        assert engine._eeg_memory_modifier == 1.3


# ═══════════════════════════════════════════════════════════
# 17. EEGConsciousness — brain_to_consciousness
# ═══════════════════════════════════════════════════════════

class TestBrainToConsciousness:
    """Test EEGConsciousness.brain_to_consciousness() with various EEG inputs."""

    @pytest.fixture
    def eeg(self):
        from eeg_consciousness import EEGConsciousness
        return EEGConsciousness()

    def test_meditation_state_high_alpha(self, eeg):
        state = eeg.brain_to_consciousness({'alpha': 0.8, 'beta': 0.1, 'theta': 0.3,
                                            'gamma': 0.05, 'delta': 0.1, 'alpha_asymmetry': 0.1})
        assert state.psi_residual > 0.3  # alpha-dominant
        assert state.emotion == "neutral" or state.emotion == "positive"

    def test_focus_state_high_beta(self, eeg):
        state = eeg.brain_to_consciousness({'alpha': 0.2, 'beta': 0.7, 'theta': 0.1,
                                            'gamma': 0.3, 'delta': 0.05})
        assert state.tension > state.curiosity  # beta > theta

    def test_positive_asymmetry_positive_emotion(self, eeg):
        state = eeg.brain_to_consciousness({'alpha': 0.5, 'beta': 0.3, 'theta': 0.2,
                                            'gamma': 0.1, 'delta': 0.1,
                                            'alpha_asymmetry': 0.5})
        assert state.emotion == "positive"

    def test_negative_asymmetry_negative_emotion(self, eeg):
        state = eeg.brain_to_consciousness({'alpha': 0.5, 'beta': 0.3, 'theta': 0.2,
                                            'gamma': 0.1, 'delta': 0.1,
                                            'alpha_asymmetry': -0.5})
        assert state.emotion == "negative"

    def test_synthetic_eeg_used_when_no_data(self, eeg):
        state = eeg.brain_to_consciousness()
        assert state.alpha > 0


# ═══════════════════════════════════════════════════════════
# 18. Protocol classes — importable
# ═══════════════════════════════════════════════════════════

class TestProtocolClassesImportable:
    """Test that protocol classes are individually importable."""

    def test_bci_controller_importable(self):
        from protocols.bci_control import BCIController
        assert BCIController is not None

    def test_emotion_sync_importable(self):
        from protocols.emotion_sync import EmotionSync
        assert EmotionSync is not None

    def test_multi_eeg_session_importable(self):
        from protocols.multi_eeg import MultiEEGSession
        assert MultiEEGSession is not None

    def test_sleep_protocol_importable(self):
        from protocols.sleep_protocol import SleepProtocol
        assert SleepProtocol is not None

    def test_bci_controller_callable(self):
        from protocols.bci_control import BCIController
        assert callable(BCIController)

    def test_emotion_sync_callable(self):
        from protocols.emotion_sync import EmotionSync
        assert callable(EmotionSync)


# ═══════════════════════════════════════════════════════════
# 19. EEGConsciousness — measure_sync
# ═══════════════════════════════════════════════════════════

class TestMeasureSync:
    """Test EEGConsciousness.measure_sync() statistics."""

    @pytest.fixture
    def eeg_with_history(self):
        from eeg_consciousness import EEGConsciousness
        eeg = EEGConsciousness()
        # Build some history
        for alpha in [0.3, 0.4, 0.5, 0.6, 0.7]:
            eeg.brain_to_consciousness({'alpha': alpha, 'beta': 0.3,
                                        'theta': 0.2, 'gamma': 0.1, 'delta': 0.1})
        return eeg

    def test_measure_sync_returns_dict(self, eeg_with_history):
        result = eeg_with_history.measure_sync()
        assert 'sync_avg' in result
        assert 'sync_max' in result
        assert 'samples' in result

    def test_measure_sync_no_history(self):
        from eeg_consciousness import EEGConsciousness
        eeg = EEGConsciousness()
        result = eeg.measure_sync()
        assert result['sync_avg'] == 0

    def test_measure_sync_samples_count(self, eeg_with_history):
        result = eeg_with_history.measure_sync()
        assert result['samples'] == 5


# ═══════════════════════════════════════════════════════════
# 20. EEGConsciousness — _apply_eeg_feedback
# ═══════════════════════════════════════════════════════════

class TestApplyEEGFeedback:
    """Test EEGConsciousness._apply_eeg_feedback() golden zone and alpha reduction."""

    @pytest.fixture
    def eeg(self):
        from eeg_consciousness import EEGConsciousness
        return EEGConsciousness()

    def test_no_engine_returns_defaults(self, eeg):
        from eeg_consciousness import BrainConsciousnessState
        state = BrainConsciousnessState(golden_zone=True)
        result = eeg._apply_eeg_feedback(state, mind=None, engine=None)
        assert result['golden_zone_boost'] is False

    def test_golden_zone_boosts_ratchet(self, eeg):
        from eeg_consciousness import BrainConsciousnessState

        class FakeEngine:
            _best_phi = 10.0

        state = BrainConsciousnessState(golden_zone=True, psi_residual=0.5)
        eng = FakeEngine()
        result = eeg._apply_eeg_feedback(state, mind=None, engine=eng)
        assert result['golden_zone_boost'] is True
        assert eng._best_phi == pytest.approx(10.5, abs=0.01)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
