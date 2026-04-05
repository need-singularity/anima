#!/usr/bin/env python3
"""Auto-generated tests for setup_secrets (meta_loop L1)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import pytest


class TestSetupSecretsImport:
    """Verify module imports without error."""

    def test_import(self):
        import setup_secrets


def test_load_env_file_exists():
    """Verify load_env_file is callable."""
    from setup_secrets import load_env_file
    assert callable(load_env_file)


def test_main_exists():
    """Verify main is callable."""
    from setup_secrets import main
    assert callable(main)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
