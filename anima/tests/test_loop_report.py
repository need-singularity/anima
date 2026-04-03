#!/usr/bin/env python3
"""Tests for loop_report.py"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from loop_report import full_report, short_report, export_all


def test_full_report_returns_string():
    text = full_report()
    assert isinstance(text, str)
    assert len(text) > 0


def test_full_report_has_box():
    text = full_report()
    assert '┌' in text
    assert '└' in text


def test_full_report_has_header():
    text = full_report()
    assert '루프' in text or 'LOOP' in text or '리포트' in text


def test_short_report_returns_string():
    line = short_report()
    assert isinstance(line, str)
    assert '[LOOP]' in line


def test_short_report_single_line():
    line = short_report()
    assert '\n' not in line


def test_export_all_returns_list():
    exported = export_all()
    assert isinstance(exported, list)


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
