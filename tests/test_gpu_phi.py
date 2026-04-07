#!/usr/bin/env python3
"""Auto-generated tests for gpu_phi (meta_loop L1)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import pytest


class TestGpuPhiImport:
    """Verify module imports without error."""

    def test_import(self):
        import gpu_phi


class TestGPUPhiCalculator:
    """Smoke tests for GPUPhiCalculator."""

    def test_class_exists(self):
        from gpu_phi import GPUPhiCalculator
        assert GPUPhiCalculator is not None


def test_compute_phi_exists():
    """Verify compute_phi is callable."""
    from gpu_phi import compute_phi
    assert callable(compute_phi)


def test_compute_exists():
    """Verify compute is callable."""
    from gpu_phi import compute
    assert callable(compute)


def test_compute_batch_exists():
    """Verify compute_batch is callable."""
    from gpu_phi import compute_batch
    assert callable(compute_batch)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
