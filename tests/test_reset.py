#!/usr/bin/env python3
"""Auto-generated tests for reset (meta_loop L1)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import pytest


class TestResetImport:
    """Verify module imports without error."""

    def test_import(self):
        import reset


def test_reset_local_exists():
    """Verify reset_local is callable."""
    from reset import reset_local
    assert callable(reset_local)


def test_reset_remote_exists():
    """Verify reset_remote is callable."""
    from reset import reset_remote
    assert callable(reset_remote)


def test_main_exists():
    """Verify main is callable."""
    from reset import main
    assert callable(main)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
