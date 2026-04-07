#!/usr/bin/env python3
"""Auto-generated tests for experiment_temperature (meta_loop L1)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import pytest


class TestExperimentTemperatureImport:
    """Verify module imports without error."""

    def test_import(self):
        import experiment_temperature


def test_measure_temperature_variance_exists():
    """Verify measure_temperature_variance is callable."""
    from experiment_temperature import measure_temperature_variance
    assert callable(measure_temperature_variance)


def test_measure_temperature_boltzmann_exists():
    """Verify measure_temperature_boltzmann is callable."""
    from experiment_temperature import measure_temperature_boltzmann
    assert callable(measure_temperature_boltzmann)


def test_measure_energy_exists():
    """Verify measure_energy is callable."""
    from experiment_temperature import measure_energy
    assert callable(measure_energy)


def test_measure_entropy_exists():
    """Verify measure_entropy is callable."""
    from experiment_temperature import measure_entropy
    assert callable(measure_entropy)


def test_inject_noise_exists():
    """Verify inject_noise is callable."""
    from experiment_temperature import inject_noise
    assert callable(inject_noise)


def test_ascii_graph_exists():
    """Verify ascii_graph is callable."""
    from experiment_temperature import ascii_graph
    assert callable(ascii_graph)


def test_ascii_dual_graph_exists():
    """Verify ascii_dual_graph is callable."""
    from experiment_temperature import ascii_dual_graph
    assert callable(ascii_dual_graph)


def test_experiment_1_baseline_exists():
    """Verify experiment_1_baseline is callable."""
    from experiment_temperature import experiment_1_baseline
    assert callable(experiment_1_baseline)


def test_experiment_2_phase_transition_exists():
    """Verify experiment_2_phase_transition is callable."""
    from experiment_temperature import experiment_2_phase_transition
    assert callable(experiment_2_phase_transition)


def test_experiment_3_hysteresis_exists():
    """Verify experiment_3_hysteresis is callable."""
    from experiment_temperature import experiment_3_hysteresis
    assert callable(experiment_3_hysteresis)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
