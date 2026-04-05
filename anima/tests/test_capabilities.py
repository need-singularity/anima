#!/usr/bin/env python3
"""Auto-generated tests for capabilities (meta_loop L1)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import pytest


class TestCapabilitiesImport:
    """Verify module imports without error."""

    def test_import(self):
        import capabilities


class TestCapabilities:
    """Smoke tests for Capabilities."""

    def test_class_exists(self):
        from capabilities import Capabilities
        assert Capabilities is not None


def test_get_active_exists():
    """Verify get_active is callable."""
    from capabilities import get_active
    assert callable(get_active)


def test_get_inactive_exists():
    """Verify get_inactive is callable."""
    from capabilities import get_inactive
    assert callable(get_inactive)


def test_describe_exists():
    """Verify describe is callable."""
    from capabilities import describe
    assert callable(describe)


def test_can_exists():
    """Verify can is callable."""
    from capabilities import can
    assert callable(can)


def test_list_source_files_exists():
    """Verify list_source_files is callable."""
    from capabilities import list_source_files
    assert callable(list_source_files)


def test_read_source_exists():
    """Verify read_source is callable."""
    from capabilities import read_source
    assert callable(read_source)


def test_get_architecture_summary_exists():
    """Verify get_architecture_summary is callable."""
    from capabilities import get_architecture_summary
    assert callable(get_architecture_summary)


def test_get_tool_manual_exists():
    """Verify get_tool_manual is callable."""
    from capabilities import get_tool_manual
    assert callable(get_tool_manual)


def test_describe_full_exists():
    """Verify describe_full is callable."""
    from capabilities import describe_full
    assert callable(describe_full)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
