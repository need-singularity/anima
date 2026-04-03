#!/usr/bin/env python3
"""Auto-generated tests for model_comparator (meta_loop L1)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import pytest


class TestModelComparatorImport:
    """Verify module imports without error."""

    def test_import(self):
        import model_comparator


def test_compare_checkpoints_exists():
    """Verify compare_checkpoints is callable."""
    from model_comparator import compare_checkpoints
    assert callable(compare_checkpoints)


def test_compare_latest_in_dir_exists():
    """Verify compare_latest_in_dir is callable."""
    from model_comparator import compare_latest_in_dir
    assert callable(compare_latest_in_dir)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
