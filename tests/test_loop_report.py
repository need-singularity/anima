#!/usr/bin/env python3
"""Auto-generated tests for loop_report (meta_loop L1)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import pytest


class TestLoopReportImport:
    """Verify module imports without error."""

    def test_import(self):
        import loop_report


def test_full_report_exists():
    """Verify full_report is callable."""
    from loop_report import full_report
    assert callable(full_report)


def test_export_all_exists():
    """Verify export_all is callable."""
    from loop_report import export_all
    assert callable(export_all)


def test_short_report_exists():
    """Verify short_report is callable."""
    from loop_report import short_report
    assert callable(short_report)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
