#!/usr/bin/env python3
"""Auto-generated tests for independent_rate_measurement (meta_loop L1)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import pytest


class TestIndependentRateMeasurementImport:
    """Verify module imports without error."""

    def test_import(self):
        import independent_rate_measurement


def test_init_gru_params_exists():
    """Verify init_gru_params is callable."""
    from independent_rate_measurement import init_gru_params
    assert callable(init_gru_params)


def test_gru_step_exists():
    """Verify gru_step is callable."""
    from independent_rate_measurement import gru_step
    assert callable(gru_step)


def test_init_engine_exists():
    """Verify init_engine is callable."""
    from independent_rate_measurement import init_engine
    assert callable(init_engine)


def test_compute_repulsion_exists():
    """Verify compute_repulsion is callable."""
    from independent_rate_measurement import compute_repulsion
    assert callable(compute_repulsion)


def test_compute_entropy_exists():
    """Verify compute_entropy is callable."""
    from independent_rate_measurement import compute_entropy
    assert callable(compute_entropy)


def test_compute_entropy_softmax_exists():
    """Verify compute_entropy_softmax is callable."""
    from independent_rate_measurement import compute_entropy_softmax
    assert callable(compute_entropy_softmax)


def test_compute_entropy_variance_exists():
    """Verify compute_entropy_variance is callable."""
    from independent_rate_measurement import compute_entropy_variance
    assert callable(compute_entropy_variance)


def test_engine_step_exists():
    """Verify engine_step is callable."""
    from independent_rate_measurement import engine_step
    assert callable(engine_step)


def test_gen_random_input_exists():
    """Verify gen_random_input is callable."""
    from independent_rate_measurement import gen_random_input
    assert callable(gen_random_input)


def test_gen_sine_input_exists():
    """Verify gen_sine_input is callable."""
    from independent_rate_measurement import gen_sine_input
    assert callable(gen_sine_input)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
