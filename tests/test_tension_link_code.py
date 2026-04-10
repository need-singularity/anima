#!/usr/bin/env python3
"""Auto-generated tests for tension_link_code (meta_loop L1)."""
import sys, os
# FIX(2026-04-10): tension_link_code moved from src/ to anima/models/legacy/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "anima", "models", "legacy"))
import pytest


class TestTensionLinkCodeImport:
    """Verify module imports without error."""

    def test_import(self):
        import tension_link_code


class TestTensionLinkCode:
    """Smoke tests for TensionLinkCode."""

    def test_class_exists(self):
        from tension_link_code import TensionLinkCode
        assert TensionLinkCode is not None


def test_main_exists():
    """Verify main is callable."""
    from tension_link_code import main
    assert callable(main)


def test_generate_exists():
    """Verify generate is callable."""
    from tension_link_code import generate
    assert callable(generate)


def test_connect_exists():
    """Verify connect is callable."""
    from tension_link_code import connect
    assert callable(connect)


def test_send_exists():
    """Verify send is callable."""
    from tension_link_code import send
    assert callable(send)


def test_stop_exists():
    """Verify stop is callable."""
    from tension_link_code import stop
    assert callable(stop)


def test_status_exists():
    """Verify status is callable."""
    from tension_link_code import status
    assert callable(status)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
