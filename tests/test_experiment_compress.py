#!/usr/bin/env python3
"""Auto-generated tests for experiment_compress (meta_loop L1)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import pytest


class TestExperimentCompressImport:
    """Verify module imports without error."""

    def test_import(self):
        import experiment_compress


def test_measure_engine_exists():
    """Verify measure_engine is callable."""
    from experiment_compress import measure_engine
    assert callable(measure_engine)


def test_warmup_engine_exists():
    """Verify warmup_engine is callable."""
    from experiment_compress import warmup_engine
    assert callable(warmup_engine)


def test_exp1_baseline_exists():
    """Verify exp1_baseline is callable."""
    from experiment_compress import exp1_baseline
    assert callable(exp1_baseline)


def test_exp2_cell_pruning_exists():
    """Verify exp2_cell_pruning is callable."""
    from experiment_compress import exp2_cell_pruning
    assert callable(exp2_cell_pruning)


def test_exp3_dimension_reduction_exists():
    """Verify exp3_dimension_reduction is callable."""
    from experiment_compress import exp3_dimension_reduction
    assert callable(exp3_dimension_reduction)


def test_exp4_distillation_exists():
    """Verify exp4_distillation is callable."""
    from experiment_compress import exp4_distillation
    assert callable(exp4_distillation)


def test_exp5_minimum_viable_exists():
    """Verify exp5_minimum_viable is callable."""
    from experiment_compress import exp5_minimum_viable
    assert callable(exp5_minimum_viable)


def test_summarize_exists():
    """Verify summarize is callable."""
    from experiment_compress import summarize
    assert callable(summarize)


def test_main_exists():
    """Verify main is callable."""
    from experiment_compress import main
    assert callable(main)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
