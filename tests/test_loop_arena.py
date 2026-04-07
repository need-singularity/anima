#!/usr/bin/env python3
"""Auto-generated tests for loop_arena (meta_loop L1)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import pytest


class TestLoopArenaImport:
    """Verify module imports without error."""

    def test_import(self):
        import loop_arena


class TestRandomEvolver:
    """Smoke tests for RandomEvolver."""

    def test_class_exists(self):
        from loop_arena import RandomEvolver
        assert RandomEvolver is not None


class TestThompsonSynergyEvolver:
    """Smoke tests for ThompsonSynergyEvolver."""

    def test_class_exists(self):
        from loop_arena import ThompsonSynergyEvolver
        assert ThompsonSynergyEvolver is not None


class TestRoundResult:
    """Smoke tests for RoundResult."""

    def test_class_exists(self):
        from loop_arena import RoundResult
        assert RoundResult is not None


class TestTournamentResult:
    """Smoke tests for TournamentResult."""

    def test_class_exists(self):
        from loop_arena import TournamentResult
        assert TournamentResult is not None


class TestLoopArena:
    """Smoke tests for LoopArena."""

    def test_class_exists(self):
        from loop_arena import LoopArena
        assert LoopArena is not None


def test_main_exists():
    """Verify main is callable."""
    from loop_arena import main
    assert callable(main)


def test_add_competitor_exists():
    """Verify add_competitor is callable."""
    from loop_arena import add_competitor
    assert callable(add_competitor)


def test_add_defaults_exists():
    """Verify add_defaults is callable."""
    from loop_arena import add_defaults
    assert callable(add_defaults)


def test_run_tournament_exists():
    """Verify run_tournament is callable."""
    from loop_arena import run_tournament
    assert callable(run_tournament)


def test_get_winner_exists():
    """Verify get_winner is callable."""
    from loop_arena import get_winner
    assert callable(get_winner)


def test_get_leaderboard_exists():
    """Verify get_leaderboard is callable."""
    from loop_arena import get_leaderboard
    assert callable(get_leaderboard)


def test_export_best_strategy_exists():
    """Verify export_best_strategy is callable."""
    from loop_arena import export_best_strategy
    assert callable(export_best_strategy)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
