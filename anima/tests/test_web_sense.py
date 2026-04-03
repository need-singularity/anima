#!/usr/bin/env python3
"""Auto-generated tests for web_sense (meta_loop L1)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import pytest


class TestWebSenseImport:
    """Verify module imports without error."""

    def test_import(self):
        import web_sense


class TestWebSense:
    """Smoke tests for WebSense."""

    def test_class_exists(self):
        from web_sense import WebSense
        assert WebSense is not None


def test_html_to_text_exists():
    """Verify html_to_text is callable."""
    from web_sense import html_to_text
    assert callable(html_to_text)


def test_fetch_url_exists():
    """Verify fetch_url is callable."""
    from web_sense import fetch_url
    assert callable(fetch_url)


def test_search_duckduckgo_exists():
    """Verify search_duckduckgo is callable."""
    from web_sense import search_duckduckgo
    assert callable(search_duckduckgo)


def test_extract_search_query_exists():
    """Verify extract_search_query is callable."""
    from web_sense import extract_search_query
    assert callable(extract_search_query)


def test_handle_starttag_exists():
    """Verify handle_starttag is callable."""
    from web_sense import handle_starttag
    assert callable(handle_starttag)


def test_handle_endtag_exists():
    """Verify handle_endtag is callable."""
    from web_sense import handle_endtag
    assert callable(handle_endtag)


def test_handle_data_exists():
    """Verify handle_data is callable."""
    from web_sense import handle_data
    assert callable(handle_data)


def test_get_text_exists():
    """Verify get_text is callable."""
    from web_sense import get_text
    assert callable(get_text)


def test_should_search_exists():
    """Verify should_search is callable."""
    from web_sense import should_search
    assert callable(should_search)


def test_search_exists():
    """Verify search is callable."""
    from web_sense import search
    assert callable(search)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
