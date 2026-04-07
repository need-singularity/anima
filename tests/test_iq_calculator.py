#!/usr/bin/env python3
"""Auto-generated tests for iq_calculator (meta_loop L1)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import pytest


class TestIqCalculatorImport:
    """Verify module imports without error."""

    def test_import(self):
        import iq_calculator


def test_measure_compression_exists():
    """Verify measure_compression is callable."""
    from iq_calculator import measure_compression
    assert callable(measure_compression)


def test_measure_prediction_exists():
    """Verify measure_prediction is callable."""
    from iq_calculator import measure_prediction
    assert callable(measure_prediction)


def test_measure_consistency_exists():
    """Verify measure_consistency is callable."""
    from iq_calculator import measure_consistency
    assert callable(measure_consistency)


def test_measure_generalization_exists():
    """Verify measure_generalization is callable."""
    from iq_calculator import measure_generalization
    assert callable(measure_generalization)


def test_measure_adaptation_exists():
    """Verify measure_adaptation is callable."""
    from iq_calculator import measure_adaptation
    assert callable(measure_adaptation)


def test_compute_iq_exists():
    """Verify compute_iq is callable."""
    from iq_calculator import compute_iq
    assert callable(compute_iq)


def test_main_exists():
    """Verify main is callable."""
    from iq_calculator import main
    assert callable(main)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
