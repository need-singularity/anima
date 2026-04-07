#!/usr/bin/env python3
"""Auto-generated tests for scale_aware_evolver (meta_loop L1)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import pytest


class TestScaleAwareEvolverImport:
    """Verify module imports without error."""

    def test_import(self):
        import scale_aware_evolver


class TestScaleReport:
    """Smoke tests for ScaleReport."""

    def test_class_exists(self):
        from scale_aware_evolver import ScaleReport
        assert ScaleReport is not None


class TestScaleAwareEvolver:
    """Smoke tests for ScaleAwareEvolver."""

    def test_class_exists(self):
        from scale_aware_evolver import ScaleAwareEvolver
        assert ScaleAwareEvolver is not None


def test_main_exists():
    """Verify main is callable."""
    from scale_aware_evolver import main
    assert callable(main)


def test_run_adaptive_exists():
    """Verify run_adaptive is callable."""
    from scale_aware_evolver import run_adaptive
    assert callable(run_adaptive)


def test_compare_scales_exists():
    """Verify compare_scales is callable."""
    from scale_aware_evolver import compare_scales
    assert callable(compare_scales)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
