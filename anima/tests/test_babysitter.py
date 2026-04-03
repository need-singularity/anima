#!/usr/bin/env python3
"""Auto-generated tests for babysitter (meta_loop L1)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import pytest


class TestBabysitterImport:
    """Verify module imports without error."""

    def test_import(self):
        import babysitter


class TestBabysitter:
    """Smoke tests for Babysitter."""

    def test_class_exists(self):
        from babysitter import Babysitter
        assert Babysitter is not None


def test_check_cli_exists():
    """Verify check_cli is callable."""
    from babysitter import check_cli
    assert callable(check_cli)


def test_start_exists():
    """Verify start is callable."""
    from babysitter import start
    assert callable(start)


def test_stop_exists():
    """Verify stop is callable."""
    from babysitter import stop
    assert callable(stop)


def test_set_topic_exists():
    """Verify set_topic is callable."""
    from babysitter import set_topic
    assert callable(set_topic)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
