#!/usr/bin/env python3
"""Auto-generated tests for consciousness_debugger (meta_loop L1)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import pytest


class TestConsciousnessDebuggerImport:
    """Verify module imports without error."""

    def test_import(self):
        import consciousness_debugger


class TestAnomalyType:
    """Smoke tests for AnomalyType."""

    def test_class_exists(self):
        from consciousness_debugger import AnomalyType
        assert AnomalyType is not None


class TestAnomaly:
    """Smoke tests for Anomaly."""

    def test_class_exists(self):
        from consciousness_debugger import Anomaly
        assert Anomaly is not None


class TestConsciousnessDebugger:
    """Smoke tests for ConsciousnessDebugger."""

    def test_class_exists(self):
        from consciousness_debugger import ConsciousnessDebugger
        assert ConsciousnessDebugger is not None


def test_main_exists():
    """Verify main is callable."""
    from consciousness_debugger import main
    assert callable(main)


def test_record_exists():
    """Verify record is callable."""
    from consciousness_debugger import record
    assert callable(record)


def test_detect_anomaly_exists():
    """Verify detect_anomaly is callable."""
    from consciousness_debugger import detect_anomaly
    assert callable(detect_anomaly)


def test_auto_recover_exists():
    """Verify auto_recover is callable."""
    from consciousness_debugger import auto_recover
    assert callable(auto_recover)


def test_render_dashboard_exists():
    """Verify render_dashboard is callable."""
    from consciousness_debugger import render_dashboard
    assert callable(render_dashboard)


def test_health_score_exists():
    """Verify health_score is callable."""
    from consciousness_debugger import health_score
    assert callable(health_score)


def test_summary_exists():
    """Verify summary is callable."""
    from consciousness_debugger import summary
    assert callable(summary)


def test_sparkline_exists():
    """Verify sparkline is callable."""
    from consciousness_debugger import sparkline
    assert callable(sparkline)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
