#!/usr/bin/env python3
"""Auto-generated tests for experiment_phase_transition (meta_loop L1)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import pytest


class TestExperimentPhaseTransitionImport:
    """Verify module imports without error."""

    def test_import(self):
        import experiment_phase_transition


def test_measure_entropy_exists():
    """Verify measure_entropy is callable."""
    from experiment_phase_transition import measure_entropy
    assert callable(measure_entropy)


def test_measure_cell_diversity_exists():
    """Verify measure_cell_diversity is callable."""
    from experiment_phase_transition import measure_cell_diversity
    assert callable(measure_cell_diversity)


def test_detect_bursts_exists():
    """Verify detect_bursts is callable."""
    from experiment_phase_transition import detect_bursts
    assert callable(detect_bursts)


def test_detect_self_reference_exists():
    """Verify detect_self_reference is callable."""
    from experiment_phase_transition import detect_self_reference
    assert callable(detect_self_reference)


def test_run_single_experiment_exists():
    """Verify run_single_experiment is callable."""
    from experiment_phase_transition import run_single_experiment
    assert callable(run_single_experiment)


def test_find_transitions_exists():
    """Verify find_transitions is callable."""
    from experiment_phase_transition import find_transitions
    assert callable(find_transitions)


def test_print_results_table_exists():
    """Verify print_results_table is callable."""
    from experiment_phase_transition import print_results_table
    assert callable(print_results_table)


def test_print_phi_curve_exists():
    """Verify print_phi_curve is callable."""
    from experiment_phase_transition import print_phi_curve
    assert callable(print_phi_curve)


def test_print_metric_curves_exists():
    """Verify print_metric_curves is callable."""
    from experiment_phase_transition import print_metric_curves
    assert callable(print_metric_curves)


def test_main_exists():
    """Verify main is callable."""
    from experiment_phase_transition import main
    assert callable(main)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
