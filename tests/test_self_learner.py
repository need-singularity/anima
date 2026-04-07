#!/usr/bin/env python3
"""Auto-generated tests for self_learner (meta_loop L1)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import pytest


class TestSelfLearnerImport:
    """Verify module imports without error."""

    def test_import(self):
        import self_learner


class TestSelfLearner:
    """Smoke tests for SelfLearner."""

    def test_class_exists(self):
        from self_learner import SelfLearner
        assert SelfLearner is not None


def test_main_exists():
    """Verify main is callable."""
    from self_learner import main
    assert callable(main)


def test_assess_exists():
    """Verify assess is callable."""
    from self_learner import assess
    assert callable(assess)


def test_collect_exists():
    """Verify collect is callable."""
    from self_learner import collect
    assert callable(collect)


def test_select_by_curiosity_exists():
    """Verify select_by_curiosity is callable."""
    from self_learner import select_by_curiosity
    assert callable(select_by_curiosity)


def test_learn_exists():
    """Verify learn is callable."""
    from self_learner import learn
    assert callable(learn)


def test_evaluate_exists():
    """Verify evaluate is callable."""
    from self_learner import evaluate
    assert callable(evaluate)


def test_save_exists():
    """Verify save is callable."""
    from self_learner import save
    assert callable(save)


def test_load_exists():
    """Verify load is callable."""
    from self_learner import load
    assert callable(load)


def test_run_cycle_exists():
    """Verify run_cycle is callable."""
    from self_learner import run_cycle
    assert callable(run_cycle)


def test_auto_loop_exists():
    """Verify auto_loop is callable."""
    from self_learner import auto_loop
    assert callable(auto_loop)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
