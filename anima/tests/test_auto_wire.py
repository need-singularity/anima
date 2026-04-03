#!/usr/bin/env python3
"""Tests for auto_wire.py"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from auto_wire import scan_modules, auto_patch, report, EXCLUDE


def test_scan_modules_returns_dict():
    result = scan_modules()
    assert isinstance(result, dict)
    assert 'connected' in result
    assert 'missing' in result
    assert 'no_main' in result


def test_scan_modules_lists():
    result = scan_modules()
    assert isinstance(result['connected'], list)
    assert isinstance(result['missing'], list)
    assert isinstance(result['no_main'], list)


def test_scan_modules_excludes_self():
    result = scan_modules()
    all_names = result['connected'] + result['missing'] + result['no_main']
    for excluded in EXCLUDE:
        assert excluded not in all_names


def test_auto_patch_dry_run():
    patched = auto_patch(dry_run=True)
    assert isinstance(patched, list)


def test_report_returns_string():
    text = report()
    assert isinstance(text, str)
    assert 'Auto-Wire' in text


def test_exclude_contains_expected():
    assert 'auto_wire.py' in EXCLUDE
    assert 'path_setup.py' in EXCLUDE
    assert '__init__.py' in EXCLUDE


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
