#!/usr/bin/env python3
"""Auto-generated tests for setup (meta_loop L1)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import pytest


class TestSetupImport:
    """Verify module imports without error."""

    def test_import(self):
        import setup


def test_create_dirs_exists():
    """Verify create_dirs is callable."""
    from setup import create_dirs
    assert callable(create_dirs)


def test_create_config_exists():
    """Verify create_config is callable."""
    from setup import create_config
    assert callable(create_config)


def test_configure_r2_exists():
    """Verify configure_r2 is callable."""
    from setup import configure_r2
    assert callable(configure_r2)


def test_download_model_exists():
    """Verify download_model is callable."""
    from setup import download_model
    assert callable(download_model)


def test_symlink_checkpoints_exists():
    """Verify symlink_checkpoints is callable."""
    from setup import symlink_checkpoints
    assert callable(symlink_checkpoints)


def test_show_status_exists():
    """Verify show_status is callable."""
    from setup import show_status
    assert callable(show_status)


def test_main_exists():
    """Verify main is callable."""
    from setup import main
    assert callable(main)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
