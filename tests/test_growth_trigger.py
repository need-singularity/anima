"""Tests for GrowthEngine dual growth trigger."""

import json
import tempfile
from pathlib import Path

import pytest

from growth_engine import GrowthEngine, STAGES


class TestDualGrowthTrigger:
    """Test should_grow requires both tension saturation AND consolidation failure."""

    def test_both_conditions_required(self):
        """Only when both saturated AND failing does should_grow return True."""
        g = GrowthEngine()

        # Neither condition met
        assert g.should_grow() is False

        # Only tension saturated (low CV), consolidation OK
        for _ in range(30):
            g.record_tension(1.0)
        assert g._tension_saturated() is True
        assert g._consolidation_failing() is False
        assert g.should_grow() is False

        # Reset — only consolidation failing, no tension history
        g2 = GrowthEngine()
        g2.update_consolidation_stats(10, 8)  # 80% fail
        assert g2._tension_saturated() is False
        assert g2._consolidation_failing() is True
        assert g2.should_grow() is False

        # Both conditions met
        g.update_consolidation_stats(10, 8)
        assert g._tension_saturated() is True
        assert g._consolidation_failing() is True
        assert g.should_grow() is True

    def test_max_stage_cannot_grow(self):
        """At the last stage, should_grow always returns False."""
        g = GrowthEngine()
        g.stage_index = len(STAGES) - 1  # adult (last stage)

        # Set up both conditions
        for _ in range(30):
            g.record_tension(1.0)
        g.update_consolidation_stats(10, 8)

        assert g._tension_saturated() is True
        assert g._consolidation_failing() is True
        assert g.should_grow() is False

    def test_not_enough_history(self):
        """With < 30 tension records, tension_saturated returns False."""
        g = GrowthEngine()
        for _ in range(29):
            g.record_tension(1.0)
        assert g._tension_saturated() is False

        # One more makes it 30
        g.record_tension(1.0)
        assert g._tension_saturated() is True

    def test_update_consolidation_rate(self):
        """10 attempted, 7 failed => rate = 0.7 (not > 0.7, so not failing)."""
        g = GrowthEngine()
        g.update_consolidation_stats(10, 7)
        assert g._consolidation_fail_rate == pytest.approx(0.7)
        assert g._consolidation_failing() is False  # > 0.7 required, 0.7 is not >

        # One more failure tips it over
        g.update_consolidation_stats(1, 1)
        assert g._consolidation_fail_rate == pytest.approx(8 / 11)
        assert g._consolidation_failing() is True

    def test_record_tension_window(self):
        """Adding 250 tensions keeps only the last 200."""
        g = GrowthEngine()
        for i in range(250):
            g.record_tension(float(i))
        assert len(g.tension_history) == 200
        assert g.tension_history[0] == 50.0
        assert g.tension_history[-1] == 249.0

    def test_save_load_preserves_stats(self):
        """Save then load into a new instance preserves consolidation state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "growth.json"

            g1 = GrowthEngine(save_path=path)
            g1.update_consolidation_stats(20, 15)
            for i in range(35):
                g1.record_tension(float(i))
            g1.save()

            g2 = GrowthEngine(save_path=path)
            g2.load()

            assert g2._consolidation_attempts == 20
            assert g2._consolidation_failures == 15
            assert g2._consolidation_fail_rate == pytest.approx(15 / 20)
            assert len(g2.tension_history) == 35
            assert g2.tension_history[-1] == 34.0
