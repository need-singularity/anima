#!/usr/bin/env python3
"""Auto-generated tests for experiment_no_memory (meta_loop L1)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import pytest


class TestExperimentNoMemoryImport:
    """Verify module imports without error."""

    def test_import(self):
        import experiment_no_memory


def test_measure_phi_exists():
    """Verify measure_phi is callable."""
    from experiment_no_memory import measure_phi
    assert callable(measure_phi)


def test_run_baseline_exists():
    """Verify run_baseline is callable."""
    from experiment_no_memory import run_baseline
    assert callable(run_baseline)


def test_run_no_hebbian_exists():
    """Verify run_no_hebbian is callable."""
    from experiment_no_memory import run_no_hebbian
    assert callable(run_no_hebbian)


def test_run_no_gru_memory_exists():
    """Verify run_no_gru_memory is callable."""
    from experiment_no_memory import run_no_gru_memory
    assert callable(run_no_gru_memory)


def test_run_no_both_exists():
    """Verify run_no_both is callable."""
    from experiment_no_memory import run_no_both
    assert callable(run_no_both)


def test_run_goldfish_exists():
    """Verify run_goldfish is callable."""
    from experiment_no_memory import run_goldfish
    assert callable(run_goldfish)


def test_run_accumulation_exists():
    """Verify run_accumulation is callable."""
    from experiment_no_memory import run_accumulation
    assert callable(run_accumulation)


def test_ascii_bar_exists():
    """Verify ascii_bar is callable."""
    from experiment_no_memory import ascii_bar
    assert callable(ascii_bar)


def test_ascii_sparkline_exists():
    """Verify ascii_sparkline is callable."""
    from experiment_no_memory import ascii_sparkline
    assert callable(ascii_sparkline)


def test_main_exists():
    """Verify main is callable."""
    from experiment_no_memory import main
    assert callable(main)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
