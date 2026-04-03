#!/usr/bin/env python3
"""Auto-generated tests for phi_curvature (meta_loop L1)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import pytest


class TestPhiCurvatureImport:
    """Verify module imports without error."""

    def test_import(self):
        import phi_curvature


class TestPhiCurvatureCalculator:
    """Smoke tests for PhiCurvatureCalculator."""

    def test_class_exists(self):
        from phi_curvature import PhiCurvatureCalculator
        assert PhiCurvatureCalculator is not None


def test_compute_phi_curvature_exists():
    """Verify compute_phi_curvature is callable."""
    from phi_curvature import compute_phi_curvature
    assert callable(compute_phi_curvature)


def test_main_exists():
    """Verify main is callable."""
    from phi_curvature import main
    assert callable(main)


def test_compute_exists():
    """Verify compute is callable."""
    from phi_curvature import compute
    assert callable(compute)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
